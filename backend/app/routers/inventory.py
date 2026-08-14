import io

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role, get_current_user
from app.models.inventory import InventoryItem
from app.models.user import User, RoleEnum
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemOut,
    InventoryItemPublicOut,
    BulkImportResult,
)

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

# ---------------------------------------------------------------------------
# Column name aliases for bulk import.
# The importer tries each alias in order and uses the first one found.
# This means existing exports (part_name, fits_models, quantity, min_stock)
# import without any manual column renaming.
# ---------------------------------------------------------------------------
COL_ALIASES = {
    "part_number":    ["part_number", "partno", "part_no", "sku", "item_code", "code"],
    "name":           ["name", "part_name", "partname", "item_name", "description"],
    "category":       ["category", "cat", "type", "item_type"],
    "stock_quantity": ["stock_quantity", "quantity", "qty", "stock", "current_stock",
                       "opening_stock"],
    "min_threshold":  ["min_threshold", "min_stock", "min_qty", "minimum_stock",
                       "reorder_level", "reorder"],
    "cost_price":     ["cost_price", "cost", "purchase_price", "buy_price", "cp"],
    "selling_price":  ["selling_price", "price", "sell_price", "mrp", "sp", "rate"],
    "brand":          ["brand", "make", "manufacturer", "oem"],
    "bike_model":     ["bike_model", "fits_models", "model", "fits", "vehicle_model",
                       "compatible_models", "model_name"],
}

REQUIRED_FIELDS = {"name", "selling_price"}


def _resolve_columns(df_cols: list[str]) -> dict[str, str]:
    col_set = set(df_cols)
    resolved = {}
    for our_field, aliases in COL_ALIASES.items():
        for alias in aliases:
            if alias in col_set:
                resolved[our_field] = alias
                break
    missing = REQUIRED_FIELDS - set(resolved.keys())
    if missing:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Could not find required column(s): {', '.join(sorted(missing))}. "
                f"Accepted names for 'name': {COL_ALIASES['name']}. "
                f"Accepted names for 'selling_price': {COL_ALIASES['selling_price']}."
            ),
        )
    return resolved


def _serialize(item: InventoryItem, role: RoleEnum):
    if role == RoleEnum.ADMIN:
        return InventoryItemOut.model_validate(item)
    return InventoryItemPublicOut.model_validate(item)


def _normalize_part_number(value):
    """Trim whitespace; treat empty/blank as None. Comparison stays
    case-sensitive to match existing data and the DB unique index."""
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _trim_inventory_list(item: InventoryItem, role: RoleEnum):
    payload = _serialize(item, role).model_dump()
    allowed = [
        "part_id", "part_number", "name", "category", "brand", "bike_model",
        "stock_quantity", "min_threshold", "cost_price", "selling_price", "is_low_stock",
    ]
    return {k: payload.get(k) for k in allowed if k in payload}


def _find_by_part_number(db: Session, part_number: str):
    return db.query(InventoryItem).filter(
        InventoryItem.part_number == part_number
    ).first()


@router.get("/by-part-number/{part_number}")
def get_by_part_number(
    part_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Real-time lookup used by the Add Part form. Returns the part if the
    part number exists, 404 if it does not."""
    pn = _normalize_part_number(part_number)
    if not pn:
        raise HTTPException(status_code=400, detail="Part number is empty.")
    item = _find_by_part_number(db, pn)
    if not item:
        raise HTTPException(status_code=404, detail="Part number not found.")
    return _serialize(item, current_user.role)


@router.get("")
def list_inventory(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = Query(None, max_length=100),
    in_stock_only: bool = False,
    low_stock_only: bool = False,
):
    query = db.query(InventoryItem).order_by(InventoryItem.name)
    search_term = (search or "").strip()
    if search_term:
        pattern = f"%{search_term}%"
        query = query.filter(or_(
            InventoryItem.name.ilike(pattern),
            InventoryItem.part_number.ilike(pattern),
            InventoryItem.category.ilike(pattern),
            InventoryItem.brand.ilike(pattern),
            InventoryItem.bike_model.ilike(pattern),
        ))
    if in_stock_only:
        query = query.filter(InventoryItem.stock_quantity > 0)
    if low_stock_only:
        query = query.filter(InventoryItem.stock_quantity <= InventoryItem.min_threshold)
    total = query.count()
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size if total else 1

    return {
        "items": [_trim_inventory_list(item, current_user.role) for item in items],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


@router.get("/low-stock")
def low_stock_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.core.cache import get_or_set_cache

    key = f"low-stock:{current_user.role.value}"
    items = get_or_set_cache(
        key,
        ttl_seconds=15,
        factory=lambda: db.query(InventoryItem)
            .filter(InventoryItem.stock_quantity <= InventoryItem.min_threshold)
            .order_by(InventoryItem.name)
            .all(),
    )
    return [_trim_inventory_list(item, current_user.role) for item in items]


@router.post("", response_model=InventoryItemOut, status_code=201)
def create_item(
    payload: InventoryItemCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role(RoleEnum.ADMIN)),
):
    data = payload.model_dump()
    data["part_number"] = _normalize_part_number(data.get("part_number"))
    if data["part_number"]:
        existing = _find_by_part_number(db, data["part_number"])
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Part number '{data['part_number']}' already exists "
                       f"(part: {existing.name}).",
            )
    item = InventoryItem(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{part_id}", response_model=InventoryItemOut)
def update_item(
    part_id: int,
    payload: InventoryItemUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role(RoleEnum.ADMIN)),
):
    item = db.query(InventoryItem).filter(InventoryItem.part_id == part_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Part not found")
    updates = payload.model_dump(exclude_unset=True)
    if "part_number" in updates:
        new_pn = _normalize_part_number(updates["part_number"])
        updates["part_number"] = new_pn
        if new_pn and new_pn != item.part_number:
            existing = _find_by_part_number(db, new_pn)
            if existing and existing.part_id != part_id:
                raise HTTPException(
                    status_code=409,
                    detail=f"Part number '{new_pn}' already exists "
                           f"(part: {existing.name}).",
                )
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{part_id}", status_code=204)
def delete_item(
    part_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role(RoleEnum.ADMIN)),
):
    item = db.query(InventoryItem).filter(InventoryItem.part_id == part_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Part not found")
    db.delete(item)
    db.commit()


@router.post("/upload", response_model=BulkImportResult)
def bulk_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role(RoleEnum.ADMIN, RoleEnum.DESK)),
):
    """
    Bulk-import parts from .xlsx, .xls, or .csv.

    Accepts flexible column names — your existing exports work as-is:
      part_name / name            → part name
      fits_models / bike_model    → compatible bike models
      quantity / stock_quantity   → current stock
      min_stock / min_threshold   → low stock alert level
      cost_price / cost           → purchase price
      selling_price / price / mrp → selling price
      brand / make                → brand
      part_number / sku           → unique part code

    Columns like 'id' and 'sync_status' are silently ignored.
    Rows with a duplicate part_number are skipped (not overwritten).
    Rows missing name or selling_price are skipped and reported.
    """
    filename = (file.filename or "").lower()
    raw_bytes = file.file.read()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(raw_bytes))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(raw_bytes))
        else:
            raise HTTPException(
                status_code=400, detail="File must be .csv, .xlsx, or .xls"
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {exc}")

    # Normalise column names: lowercase + replace spaces with underscores
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    col_map = _resolve_columns(list(df.columns))

    def _get(row, field, default=None):
        col = col_map.get(field)
        if col is None:
            return default
        val = row.get(col)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return default
        return val

    new_items = []
    skipped_rows = []
    errors = []

    # Pre-load existing part numbers to avoid per-row DB queries
    seen_in_batch: set[str] = set()
    existing_part_numbers: set[str] = {
        r[0] for r in
        db.query(InventoryItem.part_number)
          .filter(InventoryItem.part_number.isnot(None)).all()
    }

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-based + header row
        try:
            # Name — required
            name = _get(row, "name")
            if not name or str(name).strip().lower() in ("", "nan"):
                raise ValueError("Missing part name")
            name = str(name).strip()

            # Selling price — required
            sp_raw = _get(row, "selling_price")
            if sp_raw is None:
                raise ValueError("Missing selling price")
            selling_price = float(sp_raw)

            # Part number — optional but must be unique
            part_number = _normalize_part_number(_get(row, "part_number"))
            if part_number is not None:
                if part_number in existing_part_numbers:
                    skipped_rows.append(row_num)
                    errors.append(
                        f"Row {row_num}: part_number '{part_number}' already exists "
                        f"in inventory — skipped."
                    )
                    continue
                if part_number in seen_in_batch:
                    skipped_rows.append(row_num)
                    errors.append(
                        f"Row {row_num}: part_number '{part_number}' appears more "
                        f"than once in this file — only the first was kept."
                    )
                    continue
                seen_in_batch.add(part_number)

            # Optional fields
            def _str(field):
                v = _get(row, field)
                return str(v).strip() if v is not None else None

            category       = _str("category")
            brand          = _str("brand")
            bike_model     = _str("bike_model")
            stock_quantity = int(float(_get(row, "stock_quantity", 0) or 0))
            min_threshold  = int(float(_get(row, "min_threshold", 5) or 5))
            cp_raw         = _get(row, "cost_price")
            cost_price     = float(cp_raw) if cp_raw is not None else None

            new_items.append(InventoryItem(
                part_number=part_number,
                name=name,
                category=category,
                brand=brand,
                bike_model=bike_model,
                stock_quantity=stock_quantity,
                min_threshold=min_threshold,
                cost_price=cost_price,
                selling_price=selling_price,
            ))

        except (ValueError, TypeError) as exc:
            skipped_rows.append(row_num)
            errors.append(f"Row {row_num}: {exc}")

    if new_items:
        try:
            db.bulk_save_objects(new_items)
            db.commit()
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Database insert failed — no rows saved: {exc}",
            )

    return BulkImportResult(
        inserted=len(new_items),
        skipped_rows=skipped_rows,
        errors=errors,
    )

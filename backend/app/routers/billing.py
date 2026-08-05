import io, os
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from app.core.database import get_db
from app.core.deps import require_role
from app.models.job_card import JobCard, JobStatusEnum
from app.models.user import User, RoleEnum

router = APIRouter(prefix="/api/billing", tags=["billing"])

# ── Colours ──────────────────────────────────────────────────────────────────
DARK_BLUE  = colors.HexColor("#1a3c6e")
RED        = colors.HexColor("#c0392b")
LIGHT_GREY = colors.HexColor("#f4f6f9")
MID_GREY   = colors.HexColor("#777777")
BORDER     = colors.HexColor("#dce3ea")
WHITE      = colors.white

ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "invoice"
)

# Preset Hindi header/footer images (same text as login page — rendered once
# with proper Devanagari shaping so PDFs don't break characters apart).
PRESET_IMAGES = {
    "shop_name": "shop_name.png",
    "tagline":   "tagline.png",
    "address":   "address.png",
    "owner":     "owner.png",
    "footer1":   "footer1.png",
    "footer2":   "footer2.png",
}


def _preset_img(key: str, height_mm: float, align=TA_LEFT) -> Image:
    """Embed a preset Hindi PNG; height_mm sets display height on the PDF."""
    path = os.path.join(ASSETS_DIR, PRESET_IMAGES[key])
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Missing preset Hindi image: {path}. "
            "Run: python scripts/generate_hindi_assets.py"
        )
    from reportlab.lib.utils import ImageReader
    reader = ImageReader(path)
    pw, ph = reader.getSize()
    target_h = height_mm * mm
    target_w = target_h * (pw / ph)
    h_align = "RIGHT" if align == TA_RIGHT else "LEFT"
    return Image(path, width=target_w, height=target_h, hAlign=h_align)


# ── Plain English paragraph helper ───────────────────────────────────────────
def _p(text, size=9, color=colors.black, font="Helvetica",
       align=TA_LEFT, leading=None):
    s = ParagraphStyle(
        "_", fontName=font, fontSize=size, textColor=color,
        alignment=align, leading=leading or max(size * 1.4, 11),
        spaceAfter=0, spaceBefore=0,
    )
    return Paragraph(str(text), s)


# ── Invoice data calculation ──────────────────────────────────────────────────
def _calculate(job: JobCard) -> dict:
    parts_lines, parts_subtotal = [], 0.0
    for jp in job.parts_used:
        lt = round(jp.quantity_used * jp.part.selling_price, 2)
        parts_subtotal += lt
        parts_lines.append({
            "name":       jp.part.name,
            "quantity":   jp.quantity_used,
            "unit_price": jp.part.selling_price,
            "line_total": lt,
        })
    grand_total = round(parts_subtotal + job.labor_charge, 2)
    return {
        "job_id":         job.job_id,
        "invoice_date":   date.today().strftime("%d/%m/%Y"),
        "customer_name":  job.customer_name  or "—",
        "customer_phone": job.customer_phone or "—",
        "vehicle_reg":    job.vehicle_reg,
        "mechanic_name":  job.mechanic.username if job.mechanic else "—",
        "parts":          parts_lines,
        "labor_charge":   job.labor_charge,
        "parts_subtotal": parts_subtotal,
        "grand_total":    grand_total,
    }


# ── PDF builder ───────────────────────────────────────────────────────────────
def _build_pdf(d: dict) -> bytes:
    buf = io.BytesIO()
    W = A4[0] - 32 * mm

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=16*mm, rightMargin=16*mm,
        topMargin=12*mm,  bottomMargin=12*mm,
    )
    story = []

    # ── HEADER ──────────────────────────────────────────────────────────────
    # Logo
    logo_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(__file__)))),
        "frontend", "Maa_Parvati.png"
    )
    logo_cell = Image(logo_path, width=20*mm, height=20*mm) \
                if os.path.exists(logo_path) else _p("")

    # Centre column: preset Hindi title + English subtitle + preset tagline
    name_block = Table([
        [_preset_img("shop_name", 6.5)],
        [_p("SHRI PARVATI MOTORS", 11, DARK_BLUE, "Helvetica-Bold")],
        [_preset_img("tagline", 3.2)],
    ], colWidths=[W - 93*mm])
    name_block.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 1),
        ("BOTTOMPADDING", (0,0),(-1,-1), 1),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
    ]))

    # Right column: preset Hindi address + phone + preset owner name
    contact_block = Table([
        [_preset_img("address", 3.0, align=TA_RIGHT)],
        [_p("Bus Stand, Amlaha",         8, MID_GREY, "Helvetica", TA_RIGHT)],
        [_p("9926452638 / 9343219256",  10, DARK_BLUE, "Helvetica-Bold", TA_RIGHT)],
        [_preset_img("owner", 3.0, align=TA_RIGHT)],
    ], colWidths=[72*mm])
    contact_block.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 1),
        ("BOTTOMPADDING", (0,0),(-1,-1), 1),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ("ALIGN",         (0,0),(-1,-1), "RIGHT"),
    ]))

    header = Table(
        [[logo_cell, name_block, contact_block]],
        colWidths=[21*mm, W - 93*mm, 72*mm]
    )
    header.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",   (0,0),(-1,-1), 3),
        ("RIGHTPADDING",  (0,0),(-1,-1), 3),
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
    ]))
    story.append(header)
    story.append(Spacer(1, 2*mm))
    story.append(HRFlowable(width=W, thickness=2.5, color=RED, spaceAfter=5))

    # ── INVOICE META ────────────────────────────────────────────────────────
    meta = Table([[
        _p(f"Invoice No.:  JOB-{d['job_id']}", 10, RED, "Helvetica-Bold"),
        _p("", 10),
        _p(f"Date:  {d['invoice_date']}", 10, colors.black, "Helvetica-Bold", TA_RIGHT),
    ]], colWidths=[W/3, W/3, W/3])
    meta.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LIGHT_GREY),
        ("BOX",           (0,0),(-1,-1), 0.5, BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (2,0), (2,0), 20),  # Push date cell content to the right
        ("ALIGN",         (2,0), (2,0), "RIGHT"),  # Align content right in the third column
    ]))
    story.append(meta)
    story.append(Spacer(1, 3*mm))

    # ── CUSTOMER + VEHICLE ──────────────────────────────────────────────────
    half = W / 2 - 1.5*mm

    def _lbl(t): return _p(t, 7.5, MID_GREY, "Helvetica-Bold")
    def _val(t): return _p(t, 9.5, colors.black, "Helvetica-Bold")

    cv = Table([
        [_p("CUSTOMER DETAILS", 7, MID_GREY, "Helvetica-Bold"), "",
         _p("VEHICLE DETAILS",  7, MID_GREY, "Helvetica-Bold"), ""],
        [_lbl("Name"),    _val(d["customer_name"]),
         _lbl("Reg. No."),_val(d["vehicle_reg"])],
        [_lbl("Phone"),   _val(d["customer_phone"]),
         _lbl("Mechanic"),_val(d["mechanic_name"])],
    ], colWidths=[22*mm, half-22*mm, 22*mm, half-22*mm])
    cv.setStyle(TableStyle([
        ("SPAN",          (0,0),(1,0)),
        ("SPAN",          (2,0),(3,0)),
        ("BACKGROUND",    (0,0),(1,0),  LIGHT_GREY),
        ("BACKGROUND",    (2,0),(3,0),  LIGHT_GREY),
        ("BOX",           (0,0),(1,-1), 0.5, BORDER),
        ("BOX",           (2,0),(3,-1), 0.5, BORDER),
        ("LINEBELOW",     (0,0),(1,0),  0.4, BORDER),
        ("LINEBELOW",     (2,0),(3,0),  0.4, BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 7),
        ("RIGHTPADDING",  (0,0),(-1,-1), 7),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(cv)
    story.append(Spacer(1, 4*mm))

    # ── LINE ITEMS ──────────────────────────────────────────────────────────
    # Amount column widened (16mm → 26mm) so "Rs. 1191.00" never wraps.
    cw = [8*mm, W - 60*mm, 12*mm, 14*mm, 26*mm]

    def TH(t): return _p(t, 9, WHITE, "Helvetica-Bold", TA_CENTER)

    rows = [[TH("#"), TH("Description"), TH("Qty"), TH("Rate (Rs.)"), TH("Amt (Rs.)")]]

    for i, p in enumerate(d["parts"], 1):
        rows.append([
            _p(str(i), 9, align=TA_CENTER),
            _p(p["name"], 9),
            _p(str(p["quantity"]), 9, align=TA_RIGHT),
            _p(f"{p['unit_price']:.2f}", 9, align=TA_RIGHT),
            _p(f"{p['line_total']:.2f}", 9, align=TA_RIGHT),
        ])

    if d["labor_charge"] > 0:
        rows.append([
            _p(str(len(d["parts"]) + 1), 9, align=TA_CENTER),
            _p("Labour Charges", 9, MID_GREY, "Helvetica-Oblique"),
            _p("—", 9, MID_GREY, align=TA_RIGHT),
            _p("—", 9, MID_GREY, align=TA_RIGHT),
            _p(f"{d['labor_charge']:.2f}", 9, align=TA_RIGHT),
        ])

    # Grand Total row
    rows.append([
        _p(""),
        _p("Grand Total", 10, colors.black, "Helvetica-Bold"),
        _p(""), _p(""),
        _p(f"Rs. {d['grand_total']:.2f}", 10, colors.black, "Helvetica-Bold", TA_RIGHT),
    ])

    n = len(rows)
    grand_idx = n - 1
    items = Table(rows, colWidths=cw, repeatRows=1)
    items.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),                DARK_BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,grand_idx-1),      [WHITE, LIGHT_GREY]),
        ("GRID",          (0,0),(-1,grand_idx-1),      0.3, BORDER),
        ("LINEABOVE",     (0,grand_idx),(-1,grand_idx), 1.5, DARK_BLUE),
        ("BACKGROUND",    (0,grand_idx),(-1,grand_idx), colors.HexColor("#eef1f5")),
        ("SPAN",          (1,grand_idx),(3,grand_idx)),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("RIGHTPADDING",  (0,0),(-1,-1), 5),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(items)
    story.append(Spacer(1, 10*mm))

    # ── FOOTER ──────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=0.8,
                             color=colors.HexColor("#e0e0e0"), spaceAfter=5))

    # Footer preset Hindi lines
    foot = Table([[
        Table([
            [_preset_img("footer1", 3.0)],
            [_p("Thank you for choosing Shri Parvati Motors.", 8, MID_GREY)],
            [_preset_img("footer2", 3.0)],
        ], colWidths=[W * 0.58]),
        Table([
            [_p("", 8)],
            [_p("________________________", 8, MID_GREY, align=TA_RIGHT)],
            [_p("Authorised Signatory", 8, MID_GREY, align=TA_RIGHT)],
            [_p("Shri Parvati Motors", 8, MID_GREY, "Helvetica-Bold", TA_RIGHT)],
        ], colWidths=[W * 0.42]),
    ]], colWidths=[W * 0.58, W * 0.42])
    foot.setStyle(TableStyle([
        ("VALIGN", (0,0),(-1,-1), "BOTTOM"),
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
    ]))
    story.append(foot)

    doc.build(story)
    return buf.getvalue()


# ── Routes ────────────────────────────────────────────────────────────────────
@router.get("/jobcards/{job_id}/preview")
def preview_invoice_data(
    job_id: int, db: Session = Depends(get_db),
    _s: User = Depends(require_role(RoleEnum.ADMIN, RoleEnum.DESK)),
):
    job = db.query(JobCard).filter(JobCard.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job card not found")
    d = _calculate(job)
    return {
        **d,
        "labor_charge":   str(d["labor_charge"]),
        "parts_subtotal": str(d["parts_subtotal"]),
        "grand_total":    str(d["grand_total"]),
        "parts": [{**p, "unit_price": str(p["unit_price"]),
                        "line_total": str(p["line_total"])} for p in d["parts"]],
    }


@router.get("/jobcards/{job_id}/invoice")
def generate_invoice(
    job_id: int, db: Session = Depends(get_db),
    _s: User = Depends(require_role(RoleEnum.ADMIN, RoleEnum.DESK)),
):
    job = db.query(JobCard).filter(JobCard.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job card not found")
    if job.status not in (JobStatusEnum.READY_FOR_BILLING, JobStatusEnum.COMPLETED):
        raise HTTPException(
            400, f"Job is '{job.status.value}' — set to Ready_For_Billing first.")

    pdf_bytes = _build_pdf(_calculate(job))

    if job.status == JobStatusEnum.READY_FOR_BILLING:
        job.status = JobStatusEnum.COMPLETED
        db.commit()

    return StreamingResponse(
        io.BytesIO(pdf_bytes), media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice_SPM_{job_id}.pdf"},
    )

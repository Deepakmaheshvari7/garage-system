-- ============================================================
-- Shri Parvati Motors — DB Migration
-- Run this in pgAdmin Query Tool before restarting the backend
-- ============================================================

-- 1. Add labor_charge column (manual entry, replaces labor_hours)
ALTER TABLE job_cards
  ADD COLUMN IF NOT EXISTS labor_charge FLOAT DEFAULT 0.0 NOT NULL;

-- 2. Copy existing labor_hours data into labor_charge
--    (converts hours × 500 to a rupee amount so no data is lost)
UPDATE job_cards
  SET labor_charge = COALESCE(labor_hours, 0) * 500
  WHERE labor_hours IS NOT NULL AND labor_hours > 0;

-- 3. Keep labor_hours column for now (safe to drop later once confirmed)
--    If you want to drop it immediately, uncomment the line below:
-- ALTER TABLE job_cards DROP COLUMN IF EXISTS labor_hours;

-- 4. Inventory new columns (if not already added from previous migration)
ALTER TABLE inventory
  ADD COLUMN IF NOT EXISTS part_number   VARCHAR,
  ADD COLUMN IF NOT EXISTS brand         VARCHAR,
  ADD COLUMN IF NOT EXISTS bike_model    VARCHAR,
  ADD COLUMN IF NOT EXISTS min_threshold INTEGER DEFAULT 5;

-- 5. Job cards customer columns (if not already added)
ALTER TABLE job_cards
  ADD COLUMN IF NOT EXISTS customer_name  VARCHAR,
  ADD COLUMN IF NOT EXISTS customer_phone VARCHAR;

-- 6. Unique index on part_number
CREATE UNIQUE INDEX IF NOT EXISTS ix_inventory_part_number
  ON inventory(part_number)
  WHERE part_number IS NOT NULL;

-- Done. Restart the backend after running this.
SELECT 'Migration complete' AS status;

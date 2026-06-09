# CLAUDE.md — MenuPlanner Project Instructions

## What this project is
PyQt6 desktop app for **Chathradhari Caterers / Oyster canteen** — weekly meal planning tool.
Planners fill in a 5-day × 26-slot grid, then export PowerPoint slides and an Excel sheet.

## Entry point
```
python menu_planner/main.py
```

## Critical rules

### Slide generation and preview alignment
`menu_planner/export/pptx_gen.py` handles PPT exports, and `menu_planner/ui/ppt_preview.py` handles the right-side preview panel. They must always use identical dynamic category resolution logic to map grid slots and categories to PPT slide sections.

`menu_planner/export/pptx_export.py` is an old broken version — ignore it entirely.

### PPT export call signature
The `export_pptx` function is robust and accepts both a nested week structure (`{day: grid.get_day_data(day)}`) and a flat day slots dictionary (`grid.get_day_data(day)`) directly. Either format can be safely passed to `week_data`.

### QImage in ppt_preview.py
Always include `bytesPerLine` as the 4th argument:
```python
QImage(data, w, h, w * 4, QImage.Format.Format_RGBA8888)
```

### PPT uses full-res images; dish grid uses thumbnails
The `image_path` in the DB is the original high-res file.
`pptx_gen.py` reads it directly — never resize or replace it.
The dish card thumbnails are scaled at render time using `FastTransformation` — the DB path is untouched.

### DB auto-save pattern
Every cell edit → `db.set_slot(plan_id, day, slot, value)` via a 500ms debounce in `planning_grid.py`.
Never batch or defer writes — the DB is the crash-recovery store.

### Category auto-assignment
`database._auto_category(name)` assigns categories by keyword. Categories: Breakfast, Lunch, Salad, Fruit Lunch, Juice, Additionals, Dessert.
Runs on migration (existing dishes) and on `add_dish()` if no category provided.

### Dialog Windows and Sizing
All dialogs (`AddDishDialog`, `SettingsDialog`, `ExportDialog`, `ImageManagerDialog`) use **fixed window sizes** (`setFixedSize(...)`) to prevent cursor resizing and layout overlaps. `AddDishDialog` is locked at `520x700` to prevent optional nutrition fields from overlapping. The Save button must always read `"✓  Save Dish"`.

### Database Seeding and Self-Healing
On launch, the app copies its bundled SQLite database and all 194 seed images into the user's `%APPDATA%/MenuPlanner/data/` folder if it doesn't exist. If the folder exists but has an unseeded database (0 images), the app self-heals by forcing a re-seed.

## Compilation to Standalone .exe
To build the single-file executable, terminate any running instances of MenuPlanner and compile from `menu_planner/`:
```powershell
Stop-Process -Name "MenuPlanner" -Force -ErrorAction SilentlyContinue
cd c:\MenuPlanner\menu_planner
python -m PyInstaller build.spec --clean
```

## Tech stack
PyQt6, SQLite (WAL mode), openpyxl, python-pptx, Pillow, certifi

## Syncing Raw Images
To import new images and update database entries before compilation, run:
```powershell
python c:\Users\kasul\.gemini\antigravity-ide\scratch\sync_raw_images.py
```

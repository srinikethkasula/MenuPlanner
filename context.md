# context.md — MenuPlanner Project Context

## Business context
Built for **Chathradhari Caterers**, who run the **Oyster canteen**.
A planner fills in next week's menu (Mon–Fri), then exports:
- One PowerPoint file per day (slides: Good Morning → dishes → Closing)
- One Excel file for the full week

The app is meant to be a single-exe distribution — no server, no cloud, fully offline.

## Current state (as of 2026-06-05)

### What works
- Full planning grid (5 days × 26 slots) with 500ms debounce auto-save to SQLite
- 189 master dishes seeded from `dishes_data.py` + custom dish support
- Drag-and-drop from dish library to grid cells
- Click-to-select dish then click-a-cell to assign
- PPT export via `pptx_gen.py` — correct slide order and fill order
- Excel export via `xlsx_export.py`
- Live PPT slide preview panel (right side, PIL-rendered thumbnails)
- Image Manager dialog (assign images to dishes individually or bulk from folder)
- Settings dialog (company name, canteen name, team photo, company image for closing slide)
- Crash recovery flag — detects unclean exit and shows recovery notice on relaunch
- Week navigation (prev/next week arrows in planning grid)

### Recent changes (sessions June 2026)
1. **Two-Zone Path System:** Configured [config.py](file:///c:/MenuPlanner/menu_planner/config.py) to segregate read-only resources (`sys._MEIPASS` when frozen) from writable AppData (`%APPDATA%/MenuPlanner/data`).
2. **First-run Seeding and Self-Healing Seeder:** Seeds the SQLite database and all 194 dish images on launch. If the database file is blank or has 0 image references, the app self-heals by forcing a re-seed.
3. **Fixed Window Dialog Sizes:** Standardized all four dialogs (`AddDishDialog` is `520x700`, `SettingsDialog` is `520x420`, `ExportDialog` is `540x520`, `ImageManagerDialog` is `760x560`) to be fixed-size (non-resizable) to avoid visual clipping.
4. **Save Dish Button Refinement:** Enforced a clean, consistent `"✓  Save Dish"` button on the `AddDishDialog` and adjusted vertical grid padding to prevent overlaps.
5. **Raw Images Match and Sync:** Developed `sync_raw_images.py` to automatically match, standardise, copy, and map 194 raw images to the database prior to executable compilation.
6. **Brand Custom Assets:** Programmatically generated app icon and startup splash screen logo featuring a gold cove dome vector graphic.
7. **Multi-Dish Layout & Overlap Refinements:** Added support for multiple dishes per slot (generating separate slides per dish), removed Good Morning logo, and adjusted PPT title & section text box wrapping.
8. **Dynamic Slide Category Labeling & Dessert Category:** Added a first-class `"Dessert"` category in DB and UI, and implemented slot-and-category-based dynamic mapping in the PPT slide generator and live preview.

### Known issues / not yet done
- `ppt_preview.py` still uses old amber/gold PPT slide backgrounds — intentional (they match actual PPT slide design)
- No image displayed inside grid cells themselves (only in the dish library cards)

## Files that must NOT be modified
- `menu_planner/resources/*.png` — 1920×1080 slide backgrounds, do not resize/replace

## Data locations
- `%APPDATA%/MenuPlanner/data/menu_planner.db` — SQLite DB (active user writable)
- `%APPDATA%/MenuPlanner/data/dish_images/` — user-uploaded & seed dish images (194 total)
- `%APPDATA%/MenuPlanner/data/crash.flag` — crash detection flag
- `menu_planner/dist/MenuPlanner.exe` — single compiled executable containing database and seed images baked-in

## PPT slide order (per day)
Good Morning → Breakfast (MORN1/2/3) → Lunch (NON_VEG, SPL_VEG, etc.) → Salad → Soup → Dessert (SWEET) → Evening Snacks (EVEN) → Fruit Lunch (FRUIT_*) → Closing → Custom slides

## Dish category breakdown (190 dishes total)
- Lunch: 109
- Dessert: 27
- Fruits: 21
- Breakfast: 19
- Juice: 9
- Additionals: 3
- Salad: 2

---

## Testing & Verification
A complete testing suite for validating the compiled single-file executable, AppData persistence, size-locked dialog constraints, data syncing, and slide preview/exports is maintained in [testing_plan.md](file:///c:/MenuPlanner/testing_plan.md).

# walkthrough.md — MenuPlanner Codebase Walkthrough

## Project layout
```
C:\MenuPlanner\
  menu_planner\
    main.py              Entry point
    config.py            All constants — paths, slots, days, colours
    theme.py             Centralised theme tokens (dark/light) and system theme detection
    database.py          SQLite CRUD layer
    dishes_data.py       189 master dishes (name + nutrition)
    export\
      pptx_gen.py        PPT export — SOURCE OF TRUTH, do not modify
      pptx_export.py     Old broken PPT export — ignore
      xlsx_export.py     Excel export
    nutrition\
      fetcher.py         Open Food Facts API lookup
    resources\
      bg_good_morning.png   1920×1080 PPT slide background
      bg_dish_slide.png     1920×1080 PPT slide background
      bg_closing.png        1920×1080 PPT slide background
    ui\
      main_window.py     QMainWindow — wires everything together
      planning_grid.py   Centre panel — 5-day × 26-slot editing grid
      dish_dock.py       Left panel — 4-col card grid of dishes with filters
      ppt_preview.py     Right panel — live slide thumbnails
      dialogs.py         AddDishDialog, SettingsDialog, ImageManagerDialog, ExportDialog
    data\
      menu_planner.db    SQLite database (auto-created on first run)
      dish_images\       User-uploaded dish image files
  CLAUDE.md              Claude instructions
  context.md             Project context and current state
  walkthrough.md         This file
  testing_plan.md        Executable testing plan
```

---

## main.py
- Checks for `data/crash.flag` — if present, a previous session crashed.
- Writes `crash.flag` on start, deletes it on clean exit.
- Performs SQLite rolling DB backup (`backup_database()`).
- Seeds the SQLite database and all 194 seed images into AppData on first launch or if the database is unseeded/blank (`seed_database_on_first_run()`, `seed_images_on_first_run()`).
- Calls `db.init_db()` → builds schema, runs migrations.
- Shows `MainWindow` with a custom gold/slate splash screen logo.

---

## config.py
The single source of truth for path constants and slot definitions.
Key paths like `DB_PATH`, `IMAGES_DIR`, and `SEED_IMAGES` are segregated between read-only package resources (`sys._MEIPASS` when frozen) and writable user AppData (`%APPDATA%/MenuPlanner/data`).

```python
SLOTS = [
    # (slot_id, display_name, section, ppt_section, is_fixed)
    ("NON_VEG", "Non.Veg", "LUNCH", "Lunch", False),
    ...
    ("MORN1", "1 Morn. Snacks", "SNACKS", "Breakfast", True),  # is_fixed=True
    ...
]
```

`is_fixed=True` means that slot is the same every day (e.g. MORN1 is always Idli).
`SLOT_IDS`, `SLOT_DISPLAY`, `SLOT_SECTION`, `SLOT_PPT` are derived dicts for quick lookup.

---

## database.py
SQLite with WAL mode. Every write commits immediately — no buffering.

Key tables:
- `dishes` — id, name, nutrition fields, image_path, category, is_custom
- `weekly_plans` — id, week_start (Monday ISO date), week_end
- `slot_assignments` — plan_id + day + slot → dish_name (UNIQUE constraint)
- `app_settings` — key/value pairs (company name, team photo path, etc.)
- `custom_slides` — extra slides appended after the closing slide

Key functions:
- `seed_database_on_first_run()` → On launch, copies the template SQLite database from resources to the active user's `%APPDATA%/MenuPlanner/data/` folder if it doesn't exist. Self-heals by forcing a re-seed if the database file is blank (0 image references).
- `seed_images_on_first_run()` → Copies the 194 bundled seed dish photos into `%APPDATA%/MenuPlanner/data/dish_images/` without overwriting existing custom files.
- `init_db()` → creates schema + `_migrate_add_category()` + seeds default settings (if missing)
- `get_or_create_plan(week_start)` → returns plan_id, pre-populates all slots as ''
- `set_slot(plan_id, day, slot, dish_name)` → upsert; called on every cell edit
- `get_week_data(plan_id)` → returns `{day: {slot: dish_name}}`
- `get_day_data` is NOT in database.py — it lives in `planning_grid.py` as `PlanningGrid.get_day_data(day)`
- `_auto_category(name)` → keyword-based category assignment
- `_migrate_add_category(conn)` → adds `category` column if missing, auto-assigns

---

## theme.py
- Centralised theme tokens for both **Dark** and **Light** modes.
- `current()` returns the active theme dictionary (colors, borders, backgrounds).
- `detect_system()` checks the Windows registry (`Software\Microsoft\Windows\CurrentVersion\Themes\Personalize\AppsUseLightTheme`) to load dark or light mode based on the user's OS preference.

---

## ui/main_window.py
`MainWindow(QMainWindow)`:
- Creates a vertical layout: `HeaderBar` on top, then a `QSplitter` (horizontal)
- Splitter children: `DishDock` (left, fixed width) | `PlanningGrid` (centre, stretches) | `PPTPreview` (right, fixed)
- `APP_QSS` global stylesheet — dark theme, scrollbars, menus, tooltips
- Signal connections:
  - `dish_dock.dish_selected` → `grid.assign_dish_to_pending(dish)` (click-to-assign mode)
  - `grid.slot_updated` → refreshes preview after 600ms
  - `grid.week_changed` → refreshes preview after 300ms

`HeaderBar(QFrame)`:
- Brand name + subtitle on the left
- "+ Dish", "Export" (blue), "Settings" buttons on the right

---

## ui/planning_grid.py
`PlanningGrid(QWidget)`:
- A `QGridLayout` with day columns (Mon–Fri) and slot rows
- Each cell is a `GridCell(QLineEdit)` with drag-accept support
- 500ms debounce timer — `_on_cell_changed` → `db.set_slot()`
- `assign_dish_to_pending(dish)` — stores dish as "pending"; next cell click assigns it
- `get_day_data(day)` → returns `{slot_id: dish_name}` for one day
- `load_week(monday_date)` → loads from DB and fills all cells
- Signals: `slot_updated(day, slot, dish_name)`, `week_changed(week_start)`

Cell drag-accept: cells accept `text/plain` MIME data dropped from dish cards.

---

## ui/dish_dock.py
`DishDock(QWidget)` — fixed width left panel:
- Title bar with dish count badge
- Search `QLineEdit`
- 8 filter chips (All / Breakfast / Lunch / Salad / Fruits / Juice / Additionals / Custom)
- `DishGrid(QScrollArea)` — 4-column grid of `DishCard` widgets
- Selection label + "Add Custom Dish" button at bottom

`DishCard(QFrame)`:
- Fixed 82×100px
- Top area: thumbnail image (loaded with `QPixmap.scaled()`, `FastTransformation`, center-cropped) or 🍽 placeholder
- Bottom area: dish name (word-wrap, 8px font)
- `mousePressEvent` → emits `clicked(dish)` signal
- `mouseMoveEvent` → starts `QDrag` with `text/plain` MIME after 8px movement threshold
- `set_selected(bool)` → blue border + dark blue bg when selected

`DishGrid(QScrollArea)`:
- Holds a `QWidget` with `QGridLayout` (4 columns, 6px gap, 8px margins)
- `populate(dishes)` — clears and rebuilds all cards
- Tracks `_selected_card` and deselects previous on new click

Filter logic in `_apply_filter()`:
- "All" → no category filter
- "Custom" → `is_custom == True` filter
- Others → `category == filter_name`

---

## ui/ppt_preview.py
`PPTPreview(QWidget)` — right panel showing slide thumbnails:
- `RenderThread(QThread)` uses PIL to draw slide thumbnails at 640×360
- Loads `bg_good_morning.png`, `bg_dish_slide.png`, `bg_closing.png` from resources
- Renders text overlaid on backgrounds
- Converts PIL `Image` to `QImage` then `QPixmap` for display
- `update_data(day_data, dishes_db)` → re-renders on each grid edit

**Note:** The preview uses the amber/gold PPT slide backgrounds intentionally — those match the actual exported PPT.

---

## ui/dialogs.py
All dialogs are constrained to **fixed window sizes** (`setFixedSize(...)`) to prevent cursor resizing and layout distortion or overlapping fields.

`ExportDialog` (Fixed Size: `540x520`) — unified export hub:
- Day selection checkboxes (Mon–Fri + Select All)
- Format checkboxes (PPT + Excel)
- Folder picker
- Calls `export_pptx(week_data={day: day_data}, ...)` for each selected day
- Calls `export_xlsx(week_data=full_week_data, ...)`

`AddDishDialog` (Fixed Size: `520x700`):
- Name + Auto-Fetch (Open Food Facts API)
- Nutrition fields (Calories, Protein, Carbs, Fat, Fiber) arranged in a grid with vertical padding to prevent squeeze overlaps.
- Category dropdown (Breakfast / Lunch / Salad / Fruits / Juice / Additionals)
- Image path + browse button
- Save button labeled **`✓  Save Dish`**

`SettingsDialog` (Fixed Size: `520x420`):
- Company name, canteen name, welcome message
- Company image path (left side of closing slide)
- Team photo path (right side of closing slide)
- Save button labeled **`✓  Save Settings`**

`ImageManagerDialog` (Fixed Size: `760x560`):
- Table of all dishes with image path and ✓/✗ status (headers fit without horizontal scrollbars)
- Double-click a row → file picker to assign image
- "Assign from Folder" button → bulk matches `dish_name.ext` files

---

## export/pptx_gen.py
`export_pptx(week_data, day, week_start, dishes_db, output_path, ...)`:
- `week_data` must be `{day_name: {slot_id: dish_names_str}}`
- Slide order: Good Morning → Breakfast → Lunch sections → Salad → Soup → Dessert → Evening Snacks → Fruit Lunch → Closing → Custom slides
- **Multi-Dish Handling**: Splits the slot string by `+`. If a single slot contains multiple dishes (e.g. `Chicken Sukha + Mutton Kolhapuri`), it automatically appends a separate slide for each dish in that slot under its respective section.
- **Overlap Refinements**: Category names (`TextBox 27`) are set to `54 pt` and company names (`TextBox 14`) are set to `40 pt` with word-wrapping disabled to ensure they stay on a single line.
- **Good Morning Slide**: Omit/delete the logo shape (`Freeform 12`) to keep the first slide clean.

---

## Data flow summary

```
User types in GridCell (or drags DishCard, or clicks card then clicks cell)
  → If text already in cell, appends dish separated by " + "
  → 500ms debounce
  → db.set_slot(plan_id, day, slot, value)
  → slot_updated signal
  → MainWindow._refresh_preview() after 600ms
  → PPTPreview.update_data(day_data, dishes_db)
  → Splits slot text by "+" into individual dishes
  → RenderThread renders separate PIL thumbnails for each dish
  → QListWidget updated with new thumbnails

Export button
  → ExportDialog
  → Splits slot text by "+" into individual dishes
  → export_pptx(week_data={day: day_data}, ...) per day (creates separate slides per dish)
  → export_xlsx(week_data=full_week, ...) (writes combined "Dish A + Dish B" text)
```

---

## Things to work on next (suggested)
- Restyle `planning_grid.py` cells to match new dark theme
- Add ability to re-assign category from Image Manager or a right-click context menu on dish cards
- Show dish image thumbnail inside grid cells when a dish with an image is assigned
- Consider making dock width resizable via splitter instead of fixed

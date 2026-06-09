# MenuPlanner 🍽️

A premium desktop application designed for **Chathradhari Caterers** to plan, structure, and export weekly menus for the **Oyster Canteen**. Built using Python and PyQt6, the application replaces manual planning with a streamlined drag-and-drop workflow, real-time PowerPoint slide previews, and direct exports.

---

## ✨ Key Features

* **📅 Interactive Planning Grid**: A 5-day (Monday to Friday) by 26-slot weekly menu grid with a 500ms auto-save debounce mechanism.
* **🍽️ Comprehensive Dish Library**: Comes pre-seeded with 194 master dishes (veggies, non-veggies, snacks, and sweets) featuring autocomplete search and filter chips.
* **🔄 Live PowerPoint Slide Preview**: A side panel displaying live slides rendered using the actual PowerPoint template layouts and matching dish photos.
* **📤 Multi-Format Exports**: 
  * **PowerPoint (`.pptx`)**: Generates individual slide decks per day (cloned from the master template) with auto-formatted nutrition cards.
  * **Excel (`.xlsx`)**: Exports the entire weekly planning grid into a cleanly styled spreadsheet complete with merged headings and borders.
* **🏷️ Dynamic Slide Category Resolution**: Smart categorization rules automatically resolve slide sections:
  * Grid assignments in the **Fruit** section map to `"Fruit Lunch"`.
  * Dishes categorized as sweets map to `"Dessert"`, regardless of grid position.
  * Additional eggs/morning snacks map to `"Breakfast"`.
* **🛠️ Database Self-Healing & Crash Recovery**: Bundled SQLite seeder extracts and regenerates assets on the first launch or during unclean shutdowns, preventing data loss.

---

## 🚀 Tech Stack

* **GUI Framework**: PyQt6 (Windowed, Dark Mode stylesheet)
* **Office Integration**: `python-pptx`, `openpyxl`
* **Image Processing**: Pillow (PIL)
* **Database**: SQLite3 (WAL mode enabled)
* **Build Tool**: PyInstaller (Standalone single-executable build spec)

---

## 📂 Project Structure

```
MenuPlanner/
├── menu_planner/             # Source code root
│   ├── data/                 # SQLite databases, uploads, and image library
│   ├── export/               # PowerPoint and Excel exporters
│   ├── nutrition/            # Open Food Facts API fetcher module
│   ├── resources/            # Slide templates, backgrounds, and application icon
│   ├── ui/                   # PyQt6 views, dialogs, widgets, and preview panels
│   ├── build.spec            # PyInstaller packaging configuration
│   ├── config.py             # App constants, slots, and color palettes
│   ├── database.py           # Database models, migrations, and seeder
│   └── main.py               # Main entry point (and splash screen)
├── scratch_output/           # Test scripts and mock assets
├── scripts/                  # Data sync and image paths migration utilities
└── README.md                 # Project documentation
```

---

## 💻 Running Locally

### 1. Prerequisites
Make sure you have Python 3.10+ installed.

### 2. Install Dependencies
Install all required packages:
```bash
pip install PyQt6 python-pptx openpyxl Pillow requests certifi
```

### 3. Run the Application
Execute the entry point:
```bash
python menu_planner/main.py
```

---

## 📦 Building Standalone Executable (.exe)

To bundle the application into a portable single-file executable, terminate any running instances of MenuPlanner and compile from the `menu_planner/` directory using PyInstaller:

```powershell
# Terminate existing process
Stop-Process -Name "MenuPlanner" -Force -ErrorAction SilentlyContinue

# Build binary
cd menu_planner
python -m PyInstaller build.spec --clean
```
The compiled binary will be generated under `menu_planner/dist/MenuPlanner.exe`.

---


"""
config.py — App-wide constants, paths, slot definitions.
"""
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
import sys, os

def _is_frozen() -> bool:
    return getattr(sys, 'frozen', False)

def _resource(rel: str) -> Path:
    """Read-only bundled resource. Uses sys._MEIPASS when frozen."""
    if _is_frozen():
        return Path(sys._MEIPASS) / rel
    return Path(__file__).parent / rel

def _app_data() -> Path:
    """Permanent user-writable folder: %APPDATA%/MenuPlanner"""
    base = Path(os.environ.get("APPDATA", Path.home())) / "MenuPlanner"
    base.mkdir(parents=True, exist_ok=True)
    return base

RESOURCES_DIR  = _resource("resources")
SEED_IMAGES    = _resource("_seed_images")   # bundled originals

APP_DATA_DIR   = _app_data()
DATA_DIR       = APP_DATA_DIR / "data"
DB_PATH        = DATA_DIR / "menu_planner.db"
IMAGES_DIR     = DATA_DIR / "dish_images"
EXPORT_DIR     = APP_DATA_DIR / "export"

# Ensure dirs exist at import time
DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# ── Slide backgrounds ─────────────────────────────────────────────────────────
BG_GOOD_MORNING = RESOURCES_DIR / "bg_good_morning.png"
BG_DISH_SLIDE   = RESOURCES_DIR / "bg_dish_slide.png"
BG_CLOSING      = RESOURCES_DIR / "bg_closing.png"

# ── App info ──────────────────────────────────────────────────────────────────
APP_NAME    = "Menu Planner"
APP_VERSION = "1.0.0"
COMPANY_NAME = "Chathradhari Caterers"

# ── Days ──────────────────────────────────────────────────────────────────────
DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
DAY_LABELS = {
    "MONDAY":    "Monday",
    "TUESDAY":   "Tuesday",
    "WEDNESDAY": "Wednesday",
    "THURSDAY":  "Thursday",
    "FRIDAY":    "Friday",
}

# ── Slot definitions ──────────────────────────────────────────────────────────
# (slot_id, display_name, section, ppt_section, is_fixed)
# is_fixed=True means dish is same every day (e.g. MORN1 = always Idli)
SLOTS = [
    # LUNCH
    ("NON_VEG",      "NON.VEG",              "LUNCH",      "Lunch",           False),
    ("SPL_VEG",      "SPL.VEG.",             "LUNCH",      "Lunch",           False),
    ("COM_VEG",      "COM.VEG.",             "LUNCH",      "Lunch",           False),
    ("RICE",         "RICE",                 "LUNCH",      "Lunch",           False),
    ("ROTI",         "ROTI / BREAD",         "LUNCH",      "Lunch",           False),
    ("DAL",          "DAL",                  "LUNCH",      "Lunch",           False),
    ("SWEET",        "SWEET",                "LUNCH",      "Dessert",         False),
    ("SALAD",        "SALAD",                "LUNCH",      "Salad",           False),
    ("CURD",         "CURD",                 "LUNCH",      "Lunch",           False),
    ("PAPAD",        "PAPAD",                "LUNCH",      "Lunch",           False),
    ("PICKLE",       "PICKLE",               "LUNCH",      "Lunch",           False),
    ("SOUP",         "SOUP",                 "LUNCH",      "Soup",            False),
    # SNACKS
    ("MORN1",        "1 MORN. SNACKS",       "SNACKS",     "Breakfast",       True),
    ("MORN2",        "2 MORN. SNACKS",       "SNACKS",     "Breakfast",       False),
    ("MORN3",        "3 MORN.SNACKS",        "SNACKS",     "Breakfast",       False),
    ("EVEN",         "EVEN.SNACKS",          "SNACKS",     "Evening Snacks",  False),
    # FRUIT / HEALTHY DIET LUNCH
    ("FRUIT_BAN",    "Elaichi Banana",       "FRUIT",      "Fruit Lunch",     True),
    ("FRUIT_DAILY",  "Daily Fruit",          "FRUIT",      "Fruit Lunch",     False),
    ("FRUIT_CUT",    "Cut Fruits",           "FRUIT",      "Fruit Lunch",     True),
    ("FRUIT_BOIL",   "Boiled Item",          "FRUIT",      "Lunch",           False),
    ("FRUIT_DRINK",  "Drink",                "FRUIT",      "Fruit Lunch",     False),
    ("FRUIT_DRY",    "Dry Fruits",           "FRUIT",      "Fruit Lunch",     False),
    ("FRUIT_CURD",   "Curd / Soup",          "FRUIT",      "Lunch",           True),
    # ADDITIONAL
    ("JUICE",        "JUICE",                "ADDITIONAL", "Juice",           False),
    ("EGG",          "EGG ",                 "ADDITIONAL", "Breakfast",       False),
    ("CORN_FLAKES",  "",                     "ADDITIONAL", "Breakfast",       True),
]

SLOT_IDS     = [s[0] for s in SLOTS]
SLOT_DISPLAY = {s[0]: s[1] for s in SLOTS}
SLOT_SECTION = {s[0]: s[2] for s in SLOTS}
SLOT_PPT     = {s[0]: s[3] for s in SLOTS}

SECTIONS = ["LUNCH", "SNACKS", "FRUIT", "ADDITIONAL"]
SECTION_LABELS = {
    "LUNCH":      "Lunch",
    "SNACKS":     "Morning & Evening Snacks",
    "FRUIT":      "Fruit / Healthy (Diet) Lunch",
    "ADDITIONAL": "Additional",
}

# ── PPT section badge colors ───────────────────────────────────────────────────
PPT_SECTION_COLORS = {
    "Breakfast":      "#C9941A",   # warm gold
    "Juice":          "#0ea5e9",   # sky blue
    "Lunch":          "#2E7D32",   # deep green
    "Fruit Lunch":    "#E64A19",   # coral orange
    "Salad":          "#388E3C",   # fresh green
    "Soup":           "#F57F17",   # amber
    "Dessert":        "#AD1457",   # rose
    "Evening Snacks": "#00695C",   # teal
}

# ── Category colors (used in dish cards, grid cells, autocomplete) ────────────
CATEGORY_COLORS = {
    "Breakfast":   "#22c55e",   # green  (veg)
    "Lunch":       "#ef4444",   # red    (non-veg / main course)
    "Snacks":      "#f59e0b",   # amber
    "Juice":       "#0ea5e9",   # sky    (beverage)
    "Soup":        "#f57f17",   # deep amber
    "Additionals": "#a78bfa",   # violet
    "Fruit Lunch": "#84cc16",   # lime   (veg / fresh)
    "Dessert":     "#AD1457",   # rose
    "Custom":      "#6b7280",   # gray
}

# ── Excel styling ─────────────────────────────────────────────────────────────
EXCEL_HEADER_FILL   = "3E2007"   # dark brown (dates row)
EXCEL_TITLE_FILL    = "7A7A7A"   # grey (title row)
EXCEL_SECTION_FILLS = {
    "LUNCH":      "D0D0D0",
    "SNACKS":     "E8E8E8",
    "FRUIT":      "D8D8D8",
    "ADDITIONAL": "C8C8C8",
}
EXCEL_FONT_HEADER   = "FFFFFF"
EXCEL_FONT_DARK     = "1A1A1A"

"""
database.py — SQLite manager. Every write is immediate. No data loss on crash.
"""
import sqlite3
import json
import shutil
from datetime import datetime, date, timedelta
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

from config import DB_PATH, DAYS, SLOT_IDS, IMAGES_DIR, SEED_IMAGES
from dishes_data import MASTER_DISHES


# ── Schema ─────────────────────────────────────────────────────────────────────
SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS dishes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    UNIQUE NOT NULL,
    calories    TEXT    DEFAULT '',
    protein     TEXT    DEFAULT '',
    carbs       TEXT    DEFAULT '',
    fat         TEXT    DEFAULT '',
    fiber       TEXT    DEFAULT '',
    image_path  TEXT    DEFAULT '',
    category    TEXT    DEFAULT '',
    is_veg      INTEGER DEFAULT 1,
    is_custom   INTEGER DEFAULT 0,
    created_at  TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS weekly_plans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start  TEXT    UNIQUE NOT NULL,
    week_end    TEXT    NOT NULL,
    created_at  TEXT    DEFAULT (datetime('now','localtime')),
    updated_at  TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS slot_assignments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id     INTEGER NOT NULL REFERENCES weekly_plans(id) ON DELETE CASCADE,
    day         TEXT    NOT NULL,
    slot        TEXT    NOT NULL,
    dish_name   TEXT    NOT NULL DEFAULT '',
    dish_id     INTEGER REFERENCES dishes(id) ON DELETE SET NULL,
    updated_at  TEXT    DEFAULT (datetime('now','localtime')),
    UNIQUE(plan_id, day, slot)
);

CREATE TABLE IF NOT EXISTS custom_slides (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id     INTEGER NOT NULL REFERENCES weekly_plans(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL DEFAULT 999,
    image_path  TEXT    NOT NULL DEFAULT '',
    caption     TEXT    DEFAULT '',
    created_at  TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS app_settings (
    key         TEXT    PRIMARY KEY,
    value       TEXT    NOT NULL DEFAULT ''
);
"""

DEFAULT_SETTINGS = {
    "company_name":   "Chathradhari Caterers",
    "canteen_name":   "Oyster",
    "team_photo":     "",
    "company_image":  "",
    "welcome_text":   "Welcome to Oyster\nWhere we start your day with a smile and a delicious meal.",
    "last_week":      "",
    "theme":          "dark",
}


# ── Connection ─────────────────────────────────────────────────────────────────
@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Init ───────────────────────────────────────────────────────────────────────
def seed_database_on_first_run():
    """
    On first run: copy bundled seed database to DB_PATH if DB_PATH does not exist.
    Self-heals if the database exists but is unseeded (0 image references).
    """
    import sys
    import logging
    import sqlite3
    
    should_seed = not DB_PATH.exists()
    if DB_PATH.exists():
        try:
            # If the database exists but has 0 dishes with images, it is unseeded.
            conn = sqlite3.connect(DB_PATH)
            img_count = conn.execute("SELECT COUNT(*) FROM dishes WHERE image_path != ''").fetchone()[0]
            conn.close()
            if img_count == 0:
                logging.info("Existing AppData database is empty/unseeded (0 images). Re-seeding database.")
                should_seed = True
        except Exception as e:
            logging.warning(f"Existing AppData database check failed ({e}). Forcing re-seed.")
            should_seed = True
            
    if not should_seed:
        return
        
    # Find bundled database
    if getattr(sys, 'frozen', False):
        src_db = Path(sys._MEIPASS) / "resources" / "menu_planner.db"
    else:
        # Dev mode
        src_db = Path(__file__).parent / "data" / "menu_planner.db"
        
    if src_db.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src_db, DB_PATH)
            logging.info(f"First-run: seeded database to {DB_PATH}")
        except Exception as e:
            logging.error(f"Failed to seed database: {e}")
    else:
        logging.warning("Seed database not found, will initialize from scratch.")


def seed_images_on_first_run():
    """
    On first run: copy bundled _seed_images/* → IMAGES_DIR.
    Skips individual files that already exist (safe to call every run).
    """
    import logging
    if not SEED_IMAGES.exists():
        return  # running in dev mode, no seed dir
    
    copied = 0
    for src in SEED_IMAGES.iterdir():
        if src.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}:
            dest = IMAGES_DIR / src.name
            if not dest.exists():
                try:
                    shutil.copy2(src, dest)
                    copied += 1
                except Exception as e:
                    logging.error(f"Failed to copy seed image {src.name}: {e}")
    if copied:
        logging.info(f"First-run: seeded {copied} dish images to {IMAGES_DIR}")


def _migrate_absolute_image_paths(conn):
    """One-time: strip absolute prefixes from image_path, keep only filename."""
    rows = conn.execute(
        "SELECT name, image_path FROM dishes WHERE image_path != '' AND image_path IS NOT NULL"
    ).fetchall()
    for row in rows:
        name = row[0]
        path_str = row[1]
        if path_str:
            p = Path(path_str)
            if p.is_absolute():
                conn.execute(
                    "UPDATE dishes SET image_path=? WHERE name=?",
                    (p.name, name)
                )


def init_db():
    """Create schema, seed dishes, then apply migrations."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _seed_dishes(conn)
        _seed_settings(conn)
        _migrate_absolute_image_paths(conn)
        _migrate_add_category(conn)
        _migrate_add_is_veg(conn)
        _migrate_standard_dish_categories(conn)
        _migrate_dessert_category(conn)


def _auto_category(name: str) -> str:
    n = name.lower().strip()
    
    # Dessert/Sweets
    sweet_kws = ["halwa", "ladoo", "laddu", "barfi", "jamun", "kulfi", "kheer", "payasam", 
                 "churma", "sweet", "dessert", "cham cham", "balushahi", "rasgulla", 
                 "soan papdi", "mysore pak", "shrikhand", "amrakhand"]
    if any(k in n for k in sweet_kws):
        if not any(ex in n for ex in ["soup", "fish", "curry", "masala", "ghassi", "fry", "chicken", "mutton"]):
            return "Dessert"
        
    # 1. Juice
    if any(k in n for k in ["juice", "panna", "lemonade", "chass", "chaas", "lassi", "solkadhi", "milkshake", "shake", "thandai", "sharbat"]):
        return "Juice"
    if n == "kokum kadhi":
        return "Juice"
        
    # 2. Soup
    if any(k in n for k in ["soup", "shorba"]):
        return "Soup"
        
    # 3. Additionals
    if any(k in n for k in ["boiled egg", "omelet", "corn flakes"]):
        return "Additionals"
    if any(k in n for k in ["boiled chana", "boiled veg", "boiled rajma", "boiled sengdana", "boiled mix", "boiled sprouts"]):
        return "Additionals"
    if any(k in n for k in ["plain curd", "roasted papad", "mango pickle", "curd", "papad", "pickle"]):
        # Exclude curry/sabji that contains papad/pickle/curd in name but are main dishes, e.g. "Dahi Kadhi", "Dahi Baigan", "Dahi Vada"
        if not any(k in n for k in ["kadhi", "baigan", "vada", "curry", "sabji"]):
            return "Additionals"
    if n in ["makhana", "masala milk"]:
        return "Additionals"
        
    # 4. Fruit Lunch
    fruits = ["banana", "grapes", "chickoo", "pear", "gauva", "malta", "peach", "plum", "papaya", "mango", "watermelon", "melon", "kiwi", "orange", "pomegranate", "fig", "anjeer", "custard apple", "cut fruits", "cut fruit", "daily fruit", "fruits blend"]
    has_fruit = any(f in n for f in fruits) or (("apple" in n) and ("pineapple" not in n))
    if has_fruit:
        # Exclude sweets/dishes made with fruits
        if not any(k in n for k in ["sheera", "halwa", "barfi", "kheer", "payasam", "lassi", "milkshake", "shake", "juice", "sabji", "curry", "salad", "dolly", "soup"]):
            return "Fruit Lunch"
    if n in ["mix dry fruits", "dry fruits"]:
        return "Fruit Lunch"
        
    # 5. Breakfast
    if any(k in n for k in ["idli", "dosa", "poha", "upma", "amboli", "dhokla", "chillar", "chilla", "khichdi"]):
        return "Breakfast"
    if "paratha" in n:
        return "Breakfast"
    if "sheera" in n:
        return "Breakfast"
    if n == "tomato omlette":
        return "Breakfast"
        
    # 6. Snacks
    if any(k in n for k in ["samosa", "bread pakoda", "bhajiya", "chivda", "sev bundi"]):
        return "Snacks"
    if any(k in n for k in ["vada", "dabeli", "pav bhaji", "misal pav", "usal pav", "khandvi", "muthiya", "chat", "karanji"]):
        return "Snacks"
    if any(k in n for k in ["momos", "bhel"]):
        return "Snacks"
    if "sandwich" in n:
        return "Snacks"
    if "uttappa" in n:
        return "Snacks"
        
    # 7. Lunch (Default)
    return "Lunch"


def _migrate_standard_dish_categories(conn):
    """Update all standard seeded dishes (is_custom = 0) with the refined categorization."""
    rows = conn.execute("SELECT name FROM dishes WHERE is_custom = 0").fetchall()
    for row in rows:
        name = row[0]
        conn.execute(
            "UPDATE dishes SET category=? WHERE name=? AND is_custom=0",
            (_auto_category(name), name)
        )


def _migrate_dessert_category(conn):
    """Ensure any dishes matching sweet keywords are categorized as Dessert, while excluding non-desserts."""
    rows = conn.execute("SELECT name, category FROM dishes").fetchall()
    sweet_kws = ["halwa", "ladoo", "laddu", "barfi", "jamun", "kulfi", "kheer", "payasam", 
                 "churma", "sweet", "dessert", "cham cham", "balushahi", "rasgulla", 
                 "soan papdi", "mysore pak", "shrikhand", "amrakhand"]
    for row in rows:
        name, category = row[0], row[1]
        n = name.lower()
        if any(k in n for k in sweet_kws):
            if not any(ex in n for ex in ["soup", "fish", "curry", "masala", "ghassi", "fry", "chicken", "mutton"]):
                if category != "Dessert":
                    conn.execute(
                        "UPDATE dishes SET category='Dessert' WHERE name=?",
                        (name,)
                    )
            else:
                if category == "Dessert":
                    conn.execute(
                        "UPDATE dishes SET category=? WHERE name=?",
                        (_auto_category(name), name)
                    )


_NON_VEG_KW = [
    "chicken", "mutton", "fish", "prawn", "egg", "meat", "keema", "kheema",
    "boneless", "mince", "liver", "lamb", "beef", "pork", "crab",
    "gosht", "surmai", "ravas", "murg", "kombdi", "laal mass",
]

def _auto_is_veg(name: str) -> int:
    n = name.lower()
    return 0 if any(k in n for k in _NON_VEG_KW) else 1


def _migrate_add_is_veg(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(dishes)").fetchall()]
    if "is_veg" not in cols:
        conn.execute("ALTER TABLE dishes ADD COLUMN is_veg INTEGER DEFAULT 1")
    # Auto-detect non-veg from name keywords for dishes not yet set
    rows = conn.execute("SELECT name FROM dishes WHERE is_veg IS NULL OR is_veg = 1").fetchall()
    for row in rows:
        if _auto_is_veg(row[0]) == 0:
            conn.execute("UPDATE dishes SET is_veg=0 WHERE name=?", (row[0],))


def _migrate_add_category(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(dishes)").fetchall()]
    if "category" not in cols:
        conn.execute("ALTER TABLE dishes ADD COLUMN category TEXT DEFAULT ''")
    rows = conn.execute("SELECT name FROM dishes WHERE category = '' OR category IS NULL").fetchall()
    for row in rows:
        conn.execute("UPDATE dishes SET category=? WHERE name=?", (_auto_category(row[0]), row[0]))


def _seed_dishes(conn):
    conn.executemany(
        """INSERT OR IGNORE INTO dishes (name, calories, protein, carbs, fat, fiber)
           VALUES (:name, :calories, :protein, :carbs, :fat, :fiber)""",
        MASTER_DISHES
    )


def _seed_settings(conn):
    for key, val in DEFAULT_SETTINGS.items():
        conn.execute(
            "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)",
            (key, val)
        )


# ── Settings ───────────────────────────────────────────────────────────────────
def get_setting(key: str) -> str:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else DEFAULT_SETTINGS.get(key, "")


def set_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
            (key, value)
        )


# ── Dishes ─────────────────────────────────────────────────────────────────────
def get_all_dishes() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM dishes ORDER BY is_custom, name"
        ).fetchall()
        return [dict(r) for r in rows]


def get_dish_by_name(name: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM dishes WHERE name=? COLLATE NOCASE", (name,)
        ).fetchone()
        return dict(row) if row else None


def copy_image_to_library(dish_name: str, src_path: str) -> str:
    if not src_path:
        return ""
    src = Path(src_path)
    if not src.exists():
        return src_path
    
    # Generate safe name
    safe_name = dish_name.replace("/", "-").replace("\\", "-").replace(":", "-")
    dest = IMAGES_DIR / f"{safe_name}.jpg"
    
    try:
        from PIL import Image
        ext = src.suffix.lower()
        if ext in (".webp", ".bmp", ".png"):
            # Convert to JPEG for compatibility
            with Image.open(src) as img:
                img.convert("RGB").save(dest, "JPEG", quality=92)
        else:
            shutil.copy2(src, dest)
        return dest.name
    except Exception:
        # If copying fails, just return original path
        return src_path


def copy_settings_image(src_path: str) -> str:
    """
    Copy a chosen company/team image to IMAGES_DIR, return only its filename.
    If it's already a relative path or doesn't exist, return it as-is.
    """
    if not src_path:
        return ""
    src = Path(src_path)
    if not src.exists():
        return src_path
    
    # Check if it is already in resources or IMAGES_DIR
    from config import RESOURCES_DIR
    if src.parent == IMAGES_DIR or src.parent == RESOURCES_DIR:
        return src.name
        
    dest = IMAGES_DIR / src.name
    try:
        shutil.copy2(src, dest)
        return dest.name
    except Exception as e:
        import logging
        logging.error(f"Failed to copy settings image {src_path}: {e}")
        return src_path


def resolve_image_path(db_path: str) -> str:
    """
    Given a stored path (may be absolute old-style OR just a filename),
    return the absolute path to the actual image file on this machine.
    Priority: IMAGES_DIR (writable) > RESOURCES_DIR (read-only defaults) > absolute path (legacy dev)
    """
    if not db_path:
        return ""
    
    candidate = IMAGES_DIR / Path(db_path).name
    if candidate.exists():
        return str(candidate)
        
    from config import RESOURCES_DIR
    res_candidate = RESOURCES_DIR / Path(db_path).name
    if res_candidate.exists():
        return str(res_candidate)
        
    p = Path(db_path)
    if p.is_absolute() and p.exists():
        return str(p)
        
    return ""


def add_dish(name: str, calories="", protein="", carbs="", fat="", fiber="",
             image_path="", category="", is_veg: int = 1) -> int:
    if not category:
        category = _auto_category(name)
    if image_path:
        image_path = copy_image_to_library(name, image_path)
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO dishes
               (name, calories, protein, carbs, fat, fiber, image_path, category, is_veg, is_custom)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (name, calories, protein, carbs, fat, fiber, image_path, category, is_veg)
        )
        return cur.lastrowid


def update_dish(dish_name: str, name: str = None, calories: str = None,
                protein: str = None, carbs: str = None, fat: str = None,
                fiber: str = None, image_path: str = None, category: str = None,
                is_veg: int = None) -> bool:
    """Update any fields of an existing dish. Returns True on success."""
    updates: dict = {}
    new_name = name.strip() if name else None
    if new_name and new_name != dish_name:
        updates["name"] = new_name
    if calories   is not None: updates["calories"]    = calories
    if protein    is not None: updates["protein"]     = protein
    if carbs      is not None: updates["carbs"]       = carbs
    if fat        is not None: updates["fat"]         = fat
    if fiber      is not None: updates["fiber"]       = fiber
    if image_path is not None:
        existing = get_dish_by_name(dish_name)
        if existing and existing.get("image_path") != image_path:
            target_name = name if name else dish_name
            image_path = copy_image_to_library(target_name, image_path)
        updates["image_path"]  = image_path
    if category   is not None: updates["category"]    = category
    if is_veg     is not None: updates["is_veg"]      = is_veg
    if not updates:
        return True
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [dish_name]
    with get_conn() as conn:
        conn.execute(
            f"UPDATE dishes SET {set_clause} WHERE name=? COLLATE NOCASE", values
        )
        if "name" in updates:
            conn.execute(
                "UPDATE slot_assignments SET dish_name=? WHERE dish_name=? COLLATE NOCASE",
                (updates["name"], dish_name),
            )
    return True


def delete_dish(dish_name: str):
    """Delete a dish and clear any slot assignments that referenced it."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE slot_assignments SET dish_name='', dish_id=NULL "
            "WHERE dish_name=? COLLATE NOCASE",
            (dish_name,),
        )
        conn.execute("DELETE FROM dishes WHERE name=? COLLATE NOCASE", (dish_name,))


def get_dish_usage(dish_name: str) -> list[dict]:
    """Return [{week_start, day, slot}] for every slot currently using this dish."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT wp.week_start, sa.day, sa.slot
               FROM slot_assignments sa
               JOIN weekly_plans wp ON sa.plan_id = wp.id
               WHERE sa.dish_name=? COLLATE NOCASE AND sa.dish_name != ''
               ORDER BY wp.week_start DESC""",
            (dish_name,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_dish_category(dish_name: str, category: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE dishes SET category=? WHERE name=? COLLATE NOCASE",
            (category, dish_name)
        )


def update_dish_image(dish_name: str, image_path: str):
    if image_path:
        image_path = copy_image_to_library(dish_name, image_path)
    with get_conn() as conn:
        conn.execute(
            "UPDATE dishes SET image_path=? WHERE name=? COLLATE NOCASE",
            (image_path, dish_name)
        )


def search_dishes(query: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM dishes WHERE name LIKE ? ORDER BY is_custom, name",
            (f"%{query}%",)
        ).fetchall()
        return [dict(r) for r in rows]


# ── Weekly Plans ───────────────────────────────────────────────────────────────
def get_or_create_plan(week_start: date) -> int:
    """Get existing plan or create one for the given Monday."""
    week_end = week_start + timedelta(days=4)
    start_str = week_start.isoformat()
    end_str   = week_end.isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM weekly_plans WHERE week_start=?", (start_str,)
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO weekly_plans (week_start, week_end) VALUES (?, ?)",
            (start_str, end_str)
        )
        plan_id = cur.lastrowid
        # Pre-populate all slots with empty strings
        for day in DAYS:
            for slot in SLOT_IDS:
                conn.execute(
                    """INSERT OR IGNORE INTO slot_assignments
                       (plan_id, day, slot, dish_name)
                       VALUES (?, ?, ?, '')""",
                    (plan_id, day, slot)
                )
        return plan_id


def get_week_data(plan_id: int) -> dict:
    """Return {day: {slot: dish_name}} for the plan."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT day, slot, dish_name FROM slot_assignments WHERE plan_id=?",
            (plan_id,)
        ).fetchall()
    result = {day: {slot: "" for slot in SLOT_IDS} for day in DAYS}
    for r in rows:
        if r["day"] in result and r["slot"] in result[r["day"]]:
            result[r["day"]][r["slot"]] = r["dish_name"] or ""
    return result


def set_slot(plan_id: int, day: str, slot: str, dish_name: str):
    """Assign a dish to a slot. Called on every cell change."""
    dish_id = None
    if dish_name:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM dishes WHERE name=? COLLATE NOCASE", (dish_name,)
            ).fetchone()
            if row:
                dish_id = row["id"]
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO slot_assignments (plan_id, day, slot, dish_name, dish_id, updated_at)
               VALUES (?, ?, ?, ?, ?, datetime('now','localtime'))
               ON CONFLICT(plan_id, day, slot) DO UPDATE SET
                   dish_name=excluded.dish_name,
                   dish_id=excluded.dish_id,
                   updated_at=excluded.updated_at""",
            (plan_id, day, slot, dish_name, dish_id)
        )
        conn.execute(
            "UPDATE weekly_plans SET updated_at=datetime('now','localtime') WHERE id=?",
            (plan_id,)
        )


def get_all_plans() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM weekly_plans ORDER BY week_start DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# ── Custom Slides ──────────────────────────────────────────────────────────────
def get_custom_slides(plan_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM custom_slides WHERE plan_id=? ORDER BY position",
            (plan_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def add_custom_slide(plan_id: int, image_path: str, caption: str = "",
                     position: int = 999) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO custom_slides (plan_id, image_path, caption, position)
               VALUES (?, ?, ?, ?)""",
            (plan_id, image_path, caption, position)
        )
        return cur.lastrowid


def delete_custom_slide(slide_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM custom_slides WHERE id=?", (slide_id,))


# ── Helpers ────────────────────────────────────────────────────────────────────
def monday_of_week(d: date = None) -> date:
    if d is None:
        d = date.today()
    return d - timedelta(days=d.weekday())


def week_dates(week_start: date) -> dict:
    """Return {DAY_NAME: date} for Mon-Fri."""
    return {
        day: week_start + timedelta(days=i)
        for i, day in enumerate(DAYS)
    }

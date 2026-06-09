"""
Run ONCE before packaging to strip absolute paths from the DB.
python scripts/migrate_image_paths.py
"""
import sqlite3
from pathlib import Path

DB = Path("menu_planner/data/menu_planner.db")
if not DB.exists():
    print(f"Error: DB not found at {DB.absolute()}")
    exit(1)

conn = sqlite3.connect(DB)

# 1. Migrate dish image paths
rows = conn.execute("SELECT name, image_path FROM dishes WHERE image_path != '' AND image_path IS NOT NULL").fetchall()
dishes_migrated = 0
for name, path in rows:
    p = Path(path)
    if p.is_absolute():
        conn.execute("UPDATE dishes SET image_path=? WHERE name=?", (p.name, name))
        print(f"  fixed dish: {name} -> {p.name}")
        dishes_migrated += 1

# 2. Migrate settings image paths (mapping root files to resources name)
rows = conn.execute("SELECT key, value FROM app_settings WHERE key IN ('company_image', 'team_photo')").fetchall()
settings_migrated = 0
for key, value in rows:
    if value:
        p = Path(value)
        if p.name == "teamlogo.jpg":
            new_val = "company_image.jpg"
        elif p.name == "teamgrpicturtr logo.jpg":
            new_val = "team_photo.jpg"
        else:
            new_val = p.name
        conn.execute("UPDATE app_settings SET value=? WHERE key=?", (new_val, key))
        print(f"  fixed setting: {key} -> {new_val}")
        settings_migrated += 1

conn.commit()
conn.close()
print(f"Done. Migrated {dishes_migrated} dishes and {settings_migrated} settings.")

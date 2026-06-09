"""
import_dish_images.py — Bulk import dish images from a folder into MenuPlanner.

Usage:
    python scripts/import_dish_images.py
    python scripts/import_dish_images.py C:/path/to/your/images

Rules:
    - Filename (without extension) is matched to dish name (fuzzy)
    - Supported formats: .jpg .jpeg .png .webp .bmp
    - Images are COPIED to data/dish_images/ (originals untouched)
    - DB image_path is updated for every matched dish
    - Already-imported dishes are skipped unless --force is passed
"""
import sys
import shutil
import sqlite3
from pathlib import Path
from difflib import get_close_matches

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# ── Resolve paths ──────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
ROOT_DIR    = SCRIPT_DIR.parent
MENU_DIR    = ROOT_DIR / "menu_planner"

sys.path.insert(0, str(MENU_DIR))
from config import DB_PATH, IMAGES_DIR

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
GREY   = "\033[90m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def normalise(s: str) -> str:
    return s.lower().replace("-", " ").replace("_", " ").replace(".", " ").strip()


def get_all_dish_names(conn) -> list[str]:
    rows = conn.execute("SELECT name FROM dishes ORDER BY name").fetchall()
    return [r[0] for r in rows]


def match_filename(stem: str, dish_names: list[str]) -> str | None:
    norm_stem = normalise(stem)

    # 1. Exact match (case-insensitive)
    for d in dish_names:
        if normalise(d) == norm_stem:
            return d

    # 2. Fuzzy match (cutoff 0.82 — tight enough to avoid wrong matches)
    norm_names = {normalise(d): d for d in dish_names}
    close = get_close_matches(norm_stem, norm_names.keys(), n=1, cutoff=0.82)
    if close:
        return norm_names[close[0]]

    # 3. Substring match — filename is contained in dish name or vice versa
    for norm_d, d in norm_names.items():
        if norm_stem in norm_d or norm_d in norm_stem:
            return d

    return None


def get_existing_image(conn, dish_name: str) -> str:
    row = conn.execute(
        "SELECT image_path FROM dishes WHERE name=? COLLATE NOCASE", (dish_name,)
    ).fetchone()
    return row[0] if row else ""


def set_image_path(conn, dish_name: str, image_path: str):
    conn.execute(
        "UPDATE dishes SET image_path=? WHERE name=? COLLATE NOCASE",
        (str(image_path), dish_name)
    )


def run(source_dir: Path, force: bool = False):
    print(f"\n{BOLD}MenuPlanner — Dish Image Importer{RESET}")
    print(f"{GREY}Source : {source_dir}{RESET}")
    print(f"{GREY}Target : {IMAGES_DIR}{RESET}")
    print(f"{GREY}DB     : {DB_PATH}{RESET}\n")

    if not source_dir.exists():
        print(f"{RED}✗ Source folder not found: {source_dir}{RESET}")
        sys.exit(1)

    # Collect image files
    image_files = [f for f in source_dir.iterdir() if f.suffix.lower() in SUPPORTED]
    if not image_files:
        print(f"{YELLOW}⚠ No image files found in {source_dir}{RESET}")
        print(f"  Supported formats: {', '.join(SUPPORTED)}")
        sys.exit(0)

    print(f"Found {BOLD}{len(image_files)}{RESET} image files.\n")

    conn = sqlite3.connect(DB_PATH)
    dish_names = get_all_dish_names(conn)

    matched   = []
    skipped   = []
    no_match  = []

    for img in sorted(image_files):
        stem = img.stem
        dish = match_filename(stem, dish_names)

        if dish is None:
            no_match.append(img.name)
            print(f"{RED}  ✗ No match  {RESET}{GREY}{img.name}{RESET}")
            continue

        existing = get_existing_image(conn, dish)
        if existing and not force:
            skipped.append((img.name, dish))
            print(f"{GREY}  ⊘ Skipped   {RESET}{GREY}{img.name}{RESET} → {dish} (already set)")
            continue

        # Determine destination filename — always save as .jpg for Qt compatibility
        safe_name = dish.replace("/", "-").replace("\\", "-").replace(":", "-")
        src_ext   = img.suffix.lower()
        dest      = IMAGES_DIR / f"{safe_name}.jpg"

        try:
            if src_ext in (".webp", ".bmp", ".png"):
                # Convert to JPEG so Qt can always display it
                from PIL import Image
                with Image.open(img) as im:
                    im.convert("RGB").save(dest, "JPEG", quality=92)
            else:
                shutil.copy2(img, dest)
            set_image_path(conn, dish, dest)
            matched.append((img.name, dish))
            match_note = f" {GREY}(fuzzy){RESET}" if normalise(stem) != normalise(dish) else ""
            print(f"{GREEN}  ✓ Imported  {RESET}{img.name}{match_note} → {CYAN}{dish}{RESET}")
        except Exception as e:
            no_match.append(img.name)
            print(f"{RED}  ✗ Error     {RESET}{img.name}: {e}")

    conn.commit()
    conn.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'─'*50}")
    print(f"{BOLD}Summary{RESET}")
    print(f"  {GREEN}✓ Imported : {len(matched)}{RESET}")
    print(f"  {GREY}⊘ Skipped  : {len(skipped)}{RESET}  (use --force to overwrite)")
    print(f"  {RED}✗ No match : {len(no_match)}{RESET}")

    if no_match:
        print(f"\n{YELLOW}Unmatched files — rename these to match dish names exactly:{RESET}")
        for name in no_match:
            print(f"  {GREY}• {name}{RESET}")

    if matched:
        print(f"\n{GREEN}Done! Images are live in the app.{RESET}")
    print()


if __name__ == "__main__":
    force = "--force" in sys.argv
    args  = [a for a in sys.argv[1:] if not a.startswith("--")]

    if args:
        source = Path(args[0])
    else:
        default = ROOT_DIR / "dish_images_raw"
        print(f"No folder specified. Using default: {default}")
        print("Or run:  python scripts/import_dish_images.py C:\\path\\to\\folder\n")
        source = default

    run(source, force=force)

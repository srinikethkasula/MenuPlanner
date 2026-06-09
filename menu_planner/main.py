"""
main.py — Entry point for the Menu Planner application.
Includes crash recovery detection.
"""
import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

# Fix SSL certificates for frozen application
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
except ImportError:
    pass

from config import DATA_DIR

CRASH_FLAG = DATA_DIR / "crash.flag"


def setup_logging():
    log_file = DATA_DIR / "menu_planner.log"
    # Max size 5MB, keep 3 backup files
    handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    
    # Also log to stdout for development, handling any stdout reconfigurations
    try:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        root_logger.addHandler(console)
    except Exception:
        pass


def backup_database():
    from config import DB_PATH
    if not DB_PATH.exists():
        return
    
    try:
        # Shift backups: .db.bak3 -> deleted, .db.bak2 -> .db.bak3, .db.bak1 -> .db.bak2
        for i in range(2, 0, -1):
            old_bak = DB_PATH.with_suffix(f".db.bak{i}")
            new_bak = DB_PATH.with_suffix(f".db.bak{i+1}")
            if old_bak.exists():
                if new_bak.exists():
                    new_bak.unlink()
                old_bak.rename(new_bak)
                
        # Copy current db to .db.bak1
        first_bak = DB_PATH.with_suffix(".db.bak1")
        if first_bak.exists():
            first_bak.rename(DB_PATH.with_suffix(".db.bak2"))
            
        import shutil
        shutil.copy2(DB_PATH, first_bak)
        logging.info("SQLite database backup created successfully.")
    except Exception as e:
        logging.error(f"Failed to create SQLite database backup: {e}", exc_info=True)


def check_crash_recovery() -> bool:
    """Return True if a crash flag was found (prior crash detected)."""
    if CRASH_FLAG.exists():
        CRASH_FLAG.unlink(missing_ok=True)
        return True
    return False


def write_crash_flag():
    """Write flag file; deleted on clean exit."""
    CRASH_FLAG.parent.mkdir(parents=True, exist_ok=True)
    CRASH_FLAG.write_text("running")


def main():
    from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
    from PyQt6.QtGui import QPixmap
    from config import RESOURCES_DIR

    app = QApplication(sys.argv)
    app.setApplicationName("Menu Planner")
    app.setOrganizationName("Chathradhari Caterers")

    # Show splash screen immediately
    splash_pix = QPixmap(str(RESOURCES_DIR / "company_image.jpg"))
    splash = QSplashScreen(splash_pix)
    splash.show()
    app.processEvents()

    # Setup logging
    setup_logging()
    logging.info("Application starting up...")
    try:
        from PyQt6.QtGui import QImageReader
        formats = [f.data().decode() for f in QImageReader.supportedImageFormats()]
        logging.info(f"Supported image formats in frozen app: {formats}")
    except Exception as e:
        logging.error(f"Failed to check supported image formats: {e}")

    try:
        from config import DB_PATH, IMAGES_DIR
        logging.info(f"Active DB path: {DB_PATH}")
        logging.info(f"Active IMAGES path: {IMAGES_DIR}")
    except Exception as e:
        logging.error(f"Failed to log active paths: {e}")

    # Crash recovery check
    recovered = check_crash_recovery()
    write_crash_flag()

    # SQLite rolling backup
    backup_database()

    # Init database
    import database as db
    db.seed_database_on_first_run()
    db.seed_images_on_first_run()
    db.init_db()

    # Build main window
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    splash.finish(window)

    if recovered:
        logging.warning("App recovered from unclean exit.")
        QMessageBox.information(
            window,
            "Recovered",
            "The application was not closed cleanly last time.\n"
            "Your data has been recovered from the database."
        )

    logging.info("Starting PyQt6 app exec loop.")
    exit_code = app.exec()

    # Clean exit: remove crash flag
    if CRASH_FLAG.exists():
        CRASH_FLAG.unlink(missing_ok=True)

    logging.info(f"Clean exit with code: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

"""
ui/main_window.py — Main window. Theme-aware (dark / light toggle).
"""
from __future__ import annotations
from datetime import date

from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QMessageBox, QStatusBar,
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

import database as db
import theme as thm
from config import DAYS, SLOTS, APP_NAME, APP_VERSION

from ui.dish_dock import DishDock
from ui.planning_grid import PlanningGrid
from ui.ppt_preview import PPTPreview
from ui.dialogs import AddDishDialog, SettingsDialog, ImageManagerDialog, ExportDialog


# ── Global QSS (generated from theme tokens) ─────────────────────────────────

def _make_app_qss() -> str:
    t = thm.current()
    return f"""
* {{ font-family: 'Segoe UI', 'Inter', Arial, sans-serif; }}

QWidget {{ background: {t['bg']}; color: {t['text']}; }}

/* Scrollbars */
QScrollBar:vertical {{
    background: {t['bg']}; width: 7px; border-radius: 3px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t['scroll']}; border-radius: 3px; min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{ background: {t['scroll_h']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {t['bg']}; height: 7px; border-radius: 3px; margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {t['scroll']}; border-radius: 3px; min-width: 28px;
}}
QScrollBar::handle:horizontal:hover {{ background: {t['scroll_h']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* Menu bar */
QMenuBar {{
    background: {t['surface']};
    color: {t['text2']};
    padding: 0 8px;
    font-size: 11px;
    border-bottom: 1px solid {t['border']};
}}
QMenuBar::item {{ padding: 6px 14px; border-radius: 4px; }}
QMenuBar::item:selected {{ background: {t['surface2']}; color: {t['text']}; }}
QMenuBar::item:pressed  {{ background: {t['surface3']}; }}

/* Menus */
QMenu {{
    background: {t['surface']};
    border: 1px solid {t['border_med']};
    border-radius: 8px;
    padding: 6px 4px;
    color: {t['text']};
}}
QMenu::item {{ padding: 8px 28px; font-size: 11px; border-radius: 4px; }}
QMenu::item:selected {{ background: {t['surface2']}; color: {t['text']}; }}
QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 10px; }}

/* Tooltips */
QToolTip {{
    background: {t['surface']};
    color: {t['text']};
    border: 1px solid {t['border_med']};
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 10px;
}}

/* Status bar */
QStatusBar {{
    background: {t['surface']};
    color: {t['text3']};
    font-size: 10px;
    border-top: 1px solid {t['border']};
}}

/* Splitter handle */
QSplitter::handle {{ background: {t['border']}; }}
QSplitter::handle:horizontal {{ width: 1px; }}

/* Dialogs */
QDialog    {{ background: {t['dlg_bg']}; }}
QMessageBox {{ background: {t['dlg_bg']}; }}
QMessageBox QLabel {{ color: {t['text']}; }}
QMessageBox QPushButton {{
    background: {t['surface2']};
    border: 1px solid {t['border_med']};
    border-radius: 6px;
    padding: 6px 18px;
    color: {t['text']};
    font-weight: bold;
}}
QMessageBox QPushButton:hover {{
    background: {t['surface3']};
    border-color: {t['accent']};
    color: {t['accent']};
}}

/* Completer popup / list views */
QAbstractItemView {{
    background: {t['surface']};
    border: 1px solid {t['border_med']};
    border-radius: 6px;
    color: {t['text']};
    selection-background-color: {t['surface2']};
    selection-color: {t['text']};
    outline: none;
}}
QAbstractItemView::item {{
    padding: 5px 10px;
    min-height: 24px;
}}
QAbstractItemView::item:hover {{ background: {t['surface2']}; }}

/* ComboBox */
QComboBox {{
    background: {t['input_bg']};
    border: 1px solid {t['border_med']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {t['text']};
    font-size: 11px;
    min-height: 32px;
}}
QComboBox:focus {{ border-color: {t['accent']}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}

/* Table widget */
QTableWidget {{
    background: {t['surface']};
    border: 1px solid {t['border_med']};
    border-radius: 8px;
    color: {t['text']};
    gridline-color: {t['border']};
    font-size: 10px;
}}
QHeaderView::section {{
    background: {t['surface2']};
    color: {t['text']};
    font-weight: bold;
    font-size: 10px;
    padding: 6px;
    border: none;
    border-bottom: 1px solid {t['border_med']};
}}
QTableWidget::item:alternate {{ background: {t['surface2']}; }}
QTableWidget::item:selected {{
    background: rgba(74,158,255,0.15);
    color: {t['text']};
}}

/* Checkboxes */
QCheckBox {{ color: {t['text']}; font-size: 11px; spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1px solid {t['border_med']};
    border-radius: 4px;
    background: {t['input_bg']};
}}
QCheckBox::indicator:checked {{
    background: {t['accent']};
    border-color: {t['accent']};
}}
QCheckBox::indicator:hover {{ border-color: {t['accent']}; }}

/* Dialog labels */
QDialog QLabel {{ color: {t['text2']}; font-size: 11px; background: transparent; }}
QDialog QLineEdit {{
    background: {t['input_bg']};
    border: 1px solid {t['border_med']};
    border-radius: 8px;
    padding: 7px 12px;
    color: {t['text']};
    font-size: 11px;
    min-height: 34px;
}}
QDialog QLineEdit:focus {{
    border-color: {t['accent']};
    background: {t['input_bg_f']};
}}

/* Radio buttons */
QRadioButton {{
    color: {t['text']};
    font-size: 11px;
    spacing: 8px;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {t['border_med']};
    border-radius: 8px;
    background: {t['input_bg']};
}}
QRadioButton::indicator:checked {{
    background: {t['accent']};
    border-color: {t['accent']};
}}
QRadioButton::indicator:hover {{
    border-color: {t['accent']};
}}

/* Custom Dialog Components */
QFrame[dialog_box="true"] {{
    background: {t['surface']};
    border: 1px solid {t['border_med']};
    border-radius: 10px;
    padding: 6px;
}}

QFrame[dialog_divider="true"] {{
    background: {t['border_med']};
    min-height: 1px;
    max-height: 1px;
}}

QFrame[dialog_header="true"] {{
    background: {t['surface2']};
    border-radius: 10px;
    border: 1px solid {t['border_med']};
}}

QFrame[dialog_header="true"] QLabel {{
    background: transparent;
    border: none;
}}

QFrame[dialog_header="true"] QLabel[header_title="true"] {{
    color: {t['text']};
    font-size: 14px;
    font-weight: bold;
}}

QFrame[dialog_header="true"] QLabel[header_subtitle="true"] {{
    color: {t['text3']};
    font-size: 10px;
}}

QLabel[section_bar="true"] {{
    color: {t['text2']};
    background: {t['surface2']};
    border: 1px solid {t['border_med']};
    border-radius: 6px;
    padding: 0 12px;
}}

/* Dialog Buttons */
QDialog QPushButton {{
    background: {t['surface2']};
    color: {t['text2']};
    font-size: 11px;
    border: 1px solid {t['border_med']};
    border-radius: 9px;
    padding: 0 20px;
    min-height: 36px;
}}
QDialog QPushButton:hover {{
    background: {t['surface3']};
    color: {t['text']};
    border-color: {t['border_hi']};
}}
QDialog QPushButton:pressed {{
    background: {t['surface3']};
}}
QDialog QPushButton[primary="true"] {{
    background: {t['accent']};
    color: #ffffff;
    font-size: 12px;
    font-weight: bold;
    border: none;
    border-radius: 9px;
    padding: 0 24px;
    min-height: 40px;
}}
QDialog QPushButton[primary="true"]:hover {{
    background: {t['accent_h']};
}}
QDialog QPushButton[primary="true"]:pressed {{
    background: {t['accent_h']};
}}
QDialog QPushButton:disabled {{
    background: {t['surface2']};
    color: {t['text3']};
    border-color: {t['border']};
}}
"""


# ── Header bar ────────────────────────────────────────────────────────────────

_HDR_BTN = """
    QPushButton {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 0 {pad}px;
        color: {fg};
        font-size: {fs}px;
        font-weight: bold;
        min-height: 34px;
    }}
    QPushButton:hover {{ background: {hover}; border-color: rgba(255,255,255,0.3); color: #ffffff; }}
    QPushButton:pressed {{ background: rgba(255,255,255,0.12); }}
"""


class HeaderBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self._setup_ui()
        self.refresh_theme()

    def _setup_ui(self):
        row = QHBoxLayout(self)
        row.setContentsMargins(20, 0, 20, 0)
        row.setSpacing(10)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(1)
        self._name_lbl = QLabel("Chathradhari Caterers")
        self._name_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._sub_lbl  = QLabel("Oyster Canteen  •  Weekly Menu Planner")
        self._sub_lbl.setStyleSheet("font-size: 9px; background: transparent;")
        brand_col.addWidget(self._name_lbl)
        brand_col.addWidget(self._sub_lbl)
        row.addLayout(brand_col)
        row.addStretch()

        self.add_btn      = QPushButton("+ Dish")
        self.export_btn   = QPushButton("Export")
        self.settings_btn = QPushButton("Settings")
        self.theme_btn    = QPushButton("🌙")

        for btn in (self.add_btn, self.export_btn, self.settings_btn, self.theme_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            row.addWidget(btn)

        self.add_btn.setToolTip("Add a custom dish  (Ctrl+N)")
        self.export_btn.setToolTip("Export PPT / Excel  (Ctrl+E)")
        self.settings_btn.setToolTip("Settings  (Ctrl+,)")
        self.theme_btn.setToolTip("Toggle light / dark mode")

        self._ver = QLabel(f"v{APP_VERSION}")
        self._ver.setStyleSheet("font-size: 9px; background: transparent;")
        row.addWidget(self._ver)

    def refresh_theme(self):
        t     = thm.current()
        is_dk = t["name"] == "dark"
        hdr_bg = ("qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                  "stop:0 #0d1117,stop:0.4 #161b22,stop:1 #0d1117)"
                  if is_dk else
                  "qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                  "stop:0 #e8f0fe,stop:0.5 #f8faff,stop:1 #e8f0fe)")
        self.setStyleSheet(f"""
            QFrame {{
                background: {hdr_bg};
                border-bottom: 1px solid {t['border']};
            }}
        """)
        self._name_lbl.setStyleSheet(f"color: {t['text']}; background: transparent;")
        self._sub_lbl.setStyleSheet(
            f"color: {t['text3']}; font-size: 9px; background: transparent;"
        )
        self._ver.setStyleSheet(f"color: {t['text3']}; font-size: 9px; background: transparent;")

        ghost = _HDR_BTN.format(
            bg=t['surface2'], border=t['border_med'],
            fg=t['text2'], pad=14, fs=11, hover=t['surface3'],
        )
        primary = _HDR_BTN.format(
            bg=t['accent'], border=t['accent'],
            fg="#ffffff", pad=18, fs=12, hover=t['accent_h'],
        )
        self.add_btn.setStyleSheet(ghost)
        self.settings_btn.setStyleSheet(ghost)
        self.export_btn.setStyleSheet(primary)
        self.theme_btn.setStyleSheet(ghost)
        self.theme_btn.setText("☀️" if thm.is_dark() else "🌙")


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  —  Chathradhari Caterers")
        self.setMinimumSize(1280, 720)
        self.resize(1700, 980)

        # Load saved theme (or detect system theme)
        saved = db.get_setting("theme")
        thm.set_theme(saved if saved in ("dark", "light") else thm.detect_system())
        QApplication.instance().setStyleSheet(_make_app_qss())

        self._dishes_db: dict[str, dict] = {}
        self._refresh_dishes_db()
        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._connect_signals()

        # Pass initial dishes to grid
        self.grid.set_dishes(self._dishes_db)

        # Restore last week
        last = db.get_setting("last_week")
        if last:
            try:
                parts = last.split("-")
                d = date(int(parts[0]), int(parts[1]), int(parts[2]))
                self.grid.load_week(db.monday_of_week(d))
            except Exception:
                pass

        QTimer.singleShot(400, self._refresh_preview)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _refresh_dishes_db(self):
        self._dishes_db = {d["name"]: d for d in db.get_all_dishes()}

    def _setup_ui(self):
        t    = thm.current()
        root = QWidget()
        root.setStyleSheet(f"QWidget {{ background: {t['bg']}; }}")
        self.setCentralWidget(root)

        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self.header = HeaderBar()
        self.header.add_btn.clicked.connect(self._add_dish)
        self.header.export_btn.clicked.connect(self._open_export)
        self.header.settings_btn.clicked.connect(self._open_settings)
        self.header.theme_btn.clicked.connect(self._toggle_theme)
        vbox.addWidget(self.header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter {{ background: {t['bg']}; }}")
        vbox.addWidget(splitter, 1)

        self.dish_dock = DishDock()
        self.grid      = PlanningGrid()
        self.preview   = PPTPreview()

        splitter.addWidget(self.dish_dock)
        splitter.addWidget(self.grid)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        self.dish_dock.add_btn.clicked.connect(self._add_dish)
        self._splitter = splitter
        self._root_widget = root

    def _setup_menu(self):
        mb = self.menuBar()

        def _act(label, slot, sc=None):
            from PyQt6.QtGui import QAction
            a = QAction(label, self)
            a.triggered.connect(slot)
            if sc:
                a.setShortcut(sc)
            return a

        file_m = mb.addMenu("File")
        file_m.addAction(_act("📤  Export…",          self._open_export,   "Ctrl+E"))
        file_m.addSeparator()
        file_m.addAction(_act("⚙  Settings…",          self._open_settings, "Ctrl+,"))
        file_m.addSeparator()
        file_m.addAction(_act("Exit",                   self.close,          "Alt+F4"))

        dish_m = mb.addMenu("Dishes")
        dish_m.addAction(_act("＋  Add Custom Dish…",  self._add_dish,            "Ctrl+N"))
        dish_m.addAction(_act("🖼  Image Manager…",    self._open_image_manager))
        dish_m.addAction(_act("↻  Refresh Dish List",  self._refresh_dock))

        view_m = mb.addMenu("View")
        view_m.addAction(_act("🌙  Toggle Theme",      self._toggle_theme,  "Ctrl+T"))

    def _setup_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.showMessage(
            "Drag a dish onto any cell  •  or click a dish then click a cell  •  Ctrl+E to export"
        )
        self.status_bar = sb

    def _connect_signals(self):
        self.dish_dock.dish_selected.connect(self._on_dish_selected)
        self.dish_dock.dish_deleted.connect(self._on_dish_deleted)
        self.dish_dock.dish_edited.connect(self._on_dish_edited)
        self.grid.slot_updated.connect(self._on_slot_updated)
        self.grid.week_changed.connect(self._on_week_changed)

    # ── Signal handlers ───────────────────────────────────────────────────────

    def _on_dish_selected(self, dish: dict):
        self.grid.assign_dish_to_pending(dish)
        self.status_bar.showMessage(
            f"✓  '{dish['name']}' selected — click any cell to assign", 5000
        )

    def _on_dish_deleted(self, name: str):
        self._refresh_dishes_db()
        self.grid.set_dishes(self._dishes_db)
        QTimer.singleShot(300, self._refresh_preview)
        self.status_bar.showMessage(f"Deleted: {name}", 3000)

    def _on_dish_edited(self, old_name: str, new_name: str):
        self._refresh_dishes_db()
        self.grid.set_dishes(self._dishes_db)
        if new_name and new_name != old_name:
            # Reload week so renamed dishes show updated name in cells
            self.grid.load_week(self.grid.get_week_start())
        QTimer.singleShot(300, self._refresh_preview)
        self.status_bar.showMessage(f"Updated: {new_name or old_name}", 3000)

    def _on_slot_updated(self, day: str, slot: str, dish_name: str):
        self.status_bar.showMessage(f"Saved: {day} / {slot} → {dish_name}", 2000)
        QTimer.singleShot(600, self._refresh_preview)

    def _on_week_changed(self, week_start: date):
        self.status_bar.showMessage(f"Week of {week_start.strftime('%d %b %Y')}", 3000)
        QTimer.singleShot(300, self._refresh_preview)

    def _refresh_preview(self):
        day_data = {day: self.grid.get_day_data(day) for day in DAYS}
        self.preview.update_data(day_data, self._dishes_db)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _toggle_theme(self):
        new_name = "light" if thm.is_dark() else "dark"
        thm.set_theme(new_name)
        db.set_setting("theme", new_name)
        QApplication.instance().setStyleSheet(_make_app_qss())
        # Refresh all theme-aware components
        self.header.refresh_theme()
        self.dish_dock.refresh_theme()
        self.grid.refresh_theme()
        t = thm.current()
        self._root_widget.setStyleSheet(f"QWidget {{ background: {t['bg']}; }}")
        self._splitter.setStyleSheet(f"QSplitter {{ background: {t['bg']}; }}")
        self.status_bar.showMessage(
            f"Switched to {'Dark' if thm.is_dark() else 'Light'} mode", 2000
        )

    def _open_export(self):
        dlg = ExportDialog(self, self.grid, self._dishes_db)
        dlg.exec()

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.status_bar.showMessage("Settings saved.", 3000)

    def _add_dish(self):
        dlg = AddDishDialog(self)
        if dlg.exec():
            self._refresh_dishes_db()
            self.grid.set_dishes(self._dishes_db)
            self.dish_dock.refresh_dishes()
            self.status_bar.showMessage(f"Dish added: {dlg.get_dish_name()}", 3000)

    def _open_image_manager(self):
        dlg = ImageManagerDialog(self)
        dlg.exec()
        self._refresh_dishes_db()
        self.grid.set_dishes(self._dishes_db)
        self.dish_dock.refresh_dishes()
        QTimer.singleShot(300, self._refresh_preview)

    def _refresh_dock(self):
        self._refresh_dishes_db()
        self.grid.set_dishes(self._dishes_db)
        self.dish_dock.refresh_dishes()

    # ── Close ─────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        from config import DATA_DIR
        f = DATA_DIR / "crash.flag"
        if f.exists():
            f.unlink()
        event.accept()

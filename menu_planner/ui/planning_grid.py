"""
ui/planning_grid.py — Weekly planning grid. Theme-aware, dish-library autocomplete.
"""
from __future__ import annotations
from datetime import date, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout,
    QLineEdit, QLabel, QPushButton, QFrame, QCompleter,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QStringListModel
from PyQt6.QtGui import QFont

import database as db
import theme as thm
from config import DAYS, SLOTS, SLOT_IDS, SLOT_DISPLAY, SLOT_SECTION, SECTION_LABELS, CATEGORY_COLORS

SECTION_ACCENT = {
    "LUNCH":      "#3b82f6",
    "SNACKS":     "#a855f7",
    "FRUIT":      "#0ea5e9",   # sky blue
    "ADDITIONAL": "#f59e0b",
}
SECTION_ICONS = {
    "LUNCH": "🍛", "SNACKS": "🥐", "FRUIT": "🍎", "ADDITIONAL": "☕",
}


def _cell_qss(t: dict, accent: str) -> str:
    """accent = category colour used for left border only. Cell bg is always sky-blue tinted."""
    is_dark  = t["name"] == "dark"
    sky      = "#0ea5e9"
    empty_bg = ("qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 rgba(255,255,255,0.04),stop:1 rgba(255,255,255,0.01))"
                if is_dark else "#ffffff")
    filled_bg = ("qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                 f"stop:0 {sky}18,stop:1 {sky}06)"
                 if is_dark else f"{sky}0f")
    return f"""
        GridCell {{
            background: {empty_bg};
            border: 1px solid {t['border']};
            border-radius: 7px;
            padding: 3px 8px;
            color: {t['text3']};
            font-size: 10px;
            min-height: 34px;
        }}
        GridCell:hover {{
            background: {t['cell_h']};
            border: 1px solid {t['border_med']};
            color: {t['text2']};
        }}
        GridCell:focus {{
            background: {t['cell_bg']};
            border: 1px solid {t['accent']};
            color: {t['text']};
        }}
        GridCell[filled="true"] {{
            background: {filled_bg};
            border: 1px solid {sky}44;
            border-left: 3px solid {accent};
            color: {t['text']};
            font-weight: 600;
            font-size: 10px;
        }}
        GridCell[filled="true"]:hover {{
            border: 1px solid {sky}77;
            border-left: 3px solid {accent};
        }}
        GridCell[filled="true"]:focus {{
            border: 1px solid {t['accent']};
            border-left: 3px solid {accent};
            color: {t['text']};
        }}
        GridCell[drop_hover="true"] {{
            background: {t['accent']}22;
            border: 1px solid {t['accent']};
        }}
        GridCell[invalid="true"] {{
            border: 1px solid {t['danger']};
            background: rgba(239,68,68,0.1);
            color: {t['danger']};
        }}
    """


class GridCell(QLineEdit):
    """Autocomplete planning cell. Validates against dish library on commit."""

    cell_changed = pyqtSignal(str, str, str)

    def __init__(self, day: str, slot: str, section: str,
                 completer_model: QStringListModel, parent=None):
        super().__init__(parent)
        self.day   = day
        self.slot  = slot
        self._section  = section
        self._accent   = SECTION_ACCENT.get(section, "#4a9eff")
        self._cat_color = ""
        self._last_valid = ""
        self._dishes_db: dict = {}

        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._emit)

        self.setAcceptDrops(True)
        self.setPlaceholderText("search or drop dish…")
        self.setFixedHeight(34)

        comp = QCompleter(completer_model, self)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        comp.setMaxVisibleItems(10)
        comp.activated.connect(self._on_completer_activated)
        self.setCompleter(comp)

        self._apply_style()
        self.textChanged.connect(self._on_text_changed)
        self.editingFinished.connect(self._validate)

    # ── Style ──────────────────────────────────────────────────────────────────

    def _apply_style(self):
        accent = self._cat_color if self._cat_color else self._accent
        self.setStyleSheet(_cell_qss(thm.current(), accent))

    def refresh_theme(self):
        self._apply_style()

    # ── Dish data ──────────────────────────────────────────────────────────────

    def set_dishes_db(self, dishes_db: dict):
        self._dishes_db = dishes_db

    # ── Text / validation ──────────────────────────────────────────────────────

    def _on_text_changed(self, txt: str):
        self.setProperty("filled",     bool(txt.strip()))
        self.setProperty("drop_hover", False)
        self.setProperty("invalid",    False)
        if not txt.strip():
            self._cat_color = ""
        self._apply_style()
        self._timer.start()

    def _validate(self):
        txt = self.text().strip()
        if not txt:
            self._last_valid = ""
            self._cat_color  = ""
            self._apply_style()
            return
        
        # Split by '+' to validate each component dish
        parts = [p.strip() for p in txt.split("+") if p.strip()]
        if not parts:
            self._revert_invalid()
            return
            
        canonical_parts = []
        all_valid = True
        for part in parts:
            canonical = next(
                (n for n in self._dishes_db if n.lower() == part.lower()), None
            )
            if canonical:
                canonical_parts.append(canonical)
            else:
                all_valid = False
                break
                
        if all_valid:
            full_val = " + ".join(canonical_parts)
            first_dish = canonical_parts[0]
            cat = self._dishes_db[first_dish].get("category", "")
            self._cat_color  = CATEGORY_COLORS.get(cat, "")
            self._last_valid = full_val
            if self.text() != full_val:
                self.blockSignals(True)
                self.setText(full_val)
                self.blockSignals(False)
            self.setProperty("filled", True)
            self.setProperty("invalid", False)
            self._apply_style()
            self._timer.start()
        else:
            self.setProperty("invalid", True)
            self._apply_style()
            QTimer.singleShot(700, self._revert_invalid)

    def _revert_invalid(self):
        self.blockSignals(True)
        self.setText(self._last_valid)
        self.blockSignals(False)
        self.setProperty("filled",  bool(self._last_valid))
        self.setProperty("invalid", False)
        if self._last_valid:
            first_dish = self._last_valid.split(" + ")[0] if " + " in self._last_valid else self._last_valid
            if first_dish in self._dishes_db:
                cat = self._dishes_db[first_dish].get("category", "")
                self._cat_color = CATEGORY_COLORS.get(cat, "")
            else:
                self._cat_color = ""
        else:
            self._cat_color = ""
        self._apply_style()

    def _on_completer_activated(self, text: str):
        self.blockSignals(True)
        self.setText(text)
        self.blockSignals(False)
        dish = self._dishes_db.get(text, {})
        self._cat_color  = CATEGORY_COLORS.get(dish.get("category", ""), "")
        self._last_valid = text
        self.setProperty("filled",  True)
        self.setProperty("invalid", False)
        self._apply_style()
        self._timer.start()

    def _emit(self):
        self.cell_changed.emit(self.day, self.slot, self.text())

    def assign_dish(self, name: str):
        if not name.strip():
            full_name = ""
        else:
            current_text = self.text().strip()
            if current_text:
                # Append if not already present in cell
                dishes = [d.strip() for d in current_text.split("+") if d.strip()]
                if name not in dishes:
                    dishes.append(name)
                full_name = " + ".join(dishes)
            else:
                full_name = name

        self._last_valid = full_name
        first_dish = full_name.split(" + ")[0] if " + " in full_name else full_name
        dish = self._dishes_db.get(first_dish, {})
        self._cat_color = CATEGORY_COLORS.get(dish.get("category", ""), "")
        
        self.blockSignals(True)
        self.setText(full_name)
        self.blockSignals(False)
        self.setProperty("filled",     bool(full_name.strip()))
        self.setProperty("drop_hover", False)
        self.setProperty("invalid",    False)
        self._apply_style()
        self._timer.start()

    # ── Context menu (clear cell & delete item) ───────────────────────────────

    def contextMenuEvent(self, event):
        current_text = self.text().strip()
        if not current_text:
            return
        from PyQt6.QtWidgets import QMenu
        t    = thm.current()
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {t['surface']};
                border: 1px solid {t['border_med']};
                border-radius: 8px;
                padding: 4px;
                color: {t['text']};
                font-size: 11px;
            }}
            QMenu::item {{ padding: 7px 22px; border-radius: 4px; }}
            QMenu::item:selected {{ background: {t['surface2']}; }}
        """)
        clear_act = menu.addAction("✕  Clear cell")
        
        # Split by "+" to display delete options for individual dishes
        dishes = [d.strip() for d in current_text.split("+") if d.strip()]
        delete_actions = {}
        if len(dishes) > 1:
            menu.addSeparator()
            for dish in dishes:
                act = menu.addAction(f"Delete: {dish}")
                delete_actions[act] = dish
                
        selected_act = menu.exec(event.globalPos())
        if selected_act == clear_act:
            self.assign_dish("")
        elif selected_act in delete_actions:
            dish_to_remove = delete_actions[selected_act]
            dishes.remove(dish_to_remove)
            new_val = " + ".join(dishes)
            self.assign_dish(new_val)

    # ── Drag-and-drop ──────────────────────────────────────────────────────────

    def dragEnterEvent(self, e):
        if e.mimeData().hasText():
            self.setProperty("drop_hover", True)
            self._apply_style()
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasText():
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self.setProperty("drop_hover", False)
        self._apply_style()
        super().dragLeaveEvent(e)

    def dropEvent(self, e):
        self.setProperty("drop_hover", False)
        self._apply_style()
        if e.mimeData().hasText():
            self.assign_dish(e.mimeData().text())
            e.acceptProposedAction()
        else:
            e.ignore()


class PlanningGrid(QWidget):
    week_changed = pyqtSignal(date)
    slot_updated = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._week_start: date      = db.monday_of_week()
        self._plan_id: int | None   = None
        self._cells: dict[tuple[str, str], GridCell] = {}
        self._pending_dish: dict | None = None
        self._dishes_db: dict       = {}
        self._completer_model       = QStringListModel()

        # Widget references kept for theme refresh
        self._nav_bar: QFrame | None       = None
        self._week_lbl: QLabel | None      = None
        self._prev_btn: QPushButton | None = None
        self._next_btn: QPushButton | None = None
        self._scroll: QScrollArea | None   = None
        self.grid_container: QWidget | None = None
        self.grid_layout: QGridLayout | None = None

        self._setup_ui()
        self._apply_theme()
        self.load_week(self._week_start)

    # ── Build ──────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Week navigation bar
        self._nav_bar = QFrame()
        self._nav_bar.setFixedHeight(54)
        nav = QHBoxLayout(self._nav_bar)
        nav.setContentsMargins(14, 8, 14, 8)
        nav.setSpacing(10)

        self._prev_btn = QPushButton("◀  Prev")
        self._prev_btn.setFixedHeight(36)
        self._prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prev_btn.clicked.connect(self._prev_week)

        self._week_lbl = QLabel()
        self._week_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._next_btn = QPushButton("Next  ▶")
        self._next_btn.setFixedHeight(36)
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.clicked.connect(self._next_week)

        nav.addWidget(self._prev_btn)
        nav.addStretch()
        nav.addWidget(self._week_lbl)
        nav.addStretch()
        nav.addWidget(self._next_btn)
        outer.addWidget(self._nav_bar)

        # ── Scrollable grid
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        outer.addWidget(self._scroll, 1)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(2)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self._scroll.setWidget(self.grid_container)

    # ── Theme ──────────────────────────────────────────────────────────────────

    def _apply_theme(self):
        t      = thm.current()
        is_dk  = t["name"] == "dark"
        nav_bg = ("qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                  "stop:0 #1a1a2e,stop:0.5 #16213e,stop:1 #1a1a2e)"
                  if is_dk else
                  "qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                  "stop:0 #f0f4ff,stop:1 #e8f0fe)")
        self.setStyleSheet(f"PlanningGrid {{ background: {t['bg']}; }}")
        if self._nav_bar:
            self._nav_bar.setStyleSheet(f"""
                QFrame {{
                    background: {nav_bg};
                    border-bottom: 1px solid {t['border']};
                }}
            """)
            _btn = f"""
                QPushButton {{
                    background: rgba(255,255,255,0.07);
                    border: 1px solid {t['border_med']};
                    border-radius: 8px;
                    padding: 0 18px;
                    color: {t['text2']};
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: {t['accent']}22;
                    border-color: {t['accent']};
                    color: {t['accent']};
                }}
                QPushButton:pressed {{ background: {t['accent']}33; }}
            """
            self._prev_btn.setStyleSheet(_btn)
            self._next_btn.setStyleSheet(_btn)
            self._week_lbl.setStyleSheet(
                f"color: {'#e0e0e0' if is_dk else t['text']}; "
                f"background: transparent; font-size: 12px; font-weight: bold;"
            )
        if self._scroll:
            self._scroll.setStyleSheet(
                f"QScrollArea {{ border: none; background: {t['bg']}; }}"
                f"QScrollArea > QWidget > QWidget {{ background: {t['bg']}; }}"
            )
        if self.grid_container:
            self.grid_container.setStyleSheet(f"background: {t['bg']};")

    def refresh_theme(self):
        """Re-apply current theme. Rebuilds the grid to re-colour all headers."""
        self._apply_theme()
        self.load_week(self._week_start)

    # ── Grid build ─────────────────────────────────────────────────────────────

    def _build_header(self, day_dates: dict):
        t  = thm.current()
        gl = self.grid_layout

        is_dk  = t["name"] == "dark"
        hdr_bg = ("qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                  "stop:0 rgba(255,255,255,0.1),stop:1 rgba(255,255,255,0.04))"
                  if is_dk else
                  "qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                  "stop:0 rgba(255,255,255,0.95),stop:1 rgba(235,242,255,0.9))")
        top_border = "rgba(255,255,255,0.2)" if is_dk else "rgba(255,255,255,0.9)"

        corner = QLabel("SLOT")
        corner.setFixedWidth(150)
        corner.setFixedHeight(54)
        corner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        corner.setStyleSheet(f"""
            background: {hdr_bg};
            color: {t['text3']};
            font-weight: bold;
            font-size: 9px;
            letter-spacing: 2px;
            border: 1px solid {t['border_med']};
            border-top: 1px solid {top_border};
            border-radius: 8px;
        """)
        gl.addWidget(corner, 0, 0)

        for col, day in enumerate(DAYS, 1):
            d   = day_dates[day]
            lbl = QLabel(f"{day[:3].upper()}\n{d.strftime('%d %b %Y')}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedHeight(54)
            lbl.setMinimumWidth(140)
            lbl.setStyleSheet(f"""
                background: {hdr_bg};
                color: {t['text']};
                font-weight: bold;
                font-size: 11px;
                border: 1px solid {t['border_med']};
                border-top: 1px solid {top_border};
                border-radius: 8px;
                padding: 4px;
            """)
            gl.addWidget(lbl, 0, col)

    def _build_rows(self, week_data: dict):
        t   = thm.current()
        gl  = self.grid_layout
        row = 1
        
        # 1. Lunch Section
        # No section header. Start directly with slots.
        for slot_id, display, section, _ppt, _ in SLOTS:
            if section != "LUNCH":
                continue
            
            slot_lbl = QLabel(display)
            slot_lbl.setFixedHeight(34)
            slot_lbl.setFixedWidth(150)
            slot_lbl.setWordWrap(True)
            slot_lbl.setStyleSheet(f"""
                color: {t['text2']};
                font-size: 9px;
                font-weight: 600;
                padding: 0 8px;
                background: transparent;
                border-radius: 5px;
            """)
            gl.addWidget(slot_lbl, row, 0)

            for col, day in enumerate(DAYS, 1):
                dish_name = week_data.get(day, {}).get(slot_id, "")
                cell = GridCell(day, slot_id, section, self._completer_model)
                cell.set_dishes_db(self._dishes_db)
                cell.blockSignals(True)
                if dish_name.strip():
                    cell._last_valid = dish_name
                    dish = self._dishes_db.get(dish_name, {})
                    cell._cat_color = CATEGORY_COLORS.get(dish.get("category", ""), "")
                    cell.setText(dish_name)
                    cell.setProperty("filled", True)
                    cell._apply_style()
                cell.blockSignals(False)
                cell.cell_changed.connect(self._on_cell_changed)
                cell.installEventFilter(self)
                gl.addWidget(cell, row, col)
                self._cells[(day, slot_id)] = cell
            row += 1

        # 2. Blank Divider between Lunch and Snacks
        blank_row_1 = QFrame()
        blank_row_1.setFixedHeight(14)
        blank_row_1.setStyleSheet("background: transparent; border: none;")
        gl.addWidget(blank_row_1, row, 0, 1, 6)
        row += 1

        # 3. Snacks Section
        # No section header.
        for slot_id, display, section, _ppt, _ in SLOTS:
            if section != "SNACKS":
                continue
            
            slot_lbl = QLabel(display)
            slot_lbl.setFixedHeight(34)
            slot_lbl.setFixedWidth(150)
            slot_lbl.setWordWrap(True)
            slot_lbl.setStyleSheet(f"""
                color: {t['text2']};
                font-size: 9px;
                font-weight: 600;
                padding: 0 8px;
                background: transparent;
                border-radius: 5px;
            """)
            gl.addWidget(slot_lbl, row, 0)

            for col, day in enumerate(DAYS, 1):
                dish_name = week_data.get(day, {}).get(slot_id, "")
                cell = GridCell(day, slot_id, section, self._completer_model)
                cell.set_dishes_db(self._dishes_db)
                cell.blockSignals(True)
                if dish_name.strip():
                    cell._last_valid = dish_name
                    dish = self._dishes_db.get(dish_name, {})
                    cell._cat_color = CATEGORY_COLORS.get(dish.get("category", ""), "")
                    cell.setText(dish_name)
                    cell.setProperty("filled", True)
                    cell._apply_style()
                cell.blockSignals(False)
                cell.cell_changed.connect(self._on_cell_changed)
                cell.installEventFilter(self)
                gl.addWidget(cell, row, col)
                self._cells[(day, slot_id)] = cell
            row += 1

        # 4. Blank Divider between Snacks and Fruit
        blank_row_2 = QFrame()
        blank_row_2.setFixedHeight(14)
        blank_row_2.setStyleSheet("background: transparent; border: none;")
        gl.addWidget(blank_row_2, row, 0, 1, 6)
        row += 1

        # 5. Fruit Section
        # Left column has a single merged label: "FRUIT / HEALTHY(DIET) LUNCH " spanning 7 rows.
        fruit_slots = [s for s in SLOTS if s[2] == "FRUIT"]
        num_fruit_slots = len(fruit_slots)
        
        if num_fruit_slots > 0:
            accent = SECTION_ACCENT.get("FRUIT", t["accent"])
            
            # Merged vertical label in column 0
            fruit_lbl = QLabel("FRUIT / HEALTHY(DIET) LUNCH ")
            fruit_lbl.setFixedWidth(150)
            fruit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fruit_lbl.setWordWrap(True)
            fruit_lbl.setStyleSheet(f"""
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {accent}20, stop:1 {accent}05);
                color: {accent};
                font-weight: bold;
                font-size: 9px;
                border: 1px solid {t['border_med']};
                border-left: 3px solid {accent};
                border-radius: 6px;
                padding: 10px;
            """)
            gl.addWidget(fruit_lbl, row, 0, num_fruit_slots, 1)
            
            # Add input fields for each fruit slot
            for r_idx, (slot_id, display, section, _ppt, _) in enumerate(fruit_slots):
                for col, day in enumerate(DAYS, 1):
                    dish_name = week_data.get(day, {}).get(slot_id, "")
                    cell = GridCell(day, slot_id, section, self._completer_model)
                    cell.set_dishes_db(self._dishes_db)
                    cell.blockSignals(True)
                    if dish_name.strip():
                        cell._last_valid = dish_name
                        dish = self._dishes_db.get(dish_name, {})
                        cell._cat_color = CATEGORY_COLORS.get(dish.get("category", ""), "")
                        cell.setText(dish_name)
                        cell.setProperty("filled", True)
                        cell._apply_style()
                    cell.blockSignals(False)
                    cell.cell_changed.connect(self._on_cell_changed)
                    cell.installEventFilter(self)
                    gl.addWidget(cell, row + r_idx, col)
                    self._cells[(day, slot_id)] = cell
            row += num_fruit_slots

        # 6. Blank Divider between Fruit and Additional
        blank_row_3 = QFrame()
        blank_row_3.setFixedHeight(14)
        blank_row_3.setStyleSheet("background: transparent; border: none;")
        gl.addWidget(blank_row_3, row, 0, 1, 6)
        row += 1

        # 7. Additional Section
        # Header row is merged spanning all columns.
        accent  = SECTION_ACCENT.get("ADDITIONAL", t["accent"])
        sec_lbl = QLabel(f"  ☕  ADDITIONAL")
        sec_lbl.setFixedHeight(30)
        sec_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        sec_lbl.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {accent}30, stop:0.6 {accent}10, stop:1 transparent);
            color: {accent};
            font-weight: bold;
            font-size: 11px;
            border: none;
            border-left: 3px solid {accent};
            border-radius: 0 6px 6px 0;
            padding-left: 8px;
            letter-spacing: 1px;
        """)
        gl.addWidget(sec_lbl, row, 0, 1, 6)
        row += 1

        for slot_id, display, section, _ppt, _ in SLOTS:
            if section != "ADDITIONAL":
                continue
            
            slot_lbl = QLabel(display)
            slot_lbl.setFixedHeight(34)
            slot_lbl.setFixedWidth(150)
            slot_lbl.setWordWrap(True)
            slot_lbl.setStyleSheet(f"""
                color: {t['text2']};
                font-size: 9px;
                font-weight: 600;
                padding: 0 8px;
                background: transparent;
                border-radius: 5px;
            """)
            gl.addWidget(slot_lbl, row, 0)

            for col, day in enumerate(DAYS, 1):
                dish_name = week_data.get(day, {}).get(slot_id, "")
                cell = GridCell(day, slot_id, section, self._completer_model)
                cell.set_dishes_db(self._dishes_db)
                cell.blockSignals(True)
                if dish_name.strip():
                    cell._last_valid = dish_name
                    dish = self._dishes_db.get(dish_name, {})
                    cell._cat_color = CATEGORY_COLORS.get(dish.get("category", ""), "")
                    cell.setText(dish_name)
                    cell.setProperty("filled", True)
                    cell._apply_style()
                cell.blockSignals(False)
                cell.cell_changed.connect(self._on_cell_changed)
                cell.installEventFilter(self)
                gl.addWidget(cell, row, col)
                self._cells[(day, slot_id)] = cell
            row += 1

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_dishes(self, dishes_db: dict):
        """Update completer and all cell dish references. Re-colours filled cells."""
        self._dishes_db = dishes_db
        self._completer_model.setStringList(sorted(dishes_db.keys()))
        for cell in self._cells.values():
            cell.set_dishes_db(dishes_db)
            txt = cell.text().strip()
            if txt:
                dish = dishes_db.get(txt, {})
                cell._cat_color = CATEGORY_COLORS.get(dish.get("category", ""), "")
                cell._apply_style()

    def load_week(self, week_start: date):
        self._week_start = week_start
        self._plan_id    = db.get_or_create_plan(week_start)
        week_data        = db.get_week_data(self._plan_id)
        day_dates        = db.week_dates(week_start)

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cells.clear()

        self._build_header(day_dates)
        self._build_rows(week_data)

        end = week_start + timedelta(days=4)
        self._week_lbl.setText(
            f"{week_start.strftime('%d %b')}  —  {end.strftime('%d %b %Y')}"
        )
        self.week_changed.emit(week_start)
        db.set_setting("last_week", week_start.isoformat())

    def assign_dish_to_pending(self, dish: dict):
        self._pending_dish = dish

    def get_day_data(self, day: str) -> dict:
        return {
            slot_id: self._cells.get((day, slot_id), QLineEdit()).text()
            for slot_id, *_ in SLOTS
        }

    def get_week_start(self) -> date:    return self._week_start
    def get_plan_id(self) -> int | None: return self._plan_id

    # ── Internal ───────────────────────────────────────────────────────────────

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if isinstance(obj, GridCell) and event.type() == QEvent.Type.MouseButtonPress:
            if self._pending_dish is not None:
                obj.assign_dish(self._pending_dish["name"])
                self._pending_dish = None
                return True
        return super().eventFilter(obj, event)

    def _on_cell_changed(self, day: str, slot: str, value: str):
        if self._plan_id is not None:
            db.set_slot(self._plan_id, day, slot, value)
        self.slot_updated.emit(day, slot, value)

    def _prev_week(self): self.load_week(self._week_start - timedelta(weeks=1))
    def _next_week(self): self.load_week(self._week_start + timedelta(weeks=1))

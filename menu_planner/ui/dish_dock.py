"""
ui/dish_dock.py — Left panel: dish library with image thumbnails, category chips,
                  and right-click Edit / Delete per card.
"""
from __future__ import annotations
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QFrame, QScrollArea, QGridLayout, QMenu, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QMimeData, QPoint, QRect
from PyQt6.QtGui import (
    QFont, QColor, QDrag, QPixmap, QPainter, QPen, QBrush, QFontMetrics, QAction,
    QImage, QPainterPath,
)

import database as db
import theme as thm
from config import CATEGORY_COLORS

FILTERS = ["All", "Veg", "Non-Veg", "Breakfast", "Lunch", "Snacks", "Juice", "Soup", "Additionals", "Fruit Lunch", "Dessert", "Custom"]

COLS       = 4
CARD_W     = 82
CARD_H     = 106    # +6 vs old 100, to fit category chip
CARD_IMG_H = 58
CARD_GAP   = 6
DOCK_PAD   = 8
DOCK_WIDTH = COLS * CARD_W + (COLS - 1) * CARD_GAP + 2 * DOCK_PAD + 7


def _chip_qss(t: dict) -> str:
    return f"""
        QPushButton {{
            background: {t['surface2']};
            border: 1px solid {t['border_med']};
            border-radius: 10px;
            padding: 0 10px;
            color: {t['text2']};
            font-size: 9px;
            font-weight: bold;
            min-height: 22px;
        }}
        QPushButton:hover {{ background: {t['surface3']}; border-color: {t['border_hi']}; }}
        QPushButton:checked {{
            background: {t['accent']};
            color: #ffffff;
            border-color: {t['accent']};
        }}
    """


from collections import OrderedDict

_MAX_CACHE_SIZE = 100
_THUMB_CACHE: OrderedDict[str, QPixmap] = OrderedDict()

def get_cached_thumbnail(path: str, w: int, h: int) -> QPixmap | None:
    if not path:
        return None
    from database import resolve_image_path
    resolved = resolve_image_path(path)
    if not resolved:
        return None
    if resolved in _THUMB_CACHE:
        # Move to end (most recently used)
        _THUMB_CACHE.move_to_end(resolved)
        return _THUMB_CACHE[resolved]
    try:
        p = Path(resolved)
        if p.exists():
            pix = DishCard._load_pixmap(resolved)
            if pix and not pix.isNull():
                pix = pix.scaled(w, h,
                                 Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                 Qt.TransformationMode.FastTransformation)
                if pix.width() > w or pix.height() > h:
                    x = (pix.width()  - w) // 2
                    y = (pix.height() - h) // 2
                    pix = pix.copy(x, y, w, h)
                
                # Insert and check size bounds
                _THUMB_CACHE[resolved] = pix
                if len(_THUMB_CACHE) > _MAX_CACHE_SIZE:
                    _THUMB_CACHE.popitem(last=False)
                return pix
    except Exception as e:
        import logging
        logging.error(f"Error in get_cached_thumbnail for path {path}: {e}", exc_info=True)
    return None

def clear_thumbnail_cache():
    _THUMB_CACHE.clear()


class DishCard(QFrame):
    clicked          = pyqtSignal(dict)
    edit_requested   = pyqtSignal(dict)
    delete_requested = pyqtSignal(dict)

    def __init__(self, dish: dict, parent=None):
        super().__init__(parent)
        self._dish       = dish
        self._drag_start: QPoint | None = None
        self.setFixedSize(CARD_W, CARD_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(self._make_tooltip())
        self._build()
        self.set_selected(False)

    def set_dish(self, dish: dict):
        self._dish = dish
        self.setToolTip(self._make_tooltip())
        self._name_lbl.setText(dish["name"])
        self._load_thumb()
        
        cat    = dish.get("category", "")
        is_veg = bool(dish.get("is_veg", 1))
        dot    = "🟢" if is_veg else "🔴"
        c_bg   = "#22c55e" if is_veg else "#ef4444"
        self._chip_lbl.setText(f"{dot} {cat}" if cat else f"{dot}")
        self._chip_lbl.setStyleSheet(f"""
            background: {c_bg};
            color: #ffffff;
            font-size: 7px;
            font-weight: bold;
            border-radius: 5px;
            padding: 0 4px;
        """)
        self.set_selected(False)

    def _make_tooltip(self) -> str:
        d = self._dish
        tip = f"<b>{d.get('name', '')}</b>"
        if d.get("calories"):
            tip += f"<br>🔥 {d['calories']}"
        tip += f"<br>Category: {d.get('category', '—')}"
        return tip

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 2)
        lay.setSpacing(1)

        # Image
        self._img_lbl = QLabel()
        self._img_lbl.setFixedSize(CARD_W - 6, CARD_IMG_H)
        self._img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_lbl.setStyleSheet(
            "background: rgba(0,0,0,0.25); border-radius: 6px; color: #555; font-size: 18px;"
        )
        self._load_thumb()
        lay.addWidget(self._img_lbl)

        # Name
        self._name_lbl = QLabel(self._dish.get("name", ""))
        self._name_lbl.setWordWrap(True)
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        self._name_lbl.setStyleSheet("color: #e0e0e0; font-size: 8px; background: transparent;")
        self._name_lbl.setFixedHeight(22)
        lay.addWidget(self._name_lbl)

        # Veg/Non-veg chip — green for veg, red for non-veg (Indian convention)
        cat    = self._dish.get("category", "")
        is_veg = bool(self._dish.get("is_veg", 1))
        dot    = "🟢" if is_veg else "🔴"
        c_bg   = "#22c55e" if is_veg else "#ef4444"
        self._chip_lbl = QLabel(f"{dot} {cat}" if cat else f"{dot}")
        self._chip_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._chip_lbl.setFixedHeight(16)
        self._chip_lbl.setStyleSheet(f"""
            background: {c_bg};
            color: #ffffff;
            font-size: 7px;
            font-weight: bold;
            border-radius: 5px;
            padding: 0 4px;
        """)
        lay.addWidget(self._chip_lbl)


    def _load_thumb(self):
        path = self._dish.get("image_path", "")
        if path:
            w, h = CARD_W - 6, CARD_IMG_H
            pix = get_cached_thumbnail(path, w, h)
            if pix:
                self._img_lbl.setPixmap(pix)
                self._img_lbl.setStyleSheet("background: #1a1a1a; border-radius: 4px;")
                return
        self._img_lbl.setText("🍽")

    @staticmethod
    def _load_pixmap(path: str) -> QPixmap:
        """Load image via Qt; fall back to PIL for formats Qt can't handle (e.g. webp)."""
        pix = QPixmap(path)
        if not pix.isNull():
            return pix
        try:
            from PIL import Image
            import io
            img = Image.open(path).convert("RGBA")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            pix2 = QPixmap()
            pix2.loadFromData(buf.getvalue(), "PNG")
            return pix2
        except Exception as e:
            import logging
            logging.error(f"Error in _load_pixmap for path {path}: {e}", exc_info=True)
            return pix

    def set_selected(self, selected: bool):
        t      = thm.current()
        is_dk  = t["name"] == "dark"
        if selected:
            self.setStyleSheet(f"""
                DishCard {{
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                        stop:0 #1e3a5f, stop:1 #162840);
                    border: 1.5px solid {t['accent']};
                    border-top: 1.5px solid {t['accent_h']};
                    border-radius: 10px;
                }}
            """)
        else:
            glass = ("qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                     "stop:0 rgba(255,255,255,0.09),stop:1 rgba(255,255,255,0.03))"
                     if is_dk else
                     "qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                     "stop:0 rgba(255,255,255,0.95),stop:1 rgba(245,248,255,0.9))")
            glass_h = ("qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                       "stop:0 rgba(255,255,255,0.14),stop:1 rgba(255,255,255,0.06))"
                       if is_dk else
                       "rgba(240,245,255,0.95)")
            top_b   = "rgba(255,255,255,0.22)" if is_dk else "rgba(255,255,255,0.9)"
            self.setStyleSheet(f"""
                DishCard {{
                    background: {glass};
                    border: 1px solid {t['border_med']};
                    border-top: 1px solid {top_b};
                    border-radius: 10px;
                }}
                DishCard:hover {{
                    background: {glass_h};
                    border-color: {t['border_hi']};
                }}
            """)

    def refresh_theme(self):
        self.set_selected(False)
        t = thm.current()
        self._name_lbl.setStyleSheet(
            f"color: {t['text']}; font-size: 8px; background: transparent;"
        )

    # ── Mouse ──────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.pos()
            self.clicked.emit(self._dish)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start and (event.buttons() & Qt.MouseButton.LeftButton):
            if (event.pos() - self._drag_start).manhattanLength() > 8:
                self._start_drag()
        super().mouseMoveEvent(event)

    def contextMenuEvent(self, event):
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
            QMenu::separator {{ height: 1px; background: {t['border']}; margin: 3px 8px; }}
        """)
        edit_act   = menu.addAction("✏  Edit Dish…")
        menu.addSeparator()
        delete_act = menu.addAction("🗑  Delete Dish…")

        chosen = menu.exec(event.globalPos())
        if chosen == edit_act:
            self.edit_requested.emit(self._dish)
        elif chosen == delete_act:
            self.delete_requested.emit(self._dish)

    def _start_drag(self):
        name = self._dish["name"]
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        fm   = QFontMetrics(font)
        w    = min(fm.horizontalAdvance(name) + 48, 280)
        h    = 34

        pix = QPixmap(w, h)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = thm.current()
        p.setBrush(QBrush(QColor("#2a3f5f")))
        p.setPen(QPen(QColor(t["accent"]), 1.5))
        p.drawRoundedRect(0, 0, w - 1, h - 1, 8, 8)
        p.setPen(QPen(QColor("#ffffff")))
        p.setFont(font)
        p.drawText(QRect(12, 0, w - 16, h), Qt.AlignmentFlag.AlignVCenter, name[:34])
        p.end()

        # Create a custom premium drag copy cursor (arrow + green plus box)
        cursor_pix = QPixmap(32, 32)
        cursor_pix.fill(Qt.GlobalColor.transparent)
        cp = QPainter(cursor_pix)
        cp.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw arrow outline
        cp.setPen(QPen(Qt.GlobalColor.black, 1.5))
        cp.setBrush(QBrush(Qt.GlobalColor.white))
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(0, 17)
        path.lineTo(4, 13)
        path.lineTo(8, 21)
        path.lineTo(11, 19)
        path.lineTo(7, 12)
        path.lineTo(12, 12)
        path.closeSubpath()
        cp.drawPath(path)
        
        # Draw green plus box in the bottom right corner
        cp.setPen(QPen(QColor("#1b5e20"), 1))
        cp.setBrush(QBrush(QColor("#4caf50")))
        cp.drawRoundedRect(12, 12, 12, 12, 2, 2)
        
        # Plus symbol lines
        cp.setPen(QPen(Qt.GlobalColor.white, 2))
        cp.drawLine(18, 14, 18, 22)
        cp.drawLine(14, 18, 22, 18)
        cp.end()

        mime = QMimeData()
        mime.setText(name)
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(pix)
        drag.setHotSpot(QPoint(w // 2, h // 2))
        drag.setDragCursor(cursor_pix, Qt.DropAction.CopyAction)
        drag.exec(Qt.DropAction.CopyAction)


class DishGrid(QScrollArea):
    dish_selected = pyqtSignal(dict)
    edit_requested   = pyqtSignal(dict)
    delete_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._container = QWidget()
        self._grid_lay  = QGridLayout(self._container)
        self._grid_lay.setSpacing(CARD_GAP)
        self._grid_lay.setContentsMargins(DOCK_PAD, DOCK_PAD, DOCK_PAD, DOCK_PAD)
        self._grid_lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setWidget(self._container)

        self._cards: list[DishCard] = []
        self._selected_card: DishCard | None = None
        self._apply_theme()

    def _apply_theme(self):
        t = thm.current()
        self.setStyleSheet(f"""
            QScrollArea {{ background: {t['bg']}; border: none; }}
            QScrollBar:vertical {{
                background: {t['bg']}; width: 6px; border-radius: 3px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {t['scroll']}; border-radius: 3px; min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {t['scroll_h']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        self._container.setStyleSheet(f"background: {t['bg']};")

    def refresh_theme(self):
        self._apply_theme()
        for card in self._cards:
            card.refresh_theme()

    def populate(self, dishes: list[dict]):
        # Hide all existing cards and remove them from layout
        for card in self._cards:
            self._grid_lay.removeWidget(card)
            card.hide()
            
        self._selected_card = None
        
        # Instantiate more cards if needed
        while len(self._cards) < len(dishes):
            card = DishCard({"name": "", "category": "", "is_veg": 1})
            card.clicked.connect(self._on_card_clicked)
            card.edit_requested.connect(self.edit_requested)
            card.delete_requested.connect(self.delete_requested)
            self._cards.append(card)
            
        # Update, show and layout the required number of cards
        for i, dish in enumerate(dishes):
            card = self._cards[i]
            card.set_dish(dish)
            self._grid_lay.addWidget(card, i // COLS, i % COLS)
            card.show()

    def _on_card_clicked(self, dish: dict):
        if self._selected_card:
            self._selected_card.set_selected(False)
        for card in self._cards:
            if card._dish is dish:
                card.set_selected(True)
                self._selected_card = card
                break
        self.dish_selected.emit(dish)

    def clear_selection(self):
        if self._selected_card:
            self._selected_card.set_selected(False)
            self._selected_card = None


class DishDock(QWidget):
    dish_selected  = pyqtSignal(dict)
    dish_deleted   = pyqtSignal(str)          # emits dish name
    dish_edited    = pyqtSignal(str, str)     # emits old_name, new_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(DOCK_WIDTH)
        self._all_dishes: list[dict] = []
        self._filter   = "All"
        self._selected: dict | None = None

        # Debounce timer for search input
        from PyQt6.QtCore import QTimer
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(150)  # 150ms delay
        self._search_timer.timeout.connect(self._apply_filter)

        self._setup_ui()
        self._apply_theme()
        self.refresh_dishes()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        self._title_bar = QFrame()
        self._title_bar.setFixedHeight(50)
        tr = QHBoxLayout(self._title_bar)
        tr.setContentsMargins(14, 0, 14, 0)
        self._title_lbl = QLabel("Dish Library")
        self._title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        tr.addWidget(self._title_lbl)
        tr.addStretch()
        self.badge = QLabel("0")
        self.badge.setFixedSize(32, 20)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tr.addWidget(self.badge)
        layout.addWidget(self._title_bar)

        # Search + filter chips
        self._search_wrap = QFrame()
        sw = QVBoxLayout(self._search_wrap)
        sw.setContentsMargins(10, 8, 10, 8)
        sw.setSpacing(6)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search dishes…")
        self.search.setFixedHeight(32)
        self.search.textChanged.connect(self._on_search_changed)
        sw.addWidget(self.search)

        row1 = QHBoxLayout(); row1.setSpacing(4)
        row2 = QHBoxLayout(); row2.setSpacing(4)
        self._chip_btns: dict[str, QPushButton] = {}
        for idx, f in enumerate(FILTERS):
            b = QPushButton(f)
            b.setCheckable(True)
            b.setChecked(f == "All")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, flt=f: self._set_filter(flt))
            (row1 if idx < 6 else row2).addWidget(b)
            self._chip_btns[f] = b
        row1.addStretch(); row2.addStretch()
        sw.addLayout(row1); sw.addLayout(row2)
        layout.addWidget(self._search_wrap)

        # Drag hint
        self._hint = QLabel("  Drag to a grid cell  •  or click to select")
        self._hint.setFixedHeight(22)
        layout.addWidget(self._hint)

        # Grid
        self.grid = DishGrid()
        self.grid.dish_selected.connect(self._on_grid_select)
        self.grid.edit_requested.connect(self._on_edit_requested)
        self.grid.delete_requested.connect(self._on_delete_requested)
        layout.addWidget(self.grid, 1)

        # Selection label
        self.sel_lbl = QLabel("No dish selected")
        self.sel_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sel_lbl.setFixedHeight(24)
        layout.addWidget(self.sel_lbl)

        # Add button
        self.add_btn = QPushButton("+ Add Custom Dish")
        self.add_btn.setFixedHeight(40)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.add_btn)

    # ── Theme ──────────────────────────────────────────────────────────────────

    def _apply_theme(self):
        t = thm.current()
        self.setStyleSheet(
            f"DishDock {{ background: {t['bg']}; "
            f"border-right: 1px solid {t['border']}; }}"
        )
        is_dk  = t["name"] == "dark"
        ttl_bg = ("qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                  "stop:0 #1a1a2e,stop:1 #16213e)"
                  if is_dk else
                  "qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                  "stop:0 #f0f4ff,stop:1 #e8f0fe)")
        self._title_bar.setStyleSheet(
            f"QFrame {{ background: {ttl_bg}; "
            f"border-bottom: 1px solid {t['border']}; }}"
        )
        self._title_lbl.setStyleSheet(
            f"color: {t['text']}; background: transparent;"
        )
        self.badge.setStyleSheet(f"""
            background: {t['surface2']};
            color: {t['text2']};
            border-radius: 10px;
            font-size: 9px;
            font-weight: bold;
        """)
        self._search_wrap.setStyleSheet(
            f"QFrame {{ background: {t['surface']}; "
            f"border-bottom: 1px solid {t['border']}; }}"
        )
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background: {t['input_bg']};
                border: 1px solid {t['border_med']};
                border-radius: 6px;
                padding: 4px 10px;
                color: {t['text']};
                font-size: 11px;
            }}
            QLineEdit:focus {{ border-color: {t['accent']}; background: {t['input_bg_f']}; }}
        """)
        chip_qss = _chip_qss(t)
        for b in self._chip_btns.values():
            b.setStyleSheet(chip_qss)
        self._hint.setStyleSheet(f"""
            background: {t['surface2']};
            color: {t['text3']};
            font-size: 8px;
            font-style: italic;
            border-bottom: 1px solid {t['border']};
            padding-left: 6px;
        """)
        self.sel_lbl.setStyleSheet(
            f"background: {t['surface']}; color: {t['text3']}; "
            f"font-size: 8px; border-top: 1px solid {t['border']};"
        )
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {t['surface']};
                color: {t['accent']};
                font-size: 11px;
                font-weight: bold;
                border: none;
                border-top: 1px solid {t['border']};
                border-radius: 0;
            }}
            QPushButton:hover {{ background: {t['surface2']}; }}
            QPushButton:pressed {{ background: {t['surface3']}; }}
        """)
        self.grid._apply_theme()

    def refresh_theme(self):
        self._apply_theme()
        self.grid.refresh_theme()
        self._refresh_sel_label()

    # ── Data ───────────────────────────────────────────────────────────────────

    def refresh_dishes(self):
        clear_thumbnail_cache()
        self._all_dishes = db.get_all_dishes()
        self._apply_filter()

    def _set_filter(self, flt: str):
        self._filter = flt
        for f, b in self._chip_btns.items():
            b.setChecked(f == flt)
        self._apply_filter()

    def _on_search_changed(self):
        self._search_timer.start()

    def _apply_filter(self):
        q        = self.search.text().strip().lower()
        filtered = []
        for d in self._all_dishes:
            if q and q not in d["name"].lower():
                continue
            if self._filter == "Veg"     and not d.get("is_veg", 1):
                continue
            if self._filter == "Non-Veg" and d.get("is_veg", 1):
                continue
            if self._filter == "Custom"  and not d.get("is_custom"):
                continue
            if self._filter not in ("All", "Veg", "Non-Veg", "Custom") \
               and d.get("category", "") != self._filter:
                continue
            filtered.append(d)
        self.grid.populate(filtered)
        self.badge.setText(str(len(filtered)))
        self._refresh_sel_label()

    # ── Signals ────────────────────────────────────────────────────────────────

    def _on_grid_select(self, dish: dict):
        self._selected = dish
        self.dish_selected.emit(dish)
        self._refresh_sel_label()

    def _on_edit_requested(self, dish: dict):
        from ui.dialogs import AddDishDialog
        dlg = AddDishDialog(self, dish=dish)
        if dlg.exec():
            old_name = dish["name"]
            new_name = dlg.get_dish_name()
            self.dish_edited.emit(old_name, new_name)
            self.refresh_dishes()

    def _on_delete_requested(self, dish: dict):
        name  = dish["name"]
        usage = db.get_dish_usage(name)
        t     = thm.current()

        msg = QMessageBox(self)
        msg.setWindowTitle("Delete Dish")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(f"Delete  \"{name}\"?")
        if usage:
            weeks = len({u["week_start"] for u in usage})
            msg.setInformativeText(
                f"This dish appears in {len(usage)} slot(s) across {weeks} week plan(s). "
                f"Those slots will be cleared."
            )
        else:
            msg.setInformativeText("This action cannot be undone.")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Ok
        )
        msg.button(QMessageBox.StandardButton.Ok).setText("Delete")
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)

        if msg.exec() == QMessageBox.StandardButton.Ok:
            db.delete_dish(name)
            if self._selected and self._selected.get("name") == name:
                self._selected = None
            self.dish_deleted.emit(name)
            self.refresh_dishes()

    def _refresh_sel_label(self):
        t = thm.current()
        if self._selected:
            self.sel_lbl.setText(f"Selected: {self._selected['name']}")
            self.sel_lbl.setStyleSheet(f"""
                background: rgba(74,158,255,0.08);
                color: {t['accent']};
                font-size: 8px;
                font-weight: bold;
                border-top: 1px solid rgba(74,158,255,0.2);
            """)
        else:
            self.sel_lbl.setText("No dish selected")
            self.sel_lbl.setStyleSheet(
                f"background: {t['surface']}; color: {t['text3']}; "
                f"font-size: 8px; border-top: 1px solid {t['border']};"
            )

    def get_selected_dish(self) -> dict | None: return self._selected

    def clear_selection(self):
        self._selected = None
        self.grid.clear_selection()
        self._refresh_sel_label()

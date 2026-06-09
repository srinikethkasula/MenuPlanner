"""
ui/dialogs.py — All dialogs. Dark glassmorphism style.
Includes ExportDialog (unified PPT + Excel export with day/folder selection).
"""
from __future__ import annotations
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QWidget, QAbstractItemView, QFrame, QCheckBox,
    QButtonGroup, QApplication, QProgressBar, QScrollArea,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

import database as db
from nutrition.fetcher import fetch_nutrition


# ── Shared style helpers ──────────────────────────────────────────────────────

_DLG_BASE = ""
_BTN_PRIMARY = ""
_BTN_SECONDARY = ""


def _section_bar(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFixedHeight(32)
    lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
    lbl.setProperty("section_bar", True)
    return lbl


def _dialog_header(icon: str, title: str, subtitle: str = "") -> QFrame:
    f = QFrame()
    f.setFixedHeight(68 if subtitle else 54)
    f.setProperty("dialog_header", True)
    hl = QHBoxLayout(f)
    hl.setContentsMargins(16, 0, 16, 0)
    hl.setSpacing(12)

    ico = QLabel(icon)
    ico.setFont(QFont("Segoe UI", 22))
    ico.setFixedWidth(36)
    hl.addWidget(ico)

    txt_col = QVBoxLayout()
    txt_col.setSpacing(2)
    tl = QLabel(title)
    tl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
    tl.setProperty("header_title", True)
    txt_col.addWidget(tl)
    if subtitle:
        sl = QLabel(subtitle)
        sl.setProperty("header_subtitle", True)
        txt_col.addWidget(sl)
    hl.addLayout(txt_col)
    hl.addStretch()
    return f


# ── Export Dialog ─────────────────────────────────────────────────────────────

class ExportDialog(QDialog):
    """
    Unified export hub.
    Select days → select formats (PPT / Excel) → pick folder → export.
    """

    def __init__(self, parent, grid, dishes_db: dict):
        super().__init__(parent)
        self.setWindowTitle("Export Menu")
        self.setFixedSize(540, 520)
        self.setStyleSheet(_DLG_BASE)
        self._grid = grid
        self._dishes_db = dishes_db
        self._out_folder = Path.home() / "Documents"
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        root.addWidget(_dialog_header(
            "📤", "Export Menu",
            "Choose days, formats, and save location"
        ))

        # ── Day selection ─────────────────────────────────────────────────────
        root.addWidget(_section_bar("  📅  Select Days to Export"))

        day_frame = QFrame()
        day_frame.setProperty("dialog_box", True)
        day_layout = QVBoxLayout(day_frame)
        day_layout.setContentsMargins(12, 10, 12, 10)
        day_layout.setSpacing(8)

        # Select All row
        sel_row = QHBoxLayout()
        self._sel_all = QCheckBox("Select All")
        self._sel_all.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._sel_all.setStyleSheet("QCheckBox { color: #4a9eff; font-weight: bold; }")
        self._sel_all.stateChanged.connect(self._toggle_all)
        sel_row.addWidget(self._sel_all)
        sel_row.addStretch()
        day_layout.addLayout(sel_row)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setProperty("dialog_divider", True)
        day_layout.addWidget(div)

        # Day checkboxes
        days_row = QHBoxLayout()
        days_row.setSpacing(10)
        self._day_checks: dict[str, QCheckBox] = {}
        day_labels = {"MONDAY": "Mon", "TUESDAY": "Tue", "WEDNESDAY": "Wed",
                      "THURSDAY": "Thu", "FRIDAY": "Fri"}
        for day, short in day_labels.items():
            cb = QCheckBox(short)
            cb.setChecked(True)
            cb.stateChanged.connect(self._sync_sel_all)
            days_row.addWidget(cb)
            self._day_checks[day] = cb
        days_row.addStretch()
        day_layout.addLayout(days_row)
        root.addWidget(day_frame)
        self._sync_sel_all()

        # ── Format selection ──────────────────────────────────────────────────
        root.addWidget(_section_bar("  📄  Export Format"))

        fmt_frame = QFrame()
        fmt_frame.setProperty("dialog_box", True)
        fmt_layout = QHBoxLayout(fmt_frame)
        fmt_layout.setContentsMargins(16, 12, 16, 12)
        fmt_layout.setSpacing(24)

        self._ppt_cb = QCheckBox("  🖥  PowerPoint (.pptx)\n  One file per selected day")
        self._ppt_cb.setChecked(True)
        self._ppt_cb.setFont(QFont("Segoe UI", 11))

        self._xl_cb = QCheckBox("  📊  Excel (.xlsx)\n  Full week in one file")
        self._xl_cb.setChecked(True)
        self._xl_cb.setFont(QFont("Segoe UI", 11))

        fmt_layout.addWidget(self._ppt_cb)
        fmt_layout.addWidget(self._xl_cb)
        fmt_layout.addStretch()
        root.addWidget(fmt_frame)

        # ── Save location ─────────────────────────────────────────────────────
        root.addWidget(_section_bar("  📁  Save Location"))

        loc_row = QHBoxLayout()
        loc_row.setSpacing(8)
        self._folder_lbl = QLineEdit(str(self._out_folder))
        self._folder_lbl.setReadOnly(True)
        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedHeight(36)
        browse_btn.setFixedWidth(100)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._pick_folder)
        loc_row.addWidget(self._folder_lbl, 1)
        loc_row.addWidget(browse_btn)
        root.addLayout(loc_row)

        # ── Progress / results ────────────────────────────────────────────────
        self._results_frame = QFrame()
        self._results_frame.setProperty("dialog_box", True)
        self._results_layout = QVBoxLayout(self._results_frame)
        self._results_layout.setContentsMargins(12, 10, 12, 10)
        self._results_layout.setSpacing(4)
        self._results_frame.hide()
        root.addWidget(self._results_frame)

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._export_btn = QPushButton("▶  Export Now")
        self._export_btn.setProperty("primary", True)
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.clicked.connect(self._run_export)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        self._done_btn = QPushButton("✓  Done")
        self._done_btn.setProperty("primary", True)
        self._done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._done_btn.clicked.connect(self.accept)
        self._done_btn.hide()

        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._export_btn)
        btn_row.addWidget(self._done_btn)
        root.addLayout(btn_row)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _toggle_all(self, state: int):
        checked = bool(state)
        for cb in self._day_checks.values():
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)

    def _sync_sel_all(self):
        all_on = all(cb.isChecked() for cb in self._day_checks.values())
        self._sel_all.blockSignals(True)
        self._sel_all.setChecked(all_on)
        self._sel_all.blockSignals(False)

    def _pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Folder",
                                                   str(self._out_folder))
        if folder:
            self._out_folder = Path(folder)
            self._folder_lbl.setText(str(self._out_folder))

    def _add_result_row(self, icon: str, text: str, ok: bool):
        color = "#4CAF50" if ok else "#FF5722"
        lbl = QLabel(f"{icon}  {text}")
        lbl.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")
        self._results_layout.addWidget(lbl)

    # ── Export logic ──────────────────────────────────────────────────────────

    def _run_export(self):
        selected_days = [d for d, cb in self._day_checks.items() if cb.isChecked()]
        do_ppt = self._ppt_cb.isChecked()
        do_xl  = self._xl_cb.isChecked()

        if not selected_days:
            QMessageBox.warning(self, "No Days", "Select at least one day to export.")
            return
        if not do_ppt and not do_xl:
            QMessageBox.warning(self, "No Format", "Select at least one export format.")
            return

        self._out_folder.mkdir(parents=True, exist_ok=True)
        self._export_btn.setEnabled(False)
        self._export_btn.setText("⏳  Exporting…")

        # Clear previous results
        while self._results_layout.count():
            w = self._results_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._results_frame.show()

        plan_id    = self._grid.get_plan_id()
        week_start = self._grid.get_week_start()
        custom     = db.get_custom_slides(plan_id) if plan_id else []
        co_name    = db.get_setting("company_name")
        ca_name    = db.get_setting("canteen_name")
        welcome    = db.get_setting("welcome_text")
        co_img     = db.get_setting("company_image")
        team_photo = db.get_setting("team_photo")

        # ── PPT: one file per day ─────────────────────────────────────────────
        if do_ppt:
            from export.pptx_gen import export_pptx
            from datetime import timedelta
            day_offsets = {"MONDAY": 0, "TUESDAY": 1, "WEDNESDAY": 2, "THURSDAY": 3, "FRIDAY": 4}
            for day in selected_days:
                day_data = self._grid.get_day_data(day)
                offset = day_offsets.get(day.upper(), 0)
                day_date = week_start + timedelta(days=offset)
                date_str = day_date.strftime("%d %B %y")  # e.g., "01 June 26"
                fname = f"{date_str} {day.lower().capitalize()} Menu.pptx"
                out   = self._out_folder / fname
                try:
                    export_pptx(
                        week_data={day: day_data},
                        day=day,
                        week_start=week_start,
                        dishes_db=self._dishes_db,
                        output_path=out,
                        company_name=co_name,
                        canteen_name=ca_name,
                        welcome_text=welcome,
                        company_image=co_img,
                        team_photo=team_photo,
                        custom_slides=custom,
                    )
                    self._add_result_row("📊", f"{fname}  —  saved", True)
                except Exception as e:
                    self._add_result_row("❌", f"{fname}  —  {e}", False)
                QApplication.processEvents()

        # ── Excel: one file for the full week ─────────────────────────────────
        if do_xl:
            from export.xlsx_export import export_xlsx
            from datetime import timedelta
            week_data = db.get_week_data(plan_id) if plan_id else {}
            
            start_date = week_start
            end_date = week_start + timedelta(days=4)
            if start_date.month == end_date.month:
                start_str = start_date.strftime("%d")
                end_str = end_date.strftime("%d %B %y")
            else:
                start_str = start_date.strftime("%d %B")
                end_str = end_date.strftime("%d %B %y")
            fname = f"Weekly Menu {start_str} to {end_str}.xlsx"
            out   = self._out_folder / fname
            try:
                export_xlsx(
                    week_data=week_data,
                    week_start=week_start,
                    output_path=out,
                    company_name=co_name,
                    canteen_name=ca_name,
                )
                self._add_result_row("📊", f"{fname}  —  saved", True)
            except Exception as e:
                self._add_result_row("❌", f"{fname}  —  {e}", False)

        # Footer summary
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(212,160,23,0.15);")
        self._results_layout.addWidget(sep)
        loc_lbl = QLabel(f"📁  {self._out_folder}")
        loc_lbl.setStyleSheet("color: #D4A017; font-size: 10px; background: transparent;")
        self._results_layout.addWidget(loc_lbl)

        self._export_btn.hide()
        self._done_btn.show()
        self.adjustSize()


# ── Nutrition fetch thread ────────────────────────────────────────────────────

class FetchThread(QThread):
    result = pyqtSignal(dict)

    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def run(self):
        self.result.emit(fetch_nutrition(self.name))


# ── Add Dish Dialog ───────────────────────────────────────────────────────────

class AddDishDialog(QDialog):
    """
    Create or edit a dish.
    Pass dish=<dict> to open in edit mode with prepopulated fields.
    """

    def __init__(self, parent=None, prefill_name: str = "", dish: dict | None = None):
        super().__init__(parent)
        self._edit_dish = dish
        self._old_name  = dish["name"] if dish else ""
        self.setWindowTitle("Edit Dish" if dish else "Add Custom Dish")
        self.setFixedSize(520, 700)
        self.setStyleSheet(_DLG_BASE)
        self._thread = None
        self._setup_ui(dish["name"] if dish else prefill_name)

    def _setup_ui(self, prefill: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        if self._edit_dish:
            root.addWidget(_dialog_header("✏", "Edit Dish",
                                           "Update details for this dish"))
        else:
            root.addWidget(_dialog_header("🍽", "Add Custom Dish",
                                           "Enter details and auto-fetch nutrition"))

        # Name + fetch
        root.addWidget(_section_bar("  Dish Name"))
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        self.name_edit = QLineEdit(prefill)
        self.name_edit.setPlaceholderText("Enter dish name…")
        self.name_edit.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.name_edit.setFixedHeight(36)
        self._fetch_btn = QPushButton("🔍  Auto-Fetch")
        self._fetch_btn.setFixedHeight(36)
        self._fetch_btn.setFixedWidth(140)
        self._fetch_btn.setProperty("primary", True)
        self._fetch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fetch_btn.clicked.connect(self._auto_fetch)
        name_row.addWidget(self.name_edit, 1)
        name_row.addWidget(self._fetch_btn)
        root.addLayout(name_row)

        self._status = QLabel("")
        self._status.setProperty("header_subtitle", True)
        root.addWidget(self._status)

        # Nutrition
        root.addWidget(_section_bar("  🔥  Nutrition Info  (optional)"))
        grid_w = QWidget()
        from PyQt6.QtWidgets import QGridLayout
        g = QGridLayout(grid_w)
        g.setSpacing(8)
        g.setContentsMargins(0, 0, 0, 0)

        self.cal_edit   = QLineEdit(); self.cal_edit.setPlaceholderText("e.g. 250 – 280 kcal")
        self.prot_edit  = QLineEdit(); self.prot_edit.setPlaceholderText("e.g. 12 – 15 grams")
        self.carbs_edit = QLineEdit(); self.carbs_edit.setPlaceholderText("e.g. 30 – 35 grams")
        self.fat_edit   = QLineEdit(); self.fat_edit.setPlaceholderText("e.g. 8 – 10 grams")
        self.fiber_edit = QLineEdit(); self.fiber_edit.setPlaceholderText("e.g. 2 – 4 grams")

        pairs = [
            ("🔥 Calories", self.cal_edit,   "🥩 Protein",  self.prot_edit),
            ("🌾 Carbs",    self.carbs_edit,  "🫒 Fat",      self.fat_edit),
            ("🌿 Fiber",    self.fiber_edit,  "",             None),
        ]
        for r, (l1, w1, l2, w2) in enumerate(pairs):
            lbl1 = QLabel(l1)
            g.addWidget(lbl1, r, 0)
            g.addWidget(w1, r, 1)
            if l2:
                lbl2 = QLabel(l2)
                g.addWidget(lbl2, r, 2)
            if w2:
                g.addWidget(w2, r, 3)
        root.addWidget(grid_w)

        # Category + Veg/Non-Veg
        root.addWidget(_section_bar("  Category & Diet Type"))
        cat_row = QHBoxLayout()
        cat_lbl = QLabel("Category:")
        cat_lbl.setFixedWidth(80)
        from PyQt6.QtWidgets import QComboBox, QRadioButton, QButtonGroup
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["Breakfast", "Lunch", "Snacks", "Juice", "Soup", "Additionals", "Fruit Lunch", "Dessert"])
        cat_row.addWidget(cat_lbl)
        cat_row.addWidget(self.cat_combo, 1)
        root.addLayout(cat_row)

        veg_row = QHBoxLayout()
        veg_lbl = QLabel("Diet:")
        veg_lbl.setFixedWidth(80)
        self._veg_btn    = QRadioButton("🟢  Vegetarian")
        self._nonveg_btn = QRadioButton("🔴  Non-Vegetarian")
        self._veg_btn.setChecked(True)
        self._veg_btn.setStyleSheet("color: #22c55e; font-weight: bold;")
        self._nonveg_btn.setStyleSheet("color: #ef4444; font-weight: bold;")
        self._diet_grp = QButtonGroup(self)
        self._diet_grp.addButton(self._veg_btn,    1)
        self._diet_grp.addButton(self._nonveg_btn, 0)
        veg_row.addWidget(veg_lbl)
        veg_row.addWidget(self._veg_btn)
        veg_row.addWidget(self._nonveg_btn)
        veg_row.addStretch()
        root.addLayout(veg_row)

        # Image
        root.addWidget(_section_bar("  Image  (optional)"))
        img_row = QHBoxLayout()
        self.img_edit = QLineEdit()
        self.img_edit.setPlaceholderText("Image file path…")
        browse = QPushButton("Browse…")
        browse.setFixedWidth(100)
        browse.clicked.connect(self._browse_img)
        img_row.addWidget(self.img_edit, 1)
        img_row.addWidget(browse)
        root.addLayout(img_row)

        # Prefill fields in edit mode
        if self._edit_dish:
            d = self._edit_dish
            self.cal_edit.setText(d.get("calories", "") or "")
            self.prot_edit.setText(d.get("protein", "") or "")
            self.carbs_edit.setText(d.get("carbs", "") or "")
            self.fat_edit.setText(d.get("fat", "") or "")
            self.fiber_edit.setText(d.get("fiber", "") or "")
            self.img_edit.setText(d.get("image_path", "") or "")
            cat = d.get("category", "")
            idx = self.cat_combo.findText(cat)
            if idx >= 0:
                self.cat_combo.setCurrentIndex(idx)
            if not d.get("is_veg", 1):
                self._nonveg_btn.setChecked(True)
            else:
                self._veg_btn.setChecked(True)

        # Buttons
        root.addSpacing(4)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        save_label = "✓  Save Dish"
        save = QPushButton(save_label)
        save.setProperty("primary", True)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        root.addLayout(btn_row)

    def _browse_img(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select Image", "",
                                            "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if p:
            self.img_edit.setText(p)

    def _auto_fetch(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Enter a dish name first.")
            return
        self._fetch_btn.setText("⏳  Fetching…")
        self._fetch_btn.setEnabled(False)
        self._status.setText("Querying Open Food Facts…")
        self._thread = FetchThread(name)
        self._thread.result.connect(self._on_fetch)
        self._thread.start()

    def _on_fetch(self, data: dict):
        self._fetch_btn.setText("🔍  Auto-Fetch")
        self._fetch_btn.setEnabled(True)
        found = any(data.values())
        self._status.setText("✓ Fetched!" if found else "⚠ No data — fill manually.")
        if data.get("calories"):  self.cal_edit.setText(data["calories"])
        if data.get("protein"):   self.prot_edit.setText(data["protein"])
        if data.get("carbs"):     self.carbs_edit.setText(data["carbs"])
        if data.get("fat"):       self.fat_edit.setText(data["fat"])
        if data.get("fiber"):     self.fiber_edit.setText(data["fiber"])

    def _accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Dish name is required.")
            return
        is_veg = 1 if self._veg_btn.isChecked() else 0
        if self._edit_dish:
            db.update_dish(
                self._old_name,
                name=name,
                calories=self.cal_edit.text().strip(),
                protein=self.prot_edit.text().strip(),
                carbs=self.carbs_edit.text().strip(),
                fat=self.fat_edit.text().strip(),
                fiber=self.fiber_edit.text().strip(),
                image_path=self.img_edit.text().strip(),
                category=self.cat_combo.currentText(),
                is_veg=is_veg,
            )
        else:
            db.add_dish(
                name=name,
                calories=self.cal_edit.text().strip(),
                protein=self.prot_edit.text().strip(),
                carbs=self.carbs_edit.text().strip(),
                fat=self.fat_edit.text().strip(),
                fiber=self.fiber_edit.text().strip(),
                image_path=self.img_edit.text().strip(),
                category=self.cat_combo.currentText(),
                is_veg=is_veg,
            )
        self.accept()

    def get_dish_name(self) -> str:
        return self.name_edit.text().strip()

    def get_old_name(self) -> str:
        return self._old_name


# ── Settings Dialog ───────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(520, 420)
        self.setStyleSheet(_DLG_BASE)
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        root.addWidget(_dialog_header("⚙", "Application Settings"))

        root.addWidget(_section_bar("  Company & Canteen"))
        self.company_edit = QLineEdit()
        self.canteen_edit  = QLineEdit()
        self.welcome_edit  = QLineEdit()
        for lbl_txt, w, ph in [
            ("Company Name",    self.company_edit, "Chathradhari Caterers"),
            ("Canteen Name",    self.canteen_edit,  "Oyster"),
            ("Welcome Message", self.welcome_edit,  "Welcome to Oyster"),
        ]:
            row = QHBoxLayout()
            l = QLabel(lbl_txt)
            l.setFixedWidth(140)
            w.setPlaceholderText(ph)
            row.addWidget(l)
            row.addWidget(w, 1)
            root.addLayout(row)

        root.addWidget(_section_bar("  🖼  Closing Slide Images"))
        self.co_img_edit   = QLineEdit()
        self.team_img_edit = QLineEdit()
        for lbl_txt, w, ph in [
            ("Company Image", self.co_img_edit,   "Left side of closing slide"),
            ("Team Photo",    self.team_img_edit,  "Right side of closing slide"),
        ]:
            row = QHBoxLayout()
            l = QLabel(lbl_txt)
            l.setFixedWidth(140)
            w.setPlaceholderText(ph)
            btn = QPushButton("Browse…")
            btn.setFixedWidth(90)
            btn.clicked.connect(lambda _, widget=w: self._browse(widget))
            row.addWidget(l)
            row.addWidget(w, 1)
            row.addWidget(btn)
            root.addLayout(row)

        root.addSpacing(4)
        btn_row = QHBoxLayout()
        save = QPushButton("✓  Save Settings")
        save.setProperty("primary", True)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self._save)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        root.addLayout(btn_row)

    def _browse(self, edit: QLineEdit):
        p, _ = QFileDialog.getOpenFileName(self, "Select Image", "",
                                            "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if p:
            edit.setText(p)

    def _load(self):
        self.company_edit.setText(db.get_setting("company_name"))
        self.canteen_edit.setText(db.get_setting("canteen_name"))
        self.welcome_edit.setText(db.get_setting("welcome_text"))
        
        co_img = db.get_setting("company_image")
        team_photo = db.get_setting("team_photo")
        self.co_img_edit.setText(db.resolve_image_path(co_img) if co_img else "")
        self.team_img_edit.setText(db.resolve_image_path(team_photo) if team_photo else "")

    def _save(self):
        co_img_path = self.co_img_edit.text().strip()
        team_img_path = self.team_img_edit.text().strip()
        
        # Copy settings images if they are absolute paths
        co_img_saved = db.copy_settings_image(co_img_path)
        team_img_saved = db.copy_settings_image(team_img_path)
        
        db.set_setting("company_name",  self.company_edit.text().strip())
        db.set_setting("canteen_name",  self.canteen_edit.text().strip())
        db.set_setting("welcome_text",  self.welcome_edit.text().strip())
        db.set_setting("company_image", co_img_saved)
        db.set_setting("team_photo",    team_img_saved)
        self.accept()


# ── Image Manager ─────────────────────────────────────────────────────────────

class ImageManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Manager")
        self.setFixedSize(760, 560)
        self.setStyleSheet(_DLG_BASE)
        self._dishes = []
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        root.addWidget(_dialog_header("🖼", "Dish Image Manager",
                                      "Double-click a row to assign an image"))

        toolbar = QHBoxLayout()
        bulk = QPushButton("📂  Assign from Folder…")
        bulk.clicked.connect(self._bulk)
        ref = QPushButton("↻  Refresh")
        ref.clicked.connect(self._load)
        toolbar.addWidget(bulk)
        toolbar.addWidget(ref)
        toolbar.addStretch()
        root.addLayout(toolbar)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Dish Name", "Image Path", "✓"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(2, 42)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self._individual)
        root.addWidget(self.table)

        close = QPushButton("Close")
        close.setProperty("primary", True)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self.accept)
        root.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)

    def _load(self):
        self._dishes = db.get_all_dishes()
        self.table.setRowCount(len(self._dishes))
        from database import resolve_image_path
        for r, d in enumerate(self._dishes):
            self.table.setItem(r, 0, QTableWidgetItem(d["name"]))
            self.table.setItem(r, 1, QTableWidgetItem(d.get("image_path", "")))
            resolved = resolve_image_path(d.get("image_path", ""))
            has = bool(resolved) and Path(resolved).exists()
            st = QTableWidgetItem("✓" if has else "✗")
            st.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            st.setForeground(QColor("#4CAF50") if has else QColor("#FF5722"))
            self.table.setItem(r, 2, st)

    def _individual(self, idx):
        d = self._dishes[idx.row()]
        p, _ = QFileDialog.getOpenFileName(self, f"Image for {d['name']}", "",
                                            "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if p:
            db.update_dish_image(d["name"], p)
            self._load()

    def _bulk(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if not folder:
            return
        fp = Path(folder)
        matched = 0
        for d in self._dishes:
            for ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                for stem in (d["name"].lower().replace(" ", "_"), d["name"]):
                    c = fp / f"{stem}{ext}"
                    if c.exists():
                        db.update_dish_image(d["name"], str(c))
                        matched += 1
                        break
        QMessageBox.information(self, "Done", f"Matched {matched} dish images.")
        self._load()

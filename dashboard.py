import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QDate
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QBrush,
    QPixmap,
    QIcon,
    QFont,
    QCursor,
)
from PyQt6.QtWidgets import (
    QWidget,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QProgressBar,
    QGraphicsDropShadowEffect,
    QStackedWidget,
    QLineEdit,
    QComboBox,
    QDialog,
    QDateEdit,
    QMessageBox,
    QGridLayout,
)

import config
from firestore_sync import FirestoreSyncService
from widget import NeonCheckBox, StreakBadge, create_neon_icon


class GlassCard(QFrame):
    """Elevated dark zinc card with subtle neon border."""
    def __init__(self, parent=None, active_hover=True):
        super().__init__(parent)
        self.active_hover = active_hover
        self._apply_style()

    def _apply_style(self):
        hover_css = f"""
            GlassCard:hover {{
                border: 1px solid {config.COLOR_NEON_GREEN};
                background-color: #1A1A1E;
            }}
        """ if self.active_hover else ""

        self.setStyleSheet(f"""
            GlassCard {{
                background-color: {config.COLOR_DARK_ZINC};
                border: 1px solid #27272A;
                border-radius: 12px;
            }}
            {hover_css}
        """)


class AddHabitDialog(QDialog):
    """Dialog to create a new habit."""
    def __init__(self, groups: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Habit")
        self.setFixedSize(380, 320)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {config.COLOR_PITCH_BLACK};
                border: 1px solid {config.COLOR_NEON_GREEN};
                border-radius: 12px;
            }}
            QLabel {{
                color: {config.COLOR_CRISP_WHITE};
                font-size: 12px;
                font-weight: 600;
            }}
            QLineEdit, QComboBox {{
                background-color: {config.COLOR_DARK_ZINC};
                color: {config.COLOR_CRISP_WHITE};
                border: 1px solid #3F3F46;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {config.COLOR_NEON_GREEN};
            }}
            QPushButton {{
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 700;
                font-size: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # Title
        header = QLabel("⚡ New Habit")
        header.setStyleSheet(f"color: {config.COLOR_NEON_GREEN}; font-size: 18px; font-weight: 800;")
        layout.addWidget(header)

        # Name
        layout.addWidget(QLabel("Habit Title:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. Read 20 Pages, Drink 3L Water")
        layout.addWidget(self.title_input)

        # Group / Routine
        layout.addWidget(QLabel("Group / Routine:"))
        self.group_combo = QComboBox()
        self.group_combo.addItem("General")
        for g in groups:
            self.group_combo.addItem(g.get("name", "Group"))
        self.group_combo.setEditable(True)
        layout.addWidget(self.group_combo)

        # Frequency
        layout.addWidget(QLabel("Cadence:"))
        self.freq_combo = QComboBox()
        self.freq_combo.addItems(["Daily", "Weekly"])
        layout.addWidget(self.freq_combo)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            background-color: #27272A;
            color: #A1A1AA;
            border: none;
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Create Habit")
        save_btn.setStyleSheet(f"""
            background-color: {config.COLOR_NEON_GREEN};
            color: {config.COLOR_PITCH_BLACK};
            border: none;
        """)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def get_data(self):
        return {
            "title": self.title_input.text().strip(),
            "group": self.group_combo.currentText().strip(),
            "frequency": self.freq_combo.currentText().lower(),
        }


class AddGoalDialog(QDialog):
    """Dialog to create a long-term goal."""
    def __init__(self, habits: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Long-Term Goal")
        self.setFixedSize(420, 440)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {config.COLOR_PITCH_BLACK};
                border: 1px solid {config.COLOR_NEON_GREEN};
                border-radius: 12px;
            }}
            QLabel {{
                color: {config.COLOR_CRISP_WHITE};
                font-size: 11px;
                font-weight: 600;
            }}
            QLineEdit, QComboBox, QDateEdit {{
                background-color: {config.COLOR_DARK_ZINC};
                color: {config.COLOR_CRISP_WHITE};
                border: 1px solid #3F3F46;
                border-radius: 8px;
                padding: 7px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{
                border: 1px solid {config.COLOR_NEON_GREEN};
            }}
            QPushButton {{
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 700;
                font-size: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header = QLabel("🎯 New Long-Term Goal")
        header.setStyleSheet(f"color: {config.COLOR_NEON_GREEN}; font-size: 18px; font-weight: 800;")
        layout.addWidget(header)

        layout.addWidget(QLabel("Goal Objective:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. Run 100km Total, Read 24 Books")
        layout.addWidget(self.title_input)

        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["Fitness", "Learning", "Career & Coding", "Health", "Financial", "Personal"])
        self.category_combo.setEditable(True)
        layout.addWidget(self.category_combo)

        # Numbers
        num_layout = QHBoxLayout()
        v1 = QVBoxLayout()
        v1.addWidget(QLabel("Current:"))
        self.curr_input = QLineEdit("0")
        v1.addWidget(self.curr_input)
        num_layout.addLayout(v1)

        v2 = QVBoxLayout()
        v2.addWidget(QLabel("Target:"))
        self.target_input = QLineEdit("100")
        v2.addWidget(self.target_input)
        num_layout.addLayout(v2)

        v3 = QVBoxLayout()
        v3.addWidget(QLabel("Unit:"))
        self.unit_input = QLineEdit("km")
        v3.addWidget(self.unit_input)
        num_layout.addLayout(v3)
        layout.addLayout(num_layout)

        # Deadline
        layout.addWidget(QLabel("Target Deadline:"))
        self.deadline_edit = QDateEdit()
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDate(QDate.currentDate().addDays(90))
        layout.addWidget(self.deadline_edit)

        # Linked Habit
        layout.addWidget(QLabel("Link to Habit (Auto-advances on completion):"))
        self.habit_combo = QComboBox()
        self.habit_combo.addItem("None (Manual Tracking)")
        for h in habits:
            self.habit_combo.addItem(h.get("cleanTitle", h.get("title", "")))
        layout.addWidget(self.habit_combo)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #27272A; color: #A1A1AA; border: none;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Goal")
        save_btn.setStyleSheet(f"background-color: {config.COLOR_NEON_GREEN}; color: {config.COLOR_PITCH_BLACK}; border: none;")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def get_data(self):
        linked = self.habit_combo.currentText()
        if linked == "None (Manual Tracking)":
            linked = ""
        try:
            curr = float(self.curr_input.text() or 0)
            target = float(self.target_input.text() or 1)
        except ValueError:
            curr, target = 0, 100

        return {
            "title": self.title_input.text().strip() or "Untitled Goal",
            "category": self.category_combo.currentText(),
            "currentValue": curr,
            "targetValue": target,
            "unit": self.unit_input.text().strip() or "units",
            "deadline": self.deadline_edit.date().toString("yyyy-MM-dd"),
            "linkedHabitTitle": linked,
            "completed": curr >= target,
        }


class GoalCard(GlassCard):
    """Card representing a long-term goal with progress tracker."""
    progress_changed = pyqtSignal(str, float)
    goal_deleted = pyqtSignal(str)

    def __init__(self, goal: Dict[str, Any], parent=None):
        super().__init__(parent, active_hover=True)
        self.goal = goal
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header: Category tag & delete button
        top_row = QHBoxLayout()
        cat_badge = QLabel(self.goal.get("category", "General").upper())
        cat_badge.setStyleSheet(f"""
            background-color: rgba(57, 255, 20, 0.1);
            color: {config.COLOR_NEON_GREEN};
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 9px;
            font-weight: 700;
        """)
        top_row.addWidget(cat_badge)

        top_row.addStretch()

        deadline = self.goal.get("deadline", "")
        if deadline:
            date_lbl = QLabel(f"Target: {deadline}")
            date_lbl.setStyleSheet("color: #71717A; font-size: 10px;")
            top_row.addWidget(date_lbl)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(18, 18)
        del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        del_btn.setStyleSheet("color: #71717A; border: none; background: transparent; font-size: 11px;")
        del_btn.setToolTip("Delete Goal")
        del_btn.clicked.connect(lambda: self.goal_deleted.emit(self.goal["id"]))
        top_row.addWidget(del_btn)
        layout.addLayout(top_row)

        # Goal Title
        title_lbl = QLabel(self.goal.get("title", "Untitled Goal"))
        title_lbl.setStyleSheet(f"color: {config.COLOR_CRISP_WHITE}; font-size: 14px; font-weight: 700;")
        layout.addWidget(title_lbl)

        # Linked Habit info
        linked = self.goal.get("linkedHabitTitle", "")
        if linked:
            link_lbl = QLabel(f"⚡ Linked to: {linked}")
            link_lbl.setStyleSheet("color: #A1A1AA; font-size: 10px; font-style: italic;")
            layout.addWidget(link_lbl)

        # Progress stats
        curr = float(self.goal.get("currentValue", 0))
        target = float(self.goal.get("targetValue", 1))
        unit = self.goal.get("unit", "")
        pct = min(100, int((curr / target * 100))) if target > 0 else 0

        stats_row = QHBoxLayout()
        stat_text = QLabel(f"{curr:g} / {target:g} {unit}")
        stat_text.setStyleSheet(f"color: {config.COLOR_CRISP_WHITE}; font-size: 12px; font-weight: 700;")
        stats_row.addWidget(stat_text)

        stats_row.addStretch()

        pct_text = QLabel(f"{pct}%")
        pct_text.setStyleSheet(f"color: {config.COLOR_NEON_GREEN}; font-size: 12px; font-weight: 800;")
        stats_row.addWidget(pct_text)
        layout.addLayout(stats_row)

        # Glowing Progress Bar
        bar = QProgressBar()
        bar.setFixedHeight(8)
        bar.setTextVisible(False)
        bar.setValue(pct)
        bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #09090B;
                border-radius: 4px;
                border: 1px solid #27272A;
            }}
            QProgressBar::chunk {{
                background-color: {config.COLOR_NEON_GREEN};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(bar)

        # Controls (+1 / +5 progress)
        ctl_row = QHBoxLayout()
        ctl_row.addStretch()

        minus_btn = QPushButton("-1")
        minus_btn.setFixedSize(32, 24)
        minus_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        minus_btn.setStyleSheet("background-color: #27272A; color: #FAFAFA; border: none; border-radius: 4px; font-size: 11px;")
        minus_btn.clicked.connect(lambda: self.progress_changed.emit(self.goal["id"], -1.0))
        ctl_row.addWidget(minus_btn)

        plus_btn = QPushButton("+1")
        plus_btn.setFixedSize(32, 24)
        plus_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        plus_btn.setStyleSheet(f"background-color: rgba(57, 255, 20, 0.2); color: {config.COLOR_NEON_GREEN}; border: 1px solid {config.COLOR_NEON_GREEN}; border-radius: 4px; font-size: 11px; font-weight: 700;")
        plus_btn.clicked.connect(lambda: self.progress_changed.emit(self.goal["id"], 1.0))
        ctl_row.addWidget(plus_btn)

        layout.addLayout(ctl_row)


class FullDashboardWindow(QMainWindow):
    """
    Full Desktop Suite for VoltHabit.
    Allows complete management of Habits, Grouped Habits / Routines,
    Long-Term Goals, and Analytics.
    """
    switch_to_widget_requested = pyqtSignal()

    def __init__(self, sync_service: FirestoreSyncService):
        super().__init__()
        self.sync_service = sync_service
        self.current_group_filter = "All"
        self.drag_position = QPoint()

        self._setup_window()
        self._init_ui()
        self._connect_signals()

    def _setup_window(self):
        self.setWindowTitle("VoltHabit - Desktop Suite & Cloud Sync")
        self.resize(1020, 700)
        self.setMinimumSize(880, 580)
        self.setWindowIcon(create_neon_icon())
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {config.COLOR_PITCH_BLACK};
            }}
            QWidget {{
                color: {config.COLOR_CRISP_WHITE};
                font-family: 'Segoe UI', system-ui, sans-serif;
            }}
            QScrollBar:vertical {{
                background: {config.COLOR_PITCH_BLACK};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(57, 255, 20, 0.3);
                border-radius: 3px;
                min-height: 25px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {config.COLOR_NEON_GREEN};
            }}
        """)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. SIDEBAR
        sidebar = self._build_sidebar()
        main_layout.addWidget(sidebar)

        # 2. MAIN CONTENT AREA
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(16)

        # Top Bar
        top_bar = self._build_top_bar()
        content_layout.addWidget(top_bar)

        # Stacked Pages
        self.stacked_pages = QStackedWidget()
        self.page_habits = self._build_habits_page()
        self.page_groups = self._build_groups_page()
        self.page_goals = self._build_goals_page()
        self.page_analytics = self._build_analytics_page()
        self.page_settings = self._build_settings_page()

        self.stacked_pages.addWidget(self.page_habits)     # index 0
        self.stacked_pages.addWidget(self.page_groups)     # index 1
        self.stacked_pages.addWidget(self.page_goals)      # index 2
        self.stacked_pages.addWidget(self.page_analytics)  # index 3
        self.stacked_pages.addWidget(self.page_settings)   # index 4

        content_layout.addWidget(self.stacked_pages, 1)

        main_layout.addWidget(content_container, 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: #0E0E11;
                border-right: 1px solid #1E1E24;
            }}
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 20)
        layout.setSpacing(8)

        # Logo & App Title
        logo_box = QHBoxLayout()
        bolt = QLabel("⚡")
        bolt.setStyleSheet(f"color: {config.COLOR_NEON_GREEN}; font-size: 22px; font-weight: 900;")
        logo_box.addWidget(bolt)

        brand_v = QVBoxLayout()
        brand_lbl = QLabel("VOLTHABIT")
        brand_lbl.setStyleSheet(f"color: {config.COLOR_CRISP_WHITE}; font-size: 15px; font-weight: 800; letter-spacing: 1.5px;")
        brand_v.addWidget(brand_lbl)

        sub_lbl = QLabel("DESKTOP SUITE")
        sub_lbl.setStyleSheet("color: #71717A; font-size: 8px; font-weight: 700; letter-spacing: 1.2px;")
        brand_v.addWidget(sub_lbl)
        logo_box.addLayout(brand_v)
        layout.addLayout(logo_box)

        layout.addSpacing(24)

        # Navigation Buttons
        self.nav_buttons = []
        nav_items = [
            ("📋 Habits Tracker", 0),
            ("📁 Grouped Routines", 1),
            ("🎯 Long-Term Goals", 2),
            ("📊 Habit Analytics", 3),
            ("⚙️ Settings & Sync", 4),
        ]

        for text, idx in nav_items:
            btn = QPushButton(text)
            btn.setFixedHeight(40)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, i=idx: self._on_nav_clicked(i))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        self._set_active_nav_button(0)

        layout.addStretch()

        # Switch to Mini Desktop Widget Button
        switch_btn = QPushButton("📌 Mini Widget Mode")
        switch_btn.setFixedHeight(38)
        switch_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        switch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(57, 255, 20, 0.12);
                color: {config.COLOR_NEON_GREEN};
                border: 1px solid {config.COLOR_NEON_GREEN};
                border-radius: 8px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {config.COLOR_NEON_GREEN};
                color: {config.COLOR_PITCH_BLACK};
            }}
        """)
        switch_btn.setToolTip("Collapse into the lightweight floating desktop widget")
        switch_btn.clicked.connect(self._on_switch_to_widget)
        layout.addWidget(switch_btn)

        return sidebar

    def _set_active_nav_button(self, index: int):
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(57, 255, 20, 0.15);
                        color: {config.COLOR_NEON_GREEN};
                        border: 1px solid {config.COLOR_NEON_GREEN};
                        border-radius: 8px;
                        text-align: left;
                        padding-left: 14px;
                        font-weight: 700;
                        font-size: 12px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: #A1A1AA;
                        border: none;
                        text-align: left;
                        padding-left: 14px;
                        font-weight: 500;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        color: {config.COLOR_CRISP_WHITE};
                        background-color: #18181B;
                        border-radius: 8px;
                    }}
                """)

    def _on_nav_clicked(self, index: int):
        self.stacked_pages.setCurrentIndex(index)
        self._set_active_nav_button(index)

    def _on_switch_to_widget(self):
        self.hide()
        self.switch_to_widget_requested.emit()

    def _build_top_bar(self) -> QWidget:
        top_bar = QWidget()
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Date & Header Info
        date_v = QVBoxLayout()
        date_v.setSpacing(2)
        today_text = datetime.now().strftime("%A, %B %d, %Y").upper()
        self.top_date_lbl = QLabel(today_text)
        self.top_date_lbl.setStyleSheet("color: #71717A; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        date_v.addWidget(self.top_date_lbl)

        self.page_heading_lbl = QLabel("My Daily Habits")
        self.page_heading_lbl.setStyleSheet("color: #FAFAFA; font-size: 20px; font-weight: 800;")
        date_v.addWidget(self.page_heading_lbl)
        layout.addLayout(date_v)

        layout.addStretch()

        # Real-time sync status badge
        self.top_sync_pill = QLabel("● LIVE SYNCED")
        self.top_sync_pill.setStyleSheet(f"""
            background-color: rgba(57, 255, 20, 0.12);
            color: {config.COLOR_NEON_GREEN};
            border: 1px solid {config.COLOR_NEON_GREEN};
            border-radius: 12px;
            padding: 4px 10px;
            font-size: 10px;
            font-weight: 700;
        """)
        layout.addWidget(self.top_sync_pill)

        # Quick action: Add Habit button
        add_habit_btn = QPushButton("+ New Habit")
        add_habit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        add_habit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {config.COLOR_NEON_GREEN};
                color: {config.COLOR_PITCH_BLACK};
                border: none;
                border-radius: 8px;
                padding: 7px 14px;
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #55FF33;
            }}
        """)
        add_habit_btn.clicked.connect(self._open_add_habit_dialog)
        layout.addWidget(add_habit_btn)

        # Quick action: Add Goal button
        add_goal_btn = QPushButton("+ New Goal")
        add_goal_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        add_goal_btn.setStyleSheet("""
            QPushButton {{
                background-color: #27272A;
                color: #FAFAFA;
                border: 1px solid #3F3F46;
                border-radius: 8px;
                padding: 7px 14px;
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton:hover {{
                border-color: #39FF14;
                color: #39FF14;
            }}
        """)
        add_goal_btn.clicked.connect(self._open_add_goal_dialog)
        layout.addWidget(add_goal_btn)

        return top_bar

    # --- PAGE 1: HABITS TRACKER ---
    def _build_habits_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Routine Filter Chips Bar
        self.chips_layout = QHBoxLayout()
        self.chips_layout.setSpacing(8)
        layout.addLayout(self.chips_layout)

        # Habits Scroll Area
        self.habits_scroll = QScrollArea()
        self.habits_scroll.setWidgetResizable(True)
        self.habits_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.habits_list_widget = QWidget()
        self.habits_vbox = QVBoxLayout(self.habits_list_widget)
        self.habits_vbox.setContentsMargins(0, 0, 0, 0)
        self.habits_vbox.setSpacing(8)
        self.habits_vbox.addStretch()

        self.habits_scroll.setWidget(self.habits_list_widget)
        layout.addWidget(self.habits_scroll, 1)

        return page

    # --- PAGE 2: GROUPED ROUTINES ---
    def _build_groups_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        intro = QLabel("Organize habits into structured routines. Complete entire routines in one click.")
        intro.setStyleSheet("color: #A1A1AA; font-size: 13px;")
        layout.addWidget(intro)

        # Groups Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.groups_container = QWidget()
        self.groups_vbox = QVBoxLayout(self.groups_container)
        self.groups_vbox.setContentsMargins(0, 0, 0, 0)
        self.groups_vbox.setSpacing(14)
        self.groups_vbox.addStretch()

        scroll.setWidget(self.groups_container)
        layout.addWidget(scroll, 1)

        return page

    # --- PAGE 3: LONG-TERM GOALS ---
    def _build_goals_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        intro = QLabel("Bridge daily habits with big outcomes. Track milestones and progress towards your yearly goals.")
        intro.setStyleSheet("color: #A1A1AA; font-size: 13px;")
        layout.addWidget(intro)

        # Goals Grid Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.goals_container = QWidget()
        self.goals_grid = QGridLayout(self.goals_container)
        self.goals_grid.setContentsMargins(0, 0, 0, 0)
        self.goals_grid.setSpacing(14)

        scroll.setWidget(self.goals_container)
        layout.addWidget(scroll, 1)

        return page

    # --- PAGE 4: ANALYTICS ---
    def _build_analytics_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Stats Cards Row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self.stat_active_streaks = self._create_stat_card("⚡ Peak Streak", "0 Days", "Current top unbroken chain")
        self.stat_completion_rate = self._create_stat_card("📈 Today's Pace", "0%", "Habits completed today")
        self.stat_total_habits = self._create_stat_card("📋 Active Habits", "0", "Monitored across routines")
        self.stat_goals_count = self._create_stat_card("🎯 Active Goals", "0", "Long-term targets tracked")

        stats_row.addWidget(self.stat_active_streaks)
        stats_row.addWidget(self.stat_completion_rate)
        stats_row.addWidget(self.stat_total_habits)
        stats_row.addWidget(self.stat_goals_count)
        layout.addLayout(stats_row)

        # 30-Day Activity Heatmap Preview
        heatmap_card = GlassCard(active_hover=False)
        heatmap_layout = QVBoxLayout(heatmap_card)
        heatmap_layout.setContentsMargins(18, 16, 18, 16)
        heatmap_layout.setSpacing(10)

        h_title = QLabel("🔥 30-Day Consistency Heatmap")
        h_title.setStyleSheet("color: #FAFAFA; font-size: 14px; font-weight: 700;")
        heatmap_layout.addWidget(h_title)

        self.heatmap_grid = QGridLayout()
        self.heatmap_grid.setSpacing(4)
        self._populate_heatmap_grid()
        heatmap_layout.addLayout(self.heatmap_grid)

        layout.addWidget(heatmap_card)
        layout.addStretch()

        return page

    def _create_stat_card(self, title: str, value: str, sub: str) -> GlassCard:
        card = GlassCard(active_hover=False)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        t = QLabel(title)
        t.setStyleSheet("color: #A1A1AA; font-size: 11px; font-weight: 600;")
        layout.addWidget(t)

        v = QLabel(value)
        v.setStyleSheet(f"color: {config.COLOR_NEON_GREEN}; font-size: 22px; font-weight: 800;")
        layout.addWidget(v)

        s = QLabel(sub)
        s.setStyleSheet("color: #71717A; font-size: 10px;")
        layout.addWidget(s)

        card.val_label = v
        return card

    def _populate_heatmap_grid(self):
        # Clear
        while self.heatmap_grid.count():
            item = self.heatmap_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Last 30 days
        today = datetime.now().date()
        for i in range(30):
            day = today - timedelta(days=29 - i)
            day_str = day.strftime("%Y-%m-%d")

            # Count completions on this day across habits
            completions = sum(1 for h in self.sync_service.habits_cache if day_str in h.get("completedDates", []))

            cell = QLabel()
            cell.setFixedSize(26, 26)
            cell.setToolTip(f"{day_str}: {completions} habits completed")

            # Heatmap intensity
            if completions == 0:
                bg = "#18181B"
                border = "1px solid #27272A"
            elif completions == 1:
                bg = "rgba(57, 255, 20, 0.3)"
                border = "1px solid rgba(57, 255, 20, 0.4)"
            elif completions == 2:
                bg = "rgba(57, 255, 20, 0.6)"
                border = "1px solid rgba(57, 255, 20, 0.7)"
            else:
                bg = config.COLOR_NEON_GREEN
                border = "1px solid #39FF14"

            cell.setStyleSheet(f"""
                background-color: {bg};
                border: {border};
                border-radius: 4px;
            """)
            col = i % 10
            row = i // 10
            self.heatmap_grid.addWidget(cell, row, col)

    # --- PAGE 5: SETTINGS ---
    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        card = GlassCard(active_hover=False)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 18, 20, 18)
        c_layout.setSpacing(12)

        title = QLabel("Cloud Sync Configuration")
        title.setStyleSheet("color: #FAFAFA; font-size: 16px; font-weight: 700;")
        c_layout.addWidget(title)

        info = QLabel(f"Project ID: {config.PROJECT_ID}\nDatabase ID: {config.DATABASE_ID}\nActive User ID: {config.USER_ID or 'Not Set (Demo Mode)'}")
        info.setStyleSheet("color: #A1A1AA; font-size: 12px; line-height: 1.6;")
        c_layout.addWidget(info)

        sync_btn = QPushButton("Force Resync from Firestore")
        sync_btn.setFixedHeight(34)
        sync_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        sync_btn.setStyleSheet(f"background-color: {config.COLOR_DARK_ZINC}; color: {config.COLOR_NEON_GREEN}; border: 1px solid {config.COLOR_NEON_GREEN}; border-radius: 6px; font-weight: 700;")
        sync_btn.clicked.connect(self.sync_service.refresh)
        c_layout.addWidget(sync_btn)

        layout.addWidget(card)
        layout.addStretch()

        return page

    # --- DATA BINDINGS & RENDERING ---
    def _connect_signals(self):
        self.sync_service.habits_updated.connect(self._on_habits_updated)
        self.sync_service.goals_updated.connect(self._on_goals_updated)
        self.sync_service.groups_updated.connect(self._on_groups_updated)
        self.sync_service.sync_status.connect(self._on_sync_status)

    def _on_habits_updated(self, habits: List[Dict[str, Any]]):
        self._render_routine_filter_chips()
        self._render_habits_list(habits)
        self._render_groups_page()
        self._update_analytics(habits)
        self._populate_heatmap_grid()

    def _on_goals_updated(self, goals: List[Dict[str, Any]]):
        self._render_goals_grid(goals)
        if hasattr(self, "stat_goals_count"):
            self.stat_goals_count.val_label.setText(str(len(goals)))

    def _on_groups_updated(self, groups: List[Dict[str, Any]]):
        self._render_routine_filter_chips()
        self._render_groups_page()

    def _on_sync_status(self, message: str, state: str):
        if state == "ok":
            self.top_sync_pill.setText("● LIVE SYNCED")
            self.top_sync_pill.setStyleSheet(f"background-color: rgba(57, 255, 20, 0.12); color: {config.COLOR_NEON_GREEN}; border: 1px solid {config.COLOR_NEON_GREEN}; border-radius: 12px; padding: 4px 10px; font-size: 10px; font-weight: 700;")
        else:
            self.top_sync_pill.setText(f"● {message.upper()}")
            self.top_sync_pill.setStyleSheet("background-color: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B; border-radius: 12px; padding: 4px 10px; font-size: 10px; font-weight: 700;")

    def _render_routine_filter_chips(self):
        # Clear existing chips
        while self.chips_layout.count():
            item = self.chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add "All" chip
        all_btn = QPushButton("All Habits")
        all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._style_chip(all_btn, active=(self.current_group_filter == "All"))
        all_btn.clicked.connect(lambda: self._set_group_filter("All"))
        self.chips_layout.addWidget(all_btn)

        # Groups chips
        seen_groups = set()
        for g in self.sync_service.groups_cache:
            name = g.get("name", "Group")
            if name not in seen_groups:
                seen_groups.add(name)
                btn = QPushButton(name)
                btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                self._style_chip(btn, active=(self.current_group_filter == name))
                btn.clicked.connect(lambda checked, n=name: self._set_group_filter(n))
                self.chips_layout.addWidget(btn)

        self.chips_layout.addStretch()

    def _style_chip(self, btn: QPushButton, active: bool):
        if active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(57, 255, 20, 0.18);
                    color: {config.COLOR_NEON_GREEN};
                    border: 1px solid {config.COLOR_NEON_GREEN};
                    border-radius: 14px;
                    padding: 5px 14px;
                    font-size: 11px;
                    font-weight: 700;
                }}
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {{
                    background-color: #18181B;
                    color: #A1A1AA;
                    border: 1px solid #27272A;
                    border-radius: 14px;
                    padding: 5px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    border-color: #39FF14;
                    color: #FAFAFA;
                }}
            """)

    def _set_group_filter(self, group_name: str):
        self.current_group_filter = group_name
        self._render_routine_filter_chips()
        self._render_habits_list(self.sync_service.habits_cache)

    def _render_habits_list(self, habits: List[Dict[str, Any]]):
        while self.habits_vbox.count() > 1:
            item = self.habits_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        today_str = datetime.now().strftime("%Y-%m-%d")

        for habit in habits:
            grp = habit.get("group", "General")
            if self.current_group_filter != "All" and self.current_group_filter != grp:
                continue

            card = GlassCard(active_hover=True)
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(16, 12, 16, 12)
            c_layout.setSpacing(14)

            # Checkbox
            is_done = today_str in habit.get("completedDates", [])
            chk = NeonCheckBox(checked=is_done)
            chk.toggled_state.connect(lambda state, hid=habit["id"]: self.sync_service.toggle_habit_today(hid, state))
            c_layout.addWidget(chk)

            # Details
            info_layout = QVBoxLayout()
            info_layout.setSpacing(2)

            title_lbl = QLabel(habit.get("cleanTitle", habit.get("title", "")))
            title_lbl.setStyleSheet(f"color: {config.COLOR_CRISP_WHITE}; font-size: 14px; font-weight: 600;")
            if is_done:
                title_lbl.setStyleSheet("color: #71717A; text-decoration: line-through; font-size: 14px;")
            info_layout.addWidget(title_lbl)

            sub_txt = f"{grp} • {habit.get('frequency', 'daily').upper()}"
            sub_lbl = QLabel(sub_txt)
            sub_lbl.setStyleSheet("color: #A1A1AA; font-size: 10px; font-weight: 600;")
            info_layout.addWidget(sub_lbl)
            c_layout.addLayout(info_layout, 1)

            # Streak badge
            streak_badge = StreakBadge(streak=habit.get("streak", 0))
            c_layout.addWidget(streak_badge)

            # Delete button
            del_btn = QPushButton("🗑️")
            del_btn.setFixedSize(26, 26)
            del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            del_btn.setStyleSheet("background: transparent; border: none; font-size: 12px;")
            del_btn.setToolTip("Delete Habit")
            del_btn.clicked.connect(lambda checked, hid=habit["id"]: self._confirm_delete_habit(hid))
            c_layout.addWidget(del_btn)

            self.habits_vbox.insertWidget(self.habits_vbox.count() - 1, card)

    def _render_groups_page(self):
        while self.groups_vbox.count() > 1:
            item = self.groups_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for group in self.sync_service.groups_cache:
            grp_name = group.get("name", "Routine")
            card = GlassCard(active_hover=False)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(18, 16, 18, 16)
            c_layout.setSpacing(10)

            # Header
            header_layout = QHBoxLayout()
            g_title = QLabel(grp_name)
            g_title.setStyleSheet("color: #FAFAFA; font-size: 15px; font-weight: 700;")
            header_layout.addWidget(g_title)

            header_layout.addStretch()

            # Batch complete button
            batch_btn = QPushButton("✓ Complete All Today")
            batch_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            batch_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(57, 255, 20, 0.15);
                    color: {config.COLOR_NEON_GREEN};
                    border: 1px solid {config.COLOR_NEON_GREEN};
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: {config.COLOR_NEON_GREEN};
                    color: {config.COLOR_PITCH_BLACK};
                }}
            """)
            batch_btn.clicked.connect(lambda checked, gn=grp_name: self.sync_service.batch_complete_group(gn))
            header_layout.addWidget(batch_btn)
            c_layout.addLayout(header_layout)

            # Habits in this group
            in_group = [h for h in self.sync_service.habits_cache if h.get("group") == grp_name]
            if not in_group:
                empty = QLabel("No habits assigned to this routine yet.")
                empty.setStyleSheet("color: #71717A; font-size: 11px; font-style: italic;")
                c_layout.addWidget(empty)
            else:
                for h in in_group:
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    is_done = today_str in h.get("completedDates", [])
                    row = QHBoxLayout()
                    chk = NeonCheckBox(checked=is_done)
                    chk.toggled_state.connect(lambda state, hid=h["id"]: self.sync_service.toggle_habit_today(hid, state))
                    row.addWidget(chk)

                    lbl = QLabel(h.get("cleanTitle", h.get("title", "")))
                    lbl.setStyleSheet("color: #FAFAFA; font-size: 13px;" if not is_done else "color: #71717A; text-decoration: line-through; font-size: 13px;")
                    row.addWidget(lbl)
                    row.addStretch()

                    badge = StreakBadge(streak=h.get("streak", 0))
                    row.addWidget(badge)
                    c_layout.addLayout(row)

            self.groups_vbox.insertWidget(self.groups_vbox.count() - 1, card)

    def _render_goals_grid(self, goals: List[Dict[str, Any]]):
        while self.goals_grid.count():
            item = self.goals_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        col = 0
        row = 0
        for goal in goals:
            card = GoalCard(goal)
            card.progress_changed.connect(self.sync_service.update_goal_progress)
            card.goal_deleted.connect(self.sync_service.delete_goal)
            self.goals_grid.addWidget(card, row, col)

            col += 1
            if col >= 2:
                col = 0
                row += 1

    def _update_analytics(self, habits: List[Dict[str, Any]]):
        today_str = datetime.now().strftime("%Y-%m-%d")
        total = len(habits)
        completed = sum(1 for h in habits if today_str in h.get("completedDates", []))
        top_streak = max((h.get("streak", 0) for h in habits), default=0)
        pct = int(completed / total * 100) if total > 0 else 0

        self.stat_active_streaks.val_label.setText(f"{top_streak} Days")
        self.stat_completion_rate.val_label.setText(f"{pct}%")
        self.stat_total_habits.val_label.setText(str(total))

    # --- DIALOG HANDLERS ---
    def _open_add_habit_dialog(self):
        dialog = AddHabitDialog(self.sync_service.groups_cache, self)
        if dialog.exec():
            data = dialog.get_data()
            if data["title"]:
                self.sync_service.add_habit(data["title"], data["frequency"], data["group"])

    def _open_add_goal_dialog(self):
        dialog = AddGoalDialog(self.sync_service.habits_cache, self)
        if dialog.exec():
            data = dialog.get_data()
            self.sync_service.add_goal(data)

    def _confirm_delete_habit(self, habit_id: str):
        reply = QMessageBox.question(
            self,
            "Delete Habit",
            "Are you sure you want to delete this habit from Firestore and all devices?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.sync_service.delete_habit(habit_id)

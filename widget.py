import os
import sys
from datetime import datetime
from typing import List, Dict, Any

from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QSize
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QBrush,
    QPixmap,
    QIcon,
    QFont,
    QCursor,
    QPainterPath,
)
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QProgressBar,
    QGraphicsDropShadowEffect,
    QSystemTrayIcon,
    QMenu,
    QApplication,
)

import config
from firestore_sync import FirestoreSyncService, calculate_streak


def create_neon_icon() -> QIcon:
    """Generate a sharp, high-DPI neon lightning bolt tray icon."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Black circular background
    painter.setBrush(QBrush(QColor(config.COLOR_PITCH_BLACK)))
    painter.setPen(QPen(QColor(config.COLOR_NEON_GREEN), 3))
    painter.drawEllipse(3, 3, size - 6, size - 6)

    # Neon lightning bolt
    path = QPainterPath()
    path.moveTo(35, 12)
    path.lineTo(20, 32)
    path.lineTo(31, 32)
    path.lineTo(27, 52)
    path.lineTo(44, 28)
    path.lineTo(33, 28)
    path.closeSubpath()

    painter.setBrush(QBrush(QColor(config.COLOR_NEON_GREEN)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPath(path)
    painter.end()

    return QIcon(pixmap)


class NeonCheckBox(QPushButton):
    """Custom frameless glowing neon-green checkbox."""
    toggled_state = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(24, 24)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.toggled.connect(self._on_toggled)

        # Neon Glow Effect
        self.glow = QGraphicsDropShadowEffect(self)
        self.glow.setBlurRadius(10)
        self.glow.setOffset(0, 0)
        self.glow.setColor(QColor(config.COLOR_NEON_GREEN))
        self.glow.setEnabled(checked)
        self.setGraphicsEffect(self.glow)

    def _on_toggled(self, checked: bool):
        self.glow.setEnabled(checked)
        self.update()
        self.toggled_state.emit(checked)

    def set_checked_silent(self, checked: bool):
        self.blockSignals(True)
        self.setChecked(checked)
        self.glow.setEnabled(checked)
        self.blockSignals(False)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)

        if self.isChecked():
            # Glowing neon green box
            painter.setBrush(QBrush(QColor(config.COLOR_NEON_GREEN)))
            painter.setPen(QPen(QColor(config.COLOR_NEON_GREEN), 1.5))
            painter.drawRoundedRect(rect, 5, 5)

            # Dark checkmark
            painter.setPen(QPen(QColor(config.COLOR_PITCH_BLACK), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            # Draw checkmark points
            x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
            p1 = QPoint(int(x + w * 0.25), int(y + h * 0.52))
            p2 = QPoint(int(x + w * 0.44), int(y + h * 0.72))
            p3 = QPoint(int(x + w * 0.76), int(y + h * 0.32))
            painter.drawLine(p1, p2)
            painter.drawLine(p2, p3)
        else:
            # Unchecked: dark translucent zinc with thin neon green border
            painter.setBrush(QBrush(QColor(24, 24, 27, 200)))
            painter.setPen(QPen(QColor(57, 255, 20, 100), 1.5))
            painter.drawRoundedRect(rect, 5, 5)

        painter.end()


class StreakBadge(QLabel):
    """Glowing neon-green pill streak badge."""
    def __init__(self, streak: int = 0, parent=None):
        super().__init__(parent)
        self.set_streak(streak)

    def set_streak(self, streak: int):
        self.setText(f"⚡ {streak}")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(57, 255, 20, 0.12);
                color: {config.COLOR_NEON_GREEN};
                border: 1px solid {config.COLOR_NEON_GREEN};
                border-radius: 8px;
                padding: 2px 7px;
                font-size: 11px;
                font-weight: 700;
            }}
        """)

        # Add glow effect if streak > 0
        if streak > 0:
            glow = QGraphicsDropShadowEffect(self)
            glow.setBlurRadius(8)
            glow.setOffset(0, 0)
            glow.setColor(QColor(config.COLOR_NEON_GREEN))
            self.setGraphicsEffect(glow)
        else:
            self.setGraphicsEffect(None)


class HabitRow(QFrame):
    """Single habit card in the widget list."""
    habit_toggled = pyqtSignal(str, bool)

    def __init__(self, habit: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.habit_id = habit.get("id", "")
        self.habit_data = habit
        self._init_ui()

    def _init_ui(self):
        self.setFixedHeight(54)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._apply_style(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        # Checkbox
        today_str = datetime.now().strftime("%Y-%m-%d")
        completed_dates = self.habit_data.get("completedDates", [])
        is_today_completed = today_str in completed_dates

        self.checkbox = NeonCheckBox(checked=is_today_completed)
        self.checkbox.toggled_state.connect(self._on_checkbox_toggled)
        layout.addWidget(self.checkbox)

        # Title & Subtitle vertical layout
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.title_label = QLabel(self.habit_data.get("title", "Untitled Habit"))
        self.title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        text_layout.addWidget(self.title_label)

        freq = self.habit_data.get("frequency", "daily").upper()
        self.sub_label = QLabel(freq)
        self.sub_label.setStyleSheet(f"color: {config.COLOR_MUTED_TEXT}; font-size: 9px; font-weight: 600; letter-spacing: 0.5px;")
        text_layout.addWidget(self.sub_label)

        layout.addLayout(text_layout, 1)

        # Streak Badge
        streak_val = self.habit_data.get("streak", 0)
        self.streak_badge = StreakBadge(streak=streak_val)
        layout.addWidget(self.streak_badge)

        self._update_text_style(is_today_completed)

    def _apply_style(self, is_completed: bool):
        border_color = "rgba(57, 255, 20, 0.4)" if is_completed else "#27272A"
        bg_color = "rgba(24, 24, 27, 0.85)"
        self.setStyleSheet(f"""
            HabitRow {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 9px;
            }}
            HabitRow:hover {{
                border: 1px solid {config.COLOR_NEON_GREEN};
                background-color: rgba(30, 30, 35, 0.95);
            }}
        """)

    def _update_text_style(self, is_completed: bool):
        self._apply_style(is_completed)
        if is_completed:
            self.title_label.setStyleSheet(f"color: {config.COLOR_MUTED_TEXT}; text-decoration: line-through;")
        else:
            self.title_label.setStyleSheet(f"color: {config.COLOR_CRISP_WHITE}; text-decoration: none;")

    def _on_checkbox_toggled(self, checked: bool):
        self._update_text_style(checked)
        self.habit_toggled.emit(self.habit_id, checked)

    def update_habit_data(self, habit: Dict[str, Any]):
        self.habit_data = habit
        today_str = datetime.now().strftime("%Y-%m-%d")
        completed_dates = habit.get("completedDates", [])
        is_today_completed = today_str in completed_dates

        self.title_label.setText(habit.get("title", "Untitled"))
        self.checkbox.set_checked_silent(is_today_completed)
        self._update_text_style(is_today_completed)
        self.streak_badge.set_streak(habit.get("streak", 0))


class VoltHabitWidget(QWidget):
    """
    Pitch-black (#09090B) semi-transparent rounded window (300px × 380px)
    with a thin 1px neon-green (#39FF14) border, white text, and glowing neon-green
    checkboxes and streak badges.
    """
    expand_dashboard_requested = pyqtSignal()

    def __init__(self, sync_service: FirestoreSyncService):
        super().__init__()
        self.sync_service = sync_service
        self.drag_position = QPoint()
        self.is_pinned_to_bottom = True

        self._setup_window_properties()
        self._init_ui()
        self._setup_system_tray()
        self._connect_signals()

    def _setup_window_properties(self):
        # Frameless, transparent background
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnBottomHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(config.WIDGET_WIDTH, config.WIDGET_HEIGHT)

    def _init_ui(self):
        # Root layout for widget with zero margins so rounded border looks crisp
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Outer rounded frame container
        self.container = QFrame(self)
        self.container.setObjectName("mainContainer")
        self.container.setStyleSheet(f"""
            QFrame#mainContainer {{
                background-color: rgba(9, 9, 11, 0.94);
                border: 1px solid {config.COLOR_BORDER_GREEN};
                border-radius: 14px;
            }}
        """)

        # Container layout
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(14, 12, 14, 12)
        container_layout.setSpacing(8)

        # --- HEADER ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        # Bolt icon & Brand title
        title_box = QHBoxLayout()
        title_box.setSpacing(4)
        bolt_label = QLabel("⚡")
        bolt_label.setStyleSheet(f"color: {config.COLOR_NEON_GREEN}; font-size: 14px; font-weight: 900;")
        title_box.addWidget(bolt_label)

        self.title_label = QLabel("VOLTHABIT")
        self.title_label.setStyleSheet(f"""
            color: {config.COLOR_CRISP_WHITE};
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 1.2px;
        """)
        title_box.addWidget(self.title_label)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Sync status dot
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {config.COLOR_NEON_GREEN}; font-size: 10px;")
        self.status_dot.setToolTip("Syncing...")
        header_layout.addWidget(self.status_dot)

        # Expand to Dashboard Button
        self.expand_btn = QPushButton("⤢")
        self.expand_btn.setFixedSize(20, 20)
        self.expand_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.expand_btn.setToolTip("Open Full VoltHabit Dashboard")
        self.expand_btn.setStyleSheet(self._btn_style())
        self.expand_btn.clicked.connect(self.expand_dashboard_requested.emit)
        header_layout.addWidget(self.expand_btn)

        # Pin Button (Pin to Desktop Layer / Always on Top)
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setFixedSize(20, 20)
        self.pin_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pin_btn.setToolTip("Desktop Layer (Stays behind windows)")
        self.pin_btn.setStyleSheet(self._btn_style(active=True))
        self.pin_btn.clicked.connect(self.toggle_pin_mode)
        header_layout.addWidget(self.pin_btn)

        # Refresh Button
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedSize(20, 20)
        self.refresh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.refresh_btn.setToolTip("Refresh Habits from Firestore")
        self.refresh_btn.setStyleSheet(self._btn_style())
        self.refresh_btn.clicked.connect(self.sync_service.refresh)
        header_layout.addWidget(self.refresh_btn)

        # Minimize to Tray Button
        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(20, 20)
        self.min_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.min_btn.setToolTip("Hide to System Tray")
        self.min_btn.setStyleSheet(self._btn_style())
        self.min_btn.clicked.connect(self.hide)
        header_layout.addWidget(self.min_btn)

        container_layout.addLayout(header_layout)

        # --- DATE & PROGRESS BAR ---
        progress_info_layout = QHBoxLayout()
        self.date_label = QLabel(datetime.now().strftime("%a, %b %d").upper())
        self.date_label.setStyleSheet(f"color: {config.COLOR_MUTED_TEXT}; font-size: 10px; font-weight: 700; letter-spacing: 0.8px;")
        progress_info_layout.addWidget(self.date_label)

        progress_info_layout.addStretch()

        self.progress_text = QLabel("0/0 (0%)")
        self.progress_text.setStyleSheet(f"color: {config.COLOR_NEON_GREEN}; font-size: 10px; font-weight: 700;")
        progress_info_layout.addWidget(self.progress_text)
        container_layout.addLayout(progress_info_layout)

        # Glowing Neon Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {config.COLOR_DARK_ZINC};
                border-radius: 2px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {config.COLOR_NEON_GREEN};
                border-radius: 2px;
            }}
        """)
        container_layout.addWidget(self.progress_bar)

        # --- HABITS SCROLL AREA ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: {config.COLOR_PITCH_BLACK};
                width: 5px;
                margin: 0px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(57, 255, 20, 0.4);
                min-height: 20px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {config.COLOR_NEON_GREEN};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.habits_container = QWidget()
        self.habits_container.setStyleSheet("background: transparent;")
        self.habits_layout = QVBoxLayout(self.habits_container)
        self.habits_layout.setContentsMargins(0, 4, 2, 4)
        self.habits_layout.setSpacing(6)
        self.habits_layout.addStretch()

        self.scroll_area.setWidget(self.habits_container)
        container_layout.addWidget(self.scroll_area, 1)

        # --- FOOTER STATUS ---
        footer_layout = QHBoxLayout()
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet(f"color: {config.COLOR_MUTED_TEXT}; font-size: 9px;")
        footer_layout.addWidget(self.status_label)

        footer_layout.addStretch()

        drag_hint = QLabel("⋮⋮")
        drag_hint.setStyleSheet(f"color: #3F3F46; font-size: 11px;")
        drag_hint.setToolTip("Drag widget from anywhere")
        footer_layout.addWidget(drag_hint)

        container_layout.addLayout(footer_layout)

        root_layout.addWidget(self.container)

    def _btn_style(self, active: bool = False) -> str:
        border = f"1px solid {config.COLOR_NEON_GREEN}" if active else "none"
        bg = "rgba(57, 255, 20, 0.15)" if active else "transparent"
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {config.COLOR_CRISP_WHITE};
                border: {border};
                border-radius: 4px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: rgba(57, 255, 20, 0.25);
                color: {config.COLOR_NEON_GREEN};
            }}
        """

    def _setup_system_tray(self):
        """Setup system tray icon with context menu."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(create_neon_icon())
        self.tray_icon.setToolTip("VoltHabit Widget")

        # Context Menu
        tray_menu = QMenu()
        tray_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {config.COLOR_PITCH_BLACK};
                color: {config.COLOR_CRISP_WHITE};
                border: 1px solid {config.COLOR_BORDER_GREEN};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 18px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: rgba(57, 255, 20, 0.2);
                color: {config.COLOR_NEON_GREEN};
            }}
        """)

        open_dash_action = tray_menu.addAction("⚡ Open Full Dashboard")
        open_dash_action.triggered.connect(self.expand_dashboard_requested.emit)

        toggle_action = tray_menu.addAction("Show / Hide Widget")
        toggle_action.triggered.connect(self.toggle_visibility)

        self.tray_pin_action = tray_menu.addAction("Desktop Layer (Pinned)")
        self.tray_pin_action.setCheckable(True)
        self.tray_pin_action.setChecked(True)
        self.tray_pin_action.triggered.connect(self.toggle_pin_mode)

        sync_action = tray_menu.addAction("Sync Now")
        sync_action.triggered.connect(self.sync_service.refresh)

        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("Exit VoltHabit")
        quit_action.triggered.connect(QApplication.instance().quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.toggle_visibility()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def toggle_pin_mode(self):
        """Toggle between Desktop Layer (WindowStaysOnBottomHint) and Always-on-top."""
        self.is_pinned_to_bottom = not self.is_pinned_to_bottom
        self.hide()

        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.is_pinned_to_bottom:
            flags |= Qt.WindowType.WindowStaysOnBottomHint
            self.pin_btn.setStyleSheet(self._btn_style(active=True))
            self.pin_btn.setToolTip("Desktop Layer (Stays behind windows)")
            self.tray_pin_action.setChecked(True)
            self.status_label.setText("Layer: Desktop Pinned")
        else:
            flags |= Qt.WindowType.WindowStaysOnTopHint
            self.pin_btn.setStyleSheet(self._btn_style(active=False))
            self.pin_btn.setToolTip("Always On Top (Floating above apps)")
            self.tray_pin_action.setChecked(False)
            self.status_label.setText("Layer: Always on Top")

        self.setWindowFlags(flags)
        self.show()

    def _connect_signals(self):
        self.sync_service.habits_updated.connect(self.render_habits)
        self.sync_service.sync_status.connect(self.update_sync_status)
        self.sync_service.error_occurred.connect(self.on_sync_error)

    def render_habits(self, habits: List[Dict[str, Any]]):
        """Re-render habits list smoothly."""
        # Clear existing items except bottom stretch
        while self.habits_layout.count() > 1:
            item = self.habits_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        today_str = datetime.now().strftime("%Y-%m-%d")
        completed_count = 0
        total_count = len(habits)

        for habit in habits:
            row = HabitRow(habit, parent=self.habits_container)
            row.habit_toggled.connect(self.sync_service.toggle_habit_today)
            # Insert before the stretch at the end
            self.habits_layout.insertWidget(self.habits_layout.count() - 1, row)

            if today_str in habit.get("completedDates", []):
                completed_count += 1

        # Update progress bar and count
        pct = int((completed_count / total_count * 100)) if total_count > 0 else 0
        self.progress_bar.setValue(pct)
        self.progress_text.setText(f"{completed_count}/{total_count} ({pct}%)")

    def update_sync_status(self, message: str, state: str):
        self.status_label.setText(message)
        if state == "ok":
            self.status_dot.setStyleSheet(f"color: {config.COLOR_NEON_GREEN}; font-size: 10px;")
            self.status_dot.setToolTip(f"Status: {message}")
        elif state == "syncing":
            self.status_dot.setStyleSheet(f"color: #FBBF24; font-size: 10px;")
            self.status_dot.setToolTip("Syncing with Firestore...")
        elif state == "warning":
            self.status_dot.setStyleSheet(f"color: #F59E0B; font-size: 10px;")
            self.status_dot.setToolTip(f"{message}")
        else:
            self.status_dot.setStyleSheet(f"color: {config.COLOR_ERROR_RED}; font-size: 10px;")
            self.status_dot.setToolTip(f"Error: {message}")

    def on_sync_error(self, err_msg: str):
        self.status_label.setText(f"Error: {err_msg[:24]}...")
        self.status_dot.setStyleSheet(f"color: {config.COLOR_ERROR_RED}; font-size: 10px;")

    # --- DRAGGING SUPPORT ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = QPoint()
        event.accept()

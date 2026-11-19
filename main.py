import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Import project modules
import config
from firestore_sync import FirestoreSyncService
from widget import VoltHabitWidget
from dashboard import FullDashboardWindow


def main():
    # Set Windows Process App User Model ID so the icon appears nicely in Windows taskbar
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = "volthabit.desktop.suite.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in system tray

    # Create Shared Sync Service
    sync_service = FirestoreSyncService()

    # Create Mini Widget & Full Dashboard
    widget = VoltHabitWidget(sync_service)
    dashboard = FullDashboardWindow(sync_service)

    # Position widget on desktop: top-right corner with margin
    screen = app.primaryScreen()
    if screen:
        screen_geo = screen.availableGeometry()
        x = screen_geo.width() - config.WIDGET_WIDTH - 28
        y = 48
        widget.move(x, y)

    # Interconnect widget and dashboard
    def show_dashboard():
        dashboard.show()
        dashboard.raise_()
        dashboard.activateWindow()

    def show_widget():
        dashboard.hide()
        widget.show()
        widget.raise_()

    widget.expand_dashboard_requested.connect(show_dashboard)
    dashboard.switch_to_widget_requested.connect(show_widget)

    # If --dashboard flag passed, start in dashboard mode, else start in widget mode
    if "--dashboard" in sys.argv:
        dashboard.show()
    else:
        widget.show()

    # Start Firestore real-time sync / listener
    sync_service.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

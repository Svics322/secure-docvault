import sys
from pathlib import Path
import PySide6.QtSvg
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui.window.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    icon_path = Path(__file__).resolve().parent / "icons.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
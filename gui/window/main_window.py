import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget
from gui.widgets.login_widget import LoginWidget
from gui.widgets.register_widget import RegisterWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Secure DocVault - Авторизація")
        self.setMinimumSize(400, 420)
        self.resize(400, 450)
        self.setMinimumSize(self.sizeHint())
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f4f6f9;
            }
            QTabWidget::pane {
                border: 1px solid #dcdcdc;
                background: white;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #e1e4e8;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                color: #333;
            }
            QTabBar::tab:selected {
                background: white;
                color: #0078d7;
            }
            QLabel {
                font-size: 13px;
                color: #333;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 13px;
                background: #fff;
                color: #000;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
            }
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QDialog, QMessageBox {
                background-color: #ffffff;
                color: #222222;
            }
            QMessageBox QLabel, QDialog QLabel {
                color: #222222;
                background-color: transparent;
                font-size: 13px;
            }
            QMessageBox QPushButton, QDialog QPushButton {
                background-color: #0078d7;
                color: #ffffff;
                border: none;
                padding: 6px 18px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
                min-width: 65px;
            }
            QMessageBox QPushButton:hover, QDialog QPushButton:hover {
                background-color: #005a9e;
            }
        """)

        self.tabs = QTabWidget()
        
        self.login_tab = LoginWidget()
        self.register_tab = RegisterWidget(self.tabs)
        
        self.tabs.addTab(self.login_tab, "Вхід")
        self.tabs.addTab(self.register_tab, "Реєстрація")
        
        layout.addWidget(self.tabs)
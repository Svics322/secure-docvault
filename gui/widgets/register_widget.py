from pathlib import Path

import requests
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import API_BASE_URL
from gui.widgets.api_errors import clear_labels, show_api_errors


class RegisterWidget(QWidget):
    def __init__(self, tab_widget_ref):
        super().__init__()
        self.tab_widget_ref = tab_widget_ref
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Ім'я користувача:"))
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet(
            "color: #000; background: #fff; padding: 5px;"
        )
        layout.addWidget(self.username_input)

        self.username_error_label = QLabel()
        self.username_error_label.setStyleSheet("color: red; font-size: 11px;")
        self.username_error_label.setWordWrap(True)
        layout.addWidget(self.username_error_label)

        layout.addWidget(QLabel("Email:"))
        self.email_input = QLineEdit()
        self.email_input.setStyleSheet(
            "color: #000; background: #fff; padding: 5px;"
        )
        layout.addWidget(self.email_input)

        self.email_error_label = QLabel()
        self.email_error_label.setStyleSheet("color: red; font-size: 11px;")
        self.email_error_label.setWordWrap(True)
        layout.addWidget(self.email_error_label)

        layout.addWidget(
            QLabel("Пароль (мін. 8 символів, літери, цифри, спецсимвол):")
        )
        self.password_input = QLineEdit()
        self.password_input.setStyleSheet(
            "color: #000; background: #fff; padding: 5px; padding-right: 35px;"
        )
        self.password_input.setEchoMode(QLineEdit.Password)

        icons_path = Path(__file__).resolve().parents[2] / "resources" / "icons"
        self.visible_icon = QIcon(str(icons_path / "visible-eye.svg"))
        self.hidden_icon = QIcon(str(icons_path / "hidden.svg"))

        self.toggle_action = self.password_input.addAction(
            self.visible_icon, QLineEdit.TrailingPosition
        )
        self.toggle_action.triggered.connect(self.toggle_password_visibility)

        layout.addWidget(self.password_input)

        self.password_error_label = QLabel()
        self.password_error_label.setStyleSheet("color: red; font-size: 11px;")
        self.password_error_label.setWordWrap(True)
        layout.addWidget(self.password_error_label)

        self.form_error_label = QLabel()
        self.form_error_label.setStyleSheet("color: red; font-size: 11px;")
        self.form_error_label.setWordWrap(True)
        layout.addWidget(self.form_error_label)

        layout.addStretch()

        self.register_btn = QPushButton("Зареєструватися")
        self.register_btn.clicked.connect(self.handle_register)
        layout.addWidget(self.register_btn)

    def toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.Password:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.toggle_action.setIcon(self.hidden_icon)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_action.setIcon(self.visible_icon)

    def clear_errors(self):
        clear_labels(
            self.username_error_label,
            self.email_error_label,
            self.password_error_label,
            self.form_error_label,
        )

    def handle_register(self):
        self.clear_errors()

        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()

        try:
            response = requests.post(
                f"{API_BASE_URL}/register",
                json={"username": username, "email": email, "password": password},
                timeout=5,
            )

            if response.status_code == 201:
                QMessageBox.information(
                    self, "Успіх", "Реєстрація пройшла успішно!"
                )
                self.username_input.clear()
                self.email_input.clear()
                self.password_input.clear()
                self.tab_widget_ref.setCurrentIndex(0)
                return

            try:
                data = response.json()
            except ValueError:
                self.form_error_label.setText(
                    f"Помилка сервера: {response.status_code}"
                )
                return

            show_api_errors(
                data.get("detail", "Помилка реєстрації"),
                field_labels={
                    "username": self.username_error_label,
                    "email": self.email_error_label,
                    "password": self.password_error_label,
                },
                general_label=self.form_error_label,
            )
        except requests.exceptions.Timeout:
            self.form_error_label.setText(
                "Перевищено час очікування відповіді від сервера!"
            )
        except requests.exceptions.RequestException:
            self.form_error_label.setText(
                "Не вдалося підключитися до сервера API!"
            )

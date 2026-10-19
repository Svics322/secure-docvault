import os
from pathlib import Path
import requests
import PySide6.QtSvg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PySide6.QtGui import QIcon
from config import API_BASE_URL
from utils.validators.user_validator import UserValidator
from utils.validators.password_validator import PasswordValidator

class RegisterWidget(QWidget):
    def __init__(self, tab_widget_ref):
        super().__init__()
        self.tab_widget_ref = tab_widget_ref
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Ім'я користувача:"))
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet("color: #000; background: #fff; padding: 5px;")
        layout.addWidget(self.username_input)
        
        self.username_error_label = QLabel()
        self.username_error_label.setStyleSheet("color: red; font-size: 11px;")
        self.username_error_label.setWordWrap(True)
        layout.addWidget(self.username_error_label)

        layout.addWidget(QLabel("Email:"))
        self.email_input = QLineEdit()
        self.email_input.setStyleSheet("color: #000; background: #fff; padding: 5px;")
        layout.addWidget(self.email_input)
        
        self.email_error_label = QLabel()
        self.email_error_label.setStyleSheet("color: red; font-size: 11px;")
        self.email_error_label.setWordWrap(True)
        layout.addWidget(self.email_error_label)

        layout.addWidget(QLabel("Пароль (мін. 8 символів, літери, цифри, спецсимвол):"))
        self.password_input = QLineEdit()
        self.password_input.setStyleSheet("color: #000; background: #fff; padding: 5px; padding-right: 35px;")
        self.password_input.setEchoMode(QLineEdit.Password)
        
        icons_path = Path(__file__).resolve().parents[2] / "resources" / "icons"
        self.visible_icon = QIcon(str(icons_path / "visible-eye.svg"))
        self.hidden_icon = QIcon(str(icons_path / "hidden.svg"))

        self.toggle_action = self.password_input.addAction(self.visible_icon, QLineEdit.TrailingPosition)
        self.toggle_action.triggered.connect(self.toggle_password_visibility)
        
        layout.addWidget(self.password_input)
        
        self.password_error_label = QLabel()
        self.password_error_label.setStyleSheet("color: red; font-size: 11px;")
        self.password_error_label.setWordWrap(True)
        layout.addWidget(self.password_error_label)

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
        self.username_error_label.setText("")
        self.email_error_label.setText("")
        self.password_error_label.setText("")

    def handle_register(self):
        self.clear_errors()

        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()

        is_user_valid, user_errors = UserValidator.validate_username(username)
        is_email_valid, email_errors = UserValidator.validate_email(email)
        is_pass_valid, pass_errors = PasswordValidator.validate_password_complexity(password)

        has_client_errors = False
        if user_errors:
            self.username_error_label.setText("\n".join(user_errors))
            has_client_errors = True
        if email_errors:
            self.email_error_label.setText("\n".join(email_errors))
            has_client_errors = True
        if pass_errors:
            self.password_error_label.setText("\n".join(pass_errors))
            has_client_errors = True

        if has_client_errors:
            return

        try:
            response = requests.post(
                f"{API_BASE_URL}/register",
                json={"username": username, "email": email, "password": password},
                timeout=5,
            )

            if response.status_code == 201:
                QMessageBox.information(self, "Успіх", "Реєстрація пройшла успішно!")
                self.username_input.clear()
                self.email_input.clear()
                self.password_input.clear()
                self.tab_widget_ref.setCurrentIndex(0)
            else:
                try:
                    data = response.json()
                except ValueError:
                    self.username_error_label.setText(f"Помилка сервера: {response.status_code}")
                    return

                detail = data.get("detail", "Помилка реєстрації")
                
                if isinstance(detail, dict) and "errors" in detail:
                    user_errs = []
                    email_errs = []
                    pass_errs = []
                    for err in detail["errors"]:
                        err_lower = err.lower()
                        if "електронн" in err_lower or "пошт" in err_lower or "формат" in err_lower or "email" in err_lower:
                            email_errs.append(err)
                        elif "пароль" in err_lower or "символ" in err_lower or "довжин" in err_lower or "літер" in err_lower or "цифр" in err_lower:
                            pass_errs.append(err)
                        else:
                            user_errs.append(err)
                    if user_errs:
                        self.username_error_label.setText("\n".join(user_errs))
                    if email_errs:
                        self.email_error_label.setText("\n".join(email_errs))
                    if pass_errs:
                        self.password_error_label.setText("\n".join(pass_errs))
                elif isinstance(detail, str):
                    self.username_error_label.setText(detail)
                else:
                    self.username_error_label.setText("Сталася помилка при реєстрації.")
        except requests.exceptions.Timeout:
            self.username_error_label.setText("Перевищено час очікування відповіді від сервера!")
        except requests.exceptions.RequestException:
            self.username_error_label.setText("Не вдалося підключитися до сервера API!")
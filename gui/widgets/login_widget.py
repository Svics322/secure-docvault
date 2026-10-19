import os
from pathlib import Path
import requests
import PySide6.QtSvg
from PySide6.QtCore import QSize
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from config import API_BASE_URL


class LoginWidget(QWidget):

  def __init__(self):
    super().__init__()
    layout = QVBoxLayout(self)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(15)

    layout.addWidget(QLabel("Ім'я користувача:"))
    self.username_input = QLineEdit()
    self.username_input.setStyleSheet("color: #000; background: #fff; padding: 5px;")
    layout.addWidget(self.username_input)

    self.username_error_label = QLabel()
    self.username_error_label.setStyleSheet("color: red; font-size: 11px;")
    self.username_error_label.setWordWrap(True)
    layout.addWidget(self.username_error_label)

    layout.addWidget(QLabel("Пароль:"))
    self.password_input = QLineEdit()
    self.password_input.setStyleSheet(
        "color: #000; background: #fff; padding: 5px; padding-right: 30px;"
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

    layout.addStretch()

    self.login_btn = QPushButton("Увійти")
    self.login_btn.clicked.connect(self.handle_login)
    layout.addWidget(self.login_btn)

  def toggle_password_visibility(self):
    if self.password_input.echoMode() == QLineEdit.Password:
      self.password_input.setEchoMode(QLineEdit.Normal)
      self.toggle_action.setIcon(self.hidden_icon)
    else:
      self.password_input.setEchoMode(QLineEdit.Password)
      self.toggle_action.setIcon(self.visible_icon)

  def clear_errors(self):
    self.username_error_label.setText("")
    self.password_error_label.setText("")

  def handle_login(self):
    self.clear_errors()

    username = self.username_input.text().strip()
    password = self.password_input.text()

    has_empty = False
    if not username:
      self.username_error_label.setText("Поле не може бути порожнім")
      has_empty = True
    if not password:
      self.password_error_label.setText("Поле не може бути порожнім")
      has_empty = True

    if has_empty:
      return

    try:
      response = requests.post(
          f"{API_BASE_URL}/login",
          json={"username": username, "password": password},
          timeout=5,
      )

      if response.status_code == 200:
        QMessageBox.information(self, "Вітаємо", f"Успішний вхід, {username}!")
      else:
        try:
          data = response.json()
        except ValueError:
          self.username_error_label.setText(
              f"Помилка сервера: {response.status_code}"
          )
          return

        detail = data.get("detail", "Помилка автентифікації!")
        if isinstance(detail, dict) and "errors" in detail:
          user_errs = []
          pass_errs = []
          for err in detail["errors"]:
            if "пароль" in err.lower():
              pass_errs.append(err)
            else:
              user_errs.append(err)
          if user_errs:
            self.username_error_label.setText("\n".join(user_errs))
          if pass_errs:
            self.password_error_label.setText("\n".join(pass_errs))
        elif isinstance(detail, str):
          self.username_error_label.setText(detail)
        else:
          self.username_error_label.setText(
              "Невірне ім'я користувача або пароль."
          )
    except requests.exceptions.Timeout:
      self.username_error_label.setText("Перевищено час очікування відповіді від сервера!")
    except requests.exceptions.RequestException:
      self.username_error_label.setText("Не вдалося підключитися до сервера API!")
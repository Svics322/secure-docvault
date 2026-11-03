from __future__ import annotations

from typing import Mapping

from PySide6.QtWidgets import QLabel


def clear_labels(*labels: QLabel) -> None:
    for label in labels:
        label.setText("")


def show_api_errors(
    detail,
    *,
    field_labels: Mapping[str, QLabel],
    general_label: QLabel,
) -> None:
    """Показує всі помилки, які повернув REST API.

    Поля, для яких сервер надіслав ``field_errors``, отримують повідомлення
    під відповідним input-ом, решта помилок збирається у загальному блоці.
    """

    clear_labels(*field_labels.values(), general_label)

    if isinstance(detail, dict):
        field_errors = detail.get("field_errors") or {}
        shown: set[str] = set()

        for field, messages in field_errors.items():
            label = field_labels.get(field)
            if label is None or not messages:
                continue
            label.setText("\n".join(messages))
            shown.update(messages)

        errors = detail.get("errors") or []
        remaining = [error for error in errors if error not in shown]
        if remaining:
            general_label.setText("\n".join(remaining))
        elif not field_errors and detail.get("message"):
            general_label.setText(str(detail["message"]))
    elif isinstance(detail, str):
        general_label.setText(detail)
    elif detail:
        general_label.setText(str(detail))

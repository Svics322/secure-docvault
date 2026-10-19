# Secure DocVault

## 📁 Структура проєкту

```text
secure-docvault/
├── gui/                        # Модуль графічного інтерфейсу (PySide6)
│   ├── widgets/                # Віджети входу та реєстрації
│   │   ├── login_widget.py
│   │   └── register_widget.py
│   └── window/                 # Головне вікно застосунку
│       └── main_window.py
├── utils/                      # Допоміжні модулі та сервіси
│   ├── db/                     # Робота з базою даних SQLite
│   │   └── db_handler.py
│   ├── hash/                   # Криптографічне хешування (bcrypt)
│   │   └── password_hasher.py
│   └── validators/             # Валідація користувача та пароля
│       ├── password_validator.py
│       └── user_validator.py
├── resources/                  # Векторні SVG-іконки інтерфейсу
│   └── icons/
├── .env.example                # Приклад конфігурації оточення
├── .gitignore                  # Список ігнорованих файлів Git
├── api.py                      # REST API сервер (FastAPI)
├── config.py                   # Завантаження конфігурації
├── icons.ico                   # Іконка вікна програми
├── main.py                     # Точка входу графічного клієнта
└── requirements.txt            # Список залежностей Python
```

---

## 🚀 Встановлення та запуск

### 1. Клонування репозиторію

```bash
git clone https://github.com/Svics322/secure-docvault.git
cd secure-docvault
```

### 2. Налаштування віртуального оточення

Створіть та активуйте віртуальне оточення Python:

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Встановлення залежностей

```bash
pip install -r requirements.txt
```

### 4. Налаштування змінних оточення

За потреби створіть файл `.env` на основі прикладу `.env.example`:
```ini
API_BASE_URL=http://127.0.0.1:8000
API_PORT=8000
```

---

## 💻 Запуск програми

Оскільки застосунок побудований на клієнт-серверній моделі, для роботи необхідно запустити **два процеси** у різних терміналах:

### Крок 1. Запуск сервера REST API (Термінал 1)

```bash
python api.py
```
*Сервер запуститься за адресою `http://127.0.0.1:8000` та автоматично ініціалізує базу даних `docvault.db`.*  
*Документація Swagger UI доступна за адресою: `http://127.0.0.1:8000/docs`.*

### Крок 2. Запуск графічного клієнта (Термінал 2)

```bash
python main.py
```
*Відкриється десктопне вікно авторизації та реєстрації.*

---


## 🏷 Релізи та теги

* `v0.1-auth-db` — Фіксація першого стабільного релізу: реалізація безпечної реєстрації, входу, хешування паролів через bcrypt, валідації та бази даних SQLite.

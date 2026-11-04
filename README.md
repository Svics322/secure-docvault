# Secure DocVault

Захищене сховище конфіденційних документів: REST API на FastAPI + вебклієнт
(і десктопний клієнт на PySide6).

Проєкт реалізує повний стек захисту: хешування паролів і параметризований SQL,
JWT-автентифікацію, захист фронтенду, WAF/Rate Limiting та AES-256-GCM-шифрування
файлів.

---

## Структура

Код розділено на шари: `app/api` (HTTP) → `app/services` (сценарії) →
`app/repositories` (SQLite). Наскрізні механізми безпеки лежать в
`app/security`, а перевірки запитів — в `app/middleware`.

```text
secure-docvault/
├── api.py                      # тонка точка входу (ASGI-застосунок)
├── config.py                   # конфігурація з .env (шляхи, ліміти, cookie)
├── app/
│   ├── main.py                 # create_app(): middleware, роутери, статика
│   ├── lifespan.py             # старт: схема БД, каталоги, очищення blacklist
│   ├── logging_config.py       # app.log + audit.log
│   ├── schemas.py              # Pydantic-моделі запитів
│   ├── dependencies.py         # get_current_user (Bearer/cookie)
│   ├── api/
│   │   ├── cookies.py          # встановлення/очищення auth-cookie
│   │   ├── errors.py           # єдиний обробник доменних помилок
│   │   └── routers/
│   │       ├── auth.py         # реєстрація, вхід, refresh, logout, профіль
│   │       ├── documents.py    # документи та коментарі
│   │       ├── signing.py      # ключі ЕЦП та експорт PKCS#8
│   │       └── web.py          # віддача вебклієнта
│   ├── services/
│   │   ├── auth.py             # сценарії автентифікації
│   │   ├── tokens.py           # видача/ротація/відкликання токенів
│   │   ├── documents.py        # сценарії роботи з документами
│   │   ├── signing.py          # підпис/верифікація документів
│   │   └── errors.py           # доменні винятки
│   ├── repositories/
│   │   ├── database.py         # підключення SQLite + транзакції
│   │   ├── schema.py           # DDL, міграції, індекси
│   │   ├── users.py            # користувачі та lockout
│   │   ├── documents.py        # метадані документів
│   │   ├── comments.py         # коментарі
│   │   ├── signing.py          # ключі підпису та ЕЦП документів
│   │   └── tokens.py           # blacklist і родини refresh-токенів
│   ├── security/
│   │   ├── secrets.py          # атомарна генерація/завантаження ключів
│   │   ├── passwords.py        # bcrypt, cost=12
│   │   ├── tokens.py           # JWT: підпис, перевірка, відкликання
│   │   ├── signatures.py       # RSA-2048, PSS/SHA-256, PKCS#8/X.509
│   │   ├── vault.py            # AES-256-GCM, контейнер IV|Ciphertext|Tag
│   │   ├── sanitizer.py        # bleach + видалення керуючих символів
│   │   ├── filenames.py        # безпечний Content-Disposition (RFC 5987)
│   │   └── file_types.py       # перевірка розширення та магічних байтів
│   └── middleware/
│       ├── state.py            # бани IP, ліміти, reset_state()
│       ├── security.py         # оркестрація перевірок запиту
│       ├── limiter.py          # sliding window + очищення пам'яті
│       ├── waf.py              # сигнатури атак, high/low confidence
│       ├── headers.py          # CSP/HSTS та інші заголовки
│       ├── csrf.py             # double-submit CSRF
│       └── client_ip.py        # IP з урахуванням TRUST_PROXY
├── main.py                     # точка входу PySide6-клієнта
├── web/                        # вебклієнт: shell + views + компоненти
│   ├── index.html              # лише каркас сторінки
│   ├── css/
│   │   ├── main.css            # @import решти стилів
│   │   ├── tokens.css          # CSS-змінні
│   │   ├── base.css            # reset і базові елементи
│   │   ├── layout.css          # topbar, layout, card
│   │   ├── components.css      # кнопки, таблиці, toast, коментарі, пароль
│   │   └── views.css           # стилі конкретних екранів
│   ├── assets/icons/           # іконки ока (копії з resources/icons)
│   ├── templates/              # HTML-фрагменти компонентів
│   └── js/
│       ├── main.js             # композиція застосунку + сценарії
│       ├── core/               # api, dom, errors, cookies, format, templates
│       ├── components/         # topbar, forms, passwords, dialogs, signing, table
│       └── views/              # auth-view, vault-view
├── gui/                        # десктопний клієнт (PySide6)
├── utils/
│   └── validators/             # валідація username/email/пароля (спільна з GUI)
├── tests/                      # pytest (auth, jwt, files, security, crypto, signatures)
├── test_integrity.py           # демонстрація перевірки цілісності (print-скрипт)
├── test_signature.py           # демонстрація ЕЦП RSA-PSS (print-скрипт)
├── test_stress.py              # демонстрація навантажувального тесту (print-скрипт)
├── lab_tests.py                # автоматичні перевірки сценаріїв ЛР №1–4
├── requirements.txt
└── requirements-dev.txt
```

---

## Запуск

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

python api.py          # API + вебклієнт: http://127.0.0.1:8000/
```

Опційно, десктопний клієнт (окремий термінал):

```powershell
python main.py
```

Swagger UI: `http://127.0.0.1:8000/docs`.

### Секрети

Файл `.env` не комітиться. Якщо `JWT_SECRET_KEY` або `FILE_ENCRYPTION_KEY`
відсутні, сервер згенерує їх при першому старті та атомарно допише у `.env`
у корені проєкту (це безпечно для кількох воркерів: використовується lock-файл).

Старт блокується, якщо:

* `JWT_SECRET_KEY` збігається з ключем, який уже був опублікований у репозиторії;
* ключ коротший за 256 біт;
* `FILE_ENCRYPTION_KEY` не є 64 hex-символами;
* ключ неможливо зберегти (read-only ФС) — жодних «ефемерних» ключів.

Згенерувати вручну:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Ротація ключа шифрування: старий ключ можна вказати у
`FILE_ENCRYPTION_KEY_OLD` (через кому) — він використовується лише для читання
вже зашифрованих файлів.

---

## Вебклієнт

`http://127.0.0.1:8000/` — реєстрація, вхід, профіль, завантаження,
скачування, видалення документів і коментарі. Автентифікація — HttpOnly cookie,
стан-змінювальні запити — з CSRF-токеном (`X-CSRF-Token`, double-submit).
Токени не зберігаються в `localStorage`, тому XSS не дає доступу до сесії.

Клієнт зібраний з компонентів за тією ж логікою, що й Qt-віджети:

* `index.html` містить лише каркас (`topbar`, `view-host`, `toast`);
* розмітка кожного компонента лежить окремо в `web/templates/`;
* `web/js/components/` — самодостатні компоненти з власними подіями та методами
  (`createLoginForm`, `createDocumentsTable`, `createCommentsPanel` тощо);
* `web/js/views/` композує компоненти в екрани `auth-view` і `vault-view`;
* `web/js/core/` — спільні речі: `api`, `dom`, `errors`, `cookies`, `format`,
  `templates`;
* `web/js/main.js` відповідає за сценарії та зв'язування екранів.

У робочій області є картка «Цифровий підпис» з генерацією ключів, переглядом
відбитка, скачуванням публічного ключа та модальним експортом приватного ключа
з парольною фразою. Статус підпису документа показується бейджем у таблиці.

Валідація форм (логін, реєстрація, коментарі, файл) виконується лише на сервері.
REST API повертає всі помилки одразу, згруповані за полями (`field_errors`) та
локалізовані українською; клієнт лише показує те, що повернув сервер. Те саме
стосується Qt-клієнта — `LoginWidget` і `RegisterWidget` не мають власних
перевірок, а лише відображають відповідь API.

---

## API

| Метод | Шлях | Опис |
|---|---|---|
| POST | `/api/v1/auth/register` | Реєстрація (201) |
| POST | `/api/v1/auth/login` | Вхід, пара токенів + cookie |
| POST | `/api/v1/auth/refresh` | Ротація refresh-токена |
| POST | `/api/v1/auth/logout` | Відкликання refresh + очищення cookie |
| GET | `/api/v1/user/profile` | Профіль поточного користувача |
| GET | `/api/v1/documents` | Список документів (свої; admin — усі) |
| POST | `/api/v1/documents/upload` | Шифрування та збереження файлу |
| GET | `/api/v1/documents/{id}` | Метадані |
| GET | `/api/v1/documents/{id}/download` | Розшифрування та видача |
| DELETE | `/api/v1/documents/{id}` | Видалення файлу й метаданих |
| POST/GET | `/api/v1/documents/{id}/comments` | Коментарі до документа |
| GET/POST | `/api/v1/signing/keys` | Публічний ключ / генерація пари ключів |
| GET | `/api/v1/signing/keys/public` | Експорт відкритого ключа (X.509 PEM) |
| POST | `/api/v1/signing/keys/export` | Експорт приватного ключа (PKCS#8 + пароль) |

Сумісні аліаси: `/register`, `/login`, `/logout`.

---

## Що захищено

**Автентифікація**
- bcrypt cost=12, унікальна сіль, обмеження 72 байт;
- тільки параметризовані SQL-запити;
- блокування акаунта на 15 хв після 5 невдалих спроб;
- перевірка `is_active` при вході та на кожному запиті;
- вирівнювання часу відповіді (dummy bcrypt) проти переліку користувачів;
- Access 15 хв / Refresh 7 діб, `iss`/`aud`/`jti`, заборона `alg: none`;
- Refresh Token Rotation + персистентний blacklist у SQLite;
- виявлення replay-атаки з відкликанням усього ланцюжка токенів;
- прив'язка refresh-токена до User-Agent.

**Фронтенд і заголовки**
- санітизація всього користувацького тексту (bleach, без HTML-тегів);
- CSP без `unsafe-inline` для застосунку (Swagger — окрема політика);
- HSTS, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`;
- cookie: `HttpOnly`, `Secure`, `SameSite=Strict`;
- CSRF double-submit для cookie-автентифікації;
- обмежений CORS (без `*`).

**Мережа**
- Rate Limiting: 5 спроб/хв на вхід, 60 запитів/хв на API, `HTTP 429` + `Retry-After`;
- WAF: path traversal, SQLi, command injection, XSS у URL;
- Greylist: блокування IP на 5 хв за явну атаку;
- ліміти й очищення пам'яті для rate limiter і greylist;
- `multipart` більше не вважається атакою (boundary `--...`).

**Електронний підпис**
- RSA-2048, публічна експонента 65537, схема RSA-PSS із SHA-256;
- приватний ключ зберігається зашифрованим AES-256-GCM (`SIGNING_KEY_ENCRYPTION_KEY`);
- експорт приватного ключа в PKCS#8 із парольною фразою, відкритого — X.509 PEM;
- підпис зберігається разом із документом; скачування перевіряє ЕЦП і повертає
  `X-Signature-Status: Signed & Verified`;
- недійсний підпис блокує видачу файлу (`409 Conflict`) і пише audit-подію.

**Файли**
- AES-256-GCM, випадковий 96-бітний nonce на кожну операцію;
- контейнер `[12B IV] + [Ciphertext] + [16B Tag]`;
- AAD прив'язує шифротекст до `doc_id` і власника — підміна файлів між
  документами виявляється;
- ліміт розміру (10 МБ за замовчуванням) і перевірка магічних байтів;
- перевірка SHA-256 після дешифрування;
- UUID як ім'я на диску (захист від IDOR та overwrite);
- коректний `Content-Disposition` для кирилиці (RFC 5987) без CR/LF.

---

## Тести

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

Тести використовують тимчасову БД і тимчасове сховище, реальні дані не змінюють.

Демонстраційні скрипти (потребують запущеного сервера):

```powershell
python test_integrity.py   # InvalidTag при зміні одного байта
python test_signature.py   # RSA-PSS: підпис, верифікація, підробка
python test_stress.py      # 429 + WAF + Greylist
python lab_tests.py http://127.0.0.1:8000   # сценарії ЛР №1–4
```

Для `lab_tests.py` сервер має бути запущений з `TRUST_PROXY=true`, щоб кожна
група тестів мала власну IP-адресу і бани WAF не впливали одна на одну:

```powershell
$env:TRUST_PROXY="true"; python api.py
```

> `test_stress.py` навмисно банить IP на 5 хвилин — це очікувана поведінка
> Greylist. Після нього дочекайтеся завершення бану або перезапустіть сервер.

---

## Журнали

- `logs/app.log` — загальний журнал (ротація 5 МБ × 5);
- `logs/audit.log` — події безпеки: вхід, невдалі спроби, WAF, rate limit,
  завантаження/скачування/видалення документів, порушення цілісності.

---

## Теги

* `v0.1-auth-db` — реєстрація/вхід, bcrypt, SQLite, параметризовані запити;
* `v0.2-jwt-api` — Access/Refresh JWT, ротація, захищені маршрути;
* `v0.3-client-security` — санітизація, CSP/HSTS/CORS, HttpOnly cookie;
* `v0.4-waf-ratelimit` — Rate Limiting, WAF, Greylist;
* `v0.5-file-encryption` — AES-256-GCM, шифроване сховище.

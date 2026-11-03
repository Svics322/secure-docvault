import requests
import time

BASE_URL = "http://127.0.0.1:8000"

print("==================================================")
print("1. ТЕСТУВАННЯ RATE LIMITER (Стрес-тест 10 запитів)")
print("==================================================")

login_url = f"{BASE_URL}/api/v1/auth/login"
payload = {"username": "testuser", "password": "wrongpassword"}

for i in range(1, 11):
    try:
        res = requests.post(login_url, json=payload, timeout=2)
        retry_after = res.headers.get("Retry-After", "-")
        print(f"Запит #{i:02d} | Статус: {res.status_code} | Retry-After: {retry_after}s | Відповідь: {res.text[:65]}")
    except Exception as e:
        print(f"Запит #{i:02d} | Помилка: {e}")
    time.sleep(0.05)  # Швидкісна відправка

print("\n==================================================")
print("2. ТЕСТУВАННЯ WAF (Перевірка Path Traversal та Greylist)")
print("==================================================")

# Запит із сигнатурою Path Traversal
path_traversal_url = f"{BASE_URL}/api/v1/user/profile?file=../../etc/passwd"

print("\n[Запит 1] Надсилання Path Traversal пейлоада...")
res1 = requests.get(path_traversal_url)
print(f"Статус: {res1.status_code} | Відповідь: {res1.text}")

print("\n[Запит 2] Перевірка Greylist (повторний легітимний запит від заблокованого IP)...")
res2 = requests.get(f"{BASE_URL}/docs")
print(f"Статус: {res2.status_code} | Відповідь: {res2.text}")
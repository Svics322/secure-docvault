from app.security.vault import encrypt_file_content, decrypt_file_content
from cryptography.exceptions import InvalidTag

original_text = b"CONFIDENTIAL FINANCIAL REPORT - SECURE DOCVAULT 2026"
print("==================================================")
print("ТЕСТУВАННЯ КОНТРОЛЮ ЦІЛІСНОСТІ AES-256-GCM")
print("==================================================")
print("1. Вихідний текст:", original_text.decode())

# 1. Шифрування
encrypted_blob = encrypt_file_content(original_text)
print(f"2. Зашифровано успішно ({len(encrypted_blob)} байт). Nonce/IV (12B) = {encrypted_blob[:12].hex()}")

# 2. Успішне розшифрування
decrypted = decrypt_file_content(encrypted_blob)
assert decrypted == original_text
print("3. Штатне розшифрування пройшло успішно!")

# 3. Модифікація 1 байта (Імітація підробки файлу на диску)
corrupted_blob = bytearray(encrypted_blob)
corrupted_blob[20] ^= 0xFF  # Інвертуємо біти 20-го байта

print("4. Спроба розшифрувати фальсифікований файл...")
try:
    decrypt_file_content(bytes(corrupted_blob))
    print("❌ ПОМИЛКА БЕЗПЕКИ: Фальсифіковані дані пройшли перевірку!")
except InvalidTag:
    print("✅ УСПІХ: AES-GCM заблокував читання! Виняток InvalidTag підтвердив підробку.")
print("==================================================")
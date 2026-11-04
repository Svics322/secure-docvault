from __future__ import annotations

from app.security.signatures import (
    generate_keypair,
    load_private_key,
    load_public_key,
    serialize_private_key,
    serialize_public_key,
    sign_content,
    verify_content,
)

original_text = b"OFFICIAL STATEMENT: APPROVED BY CHIEF SECURITY OFFICER"

print("==================================================")
print("ТЕСТУВАННЯ ЕЛЕКТРОННОГО ЦИФРОВОГО ПІДПИСУ RSA-PSS")
print("==================================================")
print("1. Вихідний документ:", original_text.decode())

private_key, public_key = generate_keypair()
print("2. Ключову пару RSA-2048 згенеровано")

signature = sign_content(original_text, private_key)
print(f"3. Підпис створено, довжина: {len(signature)} байт")

assert verify_content(original_text, signature, public_key)
print("4. Штатний підпис успішно верифіковано!")

tampered_text = b"OFFICIAL STATEMENT: REJECTED BY CHIEF SECURITY OFFICER"
is_valid = verify_content(tampered_text, signature, public_key)
print("5. Перевірка підробленого документа...")
if is_valid:
    print("   ❌ ПОМИЛКА БЕЗПЕКИ: підпис прийняв змінений документ!")
else:
    print("   ✅ УСПІХ: підпис відхилив змінений документ!")

public_pem = serialize_public_key(public_key)
private_pem = serialize_private_key(private_key, "Aa1!aaaa")
assert "BEGIN PUBLIC KEY" in public_pem
assert "BEGIN ENCRYPTED PRIVATE KEY" in private_pem
assert load_public_key(public_pem).key_size == 2048
assert load_private_key(private_pem, "Aa1!aaaa").key_size == 2048
print("6. Експорт/імпорт PEM: відкритий X.509 і приватний PKCS#8 (з паролем) працюють")

print("==================================================")

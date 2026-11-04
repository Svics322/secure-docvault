from __future__ import annotations

import base64
import hashlib
import os

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.security.secrets import load_secret

ALGORITHM = "RSA-PSS-SHA256"
KEY_SIZE = 2048
PUBLIC_EXPONENT = 65537
NONCE_SIZE = 12
PRIVATE_KEY_AAD = b"docvault|signing-key|v1"

_PRIVATE_KEY_ENCRYPTION_KEY: bytes | None = None


def _encryption_key() -> bytes:
    global _PRIVATE_KEY_ENCRYPTION_KEY
    if _PRIVATE_KEY_ENCRYPTION_KEY is None:
        _PRIVATE_KEY_ENCRYPTION_KEY = bytes.fromhex(
            load_secret("SIGNING_KEY_ENCRYPTION_KEY", nbytes=32)
        )
    return _PRIVATE_KEY_ENCRYPTION_KEY


def generate_keypair() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    private_key = rsa.generate_private_key(
        public_exponent=PUBLIC_EXPONENT,
        key_size=KEY_SIZE,
    )
    return private_key, private_key.public_key()


def serialize_public_key(public_key: rsa.RSAPublicKey) -> str:
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def load_public_key(pem: str) -> rsa.RSAPublicKey:
    return serialization.load_pem_public_key(pem.encode("ascii"))


def serialize_private_key(
    private_key: rsa.RSAPrivateKey, passphrase: str | None = None
) -> str:
    if passphrase:
        encryption = serialization.BestAvailableEncryption(
            passphrase.encode("utf-8")
        )
    else:
        encryption = serialization.NoEncryption()

    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    ).decode("ascii")


def load_private_key(
    pem: str, passphrase: str | None = None
) -> rsa.RSAPrivateKey:
    password = passphrase.encode("utf-8") if passphrase else None
    return serialization.load_pem_private_key(pem.encode("ascii"), password=password)


def public_key_fingerprint(public_key: rsa.RSAPublicKey) -> str:
    der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der).hexdigest()


def sign_content(content: bytes, private_key: rsa.RSAPrivateKey) -> bytes:
    return private_key.sign(
        content,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )


def verify_content(
    content: bytes, signature: bytes, public_key: rsa.RSAPublicKey
) -> bool:
    try:
        public_key.verify(
            signature,
            content,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def encrypt_private_key_pem(pem: str) -> str:
    nonce = os.urandom(NONCE_SIZE)
    encrypted = AESGCM(_encryption_key()).encrypt(
        nonce, pem.encode("utf-8"), PRIVATE_KEY_AAD
    )
    return base64.b64encode(nonce + encrypted).decode("ascii")


def decrypt_private_key_pem(token: str) -> str:
    try:
        raw = base64.b64decode(token.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise ValueError("Пошкоджений зашифрований приватний ключ") from exc

    if len(raw) < NONCE_SIZE + 16:
        raise ValueError("Пошкоджений зашифрований приватний ключ")

    nonce = raw[:NONCE_SIZE]
    ciphertext = raw[NONCE_SIZE:]
    try:
        plaintext = AESGCM(_encryption_key()).decrypt(
            nonce, ciphertext, PRIVATE_KEY_AAD
        )
    except InvalidTag as exc:
        raise ValueError("Не вдалося розшифрувати приватний ключ") from exc

    return plaintext.decode("utf-8")

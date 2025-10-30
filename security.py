import base64
import hashlib
import os

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.fernet import InvalidToken
except ImportError:
    raise Exception('Install "cryptography" Python package to use security utils.')

from connection_module import RedisConnector
from src.query_and_statement.reference_qas_manager import ReferenceQueryAndStatementManager

def __generate_fernet_key(secret_key: str) -> bytes:
    key = hashlib.sha256(secret_key.encode()).digest()
    return base64.urlsafe_b64encode(key)


def __generate_fernet_key_kdf(secret_key: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
    return base64.urlsafe_b64encode(kdf.derive(secret_key.encode("utf-8")))


def encrypt(plain_text: str, secret_key: str) -> str:
    salt = os.urandom(16)
    key = __generate_fernet_key_kdf(secret_key, salt)
    f = Fernet(key)
    return base64.urlsafe_b64encode(
        salt + f.encrypt(plain_text.encode("utf-8"))
    ).decode()


def decrypt(encrypted_data: str, secret_key: str) -> str:
    encrypted_data_bytes = base64.urlsafe_b64decode(encrypted_data)
    salt = encrypted_data_bytes[:16]
    key = __generate_fernet_key_kdf(secret_key, salt)
    f = Fernet(key)
    return f.decrypt(encrypted_data_bytes[16:]).decode("utf-8")


def encrypt_aes_gcm_256(plain_text: str, secret_key: str) -> str:
    nonce = os.urandom(32)
    salt = os.urandom(16)
    key = __generate_fernet_key_kdf(secret_key, salt)
    key = hashlib.sha256(key).hexdigest()
    ag = AESGCM(key[:32].encode())
    return base64.urlsafe_b64encode(
        salt + nonce + ag.encrypt(nonce, plain_text.encode("utf-8"), None)
    ).decode("utf-8")


def decrypt_aes_gcm_256(encrypted_data: str, secret_key: str) -> str:
    ciphertext_data_in_bytes = base64.urlsafe_b64decode(encrypted_data)
    salt = ciphertext_data_in_bytes[:16]
    key = __generate_fernet_key_kdf(secret_key, salt)
    key = hashlib.sha256(key).hexdigest()
    ag = AESGCM(key[:32].encode())
    return ag.decrypt(
        ciphertext_data_in_bytes[16:48], ciphertext_data_in_bytes[48:], None
    ).decode("utf-8")

InvalidToken = InvalidToken


MAX_FAILED_ATTEMPTS = 5
LOCKOUT_TIME_SECONDS = 120  # секунд блокировки
REDIS_KEY_PREFIX = "auth_fail:"

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

async def is_ip_blocked(ip: str) -> bool:
    async with RedisConnector.get_async_redis_session() as redis:
        key = REDIS_KEY_PREFIX + ip
        count = await redis.get(key)
        if count is not None and int(count) >= MAX_FAILED_ATTEMPTS:
            return True
    return False

async def record_failed_attempt(ip: str):
    async with RedisConnector.get_async_redis_session() as redis:
        key = REDIS_KEY_PREFIX + ip
        # Увеличиваем счётчик; если ключа нет — создаём с TTL
        current = await redis.incr(key)
        if current == 1:
            # Устанавливаем TTL только при первом инкременте
            await redis.expire(key, LOCKOUT_TIME_SECONDS)

async def clear_failed_attempts(ip: str):
    async with RedisConnector.get_async_redis_session() as redis:
        key = REDIS_KEY_PREFIX + ip
        await redis.delete(key)

security = HTTPBasic()

async def check_app_auth(
    credentials: HTTPBasicCredentials = Depends(security),
    request: Request = None,
) -> None:
    ip = get_client_ip(request)
    
    access = await ReferenceQueryAndStatementManager.app_auth(
        login=credentials.username,
        password=credentials.password,
    )
    
    if access is False:
        await record_failed_attempt(ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Введен неверный логин и/или пароль!",
            headers={"WWW-Authenticate": "Basic"},
        )
    else:
        await clear_failed_attempts(ip)

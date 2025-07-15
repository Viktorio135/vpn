import jwt
from datetime import datetime, timedelta, timezone


SECRET_KEY = "твой_секретный_ключ"
ALGORITHM = "HS256"


def create_jwt_token(data: dict, expires_minutes: int = 60):
    payload = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload.update({"exp": expire})

    token = jwt.encode(
        payload, SECRET_KEY, algorithm=ALGORITHM
    )

    return token


def verify_jwt_token(token: str):
    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM]
        )
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, 'expired'
    except jwt.InvalidTokenError:
        return False, 'invalid'

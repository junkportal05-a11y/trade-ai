"""SlowAPI Limiter core module."""
from fastapi import Request
from slowapi import Limiter


def get_real_client_ip(request: Request) -> str:
    return request.client.host if request.client else "127.0.0.1"


limiter = Limiter(key_func=get_real_client_ip, default_limits=["120/minute"])

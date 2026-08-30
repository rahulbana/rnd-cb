"""Security: auth primitives and FastAPI dependencies."""
from .auth import create_access_token, decode_token, hash_password, verify_password
from .deps import get_optional_user_id, require_user_id

__all__ = ["create_access_token", "decode_token", "hash_password", "verify_password",
           "get_optional_user_id", "require_user_id"]

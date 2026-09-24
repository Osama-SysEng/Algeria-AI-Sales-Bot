from fastapi import Header, HTTPException
from backend.app.core.config import settings

def require_operator(x_operator_token: str | None = Header(default=None)) -> str:
    if not settings.operator_tokens:
        if settings.environment == "production":
            raise HTTPException(status_code=503, detail="Operator access is not configured")
        return "development-operator"
    if x_operator_token not in settings.operator_tokens:
        raise HTTPException(status_code=403, detail="Operator authorization required")
    return "approved-operator"

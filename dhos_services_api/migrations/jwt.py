from __future__ import annotations

from datetime import datetime, timedelta

from flask import current_app
from jose import jwt as jose_jwt


def get_system_jwt(permissions: list[str]) -> str:
    expiry = datetime.utcnow() + timedelta(
        seconds=current_app.config["JWT_EXPIRY_IN_SECONDS"]
    )
    jwt_token: str = jose_jwt.encode(
        {
            "metadata": {"system_id": "dhos-robot"},
            "iss": current_app.config["HS_ISSUER"],
            "aud": current_app.config["PROXY_URL"].rstrip("/") + "/",
            "scope": " ".join(permissions),
            "exp": expiry,
        },
        key=current_app.config["HS_KEY"],
        algorithm="HS512",
    )
    return jwt_token

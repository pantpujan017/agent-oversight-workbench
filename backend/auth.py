
import json
import os

from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import jwt

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt import PyJWKClient
from jwt.exceptions import (
    InvalidTokenError,
    PyJWKClientConnectionError,
    PyJWKClientError,
)


# Load backend environment variables.
ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_FILE)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_PUBLISHABLE_KEY = os.getenv(
    "SUPABASE_PUBLISHABLE_KEY",
    "",
)

SUPABASE_ISSUER = f"{SUPABASE_URL}/auth/v1"

JWKS_URL = (
    f"{SUPABASE_ISSUER}/.well-known/jwks.json"
    if SUPABASE_URL
    else ""
)

# Cache Supabase public signing keys.
jwks_client = (
    PyJWKClient(JWKS_URL)
    if JWKS_URL
    else None
)

# Read Bearer tokens from incoming API requests.
bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Invalid or expired authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_legacy_token(token: str) -> dict[str, Any]:
    """
    Verify legacy HS256 tokens directly with Supabase Auth.

    Never expose the legacy JWT signing secret.
    """

    request = Request(
        url=f"{SUPABASE_URL}/auth/v1/user",
        headers={
            "apikey": SUPABASE_PUBLISHABLE_KEY,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=5) as response:
            user = json.loads(
                response.read().decode("utf-8")
            )

    except HTTPError as error:
        if error.code in (400, 401, 403):
            raise unauthorized() from error

        raise HTTPException(
            status_code=503,
            detail="Could not verify authentication with Supabase.",
        ) from error

    except (URLError, TimeoutError, OSError) as error:
        raise HTTPException(
            status_code=503,
            detail="Supabase authentication service is unavailable.",
        ) from error

    if not isinstance(user, dict) or not user.get("id"):
        raise unauthorized()

    return {
        "id": user["id"],
        "email": user.get("email"),
        "claims": None,
    }


def verify_es256_token(token: str) -> dict[str, Any]:
    """
    Verify ES256 access tokens using Supabase public JWKS keys.
    """

    if jwks_client is None:
        raise HTTPException(
            status_code=503,
            detail="Supabase authentication is not configured.",
        )

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(
            token
        )

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            issuer=SUPABASE_ISSUER,
            options={
                "require": [
                    "exp",
                    "sub",
                    "iss",
                    "aud",
                ]
            },
        )

    except PyJWKClientConnectionError as error:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve Supabase signing keys.",
        ) from error

    except (PyJWKClientError, InvalidTokenError) as error:
        raise unauthorized() from error

    if claims.get("role") != "authenticated":
        raise unauthorized()

    user_id = claims.get("sub")

    if not isinstance(user_id, str) or not user_id:
        raise unauthorized()

    return {
        "id": user_id,
        "email": claims.get("email"),
        "claims": claims,
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> dict[str, Any]:
    """
    FastAPI dependency that authenticates a Supabase user.

    Supports:
    - ES256: Local JWT verification using public JWKS.
    - HS256: Verification through the Supabase Auth server.
    """

    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise HTTPException(
            status_code=503,
            detail="Supabase authentication is not configured.",
        )

    if credentials is None:
        raise unauthorized()

    token = credentials.credentials

    try:
        header = jwt.get_unverified_header(token)
    except InvalidTokenError as error:
        raise unauthorized() from error

    algorithm = header.get("alg")

    if algorithm == "ES256":
        return verify_es256_token(token)

    if algorithm == "HS256":
        return verify_legacy_token(token)

    raise unauthorized()

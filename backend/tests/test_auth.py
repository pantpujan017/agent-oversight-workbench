
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest

import auth

from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


@pytest.fixture
def test_signing_keys(monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    monkeypatch.setattr(
        auth,
        "SUPABASE_URL",
        "https://example.supabase.co",
    )

    monkeypatch.setattr(
        auth,
        "SUPABASE_PUBLISHABLE_KEY",
        "test-publishable-key",
    )

    monkeypatch.setattr(
        auth,
        "SUPABASE_ISSUER",
        "https://example.supabase.co/auth/v1",
    )

    monkeypatch.setattr(
        auth,
        "jwks_client",
        SimpleNamespace(
            get_signing_key_from_jwt=lambda token:
                SimpleNamespace(key=public_key)
        ),
    )

    return private_key


def make_es256_token(private_key, expired=False):
    expiration = (
        datetime.now(timezone.utc) - timedelta(minutes=5)
        if expired
        else datetime.now(timezone.utc) + timedelta(minutes=30)
    )

    return jwt.encode(
        {
            "sub": "test-user-123",
            "email": "test@example.com",
            "iss": "https://example.supabase.co/auth/v1",
            "aud": "authenticated",
            "role": "authenticated",
            "exp": expiration,
        },
        private_key,
        algorithm="ES256",
    )


def make_credentials(token):
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )


def test_missing_token_is_rejected(test_signing_keys):
    with pytest.raises(HTTPException) as error:
        auth.get_current_user(None)

    assert error.value.status_code == 401


def test_valid_es256_token_is_accepted(test_signing_keys):
    token = make_es256_token(test_signing_keys)

    user = auth.get_current_user(
        make_credentials(token)
    )

    assert user["id"] == "test-user-123"
    assert user["email"] == "test@example.com"


def test_expired_es256_token_is_rejected(test_signing_keys):
    token = make_es256_token(
        test_signing_keys,
        expired=True,
    )

    with pytest.raises(HTTPException) as error:
        auth.get_current_user(make_credentials(token))

    assert error.value.status_code == 401


def test_unsupported_algorithm_is_rejected(
    test_signing_keys,
    monkeypatch,
):
    monkeypatch.setattr(
        auth.jwt,
        "get_unverified_header",
        lambda token: {"alg": "none"},
    )

    with pytest.raises(HTTPException) as error:
        auth.get_current_user(
            make_credentials("test-token")
        )

    assert error.value.status_code == 401


def test_hs256_uses_supabase_auth_verification(
    test_signing_keys,
    monkeypatch,
):
    monkeypatch.setattr(
        auth.jwt,
        "get_unverified_header",
        lambda token: {"alg": "HS256"},
    )

    expected_user = {
        "id": "legacy-user-123",
        "email": "legacy@example.com",
        "claims": None,
    }

    monkeypatch.setattr(
        auth,
        "verify_legacy_token",
        lambda token: expected_user,
    )

    user = auth.get_current_user(
        make_credentials("legacy-test-token")
    )

    assert user["id"] == "legacy-user-123"

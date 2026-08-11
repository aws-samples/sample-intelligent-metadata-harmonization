# Copyright (c) 2026 Amazon.com
# This file is licensed under the MIT License.
# See the LICENSE file in the project root for full license information.

"""Auth for API."""

import os
from typing import Any, Dict, Optional

import jwt
import requests
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from starlette.status import HTTP_401_UNAUTHORIZED

if not jwt.algorithms.has_crypto:
    message = "No crypto support for JWT."
    logger.error(message)
    raise RuntimeError(message)


class OIDCHTTPBearer(HTTPBearer):
    """OIDC based bearer token authenticator."""

    def __init__(self, **kwargs: Dict[str, Any]) -> None:
        """Constructor."""
        super().__init__(**kwargs)

        oidc_metadata = self.get_oidc_metadata()
        self.jwks_client = jwt.PyJWKClient(oidc_metadata["jwks_uri"], cache_jwk_set=True, lifespan=360)

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        """Verify the provided bearer token."""
        http_auth_creds = await super().__call__(request)
        try:
            decoded_jwt = self.decode_jwt(
                id_token=http_auth_creds.credentials,
                authority=os.environ["AUTHORITY"],
                client_id=os.environ["CLIENT_ID"],
            )

        except jwt.exceptions.PyJWTError as e:
            logger.exception("JWT authentication error: {error}", error=str(e))
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        # Add user ID to request
        request.state.user_id = decoded_jwt["sub"]

        return http_auth_creds

    def get_oidc_metadata(self) -> Dict[str, Any]:
        """Get OIDC endpoints and metadata from authority."""
        authority = os.environ.get("AUTHORITY")
        response = requests.get(f"{authority}/.well-known/openid-configuration", timeout=30)
        response.raise_for_status()

        json_response: Dict[str, Any] = response.json()
        return json_response

    def decode_jwt(self, id_token: str, client_id: str, authority: str) -> Any:
        """Decode JWT."""
        signing_key = self.jwks_client.get_signing_key_from_jwt(id_token)
        return jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=authority,
            audience=client_id,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )

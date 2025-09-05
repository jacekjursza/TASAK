"""PKCE (Proof Key for Code Exchange) implementation for OAuth 2.1."""

import base64
import hashlib
import secrets


def generate_pkce_pair():
    """
    Generate PKCE code verifier and challenge pair.

    Returns:
        tuple: (code_verifier, code_challenge)
    """
    # Generate code verifier - random 43-128 character string
    code_verifier = (
        base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")
    )

    # Generate code challenge using S256 method
    challenge_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = (
        base64.urlsafe_b64encode(challenge_bytes).decode("utf-8").rstrip("=")
    )

    return code_verifier, code_challenge

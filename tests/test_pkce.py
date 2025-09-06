"""Tests for PKCE implementation."""

import base64
import hashlib
from unittest.mock import patch

from tasak.pkce import generate_pkce_pair


class TestGeneratePKCEPair:
    """Tests for generate_pkce_pair function."""

    def test_generate_pkce_pair_returns_tuple(self):
        """Test that function returns a tuple of two strings."""
        verifier, challenge = generate_pkce_pair()

        assert isinstance(verifier, str)
        assert isinstance(challenge, str)
        assert len(verifier) > 0
        assert len(challenge) > 0

    def test_verifier_length_and_format(self):
        """Test that verifier has correct length and format."""
        verifier, _ = generate_pkce_pair()

        # Should be base64url encoded (43 chars for 32 bytes)
        assert 43 <= len(verifier) <= 128
        # Should only contain base64url characters
        assert all(
            c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
            for c in verifier
        )

    def test_challenge_format(self):
        """Test that challenge has correct format."""
        _, challenge = generate_pkce_pair()

        # Should be base64url encoded SHA256 (43 chars)
        assert len(challenge) == 43
        # Should only contain base64url characters
        assert all(
            c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
            for c in challenge
        )

    def test_challenge_is_sha256_of_verifier(self):
        """Test that challenge is correctly derived from verifier."""
        verifier, challenge = generate_pkce_pair()

        # Manually compute what challenge should be
        expected_challenge_bytes = hashlib.sha256(verifier.encode("utf-8")).digest()
        expected_challenge = (
            base64.urlsafe_b64encode(expected_challenge_bytes)
            .decode("utf-8")
            .rstrip("=")
        )

        assert challenge == expected_challenge

    def test_different_pairs_each_time(self):
        """Test that each call generates different pairs."""
        pair1 = generate_pkce_pair()
        pair2 = generate_pkce_pair()
        pair3 = generate_pkce_pair()

        # Verifiers should be different (random)
        assert pair1[0] != pair2[0]
        assert pair2[0] != pair3[0]
        assert pair1[0] != pair3[0]

        # Challenges should also be different
        assert pair1[1] != pair2[1]
        assert pair2[1] != pair3[1]
        assert pair1[1] != pair3[1]

    @patch("tasak.pkce.secrets.token_bytes")
    def test_deterministic_with_mocked_random(self, mock_token_bytes):
        """Test that with fixed random, we get expected output."""
        # Mock to return fixed bytes
        fixed_bytes = b"0123456789abcdef0123456789abcdef"
        mock_token_bytes.return_value = fixed_bytes

        verifier, challenge = generate_pkce_pair()

        # Verifier should be base64url of our fixed bytes
        expected_verifier = (
            base64.urlsafe_b64encode(fixed_bytes).decode("utf-8").rstrip("=")
        )
        assert verifier == expected_verifier

        # Challenge should be base64url of SHA256 of verifier
        expected_challenge_bytes = hashlib.sha256(
            expected_verifier.encode("utf-8")
        ).digest()
        expected_challenge = (
            base64.urlsafe_b64encode(expected_challenge_bytes)
            .decode("utf-8")
            .rstrip("=")
        )
        assert challenge == expected_challenge

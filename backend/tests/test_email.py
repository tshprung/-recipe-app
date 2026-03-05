"""Tests for email service (Resend verification and error handling)."""
import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.email import send_verification_email


def _make_http_error(status_code: int, text: str = ""):
    request = MagicMock()
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.request = request
    return httpx.HTTPStatusError(f"{status_code}", request=request, response=response)


@patch.dict(os.environ, {"RESEND_API_KEY": "test-key", "RESEND_FROM_EMAIL": "noreply@test.com"})
def test_send_verification_email_raises_when_no_api_key():
    with patch.dict(os.environ, {"RESEND_API_KEY": ""}, clear=False):
        with pytest.raises(RuntimeError) as exc_info:
            send_verification_email("user@example.com", "token123")
    assert "RESEND_API_KEY" in str(exc_info.value)


@patch.dict(os.environ, {"RESEND_API_KEY": "test-key", "RESEND_FROM_EMAIL": "noreply@test.com"})
def test_send_verification_email_raises_clear_error_on_resend_401():
    with patch("app.services.email.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = _make_http_error(401, "Invalid API key")
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError) as exc_info:
            send_verification_email("user@example.com", "token123")

    assert "RESEND_API_KEY" in str(exc_info.value)
    assert "invalid or expired" in str(exc_info.value).lower()


@patch.dict(os.environ, {"RESEND_API_KEY": "test-key", "RESEND_FROM_EMAIL": "noreply@test.com"})
def test_send_verification_email_raises_clear_error_on_resend_422():
    with patch("app.services.email.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = _make_http_error(
            422, '{"message": "From address not verified"}'
        )
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError) as exc_info:
            send_verification_email("user@example.com", "token123")

    assert "RESEND_FROM_EMAIL" in str(exc_info.value) or "Resend rejected" in str(exc_info.value)
    assert "Domains" in str(exc_info.value) or "verified" in str(exc_info.value).lower()


@patch.dict(os.environ, {"RESEND_API_KEY": "test-key", "RESEND_FROM_EMAIL": "noreply@test.com"})
def test_send_verification_email_raises_with_status_and_body_on_other_resend_error():
    with patch("app.services.email.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = _make_http_error(429, "Rate limit exceeded")
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError) as exc_info:
            send_verification_email("user@example.com", "token123")

    assert "429" in str(exc_info.value)
    assert "Rate limit" in str(exc_info.value) or "unknown" in str(exc_info.value)


@patch.dict(os.environ, {"RESEND_API_KEY": "test-key", "RESEND_FROM_EMAIL": "noreply@test.com"})
def test_send_verification_email_succeeds_when_resend_returns_200():
    with patch("app.services.email.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        send_verification_email("user@example.com", "token123")

    mock_post.assert_called_once()
    call_kw = mock_post.call_args.kwargs
    assert call_kw["json"]["to"] == ["user@example.com"]
    assert call_kw["json"]["subject"] == "Verify your email address"
    assert "token123" in call_kw["json"]["html"]
    assert call_kw["headers"]["Authorization"] == "Bearer test-key"

"""TikTok OAuth 2.0 flow — authorization code + PKCE + token exchange."""

import base64
import hashlib
import logging
import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# TikTok Shop OAuth endpoints (Partner Center app — khác với developers.tiktok.com)
TIKTOK_AUTH_URL = "https://auth.tiktok-shops.com/oauth/authorize"
TIKTOK_TOKEN_URL = "https://auth.tiktok-shops.com/api/v2/token/get"

REDIRECT_URI = "http://localhost:8000/api/v1/auth/tiktok/callback"

# In-memory store: state -> (created_at, code_verifier)
_oauth_states: dict[str, tuple[datetime, str]] = {}


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge



@router.get("/tiktok")
async def tiktok_auth_start():
    """Bắt đầu TikTok OAuth — redirect user đến trang xác thực TikTok."""
    if not settings.tiktok_app_key:
        raise HTTPException(422, "Chưa cấu hình TIKTOK_APP_KEY. Vào Settings → Kết nối nền tảng.")

    state = secrets.token_urlsafe(16)
    code_verifier, code_challenge = _generate_pkce()
    _oauth_states[state] = (datetime.now(timezone.utc), code_verifier)

    params = {
        "app_key": settings.tiktok_app_key,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{TIKTOK_AUTH_URL}?{urlencode(params)}"
    logger.info(f"[TikTok OAuth] Redirecting to auth, state={state[:8]}...")
    return RedirectResponse(url=auth_url)


@router.get("/tiktok/callback")
async def tiktok_auth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """TikTok redirect về đây sau khi user authorize."""
    # User từ chối hoặc lỗi
    if error:
        logger.warning(f"[TikTok OAuth] Error: {error} — {error_description}")
        return HTMLResponse(
            _result_page(
                success=False,
                message=f"Xác thực thất bại: {error_description or error}",
            )
        )

    # Validate state chống CSRF
    if not state or state not in _oauth_states:
        return HTMLResponse(
            _result_page(
                success=False,
                message="State không hợp lệ — vui lòng thử lại.",
            )
        )
    _, code_verifier = _oauth_states.pop(state)

    if not code:
        return HTMLResponse(
            _result_page(
                success=False,
                message="Không nhận được authorization code từ TikTok.",
            )
        )

    # Đổi code lấy access token
    try:
        token_data = await _exchange_code_for_token(code, code_verifier)
    except Exception as e:
        logger.error(f"[TikTok OAuth] Token exchange failed: {e}")
        return HTMLResponse(
            _result_page(
                success=False,
                message=f"Lỗi lấy token: {str(e)}",
            )
        )

    access_token = token_data.get("access_token", "")
    open_id = token_data.get("open_id", "")
    scope = token_data.get("scope", "")
    expires_in = token_data.get("expires_in", 0)

    if not access_token:
        return HTMLResponse(
            _result_page(
                success=False,
                message="TikTok không trả về access token.",
            )
        )

    # Lưu vào system_settings
    await _save_tiktok_token(db, access_token, open_id, scope)

    logger.info(f"[TikTok OAuth] Token saved, open_id={open_id[:8]}..., scope={scope}")

    return HTMLResponse(
        _result_page(
            success=True,
            message=f"Kết nối TikTok thành công! Open ID: {open_id[:8]}... | Scope: {scope} | Hết hạn sau: {expires_in // 3600}h",
        )
    )


async def _exchange_code_for_token(code: str, code_verifier: str) -> dict:
    """Đổi authorization code lấy access token từ TikTok (PKCE)."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            TIKTOK_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "app_key": settings.tiktok_app_key,
                "app_secret": settings.tiktok_app_secret,
                "auth_code": code,
                "grant_type": "authorized_code",
                "redirect_uri": REDIRECT_URI,
                "code_verifier": code_verifier,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise ValueError(f"{data['error']}: {data.get('error_description', '')}")
        return data


async def _save_tiktok_token(db: AsyncSession, access_token: str, open_id: str, scope: str) -> None:
    """Lưu TikTok token vào bảng system_settings."""
    from sqlalchemy import text

    # Keys phải viết hoa để apply_db_settings() load được vào settings singleton
    entries = {
        "TIKTOK_ACCESS_TOKEN": access_token,
        "TIKTOK_OPEN_ID": open_id,
        "TIKTOK_SCOPE": scope,
    }

    for key, value in entries.items():
        # Upsert đơn giản
        await db.execute(
            text("""
                INSERT INTO system_settings (key, value, updated_at)
                VALUES (:key, :value, now())
                ON CONFLICT (key) DO UPDATE SET value = :value, updated_at = now()
            """),
            {"key": key, "value": value},
        )

    await db.commit()


def _result_page(success: bool, message: str) -> str:
    """HTML page hiển thị kết quả OAuth — tự đóng sau 3 giây."""
    color = "#22c55e" if success else "#ef4444"
    icon = "✅" if success else "❌"
    title = "Kết nối thành công" if success else "Kết nối thất bại"
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    body {{ font-family: sans-serif; display: flex; align-items: center; justify-content: center;
           height: 100vh; margin: 0; background: #0f172a; color: #f1f5f9; }}
    .card {{ text-align: center; padding: 2rem 3rem; background: #1e293b;
             border-radius: 1rem; border: 2px solid {color}; max-width: 480px; }}
    h2 {{ color: {color}; font-size: 1.5rem; margin-bottom: 1rem; }}
    p {{ color: #94a3b8; line-height: 1.6; }}
    .note {{ margin-top: 1.5rem; font-size: 0.85rem; color: #64748b; }}
  </style>
</head>
<body>
  <div class="card">
    <h2>{icon} {title}</h2>
    <p>{message}</p>
    <p class="note">Bạn có thể đóng tab này. Quay lại ứng dụng để tiếp tục.</p>
  </div>
</body>
</html>"""

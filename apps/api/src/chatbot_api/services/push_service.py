"""Push notification service via Firebase Cloud Messaging (web push).

Lazy init: Firebase app is created on first send. Credentials come from env
vars (FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, FIREBASE_PRIVATE_KEY,
FIREBASE_PRIVATE_KEY_ID). If config is missing, notify_admin() logs a
warning and returns 0 instead of crashing the API.
"""

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.settings import get_settings
from chatbot_api.models import AdminDevice
from chatbot_api.repositories.admin_device import admin_device_repository

log = structlog.get_logger()

_firebase_app: Any | None = None
_init_failed: bool = False


def _build_credentials_dict() -> dict[str, str] | None:
    """Build the service account dict from env vars. None if config missing."""
    s = get_settings()
    if not (s.firebase_project_id and s.firebase_client_email and s.firebase_private_key):
        return None
    return {
        "type": "service_account",
        "project_id": s.firebase_project_id,
        "private_key_id": s.firebase_private_key_id,
        "private_key": s.firebase_private_key.replace("\\n", "\n"),
        "client_email": s.firebase_client_email,
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def _get_firebase_app() -> Any | None:
    """Lazy-init Firebase app. Returns None if not configured."""
    global _firebase_app, _init_failed
    if _firebase_app is not None:
        return _firebase_app
    if _init_failed:
        return None

    cred_dict = _build_credentials_dict()
    if cred_dict is None:
        log.warning(
            "firebase_config_missing",
            hint="set FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, FIREBASE_PRIVATE_KEY in .env",
        )
        _init_failed = True
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(cred_dict)
        _firebase_app = firebase_admin.initialize_app(cred)
        log.info("firebase_initialized", project_id=cred_dict["project_id"])
        return _firebase_app
    except Exception as exc:
        log.error("firebase_init_failed", error=str(exc))
        _init_failed = True
        return None


def reset_firebase_app() -> None:
    """Test helper — reset cached firebase app."""
    global _firebase_app, _init_failed
    _firebase_app = None
    _init_failed = False


async def register_device(
    db: AsyncSession,
    *,
    admin_id: int,
    fcm_token: str,
    platform: str = "web",
    user_agent: str | None = None,
) -> AdminDevice:
    """Upsert FCM device token for the given admin. Same token re-registered
    just updates updated_at and (optionally) reassigns the admin."""
    existing = await admin_device_repository.get_by_token(db, fcm_token)
    if existing is not None:
        existing.admin_id = admin_id
        existing.platform = platform
        existing.user_agent = user_agent
        await db.flush()
        await db.refresh(existing)
        return existing

    device = AdminDevice(
        admin_id=admin_id,
        fcm_token=fcm_token,
        platform=platform,
        user_agent=user_agent,
    )
    db.add(device)
    await db.flush()
    await db.refresh(device)
    return device


async def notify_all_admins(
    db: AsyncSession,
    *,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> int:
    """Broadcast a push to every active admin. Returns total successful sends."""
    from chatbot_api.repositories.admin import admin_repository

    admins = await admin_repository.list_active(db)
    if not admins:
        log.info("notify_all_admins_no_admins")
        return 0
    total = 0
    for admin in admins:
        total += await notify_admin(
            db, admin_id=admin.id, title=title, body=body, data=data
        )
    return total


async def notify_admin(
    db: AsyncSession,
    *,
    admin_id: int,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> int:
    """Send web push to all registered devices of the given admin.

    Returns count of successful sends. 0 if Firebase isn't configured.
    """
    app = _get_firebase_app()
    if app is None:
        log.warning(
            "notify_admin_skipped_no_firebase", admin_id=admin_id, title=title
        )
        return 0

    devices = await admin_device_repository.list_by_admin(db, admin_id)
    if not devices:
        log.info("notify_admin_no_devices", admin_id=admin_id)
        return 0

    from firebase_admin import messaging

    # Send DATA-only payload (no `notification` field). The SW renders the
    # notification with its own showNotification() call. Otherwise FCM web shows
    # the auto notification AND the SW shows another → duplicates.
    payload_data: dict[str, str] = {"title": title, "body": body}
    if data:
        payload_data.update(data)

    sent = 0
    for device in devices:
        try:
            message = messaging.Message(
                data=payload_data,
                token=device.fcm_token,
            )
            messaging.send(message, app=app)
            sent += 1
        except Exception as exc:
            log.error(
                "push_send_failed",
                admin_id=admin_id,
                device_id=device.id,
                error=str(exc),
            )
    log.info(
        "notify_admin_done", admin_id=admin_id, sent=sent, total=len(devices)
    )
    return sent

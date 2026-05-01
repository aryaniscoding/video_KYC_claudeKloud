"""LiveKit room management and participant token generation."""
import logging
from livekit.api import LiveKitAPI, AccessToken, VideoGrants

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def create_room_and_token(session_id: str, customer_id: str) -> tuple[str, str]:
    """Create a LiveKit room and return (room_name, customer_jwt_token)."""
    room_name = f"kyc-{session_id}"
    identity = f"customer-{customer_id}"

    try:
        lk = LiveKitAPI(
            url=settings.livekit_host,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
        from livekit.api import CreateRoomRequest
        await lk.room.create_room(CreateRoomRequest(name=room_name, max_participants=2))
        await lk.aclose()
    except Exception as exc:
        logger.warning("LiveKit unavailable (%s) — running without video room", exc)

    token = _build_participant_token(room_name, identity)
    return room_name, token


def _build_participant_token(room_name: str, identity: str, name: str = "Customer") -> str:
    token = (
        AccessToken(api_key=settings.livekit_api_key, api_secret=settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(name)
        .with_grants(VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
    )
    return token.to_jwt()


async def delete_room(session_id: str) -> None:
    room_name = f"kyc-{session_id}"
    try:
        async with LiveKitAPI(
            url=settings.livekit_host,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        ) as lk:
            from livekit.api import DeleteRoomRequest
            await lk.room.delete_room(DeleteRoomRequest(room=room_name))
    except Exception as exc:
        logger.warning("Failed to delete room %s: %s", room_name, exc)

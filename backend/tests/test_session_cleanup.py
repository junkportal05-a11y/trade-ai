import time
import asyncio
from app.core.auth import ACTIVE_SESSIONS, create_session, cleanup_sessions, SESSION_TTL

async def test_cleanup():
    # Setup initial state
    ACTIVE_SESSIONS.clear()
    token = create_session("test_user")

    # Verify token added
    assert token in ACTIVE_SESSIONS

    # Mock time so session expires
    ACTIVE_SESSIONS[token]["time"] = time.time() - SESSION_TTL - 100

    # Run cleanup
    cleanup_sessions()

    # Verify token removed
    assert token not in ACTIVE_SESSIONS
    print("Test passed: cleanup_sessions successfully removed expired session")

if __name__ == "__main__":
    asyncio.run(test_cleanup())

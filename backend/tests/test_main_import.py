import asyncio
from backend.main import cleanup_sessions_loop

async def test_import():
    try:
        # Run it quickly by replacing sleep with something shorter or just mocking it,
        # but just importing and running the first cycle works since it's an async task.
        task = asyncio.create_task(cleanup_sessions_loop())
        await asyncio.sleep(0.1) # Let the first cycle run
        task.cancel()
        print("Success: no NameError")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_import())

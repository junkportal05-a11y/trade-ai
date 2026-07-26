import asyncio
from app.main import app

async def test_import():
    assert app.title == "ApexTrade API"
    print("Success: app main imported cleanly")

if __name__ == "__main__":
    asyncio.run(test_import())

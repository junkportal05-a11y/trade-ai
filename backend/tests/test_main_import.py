import pytest
from app.main import app

@pytest.mark.asyncio
async def test_import():
    assert app.title == "ApexTrade API"
    print("Success: app main imported cleanly")

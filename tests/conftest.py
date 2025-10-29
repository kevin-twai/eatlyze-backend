# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    """讓 pytest 知道使用 asyncio event loop"""
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    """建立可用的 AsyncClient（新版 httpx 無 lifespan 參數）"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

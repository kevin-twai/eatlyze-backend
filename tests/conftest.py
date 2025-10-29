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
    """建立可用的 AsyncClient，支援 lifespan"""
    transport = ASGITransport(app=app, lifespan="on")
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

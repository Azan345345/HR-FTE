import pytest
from httpx import AsyncClient
from fastapi import status

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_unauthorized_cv_list(client: AsyncClient):
    # This should fail because we don't have a token
    response = await client.get("/api/cv/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_unauthorized_jobs_search(client: AsyncClient):
    response = await client.post("/api/jobs/search", json={"query": "python"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

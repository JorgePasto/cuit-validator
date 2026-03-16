import pytest
import asyncio

from app.services.auth_service import AuthService
from app.models.afip_models import TokenData
from datetime import datetime, timedelta, timezone


class DummyConnector:
    def __init__(self):
        self.calls = 0

    async def get_token(self):
        self.calls += 1
        # Simular retardo en la obtención del token
        await asyncio.sleep(0.01)
        now = datetime.now(timezone.utc)
        return TokenData(
            token="tok",
            sign="sig",
            generation_time=now,
            expiration_time=now + timedelta(hours=12)
        )

    def get_service_name(self):
        return "ws_sr_padron_a13"


@pytest.mark.asyncio
async def test_concurrent_get_valid_token_uses_lock(monkeypatch):
    connector = DummyConnector()
    service = AuthService(wsaa_connector=connector)

    # Ejecutar múltiples coroutines que solicitan token concurrentemente
    results = await asyncio.gather(*(service.get_valid_token() for _ in range(5)))

    # Todos los resultados deben ser TokenData
    assert all(r.token == "tok" for r in results)
    # El connector debe haber sido llamado solo una vez debido al lock + re-check
    assert connector.calls == 1

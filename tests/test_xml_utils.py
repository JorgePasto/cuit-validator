import pytest
from app.utils.xml_utils import build_login_ticket_request, parse_afip_timestamp
from datetime import timezone


def test_build_login_ticket_request_basic():
    xml = build_login_ticket_request(service="ws_sr_padron_a13", expiration_hours=1)
    assert "loginTicketRequest" in xml
    assert "ws_sr_padron_a13" in xml


def test_parse_afip_timestamp_with_offset():
    # timestamp con offset -03:00
    ts = "2024-03-14T10:30:00-03:00"
    dt = parse_afip_timestamp(ts)
    # Debe ser timezone-aware UTC
    assert dt.tzinfo is not None
    # Convertido a UTC -> 13:30:00Z
    assert dt.hour == 13 and dt.minute == 30

from unittest.mock import MagicMock, patch


def test_resolve_city_success(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "post code": "50-001",
        "country abbreviation": "PL",
        "places": [{"place name": "Wrocław", "state": "Dolnośląskie", "latitude": "51.1", "longitude": "17.0"}],
    }
    with patch("app.routers.meta.httpx.get", return_value=mock_resp):
        r = client.get("/api/meta/resolve-city?country=PL&zip=50-001")
    assert r.status_code == 200
    data = r.json()
    assert data["city"] == "Wrocław"
    assert data["country"] == "PL"


def test_resolve_city_not_found(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch("app.routers.meta.httpx.get", return_value=mock_resp):
        r = client.get("/api/meta/resolve-city?country=PL&zip=00-000")
    assert r.status_code == 404


def test_resolve_city_invalid_inputs(client):
    r = client.get("/api/meta/resolve-city?country=P&zip=50-001")
    assert r.status_code == 422
    r = client.get("/api/meta/resolve-city?country=PL&zip=x")
    assert r.status_code == 422


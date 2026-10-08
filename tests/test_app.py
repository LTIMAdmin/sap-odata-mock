import base64
import importlib
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("MOCK_REQUIRE_AUTH", "true")
    monkeypatch.setenv("MOCK_USER", "demo")
    monkeypatch.setenv("MOCK_PASS", "demo123")
    monkeypatch.setenv(
        "MOCK_SOURCE_FILE", str(PROJECT_ROOT / "sap-response.actual.json")
    )
    monkeypatch.setenv("MOCK_REPLICATE_FACTOR", "1")
    monkeypatch.setenv("MOCK_LIMIT_ROWS", "0")

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    return TestClient(module.app)


def _auth_header() -> dict[str, str]:
    token = base64.b64encode(b"demo:demo123").decode("ascii")
    return {"Authorization": f"Basic {token}"}


def test_delta_endpoint_returns_only_customer_contract_fields(monkeypatch) -> None:
    client = _load_client(monkeypatch)

    response = client.get(
        "/sap/opu/odata/sap/ZODATA_PS_MS_ALLOC_DET_API_SRV/IT_RESSet",
        params={"$format": "json", "$orderby": "Psid asc"},
        headers=_auth_header(),
    )

    assert response.status_code == 200
    rows = response.json()["d"]["results"]
    assert len(rows) == 2
    assert set(rows[0]) == {
        "__metadata",
        "LvFlag",
        "Guid",
        "Psid",
        "EventType",
        "OldProjid",
        "NewProjid",
        "OldIrmid",
        "OldIrmName",
        "NewIrmid",
        "NewIrmName",
        "OldLocCode",
        "OldLocDesc",
        "NewLocCode",
        "NewLocDesc",
        "StartDate",
        "EndDate",
    }
    assert rows[0]["Psid"] == "00277262"
    assert rows[0]["StartDate"] == "/Date(1788220800000)/"
    assert rows[0]["EndDate"] == "/Date(253402214400000)/"


def test_delta_endpoint_supports_connector_query_parameters(monkeypatch) -> None:
    client = _load_client(monkeypatch)

    response = client.get(
        "/sap/opu/odata/sap/ZODATA_PS_MS_ALLOC_DET_API_SRV/IT_RESSet",
        params={
            "$top": 1,
            "$skip": 0,
            "$filter": "EventType eq 'Project Change'",
            "$orderby": "Psid desc",
            "$select": "Guid,Psid,EventType",
            "$format": "json",
        },
        headers=_auth_header(),
    )

    assert response.status_code == 200
    payload = response.json()["d"]
    assert payload["results"] == [
        {
            "Guid": "974bc97f-79f5-1fd1-ab84-508db70f1bbc",
            "Psid": "00278849",
            "EventType": "Project Change",
        }
    ]
    next_query = parse_qs(urlparse(payload["__next"]).query)
    assert next_query["$skip"] == ["1"]


def test_delta_endpoint_requires_authentication(monkeypatch) -> None:
    client = _load_client(monkeypatch)

    response = client.get(
        "/sap/opu/odata/sap/ZODATA_PS_MS_ALLOC_DET_API_SRV/IT_RESSet"
    )

    assert response.status_code == 401


def test_delta_endpoint_rejects_old_snapshot_fields(monkeypatch) -> None:
    client = _load_client(monkeypatch)

    response = client.get(
        "/sap/opu/odata/sap/ZODATA_PS_MS_ALLOC_DET_API_SRV/IT_RESSet",
        params={"$select": "Pernr,ProjectId"},
        headers=_auth_header(),
    )

    assert response.status_code == 400

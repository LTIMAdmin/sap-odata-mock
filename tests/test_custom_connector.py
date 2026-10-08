import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONNECTOR_PATH = PROJECT_ROOT / "custom-connector" / "apiDefinition.swagger.json"


def test_custom_connector_matches_delta_api_contract() -> None:
    connector = json.loads(CONNECTOR_PATH.read_text(encoding="utf-8"))

    assert connector["swagger"] == "2.0"
    assert connector["host"] == "sap-odata-mock.onrender.com"
    assert connector["basePath"] == (
        "/sap/opu/odata/sap/ZODATA_PS_MS_ALLOC_DET_API_SRV"
    )

    operation = connector["paths"]["/IT_RESSet"]["get"]
    assert operation["operationId"] == "GetDeltaEvents"
    assert {parameter["name"] for parameter in operation["parameters"]} == {
        "$top",
        "$skip",
        "$filter",
        "$orderby",
        "$select",
        "$format",
    }

    event = connector["definitions"]["DeltaEvent"]
    assert set(event["properties"]) == {
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
    assert set(event["required"]) == set(event["properties"])


def test_custom_connector_uses_basic_authentication() -> None:
    connector = json.loads(CONNECTOR_PATH.read_text(encoding="utf-8"))

    assert connector["securityDefinitions"]["basic_auth"] == {"type": "basic"}
    assert connector["security"] == [{"basic_auth": []}]

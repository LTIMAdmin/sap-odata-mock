import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONNECTOR_PATH = PROJECT_ROOT / "custom-connector" / "apiDefinition.swagger.json"


def test_custom_connector_matches_delta_api_contract() -> None:
    connector = json.loads(CONNECTOR_PATH.read_text(encoding="utf-8"))

    assert connector["swagger"] == "2.0"
    assert connector["host"] == '@environmentVariables("ltm_SAPDeltaApiHost")'
    assert connector["basePath"] == (
        '@environmentVariables("ltm_SAPDeltaApiBaseUrl")'
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

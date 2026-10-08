# SAP Delta OData Mock API

Temporary implementation of the customer SAP service:

```text
ZODATA_PS_MS_ALLOC_DET_API_SRV/IT_RESSet
```

Use this service until LTIM provides a reachable non-production API.

## Endpoint

```text
https://sap-odata-mock.onrender.com/sap/opu/odata/sap/ZODATA_PS_MS_ALLOC_DET_API_SRV/IT_RESSet
```

The response uses the OData V2 envelope:

```json
{
  "d": {
    "results": [],
    "__next": null
  }
}
```

Each event contains only:

- `__metadata`
- `LvFlag`
- `Guid`
- `Psid`
- `EventType`
- `OldProjid`
- `NewProjid`
- `OldIrmid`
- `OldIrmName`
- `NewIrmid`
- `NewIrmName`
- `OldLocCode`
- `OldLocDesc`
- `NewLocCode`
- `NewLocDesc`
- `StartDate`
- `EndDate`

The old snapshot fields such as `Pernr`, `ProjectId`, `Ename`, `Resigned`, and `ExDate` are no longer returned.

## Supported OData parameters

- `$top`
- `$skip`
- `$filter`
- `$orderby`
- `$select`
- `$format=json`

The mock supports equality filters joined by `and`, for example:

```text
$filter=EventType eq 'Project Change' and Psid eq '00277262'
```

## Local run

```powershell
$env:MOCK_REQUIRE_AUTH = "true"
$env:MOCK_USER = "demo"
$env:MOCK_PASS = "demo123"
$env:MOCK_SOURCE_FILE = "c:\Users\vinothselvam\source\repos\LTIM Solutions\sap-mock-api\sap-response.actual.json"
& "c:\Users\vinothselvam\source\repos\LTIM Solutions\.venv\Scripts\python.exe" -m uvicorn app:app --host 0.0.0.0 --port 8000
```

## Render deployment

The service is deployed from [render.yaml](./render.yaml) as a Docker web service.

Render uses:

- `MOCK_SOURCE_FILE=/app/sap-response.actual.json`
- `MOCK_REPLICATE_FACTOR=1`
- `MOCK_LIMIT_ROWS=0`
- Basic authentication enabled

`autoDeploy: true` deploys repository changes after they are pushed to the connected branch.

## Custom connector

Flow 1 must not call this API with a direct HTTP action.

Import [apiDefinition.swagger.json](./custom-connector/apiDefinition.swagger.json) as the `LTIM SAP Delta API` custom connector inside `LTM Operations Solution`.

Create solution environment variables for:

- API Host
- API Base URL

Use a solution connection reference for authentication. See [custom-connector/README.md](./custom-connector/README.md).

## Tests

```powershell
& "c:\Users\vinothselvam\source\repos\LTIM Solutions\.venv\Scripts\python.exe" -m pytest tests\test_app.py -q
```

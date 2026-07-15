# SAP Mock API for Power Automate Testing

This mock service emulates the SAP OData endpoint you are using for pagination tests.

Endpoint path:
- `/sap/opu/odata/SAP/ZPS_ODATA_DATALAKE_SRV/PS_MANPOWER_REPORT_DATASet`

Response shape:
- OData V2 style: `{ "d": { "results": [...], "__next": "..." } }`

Supports these query params:
- `$top`
- `$skip`
- `$orderby` (example: `Pernr asc`)
- `$select`
- `$filter` with simple `eq` clauses joined by `and`

Accepted filter fields include:
- Data fields: `Pernr`, `ProjectId`, `Resigned`, `ExDate`, etc.
- Parameter-like fields used in your flow tests: `IStartDate`, `IEndDate`, `IInterfaceId`, `ISystemId`

## 1) Run locally

```powershell
cd sap-mock-api
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

Quick test URL:

```text
http://localhost:8000/sap/opu/odata/SAP/ZPS_ODATA_DATALAKE_SRV/PS_MANPOWER_REPORT_DATASet?$format=json&$orderby=Pernr asc&$top=200&$skip=0
```

## 2) Deploy to Render (easy public URL)

1. Push `sap-mock-api` folder to a GitHub repo.
2. In Render, create a new Web Service from the repo.
3. Render auto-detects `render.yaml` and deploys.
4. Copy the public URL, for example:
   - `https://sap-odata-mock.onrender.com`

Final API URL for Power Automate:

```text
https://<your-render-host>/sap/opu/odata/SAP/ZPS_ODATA_DATALAKE_SRV/PS_MANPOWER_REPORT_DATASet
```

## 3) Auth settings

Default in `render.yaml`:
- `MOCK_REQUIRE_AUTH=true`
- `MOCK_USER=demo`
- `MOCK_PASS=demo123`

Build Authorization header value in Power Automate:
- `Basic <base64(username:password)>`
- For `demo:demo123`, the base64 value is `ZGVtbzpkZW1vMTIz`
- Header example:
  - `Authorization: Basic ZGVtbzpkZW1vMTIz`

## 4) Suggested Power Automate values

- Base URL:

```text
https://<your-render-host>/sap/opu/odata/SAP/ZPS_ODATA_DATALAKE_SRV/PS_MANPOWER_REPORT_DATASet
```

- Keep your existing paging logic:
  - `$top=200`
  - `$skip` increments by 200
  - stop when returned row count `< top`

## 5) Sample call compatible with your current flow

```text
https://<your-render-host>/sap/opu/odata/SAP/ZPS_ODATA_DATALAKE_SRV/PS_MANPOWER_REPORT_DATASet?$filter=IStartDate eq '06/01/2026' and IEndDate eq '06/01/2026' and IInterfaceId eq 'PS_MANPOWER_RPT' and ISystemId eq 'DATALAKE'&$format=json&$orderby=Pernr asc&$top=200&$skip=0
```

## 6) Notes

- Dataset is synthetic and deterministic (1200 records).
- Some records are marked `Resigned=Yes` to test UC-041 candidate behavior.
- You can tune record count in `app.py` (`_build_dataset(count=1200)`).

## 7) Use your real SAP response JSON

You can feed the mock API with your actual SAP response and still keep pagination.

1. Save your real response JSON into this folder, for example:
  - `sap-response.actual.json`
2. Start the API with these env vars:

```powershell
$env:MOCK_SOURCE_FILE = "c:\Users\vinothselvam\source\repos\LTIM Solutions\sap-mock-api\sap-response.actual.json"
$env:MOCK_REPLICATE_FACTOR = "20"
$env:MOCK_LIMIT_ROWS = "0"
uvicorn app:app --host 0.0.0.0 --port 8000
```

What this does:
1. Loads rows from your real payload.
2. Auto-maps common aliases to canonical fields used by your flow (`Pernr`, `ProjectId`, `Resigned`, etc.).
3. Replicates rows so you get enough volume to test pagination (`$top/$skip`) at scale.

Supported input payload shapes:
1. OData V2: `{ "d": { "results": [ ... ] } }`
2. Flat array: `[ ... ]`
3. Wrapper keys: `{ "results": [ ... ] }`, `{ "value": [ ... ] }`, `{ "items": [ ... ] }`

Quick validation:
1. Open `http://localhost:8000/`
2. Check `records`, `sourceFile`, and `replicateFactor` values.

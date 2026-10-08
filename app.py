import base64
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from uuid import NAMESPACE_URL, uuid5

from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="SAP Delta OData Mock API", version="2.0.0")

SERVICE_ROOT = "/sap/opu/odata/sap/ZODATA_PS_MS_ALLOC_DET_API_SRV"
BASE_PATH = f"{SERVICE_ROOT}/IT_RESSet"
METADATA_BASE_URL = "https://iconnectqas.ltm.info"
REQUIRE_AUTH = os.getenv("MOCK_REQUIRE_AUTH", "false").lower() == "true"
MOCK_USER = os.getenv("MOCK_USER", "demo")
MOCK_PASS = os.getenv("MOCK_PASS", "demo123")
MOCK_SOURCE_FILE = os.getenv("MOCK_SOURCE_FILE", "")
MOCK_REPLICATE_FACTOR = int(os.getenv("MOCK_REPLICATE_FACTOR", "1"))
MOCK_LIMIT_ROWS = int(os.getenv("MOCK_LIMIT_ROWS", "0"))

SOURCE_FIELDS = (
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
)


def _metadata(psid: str) -> dict[str, str]:
    entity_url = f"{METADATA_BASE_URL}{BASE_PATH}('{psid}')"
    return {
        "id": entity_url,
        "uri": entity_url,
        "type": "ZODATA_PS_MS_ALLOC_DET_API_SRV.IT_RES",
    }


def _build_dataset() -> list[dict[str, Any]]:
    return [
        {
            "__metadata": _metadata("00277262"),
            "LvFlag": "",
            "Guid": "974bc97f-79f5-1fd1-ab84-508db70efbbc",
            "Psid": "00277262",
            "EventType": "Project Change",
            "OldProjid": "119392-001",
            "NewProjid": "90025-003",
            "OldIrmid": "00717210",
            "OldIrmName": "Ashish Shalu",
            "NewIrmid": "00717210",
            "NewIrmName": "Ashish Shalu",
            "OldLocCode": "220",
            "OldLocDesc": "Pune-Godrej Eternia Shivajinagar",
            "NewLocCode": "220",
            "NewLocDesc": "Pune-Godrej Eternia Shivajinagar",
            "StartDate": "/Date(1788220800000)/",
            "EndDate": "/Date(253402214400000)/",
        },
        {
            "__metadata": _metadata("00278849"),
            "LvFlag": "",
            "Guid": "974bc97f-79f5-1fd1-ab84-508db70f1bbc",
            "Psid": "00278849",
            "EventType": "Project Change",
            "OldProjid": "25672-06",
            "NewProjid": "110286-001",
            "OldIrmid": "00722023",
            "OldIrmName": "Karthikeyan",
            "NewIrmid": "00722023",
            "NewIrmName": "Karthikeyan",
            "OldLocCode": "268",
            "OldLocDesc": "Chennai-Innovation Campus,Tw 2",
            "NewLocCode": "268",
            "NewLocDesc": "Chennai-Innovation Campus,Tw 2",
            "StartDate": "/Date(1788912000000)/",
            "EndDate": "/Date(1793318400000)/",
        },
    ]


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]

    if not isinstance(payload, dict):
        return []

    # OData V2: {"d": {"results": [...]}}
    d = payload.get("d")
    if isinstance(d, dict):
        results = d.get("results")
        if isinstance(results, list):
            return [x for x in results if isinstance(x, dict)]

    # Alternate forms.
    for key in ("results", "value", "items", "data"):
        maybe = payload.get(key)
        if isinstance(maybe, list):
            return [x for x in maybe if isinstance(x, dict)]

    return []


def _sanitize_row(row: dict[str, Any]) -> dict[str, Any]:
    sanitized = {"__metadata": row.get("__metadata", {})}
    sanitized.update({field: row.get(field, "") for field in SOURCE_FIELDS})

    psid = str(sanitized["Psid"])
    if not isinstance(sanitized["__metadata"], dict):
        sanitized["__metadata"] = _metadata(psid)
    else:
        sanitized["__metadata"] = {
            "id": str(sanitized["__metadata"].get("id", _metadata(psid)["id"])),
            "uri": str(sanitized["__metadata"].get("uri", _metadata(psid)["uri"])),
            "type": str(
                sanitized["__metadata"].get(
                    "type", "ZODATA_PS_MS_ALLOC_DET_API_SRV.IT_RES"
                )
            ),
        }
    return sanitized


def _replicate_rows(rows: list[dict[str, Any]], factor: int) -> list[dict[str, Any]]:
    if factor <= 1 or not rows:
        return rows

    expanded: list[dict[str, Any]] = []
    for batch in range(factor):
        for row in rows:
            new_row = _sanitize_row(row)

            if batch > 0:
                original_psid = str(new_row["Psid"])
                new_psid = f"{int(original_psid) + (batch * 100000):08d}"
                new_row["Psid"] = new_psid
                new_row["Guid"] = str(uuid5(NAMESPACE_URL, f"{new_row['Guid']}:{batch}"))
                new_row["__metadata"] = _metadata(new_psid)

            expanded.append(new_row)
    return expanded


def _load_dataset() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    if MOCK_SOURCE_FILE:
        src = Path(MOCK_SOURCE_FILE)
        if src.exists() and src.is_file():
            try:
                payload = json.loads(src.read_text(encoding="utf-8"))
                raw_rows = _extract_rows(payload)
                if raw_rows:
                    rows = [_sanitize_row(row) for row in raw_rows]
                    rows = _replicate_rows(rows, max(1, MOCK_REPLICATE_FACTOR))
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                rows = []

    if not rows:
        rows = _replicate_rows(_build_dataset(), max(1, MOCK_REPLICATE_FACTOR))

    if MOCK_LIMIT_ROWS > 0:
        return rows[:MOCK_LIMIT_ROWS]
    return rows


DATASET = _load_dataset()


def _check_auth(request: Request) -> None:
    if not REQUIRE_AUTH:
        return

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        raise HTTPException(status_code=401, detail="Missing Basic auth")

    try:
        token = auth.split(" ", 1)[1].strip()
        decoded = base64.b64decode(token).decode("utf-8")
        user, pwd = decoded.split(":", 1)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid Basic auth") from exc

    if user != MOCK_USER or pwd != MOCK_PASS:
        raise HTTPException(status_code=401, detail="Invalid credentials")


def _apply_filter(rows: list[dict[str, Any]], filter_expr: str | None) -> list[dict[str, Any]]:
    if not filter_expr:
        return rows

    clauses = [c.strip() for c in filter_expr.split(" and ") if c.strip()]

    def row_matches(row: dict[str, Any]) -> bool:
        for clause in clauses:
            if " eq " not in clause:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported $filter clause: {clause}",
                )
            left, right = clause.split(" eq ", 1)
            field = left.strip()
            value = right.strip().strip("'")

            if field not in SOURCE_FIELDS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported $filter field: {field}",
                )

            current = str(row.get(field, ""))
            if current != value:
                return False
        return True

    return [r for r in rows if row_matches(r)]


def _apply_order(rows: list[dict[str, Any]], order_expr: str | None) -> list[dict[str, Any]]:
    if not order_expr:
        return rows

    parts = order_expr.strip().split()
    key = parts[0]
    if key not in SOURCE_FIELDS:
        raise HTTPException(status_code=400, detail=f"Unsupported $orderby field: {key}")
    if len(parts) > 1 and parts[1].lower() not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="Use asc or desc for $orderby")
    reverse = len(parts) > 1 and parts[1].lower() == "desc"
    return sorted(rows, key=lambda r: str(r.get(key, "")), reverse=reverse)


def _apply_select(rows: list[dict[str, Any]], select_expr: str | None) -> list[dict[str, Any]]:
    if not select_expr:
        return rows

    fields = [f.strip() for f in select_expr.split(",") if f.strip()]
    if not fields:
        return rows
    unsupported = [field for field in fields if field not in SOURCE_FIELDS]
    if unsupported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported $select fields: {', '.join(unsupported)}",
        )
    return [{k: row.get(k) for k in fields} for row in rows]


def _next_link(request: Request, current_skip: int, top: int, total: int) -> str | None:
    next_skip = current_skip + top
    if next_skip >= total:
        return None

    qp = dict(request.query_params)
    qp["$skip"] = str(next_skip)
    encoded = urlencode(qp)
    return f"{request.base_url.scheme}://{request.url.netloc}{BASE_PATH}?{encoded}"


@app.get("/")
def health() -> dict[str, Any]:
    return {
        "name": "sap-odata-mock",
        "status": "ok",
        "service": "ZODATA_PS_MS_ALLOC_DET_API_SRV",
        "entitySet": "IT_RESSet",
        "path": BASE_PATH,
        "records": len(DATASET),
        "sourceFile": MOCK_SOURCE_FILE or "synthetic-default",
        "replicateFactor": max(1, MOCK_REPLICATE_FACTOR),
    }


@app.get(BASE_PATH)
def delta_events(request: Request) -> dict[str, Any]:
    _check_auth(request)

    q = request.query_params
    try:
        top = int(q.get("$top", "200"))
        skip = int(q.get("$skip", "0"))
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="$top and $skip must be integers"
        ) from exc

    orderby = q.get("$orderby")
    select = q.get("$select")
    filter_expr = q.get("$filter")
    response_format = q.get("$format", "json")

    if response_format.lower() != "json":
        raise HTTPException(status_code=400, detail="Only $format=json is supported")

    top = max(1, min(top, 500))
    skip = max(0, skip)

    filtered = _apply_filter(DATASET, filter_expr)
    ordered = _apply_order(filtered, orderby)

    page = ordered[skip : skip + top]
    page = _apply_select(page, select)

    next_url = _next_link(request, skip, top, len(ordered))

    return {
        "d": {
            "results": page,
            "__next": next_url,
        }
    }


@app.get(f"{BASE_PATH}('{{psid}}')")
def delta_event_by_psid(psid: str, request: Request) -> dict[str, Any]:
    _check_auth(request)

    for row in DATASET:
        if str(row.get("Psid", "")) == psid:
            return {"d": row}
    raise HTTPException(status_code=404, detail="SAP delta event not found")

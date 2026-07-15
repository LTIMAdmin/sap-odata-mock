import base64
import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="SAP OData Mock API", version="1.0.0")

BASE_PATH = "/sap/opu/odata/SAP/ZPS_ODATA_DATALAKE_SRV/PS_MANPOWER_REPORT_DATASet"
DEFAULT_EXDATE = os.getenv("MOCK_EXDATE", "06/01/2026")
REQUIRE_AUTH = os.getenv("MOCK_REQUIRE_AUTH", "false").lower() == "true"
MOCK_USER = os.getenv("MOCK_USER", "demo")
MOCK_PASS = os.getenv("MOCK_PASS", "demo123")
MOCK_SOURCE_FILE = os.getenv("MOCK_SOURCE_FILE", "")
MOCK_REPLICATE_FACTOR = int(os.getenv("MOCK_REPLICATE_FACTOR", "1"))
MOCK_LIMIT_ROWS = int(os.getenv("MOCK_LIMIT_ROWS", "0"))


def _build_dataset(count: int = 1200) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base_project = 90000
    managers = ["Srinivas Veluvali", "Deepak Vupperige", "Darshan Hardas", "Ankur Gupta"]

    for i in range(count):
        emp = f"{123000 + i:08d}"
        project_num = base_project + (i % 40)
        project = f"{project_num}-{(i % 10) + 1:03d}"
        start = date(2025, 1, 1) + timedelta(days=i % 180)
        end = date(9999, 12, 31)
        resigned = "Yes" if i % 37 == 0 else "No"

        rows.append(
            {
                "Pernr": emp,
                "Ename": f"Employee {i + 1}",
                "ProjectId": project,
                "ProjectName": f"Program {project_num}",
                "StartDate": start.strftime("%m/%d/%Y"),
                "EndDate": end.strftime("%m/%d/%Y"),
                "Allocation": "100.00",
                "Resigned": resigned,
                "ExDate": DEFAULT_EXDATE,
                "ReptManager": managers[i % len(managers)],
                "PsManager": f"{10670000 + i % 200}",
            }
        )
    return rows


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


def _get_first_value(row: dict[str, Any], keys: list[str], default: str = "") -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    # Keep original fields for flexibility.
    normalized: dict[str, Any] = dict(row)

    # Add canonical aliases expected by your flow.
    normalized.setdefault(
        "Pernr",
        _get_first_value(row, ["Pernr", "pernr", "EmployeeId", "employeeId", "EmpId", "empId"], ""),
    )
    normalized.setdefault(
        "Ename",
        _get_first_value(row, ["Ename", "ename", "EmployeeName", "employeeName", "Name", "name"], ""),
    )
    normalized.setdefault(
        "ProjectId",
        _get_first_value(
            row,
            ["ProjectId", "projectId", "NewProjectId", "newProjectId", "ToProjectId", "toProjectId"],
            "",
        ),
    )
    normalized.setdefault(
        "ProjectName",
        _get_first_value(row, ["ProjectName", "projectName", "NewProjectName", "newProjectName"], ""),
    )
    normalized.setdefault(
        "StartDate",
        _get_first_value(row, ["StartDate", "startDate", "AllocationStartDate", "allocationStartDate"], ""),
    )
    normalized.setdefault(
        "EndDate",
        _get_first_value(row, ["EndDate", "endDate", "AllocationEndDate", "allocationEndDate"], "12/31/9999"),
    )
    normalized.setdefault(
        "Allocation",
        _get_first_value(row, ["Allocation", "allocation", "AllocationPct", "allocationPct"], "100.00"),
    )
    normalized.setdefault(
        "Resigned",
        _get_first_value(row, ["Resigned", "resigned", "IsResigned", "isResigned"], "No"),
    )
    normalized.setdefault(
        "ExDate",
        _get_first_value(
            row,
            ["ExDate", "exDate", "ExtractDate", "extractDate", "EventDate", "eventDate"],
            DEFAULT_EXDATE,
        ),
    )
    normalized.setdefault(
        "ReptManager",
        _get_first_value(row, ["ReptManager", "reptManager", "Manager", "manager"], ""),
    )
    normalized.setdefault(
        "PsManager",
        _get_first_value(row, ["PsManager", "psManager", "ManagerId", "managerId"], ""),
    )

    return normalized


def _replicate_rows(rows: list[dict[str, Any]], factor: int) -> list[dict[str, Any]]:
    if factor <= 1 or not rows:
        return rows

    expanded: list[dict[str, Any]] = []
    for batch in range(factor):
        for i, row in enumerate(rows):
            new_row = dict(row)

            # Keep records unique across replicated batches.
            if batch > 0:
                pernr = str(new_row.get("Pernr", ""))
                if pernr:
                    new_row["Pernr"] = f"{pernr}-{batch:03d}"
                else:
                    new_row["Pernr"] = f"MOCK-{i + 1:08d}-{batch:03d}"

            expanded.append(new_row)
    return expanded


def _load_dataset() -> list[dict[str, Any]]:
    if not MOCK_SOURCE_FILE:
        return _build_dataset()

    src = Path(MOCK_SOURCE_FILE)
    if not src.exists() or not src.is_file():
        return _build_dataset()

    try:
        payload = json.loads(src.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return _build_dataset()

    raw_rows = _extract_rows(payload)
    if not raw_rows:
        return _build_dataset()

    mapped = [_normalize_row(row) for row in raw_rows]
    expanded = _replicate_rows(mapped, max(1, MOCK_REPLICATE_FACTOR))

    if MOCK_LIMIT_ROWS > 0:
        return expanded[:MOCK_LIMIT_ROWS]
    return expanded


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

    # Supports simple clauses joined by 'and': Field eq 'Value'
    clauses = [c.strip() for c in filter_expr.split(" and ") if c.strip()]

    def row_matches(row: dict[str, Any]) -> bool:
        for clause in clauses:
            if " eq " not in clause:
                continue
            left, right = clause.split(" eq ", 1)
            field = left.strip()
            value = right.strip().strip("'")

            # These are SAP parameter-style filters used in your tests.
            # They are accepted and treated as request-level constraints.
            if field in {"IStartDate", "IEndDate", "IInterfaceId", "ISystemId"}:
                if field == "IStartDate" and value != DEFAULT_EXDATE:
                    return False
                if field == "IEndDate" and value != DEFAULT_EXDATE:
                    return False
                if field == "IInterfaceId" and value != "PS_MANPOWER_RPT":
                    return False
                if field == "ISystemId" and value != "DATALAKE":
                    return False
                continue

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
    reverse = len(parts) > 1 and parts[1].lower() == "desc"
    return sorted(rows, key=lambda r: str(r.get(key, "")), reverse=reverse)


def _apply_select(rows: list[dict[str, Any]], select_expr: str | None) -> list[dict[str, Any]]:
    if not select_expr:
        return rows

    fields = [f.strip() for f in select_expr.split(",") if f.strip()]
    if not fields:
        return rows
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
        "path": BASE_PATH,
        "records": len(DATASET),
        "sourceFile": MOCK_SOURCE_FILE or "synthetic-default",
        "replicateFactor": max(1, MOCK_REPLICATE_FACTOR),
    }


@app.get(BASE_PATH)
def manpower_dataset(request: Request) -> dict[str, Any]:
    _check_auth(request)

    q = request.query_params
    top = int(q.get("$top", "200"))
    skip = int(q.get("$skip", "0"))
    orderby = q.get("$orderby")
    select = q.get("$select")
    filter_expr = q.get("$filter")

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

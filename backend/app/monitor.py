"""
Skyline Monitor: read-only analytics over the Skyline voice agent's telemetry.

Sources
  - Log Analytics (App Insights, workspace-based): API usage, latency, cache I/O, agent spans
  - Table Storage "ApiCache": cache state and lookup keys (routes, flights)

Auth: azure-identity DefaultAzureCredential. Locally this uses `az login`; on Render set
AZURE_TENANT_ID / AZURE_CLIENT_ID / AZURE_CLIENT_SECRET for a read-only service principal
(Log Analytics Reader + Storage Table Data Reader).

Env:
  MONITOR_WORKSPACE_ID     Log Analytics workspace (customer) ID
  MONITOR_STORAGE_ACCOUNT  storage account name (default skylinedemo13038)
  MONITOR_TABLE            cache table name (default ApiCache)
  MONITOR_ACCESS_KEY       optional shared key, sent by clients as X-Monitor-Key
"""
from __future__ import annotations

import os
import time
from collections import Counter
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Query

router = APIRouter(prefix="/api/monitor", tags=["monitor"])

WORKSPACE_ID = os.getenv("MONITOR_WORKSPACE_ID", "")
STORAGE_ACCOUNT = os.getenv("MONITOR_STORAGE_ACCOUNT", "skylinedemo13038")
TABLE_NAME = os.getenv("MONITOR_TABLE", "ApiCache")
ACCESS_KEY = os.getenv("MONITOR_ACCESS_KEY", "")

RANGES = {"24h": "1d", "7d": "7d", "30d": "30d"}

# Approximate coordinates for the heatmap (IATA -> lat, lon). Unknown airports are still counted.
AIRPORT_COORDS: Dict[str, tuple] = {
    "JFK": (40.64, -73.78), "LAX": (33.94, -118.41), "ORD": (41.98, -87.90), "ATL": (33.64, -84.43),
    "SFO": (37.62, -122.38), "MIA": (25.79, -80.29), "DFW": (32.90, -97.04), "SEA": (47.45, -122.31),
    "BOS": (42.36, -71.01), "LHR": (51.47, -0.46), "CDG": (49.01, 2.55), "FRA": (50.04, 8.56),
    "AMS": (52.31, 4.76), "MAD": (40.49, -3.57), "DXB": (25.25, 55.36), "DOH": (25.27, 51.61),
    "SIN": (1.36, 103.99), "HND": (35.55, 139.78), "NRT": (35.77, 140.39), "HKG": (22.31, 113.91),
    "SYD": (-33.94, 151.18), "DEL": (28.56, 77.10), "BOM": (19.09, 72.87), "YYZ": (43.68, -79.63),
    "MEX": (19.44, -99.07), "IST": (41.28, 28.74), "LGA": (40.78, -73.87), "EWR": (40.69, -74.17),
}

_cred = None
_tokens: Dict[str, Any] = {}


def _token(scope: str) -> str:
    """Cached bearer token for the given scope."""
    global _cred
    cached = _tokens.get(scope)
    if cached and cached[1] - 120 > time.time():
        return cached[0]
    if _cred is None:
        from azure.identity import DefaultAzureCredential  # lazy: optional dependency

        _cred = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    tok = _cred.get_token(scope)
    _tokens[scope] = (tok.token, tok.expires_on)
    return tok.token


def require_access(x_monitor_key: Optional[str] = Header(default=None)) -> None:
    if ACCESS_KEY and x_monitor_key != ACCESS_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing monitor access key")


def _kql(query: str) -> List[Dict[str, Any]]:
    if not WORKSPACE_ID:
        raise HTTPException(status_code=503, detail="MONITOR_WORKSPACE_ID is not configured")
    try:
        r = requests.post(
            f"https://api.loganalytics.io/v1/workspaces/{WORKSPACE_ID}/query",
            headers={"Authorization": f"Bearer {_token('https://api.loganalytics.io/.default')}"},
            json={"query": query},
            timeout=40,
        )
    except Exception as e:  # credential or network failure
        raise HTTPException(status_code=502, detail=f"Log Analytics unreachable: {e}")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Log Analytics error {r.status_code}: {r.text[:900]}")
    t = r.json()["tables"][0]
    cols = [c["name"] for c in t["columns"]]
    return [dict(zip(cols, row)) for row in t["rows"]]


def _cache_rows(limit: int = 5000) -> List[Dict[str, Any]]:
    """Read ApiCache rows (Key, Timestamp, ExpiresAt only), following continuation tokens."""
    headers = {
        "Authorization": f"Bearer {_token('https://storage.azure.com/.default')}",
        "x-ms-version": "2020-12-06",
        "Accept": "application/json;odata=nometadata",
    }
    url = f"https://{STORAGE_ACCOUNT}.table.core.windows.net/{TABLE_NAME}()"
    params: Dict[str, Any] = {"$select": "Key,Timestamp,ExpiresAt,Payload", "$top": 1000}
    rows: List[Dict[str, Any]] = []
    while len(rows) < limit:
        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Table Storage unreachable: {e}")
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Table Storage error {r.status_code}: {r.text[:200]}")
        rows.extend(r.json().get("value", []))
        pk, rk = r.headers.get("x-ms-continuation-NextPartitionKey"), r.headers.get("x-ms-continuation-NextRowKey")
        if not pk:
            break
        params["NextPartitionKey"], params["NextRowKey"] = pk, rk
    return rows


def _range(r: str) -> str:
    if r not in RANGES:
        raise HTTPException(status_code=400, detail=f"range must be one of {list(RANGES)}")
    return RANGES[r]


@router.get("/status", dependencies=[Depends(require_access)])
def status() -> Dict[str, Any]:
    return {
        "workspace_configured": bool(WORKSPACE_ID),
        "storage_account": STORAGE_ACCOUNT,
        "table": TABLE_NAME,
        "access_key_required": bool(ACCESS_KEY),
    }


@router.get("/usage", dependencies=[Depends(require_access)])
def usage(range: str = Query("7d")) -> Dict[str, Any]:
    """Calls, latency and failures per Function endpoint, plus agent-side tool and model activity."""
    ago = _range(range)
    step = "1h" if ago == "1d" else "1d"
    tools = _kql(
        f"AppRequests | where TimeGenerated > ago({ago}) | where Url contains 'azurewebsites' "
        "| summarize calls=count(), p50=percentile(DurationMs, 50), p95=percentile(DurationMs, 95), "
        "failures=countif(tostring(Success) =~ 'false') by Name | order by calls desc"
    )
    for r in tools:
        r["tool"] = r.get("Name")
    series = _kql(
        f"AppRequests | where TimeGenerated > ago({ago}) | where Url contains 'azurewebsites' "
        f"| summarize calls=count() by bucket=bin(TimeGenerated, {step}), Name | order by bucket asc"
    )
    for r in series:
        r["tool"] = r.get("Name")
    agent = _kql(
        f"AppDependencies | where TimeGenerated > ago({ago}) "
        "| summarize calls=count(), avg_ms=avg(DurationMs) by Name | order by calls desc"
    )
    labels = (
        ("execute_tool", "tool call"),
        ("chat", "model turn"),
        ("text_to_speech", "speech out"),
        ("speech_to_text", "speech in"),
    )
    agent_rows = []
    for r in agent:
        nm = r.get("Name") or ""
        for prefix, label in labels:
            if nm.startswith(prefix):
                agent_rows.append({"kind": label, "name": nm, "calls": r["calls"], "avg_ms": r["avg_ms"]})
                break
    agent = agent_rows
    return {"range": range, "tools": tools, "series": series, "agent": agent}


@router.get("/cache", dependencies=[Depends(require_access)])
def cache(range: str = Query("7d")) -> Dict[str, Any]:
    """Cache I/O from Table Storage traffic (approximation) and live cache state from the table."""
    ago = _range(range)
    io = _kql(
        f"""AppTraces | where TimeGenerated > ago({ago})
        | where Message startswith 'Response status:'
        | summarize n=count() by status=substring(Message, 17, 3)"""
    )
    counts = {row["status"]: row["n"] for row in io}
    hits, misses, writes = counts.get("200", 0), counts.get("404", 0), counts.get("204", 0)
    lookups = hits + misses

    now = time.time()
    rows = _cache_rows()
    by_type: Counter = Counter()
    warm = 0
    entries: List[Dict[str, Any]] = []
    for row in rows:
        key = row.get("Key") or "unknown"
        by_type[key.split("|")[0]] += 1
        try:
            exp = float(row.get("ExpiresAt") or 0)
        except (TypeError, ValueError):
            exp = 0.0
        is_warm = exp > now
        if is_warm:
            warm += 1
        entries.append({
            "key": key,
            "type": key.split("|")[0],
            "stored": row.get("Timestamp"),
            "expires_in_min": round((exp - now) / 60) if exp else None,
            "warm": is_warm,
            "size_bytes": len(row.get("Payload") or ""),
        })
    entries.sort(key=lambda e: e.get("stored") or "", reverse=True)
    return {
        "range": range,
        "io": {
            "hits": hits,
            "misses": misses,
            "writes": writes,
            "hit_rate": round(hits / lookups, 3) if lookups else None,
            "note": "Approximation from Table Storage response codes (200 = hit, 404 = miss, 204 = write).",
        },
        "state": {"entries": len(rows), "warm": warm, "expired": len(rows) - warm, "by_type": dict(by_type),
                  "items": entries[:100], "total_bytes": sum(e["size_bytes"] for e in entries)},
    }


@router.get("/heatmap", dependencies=[Depends(require_access)])
def heatmap() -> Dict[str, Any]:
    """Airport demand from cached lookup keys (board|ORIGIN|DEST|...). Counts distinct cached lookups."""
    origins: Counter = Counter()
    dests: Counter = Counter()
    pairs: Counter = Counter()
    for row in _cache_rows():
        parts = (row.get("Key") or "").split("|")
        if parts[0] == "board" and len(parts) >= 3:
            o, d = parts[1].upper(), parts[2].upper()
            origins[o] += 1
            dests[d] += 1
            pairs[(o, d)] += 1

    def points(counter: Counter) -> List[Dict[str, Any]]:
        out = []
        for code, n in counter.most_common():
            lat, lon = AIRPORT_COORDS.get(code, (None, None))
            out.append({"airport": code, "count": n, "lat": lat, "lon": lon})
        return out

    return {
        "origins": points(origins),
        "destinations": points(dests),
        "routes": [{"origin": o, "destination": d, "count": n} for (o, d), n in pairs.most_common(50)],
        "note": "Counts distinct cached schedule lookups, not total searches. Repeat searches within the cache TTL are not counted.",
    }

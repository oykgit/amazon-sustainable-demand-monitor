"""Offline evidence-quality analysis of operator-supplied dated price/BSR observations.

This is NOT Keepa normalization, proof of sales, or a purchasing signal.
"""
import calendar
import math
from datetime import date, datetime, timedelta, timezone
from statistics import median

REQUIRED = ("asin", "market", "observed_date", "source_provider", "source_reference",
            "evidence_type", "value")
ALLOWED_TYPES = {"PRICE_EUR", "SALES_RANK"}
ALLOWED_MARKETS = {"UK", "IE"}

def _number(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a measurement")
    try:
        n = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Measurement must be numeric") from None
    if not math.isfinite(n) or n <= 0:
        raise ValueError("Measurement must be finite and positive")
    return n

def _month_back(day):
    year = day.year - (1 if day.month == 1 else 0)
    month = day.month - 1 if day.month > 1 else 12
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))

def _year_back(day):
    year = day.year - 1
    return date(year, day.month, min(day.day, calendar.monthrange(year, day.month)[1]))

def analyse(rows, as_of=None):
    """Return an offline quality report. All supplied rows must be valid."""
    as_of = as_of or datetime.now(timezone.utc).date()
    if isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)
    if not isinstance(as_of, date):
        raise ValueError("Invalid as_of date")
    if len(rows) > 5000:
        raise ValueError("Maximum 5000 rows per offline analysis")
    normalized = []
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or any(k not in row for k in REQUIRED):
            raise ValueError(f"Row {i}: missing required fields")
        asin = str(row["asin"]).strip().upper()
        market = str(row["market"]).strip().upper()
        kind = str(row["evidence_type"]).strip().upper()
        source = str(row["source_provider"]).strip()
        reference = str(row["source_reference"]).strip()
        if len(asin) != 10 or not asin.isascii() or not asin.isalnum():
            raise ValueError(f"Row {i}: invalid ASIN")
        if market not in ALLOWED_MARKETS or kind not in ALLOWED_TYPES:
            raise ValueError(f"Row {i}: unsupported market or evidence type")
        if not source or not reference or len(source) > 200 or len(reference) > 1000:
            raise ValueError(f"Row {i}: source provenance required")
        try:
            observed = date.fromisoformat(str(row["observed_date"]).strip())
        except ValueError:
            raise ValueError(f"Row {i}: invalid ISO observation date") from None
        if observed > as_of:
            raise ValueError(f"Row {i}: future observation date")
        val = _number(row["value"])
        if kind == "SALES_RANK" and (not val.is_integer() or val > 100_000_000):
            raise ValueError(f"Row {i}: invalid sales rank")
        if kind == "PRICE_EUR" and val > 1_000_000:
            raise ValueError(f"Row {i}: implausible price")
        normalized.append((asin, market, kind, observed, val, source, reference))
    groups = {}
    for rec in normalized:
        groups.setdefault(rec[:3], []).append(rec)
    cutoff = _year_back(as_of)
    reports = []
    for (asin, market, kind), entries in sorted(groups.items()):
        recent = [r for r in entries if cutoff <= r[3] <= as_of]
        dates = sorted({r[3] for r in recent})
        monthly = {(d.year, d.month) for d in dates}
        expected_months = set()
        cursor = date(cutoff.year, cutoff.month, 1)
        end = date(as_of.year, as_of.month, 1)
        while cursor <= end:
            expected_months.add((cursor.year, cursor.month))
            cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
        values = [r[4] for r in recent]
        source_pairs = {(r[5], r[6]) for r in recent}
        dupes = len(recent) - len({(r[3], r[5], r[6], r[4]) for r in recent})
        sufficient = len(monthly) >= 10 and len(dates) >= 12 and min(dates, default=as_of) <= cutoff + timedelta(days=45) and max(dates, default=cutoff) >= as_of - timedelta(days=45)
        report = {
            "asin": asin, "market": market, "evidence_type": kind,
            "observations_last_12_months": len(recent),
            "distinct_dates": len(dates),
            "months_with_observations": len(monthly),
            "months_in_window": len(expected_months),
            "missing_months": [f"{y:04d}-{m:02d}" for y, m in sorted(expected_months - monthly)],
            "first_date": dates[0].isoformat() if dates else None,
            "last_date": dates[-1].isoformat() if dates else None,
            "source_references": len(source_pairs),
            "duplicate_observations": dupes,
            "median_observed_value": median(values) if values else None,
            "minimum_observed_value": min(values) if values else None,
            "maximum_observed_value": max(values) if values else None,
            "coverage_gate": "SUFFICIENT_FOR_DESCRIPTIVE_REVIEW" if sufficient else "INSUFFICIENT",
            "provider_origin_authenticated": False,
            "amazon_sales_volume_verified": False,
            "sustained_demand_verified": False,
            "note": ("Rank is not unit sales; trends may reflect category changes, "
                     "stockouts and sampling bias." if kind == "SALES_RANK"
                     else "Price observations are not sales or demand evidence; EUR conversion must be documented.")
        }
        reports.append(report)
    return {
        "mode": "HISTORICAL_EVIDENCE_OFFLINE_READ_ONLY",
        "as_of": as_of.isoformat(),
        "input_rows": len(normalized),
        "groups": reports,
        "network_requests": 0, "database_writes": 0, "purchases_enabled": False,
        "historical_demand_verified": False,
        "note": "Operator-supplied evidence is not provider-authenticated. Coverage is a descriptive screening gate, not a demand validation."
    }

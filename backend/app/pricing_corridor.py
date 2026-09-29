"""
Dynamic Pricing Corridor module for aircraft parts.
Ports the structure of the Aerfin_Analysis Power BI report:
  - Part-level sales data (PartNumber, PartClassDescription, PartConditionCodeDescription,
    YearInvoiced, MonthInvoiced, InvoiceUnitPrice, AverageSalesHistPrice, AverageHistQuotePrice)
  - Pricing corridor bands (RedPrice, AmberPrice, GreenPrice, Corridor) representing a
    traffic-light pricing guidance system: Green = healthy margin, Amber = caution,
    Red = below-floor / at-risk pricing.

Since the original .pbix embeds its dataset in a binary data model, this module generates
a realistic synthetic dataset with the same schema so the dashboard is fully self-contained
and runs offline.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

PART_CLASSES = ["ENGINE", "AIRFRAME", "AVIONICS", "LANDING GEAR", "APU"]
CONDITIONS = ["Overhauled", "Serviceable", "New", "As Removed", "Repaired"]
YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
MONTHS = list(range(1, 13))

PART_PREFIXES = {
    "ENGINE": ["CFM56", "V2500", "PW4000", "GE90", "LEAP"],
    "AIRFRAME": ["A320-FRM", "B737-FRM", "A350-FRM", "B777-FRM"],
    "AVIONICS": ["ARINC", "FMS", "TCAS", "ADIRU"],
    "LANDING GEAR": ["LG-MLG", "LG-NLG", "LG-BRK"],
    "APU": ["APU-131", "APU-36", "APU-85"],
}


def _generate_dataset(n_rows: int = 1200) -> pd.DataFrame:
    rows = []
    # Generate a pool of distinct part numbers with a stable "base price" each
    n_parts = 140
    parts = []
    for i in range(n_parts):
        cls = random.choice(PART_CLASSES)
        prefix = random.choice(PART_PREFIXES[cls])
        part_number = f"{prefix}-{1000 + i}"
        base_price = {
            "ENGINE": np.random.uniform(40000, 260000),
            "AIRFRAME": np.random.uniform(8000, 90000),
            "AVIONICS": np.random.uniform(3000, 45000),
            "LANDING GEAR": np.random.uniform(15000, 120000),
            "APU": np.random.uniform(20000, 150000),
        }[cls]
        parts.append({"part_number": part_number, "part_class": cls, "base_price": base_price})

    for _ in range(n_rows):
        p = random.choice(parts)
        year = random.choice(YEARS)
        month = random.choice(MONTHS)
        condition = random.choice(CONDITIONS)
        condition_factor = {
            "New": 1.35,
            "Serviceable": 1.05,
            "Overhauled": 1.0,
            "Repaired": 0.85,
            "As Removed": 0.55,
        }[condition]

        # Historical quote/sales prices with some noise
        hist_quote = p["base_price"] * condition_factor * np.random.uniform(0.92, 1.08)
        hist_sales = p["base_price"] * condition_factor * np.random.uniform(0.88, 1.04)

        # Pricing corridor bands (traffic light) centered around historical average
        center = (hist_quote + hist_sales) / 2
        green_price = center * 1.08
        amber_price = center * 0.95
        red_price = center * 0.80

        # Actual invoiced price - sometimes healthy, sometimes discounted (creates spread across bands)
        noise_roll = np.random.random()
        if noise_roll < 0.55:
            invoice_price = center * np.random.uniform(0.98, 1.15)  # near/above green -> healthy
        elif noise_roll < 0.85:
            invoice_price = center * np.random.uniform(0.83, 0.97)  # amber zone
        else:
            invoice_price = center * np.random.uniform(0.55, 0.82)  # red zone / risk

        if invoice_price >= green_price:
            corridor = "Green"
        elif invoice_price >= amber_price:
            corridor = "Amber"
        else:
            corridor = "Red"

        rows.append(
            {
                "PartNumber": p["part_number"],
                "PartClassDescription": p["part_class"],
                "PartConditionCodeDescription": condition,
                "YearInvoiced": year,
                "MonthInvoiced": month,
                "InvoiceUnitPrice": round(float(invoice_price), 2),
                "AverageSalesHistPrice": round(float(hist_sales), 2),
                "AverageHistQuotePrice": round(float(hist_quote), 2),
                "RedPrice": round(float(red_price), 2),
                "AmberPrice": round(float(amber_price), 2),
                "GreenPrice": round(float(green_price), 2),
                "Corridor": corridor,
            }
        )

    return pd.DataFrame(rows)


DATASET: pd.DataFrame = _generate_dataset()

CORRIDOR_COLOR = {"Green": "#34d399", "Amber": "#facc15", "Red": "#f87171"}


def _apply_filters(
    df: pd.DataFrame,
    part_class: Optional[List[str]] = None,
    condition: Optional[List[str]] = None,
    year: Optional[List[int]] = None,
    part_number: Optional[List[str]] = None,
) -> pd.DataFrame:
    out = df
    if part_class:
        out = out[out["PartClassDescription"].isin(part_class)]
    if condition:
        out = out[out["PartConditionCodeDescription"].isin(condition)]
    if year:
        out = out[out["YearInvoiced"].isin(year)]
    if part_number:
        out = out[out["PartNumber"].isin(part_number)]
    return out


def get_filter_options() -> Dict[str, Any]:
    return {
        "part_classes": sorted(DATASET["PartClassDescription"].unique().tolist()),
        "conditions": sorted(DATASET["PartConditionCodeDescription"].unique().tolist()),
        "years": sorted(int(y) for y in DATASET["YearInvoiced"].unique().tolist()),
        "part_numbers": sorted(DATASET["PartNumber"].unique().tolist()),
    }


def get_kpis(**filters) -> Dict[str, Any]:
    df = _apply_filters(DATASET, **filters)
    total_parts = int(df["PartNumber"].nunique())
    total_invoice_value = float(df["InvoiceUnitPrice"].sum())
    avg_invoice_price = float(df["InvoiceUnitPrice"].mean()) if len(df) else 0.0
    corridor_counts = df["Corridor"].value_counts().to_dict()
    total = len(df) or 1
    corridor_pct = {
        "Green": round(corridor_counts.get("Green", 0) / total * 100, 1),
        "Amber": round(corridor_counts.get("Amber", 0) / total * 100, 1),
        "Red": round(corridor_counts.get("Red", 0) / total * 100, 1),
    }
    return {
        "total_parts": total_parts,
        "total_records": int(len(df)),
        "total_invoice_value": round(total_invoice_value, 2),
        "avg_invoice_price": round(avg_invoice_price, 2),
        "corridor_counts": {k: int(v) for k, v in corridor_counts.items()},
        "corridor_pct": corridor_pct,
    }


def get_scatter_data(**filters) -> Dict[str, Any]:
    df = _apply_filters(DATASET, **filters)
    points = [
        {
            "x": float(r.InvoiceUnitPrice),
            "y": float(r.AmberPrice),
            "green": float(r.GreenPrice),
            "red": float(r.RedPrice),
            "corridor": r.Corridor,
            "part_number": r.PartNumber,
            "part_class": r.PartClassDescription,
        }
        for r in df.itertuples()
    ]
    return {"points": points, "count": len(points)}


def get_corridor_table(**filters) -> Dict[str, Any]:
    df = _apply_filters(DATASET, **filters)
    if df.empty:
        return {"rows": []}
    grouped = (
        df.groupby("Corridor")
        .agg(
            part_count=("PartNumber", "nunique"),
            invoice_sum=("InvoiceUnitPrice", "sum"),
            red_sum=("RedPrice", "sum"),
            amber_sum=("AmberPrice", "sum"),
            green_sum=("GreenPrice", "sum"),
        )
        .reset_index()
        .sort_values("amber_sum", ascending=False)
    )
    rows = [
        {
            "corridor": r.Corridor,
            "part_count": int(r.part_count),
            "invoice_sum": round(float(r.invoice_sum), 2),
            "red_sum": round(float(r.red_sum), 2),
            "amber_sum": round(float(r.amber_sum), 2),
            "green_sum": round(float(r.green_sum), 2),
        }
        for r in grouped.itertuples()
    ]
    return {"rows": rows}


def get_trend_data(**filters) -> Dict[str, Any]:
    df = _apply_filters(DATASET, **filters)
    if df.empty:
        return {"series": []}
    grouped = (
        df.groupby(["PartClassDescription", "YearInvoiced"])
        .agg(
            invoice_avg=("InvoiceUnitPrice", "mean"),
            red_avg=("RedPrice", "mean"),
            amber_avg=("AmberPrice", "mean"),
            green_avg=("GreenPrice", "mean"),
        )
        .reset_index()
        .sort_values(["PartClassDescription", "YearInvoiced"])
    )
    series = [
        {
            "part_class": r.PartClassDescription,
            "year": int(r.YearInvoiced),
            "invoice_avg": round(float(r.invoice_avg), 2),
            "red_avg": round(float(r.red_avg), 2),
            "amber_avg": round(float(r.amber_avg), 2),
            "green_avg": round(float(r.green_avg), 2),
        }
        for r in grouped.itertuples()
    ]
    return {"series": series}


def get_yearly_bar(**filters) -> Dict[str, Any]:
    df = _apply_filters(DATASET, **filters)
    if df.empty:
        return {"bars": []}
    grouped = (
        df.groupby("YearInvoiced")
        .agg(part_count=("PartNumber", "count"), invoice_sum=("InvoiceUnitPrice", "sum"))
        .reset_index()
        .sort_values("YearInvoiced")
    )
    bars = [
        {"year": int(r.YearInvoiced), "part_count": int(r.part_count), "invoice_sum": round(float(r.invoice_sum), 2)}
        for r in grouped.itertuples()
    ]
    return {"bars": bars}


def get_class_pie(**filters) -> Dict[str, Any]:
    df = _apply_filters(DATASET, **filters)
    if df.empty:
        return {"slices": []}
    grouped = df.groupby("PartClassDescription").size().reset_index(name="count").sort_values("count", ascending=False)
    slices = [{"label": r.PartClassDescription, "value": int(r.count)} for r in grouped.itertuples()]
    return {"slices": slices}

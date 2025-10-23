# ec_fetch.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import datetime as dt
from pathlib import Path
import sys
import pandas as pd

# Submodul-Pfad
BASE_DIR = Path(__file__).resolve().parent
SUBMODULE_ROOT = (BASE_DIR / "libs" / "energy-charts").resolve()
sys.path.insert(0, str(SUBMODULE_ROOT))

from app.api import EnergyChartsAPI
from app.enums import Countries
from app.parser import make_dataframe


def last_full_week() -> tuple[dt.date, dt.date]:
    today = dt.date.today()
    weekday = today.weekday()
    start = today - dt.timedelta(days=weekday + 7)
    end = start + dt.timedelta(days=7)
    return start, end


def _to_date(d: str | dt.date | dt.datetime) -> dt.date:
    if isinstance(d, dt.datetime):
        return d.date()
    if isinstance(d, dt.date):
        return d
    return dt.date.fromisoformat(str(d))


def fetch_public_power(
    start: str | dt.date | dt.datetime,
    end: str | dt.date | dt.datetime,
    country=Countries.GERMANY,
) -> pd.DataFrame:
    """Hole Public Power Daten für beliebiges Zeitfenster [start, end)."""
    s = _to_date(start)
    e = _to_date(end)
    if e <= s:
        raise ValueError("end muss nach start liegen (exklusiv).")

    api = EnergyChartsAPI()
    resp = api.get_public_power(country=country, start=s.isoformat(), end=e.isoformat(), subtype=None)
    if not resp:
        raise RuntimeError("Leere Antwort vom Submodul (get_public_power).")

    df_raw = make_dataframe(resp)
    if "timestamp" not in df_raw.columns:
        raise RuntimeError("Parser-Ergebnis enthält keine 'timestamp'-Spalte.")

    mask = (df_raw["timestamp"] >= pd.Timestamp(s)) & (df_raw["timestamp"] < pd.Timestamp(e))
    return df_raw.loc[mask].reset_index(drop=True)


def fetch_public_power_week_de(start=None, end=None) -> pd.DataFrame:
    if start is None or end is None:
        start, end = last_full_week()
    return fetch_public_power(start, end, country=Countries.GERMANY)

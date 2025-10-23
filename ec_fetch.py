# ec_fetch.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import datetime as dt
from pathlib import Path
import sys
import pandas as pd

# -----------------------------------------------------------
# Submodul einbinden: Elternordner von "app" auf sys.path
# Erwartete Struktur: <repo>/libs/energy-charts/app/{api.py,enums.py,parser.py,...}
# -----------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
SUBMODULE_ROOT = (BASE_DIR / "libs" / "energy-charts").resolve()
sys.path.insert(0, str(SUBMODULE_ROOT))  # wichtig für "from app import ..."

from app.api import EnergyChartsAPI
from app.enums import Countries
from app.parser import make_dataframe


def last_full_week() -> tuple[dt.date, dt.date]:
    """Letzte volle Woche (Mo–So), end exklusiv."""
    today = dt.date.today()
    weekday = today.weekday()  # Mo=0..So=6
    start = today - dt.timedelta(days=weekday + 7)
    end = start + dt.timedelta(days=7)
    return start, end


def fetch_public_power_week_de(
    start: dt.date | None = None,
    end: dt.date | None = None,
) -> pd.DataFrame:
    """
    Holt den öffentlichen Leistungs-Mix (Public Power) für Deutschland (DE)
    ausschließlich über das Submodul und gibt den „rohen“ DataFrame zurück,
    wie ihn euer Parser erzeugt (timestamp + viele Spalten).
    """
    if start is None or end is None:
        start, end = last_full_week()

    api = EnergyChartsAPI()
    resp = api.get_public_power(
        country=Countries.GERMANY,
        start=start.isoformat(),
        end=end.isoformat(),
        subtype=None,
    )
    if not resp:
        raise RuntimeError("Leere Antwort vom Submodul (get_public_power).")

    df_raw = make_dataframe(resp)
    if "timestamp" not in df_raw.columns:
        raise RuntimeError("Parser-Ergebnis enthält keine 'timestamp'-Spalte.")

    # robust auf Mo–So zuschneiden
    mask = (df_raw["timestamp"] >= pd.Timestamp(start)) & (df_raw["timestamp"] < pd.Timestamp(end))
    return df_raw.loc[mask].reset_index(drop=True)

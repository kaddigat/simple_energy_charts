# plot_power_mix.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import matplotlib.pyplot as plt
import pandas as pd

from ec_fetch import fetch_public_power_week_de, last_full_week
from ec_transform import transform_df

def main():
    # 1) Live abrufen (DE, letzte volle Woche)
    df_raw = fetch_public_power_week_de()

    # 2) In drei DataFrames aufteilen (hard-coded)
    df_erzeuger, df_ausgleich, df_aggregated = transform_df(df_raw)

    # 3) Plot: Erzeuger & Ausgleich gestapelt (ax1), Aggregate als Linien (ax2)
    t = pd.to_datetime(df_erzeuger["timestamp"])

    # Primärachse
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Erzeuger-Stack
    prod_cols = [c for c in df_erzeuger.columns if c != "timestamp"]
    if prod_cols:
        prod_vals = [pd.to_numeric(df_erzeuger[c], errors="coerce").fillna(0.0).values for c in prod_cols]
        ax1.stackplot(t, *prod_vals, labels=prod_cols)

    # Ausgleich-Stack (als zusätzliche Gruppe)
    bal_cols = [c for c in df_ausgleich.columns if c != "timestamp"]
    if bal_cols:
        bal_vals = [pd.to_numeric(df_ausgleich[c], errors="coerce").fillna(0.0).values for c in bal_cols]
        ax1.stackplot(t, *bal_vals, labels=bal_cols)

    ax1.set_xlabel("Time")
    ax1.set_ylabel("Power [MW]")

    # Sekundärachse (Aggregate als Linien)
    ax2 = ax1.twinx()
    agg_cols = [c for c in df_aggregated.columns if c != "timestamp"]
    for c in agg_cols:
        ax2.plot(t, pd.to_numeric(df_aggregated[c], errors="coerce"), label=c, linewidth=1.6)

    ax2.set_ylabel("Aggregated indicators")

    # Gemeinsame Legende (ax1 + ax2)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    if h1 or h2:
        ax1.legend(h1 + h2, l1 + l2, loc="upper left", ncol=3, fontsize="small", frameon=False)

    # Titel
    start_date, end_date = last_full_week()
    ax1.set_title(
        f"Germany – Power mix (public power)\n"
        f"{start_date:%d.%m.%Y} bis {(end_date - pd.Timedelta(days=1)):%d.%m.%Y}"
    )

    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()

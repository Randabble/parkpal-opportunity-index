from __future__ import annotations
import pandas as pd
import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX

def build_synthetic_hourly(areas: list[str], days: int = 21, seed: int = 7) -> pd.DataFrame:
    """
    Create synthetic hourly demand with weekday commute peaks and weekend events.
    demand_index ~ baseline + commute_wave + event_spikes + noise
    """
    rng = np.random.default_rng(seed)
    hours = pd.date_range("2025-06-01", periods=24*days, freq="H")
    rows = []
    for a in areas:
        base = rng.uniform(10, 30)
        series = []
        for t in hours:
            hour = t.hour
            dow = t.dayofweek  # 0=Mon
            commute = 25*np.exp(-((hour-8)/2.5)**2) + 22*np.exp(-((hour-17)/2.5)**2) if dow < 5 else 6
            weekend_event = 18 if (dow in [5,6] and hour in [19,20]) else 0
            noise = rng.normal(0, 3)
            series.append(max(0, base + commute + weekend_event + noise))
        rows.append(pd.DataFrame({"timestamp": hours, "area_id": a, "demand_index": series}))
    return pd.concat(rows, ignore_index=True)

def sarima_forecast(df: pd.DataFrame, area_id: str, steps: int = 24*7) -> pd.DataFrame:
    """
    Fit a light SARIMAX per area on synthetic hourlies and forecast next week.
    """
    ts = df.loc[df["area_id"] == area_id].set_index("timestamp")["demand_index"].asfreq("H")
    # A tiny configuration that usually converges fast on synthetic data
    model = SARIMAX(ts, order=(1,0,1), seasonal_order=(1,1,1,24), enforce_stationarity=False, enforce_invertibility=False)
    res = model.fit(disp=False)
    fc = res.get_forecast(steps=steps)
    out = fc.summary_frame()[["mean", "mean_ci_lower", "mean_ci_upper"]].rename(
        columns={"mean": "forecast", "mean_ci_lower": "lo", "mean_ci_upper": "hi"}
    )
    out["area_id"] = area_id
    out.index.name = "timestamp"
    return out.reset_index()

def next_week_peak_index(forecasts: pd.DataFrame) -> pd.DataFrame:
    """
    Reduce hourly forecast to one value per area: next-week peak hour average across top 3 hours.
    """
    topk = (forecasts
            .sort_values(["area_id", "forecast"], ascending=[True, False])
            .groupby("area_id").head(3)
            .groupby("area_id")["forecast"].mean()
            .rename("forecast_peak_index"))
    return topk.reset_index()

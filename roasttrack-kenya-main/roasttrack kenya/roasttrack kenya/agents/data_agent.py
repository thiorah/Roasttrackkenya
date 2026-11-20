import numpy as np
import pandas as pd


class DataAgent:
    """Loads historical annual coffee export context and generates synthetic hourly roastery inputs."""

    def __init__(self, seed: int = 42):
        self.seed = seed

    def load_historical_data(self) -> tuple[pd.DataFrame, str]:
        # Synthetic annual Kenya specialty coffee historical context fallback
        years = np.arange(2015, 2026)
        rng = np.random.default_rng(self.seed)
        df = pd.DataFrame({
            "year": years,
            "country": "Kenya",
            "total_production_tonnes": np.round(40000 + np.linspace(0, 8500, len(years)) + rng.normal(0, 1200, len(years)), 1),
            "arabica_export_tonnes": np.round(36000 + np.linspace(0, 7800, len(years)) + rng.normal(0, 1000, len(years)), 1),
            "specialty_grade_aa_share_pct": np.round(28.0 + np.linspace(0, 6.5, len(years)) + rng.normal(0, 0.8, len(years)), 2),
        })
        return df, "synthetic_fallback"

    def generate_hourly_simulation(self, hours: int = 336, demand_scale: float = 1.0) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed)
        t = np.arange(hours)
        timestamps = pd.date_range("2026-10-01 00:00:00", periods=hours, freq="h")

        hour_of_day = timestamps.hour.to_numpy()
        day_of_year = timestamps.dayofyear.to_numpy()

        # Cyclic features
        hour_sin = np.sin(2 * np.pi * hour_of_day / 24.0)
        hour_cos = np.cos(2 * np.pi * hour_of_day / 24.0)
        day_sin = np.sin(2 * np.pi * day_of_year / 365.0)
        day_cos = np.cos(2 * np.pi * day_of_year / 365.0)

        # Synthetic environmental covariates
        temperature_c = 21.0 + 5.5 * np.sin(2 * np.pi * (hour_of_day - 8) / 24.0) + rng.normal(0, 0.7, hours)
        irradiance_wm2 = np.maximum(0.0, 850.0 * np.sin(np.pi * np.clip((hour_of_day - 6) / 12.0, 0, 1)))
        irradiance_wm2 = np.where((hour_of_day >= 6) & (hour_of_day <= 18), irradiance_wm2 + rng.normal(0, 20, hours), 0.0)
        irradiance_wm2 = np.maximum(0.0, irradiance_wm2)

        # Synthetic green-bean / roast demand (kg/h)
        daily_load = 3400.0 + 1150.0 * np.sin(2 * np.pi * (hour_of_day - 7) / 24.0)
        evening_peak = 650.0 * np.exp(-0.5 * ((hour_of_day - 19) / 2.2) ** 2)
        seasonal_term = 250.0 * day_sin
        noise = rng.normal(0, 110.0, hours)
        demand_kgh = np.maximum(800.0, (daily_load + evening_peak + seasonal_term + noise) * demand_scale)

        # Raw supply availability across 4 Kenyan specialty lots (kg/h)
        meru_peaberry_raw = 920.0 + 110.0 * np.sin(2 * np.pi * t / 72.0) + rng.normal(0, 25.0, hours)
        embu_sl34_raw = 1450.0 + 420.0 * np.cos(2 * np.pi * t / 168.0) + rng.normal(0, 60.0, hours)
        kirinyaga_sl28_raw = 1100.0 + 450.0 * np.sin(2 * np.pi * t / 48.0) + rng.normal(0, 75.0, hours)
        nyeri_aa_raw = 2100.0 * ((irradiance_wm2 / 850.0) ** 0.85) + rng.normal(0, 40.0, hours)

        return pd.DataFrame({
            "timestamp": timestamps,
            "hour_sin": hour_sin,
            "hour_cos": hour_cos,
            "day_sin": day_sin,
            "day_cos": day_cos,
            "temperature_c": np.round(temperature_c, 2),
            "irradiance_wm2": np.round(irradiance_wm2, 2),
            "demand_kgh": np.round(demand_kgh, 2),
            "meru_peaberry_raw": meru_peaberry_raw,
            "embu_sl34_raw": embu_sl34_raw,
            "kirinyaga_sl28_raw": kirinyaga_sl28_raw,
            "nyeri_aa_raw": nyeri_aa_raw,
        })

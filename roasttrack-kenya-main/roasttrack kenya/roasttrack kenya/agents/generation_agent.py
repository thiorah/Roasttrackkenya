import numpy as np
import pandas as pd


class GenerationAgent:
    """Clips lot supply to illustrative capacity bounds and totals available supply."""

    BOUNDS = {
        "meru_peaberry": (700.0, 1100.0),
        "embu_sl34": (0.0, 2200.0),
        "kirinyaga_sl28": (0.0, 1700.0),
        "nyeri_aa": (0.0, 2200.0),
    }

    def compute_availability(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        for name, (low, high) in self.BOUNDS.items():
            out[f"{name}_avail_kgh"] = np.round(np.clip(out[f"{name}_raw"], low, high), 2)

        out["total_available_kgh"] = np.round(
            out["meru_peaberry_avail_kgh"]
            + out["embu_sl34_avail_kgh"]
            + out["kirinyaga_sl28_avail_kgh"]
            + out["nyeri_aa_avail_kgh"],
            2,
        )
        out["supply_share_pct"] = np.round((out["total_available_kgh"] / out["demand_kgh"]) * 100.0, 2)
        return out

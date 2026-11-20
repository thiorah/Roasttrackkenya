import numpy as np
import pandas as pd
from scipy.optimize import linprog


class OptimizationAgent:
    """Solves hourly linear dispatch and updates conditioning/storage buffer state."""

    COSTS = {
        "meru_peaberry": 55.0,
        "embu_sl34": 42.0,
        "kirinyaga_sl28": 26.0,
        "nyeri_aa": 6.0,
        "buffer_release": 8.0,
        "buffer_intake": 0.0,
        "unmet_penalty": 2000.0,
    }

    NOMINAL_CAPACITY_KG = 1800.0
    RATE_LIMIT_KGH = 500.0
    MIN_STATE_KG = 180.0
    MAX_STATE_KG = 1620.0
    EFFICIENCY = 0.92

    def dispatch_schedule(self, df: pd.DataFrame, initial_buffer_kg: float = 900.0) -> pd.DataFrame:
        n = len(df)
        state_kg = float(np.clip(initial_buffer_kg, self.MIN_STATE_KG, self.MAX_STATE_KG))

        records = []
        # Decision variables: [P_peaberry, P_sl34, P_sl28, P_aa, P_intake, P_release, U_unmet]
        c = np.array([
            self.COSTS["meru_peaberry"],
            self.COSTS["embu_sl34"],
            self.COSTS["kirinyaga_sl28"],
            self.COSTS["nyeri_aa"],
            self.COSTS["buffer_intake"],
            self.COSTS["buffer_release"],
            self.COSTS["unmet_penalty"],
        ])

        # Equality constraint: P_peaberry + P_sl34 + P_sl28 + P_aa - P_intake + P_release + U_unmet = Demand
        A_eq = np.array([[1.0, 1.0, 1.0, 1.0, -1.0, 1.0, 1.0]])

        for i in range(n):
            row = df.iloc[i]
            demand = float(row["demand_kgh"])

            max_intake = min(self.RATE_LIMIT_KGH, (self.MAX_STATE_KG - state_kg) / self.EFFICIENCY)
            max_release = min(self.RATE_LIMIT_KGH, (state_kg - self.MIN_STATE_KG) * self.EFFICIENCY)
            max_intake = max(0.0, max_intake)
            max_release = max(0.0, max_release)

            bounds = [
                (0.0, float(row["meru_peaberry_avail_kgh"])),
                (0.0, float(row["embu_sl34_avail_kgh"])),
                (0.0, float(row["kirinyaga_sl28_avail_kgh"])),
                (0.0, float(row["nyeri_aa_avail_kgh"])),
                (0.0, max_intake),
                (0.0, max_release),
                (0.0, None),
            ]

            res = linprog(c, A_eq=A_eq, b_eq=np.array([demand]), bounds=bounds, method="highs")
            p_pea, p_sl34, p_sl28, p_aa, p_in, p_out, unmet = res.x

            state_kg = state_kg + self.EFFICIENCY * p_in - (p_out / self.EFFICIENCY)
            state_kg = float(np.clip(state_kg, self.MIN_STATE_KG, self.MAX_STATE_KG))

            records.append({
                "meru_peaberry_disp_kgh": round(float(p_pea), 2),
                "embu_sl34_disp_kgh": round(float(p_sl34), 2),
                "kirinyaga_sl28_disp_kgh": round(float(p_sl28), 2),
                "nyeri_aa_disp_kgh": round(float(p_aa), 2),
                "buffer_intake_kgh": round(float(p_in), 2),
                "buffer_release_kgh": round(float(p_out), 2),
                "unmet_kgh": round(float(unmet), 2),
                "buffer_kg": round(state_kg, 2),
                "dispatch_cost": round(float(res.fun), 2),
            })

        return pd.concat([df.reset_index(drop=True), pd.DataFrame(records)], axis=1)

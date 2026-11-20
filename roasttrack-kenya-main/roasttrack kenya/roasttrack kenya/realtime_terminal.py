import time
from pathlib import Path
import pandas as pd

CSV_SNAPSHOT = Path("output/live_simulation.csv")
LOG_FILE = Path("logs/scenario-terminal.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def classify_state(row: pd.Series) -> tuple[str, str]:
    if row["unmet_kgh"] > 0.01:
        return "SUPPLY GAP", f"Unfulfilled order demand of {row['unmet_kgh']:.1f} kg/h."
    if row["buffer_kg"] <= 230.0:
        return "LOW BATTERY RESERVE", f"Conditioning buffer reserve low at {row['buffer_kg']:.1f} kg."
    if row["buffer_intake_kgh"] > 10.0:
        return "RENEWABLE SURPLUS / CHARGING", f"Surplus lot capacity storing +{row['buffer_intake_kgh']:.1f} kg/h."
    if row["buffer_release_kgh"] > 10.0:
        return "PEAK SUPPORT / DISCHARGING", f"Releasing {row['buffer_release_kgh']:.1f} kg/h from buffer."
    if row["demand_kgh"] >= 4500.0:
        return "HIGH-DEMAND PERIOD", f"Elevated roast demand at {row['demand_kgh']:.1f} kg/h."
    return "NORMAL BALANCE", "Supply lots and demand balanced within normal operating bounds."


def main() -> None:
    idx = 0
    while True:
        if CSV_SNAPSHOT.exists():
            try:
                df = pd.read_csv(CSV_SNAPSHOT)
                if len(df) > 0:
                    row = df.iloc[idx % len(df)]
                    state, reason = classify_state(row)
                    line = (
                        f"[{row['timestamp']}] Demand={row['demand_kgh']:.1f} kg/h | "
                        f"RF={row['random_forest_forecast_kgh']:.1f} kg/h | "
                        f"Buffer={row['buffer_kg']:.1f} kg | {state} -> {reason}"
                    )
                    print(line, flush=True)
                    with LOG_FILE.open("a", encoding="utf-8") as f:
                        f.write(line + "\n")
                    idx += 1
            except Exception:
                pass
        time.sleep(0.25)


if __name__ == "__main__":
    main()

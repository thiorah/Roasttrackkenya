import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd


class ReportingAgent:
    """Computes summary metrics, exports Excel, and persists simulation runs to SQLite."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def summarize(self, df: pd.DataFrame, metrics: dict) -> dict:
        return {
            "total_hours": int(len(df)),
            "total_demand_kg": round(float(df["demand_kgh"].sum()), 2),
            "total_available_supply_kg": round(float(df["total_available_kgh"].sum()), 2),
            "total_unmet_kg": round(float(df["unmet_kgh"].sum()), 2),
            "supply_gap_hours": int((df["unmet_kgh"] > 0.01).sum()),
            "total_dispatch_cost": round(float(df["dispatch_cost"].sum()), 2),
            "rf_mae_kgh": metrics["random_forest"]["mae_kgh"],
            "rf_rmse_kgh": metrics["random_forest"]["rmse_kgh"],
            "lr_mae_kgh": metrics["linear_regression"]["mae_kgh"],
            "lr_rmse_kgh": metrics["linear_regression"]["rmse_kgh"],
        }

    def export_excel(
        self,
        sim_df: pd.DataFrame,
        summary: dict,
        metrics: dict,
        hist_df: pd.DataFrame,
        filename: str = "roast_track_results.xlsx",
    ) -> Path:
        path = self.output_dir / filename
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            sim_df.to_excel(writer, sheet_name="Simulation_Rows", index=False)
            pd.DataFrame([summary]).to_excel(writer, sheet_name="Summary", index=False)
            pd.DataFrame(metrics["feature_importances"], index=["importance"]).T.reset_index().rename(
                columns={"index": "feature"}
            ).to_excel(writer, sheet_name="Model_Metrics", index=False)
            hist_df.to_excel(writer, sheet_name="Historical_Context", index=False)
        return path

    def save_sqlite(
        self,
        sim_df: pd.DataFrame,
        summary: dict,
        metrics: dict,
        data_source: str,
        filename: str = "roast_track_simulation.sqlite",
    ) -> int:
        db_path = self.output_dir / filename
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulation_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                data_source TEXT NOT NULL,
                summary_json TEXT NOT NULL,
                metrics_json TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulation_readings (
                reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                demand_kgh REAL,
                linear_forecast_kgh REAL,
                random_forest_forecast_kgh REAL,
                total_available_kgh REAL,
                buffer_intake_kgh REAL,
                buffer_release_kgh REAL,
                buffer_kg REAL,
                unmet_kgh REAL,
                FOREIGN KEY (run_id) REFERENCES simulation_runs(run_id)
            )
        """)

        created_at = datetime.now(timezone.utc).isoformat()
        cur.execute(
            "INSERT INTO simulation_runs (created_at, data_source, summary_json, metrics_json) VALUES (?, ?, ?, ?)",
            (created_at, data_source, json.dumps(summary), json.dumps(metrics)),
        )
        run_id = int(cur.lastrowid)

        rows = [
            (
                run_id,
                str(r["timestamp"]),
                float(r["demand_kgh"]),
                float(r["linear_forecast_kgh"]),
                float(r["random_forest_forecast_kgh"]),
                float(r["total_available_kgh"]),
                float(r["buffer_intake_kgh"]),
                float(r["buffer_release_kgh"]),
                float(r["buffer_kg"]),
                float(r["unmet_kgh"]),
            )
            for _, r in sim_df.iterrows()
        ]
        cur.executemany(
            """INSERT INTO simulation_readings (
                run_id, timestamp, demand_kgh, linear_forecast_kgh, random_forest_forecast_kgh,
                total_available_kgh, buffer_intake_kgh, buffer_release_kgh, buffer_kg, unmet_kgh
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
        conn.close()
        return run_id

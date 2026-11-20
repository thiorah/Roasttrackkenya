import json
import os
import time
from pathlib import Path
from agents import DataAgent, ForecastAgent, GenerationAgent, OptimizationAgent, ReportingAgent

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CSV_SNAPSHOT = OUTPUT_DIR / "live_simulation.csv"
JSON_SNAPSHOT = OUTPUT_DIR / "live_summary.json"
CONTROL_FILE = OUTPUT_DIR / "control_params.json"


def run_cycle(demand_scale: float = 1.0) -> None:
    data_agent = DataAgent(seed=42)
    forecast_agent = ForecastAgent(random_state=42)
    generation_agent = GenerationAgent()
    optimization_agent = OptimizationAgent()
    reporting_agent = ReportingAgent(output_dir="output")

    hist_df, source_label = data_agent.load_historical_data()
    raw_df = data_agent.generate_hourly_simulation(hours=336, demand_scale=demand_scale)
    pred_df, metrics = forecast_agent.fit_and_predict(raw_df)
    avail_df = generation_agent.compute_availability(pred_df)
    disp_df = optimization_agent.dispatch_schedule(avail_df, initial_buffer_kg=900.0)
    summary = reporting_agent.summarize(disp_df, metrics)

    # Atomic CSV and JSON refresh
    tmp_csv = OUTPUT_DIR / ".live_simulation.tmp.csv"
    disp_df.to_csv(tmp_csv, index=False)
    os.replace(tmp_csv, CSV_SNAPSHOT)

    tmp_json = OUTPUT_DIR / ".live_summary.tmp.json"
    payload = {
        "data_source": source_label,
        "demand_scale": demand_scale,
        "summary": summary,
        "metrics": metrics,
    }
    tmp_json.write_text(json.dumps(payload, indent=2))
    os.replace(tmp_json, JSON_SNAPSHOT)


def main() -> None:
    last_scale = None
    while True:
        scale = 1.0
        if CONTROL_FILE.exists():
            try:
                scale = float(json.loads(CONTROL_FILE.read_text()).get("demand_scale", 1.0))
            except Exception:
                scale = 1.0

        if scale != last_scale or not CSV_SNAPSHOT.exists():
            run_cycle(demand_scale=scale)
            last_scale = scale

        time.sleep(0.5)


if __name__ == "__main__":
    main()

import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from agents import DataAgent, ReportingAgent

OUTPUT_DIR = Path("output")
CSV_SNAPSHOT = OUTPUT_DIR / "live_simulation.csv"
JSON_SNAPSHOT = OUTPUT_DIR / "live_summary.json"
CONTROL_FILE = OUTPUT_DIR / "control_params.json"
LOG_FILE = Path("logs/scenario-terminal.log")


class RoastTrackApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RoastTrack Kenya Coffee Supply & Roastery Telemetry")
        self.geometry("1180x760")

        self.frame_idx = 0
        self.df = pd.DataFrame()
        self.summary_data = {}

        self._build_ui()
        self._poll_snapshots()
        self._animate_step()

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)

        self.cards = {}
        for label in ["Current Demand (kg/h)", "RF Forecast (kg/h)", "Supply Share (%)", "Buffer State (kg)"]:
            card = ttk.LabelFrame(top, text=label, padding=8)
            card.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
            val = ttk.Label(card, text="--", font=("Helvetica", 14, "bold"))
            val.pack()
            self.cards[label] = val

        ctrl = ttk.Frame(self, padding=10)
        ctrl.pack(fill=tk.X)
        ttk.Label(ctrl, text="Demand Scenario Multiplier:").pack(side=tk.LEFT)
        self.scale_var = tk.DoubleVar(value=1.0)
        slider = ttk.Scale(ctrl, from_=0.7, to=1.5, variable=self.scale_var, command=self._on_scale_change)
        slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        ttk.Button(ctrl, text="Export Excel", command=self._export_excel).pack(side=tk.RIGHT, padx=4)
        ttk.Button(ctrl, text="Save to SQLite", command=self._save_sqlite).pack(side=tk.RIGHT, padx=4)

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        # Tab 1: Charts
        chart_tab = ttk.Frame(notebook)
        notebook.add(chart_tab, text="Live Telemetry Charts")
        self.fig = Figure(figsize=(10, 5.5), dpi=100)
        self.ax_demand = self.fig.add_subplot(221)
        self.ax_supply = self.fig.add_subplot(222)
        self.ax_buffer = self.fig.add_subplot(223)
        self.ax_resid = self.fig.add_subplot(224)
        self.fig.tight_layout(pad=2.5)

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_tab)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Tab 2: Live Scenario Terminal
        term_tab = ttk.Frame(notebook)
        notebook.add(term_tab, text="Live Scenario Terminal")
        self.term_text = tk.Text(term_tab, bg="#111111", fg="#e6e6e6", font=("Courier", 10))
        self.term_text.pack(fill=tk.BOTH, expand=True)

    def _on_scale_change(self, _val):
        CONTROL_FILE.write_text(json.dumps({"demand_scale": round(self.scale_var.get(), 2)}))

    def _poll_snapshots(self):
        if CSV_SNAPSHOT.exists():
            try:
                self.df = pd.read_csv(CSV_SNAPSHOT)
            except Exception:
                pass
        if JSON_SNAPSHOT.exists():
            try:
                self.summary_data = json.loads(JSON_SNAPSHOT.read_text())
            except Exception:
                pass
        if LOG_FILE.exists():
            try:
                lines = LOG_FILE.read_text(encoding="utf-8").splitlines()[-25:]
                self.term_text.delete("1.0", tk.END)
                self.term_text.insert(tk.END, "\n".join(lines))
            except Exception:
                pass
        self.after(250, self._poll_snapshots)

    def _animate_step(self):
        if len(self.df) > 0:
            idx = self.frame_idx % len(self.df)
            row = self.df.iloc[idx]
            self.cards["Current Demand (kg/h)"].config(text=f"{row['demand_kgh']:.1f}")
            self.cards["RF Forecast (kg/h)"].config(text=f"{row['random_forest_forecast_kgh']:.1f}")
            self.cards["Supply Share (%)"].config(text=f"{row['supply_share_pct']:.1f}%")
            self.cards["Buffer State (kg)"].config(text=f"{row['buffer_kg']:.1f}")

            window = self.df.iloc[max(0, idx - 48): idx + 1]
            self._redraw_charts(window)
            self.frame_idx += 1
        self.after(90, self._animate_step)

    def _redraw_charts(self, w: pd.DataFrame):
        for ax in (self.ax_demand, self.ax_supply, self.ax_buffer, self.ax_resid):
            ax.clear()

        x = range(len(w))
        self.ax_demand.plot(x, w["demand_kgh"], label="Actual")
        self.ax_demand.plot(x, w["linear_forecast_kgh"], "--", label="Linear")
        self.ax_demand.plot(x, w["random_forest_forecast_kgh"], ":", label="RF")
        self.ax_demand.set_title("Demand & Forecasts (kg/h)")
        self.ax_demand.legend(fontsize=7)

        self.ax_supply.plot(x, w["nyeri_aa_avail_kgh"], label="Nyeri AA")
        self.ax_supply.plot(x, w["embu_sl34_avail_kgh"], label="Embu SL34")
        self.ax_supply.plot(x, w["kirinyaga_sl28_avail_kgh"], label="Kirinyaga SL28")
        self.ax_supply.plot(x, w["meru_peaberry_avail_kgh"], label="Meru Peaberry")
        self.ax_supply.set_title("Lot Supply Availability (kg/h)")
        self.ax_supply.legend(fontsize=7)

        self.ax_buffer.plot(x, w["buffer_kg"], color="tab:green")
        self.ax_buffer.axhline(1620, linestyle="--", color="gray")
        self.ax_buffer.axhline(180, linestyle="--", color="gray")
        self.ax_buffer.set_title("Conditioning Buffer State (kg)")

        self.ax_resid.plot(x, w["rf_residual_kgh"], color="tab:red")
        self.ax_resid.axhline(0, linestyle="--", color="black")
        self.ax_resid.set_title("RF Forecast Residual (kg/h)")

        self.fig.tight_layout(pad=2.0)
        self.canvas.draw_idle()

    def _export_excel(self):
        if len(self.df) == 0:
            return
        hist_df, _ = DataAgent().load_historical_data()
        rep = ReportingAgent("output")
        path = rep.export_excel(
            self.df,
            self.summary_data.get("summary", {}),
            self.summary_data.get("metrics", {"feature_importances": {}}),
            hist_df,
        )
        messagebox.showinfo("Excel Exported", f"Saved to {path}")

    def _save_sqlite(self):
        if len(self.df) == 0:
            return
        rep = ReportingAgent("output")
        run_id = rep.save_sqlite(
            self.df,
            self.summary_data.get("summary", {}),
            self.summary_data.get("metrics", {}),
            self.summary_data.get("data_source", "synthetic_fallback"),
        )
        messagebox.showinfo("SQLite Saved", f"Persisted simulation run_id={run_id}")


if __name__ == "__main__":
    app = RoastTrackApp()
    app.mainloop()

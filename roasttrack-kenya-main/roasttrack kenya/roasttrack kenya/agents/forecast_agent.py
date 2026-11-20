import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error


class ForecastAgent:
    """Trains and evaluates Multiple Linear Regression and Random Forest demand predictors."""

    FEATURES = [
        "hour_sin",
        "hour_cos",
        "day_sin",
        "day_cos",
        "temperature_c",
        "irradiance_wm2",
    ]

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.lr_model = LinearRegression()
        self.rf_model = RandomForestRegressor(n_estimators=120, random_state=random_state)

    def fit_and_predict(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        X = df[self.FEATURES].to_numpy()
        y = df["demand_kgh"].to_numpy()

        split_idx = int(len(df) * 0.80)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        self.lr_model.fit(X_train, y_train)
        self.rf_model.fit(X_train, y_train)

        lr_test_pred = self.lr_model.predict(X_test)
        rf_test_pred = self.rf_model.predict(X_test)

        metrics = {
            "split_index": split_idx,
            "linear_regression": {
                "mae_kgh": round(float(mean_absolute_error(y_test, lr_test_pred)), 3),
                "rmse_kgh": round(float(root_mean_squared_error(y_test, lr_test_pred)), 3),
            },
            "random_forest": {
                "mae_kgh": round(float(mean_absolute_error(y_test, rf_test_pred)), 3),
                "rmse_kgh": round(float(root_mean_squared_error(y_test, rf_test_pred)), 3),
            },
            "feature_importances": {
                feat: round(float(imp), 4)
                for feat, imp in zip(self.FEATURES, self.rf_model.feature_importances_)
            },
        }

        out = df.copy()
        out["linear_forecast_kgh"] = np.round(self.lr_model.predict(X), 2)
        out["random_forest_forecast_kgh"] = np.round(self.rf_model.predict(X), 2)
        out["rf_residual_kgh"] = np.round(out["demand_kgh"] - out["random_forest_forecast_kgh"], 2)
        return out, metrics

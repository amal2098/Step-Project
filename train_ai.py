from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


def resolve_data_path() -> Path:
    candidates = [Path("refined_yemeni_dataset.csv"), Path("dataset.csv"), Path("data.csv"), Path("data.CSV")]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("refined_yemeni_dataset.csv/dataset.csv/data.csv/data.CSV not found")


def col(df: pd.DataFrame, *names: str) -> str:
    lowered = {c.strip().lower(): c for c in df.columns}
    for name in names:
        key = name.strip().lower()
        if key in lowered:
            return lowered[key]
    raise KeyError(f"Missing required column. Tried: {names}")


def fit_linear_raw_to_scaled(raw: pd.Series, scaled: pd.Series) -> tuple[float, float]:
    x = pd.to_numeric(raw, errors="coerce")
    y = pd.to_numeric(scaled, errors="coerce")
    mask = x.notna() & y.notna()
    if mask.sum() < 2:
        return 1.0, 0.0
    slope, intercept = np.polyfit(x[mask].to_numpy(), y[mask].to_numpy(), 1)
    return float(slope), float(intercept)


data_path = resolve_data_path()
print('Using dataset:', data_path.resolve())
df = pd.read_csv(data_path, encoding='utf-8-sig')
df.columns = [c.strip() for c in df.columns]

sector_col = col(df, "القطاع")
location_col = col(df, "الموقع")
capital_col = col(df, "رأس المال")
sales_col = col(df, "تكلفة المبيعات")
revenue_col = col(df, "الإيرادات")
workers_col = col(df, "عدد العمال")

capital_scaled_col = col(df, "رأس المال_Scaled")
sales_scaled_col = col(df, "تكلفة المبيعات_Scaled")
revenue_scaled_col = col(df, "الإيرادات_Scaled")
workers_scaled_col = col(df, "عدد العمال_Scaled")

project_type_encoded_col = col(df, "نوع المشروع الدقيق_Encoded")
target_col = col(df, "Target_الجدوى")

# Categorical encoding (Arabic-friendly)
le_sector = LabelEncoder()
le_location = LabelEncoder()
sector_encoded = le_sector.fit_transform(df[sector_col].astype(str))
location_encoded = le_location.fit_transform(df[location_col].astype(str))

# Numeric scaled features from dataset
capital_scaled = pd.to_numeric(df[capital_scaled_col], errors="coerce")
sales_scaled = pd.to_numeric(df[sales_scaled_col], errors="coerce")
revenue_scaled = pd.to_numeric(df[revenue_scaled_col], errors="coerce")
workers_scaled = pd.to_numeric(df[workers_scaled_col], errors="coerce")
project_type_encoded = pd.to_numeric(df[project_type_encoded_col], errors="coerce")
target = pd.to_numeric(df[target_col], errors="coerce")

X = pd.DataFrame(
    {
        "sector_encoded": sector_encoded,
        "capital_scaled": capital_scaled,
        "sales_cost_scaled": sales_scaled,
        "revenue_scaled": revenue_scaled,
        "workers_scaled": workers_scaled,
        "location_encoded": location_encoded,
        "project_type_encoded": project_type_encoded,
    }
)

# Fill missing features with median
for c in X.columns:
    X[c] = X[c].fillna(X[c].median())

y = target.fillna(target.mode().iloc[0] if not target.dropna().empty else 0).round().astype(int)

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y if y.nunique() > 1 else None,
)

model = RandomForestClassifier(n_estimators=220, random_state=42, class_weight="balanced")
model.fit(X_train, y_train)

accuracy = model.score(X_test, y_test)
print(f"Model accuracy: {accuracy:.2%}")
print("Feature importance:")
for feature, importance in zip(X.columns, model.feature_importances_):
    print(f"- {feature}: {importance:.2%}")

# Save transformation metadata for API prediction
capital_slope, capital_intercept = fit_linear_raw_to_scaled(df[capital_col], df[capital_scaled_col])
sales_slope, sales_intercept = fit_linear_raw_to_scaled(df[sales_col], df[sales_scaled_col])
revenue_slope, revenue_intercept = fit_linear_raw_to_scaled(df[revenue_col], df[revenue_scaled_col])
workers_slope, workers_intercept = fit_linear_raw_to_scaled(df[workers_col], df[workers_scaled_col])

sector_type = (
    pd.DataFrame(
        {
            "sector": df[sector_col].astype(str),
            "project_type_encoded": pd.to_numeric(df[project_type_encoded_col], errors="coerce"),
        }
    )
    .dropna()
    .groupby("sector")["project_type_encoded"]
    .agg(lambda s: float(s.mode().iloc[0]) if not s.mode().empty else float(s.median()))
    .to_dict()
)

meta = {
    "feature_order": [
        "sector_encoded",
        "capital_scaled",
        "sales_cost_scaled",
        "revenue_scaled",
        "workers_scaled",
        "location_encoded",
        "project_type_encoded",
    ],
    "raw_to_scaled": {
        "capital": {"slope": capital_slope, "intercept": capital_intercept},
        "sales_cost": {"slope": sales_slope, "intercept": sales_intercept},
        "revenue": {"slope": revenue_slope, "intercept": revenue_intercept},
        "workers": {"slope": workers_slope, "intercept": workers_intercept},
    },
    "sector_to_project_type": sector_type,
    "default_project_type_encoded": float(project_type_encoded.median())
    if not project_type_encoded.dropna().empty
    else 0.0,
    "dataset_path": str(data_path),
    "target_column": target_col,
    "columns_used": {
        "sector": sector_col,
        "location": location_col,
        "capital_raw": capital_col,
        "sales_raw": sales_col,
        "revenue_raw": revenue_col,
        "workers_raw": workers_col,
        "capital_scaled": capital_scaled_col,
        "sales_scaled": sales_scaled_col,
        "revenue_scaled": revenue_scaled_col,
        "workers_scaled": workers_scaled_col,
        "project_type_encoded": project_type_encoded_col,
        "target": target_col,
    },
}

joblib.dump(model, "feasibility_model.joblib")
joblib.dump(le_sector, "le_sector.joblib")
joblib.dump(le_location, "le_location.joblib")
joblib.dump(meta, "model_meta.joblib")

print("Training completed successfully")




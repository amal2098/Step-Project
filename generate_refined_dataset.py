from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
SOURCE_DATASET = BASE_DIR / "dataset.csv"
OUTPUT_DATASET = BASE_DIR / "refined_yemeni_dataset.csv"

SEED = 42
ROWS = 1000


SECTOR_PROFILES = {
    "تقنية": {
        "capital_min": 1_200_000,
        "capital_max": 7_500_000,
        "workers": (2, 8),
        "unit_price": (15_000, 75_000),
        "capacity": (120, 600),
        "competition": (6, 18),
        "demand": ["متوسط", "مرتفع"],
        "clients": ["طلاب", "موظفون", "شركات صغيرة"],
        "markets": ["محلي", "طلاب الجامعات", "الأحياء التجارية"],
        "channels": ["اونلاين", "مباشر", "تطبيقات المراسلة"],
        "marketing": ["سوشيال ميديا", "عروض افتتاح", "إحالات"],
        "equipment": ["حاسوب", "سيرفر بسيط", "أجهزة شبكات"],
        "project_templates": ["خدمة تقنية", "متجر إلكتروني", "مركز تدريب رقمي"],
    },
    "تجارة": {
        "capital_min": 900_000,
        "capital_max": 6_500_000,
        "workers": (2, 10),
        "unit_price": (2_000, 35_000),
        "capacity": (300, 2500),
        "competition": (8, 25),
        "demand": ["متوسط", "مرتفع"],
        "clients": ["عائلات", "طلاب", "موظفون"],
        "markets": ["محلي", "أحياء سكنية", "قرب الجامعات"],
        "channels": ["محل", "توصيل", "اونلاين"],
        "marketing": ["لافتات", "سوشيال ميديا", "عروض أسبوعية"],
        "equipment": ["رفوف", "ثلاجات", "نقاط بيع"],
        "project_templates": ["بوفيه", "بقالة تخصصية", "متجر مستلزمات"],
    },
    "تعليم": {
        "capital_min": 700_000,
        "capital_max": 4_500_000,
        "workers": (2, 12),
        "unit_price": (8_000, 40_000),
        "capacity": (80, 500),
        "competition": (5, 16),
        "demand": ["متوسط", "مرتفع"],
        "clients": ["طلاب", "أولياء أمور", "خريجون"],
        "markets": ["طلاب الجامعات", "طلاب المدارس", "محلي"],
        "channels": ["مباشر", "اونلاين", "هجين"],
        "marketing": ["محتوى تعليمي", "إعلانات محلية", "شراكات مدارس"],
        "equipment": ["سبورة ذكية", "أجهزة عرض", "حاسوب"],
        "project_templates": ["مركز تدريبي", "دورات لغات", "منصة تعليم"],
    },
    "صحة": {
        "capital_min": 1_500_000,
        "capital_max": 9_000_000,
        "workers": (3, 15),
        "unit_price": (10_000, 90_000),
        "capacity": (60, 420),
        "competition": (4, 14),
        "demand": ["متوسط", "مرتفع"],
        "clients": ["عائلات", "موظفون", "طلاب"],
        "markets": ["محلي", "أحياء مكتظة", "قرب المستشفيات"],
        "channels": ["مباشر", "حجز هاتفي", "اونلاين"],
        "marketing": ["توعية صحية", "سمعة وجودة", "تعاون أطباء"],
        "equipment": ["أجهزة طبية", "معدات تعقيم", "حاسوب"],
        "project_templates": ["عيادة مصغرة", "مختبر تحاليل", "صيدلية متخصصة"],
    },
    "خدمات": {
        "capital_min": 600_000,
        "capital_max": 5_500_000,
        "workers": (1, 9),
        "unit_price": (5_000, 50_000),
        "capacity": (90, 900),
        "competition": (5, 20),
        "demand": ["متوسط", "مرتفع"],
        "clients": ["طلاب", "عائلات", "شركات صغيرة"],
        "markets": ["محلي", "قرب الجامعات", "الأحياء النشطة"],
        "channels": ["مباشر", "اونلاين", "واتساب"],
        "marketing": ["عروض باقات", "سوشيال ميديا", "توصيات العملاء"],
        "equipment": ["معدات خدمية", "حاسوب", "معدات متنقلة"],
        "project_templates": ["خدمة صيانة", "خدمة طباعة", "خدمة لوجستية"],
    },
}


def round_1000(value: float) -> int:
    return int(round(value / 1000.0) * 1000)


def min_max_scale(series: pd.Series) -> pd.Series:
    min_val = float(series.min())
    max_val = float(series.max())
    if math.isclose(min_val, max_val):
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - min_val) / (max_val - min_val)


def weighted_choice(options: list[str]) -> str:
    if len(options) == 1:
        return options[0]
    return random.choices(options, weights=[0.35, 0.65], k=1)[0]


def build_rows(n_rows: int) -> list[dict]:
    rows: list[dict] = []
    sectors = list(SECTOR_PROFILES.keys())

    for i in range(1, n_rows + 1):
        sector = random.choice(sectors)
        profile = SECTOR_PROFILES[sector]

        capital = round_1000(random.uniform(profile["capital_min"], profile["capital_max"]))

        revenue_ratio = random.uniform(0.12, 0.18)
        revenue = round_1000(capital * revenue_ratio)

        sales_ratio = random.uniform(0.40, 0.58)
        operating_ratio = random.uniform(0.02, 0.06)

        sales_cost = round_1000(revenue * sales_ratio)
        operating_cost = round_1000(capital * operating_ratio)

        monthly_profit = revenue - sales_cost - operating_cost
        if monthly_profit < 20_000:
            adjustment = 20_000 - monthly_profit
            sales_cost = max(1_000, round_1000(sales_cost - (adjustment * 0.65)))
            operating_cost = max(1_000, round_1000(operating_cost - (adjustment * 0.35)))
            monthly_profit = revenue - sales_cost - operating_cost

        if monthly_profit <= 0:
            monthly_profit = max(10_000, round_1000(revenue * 0.08))
            total_cost = revenue - monthly_profit
            sales_cost = round_1000(total_cost * 0.72)
            operating_cost = round_1000(total_cost * 0.28)

        margin = max(0.0, min(1.0, monthly_profit / revenue if revenue > 0 else 0.0))
        payback = max(1, int(round(capital / monthly_profit)))

        workers = random.randint(*profile["workers"])
        unit_price = round_1000(random.uniform(*profile["unit_price"]))
        capacity = int(round(random.uniform(*profile["capacity"])))
        competitors = int(round(random.uniform(*profile["competition"])))

        demand = weighted_choice(profile["demand"])
        client_type = random.choice(profile["clients"])
        market = random.choice(profile["markets"])
        channel = random.choice(profile["channels"])
        marketing = random.choice(profile["marketing"])
        equipment = random.choice(profile["equipment"])

        project_name = f"{random.choice(profile['project_templates'])} {i}"

        feasibility_target = 1 if (margin >= 0.10 and payback <= 24) else 0

        row = {
            "اسم المشروع": project_name,
            "القطاع": sector,
            "رأس المال": int(capital),
            "تكلفة المبيعات": int(sales_cost),
            "الإيرادات": int(revenue),
            "التكلفة التشغيلية الشهرية": int(operating_cost),
            "سعر المنتج او الخدمة": int(unit_price),
            "الطاقة الإنتاجية الشهرية": int(capacity),
            "هامش الربح": round(margin, 4),
            "نوع العميل": client_type,
            "السوق المستهدف": market,
            "قنوات التوزيع": channel,
            "حجم الطلب": demand,
            "عدد المنافسين": int(competitors),
            "طرق التسويق": marketing,
            "عدد العمال": int(workers),
            "نوع المعدات": equipment,
            "الموقع": "صنعاء",
            "فترة الاسترداد": int(payback),
            "النتيجة_رقم": int(feasibility_target),
        }
        rows.append(row)

    return rows


def enrich_engineered_columns(df: pd.DataFrame) -> pd.DataFrame:
    df["رأس المال_Scaled"] = min_max_scale(pd.to_numeric(df["رأس المال"], errors="coerce").fillna(0)).round(6)
    df["الإيرادات_Scaled"] = min_max_scale(pd.to_numeric(df["الإيرادات"], errors="coerce").fillna(0)).round(6)
    df["تكلفة المبيعات_Scaled"] = min_max_scale(pd.to_numeric(df["تكلفة المبيعات"], errors="coerce").fillna(0)).round(6)

    # Encoded project subtype derived from sector + template family
    df["نوع المشروع الدقيق_Encoded"] = pd.factorize(df["اسم المشروع"].str.split().str[0] + "_" + df["القطاع"])[0]

    log_capital = np.log1p(pd.to_numeric(df["رأس المال"], errors="coerce").fillna(0))
    df["Log_رأس_المال"] = log_capital.round(6)
    df["Log_رأس_المال_Scaled"] = min_max_scale(log_capital).round(6)

    df["عدد العمال_Scaled"] = min_max_scale(pd.to_numeric(df["عدد العمال"], errors="coerce").fillna(0)).round(6)

    demand_map = {"منخفض": 1, "متوسط": 2, "مرتفع": 3}
    demand_num = df["حجم الطلب"].map(demand_map).fillna(2)
    df["حجم الطلب_Scaled"] = min_max_scale(demand_num).round(6)

    df["عدد المنافسين_Scaled"] = min_max_scale(pd.to_numeric(df["عدد المنافسين"], errors="coerce").fillna(0)).round(6)

    df["Target_الجدوى"] = df["النتيجة_رقم"].astype(int)
    df["Target_فترة_الاسترداد"] = pd.to_numeric(df["فترة الاسترداد"], errors="coerce").fillna(0).round().astype(int)

    return df


def force_column_order(df: pd.DataFrame, reference_cols: list[str]) -> pd.DataFrame:
    for col in reference_cols:
        if col not in df.columns:
            df[col] = ""
    return df[reference_cols]


def main() -> None:
    random.seed(SEED)
    np.random.seed(SEED)

    if SOURCE_DATASET.exists():
        ref_df = pd.read_csv(SOURCE_DATASET, encoding="utf-8-sig")
        reference_cols = list(ref_df.columns)
    else:
        reference_cols = [
            "اسم المشروع",
            "القطاع",
            "رأس المال",
            "تكلفة المبيعات",
            "الإيرادات",
            "التكلفة التشغيلية الشهرية",
            "سعر المنتج او الخدمة",
            "الطاقة الإنتاجية الشهرية",
            "هامش الربح",
            "نوع العميل",
            "السوق المستهدف",
            "قنوات التوزيع",
            "حجم الطلب",
            "عدد المنافسين",
            "طرق التسويق",
            "عدد العمال",
            "نوع المعدات",
            "الموقع",
            "فترة الاسترداد",
            "النتيجة_رقم",
            "رأس المال_Scaled",
            "الإيرادات_Scaled",
            "تكلفة المبيعات_Scaled",
            "نوع المشروع الدقيق_Encoded",
            "Log_رأس_المال",
            "Log_رأس_المال_Scaled",
            "عدد العمال_Scaled",
            "حجم الطلب_Scaled",
            "عدد المنافسين_Scaled",
            "Target_الجدوى",
            "Target_فترة_الاسترداد",
        ]

    rows = build_rows(ROWS)
    out_df = pd.DataFrame(rows)
    out_df = enrich_engineered_columns(out_df)
    out_df = force_column_order(out_df, reference_cols)

    # Enforce financial columns as integers rounded to nearest 1000 (no decimals)
    for col in ["رأس المال", "تكلفة المبيعات", "الإيرادات", "التكلفة التشغيلية الشهرية", "سعر المنتج او الخدمة"]:
        if col in out_df.columns:
            out_df[col] = pd.to_numeric(out_df[col], errors="coerce").fillna(0).round(0).astype(int)

    if "فترة الاسترداد" in out_df.columns:
        out_df["فترة الاسترداد"] = pd.to_numeric(out_df["فترة الاسترداد"], errors="coerce").fillna(0).round().astype(int)

    out_df.to_csv(OUTPUT_DATASET, index=False, encoding="utf-8-sig")

    print(f"Generated {len(out_df)} rows")
    print(f"Saved: {OUTPUT_DATASET}")


if __name__ == "__main__":
    main()

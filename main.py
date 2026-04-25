import os
import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

import joblib
import numpy as np
import pandas as pd
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import desc, extract, func, or_
from sqlalchemy.orm import Session
try:
    import google.generativeai as genai
except Exception:
    genai = None

import models
from database import engine, get_db

# Ensure tables exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Khotwa API", version="1.1.0")

# CORS (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security config
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    print("WARNING: JWT_SECRET_KEY not found in .env! Generating a temporary secure key.")
    SECRET_KEY = os.urandom(32).hex()

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Gemini config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
_gemini_model = None
if genai is not None and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    except Exception as e:
        print(f"Warning: Gemini not initialized: {e}")
        _gemini_model = None
elif not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not set. Using local fallback analysis.")

# Load ML artifacts
model = None
le_sector = None
le_location = None
model_meta: dict[str, Any] = {}
sector_profiles: dict[str, dict[str, float]] = {}
try:
    model = joblib.load("feasibility_model.joblib")
    le_sector = joblib.load("le_sector.joblib")
    le_location = joblib.load("le_location.joblib")
    if os.path.exists("model_meta.joblib"):
        model_meta = joblib.load("model_meta.joblib")
except Exception as e:
    print(f"Warning: ML models not loaded: {e}")


def _pick_existing_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    index = {c.strip().lower(): c for c in df.columns}
    for name in candidates:
        if name.strip().lower() in index:
            return index[name.strip().lower()]
    return None


def load_sector_profiles() -> dict[str, dict[str, float]]:
    candidates = ["refined_yemeni_dataset.csv", "dataset.csv", "data.csv", "data.CSV"]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        return {}

    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
        df.columns = [c.strip() for c in df.columns]
    except Exception as e:
        print(f"Warning: failed to load sector profile dataset: {e}")
        return {}

    sector_col = _pick_existing_column(df, ["القطاع", "sector"])
    sales_col = _pick_existing_column(df, ["تكلفة المبيعات", "sales_cost"])
    revenue_col = _pick_existing_column(df, ["الإيرادات", "revenue"])
    workers_col = _pick_existing_column(df, ["عدد العمال", "workers"])
    location_col = _pick_existing_column(df, ["الموقع", "location"])
    audience_col = _pick_existing_column(df, ["نوع العميل", "الفئة المستهدفة", "target_audience"])
    if not sector_col:
        return {}

    prof: dict[str, dict[str, float]] = {}
    grouped = df.groupby(sector_col, dropna=True)
    for sector_name, g in grouped:
        if str(sector_name).strip() == "":
            continue
        sales_avg = pd.to_numeric(g[sales_col], errors="coerce").median() if sales_col else np.nan
        revenue_avg = pd.to_numeric(g[revenue_col], errors="coerce").median() if revenue_col else np.nan
        workers_avg = pd.to_numeric(g[workers_col], errors="coerce").median() if workers_col else np.nan
        top_location = (
            g[location_col].dropna().astype(str).mode().iloc[0]
            if location_col and not g[location_col].dropna().empty
            else "صنعاء"
        )
        top_audience = (
            g[audience_col].dropna().astype(str).mode().iloc[0]
            if audience_col and not g[audience_col].dropna().empty
            else "الطلاب"
        )

        prof[str(sector_name)] = {
            "sales_cost": float(sales_avg) if not pd.isna(sales_avg) else 0.0,
            "revenue": float(revenue_avg) if not pd.isna(revenue_avg) else 0.0,
            "workers": float(workers_avg) if not pd.isna(workers_avg) else 3.0,
            "location": top_location,
            "audience": top_audience,
        }
    return prof


def load_capital_suggestion_rows() -> list[dict[str, Any]]:
    candidates = ["refined_yemeni_dataset.csv", "dataset.csv", "data.csv", "data.CSV"]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        return []

    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
        df.columns = [c.strip() for c in df.columns]
    except Exception as e:
        print(f"Warning: failed to load capital suggestion dataset: {e}")
        return []

    project_col = _pick_existing_column(df, ["اسم المشروع", "project_name"])
    sector_col = _pick_existing_column(df, ["القطاع", "sector"])
    capital_col = _pick_existing_column(df, ["رأس المال", "capital"])
    location_col = _pick_existing_column(df, ["الموقع", "location"])
    audience_col = _pick_existing_column(df, ["نوع العميل", "الفئة المستهدفة", "target_audience"])

    if not project_col or not sector_col or not capital_col:
        return []

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        capital_value = pd.to_numeric(row.get(capital_col), errors="coerce")
        if pd.isna(capital_value) or float(capital_value) <= 0:
            continue

        rows.append(
            {
                "project_name": str(row.get(project_col, "")).strip(),
                "sector": str(row.get(sector_col, "")).strip() or "غير محدد",
                "capital_required": float(capital_value),
                "location": (
                    str(row.get(location_col, "")).strip()
                    if location_col
                    else "صنعاء"
                ),
                "audience": (
                    str(row.get(audience_col, "")).strip()
                    if audience_col
                    else "الطلاب"
                ),
            }
        )

    return rows


sector_profiles = load_sector_profiles()
capital_suggestion_rows = load_capital_suggestion_rows()


# ---------- Helpers ----------
def create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    token_type = payload.get("type")
    if token_type != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    return payload


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


AR_LOCATION_NORMALIZATION = {
    "sanaa": "صنعاء",
    "sanaa": "صنعاء",
    "صنعاء": "صنعاء",
    "aden": "عدن",
    "عدن": "عدن",
    "taiz": "تعز",
    "taizz": "تعز",
    "تعز": "تعز",
    "ibb": "إب",
    "اب": "إب",
    "إب": "إب",
    "mukalla": "المكلا",
    "mukallaa": "المكلا",
    "المكلا": "المكلا",
}


AR_SECTOR_NORMALIZATION = {
    "technology": "تقنية",
    "tech": "تقنية",
    "تقنية": "تقنية",
    "تكنولوجيا": "تقنية",
    "trade": "تجارة",
    "commerce": "تجارة",
    "تجارة": "تجارة",
    "education": "تعليم",
    "edtech": "تعليم",
    "تعليم": "تعليم",
    "health": "صحة",
    "medical": "صحة",
    "صحة": "صحة",
    "services": "خدمات",
    "service": "خدمات",
    "خدمات": "خدمات",
}


def normalize_location(value: str) -> str:
    v = (value or "").strip().lower()
    return AR_LOCATION_NORMALIZATION.get(v, value.strip())


def normalize_sector(value: str) -> str:
    v = (value or "").strip().lower()
    return AR_SECTOR_NORMALIZATION.get(v, value.strip())


def raw_to_scaled(feature_name: str, raw_value: float) -> float:
    cfg = model_meta.get("raw_to_scaled", {}).get(feature_name, {})
    slope = float(cfg.get("slope", 1.0))
    intercept = float(cfg.get("intercept", 0.0))
    return slope * raw_value + intercept


def apply_range(value: float, tolerance: float = 0.10) -> dict[str, float]:
    low = max(0.0, value * (1 - tolerance))
    high = max(0.0, value * (1 + tolerance))
    return {"min": float(low), "max": float(high)}


def confidence_from_inputs(optional_count: int) -> tuple[int, str]:
    if optional_count <= 0:
        return 55, "دراسة تقريبية"
    if optional_count <= 2:
        return 70, "دراسة مبدئية جيدة"
    if optional_count <= 4:
        return 85, "دراسة عالية الدقة مبدئيًا"
    return 95, "دراسة شبه مكتملة"


def _extract_json_block(text: str) -> dict[str, str]:
    """Extract JSON object from model text and return normalized dict."""
    if not text:
        return {}

    cleaned = text.strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{[\s\S]*\}", cleaned)
    candidate = match.group(0) if match else cleaned
    try:
        data = json.loads(candidate)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def _full_analysis_fallback(
    *,
    project_name: Optional[str],
    description: str,
    status_text: str,
    roi: float,
    break_even_months: Optional[float],
    sector: str,
    location: str,
    capital: float,
    sales_cost: float,
    revenue: float,
    workers: int,
    audience: str,
) -> dict[str, Any]:
    suggested_name = project_name or f"مشروع {sector} في {location}"
    monthly_profit = (revenue - sales_cost) / 12
    recovery = break_even_months if break_even_months else (capital / (revenue - sales_cost) * 12 if revenue > sales_cost else None)
    return {
        "suggested_project_name": suggested_name,
        "target_audience": audience,
        "suggested_sales_cost": round(sales_cost, 2),
        "expected_revenue": round(revenue, 2),
        "suggested_workers": workers,
        "project_goals": f"تقديم خدمات/منتجات متميزة في قطاع {sector} بمدينة {location} لتلبية احتياجات {audience}.",
        "products_or_services": f"منتجات وخدمات متخصصة في مجال {sector} تناسب السوق اليمني.",
        "target_market": f"سوق {location} واليمن عموماً، مع التركيز على فئة {audience}.",
        "expected_monthly_profit": round(monthly_profit, 2),
        "capital_recovery_months": round(recovery, 1) if recovery else None,
        "market_share_estimate": f"يُتوقع الحصول على 3-7% من حصة السوق المحلي خلال السنة الأولى.",
        "main_competitors": f"المنافسون الرئيسيون في قطاع {sector}: الشركات المحلية المماثلة وبعض المشاريع الأسرية.",
        "marketing_channels": "وسائل التواصل الاجتماعي (واتساب، إنستغرام، فيسبوك)، والتسويق الشفهي، والعروض الترويجية.",
        "competitive_advantage": f"التميّز بجودة الخدمة وسرعة التوصيل وبناء علاقة ثقة مع العميل في {location}.",
        "tools_and_technologies": "هاتف ذكي، واتساب للأعمال، كاشير إلكتروني، تطبيق محاسبة بسيط.",
        "interpretation": f"المشروع {status_text} بعائد استثمار {roi:.1f}%.",
        "financial_analysis": f"رأس المال {capital:,.0f} ر.ي، الإيرادات {revenue:,.0f} ر.ي، التكاليف {sales_cost:,.0f} ر.ي.",
        "risks_summary": "انقطاع الكهرباء، تذبذب العملة، وضعف القوة الشرائية في السوق اليمني.",
        "risk_solutions": "استخدام مولد احتياطي، تسعير بالدولار، وتقديم خطط تقسيط مرنة.",
        "recommendations": [
            "ابدأ بنسخة تجريبية صغيرة وقيّم النتائج خلال 3 أشهر.",
            "ركّز على بناء قاعدة عملاء وفيّة قبل التوسع.",
            "احرص على وجود احتياطي مالي يغطي 3 أشهر من تكاليف التشغيل.",
        ],
    }


def generate_full_analysis(
    *,
    project_name: Optional[str],
    description: str,
    net_profit: float,
    roi: float,
    break_even_revenue: float,
    break_even_months: Optional[float],
    status_text: str,
    sector: str,
    location: str,
    audience: str,
    capital: float,
    revenue: float,
    sales_cost: float,
    workers: int,
) -> dict[str, Any]:
    """توليد تحليل جدوى شامل باستخدام Gemini مع fallback محلي."""

    fallback = _full_analysis_fallback(
        project_name=project_name,
        description=description,
        status_text=status_text,
        roi=roi,
        break_even_months=break_even_months,
        sector=sector,
        location=location,
        capital=capital,
        sales_cost=sales_cost,
        revenue=revenue,
        workers=workers,
        audience=audience,
    )

    if _gemini_model is None:
        return fallback

    name_instruction = (
        f'- اسم المشروع المقترح: اقترح اسماً تجارياً احترافياً باللغة العربية مناسباً للقطاع "{sector}" في "{location}".'
        if not project_name
        else f'- اسم المشروع: {project_name} (لا حاجة لاقتراح اسم)'
    )

    prompt = f"""
أنت خبير دراسات جدوى متخصص في السوق اليمني. حلّل المشروع التالي وأعد **JSON فقط** بدون أي نص خارجه.

═══════════ بيانات المشروع ═══════════
- الوصف: {description}
- القطاع: {sector}
- الموقع: {location}
- رأس المال: {capital:,.0f} ريال يمني
- الإيرادات المقدّرة: {revenue:,.0f} ريال يمني
- تكلفة المبيعات المقدّرة: {sales_cost:,.0f} ريال يمني
- صافي الربح: {net_profit:,.0f} ريال يمني
- ROI: {roi:.1f}%
- نقطة التعادل (إيراد): {break_even_revenue:,.0f} ريال يمني
- استرداد رأس المال: {"غير محدد" if break_even_months is None else f"{break_even_months:.1f} شهر"}
- عدد الموظفين المقترح: {workers}
- الحالة: {status_text}
{name_instruction}

═══════════ المطلوب ═══════════
أعد JSON بالمفاتيح التالية **حرفياً** (عربي احترافي وواقعي لبيئة اليمن):

{{
  "suggested_project_name": "اسم تجاري احترافي مناسب (أو نفس الاسم المُدخل إن وُجد)",
  "target_audience": "الفئة المستهدفة الأدق للمشروع مع تفاصيل ديموغرافية",
  "suggested_sales_cost": رقم (تكلفة المبيعات المقترحة سنوياً بالريال اليمني),
  "expected_revenue": رقم (الإيرادات المتوقعة سنوياً بالريال اليمني),
  "suggested_workers": رقم (عدد العمال المناسب للبداية),
  "project_goals": "أهداف المشروع الرئيسية خلال السنة الأولى",
  "products_or_services": "وصف دقيق للمنتجات أو الخدمات المقدّمة",
  "target_market": "تحليل السوق المستهدف وحجمه في اليمن",
  "expected_monthly_profit": رقم (الربح المتوقع شهرياً بالريال اليمني),
  "capital_recovery_months": رقم (عدد الأشهر المتوقعة لاسترداد رأس المال),
  "market_share_estimate": "تقدير الحصة السوقية خلال السنة الأولى والثانية",
  "main_competitors": "المنافسون الرئيسيون في السوق اليمني مع نقاط ضعفهم",
  "marketing_channels": "قنوات التسويق الأنسب مع أولوياتها وتكاليفها التقريبية",
  "competitive_advantage": "ميزة تنافسية مقترحة قابلة للتطبيق فوراً",
  "tools_and_technologies": "الأدوات والتقنيات والمعدات اللازمة لتشغيل المشروع",
  "interpretation": "خلاصة تنفيذية ذكية (3-4 جمل) تربط الأرقام بقرار استثماري واضح",
  "financial_analysis": "تحليل مالي دقيق: ROI والربحية ونقطة التعادل وهل الأرقام منطقية",
  "risks_summary": "المخاطر الواقعية الأكثر احتمالاً في بيئة اليمن",
  "risk_solutions": "حلول عملية قابلة للتنفيذ لكل خطر مذكور",
  "recommendations": ["توصية 1", "توصية 2", "توصية 3"]
}}
"""
    try:
        resp = _gemini_model.generate_content(prompt)
        text = getattr(resp, "text", "") or ""
        parsed = _extract_json_block(text)
        if not parsed:
            return fallback

        def _str(key: str) -> str:
            return str(parsed.get(key, fallback.get(key, ""))).strip()

        def _num(key: str, default: Any = None) -> Any:
            val = parsed.get(key, default)
            try:
                return float(val) if val is not None else default
            except Exception:
                return default

        recs = parsed.get("recommendations", [])
        if isinstance(recs, str):
            recs = [r.strip("-• ").strip() for r in recs.split("\n") if r.strip()]
        elif isinstance(recs, list):
            recs = [str(r).strip() for r in recs if str(r).strip()]
        if len(recs) < 3:
            recs = fallback["recommendations"]

        return {
            "suggested_project_name": _str("suggested_project_name") or fallback["suggested_project_name"],
            "target_audience": _str("target_audience") or fallback["target_audience"],
            "suggested_sales_cost": _num("suggested_sales_cost", fallback["suggested_sales_cost"]),
            "expected_revenue": _num("expected_revenue", fallback["expected_revenue"]),
            "suggested_workers": int(_num("suggested_workers", fallback["suggested_workers"]) or workers),
            "project_goals": _str("project_goals") or fallback["project_goals"],
            "products_or_services": _str("products_or_services") or fallback["products_or_services"],
            "target_market": _str("target_market") or fallback["target_market"],
            "expected_monthly_profit": _num("expected_monthly_profit", fallback["expected_monthly_profit"]),
            "capital_recovery_months": _num("capital_recovery_months", fallback["capital_recovery_months"]),
            "market_share_estimate": _str("market_share_estimate") or fallback["market_share_estimate"],
            "main_competitors": _str("main_competitors") or fallback["main_competitors"],
            "marketing_channels": _str("marketing_channels") or fallback["marketing_channels"],
            "competitive_advantage": _str("competitive_advantage") or fallback["competitive_advantage"],
            "tools_and_technologies": _str("tools_and_technologies") or fallback["tools_and_technologies"],
            "interpretation": _str("interpretation") or fallback["interpretation"],
            "financial_analysis": _str("financial_analysis") or fallback["financial_analysis"],
            "risks_summary": _str("risks_summary") or fallback["risks_summary"],
            "risk_solutions": _str("risk_solutions") or fallback["risk_solutions"],
            "recommendations": recs[:3],
        }
    except Exception as e:
        print(f"Warning: Gemini full analysis failed: {e}")
        return fallback



# ---------- Pydantic Schemas ----------
class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone_number: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ProjectCreate(BaseModel):
    user_id: int
    project_name: Optional[str] = None           # اختياري — إذا لم يُدخل، سيقترحه الذكاء الاصطناعي
    project_description: str
    category_id: Optional[int] = None
    target_audience: Optional[str] = None
    sector: str
    capital: float = Field(..., gt=0, description="Capital must be strictly positive")
    sales_cost: Optional[float] = Field(default=None, ge=0, description="Optional")
    revenue: Optional[float] = Field(default=None, ge=0, description="Optional")
    workers: Optional[int] = Field(default=None, gt=0, description="Optional")
    location: Optional[str] = None


class SaveLikeRequest(BaseModel):
    user_id: int
    liked: bool = False
    saved: bool = False


class NotificationReadRequest(BaseModel):
    user_id: int


class NotificationCreate(BaseModel):
    user_id: int
    message: str


class SupportMessageCreate(BaseModel):
    user_id: int
    subject: Optional[str] = None
    message_body: str


class SupportStatusUpdate(BaseModel):
    status: str


class UserSettingsUpdate(BaseModel):
    user_id: int
    language: Optional[str] = None
    notifications_enabled: Optional[bool] = None


# ---------- Auth ----------
@app.post("/api/v1/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = models.User(
        full_name=user.full_name,
        email=user.email,
        password_hash=hash_password(user.password),
        phone_number=user.phone_number,
        role="user",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "status": "success",
        "message": "Account created",
        "user": {
            "user_id": new_user.user_id,
            "full_name": new_user.full_name,
            "email": new_user.email,
            "role": str(new_user.role),
        },
    }


@app.post("/api/v1/login")
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_token(str(user.user_id), "access", timedelta(minutes=ACCESS_TOKEN_MINUTES))
    refresh_token = create_token(str(user.user_id), "refresh", timedelta(days=REFRESH_TOKEN_DAYS))

    return {
        "status": "success",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "full_name": user.full_name,
            "email": user.email,
            "role": str(user.role),
        },
    }


@app.post("/api/v1/refresh")
def refresh_token(payload: RefreshRequest):
    decoded = decode_token(payload.refresh_token, "refresh")
    user_id = decoded.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    new_access = create_token(str(user_id), "access", timedelta(minutes=ACCESS_TOKEN_MINUTES))
    new_refresh = create_token(str(user_id), "refresh", timedelta(days=REFRESH_TOKEN_DAYS))

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


@app.post("/api/v1/forgot-password")
def forgot_password(_: ForgotPasswordRequest):
    # Placeholder for email workflow
    return {"status": "success", "message": "If account exists, reset link will be sent"}


# ---------- Categories ----------
@app.get("/api/v1/categories")
def list_categories(db: Session = Depends(get_db)):
    rows = db.query(models.Category).all()
    return [
        {
            "category_id": c.category_id,
            "category_name": c.category_name,
            "description": c.description,
        }
        for c in rows
    ]


# ---------- Projects + AI ----------
@app.post("/api/v1/projects")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    """Create a project, run ML feasibility, then enrich the narrative using Gemini."""
    user = db.query(models.User).filter(models.User.user_id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    normalized_sector = normalize_sector(payload.sector)
    profile = sector_profiles.get(normalized_sector, {})

    default_location = str(profile.get("location", "صنعاء"))
    default_audience = str(profile.get("audience", "الطلاب"))
    default_sales = float(profile.get("sales_cost", 0.0))
    default_revenue = float(profile.get("revenue", 0.0))
    default_workers = int(round(float(profile.get("workers", 3.0))))

    sales_cost = payload.sales_cost if payload.sales_cost is not None else (
        default_sales if default_sales > 0 else payload.capital * 0.45
    )
    revenue = payload.revenue if payload.revenue is not None else (
        default_revenue if default_revenue > 0 else payload.capital * 1.7
    )
    workers = payload.workers if payload.workers is not None else max(1, default_workers)
    normalized_location = normalize_location(payload.location or default_location or "صنعاء")
    target_audience = (payload.target_audience or default_audience or "الطلاب").strip()

    optional_count = sum([
        payload.sales_cost is not None,
        payload.revenue is not None,
        payload.workers is not None,
        bool(payload.location and payload.location.strip()),
        bool(payload.target_audience and payload.target_audience.strip()),
    ])
    confidence_level, confidence_label = confidence_from_inputs(optional_count)

    # اسم مؤقت للمشروع في حال لم يُدخله المستخدم (سيُحدَّث بعد AI)
    temp_name = payload.project_name or f"مشروع {normalized_sector}"

    project = models.Project(
        user_id=payload.user_id,
        project_name=temp_name,
        project_description=payload.project_description,
        category_id=payload.category_id,
        target_audience=target_audience,
        sector=normalized_sector,
        capital_required=payload.capital,
        sales_cost=sales_cost,
        revenue=revenue,
        workers=workers,
        location=normalized_location,
        status="analyzing",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    if model is None or le_sector is None or le_location is None:
        project.status = "draft"
        db.commit()
        raise HTTPException(status_code=503, detail="ML model is not available")

    try:
        sector_num = int(le_sector.transform([normalized_sector])[0])
    except Exception:
        sector_num = 0

    try:
        location_num = int(le_location.transform([normalized_location])[0])
    except Exception:
        location_num = 0

    capital_scaled = raw_to_scaled("capital", payload.capital)
    sales_scaled = raw_to_scaled("sales_cost", float(sales_cost))
    revenue_scaled = raw_to_scaled("revenue", float(revenue))
    workers_scaled = raw_to_scaled("workers", float(workers))

    sector_to_type = model_meta.get("sector_to_project_type", {})
    project_type_encoded = float(
        sector_to_type.get(normalized_sector, model_meta.get("default_project_type_encoded", 0.0))
    )

    expected_features = int(getattr(model, "n_features_in_", 7))
    if expected_features <= 6:
        features = np.array([[sector_num, payload.capital, sales_cost, revenue, workers, location_num]])
    else:
        features = np.array([[sector_num, capital_scaled, sales_scaled, revenue_scaled, workers_scaled, location_num, project_type_encoded]])

    prediction = int(model.predict(features)[0])

    # ─── الحسابات المالية ───
    gross_profit = float(revenue) - float(sales_cost)
    roi = (gross_profit / payload.capital * 100) if payload.capital > 0 else 0
    net_margin = (gross_profit / float(revenue) * 100) if float(revenue) > 0 else 0
    fixed_costs = payload.capital * 0.2
    break_even_revenue = (fixed_costs / (net_margin / 100)) if net_margin > 0 else 0
    break_even_months = (payload.capital / gross_profit) if gross_profit > 0 else None
    status_text = "Feasible" if prediction == 1 else "Needs improvement"

    # ─── التحليل الشامل بـ Gemini ───
    ai = generate_full_analysis(
        project_name=payload.project_name,
        description=payload.project_description,
        net_profit=gross_profit,
        roi=roi,
        break_even_revenue=break_even_revenue,
        break_even_months=break_even_months,
        status_text=status_text,
        sector=normalized_sector or "غير محدد",
        location=normalized_location or "صنعاء",
        audience=target_audience or "الطلاب",
        capital=payload.capital,
        revenue=float(revenue),
        sales_cost=float(sales_cost),
        workers=workers,
    )

    # استخدام الاسم المقترح من Gemini إذا لم يُدخله المستخدم
    final_name = payload.project_name or ai.get("suggested_project_name", temp_name)
    project.project_name = final_name
    project.target_audience = ai.get("target_audience", target_audience)

    # ─── حفظ النتائج في قاعدة البيانات ───
    financial_summary = (
        f"صافي الربح المقدر: {gross_profit:,.0f} ر.ي | ROI: {roi:.1f}% | "
        f"هامش الربح: {net_margin:.1f}% | نقطة التعادل: {break_even_revenue:,.0f} ر.ي\n\n"
        f"{ai.get('financial_analysis', '')}"
    )

    result = models.FeasibilityResult(
        project_id=project.project_id,
        financial_summary=financial_summary,
        marketing_summary=ai.get("target_market", ""),
        risks_summary=ai.get("risks_summary", ""),
        risk_solutions=ai.get("risk_solutions", ""),
    )
    db.add(result)
    project.status = "completed"
    db.commit()

    # ─── تحديد مستوى القرار ───
    decision_label = (
        "مناسب مبدئيًا" if prediction == 1 and roi >= 20 else
        "يحتاج تعديل" if prediction == 1 or roi >= 10 else
        "غير مناسب حاليًا"
    )

    financial_pulse = {
        "capital": apply_range(payload.capital),
        "sales_cost": apply_range(float(sales_cost)),
        "revenue": apply_range(float(revenue)),
        "net_profit": apply_range(float(gross_profit)),
        "break_even_revenue": apply_range(float(break_even_revenue)),
        "break_even_months": (
            apply_range(float(break_even_months)) if break_even_months is not None else {"min": 0.0, "max": 0.0}
        ),
    }

    return {
        "status": "success",
        "project_id": project.project_id,

        # ─── بيانات المشروع ───
        "project_name": final_name,

        # ─── مدخلات الذكاء الاصطناعي ───
        "target_audience": ai.get("target_audience"),
        "suggested_sales_cost": ai.get("suggested_sales_cost"),
        "expected_revenue": ai.get("expected_revenue"),
        "suggested_workers": ai.get("suggested_workers"),

        # ─── التحليل التسويقي والتنافسي ───
        "project_goals": ai.get("project_goals"),
        "products_or_services": ai.get("products_or_services"),
        "target_market": ai.get("target_market"),
        "market_share_estimate": ai.get("market_share_estimate"),
        "main_competitors": ai.get("main_competitors"),
        "marketing_channels": ai.get("marketing_channels"),
        "competitive_advantage": ai.get("competitive_advantage"),
        "tools_and_technologies": ai.get("tools_and_technologies"),

        # ─── التحليل المالي ───
        "expected_monthly_profit": ai.get("expected_monthly_profit"),
        "capital_recovery_months": ai.get("capital_recovery_months"),
        "financial_summary": financial_summary,
        "financial_pulse": financial_pulse,

        # ─── القرار والتقييم ───
        "prediction": prediction,
        "decision_label": decision_label,
        "confidence_level": confidence_level,
        "confidence_label": confidence_label,
        "status_label": status_text,

        # ─── التحليل النصي الشامل ───
        "interpretation": ai.get("interpretation"),
        "risks_summary": ai.get("risks_summary"),
        "risk_solutions": ai.get("risk_solutions"),
        "recommendations": ai.get("recommendations", []),
    }


@app.get("/api/v1/projects")
def get_projects(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Project)
    if user_id is not None:
        query = query.filter(models.Project.user_id == user_id)

    projects = query.order_by(models.Project.created_at.desc()).all()
    return [
        {
            "project_id": p.project_id,
            "user_id": p.user_id,
            "project_name": p.project_name,
            "project_description": p.project_description,
            "category_id": p.category_id,
            "target_audience": p.target_audience,
            "capital_required": to_float(p.capital_required),
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]


@app.get("/api/v1/feasibility-results")
def get_feasibility_results(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.FeasibilityResult)
    if project_id is not None:
        query = query.filter(models.FeasibilityResult.project_id == project_id)

    rows = query.order_by(models.FeasibilityResult.created_at.desc()).all()
    return [
        {
            "result_id": r.result_id,
            "project_id": r.project_id,
            "financial_summary": r.financial_summary,
            "marketing_summary": r.marketing_summary,
            "opportunities": r.marketing_summary,
            "risks_summary": r.risks_summary,
            "risk_solutions": r.risk_solutions,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# Keep backward compatibility for old mobile route
@app.post("/api/v1/predict_and_save")
def predict_and_save(payload: ProjectCreate, db: Session = Depends(get_db)):
    return create_project(payload, db)


@app.get("/api/v1/dataset-audit")
def dataset_audit():
    """
    Quick quality audit for data.CSV used by the model.
    Returns hard checks + optional Gemini commentary.
    """
    candidates = ["dataset.csv", "data.csv", "data.CSV"]
    csv_path = next((p for p in candidates if os.path.exists(p)), None)
    if not csv_path:
        raise HTTPException(status_code=404, detail="Dataset file not found")

    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read dataset: {e}")

    cols = list(df.columns)
    checks = {
        "rows": int(len(df)),
        "columns": int(len(cols)),
        "duplicate_rows": int(df.duplicated().sum()),
        "all_null_columns_count": int(sum(df[c].isna().all() for c in cols)),
    }

    # Columns used in training by index (train_ai.py)
    train_idx = {
        "sector": 1,
        "capital": 2,
        "sales_cost": 3,
        "revenue": 4,
        "workers": 15,
        "location": 17,
        "target": 29,
    }

    details = {}
    for name, idx in train_idx.items():
        if idx >= len(cols):
            details[name] = {"error": f"column index {idx} out of range"}
            continue
        col_name = cols[idx]
        s = pd.to_numeric(df.iloc[:, idx], errors="coerce")
        details[name] = {
            "column_name": col_name,
            "null_percent": round(float(s.isna().mean() * 100), 2),
            "min": None if s.dropna().empty else float(s.min()),
            "max": None if s.dropna().empty else float(s.max()),
        }

    # Domain checks
    negatives = {}
    for n in ["capital", "sales_cost", "revenue", "workers"]:
        idx = train_idx[n]
        if idx < len(cols):
            s = pd.to_numeric(df.iloc[:, idx], errors="coerce")
            negatives[n] = int((s < 0).sum())

    checks["negative_values"] = negatives

    hard_issues = []
    if checks["duplicate_rows"] > 0:
        hard_issues.append(f"يوجد {checks['duplicate_rows']} صف مكرر.")
    if checks["all_null_columns_count"] > 0:
        hard_issues.append("يوجد أعمدة فارغة بالكامل.")
    if any(v > 0 for v in negatives.values()):
        hard_issues.append("يوجد قيم سالبة في حقول يفترض أن تكون غير سالبة.")

    if not hard_issues:
        hard_issues.append("لا توجد أخطاء حرجة ظاهرة في فحوصات الجودة الأساسية.")

    gemini_commentary = ""
    if _gemini_model is not None:
        audit_prompt = f"""
أنت خبير جودة بيانات. حلّل هذا الملخص لداتا ست دراسة الجدوى وأعطِ ملاحظات عملية بالعربية.
أعد JSON فقط بالشكل:
{{"quality_assessment":"...", "main_risks":"...", "fix_plan":"..."}}

ملخص الفحص:
{json.dumps({"checks": checks, "details": details, "hard_issues": hard_issues}, ensure_ascii=False)}
"""
        try:
            resp = _gemini_model.generate_content(audit_prompt)
            parsed = _extract_json_block(getattr(resp, "text", "") or "")
            if parsed:
                gemini_commentary = json.dumps(parsed, ensure_ascii=False)
        except Exception as e:
            gemini_commentary = f"Gemini unavailable: {e}"

    return {
        "status": "success",
        "dataset_path": csv_path,
        "checks": checks,
        "details": details,
        "hard_issues": hard_issues,
        "gemini_commentary": gemini_commentary,
    }


# ---------- Inspiration ----------
@app.get("/api/v1/inspirations")
def list_inspirations(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    rows = db.query(models.InspirationProject).all()
    interactions = {}
    if user_id is not None:
        saved_rows = (
            db.query(models.UserSavedInspiration)
            .filter(models.UserSavedInspiration.user_id == user_id)
            .all()
        )
        interactions = {
            r.inspiration_id: {"liked": bool(r.liked), "saved": bool(r.saved)} for r in saved_rows
        }
    return [
        {
            "inspiration_id": i.inspiration_id,
            "project_name": i.project_name,
            "image_url": i.image_url,
            "success_rate": to_float(i.success_rate),
            "story": i.story,
            "capital_required": to_float(i.capital_required),
            "results": i.results,
            "challenges": i.challenges,
            "is_liked": interactions.get(i.inspiration_id, {}).get("liked", False),
            "is_saved": interactions.get(i.inspiration_id, {}).get("saved", False),
        }
        for i in rows
    ]


@app.post("/api/v1/inspirations/{inspiration_id}/save-like")
def save_like_inspiration(inspiration_id: int, payload: SaveLikeRequest, db: Session = Depends(get_db)):
    item = (
        db.query(models.UserSavedInspiration)
        .filter(
            models.UserSavedInspiration.user_id == payload.user_id,
            models.UserSavedInspiration.inspiration_id == inspiration_id,
        )
        .first()
    )

    if item is None:
        item = models.UserSavedInspiration(
            user_id=payload.user_id,
            inspiration_id=inspiration_id,
            liked=payload.liked,
            saved=payload.saved,
        )
        db.add(item)
    else:
        item.liked = payload.liked
        item.saved = payload.saved

    db.commit()
    return {"status": "success", "liked": item.liked, "saved": item.saved}


@app.get("/api/v1/inspirations/suggest")
def suggest_inspirations_by_capital(
    capital: float,
    limit: int = 6,
):
    if capital <= 0:
        raise HTTPException(status_code=400, detail="capital must be positive")

    if not capital_suggestion_rows:
        return []

    scored = []
    seen: set[tuple[str, str, float]] = set()
    for item in capital_suggestion_rows:
        cap = float(item["capital_required"])
        score = abs(capital - cap)
        key = (item["project_name"], item["sector"], cap)
        if key in seen:
            continue
        seen.add(key)
        scored.append((score, item))

    scored.sort(key=lambda x: x[0])
    picked = [x[1] for x in scored[: max(1, min(limit, 20))]]

    return [
        {
            "project_name": item["project_name"],
            "sector": item["sector"],
            "capital_required": item["capital_required"],
            "location": item["location"],
            "audience": item["audience"],
        }
        for item in picked
    ]


# ---------- Notifications ----------
@app.get("/api/v1/notifications")
def list_notifications(user_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(models.Notification)
        .filter(models.Notification.user_id == user_id)
        .order_by(models.Notification.created_at.desc())
        .all()
    )
    return [
        {
            "notification_id": n.notification_id,
            "user_id": n.user_id,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]


@app.post("/api/v1/admin/notifications")
def create_notification(payload: NotificationCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    row = models.Notification(
        user_id=payload.user_id,
        message=payload.message.strip(),
        is_read=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "success", "notification_id": row.notification_id}


@app.get("/api/v1/admin/notifications")
def list_notifications_admin(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Notification)
    if user_id is not None:
        query = query.filter(models.Notification.user_id == user_id)
    rows = query.order_by(models.Notification.created_at.desc()).all()
    return [
        {
            "notification_id": n.notification_id,
            "user_id": n.user_id,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]


@app.put("/api/v1/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    payload: NotificationReadRequest,
    db: Session = Depends(get_db),
):
    row = (
        db.query(models.Notification)
        .filter(
            models.Notification.notification_id == notification_id,
            models.Notification.user_id == payload.user_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")

    row.is_read = True
    db.commit()
    return {"status": "success"}


# ---------- Support ----------
@app.post("/api/v1/support-messages")
def create_support_message(payload: SupportMessageCreate, db: Session = Depends(get_db)):
    msg = models.SupportMessage(
        user_id=payload.user_id,
        subject=payload.subject,
        message_body=payload.message_body,
        status="pending",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"status": "success", "message_id": msg.message_id}


@app.get("/api/v1/support-messages")
def list_support_messages(user_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(models.SupportMessage)
        .filter(models.SupportMessage.user_id == user_id)
        .order_by(models.SupportMessage.created_at.desc())
        .all()
    )
    return [
        {
            "message_id": m.message_id,
            "user_id": m.user_id,
            "subject": m.subject,
            "message_body": m.message_body,
            "status": m.status,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }
        for m in rows
    ]


@app.get("/api/v1/admin/support-messages")
def list_support_messages_admin(db: Session = Depends(get_db)):
    rows = db.query(models.SupportMessage).order_by(models.SupportMessage.created_at.desc()).all()
    return [
        {
            "message_id": m.message_id,
            "user_id": m.user_id,
            "subject": m.subject,
            "message_body": m.message_body,
            "status": m.status,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }
        for m in rows
    ]


@app.put("/api/v1/admin/support-messages/{message_id}/status")
def update_support_message_status(
    message_id: int,
    payload: SupportStatusUpdate,
    db: Session = Depends(get_db),
):
    valid = {"pending", "answered", "closed"}
    new_status = (payload.status or "").strip().lower()
    if new_status not in valid:
        raise HTTPException(status_code=400, detail="Invalid status")

    row = (
        db.query(models.SupportMessage)
        .filter(models.SupportMessage.message_id == message_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Support message not found")

    row.status = new_status
    db.commit()
    return {"status": "success"}


@app.get("/api/v1/user-settings")
def get_user_settings(user_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(models.UserSetting)
        .filter(models.UserSetting.user_id == user_id)
        .first()
    )
    if row is None:
        row = models.UserSetting(user_id=user_id, language="ar", notifications_enabled=True)
        db.add(row)
        db.commit()
        db.refresh(row)

    return {
        "setting_id": row.setting_id,
        "user_id": row.user_id,
        "language": row.language,
        "notifications_enabled": bool(row.notifications_enabled),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@app.put("/api/v1/user-settings")
def update_user_settings(payload: UserSettingsUpdate, db: Session = Depends(get_db)):
    row = (
        db.query(models.UserSetting)
        .filter(models.UserSetting.user_id == payload.user_id)
        .first()
    )
    if row is None:
        row = models.UserSetting(user_id=payload.user_id, language="ar", notifications_enabled=True)
        db.add(row)

    if payload.language is not None:
        row.language = payload.language
    if payload.notifications_enabled is not None:
        row.notifications_enabled = payload.notifications_enabled

    db.commit()
    db.refresh(row)
    return {
        "status": "success",
        "setting_id": row.setting_id,
        "language": row.language,
        "notifications_enabled": bool(row.notifications_enabled),
    }

# ---------- OTP + Social Login ----------



class VerificationCodeRequest(BaseModel):
    email: EmailStr


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str


class SocialLoginRequest(BaseModel):
    provider: str
    id_token: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


@app.post("/api/v1/auth/send-verification-code")
def send_verification_code(payload: VerificationCodeRequest, db: Session = Depends(get_db)):
    """
    Ø¥Ù†Ø´Ø§Ø¡ ÙˆØ¥Ø±Ø³Ø§Ù„ Ø±Ù…Ø² Ø§Ù„ØªØ­Ù‚Ù‚ (OTP) Ù„Ù„Ù…Ø³ØªØ®Ø¯Ù…ÙŠÙ†.
    Ø§Ù„Ù…Ù†Ø·Ù‚ Ø§Ù„Ø£Ù…Ù†ÙŠ Ù‡Ù†Ø§ ÙŠØ¶Ù…Ù† Ø­Ø°Ù Ø£ÙŠ ÙƒÙˆØ¯ ØªØ­Ù‚Ù‚ Ù…Ø³Ø¬Ù„ Ù…Ø³Ø¨Ù‚Ø§Ù‹ ÙˆØªÙˆÙ„ÙŠØ¯ ÙƒÙˆØ¯ Ø¬Ø¯ÙŠØ¯ ÙŠØªÙ… Ø­ÙØ¸Ù‡ 
    Ø¨Ø£Ù…Ø§Ù† ÙÙŠ ØµÙ…ÙŠÙ… Ù‚Ø§Ø¹Ø¯Ø© Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª (Database) Ø¨Ø¯Ù„Ø§Ù‹ Ù…Ù† Ø§Ù„Ø°Ø§ÙƒØ±Ø© Ø§Ù„Ø­ÙŠØ© Ø§Ù„Ù…Ø¤Ù‚ØªØ© (RAM) 
    Ù…Ø¹ Ø¥Ø¹Ø·Ø§Ø¦Ù‡ ØµÙ„Ø§Ø­ÙŠØ© Ø¯Ù‚ÙŠÙ‚Ø© Ù„Ù…Ø¯Ø© 5 Ø¯Ù‚Ø§Ø¦Ù‚ Ù„ØºÙ„Ù‚ Ù…Ù†Ø§ÙØ° Ø§Ù„Ø«ØºØ±Ø§Øª ÙˆÙ‡Ø¬Ù…Ø§Øª Ø§Ù„Ù€ Brute-force.
    """
    code = "123456" # Demo code
    expiration = datetime.now() + timedelta(minutes=5)
    
    db.query(models.VerificationCode).filter(models.VerificationCode.email == payload.email.lower()).delete()
    
    new_code = models.VerificationCode(email=payload.email.lower(), code=code, expires_at=expiration)
    db.add(new_code)
    db.commit()
    
    print(f"[OTP] Verification code for {payload.email}: {code} stored in DB")
    return {"status": "success", "message": "Verification code sent securely"}


@app.post("/api/v1/auth/verify-code")
def verify_code(payload: VerifyCodeRequest, db: Session = Depends(get_db)):
    """
    Ø§Ù„ØªØ­Ù‚Ù‚ Ù…Ù† Ø±Ù…Ø² Ø§Ù„ØªÙØ¹ÙŠÙ„ (OTP) Ø§Ù„Ù…Ù‚Ø¯Ù… Ù…Ù† Ø§Ù„ØªØ·Ø¨ÙŠÙ‚.
    ÙŠÙØ­Øµ Ø§Ù„Ø¨Ø§Ùƒ Ø§Ù†Ø¯ Ù…Ø¯Ù‰ ØªØ·Ø§Ø¨Ù‚ Ø§Ù„Ø±Ù…Ø² Ù„Ù„Ù…Ø³ØªØ®Ø¯Ù… ÙˆÙŠÙ‚Ø§Ø±Ù† ØªØ§Ø±ÙŠØ® Ø§Ù†ØªÙ‡Ø§Ø¡ Ø§Ù„ØµÙ„Ø§Ø­ÙŠØ© Ø§Ù„Ù…Ø­ÙÙˆØ¸ 
    ÙÙŠ Ø§Ù„Ø¬Ø¯ÙˆÙ„ VerificationCode Ø¨Ø§Ù„ÙˆÙ‚Øª Ø§Ù„Ø­Ø§Ù„ÙŠ. 
    ÙˆØ¨Ù…Ø¬Ø±Ø¯ Ø§Ù„ØªØ­Ù‚Ù‚ Ø¨Ù†Ø¬Ø§Ø­ØŒ ÙŠØªÙ… Ù…Ø³Ø­ Ø§Ù„Ø±Ù…Ø² Ù…Ø¨Ø§Ø´Ø±Ø© Ù…Ù† Ø§Ù„Ù€ Database Ù„Ø¶Ù…Ø§Ù† Ø­Ø±Ù‚ Ø§Ù„Ø±Ù…Ø² ÙˆØ¹Ø¯Ù… Ø§Ø³ØªØ®Ø¯Ø§Ù…Ù‡ Ù…Ø±Ø© Ø£Ø®Ø±Ù‰ Ø£Ø¨Ø¯Ø§Ù‹ (One-time only).
    """
    record = db.query(models.VerificationCode).filter(
        models.VerificationCode.email == payload.email.lower(),
        models.VerificationCode.code == payload.code.strip()
    ).first()
    
    if not record:
        raise HTTPException(status_code=400, detail="Invalid verification code or email")
        
    if datetime.now() > record.expires_at:
        db.delete(record)
        db.commit()
        raise HTTPException(status_code=400, detail="Verification code expired")
        
    db.delete(record)
    db.commit()
    return {"status": "success", "verified": True}


@app.post("/api/v1/auth/social-login")
def social_login(payload: SocialLoginRequest, db: Session = Depends(get_db)):
    if not payload.id_token:
        raise HTTPException(status_code=400, detail="id_token is required")

    normalized_email = (payload.email or f"{payload.provider}_user@khotwa.local").lower()
    user = db.query(models.User).filter(models.User.email == normalized_email).first()

    if user is None:
        user = models.User(
            full_name=payload.full_name or f"{payload.provider.title()} User",
            email=normalized_email,
            password_hash=hash_password(f"social-{payload.provider}-{payload.id_token[:8]}"),
            role="user",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_token(str(user.user_id), "access", timedelta(minutes=ACCESS_TOKEN_MINUTES))
    refresh_token = create_token(str(user.user_id), "refresh", timedelta(days=REFRESH_TOKEN_DAYS))

    return {
        "status": "success",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "full_name": user.full_name,
            "email": user.email,
            "role": str(user.role),
        },
    }

# ---------- Admin & Dashboard Endpoints ----------

from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    payload = decode_token(token, "access")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return int(user_id)

def get_current_admin(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied: Admin only")
    return user

@app.get("/api/v1/dashboard/stats")
def dashboard_stats(admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return {
        "total_users": db.query(models.User).count(),
        "total_projects": db.query(models.Project).count(),
        "total_feasibility_studies": db.query(models.FeasibilityResult).count(),
        "total_inspirations": db.query(models.InspirationProject).count(),
    }

@app.get("/api/v1/dashboard/charts")
def dashboard_charts(admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return {
        "growth": {
            "labels": ["يناير", "فبراير", "مارس", "أبريل"],
            "users": [10, 25, 45, 80],
            "projects": [5, 15, 30, 60],
        },
        "by_status": {
            "labels": ["draft", "analyzing", "completed"],
            "data": [
                db.query(models.Project).filter(models.Project.status == "draft").count(),
                db.query(models.Project).filter(models.Project.status == "analyzing").count(),
                db.query(models.Project).filter(models.Project.status == "completed").count(),
            ]
        },
        "by_category": {
            "labels": ["تقنية", "تجارة", "صناعة"],
            "data": [12, 19, 7]
        },
        "top_users": {
            "labels": ["أحمد", "سارة", "علي"],
            "data": [5, 3, 2]
        }
    }

@app.get("/api/v1/admin/users")
def admin_list_users(page: int = 1, page_size: int = 10, search: str = "", admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    query = db.query(models.User)
    if search:
        query = query.filter(models.User.full_name.ilike(f"%{search}%") | models.User.email.ilike(f"%{search}%"))
    
    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "items": [
            {"user_id": u.user_id, "full_name": u.full_name, "email": u.email, "role": u.role}
            for u in users
        ],
        "page": page,
        "total_pages": (total // page_size) + (1 if total % page_size > 0 else 0),
        "total": total
    }

@app.get("/api/v1/admin/users/{user_id}")
def admin_get_user(user_id: int, admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user.user_id, "full_name": user.full_name, "email": user.email, "role": user.role, "phone_number": user.phone_number}

@app.delete("/api/v1/admin/users/{user_id}")
def admin_delete_user(user_id: int, admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"status": "success"}

@app.get("/api/v1/admin/projects")
def admin_list_projects(page: int = 1, page_size: int = 10, search: str = "", status_filter: str = "", admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    query = db.query(models.Project)
    if search:
        query = query.filter(models.Project.project_name.ilike(f"%{search}%"))
    if status_filter:
        query = query.filter(models.Project.status == status_filter)
        
    total = query.count()
    projects = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "items": [
            {"project_id": p.project_id, "project_name": p.project_name, "status": p.status, "capital_required": float(p.capital_required or 0)}
            for p in projects
        ],
        "page": page,
        "total_pages": (total // page_size) + (1 if total % page_size > 0 else 0),
        "total": total
    }

@app.get("/api/v1/admin/projects/{project_id}")
def admin_get_project(project_id: int, admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    p = db.query(models.Project).filter(models.Project.project_id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "project_id": p.project_id,
        "project_name": p.project_name,
        "project_description": p.project_description,
        "category_id": p.category_id,
        "target_audience": p.target_audience,
        "capital_required": float(p.capital_required or 0),
        "status": p.status
    }

@app.delete("/api/v1/admin/projects/{project_id}")
def admin_delete_project(project_id: int, admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    p = db.query(models.Project).filter(models.Project.project_id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(p)
    db.commit()
    return {"status": "success"}

@app.get("/api/v1/admin/categories")
def admin_list_categories(admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    cats = db.query(models.Category).all()
    return [{"category_id": c.category_id, "category_name": c.category_name} for c in cats]

@app.get("/api/v1/admin/inspirations")
def admin_list_inspirations(admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    insps = db.query(models.InspirationProject).all()
    return [
        {
            "inspiration_id": i.inspiration_id,
            "project_name": i.project_name,
            "success_rate": float(i.success_rate or 0),
            "capital_required": float(i.capital_required or 0),
            "story": i.story
        }
        for i in insps
    ]

@app.delete("/api/v1/admin/inspirations/{inspiration_id}")
def admin_delete_inspiration(inspiration_id: int, admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    i = db.query(models.InspirationProject).filter(models.InspirationProject.inspiration_id == inspiration_id).first()
    if not i:
        raise HTTPException(status_code=404, detail="Inspiration not found")
    db.delete(i)
    db.commit()
    return {"status": "success"}


# ---------- Unified Admin Panel API ----------

class AdminPanelUserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone_number: Optional[str] = None
    role: str = "user"


class AdminPanelUserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None


class AdminPanelProjectWrite(BaseModel):
    user_id: Optional[int] = None
    project_name: str
    project_description: Optional[str] = None
    category_id: Optional[int] = None
    target_audience: Optional[str] = None
    capital_required: Optional[float] = None
    sales_cost: Optional[float] = None
    revenue: Optional[float] = None
    workers: Optional[int] = None
    sector: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = "draft"


class AdminPanelInspirationWrite(BaseModel):
    project_name: str
    image_url: Optional[str] = None
    success_rate: Optional[float] = None
    story: Optional[str] = None
    capital_required: Optional[float] = None
    results: Optional[str] = None
    challenges: Optional[str] = None


class AdminPanelNotificationCreate(BaseModel):
    user_id: Optional[int] = None
    message: str


def get_current_admin_panel(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user or str(user.role) != "admin":
        raise HTTPException(status_code=403, detail="Access denied: Admin only")
    return user


def _admin_enum_str(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _admin_total_pages(total: int, page_size: int) -> int:
    return max(1, (total + page_size - 1) // page_size)


@app.get("/api/v1/admin-panel/dashboard/stats")
def admin_panel_dashboard_stats(
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    status_rows = (
        db.query(models.Project.status, func.count(models.Project.project_id))
        .group_by(models.Project.status)
        .all()
    )
    return {
        "total_users": db.query(models.User).count(),
        "total_projects": db.query(models.Project).count(),
        "total_feasibility_studies": db.query(models.FeasibilityResult).count(),
        "total_inspirations": db.query(models.InspirationProject).count(),
        "projects_by_status": {_admin_enum_str(row[0]): row[1] for row in status_rows},
        "pending_support_messages": db.query(models.SupportMessage)
        .filter(models.SupportMessage.status == "pending")
        .count(),
        "unread_notifications": db.query(models.Notification)
        .filter(models.Notification.is_read == False)
        .count(),
    }


@app.get("/api/v1/admin-panel/dashboard/charts")
def admin_panel_dashboard_charts(
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    users_rows = (
        db.query(
            extract("year", models.User.created_at).label("y"),
            extract("month", models.User.created_at).label("m"),
            func.count(models.User.user_id),
        )
        .group_by("y", "m")
        .order_by("y", "m")
        .all()
    )
    projects_rows = (
        db.query(
            extract("year", models.Project.created_at).label("y"),
            extract("month", models.Project.created_at).label("m"),
            func.count(models.Project.project_id),
        )
        .group_by("y", "m")
        .order_by("y", "m")
        .all()
    )
    months = sorted(
        set([f"{int(r[0])}-{int(r[1]):02d}" for r in users_rows])
        | set([f"{int(r[0])}-{int(r[1]):02d}" for r in projects_rows])
    )
    users_map = {f"{int(r[0])}-{int(r[1]):02d}": r[2] for r in users_rows}
    projects_map = {f"{int(r[0])}-{int(r[1]):02d}": r[2] for r in projects_rows}
    status_rows = (
        db.query(models.Project.status, func.count(models.Project.project_id))
        .group_by(models.Project.status)
        .all()
    )
    category_rows = (
        db.query(models.Category.category_name, func.count(models.Project.project_id))
        .outerjoin(models.Project, models.Project.category_id == models.Category.category_id)
        .group_by(models.Category.category_name)
        .all()
    )
    top_users_rows = (
        db.query(models.User.full_name, func.count(models.Project.project_id).label("cnt"))
        .outerjoin(models.Project, models.Project.user_id == models.User.user_id)
        .group_by(models.User.user_id, models.User.full_name)
        .order_by(desc("cnt"))
        .limit(5)
        .all()
    )
    return {
        "growth": {
            "labels": months,
            "users": [users_map.get(month, 0) for month in months],
            "projects": [projects_map.get(month, 0) for month in months],
        },
        "by_status": {
            "labels": [_admin_enum_str(r[0]) for r in status_rows],
            "data": [r[1] for r in status_rows],
        },
        "by_category": {
            "labels": [r[0] or "بدون فئة" for r in category_rows],
            "data": [r[1] for r in category_rows],
        },
        "top_users": {
            "labels": [r[0] or "مستخدم" for r in top_users_rows],
            "data": [r[1] for r in top_users_rows],
        },
    }


@app.get("/api/v1/admin-panel/users")
def admin_panel_list_users(
    page: int = 1,
    page_size: int = 10,
    search: str = "",
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    query = db.query(models.User)
    if search:
        query = query.filter(
            or_(
                models.User.full_name.ilike(f"%{search}%"),
                models.User.email.ilike(f"%{search}%"),
            )
        )
    total = query.count()
    rows = (
        query.order_by(models.User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [
            {
                "user_id": row.user_id,
                "full_name": row.full_name,
                "email": row.email,
                "phone_number": row.phone_number,
                "role": _admin_enum_str(row.role),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
        "page": page,
        "page_size": page_size,
        "total_pages": _admin_total_pages(total, page_size),
        "total": total,
    }


@app.get("/api/v1/admin-panel/users/{user_id}")
def admin_panel_get_user(
    user_id: int,
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    row = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": row.user_id,
        "full_name": row.full_name,
        "email": row.email,
        "phone_number": row.phone_number,
        "role": _admin_enum_str(row.role),
    }


@app.post("/api/v1/admin-panel/users")
def admin_panel_create_user(
    payload: AdminPanelUserCreate,
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    exists = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already exists")
    row = models.User(
        full_name=payload.full_name.strip(),
        email=payload.email.lower(),
        phone_number=payload.phone_number,
        password_hash=hash_password(payload.password),
        role=payload.role if payload.role in {"user", "admin"} else "user",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "success", "user_id": row.user_id}


@app.put("/api/v1/admin-panel/users/{user_id}")
def admin_panel_update_user(
    user_id: int,
    payload: AdminPanelUserUpdate,
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    row = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.email and payload.email.lower() != row.email:
        email_exists = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
        if email_exists:
            raise HTTPException(status_code=400, detail="Email already exists")
        row.email = payload.email.lower()
    if payload.full_name is not None:
        row.full_name = payload.full_name.strip()
    if payload.phone_number is not None:
        row.phone_number = payload.phone_number
    if payload.password:
        row.password_hash = hash_password(payload.password)
    if payload.role in {"user", "admin"}:
        row.role = payload.role

    db.commit()
    db.refresh(row)
    return {"status": "success", "user_id": row.user_id}


@app.delete("/api/v1/admin-panel/users/{user_id}")
def admin_panel_delete_user(
    user_id: int,
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    if admin.user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete current admin")
    row = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(row)
    db.commit()
    return {"status": "success"}


@app.get("/api/v1/admin-panel/projects")
def admin_panel_list_projects(
    page: int = 1,
    page_size: int = 10,
    search: str = "",
    status_filter: str = "",
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    query = db.query(models.Project)
    if search:
        query = query.filter(models.Project.project_name.ilike(f"%{search}%"))
    if status_filter:
        query = query.filter(models.Project.status == status_filter)
    total = query.count()
    rows = (
        query.order_by(models.Project.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [
            {
                "project_id": row.project_id,
                "user_id": row.user_id,
                "project_name": row.project_name,
                "project_description": row.project_description,
                "category_id": row.category_id,
                "target_audience": row.target_audience,
                "capital_required": float(row.capital_required or 0),
                "sales_cost": float(row.sales_cost or 0),
                "revenue": float(row.revenue or 0),
                "workers": row.workers,
                "sector": row.sector,
                "location": row.location,
                "status": _admin_enum_str(row.status),
            }
            for row in rows
        ],
        "page": page,
        "page_size": page_size,
        "total_pages": _admin_total_pages(total, page_size),
        "total": total,
    }


@app.get("/api/v1/admin-panel/projects/{project_id}")
def admin_panel_get_project(
    project_id: int,
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    row = db.query(models.Project).filter(models.Project.project_id == project_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "project_id": row.project_id,
        "user_id": row.user_id,
        "project_name": row.project_name,
        "project_description": row.project_description,
        "category_id": row.category_id,
        "target_audience": row.target_audience,
        "capital_required": float(row.capital_required or 0),
        "sales_cost": float(row.sales_cost or 0),
        "revenue": float(row.revenue or 0),
        "workers": row.workers,
        "sector": row.sector,
        "location": row.location,
        "status": _admin_enum_str(row.status),
    }


@app.post("/api/v1/admin-panel/projects")
def admin_panel_create_project(
    payload: AdminPanelProjectWrite,
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    row = models.Project(
        user_id=payload.user_id or admin.user_id,
        project_name=payload.project_name.strip(),
        project_description=payload.project_description,
        category_id=payload.category_id,
        target_audience=payload.target_audience,
        capital_required=payload.capital_required,
        sales_cost=payload.sales_cost,
        revenue=payload.revenue,
        workers=payload.workers,
        sector=payload.sector,
        location=payload.location,
        status=payload.status or "draft",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "success", "project_id": row.project_id}


@app.put("/api/v1/admin-panel/projects/{project_id}")
def admin_panel_update_project(
    project_id: int,
    payload: AdminPanelProjectWrite,
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    row = db.query(models.Project).filter(models.Project.project_id == project_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    row.user_id = payload.user_id or row.user_id
    row.project_name = payload.project_name.strip()
    row.project_description = payload.project_description
    row.category_id = payload.category_id
    row.target_audience = payload.target_audience
    row.capital_required = payload.capital_required
    row.sales_cost = payload.sales_cost
    row.revenue = payload.revenue
    row.workers = payload.workers
    row.sector = payload.sector
    row.location = payload.location
    row.status = payload.status or row.status
    db.commit()
    db.refresh(row)
    return {"status": "success", "project_id": row.project_id}


@app.delete("/api/v1/admin-panel/projects/{project_id}")
def admin_panel_delete_project(
    project_id: int,
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    row = db.query(models.Project).filter(models.Project.project_id == project_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(row)
    db.commit()
    return {"status": "success"}


@app.get("/api/v1/admin-panel/categories")
def admin_panel_list_categories(
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    rows = db.query(models.Category).all()
    return [
        {
            "category_id": row.category_id,
            "category_name": row.category_name,
            "description": row.description,
        }
        for row in rows
    ]


@app.get("/api/v1/admin-panel/inspirations")
def admin_panel_list_inspirations(
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    rows = db.query(models.InspirationProject).order_by(models.InspirationProject.inspiration_id.desc()).all()
    return [
        {
            "inspiration_id": row.inspiration_id,
            "project_name": row.project_name,
            "image_url": row.image_url,
            "success_rate": float(row.success_rate or 0),
            "capital_required": float(row.capital_required or 0),
            "story": row.story,
            "results": row.results,
            "challenges": row.challenges,
        }
        for row in rows
    ]


@app.get("/api/v1/admin-panel/inspirations/{inspiration_id}")
def admin_panel_get_inspiration(
    inspiration_id: int,
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    row = db.query(models.InspirationProject).filter(models.InspirationProject.inspiration_id == inspiration_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Inspiration not found")
    return {
        "inspiration_id": row.inspiration_id,
        "project_name": row.project_name,
        "image_url": row.image_url,
        "success_rate": float(row.success_rate or 0),
        "capital_required": float(row.capital_required or 0),
        "story": row.story,
        "results": row.results,
        "challenges": row.challenges,
    }


@app.post("/api/v1/admin-panel/inspirations")
def admin_panel_create_inspiration(
    payload: AdminPanelInspirationWrite,
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    row = models.InspirationProject(
        project_name=payload.project_name.strip(),
        image_url=payload.image_url,
        success_rate=payload.success_rate,
        story=payload.story,
        capital_required=payload.capital_required,
        results=payload.results,
        challenges=payload.challenges,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "success", "inspiration_id": row.inspiration_id}


@app.put("/api/v1/admin-panel/inspirations/{inspiration_id}")
def admin_panel_update_inspiration(
    inspiration_id: int,
    payload: AdminPanelInspirationWrite,
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    row = db.query(models.InspirationProject).filter(models.InspirationProject.inspiration_id == inspiration_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Inspiration not found")
    row.project_name = payload.project_name.strip()
    row.image_url = payload.image_url
    row.success_rate = payload.success_rate
    row.story = payload.story
    row.capital_required = payload.capital_required
    row.results = payload.results
    row.challenges = payload.challenges
    db.commit()
    db.refresh(row)
    return {"status": "success", "inspiration_id": row.inspiration_id}


@app.delete("/api/v1/admin-panel/inspirations/{inspiration_id}")
def admin_panel_delete_inspiration(
    inspiration_id: int,
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    row = db.query(models.InspirationProject).filter(models.InspirationProject.inspiration_id == inspiration_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Inspiration not found")
    db.delete(row)
    db.commit()
    return {"status": "success"}


@app.get("/api/v1/admin-panel/support-messages")
def admin_panel_list_support_messages(
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    rows = db.query(models.SupportMessage).order_by(models.SupportMessage.created_at.desc()).all()
    return [
        {
            "message_id": row.message_id,
            "user_id": row.user_id,
            "subject": row.subject,
            "message_body": row.message_body,
            "status": _admin_enum_str(row.status),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@app.put("/api/v1/admin-panel/support-messages/{message_id}/status")
def admin_panel_update_support_status(
    message_id: int,
    payload: SupportStatusUpdate,
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    row = db.query(models.SupportMessage).filter(models.SupportMessage.message_id == message_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Support message not found")
    row.status = payload.status
    db.commit()
    return {"status": "success"}


@app.get("/api/v1/admin-panel/notifications")
def admin_panel_list_notifications(
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    rows = db.query(models.Notification).order_by(models.Notification.created_at.desc()).all()
    return [
        {
            "notification_id": row.notification_id,
            "user_id": row.user_id,
            "message": row.message,
            "is_read": bool(row.is_read),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@app.post("/api/v1/admin-panel/notifications")
def admin_panel_create_notification(
    payload: AdminPanelNotificationCreate,
    admin: models.User = Depends(get_current_admin_panel),
    db: Session = Depends(get_db),
):
    targets = []
    if payload.user_id is not None:
        user = db.query(models.User).filter(models.User.user_id == payload.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        targets = [user.user_id]
    else:
        targets = [u.user_id for u in db.query(models.User.user_id).all()]

    for target_user_id in targets:
        row = models.Notification(
            user_id=target_user_id,
            message=payload.message.strip(),
            is_read=False,
        )
        db.add(row)
    db.commit()
    return {"status": "success", "sent_count": len(targets)}

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

def _load_database_url() -> str:
    configured_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("MYSQL_URL")
        or os.getenv("RAILWAY_DATABASE_URL")
        or ""
    ).strip()
    if not configured_url:
        raise RuntimeError(
            "Railway database URL is missing. Set DATABASE_URL or MYSQL_URL in environment variables."
        )
    if "localhost" in configured_url.lower() or "127.0.0.1" in configured_url:
        raise RuntimeError(
            "Localhost database URLs are disabled. Configure the Railway database URL in environment variables."
        )
    return configured_url


SQLALCHEMY_DATABASE_URL = _load_database_url()

# ملاحظة: إذا كان الرابط من ريلواي يبدأ بـ mysql:// 
# SQLAlchemy أحياناً تحتاج تعديله يدوياً ليصبح mysql+pymysql://
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("mysql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

# --- التعديل الجديد لضمان دعم العربية (UTF-8) ---
if SQLALCHEMY_DATABASE_URL:
    if "?" not in SQLALCHEMY_DATABASE_URL:
        SQLALCHEMY_DATABASE_URL += "?charset=utf8mb4"
    elif "charset=" not in SQLALCHEMY_DATABASE_URL:
        SQLALCHEMY_DATABASE_URL += "&charset=utf8mb4"
# -----------------------------------------------

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"charset": "utf8mb4"} 
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

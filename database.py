import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# التعديل هنا: غيرنا DATABASE_URL إلى MYSQL_URL لتطابق Railway
SQLALCHEMY_DATABASE_URL = os.getenv(
    "MYSQL_URL", 
    "mysql+pymysql://root:@localhost:3306/step_app_db"
)

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
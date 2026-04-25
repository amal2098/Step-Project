import models
from database import SessionLocal
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def update_admin_password():
    db = SessionLocal()
    try:
        admin = db.query(models.User).filter(models.User.email == "am@example.com").first()
        if admin:
            admin.password_hash = pwd_context.hash("admin123")
            db.commit()
            print("Password for am@example.com has been updated to: admin123")
        else:
            print("Admin not found.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_admin_password()

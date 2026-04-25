import models
from database import SessionLocal, engine
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def check_and_create_admin():
    db = SessionLocal()
    try:
        admin = db.query(models.User).filter(models.User.role == "admin").first()
        if admin:
            print(f"Found existing admin: {admin.email}")
        else:
            print("No admin found. Creating a new one...")
            new_admin = models.User(
                full_name="System Admin",
                email="admin@khotwa.com",
                password_hash=hash_password("admin123"),
                role="admin"
            )
            db.add(new_admin)
            db.commit()
            print("Admin created successfully! Email: admin@khotwa.com, Pass: admin123")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_and_create_admin()

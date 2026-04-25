import models
from database import SessionLocal
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_fresh_admin():
    db = SessionLocal()
    try:
        # Delete if exists to be sure
        existing = db.query(models.User).filter(models.User.email == "admin@step.com").first()
        if existing:
            db.delete(existing)
            db.commit()
            
        new_admin = models.User(
            full_name="Administrator",
            email="admin@step.com",
            password_hash=pwd_context.hash("password123"),
            role="admin"
        )
        db.add(new_admin)
        db.commit()
        print("Fresh Admin Created: admin@step.com / password123")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_fresh_admin()

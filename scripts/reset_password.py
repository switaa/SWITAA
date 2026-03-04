import sys
sys.path.insert(0, "/app")
import bcrypt
from app.core.database import SessionLocal
from app.models.user import User

db = SessionLocal()
user = db.query(User).filter(User.email == "contact@switaa.com").first()
if user:
    new_hash = bcrypt.hashpw(b"Marcus2024!", bcrypt.gensalt()).decode()
    user.hashed_password = new_hash
    db.commit()
    print(f"Password reset for {user.email}")
else:
    print("User not found")
db.close()

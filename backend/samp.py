from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Replace with your actual credentials
DB_USER = "admin"
DB_PASS = "Dhoni07!"
DB_HOST = "abtesting-db.ctek0o062v8b.ap-south-1.rds.amazonaws.com"
DB_PORT = "3306"
DB_NAME = "abtesting"

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
try:
    db = SessionLocal()
    print("✅ Connected to RDS successfully!")
    db.close()
except Exception as e:
    print("❌ Failed to connect:", e)
Base = declarative_base()

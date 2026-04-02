"""
Seed script to populate initial data for testing.
"""
import sys
import os
from datetime import datetime, timedelta, date, timezone
from decimal import Decimal
import random

# Add project root to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal, Base, engine
from app.models.user import User, UserRole
from app.models.record import FinancialRecord, RecordType
from app.core.security import hash_password

def seed_database():
    print("Creating tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("Checking if admin exists...")
    admin = db.query(User).filter(User.email == "admin@finance.dev").first()
    if not admin:
        print("Creating admin user...")
        admin = User(
            name="Admin User",
            email="admin@finance.dev",
            password_hash=hash_password("Admin@123"),
            role=UserRole.ADMIN
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    else:
        print("Admin user already exists.")

    print("Checking if analyst exists...")
    analyst = db.query(User).filter(User.email == "analyst@finance.dev").first()
    if not analyst:
        print("Creating analyst user...")
        analyst = User(
            name="Analyst User",
            email="analyst@finance.dev",
            password_hash=hash_password("Analyst@123"),
            role=UserRole.ANALYST
        )
        db.add(analyst)
        db.commit()
    
    print("Checking if viewer exists...")
    viewer = db.query(User).filter(User.email == "viewer@finance.dev").first()
    if not viewer:
        print("Creating viewer user...")
        viewer = User(
            name="Viewer User",
            email="viewer@finance.dev",
            password_hash=hash_password("Viewer@123"),
            role=UserRole.VIEWER
        )
        db.add(viewer)
        db.commit()

    print("Checking records...")
    record_count = db.query(FinancialRecord).count()
    if record_count < 50:
        print("Seeding records...")
        categories_income = ["Salary", "Consulting", "Investment", "Bonus"]
        categories_expense = ["Rent", "Travel", "Utilities", "Food", "Marketing", "Insurance", "Software"]
        
        records_to_add = []
        for i in range(50 - record_count):
            is_income = random.random() > 0.6
            rec_type = RecordType.INCOME if is_income else RecordType.EXPENSE
            cat = random.choice(categories_income) if is_income else random.choice(categories_expense)
            amt = round(random.uniform(50.0, 5000.0), 2)
            # random date within last 180 days
            days_ago = random.randint(0, 180)
            rec_date = date.today() - timedelta(days=days_ago)
            
            record = FinancialRecord(
                amount=Decimal(str(amt)),
                type=rec_type,
                category=cat,
                date=rec_date,
                notes=f"Sample {cat} record",
                created_by=admin.id
            )
            records_to_add.append(record)
        
        db.add_all(records_to_add)
        db.commit()
        print(f"Added {50 - record_count} records.")
    else:
        print("Records already populated.")

    db.close()
    print("Seed complete.")
    print("\nCredentials:")
    print("Admin: admin@finance.dev / Admin@123")
    print("Analyst: analyst@finance.dev / Analyst@123")
    print("Viewer: viewer@finance.dev / Viewer@123")

if __name__ == "__main__":
    seed_database()

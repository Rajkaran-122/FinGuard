"""
Database Seed Script
====================
Populates the database with initial users and realistic financial records.
Generates 180+ days of historical data for analytics demonstration.
"""

import asyncio
import random
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

from app.core.database import AsyncSessionLocal, engine, Base
from app.models.user import User, UserRole, UserStatus
from app.models.record import FinancialRecord, TransactionType, Category
from app.core.security import security_manager


async def seed_data():
    """Main seeding logic."""
    print("info: starting_seed")
    
    # Optional: Clear tables first (Development only!)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)
    #     await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # 1. Create Users
        users_to_create = [
            {
                "email": "admin@finguard.com",
                "first_name": "System",
                "last_name": "Administrator",
                "password": "Admin@123",
                "role": UserRole.ADMIN,
            },
            {
                "email": "analyst@finguard.com",
                "first_name": "Financial",
                "last_name": "Analyst",
                "password": "Analyst@123",
                "role": UserRole.ANALYST,
            },
            {
                "email": "viewer@finguard.com",
                "first_name": "Casual",
                "last_name": "Viewer",
                "password": "Viewer@123",
                "role": UserRole.VIEWER,
            }
        ]

        created_users = []
        for u_data in users_to_create:
            # Check if exists
            import sqlalchemy as sa
            res = await db.execute(sa.select(User).where(User.email == u_data["email"]))
            if res.scalar_one_or_none():
                print(f"info: skip_existing_user email={u_data['email']}")
                continue

            password = u_data.pop("password")
            user = User(**u_data, hashed_password=security_manager.get_password_hash(password))
            db.add(user)
            created_users.append(user)
        
        await db.commit()
        for u in created_users: await db.refresh(u)

        # 2. Generate Records for Analyst
        analyst = next((u for u in created_users if u.role == UserRole.ANALYST), None)
        if not analyst:
            # Try to fetch existing if skipped
            res = await db.execute(sa.select(User).where(User.role == UserRole.ANALYST))
            analyst = res.scalar_one_or_none()

        if analyst:
            print(f"info: seeding_records user_id={analyst.id}")
            
            categories_income = [Category.SALARY, Category.BUSINESS, Category.INVESTMENT]
            categories_expense = [
                Category.FOOD, Category.TRANSPORT, Category.UTILITIES,
                Category.ENTERTAINMENT, Category.HEALTHCARE, Category.SHOPPING
            ]
            
            records = []
            now = datetime.now()
            
            # Seed 6 months of data
            for i in range(180):
                current_date = (now - timedelta(days=i)).date()
                
                # Randomized transactions per day
                num_tx = random.choices([0, 1, 2, 3], weights=[40, 40, 15, 5])[0]
                
                for _ in range(num_tx):
                    is_income = random.random() < 0.25 # 25% chance of income
                    
                    if is_income:
                        type = TransactionType.INCOME
                        cat = random.choice(categories_income)
                        amount = Decimal(random.randint(2000, 8000))
                        desc = f"Revenue from {cat.value}"
                    else:
                        type = TransactionType.EXPENSE
                        cat = random.choice(categories_expense)
                        amount = Decimal(random.randint(5, 500))
                        desc = f"Payment for {cat.value}"

                    records.append(FinancialRecord(
                        user_id=analyst.id,
                        amount=amount,
                        type=type,
                        category=cat,
                        date=current_date,
                        description=desc
                    ))

            db.add_all(records)
            await db.commit()
            print(f"info: seed_complete total_records={len(records)}")


if __name__ == "__main__":
    asyncio.run(seed_data())
    print("\n" + "="*30)
    print("Credentials:")
    print("Admin: admin@finguard.com / Admin@123")
    print("Analyst: analyst@finguard.com / Analyst@123")
    print("Viewer: viewer@finguard.com / Viewer@123")
    print("="*30)

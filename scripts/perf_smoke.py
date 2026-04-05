"""
Performance smoke test for dashboard summary aggregations.

Usage:
  python scripts/perf_smoke.py --rows 100000 --target-ms 150
"""

import argparse
import os
import random
import sys
import time
from datetime import date, timedelta
from decimal import Decimal

import alembic.command
import alembic.config

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.record import FinancialRecord, RecordType
from app.models.user import User
from app.repositories import record_repository
from app.services.summary_service import get_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run summary aggregation perf smoke test.")
    parser.add_argument("--rows", type=int, default=100000, help="Total records target for test user.")
    parser.add_argument("--batch-size", type=int, default=2000, help="Insert batch size.")
    parser.add_argument("--target-ms", type=float, default=150.0, help="Warm summary response target in ms.")
    return parser.parse_args()


def ensure_schema():
    cfg = alembic.config.Config("alembic.ini")
    alembic.command.upgrade(cfg, "head")


def get_admin(db):
    admin = db.query(User).filter(User.email == "admin@finance.dev").first()
    if not admin:
        raise RuntimeError("Admin user not found. Run: python scripts/seed.py")
    return admin


def seed_records(db, admin: User, target_rows: int, batch_size: int):
    current_count = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.created_by == admin.id, FinancialRecord.deleted_at.is_(None))
        .count()
    )
    to_create = max(0, target_rows - current_count)
    if to_create == 0:
        print(f"Dataset already >= {target_rows} rows ({current_count} rows).")
        return

    print(f"Seeding {to_create} rows (current={current_count}, target={target_rows})...")
    categories_income = ["Salary", "Consulting", "Investment", "Bonus"]
    categories_expense = ["Rent", "Travel", "Utilities", "Food", "Marketing", "Insurance", "Software"]

    created = 0
    while created < to_create:
        chunk = min(batch_size, to_create - created)
        rows = []
        for _ in range(chunk):
            is_income = random.random() > 0.6
            rec_type = RecordType.INCOME if is_income else RecordType.EXPENSE
            category = random.choice(categories_income if is_income else categories_expense)
            amount = Decimal(str(round(random.uniform(10.0, 9000.0), 2)))
            rec_date = date.today() - timedelta(days=random.randint(0, 365))
            rows.append(
                FinancialRecord(
                    amount=amount,
                    type=rec_type,
                    category=category,
                    date=rec_date,
                    notes="perf-smoke",
                    created_by=admin.id,
                )
            )
        db.bulk_save_objects(rows)
        db.commit()
        created += chunk
        print(f"Inserted {created}/{to_create}")


def run_summary_benchmark(db, admin: User):
    # Cold query via repository
    start_cold = time.perf_counter()
    cold_summary = record_repository.get_summary_totals(db, user_id=admin.id)
    cold_ms = (time.perf_counter() - start_cold) * 1000

    # Warm query via cache-aside path
    start_warm_1 = time.perf_counter()
    get_summary(db, admin)
    warm_1_ms = (time.perf_counter() - start_warm_1) * 1000

    start_warm_2 = time.perf_counter()
    get_summary(db, admin)
    warm_2_ms = (time.perf_counter() - start_warm_2) * 1000

    return cold_summary, cold_ms, warm_1_ms, warm_2_ms


def main():
    args = parse_args()
    ensure_schema()

    db = SessionLocal()
    try:
        admin = get_admin(db)
        seed_records(db, admin, args.rows, args.batch_size)
        summary, cold_ms, warm_1_ms, warm_2_ms = run_summary_benchmark(db, admin)

        print("\nSummary metrics:")
        print(f"  total_income:   {summary['total_income']}")
        print(f"  total_expenses: {summary['total_expenses']}")
        print(f"  record_count:   {summary['record_count']}")
        print("\nLatency:")
        print(f"  cold_db_ms:     {cold_ms:.2f}")
        print(f"  warm_cache_1ms: {warm_1_ms:.2f}")
        print(f"  warm_cache_2ms: {warm_2_ms:.2f}")

        if warm_2_ms > args.target_ms:
            print(
                f"\nFAIL: warm cached summary ({warm_2_ms:.2f}ms) exceeded target ({args.target_ms:.2f}ms)."
            )
            raise SystemExit(1)

        print(
            f"\nPASS: warm cached summary ({warm_2_ms:.2f}ms) is within target ({args.target_ms:.2f}ms)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()

"""
Migration Script: Add ai_restrictions column to tenants table.
Separates company description from AI restrictions.

Run: python scripts/add_ai_restrictions_column.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.database import engine, SessionLocal


def migrate():
    """Add ai_restrictions column and migrate existing data."""
    db = SessionLocal()
    try:
        # Step 1: Add column if it doesn't exist
        try:
            db.execute(text("ALTER TABLE tenants ADD COLUMN ai_restrictions TEXT"))
            db.commit()
            print("✅ Column 'ai_restrictions' added to tenants table.")
        except Exception as e:
            db.rollback()
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("ℹ️  Column 'ai_restrictions' already exists — skipping.")
            else:
                print(f"⚠️  ALTER TABLE error (may already exist): {e}")

        # Step 2: Copy existing description → ai_restrictions
        # (current description data IS restrictions, not company descriptions)
        result = db.execute(text(
            "UPDATE tenants SET ai_restrictions = description "
            "WHERE description IS NOT NULL AND description != '' "
            "AND (ai_restrictions IS NULL OR ai_restrictions = '')"
        ))
        db.commit()
        rows = result.rowcount
        print(f"✅ Copied description → ai_restrictions for {rows} tenant(s).")

        # Step 3: Clear description so users can re-enter actual company info
        result = db.execute(text(
            "UPDATE tenants SET description = NULL "
            "WHERE ai_restrictions IS NOT NULL AND ai_restrictions != ''"
        ))
        db.commit()
        rows = result.rowcount
        print(f"✅ Cleared description for {rows} tenant(s) (enter real company info in Settings).")

        print("\n🎉 Migration complete!")

    finally:
        db.close()


if __name__ == "__main__":
    migrate()

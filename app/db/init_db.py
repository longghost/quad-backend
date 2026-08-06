"""Runs schema.sql against the database configured in DATABASE_URL.
Usage: python -m app.db.init_db
"""
import os

import psycopg2

from app.config import settings

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def main():
    with open(SCHEMA_PATH) as f:
        schema_sql = f.read()

    conn = psycopg2.connect(settings.database_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        print("Schema applied successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

import sqlite3
from sqlalchemy import create_engine, text

# =====================================================
# CONFIGURATION
# =====================================================

SQLITE_DB = "database/betpro.db"

POSTGRES_URL = (
    "postgresql://neondb_owner:npg_AQJN9OjYGvk5@"
    "ep-broad-sound-avehq59s-pooler.c-11.us-east-1.aws.neon.tech/"
    "neondb?sslmode=require&channel_binding=require"
)

TABLE_ORDER = [
    "roles",
    "users",
    "sports",
    "leagues",
    "matches",
    "odds",
    "system_settings",
    "user_roles",
    "wallets",
    "wallet_transactions",
    "deposits",
    "withdrawals",
    "bets",
    "bet_selections",
    "bonuses",
    "notifications",
    "announcements",
    "audit_logs",
    "admin_logs",
]

SKIP_TABLES = {
    "sqlite_sequence",
    "alembic_version",
}

# =====================================================
# CONNECT
# =====================================================

sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_conn.row_factory = sqlite3.Row

pg_engine = create_engine(
    POSTGRES_URL,
    pool_pre_ping=True,
)

# =====================================================
# EXISTING SQLITE TABLES
# =====================================================

sqlite_tables = {
    row["name"]
    for row in sqlite_conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        """
    ).fetchall()
}

success = []
failed = []

# =====================================================
# IMPORT TABLES
# =====================================================

for table_name in TABLE_ORDER:

    if table_name in SKIP_TABLES:
        continue

    if table_name not in sqlite_tables:
        print(f"\nSkipping {table_name} (not found)")
        continue

    print(f"\nCopying {table_name}...")

    rows = sqlite_conn.execute(
        f"SELECT * FROM {table_name}"
    ).fetchall()

    if len(rows) == 0:
        print("  -> empty")
        success.append(table_name)
        continue

    columns = list(rows[0].keys())

    column_string = ", ".join(columns)
    placeholder_string = ", ".join(f":{c}" for c in columns)

    stmt = text(f"""
        INSERT INTO {table_name}
        ({column_string})
        VALUES
        ({placeholder_string})
        ON CONFLICT DO NOTHING
    """)

    try:

        with pg_engine.begin() as pg_conn:

            # Automatically discover BOOLEAN columns
            bool_columns = {
                row[0]
                for row in pg_conn.execute(
                    text("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name=:table
                        AND data_type='boolean'
                    """),
                    {"table": table_name},
                )
            }

            inserted = 0

            for row in rows:

                data = dict(row)

                # Convert SQLite integers to PostgreSQL booleans
                for col in bool_columns:
                    if col in data and data[col] is not None:
                        data[col] = bool(data[col])

                try:
                    pg_conn.execute(stmt, data)
                    inserted += 1

                except Exception as row_error:
                    print(
                        f"   Skipped row {data.get('id','?')} : "
                        f"{row_error.__class__.__name__}"
                    )

            print(f"✓ {table_name} copied ({inserted} rows)")
            success.append(table_name)

    except Exception as e:

        print(f"✗ Failed {table_name}")
        print(e)
        failed.append(table_name)

# =====================================================
# RESET SEQUENCES
# =====================================================

print("\nResetting PostgreSQL sequences...")

with pg_engine.begin() as pg_conn:

    for table in success:

        try:

            pg_conn.execute(
                text(f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table}','id'),
                        COALESCE((SELECT MAX(id) FROM {table}),1),
                        true
                    );
                """)
            )

        except Exception:
            pass

# =====================================================
# SUMMARY
# =====================================================

print("\n===================================")
print("Migration Complete")
print("===================================")

print(f"Successful tables : {len(success)}")
print(f"Failed tables     : {len(failed)}")

if success:
    print("\nCopied tables:")
    for table in success:
        print(f"  ✓ {table}")

if failed:
    print("\nFailed tables:")
    for table in failed:
        print(f"  ✗ {table}")

sqlite_conn.close()

print("\nDone.")
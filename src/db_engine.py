"""
Database engine module for SQLite connection and schema introspection.
"""

import os
import sqlite3
import time
from typing import Dict, Any, List, Optional
import pandas as pd
from src.security import sanitize_sql, validate_query, enforce_row_limit, SecurityViolationError

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "enterprise_data.db"
)


class DatabaseEngine:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}. Please run seed_database.py first.")

    def get_connection(self) -> sqlite3.Connection:
        """Returns a connection to the SQLite database with read-only URI when possible."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_schema_info(self) -> Dict[str, Any]:
        """
        Introspects the database to retrieve table names, column names,
        types, primary keys, foreign keys, and row counts.
        """
        schema = {}
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                # Column info
                cursor.execute(f"PRAGMA table_info({table});")
                columns = []
                for col in cursor.fetchall():
                    columns.append({
                        "cid": col[0],
                        "name": col[1],
                        "type": col[2],
                        "notnull": bool(col[3]),
                        "default_value": col[4],
                        "primary_key": bool(col[5])
                    })

                # Foreign keys
                cursor.execute(f"PRAGMA foreign_key_list({table});")
                foreign_keys = []
                for fk in cursor.fetchall():
                    foreign_keys.append({
                        "from_col": fk[3],
                        "to_table": fk[2],
                        "to_col": fk[4]
                    })

                # Row count
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                row_count = cursor.fetchone()[0]

                # Sample 2 rows (anonymized/safe preview)
                cursor.execute(f"SELECT * FROM {table} LIMIT 2;")
                sample_rows = [dict(row) for row in cursor.fetchall()]

                schema[table] = {
                    "columns": columns,
                    "foreign_keys": foreign_keys,
                    "row_count": row_count,
                    "sample_rows": sample_rows
                }

        return schema

    def get_schema_prompt_context(self) -> str:
        """
        Formats the database schema into a compact, highly readable context string
        specifically tailored for LLM prompt injection.
        """
        schema = self.get_schema_info()
        lines = ["### Database Schema (SQLite):", ""]

        for table, details in schema.items():
            lines.append(f"Table: `{table}` ({details['row_count']} total records)")
            lines.append("Columns:")
            for col in details["columns"]:
                pk_flag = " [PRIMARY KEY]" if col["primary_key"] else ""
                lines.append(f"  - `{col['name']}` ({col['type']}){pk_flag}")

            if details["foreign_keys"]:
                lines.append("Relationships / Foreign Keys:")
                for fk in details["foreign_keys"]:
                    lines.append(f"  - `{table}.{fk['from_col']}` -> `{fk['to_table']}.{fk['to_col']}`")

            lines.append("")

        return "\n".join(lines)

    def execute_query(self, sql_query: str) -> Dict[str, Any]:
        """
        Executes an SQL query with security validation, timing, and DataFrame conversion.
        Returns a dictionary with status, results DataFrame, row count, execution time, and raw query.
        """
        # Validate security
        is_valid, error_msg = validate_query(sql_query)
        if not is_valid:
            raise SecurityViolationError(error_msg)

        # Enforce safe row limit
        safe_sql = enforce_row_limit(sql_query)

        start_time = time.perf_counter()
        with self.get_connection() as conn:
            try:
                df = pd.read_sql_query(safe_sql, conn)
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return {
                    "success": True,
                    "dataframe": df,
                    "row_count": len(df),
                    "execution_time_ms": duration_ms,
                    "executed_sql": safe_sql,
                    "error": None
                }
            except Exception as e:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return {
                    "success": False,
                    "dataframe": pd.DataFrame(),
                    "row_count": 0,
                    "execution_time_ms": duration_ms,
                    "executed_sql": safe_sql,
                    "error": str(e)
                }

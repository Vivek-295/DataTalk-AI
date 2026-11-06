"""
Security guardrails to enforce read-only queries and prevent SQL injection.
"""

import re
from typing import Tuple, Optional


DISALLOWED_COMMANDS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bUPDATE\b",
    r"\bINSERT\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bREPLACE\b",
    r"\bCREATE\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"\bVACUUM\b",
    r"\bREINDEX\b",
    r"\bPRAGMA\s+(?!table_info|table_list)",
    r"\bEXEC(UTE)?\b",
    r"\bGRANT\b",
    r"\bREVOKE\b"
]

MAX_DEFAULT_LIMIT = 200


class SecurityViolationError(Exception):
    """Raised when an SQL query violates security guardrails."""
    pass


def sanitize_sql(sql_query: str) -> str:
    """
    Cleans raw markdown formatting, backticks, or trailing semicolons from LLM output.
    """
    cleaned = sql_query.strip()
    # Strip markdown code blocks
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:sql|sqlite)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    
    cleaned = cleaned.strip()
    # Remove terminal semicolon for consistent processing
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    
    return cleaned


def validate_query(sql_query: str) -> Tuple[bool, Optional[str]]:
    """
    Validates whether an SQL query is strictly a read-only SELECT statement.
    Returns (is_valid, error_message).
    """
    cleaned = sanitize_sql(sql_query)
    
    if not cleaned:
        return False, "Query is empty."

    # Prevent multiple chained queries (prevent SQL injection via ';')
    statements = [stmt.strip() for stmt in cleaned.split(";") if stmt.strip()]
    if len(statements) > 1:
        return False, "Multiple SQL statements detected. Only a single SELECT query is permitted."

    single_query = statements[0]

    # Must start with SELECT or WITH (for CTE queries)
    if not re.match(r"^\s*(SELECT|WITH)\b", single_query, re.IGNORECASE):
        return False, "Permission Denied: Only SELECT (read-only) queries are authorized."

    # Check for disallowed mutation keywords
    for pattern in DISALLOWED_COMMANDS:
        if re.search(pattern, single_query, re.IGNORECASE):
            match = re.search(pattern, single_query, re.IGNORECASE).group()
            return False, f"Security Violation: Destructive operation '{match.upper()}' is strictly prohibited."

    return True, None


def enforce_row_limit(sql_query: str, max_limit: int = MAX_DEFAULT_LIMIT) -> str:
    """
    Appends or caps LIMIT to prevent unbounded memory consumption.
    """
    cleaned = sanitize_sql(sql_query)
    
    # Check if LIMIT exists
    limit_match = re.search(r"\bLIMIT\s+(\d+)", cleaned, re.IGNORECASE)
    if limit_match:
        current_limit = int(limit_match.group(1))
        if current_limit > max_limit:
            # Cap it
            cleaned = re.sub(r"\bLIMIT\s+\d+", f"LIMIT {max_limit}", cleaned, flags=re.IGNORECASE)
    else:
        # Append limit
        cleaned = f"{cleaned}\nLIMIT {max_limit}"

    return cleaned + ";"

"""
Unit and Integration Tests for NL2SQL Agent.
"""

import os
import pytest
import pandas as pd
from src.db_engine import DatabaseEngine
from src.security import validate_query, enforce_row_limit, sanitize_sql, SecurityViolationError
from src.semantic_layer import SemanticLayer
from src.few_shot import FewShotManager
from src.visualizer import create_auto_chart
from src.agent import NL2SQLAgent


def test_database_connection_and_schema():
    engine = DatabaseEngine()
    schema = engine.get_schema_info()
    assert "customers" in schema
    assert "orders" in schema
    assert "products" in schema
    assert schema["customers"]["row_count"] > 0
    assert schema["orders"]["row_count"] > 0

    prompt_context = engine.get_schema_prompt_context()
    assert "Table: `customers`" in prompt_context
    assert "Relationships / Foreign Keys:" in prompt_context


def test_security_validation():
    # Valid SELECT query
    valid, err = validate_query("SELECT * FROM customers LIMIT 10;")
    assert valid is True
    assert err is None

    # Valid query with CTE
    valid, err = validate_query("WITH top_cust AS (SELECT customer_id FROM orders) SELECT * FROM top_cust;")
    assert valid is True

    # Blocked DROP TABLE
    valid, err = validate_query("DROP TABLE customers;")
    assert valid is False
    assert "Only SELECT" in err or "DROP" in err

    # Blocked DELETE
    valid, err = validate_query("DELETE FROM orders WHERE order_id = 5;")
    assert valid is False
    assert "Only SELECT" in err or "DELETE" in err

    # Blocked UPDATE
    valid, err = validate_query("UPDATE products SET unit_price = 0;")
    assert valid is False
    assert "Only SELECT" in err or "UPDATE" in err

    # Blocked multiple statements (SQL injection chain)
    valid, err = validate_query("SELECT * FROM products; DROP TABLE customers;")
    assert valid is False


def test_row_limit_enforcement():
    sql = "SELECT * FROM orders"
    limited = enforce_row_limit(sql, max_limit=50)
    assert "LIMIT 50" in limited

    sql_with_large_limit = "SELECT * FROM orders LIMIT 5000"
    capped = enforce_row_limit(sql_with_large_limit, max_limit=100)
    assert "LIMIT 100" in capped


def test_semantic_layer():
    sem = SemanticLayer()
    assert "total_revenue" in sem.metrics
    assert "customers" in sem.entities
    context = sem.get_prompt_context()
    assert "Total Gross Revenue" in context
    assert "Recommended Join Paths" in context


def test_few_shot_manager():
    mgr = FewShotManager()
    assert len(mgr.examples) >= 4
    context = mgr.get_prompt_context(limit=3)
    assert "Example 1:" in context
    assert "Verified SQLite Query:" in context


def test_visualization_engine():
    # Test categorical + numeric
    df = pd.DataFrame({
        "category": ["Cloud Infra", "Dev Tools", "Security"],
        "revenue": [15000.0, 8500.0, 12000.0]
    })
    fig = create_auto_chart(df, title="Category Revenue")
    assert fig is not None

    # Test time series + numeric
    df_ts = pd.DataFrame({
        "order_month": ["2024-01", "2024-02", "2024-03"],
        "monthly_revenue": [5200.0, 6800.0, 7400.0]
    })
    fig_ts = create_auto_chart(df_ts, title="Monthly Trend")
    assert fig_ts is not None


def test_nl2sql_agent_offline_mode():
    agent = NL2SQLAgent(api_key=None)
    assert not agent.is_configured()

    res = agent.process_query("What are our top products by revenue?")
    assert res["success"] is True
    assert res["row_count"] > 0
    assert not res["dataframe"].empty
    assert "Predictive AI" in res["natural_answer"] or "revenue" in res["natural_answer"].lower()
    assert res["figure"] is not None
    assert res["mode"] == "offline_demo"


def test_security_violation_in_agent():
    agent = NL2SQLAgent(api_key=None)
    with pytest.raises(SecurityViolationError):
        agent.db.execute_query("DELETE FROM customers WHERE customer_id = 1;")

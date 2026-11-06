"""
NL2SQL Database Agent Module.
Orchestrates schema introspection, semantic layer injection, few-shot prompting,
secure SQL generation via Gemini / LangChain, database execution, and executive answer synthesis.
Includes an intelligent offline demo mode for instant evaluation without an API key.
"""

import os
import re
import json
from typing import Dict, Any, Optional, List
import pandas as pd
from dotenv import load_dotenv

from src.db_engine import DatabaseEngine
from src.semantic_layer import SemanticLayer
from src.few_shot import FewShotManager
from src.security import sanitize_sql, validate_query, SecurityViolationError
from src.visualizer import create_auto_chart

load_dotenv()


class NL2SQLAgent:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash", db_path: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.db = DatabaseEngine(db_path) if db_path else DatabaseEngine()
        self.semantic_layer = SemanticLayer()
        self.few_shot_mgr = FewShotManager()
        self.client = None

        if self.api_key:
            self._init_llm_client()

    def _init_llm_client(self):
        """Initializes the Google GenAI / LangChain Gemini client."""
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            # Fallback to langchain_google_genai if needed
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self.client = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    temperature=0.0
                )
            except Exception as e2:
                self.client = None
                print(f"Warning: Failed to initialize Gemini client: {e2}")

    def is_configured(self) -> bool:
        """Returns True if a live LLM API client is ready."""
        return self.client is not None and bool(self.api_key)

    def _call_gemini(self, prompt: str) -> str:
        """Invokes the Gemini model with low latency and temperature 0.0."""
        if not self.is_configured():
            raise ValueError("Gemini API key is not configured.")

        # Check if Google GenAI native client
        if hasattr(self.client, "models") and hasattr(self.client.models, "generate_content"):
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip()
        else:
            # Langchain invoke
            response = self.client.invoke(prompt)
            return getattr(response, "content", str(response)).strip()

    def _build_sql_prompt(self, user_question: str) -> str:
        """Assembles schema, semantic rules, few-shot examples, and strict SQL generation directives."""
        schema_context = self.db.get_schema_prompt_context()
        semantic_context = self.semantic_layer.get_prompt_context()
        few_shot_context = self.few_shot_mgr.get_prompt_context(limit=4)

        prompt = f"""You are a helpful SQL assistant. Given a database schema and a user's natural language question, write an accurate and efficient SQLite query.

{schema_context}

{semantic_context}

{few_shot_context}

### SQL Generation Guidelines:
1. Dialect: Generate strictly valid SQLite syntax.
2. Read-Only: Output ONLY a SELECT statement. Never output INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA, or ATTACH.
3. Filtering & Formatting:
   - For revenue calculations, filter by `orders.status IN ('Completed', 'Shipped')` unless asked otherwise.
   - Use meaningful column aliases (`total_revenue`, `customer_name`, `units_sold`).
   - Round numeric currency amounts to 2 decimal places using `ROUND(..., 2)`.
   - When grouping or ranking, include an appropriate ORDER BY clause.
   - For year or month filtering, use SQLite date functions like `strftime('%Y-%m', date_col)`.
4. Output Format: Return ONLY the raw SQL query. Do not wrap in markdown code fences (no ```sql), greetings, or extra explanations.

User Question:
"{user_question}"

Executable SQLite Query:"""
        return prompt

    def _build_synthesis_prompt(self, user_question: str, sql_query: str, sample_data_str: str, row_count: int) -> str:
        """Generates the prompt for translating tabular database output into a polished executive answer."""
        prompt = f"""You are a data assistant. Given the following query results for a user's question, summarize the key findings in clear, concise language with bullet points for important takeaways.

User Question:
"{user_question}"

Executed SQL Query:
{sql_query}

Total Rows Returned: {row_count}
Query Results Sample:
{sample_data_str}

### Instructions:
- Answer the user's question directly in the opening sentence.
- Highlight key trends, top performers, or notable patterns using 2-3 concise bullet points.
- Format currency amounts with dollar signs ($) and format percentages cleanly (e.g., 18.5%).
- Keep the summary clean and focused on the data findings."""
        return prompt

    def _offline_demo_query(self, user_question: str) -> Dict[str, Any]:
        """
        Intelligent offline demo engine for evaluation when an API key is not yet provided.
        Matches questions to realistic gold enterprise queries.
        """
        q_lower = user_question.lower()
        
        # 1. Top products / best selling
        if any(w in q_lower for w in ["product", "selling", "bestseller", "item"]):
            sql = """SELECT 
    p.product_name,
    cat.category_name,
    ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - (oi.discount_percent / 100.0))), 2) AS total_revenue,
    SUM(oi.quantity) AS units_sold
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
JOIN categories cat ON p.category_id = cat.category_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status IN ('Completed', 'Shipped')
GROUP BY p.product_id, p.product_name, cat.category_name
ORDER BY total_revenue DESC
LIMIT 7;"""
            ans = ("Our top revenue-generating product is **Predictive AI Engine API** ($32,346.00 in net revenue with 54 units sold), "
                   "closely followed by **Database Cluster Dedicated** and **Ergonomic High-Back Chair**. "
                   "\n\n**Key Takeaways:**\n"
                   "- Enterprise AI & Cloud infrastructure categories account for over 58% of product revenue.\n"
                   "- Workplace hardware items maintain steady unit volume with minimal discount degradation.")

        # 2. Monthly revenue / trend
        elif any(w in q_lower for w in ["trend", "month", "timeline", "sales over time", "revenue over time"]):
            sql = """SELECT 
    strftime('%Y-%m', o.order_date) AS order_month,
    ROUND(SUM(o.total_amount), 2) AS monthly_revenue,
    COUNT(o.order_id) AS total_orders
FROM orders o
WHERE o.status IN ('Completed', 'Shipped')
GROUP BY order_month
ORDER BY order_month ASC
LIMIT 12;"""
            ans = ("Monthly sales revenue has shown steady upward momentum across the measured timeframe. "
                   "Peak monthly revenue was achieved in recent quarters driven by end-of-year enterprise contract renewals."
                   "\n\n**Key Takeaways:**\n"
                   "- Completed transaction volume averages ~45-50 orders per calendar month.\n"
                   "- Q4 showed the strongest surge corresponding with targeted holiday and enterprise renewal campaigns.")

        # 3. Customer segments / AOV
        elif any(w in q_lower for w in ["segment", "aov", "average order", "tier", "client"]):
            sql = """SELECT 
    c.segment,
    ROUND(AVG(o.total_amount), 2) AS average_order_value,
    ROUND(SUM(o.total_amount), 2) AS total_segment_revenue,
    COUNT(o.order_id) AS total_orders
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.status IN ('Completed', 'Shipped')
GROUP BY c.segment
ORDER BY total_segment_revenue DESC;"""
            ans = ("The **Enterprise** segment produces the highest Average Order Value (AOV) and represents the largest revenue driver, "
                   "followed by Mid-Market and SMB accounts."
                   "\n\n**Key Takeaways:**\n"
                   "- Enterprise clients exhibit an AOV roughly 2.8x higher than Consumer accounts.\n"
                   "- SMB accounts generate consistent transaction volume and represent an ideal expansion pool.")

        # 4. Top customers / lifetime spend
        elif any(w in q_lower for w in ["customer", "buyer", "clv", "lifetime", "spend", "user", "who bought"]):
            sql = """SELECT 
    c.first_name || ' ' || c.last_name AS customer_name,
    c.email,
    c.segment,
    c.loyalty_tier,
    ROUND(SUM(o.total_amount), 2) AS lifetime_spend,
    COUNT(o.order_id) AS total_orders
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status IN ('Completed', 'Shipped')
GROUP BY c.customer_id, customer_name, c.email, c.segment, c.loyalty_tier
ORDER BY lifetime_spend DESC
LIMIT 5;"""
            ans = ("Here are our top 5 high-value customers ranked by lifetime spend. Our top account has generated "
                   "substantial recurring revenue across multiple enterprise orders."
                   "\n\n**Key Takeaways:**\n"
                   "- Platinum and Gold tier clients represent our most loyal customer cohort.\n"
                   "- Dedicated account management is recommended for retention of the top 5 spenders.")

        # 5. Marketing campaigns / ROI / Ads
        elif any(w in q_lower for w in ["marketing", "ad", "campaign", "roi", "conversion", "budget"]):
            sql = """SELECT 
    channel,
    ROUND(SUM(budget), 2) AS total_budget,
    ROUND(SUM(spent), 2) AS total_spent,
    SUM(conversions) AS total_conversions,
    ROUND(SUM(spent) * 1.0 / NULLIF(SUM(conversions), 0), 2) AS cost_per_conversion
FROM marketing_campaigns
GROUP BY channel
ORDER BY total_conversions DESC;"""
            ans = ("**Google Ads** and **LinkedIn** generated the highest total conversion volume among all channels. "
                   "Email campaigns yielded the lowest cost per conversion ($28.32/conversion)."
                   "\n\n**Key Takeaways:**\n"
                   "- LinkedIn is our most effective B2B channel for driving high-intent Enterprise pipeline.\n"
                   "- Email nurturing provides exceptional capital efficiency for product upgrades.")

        # 6. Default fallback: Category revenue
        else:
            sql = """SELECT 
    cat.category_name,
    ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - (oi.discount_percent / 100.0))), 2) AS total_revenue,
    SUM(oi.quantity) AS total_units_sold
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
JOIN categories cat ON p.category_id = cat.category_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status IN ('Completed', 'Shipped')
GROUP BY cat.category_id, cat.category_name
ORDER BY total_revenue DESC;"""
            ans = ("Here is the revenue performance breakdown across all product categories. "
                   "**Cloud Infrastructure** and **AI & Data Analytics** lead overall corporate sales."
                   "\n\n**Key Takeaways:**\n"
                   "- Tech-driven departments dominate top-line bookings.\n"
                   "- Workplace Hardware exhibits consistent margins and strong bundle attach rates.")

        return {
            "sql": sql,
            "simulated_answer": ans,
            "is_simulated": True
        }

    def process_query(self, user_question: str) -> Dict[str, Any]:
        """
        Main pipeline:
        1. Context assembly & prompt preparation
        2. SQL generation (via Gemini API or smart demo fallback)
        3. Security validation and row limit enforcement
        4. Database execution
        5. Natural language translation & executive insights
        6. Plotly auto-visualization
        """
        response_data = {
            "question": user_question,
            "generated_sql": "",
            "executed_sql": "",
            "success": False,
            "row_count": 0,
            "execution_time_ms": 0.0,
            "dataframe": pd.DataFrame(),
            "natural_answer": "",
            "figure": None,
            "error": None,
            "mode": "live_llm" if self.is_configured() else "offline_demo"
        }

        # Step 1 & 2: SQL Generation
        if self.is_configured():
            try:
                sql_prompt = self._build_sql_prompt(user_question)
                raw_sql = self._call_gemini(sql_prompt)
                clean_sql = sanitize_sql(raw_sql)
                response_data["generated_sql"] = clean_sql
            except Exception as e:
                response_data["error"] = f"LLM SQL Generation Error: {str(e)}"
                return response_data
        else:
            # Offline demo mode
            demo_result = self._offline_demo_query(user_question)
            clean_sql = demo_result["sql"]
            response_data["generated_sql"] = clean_sql
            offline_ans = demo_result["simulated_answer"]

        # Step 3: Security Validation & DB Execution
        try:
            db_res = self.db.execute_query(clean_sql)
            response_data["execution_time_ms"] = db_res["execution_time_ms"]
            response_data["executed_sql"] = db_res["executed_sql"]
            response_data["dataframe"] = db_res["dataframe"]
            response_data["row_count"] = db_res["row_count"]

            if not db_res["success"]:
                response_data["error"] = f"Database Error: {db_res['error']}"
                return response_data

            response_data["success"] = True

        except SecurityViolationError as sve:
            response_data["error"] = str(sve)
            return response_data
        except Exception as e:
            response_data["error"] = f"Execution Exception: {str(e)}"
            return response_data

        # Step 4: Executive Natural Language Translation
        df = response_data["dataframe"]
        if self.is_configured() and not df.empty:
            try:
                # Format up to 10 rows for synthesis
                sample_data = df.head(10).to_dict(orient="records")
                sample_str = json.dumps(sample_data, default=str, indent=2)
                synthesis_prompt = self._build_synthesis_prompt(
                    user_question=user_question,
                    sql_query=clean_sql,
                    sample_data_str=sample_str,
                    row_count=len(df)
                )
                ans = self._call_gemini(synthesis_prompt)
                response_data["natural_answer"] = ans
            except Exception as e:
                response_data["natural_answer"] = f"Query executed successfully, returning {len(df)} rows."
        else:
            if not self.is_configured():
                response_data["natural_answer"] = offline_ans
            else:
                response_data["natural_answer"] = "No matching records found in the database for the given criteria."

        # Step 5: Auto-Visualization
        try:
            if not df.empty:
                response_data["figure"] = create_auto_chart(df, title=user_question[:60])
        except Exception as e:
            print(f"Visualization warning: {e}")
            response_data["figure"] = None

        return response_data

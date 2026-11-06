"""
DataTalk AI - Enterprise Natural Language to SQL (NL2SQL) Database Agent
Streamlit Web Application
"""

import os
import sys
import time
import pandas as pd
import streamlit as st

# Ensure project root is in Python module search path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.agent import NL2SQLAgent
from src.db_engine import DatabaseEngine
from src.semantic_layer import SemanticLayer
from src.few_shot import FewShotManager
from src.visualizer import create_auto_chart
from data.seed_database import init_db, DB_PATH


# ==============================================================================
# Page Configuration & Global Theme
# ==============================================================================
st.set_page_config(
    page_title="DataTalk AI | Enterprise NL2SQL Database Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Enterprise CSS
st.markdown("""
<style>
    /* Metric Card Styling */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.9));
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 12px;
    }
    .metric-title {
        color: #94A3B8;
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        color: #38BDF8;
        font-size: 1.4rem;
        font-weight: 700;
        margin-top: 4px;
    }
    /* Prompt Chip Buttons */
    .stButton > button {
        border-radius: 8px;
        transition: all 0.2s ease-in-out;
    }
    /* SQL Code Block */
    .sql-meta-badge {
        display: inline-block;
        background-color: #059669;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 8px;
    }
    .sql-time-badge {
        display: inline-block;
        background-color: #3B82F6;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# Session State Initialization
# ==============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "natural_answer": (
                "👋 **Welcome to DataTalk AI!** I am your Enterprise NL2SQL Database Agent.\n\n"
                "I translate your business questions into verified, read-only SQL queries, "
                "execute them against our enterprise data warehouse, and generate executive summaries "
                "with interactive charts in real time.\n\n"
                "Try asking a question in plain English or click one of the suggested prompts below!"
            ),
            "generated_sql": None,
            "executed_sql": None,
            "dataframe": None,
            "figure": None,
            "execution_time_ms": 0.0,
            "row_count": 0,
            "mode": "system"
        }
    ]

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


# ==============================================================================
# Sidebar: Engine Configuration & Knowledge Explorer
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚡ DataTalk Engine")
    st.caption("AI-Powered Business Intelligence & Natural Language Querying")

    # API Configuration
    env_key = os.getenv("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "Google Gemini API Key",
        value=env_key,
        type="password",
        help="Free lifetime API Key from Google AI Studio. Leave empty to use intelligent Offline Demo Mode."
    )

    col_model, col_status = st.columns([2, 1])
    with col_model:
        selected_model = st.selectbox(
            "Model",
            ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
            index=0,
            help="gemini-2.0-flash is ultra-fast and free."
        )
    with col_status:
        if api_key_input:
            st.markdown("<br><span style='color:#10B981; font-weight:600;'>🟢 Live LLM</span>", unsafe_allow_html=True)
        else:
            st.markdown("<br><span style='color:#F59E0B; font-weight:600;'>🟡 Demo Mode</span>", unsafe_allow_html=True)

    if not api_key_input:
        st.info("💡 **Free Lifetime Setup:** [Get a 100% Free Gemini API Key](https://aistudio.google.com/app/apikey) (No credit card needed).")

    st.divider()

    # Database Architecture & Tables
    st.markdown("### 🗄️ Database Architecture")
    db_engine = DatabaseEngine(DB_PATH)
    schema_info = db_engine.get_schema_info()

    # Summary metrics in sidebar
    total_tables = len(schema_info)
    total_records = sum(details["row_count"] for details in schema_info.values())
    st.markdown(f"**Dialect:** SQLite (Read-Only Guardrailed)")
    st.markdown(f"**Scope:** {total_tables} Tables | {total_records:,} Total Records")

    with st.expander("🔍 Explore Tables & Schema", expanded=False):
        for table, details in schema_info.items():
            st.markdown(f"**Table `{table}`** ({details['row_count']} rows)")
            col_list = [f"`{c['name']}` ({c['type']})" for c in details["columns"][:6]]
            st.caption(", ".join(col_list) + ("..." if len(details["columns"]) > 6 else ""))
            if details["foreign_keys"]:
                for fk in details["foreign_keys"]:
                    st.caption(f"↳ FK: `{fk['from_col']}` → `{fk['to_table']}.{fk['to_col']}`")
            st.divider()

    # Semantic Layer Inspector
    with st.expander("📐 Semantic Model Layer (YAML)", expanded=False):
        sem_layer = SemanticLayer()
        st.markdown("**Defined Business Metrics:**")
        for key, m in sem_layer.metrics.items():
            st.markdown(f"- **{m.get('label', key)}**: `{m.get('formula', '')}`")
            if m.get("business_rule"):
                st.caption(f"Rule: {m.get('business_rule')}")

    # Few-Shot Examples Inspector
    with st.expander("🎯 Validated Few-Shot Prompts", expanded=False):
        few_shot = FewShotManager()
        st.caption(f"{len(few_shot.examples)} validated gold SQL queries loaded for high precision.")
        for idx, ex in enumerate(few_shot.examples[:3], 1):
            st.markdown(f"**{idx}. {ex['question']}**")
            st.code(ex["sql"].strip(), language="sql")

    # Database Tools
    st.divider()
    if st.button("🔄 Reset / Re-seed Database"):
        with st.spinner("Re-seeding database with fresh records..."):
            init_db(DB_PATH)
            st.success("Database re-seeded successfully!")
            time.sleep(1)
            st.rerun()


# ==============================================================================
# Header & Executive Summary
# ==============================================================================
st.markdown("## ⚡ DataTalk AI: Natural Language to SQL Agent")
st.markdown(
    "Eliminate reporting bottlenecks. Ask any analytical question in plain English and receive "
    "instant, verified SQL execution, executive insights, and interactive visualizations."
)

# Suggested Query Chips
st.markdown("##### 💡 Suggested Questions (Click to Test):")
chip_cols = st.columns(3)

prompt_options = [
    ("🏆 Top Products", "What were our top 5 best-selling products by total revenue?"),
    ("📈 Monthly Trend", "Show the monthly revenue trend for the year 2024."),
    ("👥 Customer AOV", "Which customer segments generate the highest average order value?"),
    ("💎 Top Spenders", "Identify top 5 customers with the highest lifetime spend."),
    ("🎯 Marketing ROI", "Compare marketing campaign budget versus actual conversions by channel."),
    ("📦 Inventory Risks", "Which products have the lowest stock quantity and what is their current status?")
]

for idx, (label, question) in enumerate(prompt_options):
    col = chip_cols[idx % 3]
    with col:
        if st.button(f"{label}", key=f"chip_{idx}", use_container_width=True):
            st.session_state.pending_prompt = question

st.divider()


# ==============================================================================
# Render Chat History
# ==============================================================================
for msg_idx, message in enumerate(st.session_state.messages):
    role = message["role"]
    with st.chat_message(role):
        # 1. Executive Natural Language Answer
        if message.get("natural_answer"):
            st.markdown(message["natural_answer"])

        # 2. Interactive Chart (Assistant messages with data)
        if message.get("figure") is not None:
            st.plotly_chart(message["figure"], use_container_width=True, key=f"chart_{msg_idx}")

        # 3. Data Table & Action Buttons
        df = message.get("dataframe")
        if df is not None and not df.empty:
            with st.expander(f"📊 Query Results Table ({message.get('row_count', len(df))} rows)", expanded=False):
                st.dataframe(df, use_container_width=True)

                col_dl, col_blank = st.columns([1, 4])
                with col_dl:
                    csv_data = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f"query_result_{msg_idx}.csv",
                        mime="text/csv",
                        key=f"dl_{msg_idx}"
                    )

        # 4. Under-the-Hood SQL & Guardrails Inspector
        if message.get("executed_sql"):
            with st.expander("🛠️ Under the Hood: Executed SQL & Security Guardrails", expanded=False):
                # Metadata Badges
                st.markdown(
                    f"<span class='sql-meta-badge'>🛡️ Read-Only Guardrail Verified</span>"
                    f"<span class='sql-time-badge'>⚡ {message.get('execution_time_ms', 0):.1f} ms</span>",
                    unsafe_allow_html=True
                )
                st.markdown(f"**Dialect:** SQLite | **Engine Mode:** `{message.get('mode', 'live_llm')}`")
                st.code(message["executed_sql"], language="sql")


# ==============================================================================
# Chat Input & Query Processing
# ==============================================================================
user_prompt = st.chat_input("Ask a data question (e.g. 'Show total revenue by category this year')...")

# Check if a suggested chip was clicked
if st.session_state.pending_prompt:
    user_prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if user_prompt:
    # 1. Display User Message
    st.session_state.messages.append({
        "role": "user",
        "content": user_prompt
    })
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # 2. Agent Processing & Execution
    with st.chat_message("assistant"):
        with st.spinner("Analyzing schema, generating secure SQL, and fetching insights..."):
            agent = NL2SQLAgent(
                api_key=api_key_input if api_key_input.strip() else None,
                model_name=selected_model,
                db_path=DB_PATH
            )
            result = agent.process_query(user_prompt)

        if not result["success"] and result.get("error"):
            st.error(f"⚠️ {result['error']}")
            st.session_state.messages.append({
                "role": "assistant",
                "natural_answer": f"**Execution Alert:** {result['error']}",
                "generated_sql": result.get("generated_sql"),
                "executed_sql": result.get("executed_sql"),
                "dataframe": None,
                "figure": None,
                "execution_time_ms": result.get("execution_time_ms", 0.0),
                "row_count": 0,
                "mode": result.get("mode", "unknown")
            })
        else:
            # Display Natural Language Answer
            st.markdown(result["natural_answer"])

            # Display Chart
            if result.get("figure"):
                st.plotly_chart(result["figure"], use_container_width=True)

            # Display Data Table
            df = result.get("dataframe")
            if df is not None and not df.empty:
                with st.expander(f"📊 Query Results Table ({result['row_count']} rows)", expanded=False):
                    st.dataframe(df, use_container_width=True)
                    csv_data = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name="query_result.csv",
                        mime="text/csv"
                    )

            # Display SQL and Telemetry
            if result.get("executed_sql"):
                with st.expander("🛠️ Under the Hood: Executed SQL & Security Guardrails", expanded=False):
                    st.markdown(
                        f"<span class='sql-meta-badge'>🛡️ Read-Only Guardrail Verified</span>"
                        f"<span class='sql-time-badge'>⚡ {result['execution_time_ms']:.1f} ms</span>",
                        unsafe_allow_html=True
                    )
                    st.markdown(f"**Dialect:** SQLite | **Engine Mode:** `{result['mode']}`")
                    st.code(result["executed_sql"], language="sql")

            # Save to session history
            st.session_state.messages.append({
                "role": "assistant",
                "natural_answer": result["natural_answer"],
                "generated_sql": result.get("generated_sql"),
                "executed_sql": result.get("executed_sql"),
                "dataframe": result.get("dataframe"),
                "figure": result.get("figure"),
                "execution_time_ms": result.get("execution_time_ms", 0.0),
                "row_count": result.get("row_count", 0),
                "mode": result.get("mode", "unknown")
            })

"""
Data Visualization Engine for NL2SQL Agent.
Intelligently inspects query result sets and automatically generates interactive Plotly figures
(Bar, Line, Donut, Area, Scatter, and KPI metric cards).
"""

import re
from typing import Optional, Dict, Any, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


COLOR_PALETTE = [
    "#4361EE", "#3A0CA3", "#7209B7", "#F72585", "#4CC9F0",
    "#06D6A0", "#FFD166", "#EF476F", "#118AB2", "#073B4C"
]

LAYOUT_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif", size=13),
    margin=dict(l=40, r=40, t=50, b=40),
    hoverlabel=dict(bgcolor="#1E293B", font_size=12, font_color="#FFFFFF"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)


def _detect_column_types(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Identifies candidate columns for (date_col, categorical_col, numeric_col).
    """
    date_col = None
    cat_col = None
    num_col = None

    for col in df.columns:
        col_lower = col.lower()
        # Date column detection
        if not date_col:
            if any(term in col_lower for term in ["date", "month", "year", "quarter", "day", "time"]):
                date_col = col
                continue
            # Try parsing
            if df[col].dtype == object and len(df) > 0:
                first_val = str(df[col].iloc[0])
                if re.match(r"^\d{4}-\d{2}", first_val):
                    date_col = col
                    continue

        # Numeric column detection
        if pd.api.types.is_numeric_dtype(df[col]):
            if not num_col:
                # Prefer value/amount/revenue/count/sum over id
                if not col_lower.endswith("_id") and col_lower != "id":
                    num_col = col
            elif "id" in (num_col or "").lower() and not ("id" in col_lower):
                num_col = col
            continue

        # Categorical column detection
        if not cat_col and (df[col].dtype == object or pd.api.types.is_string_dtype(df[col])):
            if not col_lower.endswith("_id") and col_lower != "id":
                cat_col = col

    # Fallback for num_col if only IDs exist
    if not num_col:
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                num_col = col
                break

    # Fallback for cat_col if none detected
    if not cat_col and not date_col:
        for col in df.columns:
            if col != num_col:
                cat_col = col
                break

    return date_col, cat_col, num_col


def create_auto_chart(df: pd.DataFrame, title: str = "Query Insights Visualization", chart_type_override: Optional[str] = None) -> Optional[go.Figure]:
    """
    Generates an interactive Plotly chart dynamically based on data structure.
    Supports chart_type_override: 'bar', 'line', 'pie', 'area', 'auto'.
    """
    if df.empty or len(df.columns) < 2:
        return None

    date_col, cat_col, num_col = _detect_column_types(df)

    # Need at least one numeric column for meaningful visualization
    if not num_col:
        return None

    selected_type = chart_type_override or "auto"

    fig = None

    # 1. Date/Time Series -> Line or Area Chart
    if date_col and (selected_type in ("auto", "line", "area")):
        df_sorted = df.sort_values(by=date_col)
        if selected_type == "area":
            fig = px.area(
                df_sorted,
                x=date_col,
                y=num_col,
                color_discrete_sequence=[COLOR_PALETTE[0]],
                title=f"{title} (Time Trend)"
            )
        else:
            fig = px.line(
                df_sorted,
                x=date_col,
                y=num_col,
                markers=True,
                color_discrete_sequence=[COLOR_PALETTE[0]],
                title=f"{title} (Time Trend)"
            )

    # 2. Categorical -> Pie / Donut Chart (if small category count or requested)
    elif (cat_col or date_col) and (selected_type == "pie" or (selected_type == "auto" and len(df) <= 6)):
        group_col = cat_col or date_col
        fig = px.pie(
            df,
            names=group_col,
            values=num_col,
            hole=0.45,
            color_discrete_sequence=COLOR_PALETTE,
            title=f"{title} (Distribution)"
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')

    # 3. Categorical / General -> Bar Chart
    elif (cat_col or date_col) and (selected_type in ("auto", "bar")):
        group_col = cat_col or date_col
        df_chart = df.copy()
        # If too many categories, show top 15
        if len(df_chart) > 15:
            df_chart = df_chart.head(15)

        fig = px.bar(
            df_chart,
            x=group_col,
            y=num_col,
            color=group_col,
            color_discrete_sequence=COLOR_PALETTE,
            title=f"{title} (Comparison)"
        )
        fig.update_layout(showlegend=False)

    # 4. Fallback: Bar chart on first column vs numeric column
    if fig is None and num_col:
        x_col = [c for c in df.columns if c != num_col][0]
        fig = px.bar(
            df.head(15),
            x=x_col,
            y=num_col,
            color_discrete_sequence=[COLOR_PALETTE[0]],
            title=title
        )

    if fig:
        fig.update_layout(**LAYOUT_THEME)
        fig.update_xaxes(showgrid=True, gridcolor="rgba(150, 150, 150, 0.15)")
        fig.update_yaxes(showgrid=True, gridcolor="rgba(150, 150, 150, 0.15)")

    return fig

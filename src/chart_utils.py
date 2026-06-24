"""Small Plotly chart helpers for the Streamlit app layer."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.i18n import t, translate_module_name, translate_rating, translate_risk_label


RISK_COLUMNS = [
    "seasonality_risk",
    "market_competition_risk",
    "policy_risk",
    "climate_physical_risk",
    "financial_pressure_risk",
    "platform_dependency_risk",
]

RISK_LABELS = {
    "seasonality_risk": "Seasonality",
    "market_competition_risk": "Competition",
    "policy_risk": "Policy",
    "climate_physical_risk": "Climate Physical",
    "financial_pressure_risk": "Financial Pressure",
    "platform_dependency_risk": "Platform Dependency",
}

MODULE_LABELS = {
    "A. REITs Cash Flow and Distribution Capacity": "Cash Flow",
    "B. Tourism Operating Quality": "Tourism Ops",
    "C. Service Quality and Online Reputation": "Service Quality",
    "D. Risk Management and Resilience": "Risk Resilience",
    "E. Data Maturity and Smart Operation": "Data Maturity",
}


def _empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        annotations=[{"text": t("common.data_unavailable"), "showarrow": False, "x": 0.5, "y": 0.5}],
        template="plotly_white",
        height=360,
    )
    return fig


def make_score_bar_chart(total_scores_df: pd.DataFrame) -> go.Figure:
    """Create a simple total-score bar chart."""
    required = {"asset_name", "total_score", "rating_level"}
    if total_scores_df.empty or not required.issubset(total_scores_df.columns):
        return _empty_figure(t("charts.score_ranking"))

    plot_df = total_scores_df.dropna(subset=["total_score"]).copy()
    if plot_df.empty:
        return _empty_figure(t("charts.score_ranking"))
    plot_df["rating_level_display"] = plot_df["rating_level"].map(translate_rating)

    fig = px.bar(
        plot_df.sort_values("total_score", ascending=False),
        x="asset_name",
        y="total_score",
        color="rating_level_display",
        text="total_score",
        title=t("charts.score_ranking"),
        range_y=[0, 100],
        color_discrete_sequence=["#2454A6", "#5B7DBE", "#8AA6D6", "#C9D6EA"],
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(
        xaxis_title="",
        yaxis_title=t("labels.score"),
        template="plotly_white",
        height=420,
        legend_title_text=t("labels.rating_level"),
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    return fig


def make_module_score_radar(module_scores_df: pd.DataFrame, asset_id: str) -> go.Figure:
    """Create a radar chart for one asset's module scores."""
    if module_scores_df.empty:
        return _empty_figure(t("charts.module_radar"))

    asset_df = module_scores_df[module_scores_df["asset_id"] == asset_id].dropna(subset=["module_score"])
    if asset_df.empty:
        return _empty_figure(t("charts.module_radar"))

    categories = asset_df["module"].map(lambda value: translate_module_name(value, short=True)).tolist()
    values = pd.to_numeric(asset_df["module_score"], errors="coerce").fillna(0).tolist()
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill="toself",
            name=str(asset_df["asset_name"].iloc[0]),
        )
    )
    fig.update_layout(
        title=t("charts.module_radar"),
        polar={"radialaxis": {"visible": True, "range": [0, 100]}},
        showlegend=False,
        template="plotly_white",
        height=430,
        margin={"l": 40, "r": 40, "t": 70, "b": 40},
    )
    return fig


def make_risk_radar(risk_df: pd.DataFrame, asset_id: str) -> go.Figure:
    """Create a simple radar chart from latest risk values for one asset."""
    if risk_df.empty:
        return _empty_figure(t("charts.risk_radar"))

    asset_df = risk_df[risk_df["asset_id"] == asset_id].copy()
    if asset_df.empty:
        return _empty_figure(t("charts.risk_radar"))

    asset_df["year"] = pd.to_numeric(asset_df["year"], errors="coerce")
    row = asset_df.sort_values("year").tail(1).iloc[0]
    available_columns = [column for column in RISK_COLUMNS if column in risk_df.columns]
    if not available_columns:
        return _empty_figure(t("charts.risk_radar"))

    values = pd.to_numeric(row[available_columns], errors="coerce").fillna(0).tolist()
    labels = [translate_risk_label(column) for column in available_columns]
    labels = labels + [labels[0]]
    values_closed = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values_closed, theta=labels, fill="toself", name=row["asset_id"]))
    fig.update_layout(
        title=t("charts.risk_radar"),
        polar={"radialaxis": {"visible": True, "range": [0, 1]}},
        showlegend=False,
        template="plotly_white",
        height=430,
        margin={"l": 40, "r": 40, "t": 70, "b": 40},
    )
    return fig


def make_indicator_bar_chart(indicator_scores_df: pd.DataFrame, asset_id: str) -> go.Figure:
    """Create a bar chart of indicator scores for one asset."""
    if indicator_scores_df.empty:
        return _empty_figure(t("charts.indicator_scores"))

    asset_df = indicator_scores_df[indicator_scores_df["asset_id"] == asset_id].copy()
    asset_df = asset_df.dropna(subset=["indicator_score"])
    if asset_df.empty:
        return _empty_figure(t("charts.indicator_scores"))
    asset_df["module_display"] = asset_df["module"].map(translate_module_name)

    fig = px.bar(
        asset_df,
        x="indicator_id",
        y="indicator_score",
        color="module_display",
        hover_data=["indicator_name", "raw_value", "direction"],
        title=t("charts.indicator_scores"),
        range_y=[0, 100],
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    fig.update_layout(
        xaxis_title=t("columns.indicator_id"),
        yaxis_title=t("labels.score"),
        template="plotly_white",
        height=430,
        legend_title_text=t("columns.module"),
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    return fig


def make_heatmap_from_risk_scores(risk_df: pd.DataFrame) -> go.Figure:
    """Create a compact heatmap from latest risk metrics."""
    if risk_df.empty:
        return _empty_figure(t("charts.risk_heatmap"))

    latest_df = risk_df.copy()
    latest_df["year"] = pd.to_numeric(latest_df["year"], errors="coerce")
    latest_df = latest_df.sort_values(["asset_id", "year"]).groupby("asset_id", as_index=False).tail(1)
    available_columns = [column for column in RISK_COLUMNS if column in latest_df.columns]
    if latest_df.empty or not available_columns:
        return _empty_figure(t("charts.risk_heatmap"))

    heatmap_df = latest_df.set_index("asset_id")[available_columns].apply(pd.to_numeric, errors="coerce")
    if heatmap_df.dropna(how="all").empty:
        return _empty_figure(t("charts.risk_heatmap"))

    heatmap_df = heatmap_df.rename(columns={column: translate_risk_label(column) for column in available_columns})
    fig = px.imshow(
        heatmap_df,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="Reds",
        title=t("charts.latest_risk_heatmap"),
        zmin=0,
        zmax=1,
    )
    fig.update_layout(
        xaxis_title=t("charts.risk_indicator"),
        yaxis_title=t("charts.asset"),
        template="plotly_white",
        height=420,
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    return fig


def make_base_vs_simulated_bar(
    base_value: float | None,
    simulated_value: float | None,
    metric_name: str,
    y_axis_title: str = "Value",
) -> go.Figure:
    """Create a two-bar base versus simulated comparison chart."""
    values = pd.Series([base_value, simulated_value], index=[t("scenario.base"), t("scenario.simulated")])
    values = pd.to_numeric(values, errors="coerce")
    if values.dropna().empty:
        return _empty_figure(metric_name)

    plot_df = pd.DataFrame({"case": values.index, "value": values.values})
    fig = px.bar(
        plot_df,
        x="case",
        y="value",
        color="case",
        text="value",
        title=metric_name,
        color_discrete_sequence=["#2454A6", "#D92D20"],
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        xaxis_title="",
        yaxis_title=y_axis_title,
        template="plotly_white",
        height=360,
        showlegend=False,
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    return fig


def make_cash_flow_impact_chart(
    base_metrics: dict,
    simulated_metrics: dict,
) -> go.Figure:
    """Create a base-versus-simulated chart for NOI, OCF, and AFFO proxy."""
    rows = [
        {
            "metric": "NOI",
            t("scenario.base"): base_metrics.get("noi"),
            t("scenario.simulated"): simulated_metrics.get("noi_after"),
        },
        {
            "metric": "Operating Cash Flow",
            t("scenario.base"): base_metrics.get("operating_cash_flow"),
            t("scenario.simulated"): simulated_metrics.get("operating_cash_flow_after"),
        },
        {
            "metric": "AFFO Proxy",
            t("scenario.base"): base_metrics.get("estimated_affo"),
            t("scenario.simulated"): simulated_metrics.get("affo_after"),
        },
    ]
    plot_df = pd.DataFrame(rows)
    long_df = plot_df.melt(id_vars="metric", var_name="case", value_name="value")
    long_df["value"] = pd.to_numeric(long_df["value"], errors="coerce")
    if long_df["value"].dropna().empty:
        return _empty_figure(t("scenario.cash_flow_impact"))

    fig = px.bar(
        long_df,
        x="metric",
        y="value",
        color="case",
        barmode="group",
        text="value",
        title=t("charts.cash_flow_impact"),
        color_discrete_sequence=["#2454A6", "#D92D20"],
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(
        xaxis_title="",
        yaxis_title=t("charts.amount"),
        template="plotly_white",
        height=420,
        legend_title_text=t("charts.case"),
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    return fig


def make_score_change_chart(
    base_score: float | None,
    score_change: float | None,
    simulated_score: float | None,
) -> go.Figure:
    """Create a simple waterfall chart for score movement."""
    values = pd.to_numeric(pd.Series([base_score, score_change, simulated_score]), errors="coerce")
    if values.dropna().empty or pd.isna(base_score) or pd.isna(score_change) or pd.isna(simulated_score):
        return _empty_figure(t("scenario.score_change"))

    fig = go.Figure(
        go.Waterfall(
            name="Score",
            orientation="v",
            measure=["absolute", "relative", "total"],
            x=[t("scenario.base_score"), t("scenario.score_change"), t("scenario.simulated_score")],
            y=[base_score, score_change, simulated_score],
            text=[f"{base_score:.1f}", f"{score_change:.1f}", f"{simulated_score:.1f}"],
            textposition="outside",
            connector={"line": {"color": "#98A2B3"}},
            increasing={"marker": {"color": "#1B7F4B"}},
            decreasing={"marker": {"color": "#D92D20"}},
            totals={"marker": {"color": "#2454A6"}},
        )
    )
    fig.update_layout(
        title=t("charts.score_change"),
        yaxis_title=t("labels.score"),
        template="plotly_white",
        height=390,
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    return fig

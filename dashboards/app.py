"""
dashboards/app.py
=================
UK Mortgage Stress Platform — Plotly Dash Interactive Application

Run locally:
    cd uk-mortgage-stress-platform
    python dashboards/app.py

Deploy to Render.com:
    See render.yaml at repo root. App binds to PORT env variable.
    Gunicorn command: gunicorn dashboards.app:server
"""

import os, json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback

# ── Load data ─────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS    = os.path.join(BASE_DIR, "outputs", "negative_equity_by_region_scenario.csv")
AFF_TABLE  = os.path.join(BASE_DIR, "data", "processed", "affordability_table.csv")
GEOJSON    = os.path.join(BASE_DIR, "data", "raw", "LAD_Dec2023_UK_BGC.geojson")

df = pd.read_csv(RESULTS)
df["prob_pct"] = df["prob_negative_equity"] * 100

aff = pd.read_csv(AFF_TABLE, parse_dates=["month_date"])

with open(GEOJSON) as f:
    geojson_data = json.load(f)

SCENARIO_OPTIONS = [
    {"label": "Scenario A: Bank Rate −1% (2.75%)",  "value": "minus_1pct"},
    {"label": "Scenario B: Base Rate (3.75%)",       "value": "base"},
    {"label": "Scenario C: Bank Rate +1% (4.75%)",  "value": "plus_1pct"},
    {"label": "Scenario D: Bank Rate +2% (5.75%)",  "value": "plus_2pct"},
]

COLOUR_SCALE = [
    [0.00, "#ffffcc"], [0.15, "#fed976"], [0.30, "#fd8d3c"],
    [0.60, "#e31a1c"], [1.00, "#800026"]
]

# ── App layout ────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    title="UK Mortgage Stress Platform",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

# For Render.com deployment
server = app.server

HEADER_STYLE = {
    "background": "#1f4e79", "color": "white",
    "padding": "16px 24px", "marginBottom": "0",
}
CARD_STYLE = {
    "background": "white", "borderRadius": "6px",
    "padding": "16px", "boxShadow": "0 2px 6px rgba(0,0,0,0.08)",
    "marginBottom": "16px",
}

app.layout = html.Div([
    # ── Header ───────────────────────────────────────────────────────────────
    html.Div([
        html.H1("UK Mortgage Stress & Housing Affordability Platform",
                style={"margin": 0, "fontSize": "22px", "fontWeight": "700"}),
        html.P("Probability of negative equity under Bank of England rate scenarios | "
               "5-year horizon | 90% LTV | 25-year repayment",
               style={"margin": "4px 0 0 0", "fontSize": "13px", "opacity": 0.85}),
    ], style=HEADER_STYLE),

    # ── Controls ─────────────────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Label("Rate Scenario", style={"fontWeight": "600", "fontSize": "13px"}),
            dcc.Dropdown(
                id="scenario-dropdown",
                options=SCENARIO_OPTIONS,
                value="base",
                clearable=False,
                style={"fontSize": "13px"},
            ),
        ], style={"width": "360px", "marginRight": "24px"}),
        html.Div([
            html.Label("Metric", style={"fontWeight": "600", "fontSize": "13px"}),
            dcc.RadioItems(
                id="metric-radio",
                options=[
                    {"label": " Probability of Negative Equity (%)", "value": "prob_pct"},
                    {"label": " Price-to-Income Ratio",              "value": "price_to_income_ratio"},
                ],
                value="prob_pct",
                inline=True,
                style={"fontSize": "13px", "marginTop": "8px"},
            ),
        ]),
    ], style={"display": "flex", "alignItems": "flex-end",
              "padding": "14px 24px 10px", "background": "#f5f7fa",
              "borderBottom": "1px solid #e0e0e0"}),

    # ── Main content ─────────────────────────────────────────────────────────
    html.Div([
        # Left: choropleth
        html.Div([
            dcc.Graph(id="choropleth-map",
                      style={"height": "580px"},
                      config={"displayModeBar": False}),
        ], style={"flex": "1.6", **CARD_STYLE}),

        # Right: detail panel (populated on click)
        html.Div([
            html.H3("Regional Detail", id="detail-title",
                    style={"color": "#1f4e79", "fontSize": "15px", "marginTop": 0}),
            html.P("Click a local authority on the map to see its detail.",
                   id="detail-subtitle",
                   style={"color": "#555", "fontSize": "12px"}),
            dcc.Graph(id="affordability-chart",
                      style={"height": "220px"},
                      config={"displayModeBar": False}),
            dcc.Graph(id="scenario-bar",
                      style={"height": "200px"},
                      config={"displayModeBar": False}),
            html.Div(id="kpi-cards", style={"marginTop": "8px"}),
        ], style={"flex": "1", "marginLeft": "16px", **CARD_STYLE}),

    ], style={"display": "flex", "padding": "16px 24px",
              "background": "#f0f2f5", "minHeight": "640px"}),

    # ── Footer ───────────────────────────────────────────────────────────────
    html.Div([
        html.P(
            "Sources: HM Land Registry UK HPI | ONS ASHE Table 8 | BoE IADB | FCA Mortgage Lending Statistics | "
            "ONS Open Geography Portal. Methodology: Monte Carlo simulation (10,000 paths, Normal returns). "
            "Limitations: Normal distribution underestimates tail risk; annual volatility used as monthly proxy. "
            "Not investment or legal advice.",
            style={"fontSize": "11px", "color": "#999", "margin": 0},
        ),
    ], style={"background": "#1f4e79", "padding": "10px 24px"}),

    # ── Hidden store for click state ─────────────────────────────────────────
    dcc.Store(id="selected-lad", data=None),

], style={"fontFamily": "Arial, sans-serif", "background": "#f0f2f5"})


# ── Callbacks ─────────────────────────────────────────────────────────────────

@callback(
    Output("choropleth-map", "figure"),
    Input("scenario-dropdown", "value"),
    Input("metric-radio", "value"),
)
def update_map(scenario, metric):
    sub = df[df["scenario"] == scenario].copy()

    if metric == "prob_pct":
        color_col   = "prob_pct"
        color_label = "P(NE) %"
        range_color = [0, sub["prob_pct"].max() * 1.05 + 0.01]
        hover_data  = {"lad_name": True, "prob_pct": ":.2f", "price_to_income_ratio": ":.1f"}
    else:
        color_col   = "price_to_income_ratio"
        color_label = "PTI Ratio"
        range_color = [3, 16]
        hover_data  = {"lad_name": True, "price_to_income_ratio": ":.1f", "prob_pct": ":.2f"}

    fig = px.choropleth_mapbox(
        sub,
        geojson=geojson_data,
        locations="lad_code",
        featureidkey="properties.LAD23CD",
        color=color_col,
        color_continuous_scale=COLOUR_SCALE,
        range_color=range_color,
        mapbox_style="carto-positron",
        zoom=4.8, center={"lat": 54.0, "lon": -2.5},
        opacity=0.75,
        labels={color_col: color_label},
        hover_name="lad_name",
        hover_data=hover_data,
    )
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar={
            "title": color_label, "thickness": 14, "len": 0.7,
            "tickfont": {"size": 11},
        },
    )
    return fig


@callback(
    Output("selected-lad", "data"),
    Input("choropleth-map", "clickData"),
)
def store_click(click_data):
    if not click_data:
        return None
    return click_data["points"][0]["location"]


@callback(
    Output("detail-title",      "children"),
    Output("detail-subtitle",   "children"),
    Output("affordability-chart", "figure"),
    Output("scenario-bar",       "figure"),
    Output("kpi-cards",          "children"),
    Input("selected-lad", "data"),
    Input("scenario-dropdown", "value"),
)
def update_detail(lad_code, scenario):
    empty_fig = go.Figure(layout=go.Layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"))
    if not lad_code:
        return ("Regional Detail",
                "Click a local authority on the map to see its detail.",
                empty_fig, empty_fig, [])

    # LAD info
    lad_row = df[(df.lad_code == lad_code) & (df.scenario == scenario)]
    if lad_row.empty:
        return (f"No data for {lad_code}", "", empty_fig, empty_fig, [])
    lad_name = lad_row.iloc[0]["lad_name"]
    region   = lad_row.iloc[0]["region"]

    # Affordability time series
    aff_sub  = aff[aff.lad_code == lad_code].sort_values("month_date")
    ts_fig   = go.Figure()
    if len(aff_sub):
        ts_fig.add_trace(go.Scatter(
            x=aff_sub["month_date"], y=aff_sub["repayment_pct_income"],
            mode="lines", name="Repayment % Income",
            line={"color": "#1f4e79", "width": 2},
            fill="tozeroy", fillcolor="rgba(31,78,121,0.12)",
        ))
        ts_fig.add_hline(y=33, line_dash="dot", line_color="#ed7d31",
                         annotation_text="33% stress threshold",
                         annotation_font_size=10)
    ts_fig.update_layout(
        title={"text": "Monthly Repayment as % of Gross Income", "font": {"size": 12}},
        margin={"t": 30, "b": 30, "l": 10, "r": 10},
        yaxis={"title": "% income", "ticksuffix": "%", "range": [0, max(60, aff_sub.repayment_pct_income.max()*1.1) if len(aff_sub) else 60]},
        xaxis={"title": ""},
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
    )

    # Scenario comparison bar
    scenario_data = df[df.lad_code == lad_code].copy()
    scenario_data["scenario_label"] = scenario_data["scenario"].map({
        "minus_1pct": "−1%", "base": "Base", "plus_1pct": "+1%", "plus_2pct": "+2%"
    })
    bar_fig = px.bar(
        scenario_data, x="scenario_label", y="prob_pct",
        color="prob_pct",
        color_continuous_scale=COLOUR_SCALE,
        labels={"prob_pct": "P(NE) %", "scenario_label": "Bank Rate Scenario"},
        text_auto=".2f",
    )
    bar_fig.update_layout(
        title={"text": "Negative Equity Probability by Scenario", "font": {"size": 12}},
        margin={"t": 30, "b": 30, "l": 10, "r": 10},
        showlegend=False, coloraxis_showscale=False,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    bar_fig.update_traces(textposition="outside")

    # KPI cards
    current_aff = aff_sub.tail(1)
    price        = float(current_aff["average_price"].values[0]) if len(current_aff) else 0
    pti          = float(current_aff["price_to_income_ratio"].values[0]) if len(current_aff) else 0
    rep_pct      = float(current_aff["repayment_pct_income"].values[0]) if len(current_aff) else 0
    ne_prob      = float(lad_row.iloc[0]["prob_pct"])
    mort_rate    = float(lad_row.iloc[0]["mortgage_rate_pct"])

    def kpi(label, value, colour="#1f4e79"):
        return html.Div([
            html.P(label, style={"fontSize": "11px", "color": "#777", "margin": "0 0 2px 0"}),
            html.P(value, style={"fontSize": "16px", "fontWeight": "700",
                                 "color": colour, "margin": 0}),
        ], style={"background": "#f5f7fa", "borderRadius": "5px",
                  "padding": "8px 12px", "marginBottom": "8px"})

    cards = [
        kpi("Avg House Price (Jun 2024)", f"£{price:,.0f}"),
        kpi("Price-to-Income Ratio",      f"{pti:.1f}×"),
        kpi("Repayment % Income (latest)", f"{rep_pct:.1f}%",
            "#c00000" if rep_pct > 40 else "#ed7d31" if rep_pct > 33 else "#1f4e79"),
        kpi(f"P(Negative Equity) — {scenario}", f"{ne_prob:.2f}%",
            "#c00000" if ne_prob > 3 else "#ed7d31" if ne_prob > 1 else "#1f4e79"),
        kpi("Mortgage Rate (scenario)",   f"{mort_rate:.2f}%"),
    ]

    title    = f"{lad_name}"
    subtitle = f"{region} | Click another LAD to update"

    return title, subtitle, ts_fig, bar_fig, cards


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)

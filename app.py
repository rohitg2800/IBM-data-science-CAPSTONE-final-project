import os
from pathlib import Path

import pandas as pd
import dash
from dash import dcc, html, Input, Output
import plotly.express as px


# ----------------------------
# Data load (Render-safe path)
# ----------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "output_file.csv"

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Missing dataset at {DATA_PATH}. Ensure output_file.csv is committed to the repo."
    )

df = pd.read_csv(DATA_PATH)

# Normalize / clean
# success can be True/False/NaN; we keep NaN as "Unknown"
df["success_label"] = df["success"].map({True: "Success", False: "Failure"}).fillna("Unknown")

# Convert date_utc -> datetime (safe even if format varies)
df["date_utc_dt"] = pd.to_datetime(df["date_utc"], errors="coerce", utc=True)
df["year"] = df["date_utc_dt"].dt.year

# For plotting success as numeric (Success=1, Failure=0, Unknown=NaN)
df["success_num"] = df["success"].map({True: 1, False: 0})

# Dropdown options
launchpads = sorted(df["launchpad"].dropna().unique().tolist())
rockets = sorted(df["rocket"].dropna().unique().tolist())

launchpad_options = [{"label": "All Launchpads", "value": "ALL"}] + [
    {"label": lp, "value": lp} for lp in launchpads
]
rocket_options = [{"label": "All Rockets", "value": "ALL"}] + [
    {"label": r, "value": r} for r in rockets
]

# ----------------------------
# Dash app
# ----------------------------
app = dash.Dash(__name__)
server = app.server  # required for gunicorn on Render

app.layout = html.Div(
    style={"maxWidth": "1100px", "margin": "0 auto", "padding": "16px"},
    children=[
        html.H1(
            "SpaceX Launch Dashboard (API v4 dataset)",
            style={"textAlign": "center", "color": "#503D36"},
        ),

        html.Div(
            style={"display": "flex", "gap": "12px", "flexWrap": "wrap"},
            children=[
                html.Div(
                    style={"flex": "1 1 340px"},
                    children=[
                        html.Label("Launchpad"),
                        dcc.Dropdown(
                            id="launchpad-dd",
                            options=launchpad_options,
                            value="ALL",
                            clearable=False,
                            searchable=True,
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": "1 1 340px"},
                    children=[
                        html.Label("Rocket"),
                        dcc.Dropdown(
                            id="rocket-dd",
                            options=rocket_options,
                            value="ALL",
                            clearable=False,
                            searchable=True,
                        ),
                    ],
                ),
            ],
        ),

        html.Br(),

        html.Div(
            style={"display": "flex", "gap": "12px", "flexWrap": "wrap"},
            children=[
                html.Div(style={"flex": "1 1 520px"}, children=[dcc.Graph(id="pie-success")]),
                html.Div(style={"flex": "1 1 520px"}, children=[dcc.Graph(id="bar-year")]),
            ],
        ),

        html.Br(),

        dcc.Graph(id="timeline-success"),

        html.Div(
            style={"fontSize": "12px", "opacity": 0.75, "marginTop": "8px"},
            children=[
                "Notes: This dataset uses IDs for launchpad/rocket/payloads. "
                "If you want human-readable names (e.g., 'KSC LC-39A'), we can enrich it by joining "
                "with SpaceX launchpad/rocket reference tables."
            ],
        ),
    ],
)

def apply_filters(data: pd.DataFrame, launchpad_value: str, rocket_value: str) -> pd.DataFrame:
    out = data
    if launchpad_value != "ALL":
        out = out[out["launchpad"] == launchpad_value]
    if rocket_value != "ALL":
        out = out[out["rocket"] == rocket_value]
    return out


@app.callback(
    Output("pie-success", "figure"),
    Output("bar-year", "figure"),
    Output("timeline-success", "figure"),
    Input("launchpad-dd", "value"),
    Input("rocket-dd", "value"),
)
def update_charts(launchpad_value, rocket_value):
    dff = apply_filters(df, launchpad_value, rocket_value)

    # --- Pie: Success vs Failure vs Unknown
    pie = px.pie(
        dff,
        names="success_label",
        title="Outcome Distribution",
    )

    # --- Bar: launches per year
    year_counts = (
        dff.dropna(subset=["year"])
           .groupby("year", as_index=False)
           .size()
           .rename(columns={"size": "launches"})
           .sort_values("year")
    )
    bar = px.bar(
        year_counts,
        x="year",
        y="launches",
        title="Launches by Year",
    )

    # --- Timeline: success over time (scatter)
    # y is success_num; Unknown becomes NaN and will be omitted
    tdf = dff.dropna(subset=["date_utc_dt"])
    timeline = px.scatter(
        tdf,
        x="date_utc_dt",
        y="success_num",
        color="success_label",
        hover_data=["name", "flight_number", "launchpad", "rocket"],
        title="Launch Outcomes Over Time",
    )
    timeline.update_yaxes(tickvals=[0, 1], ticktext=["Failure", "Success"], title=None)

    return pie, bar, timeline


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8050"))
    app.run_server(host="0.0.0.0", port=port, debug=False)

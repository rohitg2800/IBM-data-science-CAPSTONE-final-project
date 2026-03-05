import os
from pathlib import Path
import pandas as pd
import dash
from dash import dcc, html, Input, Output
import plotly.express as px


# -----------------------------
# Load Dataset
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "output_file.csv"

if not DATA_PATH.exists():
    raise FileNotFoundError("output_file.csv not found in project root")

df = pd.read_csv(DATA_PATH)

# -----------------------------
# Data Cleaning
# -----------------------------

# Convert date column
df["date_utc"] = pd.to_datetime(df["date_utc"], errors="coerce")

# Remove upcoming launches
if "upcoming" in df.columns:
    df = df[df["upcoming"] == False]

# Remove unknown success values
df = df[df["success"].notna()]

# Create labels
df["success_label"] = df["success"].map({True: "Success", False: "Failure"})
df["success_num"] = df["success"].map({True: 1, False: 0})

# Year column
df["year"] = df["date_utc"].dt.year


# -----------------------------
# Dropdown options
# -----------------------------
launchpads = df["launchpad"].unique()

launchpad_options = [{"label": "All Launchpads", "value": "ALL"}]

for lp in launchpads:
    launchpad_options.append({
        "label": lp,
        "value": lp
    })


# -----------------------------
# Initialize Dash
# -----------------------------
app = dash.Dash(__name__)
server = app.server


# -----------------------------
# App Layout
# -----------------------------
app.layout = html.Div(

    style={
        "backgroundColor": "#0e1117",
        "color": "white",
        "minHeight": "100vh",
        "padding": "30px",
        "fontFamily": "Arial"
    },

    children=[

        html.H1(
            "SpaceX Launch Analytics Dashboard",
            style={
                "textAlign": "center",
                "color": "#00d4ff",
                "marginBottom": "30px"
            }
        ),

        html.Div([
            html.Label("Select Launchpad"),

            dcc.Dropdown(
                id="launchpad-dropdown",
                options=launchpad_options,
                value="ALL",
                clearable=False,
                style={"color": "black"}
            )
        ], style={"width": "40%", "margin": "auto"}),

        html.Br(),

        dcc.Graph(id="success-pie-chart"),

        html.Br(),

        dcc.Graph(id="launch-trend-chart"),

        html.Br(),

        dcc.Graph(id="success-timeline-chart")

    ]
)


# -----------------------------
# Callbacks
# -----------------------------
@app.callback(
    Output("success-pie-chart", "figure"),
    Input("launchpad-dropdown", "value")
)
def update_pie(selected_launchpad):

    if selected_launchpad == "ALL":
        data = df
        title = "Overall Launch Success Distribution"
    else:
        data = df[df["launchpad"] == selected_launchpad]
        title = f"Launch Success Distribution ({selected_launchpad})"

    fig = px.pie(
        data,
        names="success_label",
        title=title,
        template="plotly_dark"
    )

    return fig


@app.callback(
    Output("launch-trend-chart", "figure"),
    Input("launchpad-dropdown", "value")
)
def update_trend(selected_launchpad):

    if selected_launchpad == "ALL":
        data = df
    else:
        data = df[df["launchpad"] == selected_launchpad]

    trend = data.groupby("year").size().reset_index(name="launches")

    fig = px.bar(
        trend,
        x="year",
        y="launches",
        title="Launch Frequency Over Time",
        template="plotly_dark"
    )

    return fig


@app.callback(
    Output("success-timeline-chart", "figure"),
    Input("launchpad-dropdown", "value")
)
def update_timeline(selected_launchpad):

    if selected_launchpad == "ALL":
        data = df
    else:
        data = df[df["launchpad"] == selected_launchpad]

    fig = px.scatter(
        data,
        x="date_utc",
        y="success_num",
        color="success_label",
        hover_data=["name", "flight_number"],
        title="Launch Outcomes Over Time",
        template="plotly_dark"
    )

    fig.update_yaxes(
        tickvals=[0,1],
        ticktext=["Failure","Success"]
    )

    return fig


# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8050))

    app.run_server(
        host="0.0.0.0",
        port=port,
        debug=False
    )

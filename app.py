import os
from pathlib import Path
import pandas as pd
import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import requests


# ---------------------------
# Load Launch Dataset
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "output_file.csv"

launch_df = pd.read_csv(DATA_PATH)


# ---------------------------
# Fetch Reference Tables
# ---------------------------
rocket_data = requests.get("https://api.spacexdata.com/v4/rockets").json()
launchpad_data = requests.get("https://api.spacexdata.com/v4/launchpads").json()

rocket_df = pd.DataFrame(rocket_data)[["id", "name"]]
launchpad_df = pd.DataFrame(launchpad_data)[["id", "name"]]

rocket_df = rocket_df.rename(columns={
    "id": "rocket",
    "name": "rocket_name"
})

launchpad_df = launchpad_df.rename(columns={
    "id": "launchpad",
    "name": "launchpad_name"
})


# ---------------------------
# Join Reference Tables
# ---------------------------
launch_df = launch_df.merge(
    rocket_df,
    on="rocket",
    how="left"
)

launch_df = launch_df.merge(
    launchpad_df,
    on="launchpad",
    how="left"
)


# ---------------------------
# Data Cleaning
# ---------------------------
launch_df["date_utc"] = pd.to_datetime(
    launch_df["date_utc"],
    errors="coerce"
)

# remove future launches
if "upcoming" in launch_df.columns:
    launch_df = launch_df[launch_df["upcoming"] == False]

# remove unknown outcomes
launch_df = launch_df[launch_df["success"].notna()]

launch_df["success_label"] = launch_df["success"].map({
    True: "Success",
    False: "Failure"
})

launch_df["year"] = launch_df["date_utc"].dt.year


# ---------------------------
# Metrics
# ---------------------------
total_launches = len(launch_df)
success_rate = round(
    launch_df["success"].mean() * 100,
    2
)

failures = len(
    launch_df[launch_df["success"] == False]
)

launchpads = launch_df["launchpad_name"].nunique()


# ---------------------------
# Dropdown Options
# ---------------------------
launchpad_options = [{"label": "All Launchpads", "value": "ALL"}]

for lp in launch_df["launchpad_name"].unique():
    launchpad_options.append({
        "label": lp,
        "value": lp
    })


# ---------------------------
# Initialize Dash
# ---------------------------
app = dash.Dash(__name__)
server = app.server


# ---------------------------
# Layout
# ---------------------------
app.layout = html.Div(

    style={
        "backgroundColor": "#0e1117",
        "color": "white",
        "minHeight": "100vh",
        "padding": "30px"
    },

    children=[

        html.H1(
            "SpaceX Launch Analytics Dashboard",
            style={
                "textAlign": "center",
                "color": "#00d4ff"
            }
        ),

        html.Br(),

        html.Div([
            html.H3(total_launches),
            html.P("Total Launches")
        ], style={"textAlign":"center"}),

        html.Br(),

        html.Div([
            html.H3(f"{success_rate}%"),
            html.P("Success Rate")
        ], style={"textAlign":"center"}),

        html.Br(),

        html.Div([
            html.H3(failures),
            html.P("Failures")
        ], style={"textAlign":"center"}),

        html.Br(),

        dcc.Dropdown(
            id="launchpad-dropdown",
            options=launchpad_options,
            value="ALL",
            clearable=False,
            style={"color":"black"}
        ),

        html.Br(),

        dcc.Graph(id="success-chart"),

        dcc.Graph(id="year-chart"),

        dcc.Graph(id="launchpad-chart")

    ]
)


# ---------------------------
# Callbacks
# ---------------------------
@app.callback(
    Output("success-chart","figure"),
    Input("launchpad-dropdown","value")
)
def update_success_chart(selected_launchpad):

    if selected_launchpad == "ALL":
        data = launch_df
    else:
        data = launch_df[
            launch_df["launchpad_name"] == selected_launchpad
        ]

    fig = px.pie(
        data,
        names="success_label",
        title="Launch Outcome Distribution",
        template="plotly_dark"
    )

    return fig


@app.callback(
    Output("year-chart","figure"),
    Input("launchpad-dropdown","value")
)
def update_year_chart(selected_launchpad):

    if selected_launchpad == "ALL":
        data = launch_df
    else:
        data = launch_df[
            launch_df["launchpad_name"] == selected_launchpad
        ]

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
    Output("launchpad-chart","figure"),
    Input("launchpad-dropdown","value")
)
def update_launchpad_chart(selected_launchpad):

    data = launch_df.groupby(
        "launchpad_name"
    ).size().reset_index(name="launches")

    fig = px.bar(
        data,
        x="launchpad_name",
        y="launches",
        title="Launch Distribution by Launchpad",
        template="plotly_dark"
    )

    return fig


# ---------------------------
# Run App
# ---------------------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT",8050))

    app.run_server(
        host="0.0.0.0",
        port=port
        debug=false
    )

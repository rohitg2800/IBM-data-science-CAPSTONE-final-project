import os
from pathlib import Path

import pandas as pd
import dash
from dash import dcc, html, Input, Output
import plotly.express as px

# ------------------ 1️⃣ Load the data ------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "spacex_launch_dash.csv"   # adjust if you move it to a sub‑folder

# Optional fallback URL (uncomment if you prefer remote download)
# DATA_URL = "https://raw.githubusercontent.com/plotly/datasets/master/spacex_launch_dash.csv"

def load_dataset():
    """Try local CSV → remote URL → clear error."""
    if DATA_PATH.is_file():
        return pd.read_csv(DATA_PATH)

    # Uncomment the block below to enable remote fallback
    # print("⚡️ Local CSV not found → downloading from", DATA_URL)
    # return pd.read_csv(DATA_URL)

    raise FileNotFoundError(
        f"Dataset not found at {DATA_PATH}. "
        "Make sure the CSV is committed (and not ignored) or enable the remote fallback."
    )

spacex_df = load_dataset()

# ------------------ 2️⃣ Prep constants ------------------
max_payload = spacex_df["Payload Mass (kg)"].max()
min_payload = spacex_df["Payload Mass (kg)"].min()

launch_sites = [{"label": "All Sites", "value": "All Sites"}] + [
    {"label": s, "value": s} for s in spacex_df["Launch Site"].unique()
]

# ------------------ 3️⃣ Build the Dash app ------------------
app = dash.Dash(__name__)
server = app.server  # <-- Gunicorn looks for this

app.layout = html.Div(
    children=[
        html.H1(
            "SpaceX Launch Records Dashboard",
            style={"textAlign": "center", "color": "#503D36", "fontSize": 40},
        ),
        dcc.Dropdown(
            id="site-dropdown",
            options=launch_sites,
            value="All Sites",
            searchable=True,
            clearable=False,
        ),
        html.Br(),
        dcc.Graph(id="success-pie-chart"),
        html.Br(),
        html.P("Payload range (Kg):"),
        dcc.RangeSlider(
            id="payload_slider",
            min=0,
            max=10000,
            step=1000,
            marks={i: {"label": f"{i} Kg"} for i in range(0, 10001, 1000)},
            value=[int(min_payload), int(max_payload)],
        ),
        html.Br(),
        dcc.Graph(id="success-payload-scatter-chart"),
    ]
)

# ------------------ 4️⃣ Callbacks ------------------
@app.callback(
    Output("success-pie-chart", "figure"),
    Input("site-dropdown", "value"),
)
def update_piegraph(site):
    if site == "All Sites":
        data = spacex_df[spacex_df["class"] == 1]
        return px.pie(data, names="Launch Site", title="Total Success Launches by All Sites")
    else:
        data = spacex_df[spacex_df["Launch Site"] == site]
        return px.pie(data, names="class", title=f"Success vs Failed for Site → {site}")


@app.callback(
    Output("success-payload-scatter-chart", "figure"),
    [Input("site-dropdown", "value"), Input("payload_slider", "value")],
)
def update_scattergraph(site, payload_range):
    low, high = payload_range
    if site == "All Sites":
        data = spacex_df
        title = "Correlation Between Payload and Success for All Sites"
    else:
        data = spacex_df[spacex_df["Launch Site"] == site]
        title = f"Correlation Between Payload and Success for Site → {site}"

    in_range = (data["Payload Mass (kg)"] >= low) & (data["Payload Mass (kg)"] <= high)
    return px.scatter(
        data[in_range],
        x="Payload Mass (kg)",
        y="class",
        color="Booster Version Category",
        size="Payload Mass (kg)",
        hover_data=["Payload Mass (kg)"],
        title=title,
    )


# ------------------ 5️⃣ Run locally (Render will use gunicorn) ------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8050"))
    app.run_server(host="0.0.0.0", port=port, debug=False)

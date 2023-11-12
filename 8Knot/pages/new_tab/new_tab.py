from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
import warnings

# import visualization cards
from .visualizations.time_to_first_response import gc_time_to_first_response

warnings.filterwarnings("ignore")

dash.register_page(__name__, path="/new_tab")

layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(gc_time_to_first_response, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
    ],
    fluid=True,
)

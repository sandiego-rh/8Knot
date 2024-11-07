from dash import html, dcc, callback
from dash.dependencies import Input, Output, State
import dash
import dash_bootstrap_components as dbc
import warnings
import dash_mantine_components as dmc
from app import augur
import app

# import visualization cards
from .visualizations.code_languages import gc_code_language
from .visualizations.package_version import gc_package_version
from .visualizations.ossf_scorecard import gc_ossf_scorecard
from .visualizations.repo_general_info import gc_repo_general_info

warnings.filterwarnings("ignore")

dash.register_page(__name__, path="/repo_overview")

layout = dbc.Container(
    [
        html.H1(
            "Search Bar Populated Analysis",
            style={"text-align": "center", "marginBottom": "1%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_code_language, width=5),
                dbc.Col(gc_package_version, width=5),
            ],
            align="center",
            justify="evenly",
            style={"marginBottom": "1%"},
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1("Per Repo Analysis:"),
                    ],
                    width=2,
                ),
                dbc.Col(
                    [
                        dmc.Select(
                            id="repo-info-selection",
                            placeholder="Repo for info section",
                            classNames={"values": "dmc-multiselect-custom"},
                            searchable=True,
                            clearable=True,
                        ),
                    ],
                    width=3,
                ),
            ],
            justify="center",
            align="center",
            style={"marginBottom": "1%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_ossf_scorecard, width=6),
                dbc.Col(gc_repo_general_info, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
    ],
    fluid=True,
)


# callback for populating repo drop down
@callback(
    [
        Output("repo-info-selection", "data"),
        Output("repo-info-selection", "value"),
    ],
    [Input("repo-choices", "data")],
)
def repo_dropdown(repo_ids):
    # array to hold repo_id and git url pairing for dropdown
    data_array = []
    for repo_id in repo_ids:
        entry = {"value": repo_id, "label": app.msoh.repo_id_to_git(repo_id)}
        data_array.append(entry)
    return data_array, repo_ids[0]

from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
import warnings

# import the visualization cards
from .visualizations.commits_over_time import gc_commits_over_time
from .visualizations.issues_over_time import gc_issues_over_time
from .visualizations.issue_staleness import gc_issue_staleness
from .visualizations.pr_staleness import gc_pr_staleness
from .visualizations.pr_over_time import gc_pr_over_time
from .visualizations.cntrib_issue_assignment import gc_cntrib_issue_assignment
from .visualizations.issue_assignment import gc_issue_assignment
from .visualizations.pr_assignment import gc_pr_assignment
from .visualizations.cntrb_pr_assignment import gc_cntrib_pr_assignment
from .visualizations.pr_first_response import gc_pr_first_response
from .visualizations.pr_review_response import gc_pr_review_response
from .visualizations.issue_pr_survival import gc_issue_pr_survival

warnings.filterwarnings("ignore")

dash.register_page(__name__, path="/contributions")

layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(gc_pr_staleness, width=6),
                dbc.Col(gc_pr_over_time, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_cntrib_pr_assignment, width=6),
                dbc.Col(gc_pr_assignment, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_issue_staleness, width=6),
                dbc.Col(gc_issues_over_time, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_cntrib_issue_assignment, width=6),
                dbc.Col(gc_issue_assignment, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_commits_over_time, width=6),
                dbc.Col(gc_pr_first_response, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_pr_review_response, width=6),
                dbc.Col(gc_issue_pr_survival, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
    ],
    fluid=True,
)

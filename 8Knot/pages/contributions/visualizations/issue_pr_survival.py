from dash import html, dcc, callback
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import logging
from dateutil.relativedelta import *  # type: ignore
import plotly.express as px
from pages.utils.graph_utils import get_graph_time_values, color_seq
from queries.issues_query import issues_query as iq
from queries.prs_query import prs_query as prq
from queries.pr_response_query import pr_response_query as prr
import io
from cache_manager.cache_manager import CacheManager as cm
import cache_manager.cache_facade as cf
from pages.utils.job_utils import nodata_graph
import time
import app
import datetime as dt
from dateutil.relativedelta import relativedelta


PAGE = "contributions"
VIZ_ID = "issue-pr-survival"

gc_issue_pr_survival = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Issue & Pull Request Survival Analysis",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """
                            This visualization displays the survival trends of issues and pull requests
                            within a repository. It highlights how long these items typically remain open
                            before they are closed, merged, or addressed (as indicated by the first comment).
                            """
                        ),
                    ],
                    id=f"popover-{PAGE}-{VIZ_ID}",
                    target=f"popover-target-{PAGE}-{VIZ_ID}",
                    placement="top",
                    is_open=False,
                ),
                dcc.Loading(
                    dcc.Graph(id=f"{PAGE}-{VIZ_ID}"),
                ),
                dbc.Form(
                    [
                        dbc.Row(
                            [
                                dbc.Label(
                                    "Date Interval:",
                                    html_for=f"date-interval-{PAGE}-{VIZ_ID}",
                                    width="auto",
                                ),
                                dbc.Col(
                                    dbc.RadioItems(
                                        id=f"date-interval-{PAGE}-{VIZ_ID}",
                                        options=[
                                            {
                                                "label": "Day",
                                                "value": "D",
                                            },
                                            {
                                                "label": "Week",
                                                "value": "W",
                                            },
                                            {"label": "Month", "value": "M"},
                                            {"label": "Year", "value": "Y"},
                                        ],
                                        value="M",
                                        inline=True,
                                    ),
                                    className="me-2",
                                ),
                            ],
                            align="center",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dcc.DatePickerRange(
                                        id=f"date-picker-range-{PAGE}-{VIZ_ID}",
                                        min_date_allowed=dt.date(2005, 1, 1),
                                        max_date_allowed=dt.date.today(),
                                        initial_visible_month=dt.date(dt.date.today().year, 1, 1),
                                        start_date=dt.date(
                                            dt.date.today().year - 2,
                                            dt.date.today().month,
                                            dt.date.today().day,
                                        ),
                                        clearable=True,
                                    ),
                                    width="auto",
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        "About Graph",
                                        id=f"popover-target-{PAGE}-{VIZ_ID}",
                                        color="secondary",
                                        size="sm",
                                    ),
                                    width="auto",
                                    style={"paddingTop": ".5em"},
                                ),
                            ],
                            align="center",
                            justify="between",
                        ),
                    ]
                ),
            ]
        ),
    ],
)
# callback for graph info popover
@callback(
    Output(f"popover-{PAGE}-{VIZ_ID}", "is_open"),
    [Input(f"popover-target-{PAGE}-{VIZ_ID}", "n_clicks")],
    [State(f"popover-{PAGE}-{VIZ_ID}", "is_open")],
)
def toggle_popover(n, is_open):
    if n:
        return not is_open
    return is_open


# callback for issue pr survival graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    [
        Input("repo-choices", "data"),
        Input(f"date-interval-{PAGE}-{VIZ_ID}", "value"),
        Input(f"date-picker-range-{PAGE}-{VIZ_ID}", "start_date"),
        Input(f"date-picker-range-{PAGE}-{VIZ_ID}", "end_date"),
        Input("bot-switch", "value"),
    ],
    background=True,
)
def issue_pr_survival_graph(repolist, interval, start_date, end_date, bot_switch):
    # wait for data to asynchronously download and become available.
    for query_func in [iq, prq]:  # Assuming i, pr, and prr are your query functions
        while not_cached := cf.get_uncached(func_name=query_func.__name__, repolist=repolist):
            logging.warning(f"{VIZ_ID}- WAITING ON DATA TO BECOME AVAILABLE")
            time.sleep(0.5)

    logging.warning(f"{VIZ_ID} - START")
    start = time.perf_counter()

    # GET ALL DATA FROM POSTGRES CACHE
    issues_df = cf.retrieve_from_cache(
        tablename=iq.__name__,
        repolist=repolist,
    )

    prs_df = cf.retrieve_from_cache(
        tablename=prq.__name__,
        repolist=repolist,
    )

    pr_response_df = cf.retrieve_from_cache(
        tablename=prr.__name__,
        repolist=repolist,
    )

    if issues_df.empty and prs_df.empty:
        logging.warning(f"{VIZ_ID} - NO DATA AVAILABLE")
        return nodata_graph

    # remove bot data (for issue and pr first response data)
    if bot_switch:
        pr_response_df = pr_response_df[~pr_response_df["cntrb_id"].isin(app.bots_list)]
        pr_response_df = pr_response_df[~pr_response_df["msg_cntrb_id"].isin(app.bots_list)]

    # function for all data pre processing
    df = process_data(issues_df, prs_df, pr_response_df, interval, start_date, end_date)

    fig = create_figure(df)

    logging.warning(f"{VIZ_ID} - END - {time.perf_counter() - start}")
    return fig


def process_data(
    issues_df: pd.DataFrame, prs_df: pd.DataFrame, pr_response_df: pd.DataFrame, interval, start_date, end_date
):
    # convert to datetime objects
    issues_df["created_at"] = pd.to_datetime(issues_df["created_at"], utc=False)
    issues_df["closed_at"] = pd.to_datetime(issues_df["closed_at"], utc=False)

    prs_df["created_at"] = pd.to_datetime(prs_df["created_at"], utc=False)
    prs_df["closed_at"] = pd.to_datetime(prs_df["closed_at"], utc=False)
    prs_df["merged_at"] = pd.to_datetime(prs_df["merged_at"], utc=False)

    pr_response_df["pr_created_at"] = pd.to_datetime(pr_response_df["pr_created_at"], utc=False)

    # drop messages from the pr creator
    pr_response_df = pr_response_df[pr_response_df["cntrb_id"] != pr_response_df["msg_cntrb_id"]]

    # sort in ascending earlier and only get ealiest value
    pr_response_df = pr_response_df.sort_values(by="msg_timestamp", axis=0, ascending=True)
    pr_response_df = pr_response_df.drop_duplicates(subset="pull_request_id", keep="first")

    # find earliest and latest events
    earliest = min(
        issues_df["created_at"].min(),
        prs_df["created_at"].min(),
        pr_response_df["pr_created_at"].min(),
    )
    latest = max(
        issues_df["closed_at"].max(),
        prs_df["closed_at"].max(),
        prs_df["merged_at"].max(),
        pr_response_df["msg_timestamp"].max(),
    )

    # filter values based on date picker
    if start_date is not None:
        issues_df = issues_df[issues_df["created_at"] >= start_date]
        prs_df = prs_df[prs_df["created_at"] >= start_date]
        pr_response_df = pr_response_df[pr_response_df["pr_created_at"] >= start_date]
        earliest = start_date
    if end_date is not None:
        issues_df = issues_df[issues_df["closed_at"] <= end_date]
        prs_df = prs_df[prs_df["closed_at"] <= end_date]
        prs_df = prs_df[prs_df["merged_at"] <= end_date]
        pr_response_df = pr_response_df[pr_response_df["msg_timestamp"] <= end_date]
        latest = end_date

    # create date range by specified interval
    dates = pd.date_range(start=earliest, end=latest, freq=interval, inclusive="both")

    # df for survival analysis
    df_survival = dates.to_frame(index=False, name="Date")

    # calculate survival probabilities
    df_survival["issue_closed_survival"] = df_survival["Date"].apply(
        lambda date: (
            (
                issues_df[issues_df["created_at"] <= date].shape[0]
                - issues_df[(issues_df["created_at"] <= date) & (issues_df["closed_at"].notnull())].shape[0]
            )
            / issues_df[issues_df["created_at"] <= date].shape[0]
            if issues_df[issues_df["created_at"] <= date].shape[0] > 0
            else 1
        )
    )
    df_survival["pr_merged_survival"] = df_survival["Date"].apply(
        lambda date: (
            (
                prs_df[prs_df["created_at"] <= date].shape[0]
                - prs_df[(prs_df["created_at"] <= date) & (prs_df["merged_at"].notnull())].shape[0]
            )
            / prs_df[prs_df["created_at"] <= date].shape[0]
            if prs_df[prs_df["created_at"] <= date].shape[0] > 0
            else 1
        )
    )
    df_survival["pr_closed_survival"] = df_survival["Date"].apply(
        lambda date: (
            (
                prs_df[prs_df["created_at"] <= date].shape[0]
                - prs_df[(prs_df["created_at"] <= date) & (prs_df["closed_at"].notnull())].shape[0]
            )
            / prs_df[prs_df["created_at"] <= date].shape[0]
            if prs_df[prs_df["created_at"] <= date].shape[0] > 0
            else 1
        )
    )
    df_survival["pr_to_first_comment_survival"] = df_survival["Date"].apply(
        lambda date: (
            (
                pr_response_df[pr_response_df["pr_created_at"] <= date].shape[0]
                - pr_response_df[
                    (pr_response_df["pr_created_at"] <= date) & (pr_response_df["msg_timestamp"].notnull())
                ].shape[0]
            )
            / pr_response_df[pr_response_df["pr_created_at"] <= date].shape[0]
            if pr_response_df[pr_response_df["pr_created_at"] <= date].shape[0] > 0
            else 1
        )
    )
    return df_survival


def create_figure(df: pd.DataFrame):
    fig = go.Figure(
        [
            go.Scatter(
                name="Issue Closed",
                x=df["Date"],
                y=df["issue_closed_survival"],
                mode="lines",
                showlegend=True,
                hovertemplate=("Survival Probability: %{y:.2f}<br>%{x|%b %d, %Y} <extra></extra>"),
                marker=dict(color=color_seq[0]),
            ),
            go.Scatter(
                name="PR Merged",
                x=df["Date"],
                y=df["pr_merged_survival"],
                mode="lines",
                showlegend=True,
                hovertemplate="Survival Probability: %{y:.2f}<br>%{x|%b %d, %Y} <extra></extra>",
                marker=dict(color=color_seq[1]),
            ),
            go.Scatter(
                name="PR Closed",
                x=df["Date"],
                y=df["pr_closed_survival"],
                mode="lines",
                showlegend=True,
                hovertemplate="Survival Probability: %{y:.2f}<br>%{x|%b %d, %Y} <extra></extra>",
                marker=dict(color=color_seq[2]),
            ),
            go.Scatter(
                name="PR to First Comment",
                x=df["Date"],
                y=df["pr_to_first_comment_survival"],
                mode="lines",
                showlegend=True,
                hovertemplate="Survival Probability: %{y:.2f}<br>%{x|%b %d, %Y} <extra></extra>",
                marker=dict(color=color_seq[3]),
            ),
        ]
    )

    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Survival Probability",
        font=dict(size=14),
    )

    return fig

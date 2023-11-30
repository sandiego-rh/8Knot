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
from queries.contributors_query import contributors_query as ctq
import io
from cache_manager.cache_manager import CacheManager as cm
from pages.utils.job_utils import nodata_graph
import time

PAGE = "Group5"
VIZ_ID = "time_to_first_response"

time_to_first_response = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Time to First Response",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """
                            Placeholder
                            """
                        ),
                    ],
                    id=f"popover-{PAGE}-{VIZ_ID}",
                    target=f"popover-target-{PAGE}-{VIZ_ID}",  # needs to be the same as dbc.Button id
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
                                    "Months Until Drifting:",
                                    html_for=f"drifting-months-{PAGE}-{VIZ_ID}",
                                    width={"size": "auto"},
                                ),
                                dbc.Col(
                                    dbc.Input(
                                        id=f"drifting-months-{PAGE}-{VIZ_ID}",
                                        type="number",
                                        min=1,
                                        max=120,
                                        step=1,
                                        value=6,
                                        size="sm",
                                    ),
                                    className="me-2",
                                    width=1,
                                ),
                                dbc.Label(
                                    "Months Until Away:",
                                    html_for=f"away-months-{PAGE}-{VIZ_ID}",
                                    width={"size": "auto"},
                                ),
                                dbc.Col(
                                    dbc.Input(
                                        id=f"away-months-{PAGE}-{VIZ_ID}",
                                        type="number",
                                        min=1,
                                        max=120,
                                        step=1,
                                        value=12,
                                        size="sm",
                                    ),
                                    className="me-2",
                                    width=1,
                                ),
                                dbc.Alert(
                                    children="Please ensure that 'Months Until Drifting' is less than 'Months Until Away'",
                                    id=f"check-alert-{PAGE}-{VIZ_ID}",
                                    dismissable=True,
                                    fade=False,
                                    is_open=False,
                                    color="warning",
                                ),
                            ],
                            align="center",
                        ),
                        dbc.Row(
                            [
                                dbc.Label(
                                    "Date Interval:",
                                    html_for=f"date-interval-{PAGE}-{VIZ_ID}",
                                    width="auto",
                                ),
                                dbc.Col(
                                    [
                                        dbc.RadioItems(
                                            id=f"date-interval-{PAGE}-{VIZ_ID}",
                                            options=[
                                                {"label": "Trend", "value": "D"},
                                                {"label": "Month", "value": "M"},
                                                {"label": "Year", "value": "Y"},
                                            ],
                                            value="M",
                                            inline=True,
                                        ),
                                    ]
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
                        ),
                    ]
                ),
            ]
        )
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


@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    Output(f"check-alert-{PAGE}-{VIZ_ID}", "is_open"),
    [
        Input("repo-choices", "data"),
        Input(f"date-interval-{PAGE}-{VIZ_ID}", "value"),
        Input(f"drifting-months-{PAGE}-{VIZ_ID}", "value"),
        Input(f"away-months-{PAGE}-{VIZ_ID}", "value"),
    ],
    background=True,
)
def active_drifting_contributors_graph(repolist, interval, drift_interval, away_interval):
    # conditional for the intervals to be valid options
    if drift_interval is None or away_interval is None:
        return dash.no_update, dash.no_update

    if drift_interval > away_interval:
        return dash.no_update, True

    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=ctq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=ctq, repos=repolist)

    logging.warning(f"ACTIVE_DRIFTING_CONTRIBUTOR_GROWTH_VIZ - START")
    start = time.perf_counter()

    # test if there is data
    if df.empty:
        logging.warning("PULL REQUEST STALENESS - NO DATA AVAILABLE")
        return nodata_graph, False

    # function for all data pre processing
    df_status = process_data(df, interval, drift_interval, away_interval)

    fig = create_figure(df_status, interval)

    logging.warning(f"ACTIVE_DRIFTING_CONTRIBUTOR_GROWTH_VIZ - END - {time.perf_counter() - start}")
    return fig, False


def process_data(df: pd.DataFrame, interval, drift_interval, away_interval):
    # convert to datetime objects with consistent column name
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    df.rename(columns={"created_at": "created"}, inplace=True)

    # order from beginning of time to most recent
    df = df.sort_values("created", axis=0, ascending=True)

    # first and last elements of the dataframe are the
    # earliest and latest events respectively
    earliest, latest = df["created"].min(), df["created"].max()

    # beginning to the end of time by the specified interval
    dates = pd.date_range(start=earliest, end=latest, freq=interval, inclusive="both")

    # df for active, driving, and away contributors for time interval
    df_status = dates.to_frame(index=False, name="Date")

    # dynamically apply the function to all dates defined in the date_range to create df_status
    df_status["Active"], df_status["Drifting"], df_status["Away"] = zip(
        *df_status.apply(
            lambda row: get_active_drifting_away_up_to(df, row.Date, drift_interval, away_interval),
            axis=1,
        )
    )

    # formatting for graph generation
    if interval == "M":
        df_status["Date"] = df_status["Date"].dt.strftime("%Y-%m")
    elif interval == "Y":
        df_status["Date"] = df_status["Date"].dt.year

    return df_status


def create_figure(df_final, threshold, step_size):
    # create custom data to update the hovertemplate with the action type and start and end dates of a given time window in addition to the lottery factor
    # make a nested list of plural action types so that it is gramatically correct in the updated hover info eg. Commit -> Commits and PR Opened -> PRs Opened
    action_types = [
        [action_type[:2] + "s" + action_type[2:]] * len(df_final)
        if action_type == "PR Opened"
        else [action_type[:5] + "s" + action_type[5:]] * len(df_final)
        if action_type == "Issue Opened" or action_type == "Issue Closed"
        else [action_type + "s"] * len(df_final)
        for action_type in df_final.columns[2:]
    ]
    time_window = list(
        df_final["period_from"].dt.strftime("%b %d, %Y") + " - " + df_final["period_to"].dt.strftime("%b %d, %Y")
    )
    customdata = np.stack(([threshold] * len(df_final), time_window), axis=-1)

    # create plotly express line graph
    fig = go.Figure(
        [
            go.Scatter(
                name="Commit",
                x=df_final["period_from"],
                y=df_final["Commit"],
                text=action_types[0],
                customdata=customdata,
                mode="lines",
                showlegend=True,
                marker=dict(color=color_seq[0]),
            ),
            go.Scatter(
                name="Issue Opened",
                x=df_final["period_from"],
                y=df_final["Issue Opened"],
                text=action_types[1],
                customdata=customdata,
                mode="lines",
                showlegend=False,
                marker=dict(color=color_seq[1]),
            ),
            go.Scatter(
                name="Issue Comment",
                x=df_final["period_from"],
                y=df_final["Issue Comment"],
                text=action_types[2],
                customdata=customdata,
                mode="lines",
                showlegend=False,
                marker=dict(color=color_seq[2]),
            ),
            go.Scatter(
                name="Issue Closed",
                x=df_final["period_from"],
                y=df_final["Issue Closed"],
                text=action_types[3],
                customdata=customdata,
                mode="lines",
                showlegend=False,
                marker=dict(color=color_seq[3]),
            ),
            go.Scatter(
                name="PR Opened",
                x=df_final["period_from"],
                y=df_final["PR Opened"],
                text=action_types[4],
                customdata=customdata,
                mode="lines",
                showlegend=False,
                marker=dict(color=color_seq[4]),
            ),
            go.Scatter(
                name="PR Comment",
                x=df_final["period_from"],
                y=df_final["PR Comment"],
                text=action_types[5],
                customdata=customdata,
                mode="lines",
                showlegend=False,
                marker=dict(color=color_seq[5]),
            ),
            go.Scatter(
                name="PR Review",
                x=df_final["period_from"],
                y=df_final["PR Review"],
                text=action_types[6],
                customdata=customdata,
                mode="lines",
                showlegend=False,
                marker=dict(color=color_seq[0]),
            ),
        ],
    )

def get_active_drifting_away_up_to(df, date, drift_interval, away_interval):
    # drop rows that are more recent than the date limit
    df_lim = df[df["created"] <= date]

    # keep more recent contribution per ID
    df_lim = df_lim.drop_duplicates(subset="cntrb_id", keep="last")

    # time difference, drifting_months before the threshold date
    drift_mos = date - relativedelta(months=+drift_interval)

    # time difference, away_months before the threshold date
    away_mos = date - relativedelta(months=+away_interval)

    # number of total contributors up until date
    numTotal = df_lim.shape[0]

    # number of 'active' contributors, people with contributions before the drift time
    numActive = df_lim[df_lim["created"] >= drift_mos].shape[0]

    # set of contributions that are before the away time
    drifting = df_lim[df_lim["created"] > away_mos]

    # number of the set of contributions that are after the drift time, but before away
    numDrifting = drifting[drifting["created"] < drift_mos].shape[0]

    # difference of the total to get the away value
    numAway = numTotal - (numActive + numDrifting)

    return [numActive, numDrifting, numAway]
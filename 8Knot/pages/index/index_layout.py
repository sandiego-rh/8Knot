from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import app
from app import augur
import os
import logging
import _multiselect

# if param doesn't exist, default to False. Otherwise, use the param's booly value.
# this determines if the log in option will be shown or not
if os.getenv("AUGUR_LOGIN_ENABLED", "False") == "True":
    logging.warning("LOGIN ENABLED")
    login_navbar = [
        dbc.Row(
            [
                dbc.Col(
                    dbc.Nav(
                        [
                            dcc.Loading(
                                children=[
                                    html.Div(
                                        id="nav-login-container",
                                        children=[],
                                    ),
                                ]
                            ),
                            dbc.NavItem(
                                dbc.NavLink("Refresh Groups", id="refresh-button", disabled=True),
                            ),
                            dbc.NavItem(
                                dbc.NavLink(
                                    "Manage Groups",
                                    id="manage-group-button",
                                    disabled=True,
                                    href=f"{augur.user_account_endpoint}?section=tracker",
                                    external_link="True",
                                    target="_blank",
                                ),
                            ),
                            dbc.NavItem(
                                dbc.NavLink(
                                    "Log out",
                                    id="logout-button",
                                    disabled=True,
                                    href="/logout/",
                                    external_link=True,
                                ),
                            ),
                            dbc.Popover(
                                children="Login Failed",
                                body=True,
                                id="login-popover",
                                is_open=False,
                                placement="bottom-end",
                                target="nav-dropdown",
                            ),
                        ]
                    )
                )
            ],
            align="center",
        ),
    ]
else:
    logging.warning("LOGIN DISABLED")
    login_navbar = [html.Div()]

# navbar for top of screen
navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Img(
                                src=dash.get_asset_url("8knot-logo-vertical.png"),
                                height="40px",
                            ),
                            dbc.NavbarBrand(
                                "8Knot",
                                id="navbar-title",
                                className="ms-2",
                            ),
                        ],
                        width={"size": "auto"},
                    ),
                    dbc.Col(
                        [
                            dbc.Nav(
                                [
                                    dbc.NavLink("Welcome", href="/", active="exact"),
                                    dbc.NavLink(
                                        "Repo Overview",
                                        href="/repo_overview",
                                        active="exact",
                                    ),
                                    dbc.NavLink(
                                        "Contributions",
                                        href="/contributions",
                                        active="exact",
                                    ),
                                    dbc.DropdownMenu(
                                        [
                                            dbc.DropdownMenuItem(
                                                "Behavior",
                                                href="/contributors/behavior",
                                            ),
                                            dbc.DropdownMenuItem(
                                                "Contribution Types",
                                                href="/contributors/contribution_types",
                                            ),
                                        ],
                                        label="Contributors",
                                        nav=True,
                                    ),
                                    dbc.NavLink(
                                        "Affiliation",
                                        href="/affiliation",
                                        active="exact",
                                    ),
                                    dbc.NavLink("CHAOSS", href="/chaoss", active="exact"),
                                    dbc.NavLink("Codebase", href="/codebase", active="exact"),
                                    dbc.NavLink("Info", href="/info", active="exact"),
                                ],
                                navbar=True,
                            )
                        ],
                        width={"size": "auto"},
                    ),
                ],
                align="center",
                className="g-0",
                justify="start",
            ),
            # packaged as a list to make linter happy-
            # it keeps making the login_navpar page-wrap as a tuple,
            # so I wrapped it in a list.
            login_navbar[0],
        ],
        fluid=True,
    ),
    color="primary",
    dark=True,
    sticky="top",
)

navbar_bottom = dbc.NavbarSimple(
    children=[
        dbc.NavItem(
            dbc.NavLink(
                "Visualization request",
                href="https://github.com/oss-aspen/8Knot/issues/new?assignees=&labels=enhancement%2Cvisualization&template=visualizations.md",
                external_link="True",
                target="_blank",
            )
        ),
        dbc.NavItem(
            dbc.NavLink(
                "Bug",
                href="https://github.com/oss-aspen/8Knot/issues/new?assignees=&labels=bug&template=bug_report.md",
                external_link="True",
                target="_blank",
            )
        ),
        dbc.NavItem(
            dbc.NavLink(
                "Repo/Org Request",
                href="https://github.com/oss-aspen/8Knot/issues/new?assignees=&labels=augur&template=augur_load.md",
                external_link="True",
                target="_blank",
            )
        ),
    ],
    brand="",
    brand_href="#",
    color="primary",
    dark=True,
    fluid=True,
)

search_bar = html.Div(
    [
        dbc.Stack(
            [
                html.Div(
                    [
                        dmc.MultiSelect(
                            id="projects",
                            searchable=True,
                            placeholder="Please select a repository or an organization.",
                            clearable=True,
                            nothingFound="No repositories matching your input!",
                            variant="filled",
                            debounce=0.5,
                            data=app.msoh.all_options(),
                            value=app.msoh.initial_option(),
                            limit=100,
                            style={"fontSize": 16},
                        ),
                        dbc.Alert(
                            children='Please ensure that your spelling is correct. \
                                If your selection definitely isn\'t present, please request that \
                                it be loaded using the help button "REPO/ORG Request" \
                                in the bottom right corner of the screen.',
                            id="help-alert",
                            dismissable=True,
                            fade=True,
                            is_open=False,
                            color="info",
                        ),
                        dbc.Alert(
                            children="List of repos",
                            id="repo-list-alert",
                            dismissable=True,
                            fade=True,
                            is_open=False,
                            color="light",
                            # if number of repos is large, render as a scrolling window
                            style={"overflow-y": "scroll", "max-height": "440px"},
                        ),
                    ],
                    style={
                        "width": "50%",
                        "paddingRight": "10px",
                    },
                ),
                dbc.Button(
                    "Search",
                    id="search",
                    n_clicks=0,
                    size="md",
                ),
                dbc.Button(
                    "Help",
                    id="search-help",
                    n_clicks=0,
                    size="md",
                ),
                dbc.Button(
                    "Repo List",
                    id="repo-list-button",
                    n_clicks=0,
                    size="md",
                ),
                dbc.Switch(
                    id="bot-switch",
                    label="GitHub Bot Filter",
                    value=True,
                    input_class_name="botlist-filter-switch",
                    style={"fontSize": 18},
                ),
            ],
            direction="horizontal",
            style={
                "width": "70%",
            },
        ),
    ]
)

layout = dbc.Container(
    [
        # componets to store data from queries
        dcc.Store(id="repo-choices", storage_type="session", data=[]),
        # components to store job-ids for the worker queue
        dcc.Store(id="job-ids", storage_type="session", data=[]),
        dcc.Store(id="user-group-loading-signal", data="", storage_type="memory"),
        dcc.Location(id="url"),
        navbar,
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label(
                            "Select GitHub repos or orgs:",
                            html_for="projects",
                            width="auto",
                            size="lg",
                        ),
                        search_bar,
                        dcc.Loading(
                            children=[html.Div(id="results-output-container", className="mb-4")],
                            color="#119DFF",
                            type="dot",
                            fullscreen=True,
                        ),
                        dcc.Loading(
                            dbc.Badge(
                                children="Data Loaded",
                                id="data-badge",
                                color="#436755",
                                className="me-1",
                                style={"marginBottom": ".5%"},
                                text_color="dark",
                            ),
                            type="cube",
                            color="#436755",
                        ),
                        # where our page will be rendered
                        dash.page_container,
                    ],
                ),
            ],
            justify="start",
        ),
        navbar_bottom,
    ],
    fluid=True,
    className="dbc",
)

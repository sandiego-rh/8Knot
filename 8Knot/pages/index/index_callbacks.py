from datetime import datetime, timedelta
import re
import os
import time
import logging
import json
from celery.result import AsyncResult
import dash_bootstrap_components as dbc
import dash
from dash import callback
from dash.dependencies import Input, Output, State
from app import augur
import app
from flask_login import current_user
from cache_manager.cache_manager import CacheManager as cm
import cache_manager.cache_facade as cf
from queries.issues_query import issues_query as iq
from queries.commits_query import commits_query as cq
from queries.contributors_query import contributors_query as cnq
from queries.prs_query import prs_query as prq
from queries.affiliation_query import affiliation_query as aq
from queries.pr_assignee_query import pr_assignee_query as praq
from queries.issue_assignee_query import issue_assignee_query as iaq
from queries.user_groups_query import user_groups_query as ugq
from queries.pr_response_query import pr_response_query as prr
from queries.cntrb_per_file_query import cntrb_per_file_query as cpfq
from queries.repo_files_query import repo_files_query as rfq
from queries.pr_files_query import pr_file_query as prfq
from queries.repo_languages_query import repo_languages_query as rlq
from queries.package_version_query import package_version_query as pvq
from queries.repo_releases_query import repo_releases_query as rrq
from queries.ossf_score_query import ossf_score_query as osq
from queries.repo_info_query import repo_info_query as riq
import redis
import flask


# list of queries to be run
QUERIES = [
    iq,
    cq,
    cnq,
    prq,
    aq,
    iaq,
    praq,
    prr,
    cpfq,
    rfq,
    prfq,
    rlq,
    pvq,
    rrq,
    osq,
    riq,
]


# check if login has been enabled in config
login_enabled = os.getenv("AUGUR_LOGIN_ENABLED", "False") == "True"


@callback(
    [Output("user-group-loading-signal", "data")],
    [Input("url", "href"), Input("refresh-button", "n_clicks")],
)
def kick_off_group_collection(url, n_clicks):
    """Schedules a Celery task to collect user groups.
    Sends a message via localStorage that will kick off a background callback
    which waits for the Celery task to finish.

    if refresh-groups clicked, forces group reload.

    Args:
        url (str): browser page URL
        n_clicks (_type_): number 'refresh_groups' button has been clicked.

    Returns:
        int: ID of Celery task that has started for group collection.
    """
    if current_user.is_authenticated:
        user_id = current_user.get_id()
        users_cache = redis.StrictRedis(
            host=os.getenv("REDIS_SERVICE_USERS_HOST", "redis-users"),
            port=6379,
            password=os.getenv("REDIS_PASSWORD", ""),
        )
        try:
            users_cache.ping()
        except redis.exceptions.ConnectionError:
            logging.error("GROUP-COLLECTION: Could not connect to users-cache.")
            return dash.no_update

        # TODO: check how old groups are. If they're pretty old (threshold tbd) then requery

        # check if groups are not already cached, or if the refresh-button was pressed
        if not users_cache.exists(f"{user_id}_groups") or (dash.ctx.triggered_id == "refresh-button"):
            # kick off celery task to collect groups
            # on query worker queue,
            return [ugq.apply_async(args=[user_id], queue="data").id]
        else:
            return dash.no_update
    else:
        # user anonymous
        return dash.no_update


@callback(
    [
        Output("nav-login-container", "children"),
        Output("login-popover", "is_open"),
        Output("refresh-button", "disabled"),
        Output("logout-button", "disabled"),
        Output("manage-group-button", "disabled"),
    ],
    Input("url", "href"),
)
def login_username_button(url):
    """Sets logged-in-status component in top left of page.

    If a non-null username is known then we're logged in so we provide
    the user a button to go to Augur. Otherwise, we redirect them to login.

    This callback also sets a login_failure popover depending on whether
    a requested login succeeded.

    Args:
        username (str | None): Username of user or None
        login_succeeded (bool): Error enabled if login failed.

    Returns:
        _type_: _description_
    """

    navlink = [
        dbc.NavLink(
            "Augur log in/sign up",
            href="/login/",
            id="login-navlink",
            active=True,
            # communicating with the underlying Flask server
            external_link=True,
        ),
    ]

    buttons_disabled = True
    login_succeeded = True

    if current_user:
        if current_user.is_authenticated:
            logging.warning(f"LOGINBUTTON: USER LOGGED IN {current_user}")
            # TODO: implement more permanent interface
            users_cache = redis.StrictRedis(
                host=os.getenv("REDIS_SERVICE_USERS_HOST", "redis-users"),
                port=6379,
                password=os.getenv("REDIS_PASSWORD", ""),
            )
            try:
                users_cache.ping()
            except redis.exceptions.ConnectionError:
                logging.error("USERNAME: Could not connect to users-cache.")
                return dash.no_update

            user_id = current_user.get_id()
            user_info = json.loads(users_cache.get(user_id))

            navlink = [
                dbc.NavItem(
                    dbc.NavLink(
                        f"{user_info['username']}",
                        href=augur.user_account_endpoint,
                        id="login-navlink",
                        disabled=True,
                    ),
                ),
            ]
            buttons_disabled = False

    return (
        navlink,
        not login_succeeded,
        buttons_disabled,
        buttons_disabled,
        buttons_disabled,
    )


# @callback(
#     [Output("projects", "data")],
#     [Input("projects", "searchValue")],
#     [
#         State("projects", "value"),
#     ],
# )
# def dynamic_multiselect_options(user_in: str, selections):
#     """
#     Ref: https://dash.plotly.com/dash-core-components/dropdown#dynamic-options

#     For all of the possible repo's / orgs, check if the substring currently
#     being searched is in the repo's name or if the repo / org name is
#     in the current list of states selected. Add it to the list if it matches
#     either of the options.
#     """

#     if not user_in:
#         return dash.no_update

#     options = augur.get_multiselect_options().copy()

#     if current_user.is_authenticated:
#         logging.warning(f"LOGINBUTTON: USER LOGGED IN {current_user}")
#         # TODO: implement more permanent interface
#         users_cache = redis.StrictRedis(
#             host=os.getenv("REDIS_SERVICE_USERS_HOST", "redis-users"),
#             port=6379,
#             password=os.getenv("REDIS_PASSWORD", ""),
#             decode_responses=True,
#         )
#         try:
#             users_cache.ping()
#         except redis.exceptions.ConnectionError:
#             logging.error("MULTISELECT: Could not connect to users-cache.")
#             return dash.no_update

#         try:
#             if users_cache.exists(f"{current_user.get_id()}_group_options"):
#                 options = options + json.loads(users_cache.get(f"{current_user.get_id()}_group_options"))
#         except redis.exceptions.ConnectionError:
#             logging.error("Searchbar: couldn't connect to Redis for user group options.")

#     # if the number of options changes then we're
#     # adding AUGUR_ entries somewhere.

#     if selections is None:
#         selections = []

#     # match lowercase inputs with lowercase possible values
#     opts = [i for i in options if user_in.lower() in i["label"]]

#     # sort matches by length
#     opts = sorted(opts, key=lambda v: len(v["label"]))

#     # always include the previous selections from the searchbar to avoid
#     # those values being clobbered when we truncate the total length.
#     # arbitrarily 'small' number of matches returned..
#     if len(opts) < 100:
#         return [opts + [v for v in options if v["value"] in selections]]

#     else:
#         return [opts[:100] + [v for v in options if v["value"] in selections]]


# callback for repo selections to feed into visualization call backs
# @callback(
#     [Output("results-output-container", "children"), Output("repo-choices", "data")],
#     [
#         Input("search", "n_clicks"),
#         State("projects", "value"),
#     ],
# )
# def multiselect_values_to_repo_ids(n_clicks, user_vals):
#     if not user_vals:
#         logging.warning("NOTHING SELECTED IN SEARCH BAR")
#         raise dash.exceptions.PreventUpdate

#     # individual repo numbers
#     repos = [r for r in user_vals if isinstance(r, int)]
#     logging.warning(f"REPOS: {repos}")

#     # names of augur groups or orgs
#     names = [n for n in user_vals if isinstance(n, str)]

#     org_repos = [augur.org_to_repos(o) for o in names if augur.is_org(o)]
#     # flatten list repo_ids in orgs to 1D
#     org_repos = [v for l in org_repos for v in l]
#     logging.warning(f"ORG_REPOS: {org_repos}")

#     user_groups = []
#     if current_user.is_authenticated:
#         logging.warning(f"LOGINBUTTON: USER LOGGED IN {current_user}")
#         # TODO: implement more permanent interface
#         users_cache = redis.StrictRedis(
#             host=os.getenv("REDIS_SERVICE_USERS_HOST", "redis-users"),
#             port=6379,
#             password=os.getenv("REDIS_PASSWORD", ""),
#             decode_responses=True,
#         )
#         try:
#             users_cache.ping()
#         except redis.exceptions.ConnectionError:
#             logging.error("SEARCH-BUTTON: Could not connect to users-cache.")
#             return dash.no_update

#         try:
#             if users_cache.exists(f"{current_user.get_id()}_groups"):
#                 user_groups = json.loads(
#                     users_cache.get(f"{current_user.get_id()}_groups")
#                 )
#                 logging.warning(f"USERS Groups: {type(user_groups)}, {user_groups}")
#         except redis.exceptions.ConnectionError:
#             logging.error(
#                 "Searchbar: couldn't connect to Redis for user group options."
#             )

#     group_repos = [user_groups[g] for g in names if not augur.is_org(g)]
#     # flatten list repo_ids in orgs to 1D
#     group_repos = [v for l in group_repos for v in l]
#     logging.warning(f"GROUP_REPOS: {group_repos}")

#     # only unique repo ids
#     all_repo_ids = list(set().union(*[repos, org_repos, group_repos]))
#     logging.warning(f"SELECTED_REPOS: {all_repo_ids}")

#     return "", all_repo_ids


# callback for repo selections to feed into visualization call backs
@callback(
    [Output("results-output-container", "children"), Output("repo-choices", "data")],
    [
        Input("search", "n_clicks"),
        State("projects", "value"),
    ],
)
def searchvals_to_vizzes(n_clicks, repos):
    if not repos:
        logging.warning("NOTHING SELECTED IN SEARCH BAR")
        raise dash.exceptions.PreventUpdate

    # gives a list of repo_ids
    repo_ids = [v["repo_id"] for v in repos if v["type"] == "repo"]

    # will give a list-of-lists
    org_ids = [app.msoh.org_map[v["org_id"]] for v in repos if v["type"] == "org"]

    # will get a list of unique repo_ids
    all_ids = list(set().union(repo_ids, *org_ids))

    logging.warning(f"NUM SELECTED REPOS: {len(all_ids)}")
    return "", all_ids


@callback(
    Output("help-alert", "is_open"),
    Input("search-help", "n_clicks"),
    State("help-alert", "is_open"),
)
def show_help_alert(n_clicks, openness):
    """Sets the 'open' state of a help message
    for the search bar to encourage users to check
    their spelling and to ask for data to be loaded
    if not available.

    Args:
        n_clicks (int): number of times 'help' button clicked.
        openness (boolean): whether help alert is currently open.

    Returns:
        dash.no_update | boolean: whether the help alert should be open.
    """
    if n_clicks == 0:
        return dash.no_update
    # switch the openness parameter, allows button to also
    # dismiss the Alert.
    return not openness


@callback(
    [Output("repo-list-alert", "is_open"), Output("repo-list-alert", "children")],
    [Input("repo-list-button", "n_clicks")],
    [State("help-alert", "is_open"), State("repo-choices", "data")],
)
def show_help_alert(n_clicks, openness, repo_ids):
    """Sets the 'open' state of a help message
    for the search bar to encourage users to check
    their spelling and to ask for data to be loaded
    if not available.
    Args:
        n_clicks (int): number of times 'help' button clicked.
        openness (boolean): whether help alert is currently open.
    Returns:
        dash.no_update | boolean: whether the help alert should be open.
    """
    print(repo_ids)
    url_list = [app.msoh.repo_id_to_git(i) for i in repo_ids]

    if n_clicks == 0:
        return dash.no_update, str(url_list)
    # switch the openness parameter, allows button to also
    # dismiss the Alert.
    return not openness, str(url_list)


@callback(
    [Output("data-badge", "children"), Output("data-badge", "color")],
    Input("job-ids", "data"),
    background=True,
)
def wait_queries(job_ids):
    # TODO add docstring to function

    jobs = [AsyncResult(j_id) for j_id in job_ids]

    # default 'result_expires' for celery config is 86400 seconds.
    # so we don't have to check if the jobs exist. if this tasks
    # is enqueued 24 hours after the query-worker tasks finish
    # then we have a big problem. However, we should 'forget' all
    # results before we exit.

    while True:
        logging.warning([(j.name, j.status) for j in jobs])

        # jobs are either all ready
        if all(j.successful() for j in jobs):
            logging.warning([(j.name, j.status) for j in jobs])
            jobs = [j.forget() for j in jobs]
            return "Data Ready", "#b5b683"

        # or one of them has failed
        if any(j.failed() for j in jobs):
            # if a job fails, we need to wait for the others to finish before
            # we can 'forget' them. otherwise to-be-successful jobs will always
            # be forgotten if one fails.

            # tasks need to have either failed or succeeded before being forgotten.
            while True:
                num_succeeded = [j.successful() for j in jobs].count(True)
                num_failed = [j.failed() for j in jobs].count(True)
                num_total = num_failed + num_succeeded

                if num_total == len(jobs):
                    break

                time.sleep(4.0)

            jobs = [j.forget() for j in jobs]
            return "Data Incomplete- Retry", "danger"

        # pause to let something change
        time.sleep(2.0)


@callback(
    Output("job-ids", "data"),
    Input("repo-choices", "data"),
)
def run_queries(repos):
    """
    Executes queries defined in /queries against Augur
    instance for input Repos; caches results in Postgres.

    Args:
        repos ([int]): repositories we collect data for.
    """

    # cache manager object
    cache = cm()

    # list of queries to process
    funcs = QUERIES

    # list of job promises
    jobs = []

    for f in funcs:
        # only download repos that aren't currently in cache
        not_ready = cf.get_uncached(f.__name__, repos)
        if len(not_ready) == 0:
            logging.warning(f"{f.__name__} - NO DISPATCH - ALL REPOS IN CACHE")
            continue

        # add job to queue
        j = f.apply_async(args=[not_ready], queue="data")

        # add job promise to local promise list
        jobs.append(j)

    return [j.id for j in jobs]

"""
    README -- Organization of Callback Functions

    In an effort to compartmentalize our development where possible, all callbacks directly relating
    to pages in our application are in their own files.

    For instance, this file contains the layout logic for the index page of our app-
    this page serves all other paths by providing the searchbar, page routing faculties,
    and data storage objects that the other pages in our app use.

    Having laid out the HTML-like organization of this page, we write the callbacks for this page in
    the neighbor 'app_callbacks.py' file.
"""
import os
import sys
import logging
import dash
import sqlalchemy as salc
from sqlalchemy.exc import SQLAlchemyError
import plotly.io as plt_io
import dash_bootstrap_components as dbc
import dash_bootstrap_templates as dbt
from db_manager.augur_manager import AugurManager
import _login
import _multiselect
from _celery import celery_app, celery_manager
import _bots as bots
import pandas as pd
import models

logging.basicConfig(format="%(asctime)s %(levelname)-8s %(message)s", level=logging.INFO)


"""CREATE DATABASE ACCESS OBJECT AND CACHE SEARCH OPTIONS"""
use_oauth = os.getenv("AUGUR_LOGIN_ENABLED", "False") == "True"
try:
    # create augur manager object. init fails if
    # necessary environment variables aren't available.
    augur = AugurManager(handles_oauth=use_oauth)

    # create engine. fails if test connection to DB fails.
    engine = augur.get_engine()

except KeyError:
    sys.exit(1)
except SQLAlchemyError:
    sys.exit(1)


# grab list of projects and orgs from Augur database.
# augur.multiselect_startup()
msoh = _multiselect.MSOptionsHandler(models.engine)


"""IMPORT AFTER GLOBAL VARIABLES SET"""
import pages.index.index_callbacks as index_callbacks


"""SET STYLING FOR APPLICATION"""
dbt.load_figure_template(["sandstone", "minty", "slate"])

# stylesheet with the .dbc class, this is a complement to the dash bootstrap templates, credit AnnMarieW
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"

# making custom plotly template with custom colors on top of the slate design template
plt_io.templates["custom_dark"] = plt_io.templates["slate"]
plt_io.templates["custom_dark"]["layout"]["colorway"] = [
    "#B5B682",  # sage
    "#c0bc5d",  # citron (yellow-ish)
    "#6C8975",  # reseda green
    "#D9AE8E",  # buff (pale pink)
    "#FFBF51",  # xanthous (orange-ish)
    "#C7A5A5",  # rosy brown
]

plt_io.templates.default = "custom_dark"


"""CREATE APPLICATION"""
app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.SLATE, dbc_css, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    background_callback_manager=celery_manager,
)

"""CONFIGURE FLASK-LOGIN"""
server = app.server
server = _login.configure_server_login(server)


"""DASH PAGES LAYOUT"""
# layout of the app stored in the app_layout file, must be imported after the app is initiated
from pages.index.index_layout import layout

app.layout = layout

"""DASH STARTUP PARAMETERS"""

if os.getenv("8KNOT_DEBUG", "False") == "True":
    app.enable_dev_tools(dev_tools_ui=True, dev_tools_hot_reload=False)

"""GITHUB BOTS LIST"""
bots_list = bots.get_bots_list()

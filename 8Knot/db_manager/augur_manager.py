"""
    Imports
"""
import pandas as pd
import numpy as np
import sqlalchemy as salc
import os
import logging
import sys
import requests
from sqlalchemy.exc import SQLAlchemyError


class AugurManager:
    """
    Handles connection and queries to Augur database.

    Attributes:
    -----------
        engine : _engine.Engine instance
            SQLAlchemy engine with credentials to connect to Augur database.

        user : str
            User credential to Augur database.

        password: str
            Password credential to Augur database.

        host : str
            Host credential to Augur database.

        port : str
            Port credential to Augur database.
            Which port on the server machine we'll target.

        database : str
            Database credential to Augur database.
            Which of the available databases on the server machine we'll target.

        schema : str
            Schema credential to Augur database.
            The target schema of the database we want to access.

    Methods:
    --------
        get_engine():
            Connects to Augur databse with supplied credentials and
            returns engine object.

        run_query(query_string):
            Runs a SQL-query against Augur database and returns resulting
            Pandas dataframe.
    """

    def __init__(self, handles_oauth=False):
        # sqlalchemy engine object
        self.engine = None
        self.initial_search_option = None

        # db connection credentials
        # if any are unavailable, raise error.
        try:
            self.user = os.environ["AUGUR_USERNAME"]
            self.password = os.environ["AUGUR_PASSWORD"]
            self.host = os.environ["AUGUR_HOST"]
            self.port = os.environ["AUGUR_PORT"]
            self.database = os.environ["AUGUR_DATABASE"]
            self.schema = os.environ["AUGUR_SCHEMA"]
        except KeyError as ke:
            logging.critical(f"AUGUR: Database credentials incomplete: {ke}")
            raise KeyError(ke)

        # oauth endpoints have to be intact to proceed
        if handles_oauth:
            try:
                # application credentials
                self.app_id = os.environ["AUGUR_APP_ID"]
                self.client_secret = os.environ["AUGUR_CLIENT_SECRET"]

                # user-level endpoints
                self.session_generate_endpoint = os.environ["AUGUR_SESSION_GENERATE_ENDPOINT"]
                self.user_groups_endpoint = os.environ["AUGUR_USER_GROUPS_ENDPOINT"]
                self.user_account_endpoint = os.environ["AUGUR_USER_ACCOUNT_ENDPOINT"]
                self.user_auth_endpoint = os.environ["AUGUR_USER_AUTH_ENDPOINT"]

                # admin-level endpoints
                self.admin_name_endpoint = os.environ["AUGUR_ADMIN_NAME_ENDPOINT"]
                self.admin_group_names_endpoint = os.environ["AUGUR_ADMIN_GROUP_NAMES_ENDPOINT"]
                self.admin_groups_endpoint = os.environ["AUGUR_ADMIN_GROUPS_ENDPOINT"]
            except KeyError as ke:
                logging.critical(f"AUGUR: Oauth endpoints incomplete: {ke}")

    def get_engine(self):
        """
        Creates _engine.Engine object connected to our Augur database.

        Returns:
        --------
            _engine.Engine: SQLAlchemy engine object.
        """

        # return engine immediately if it already exists
        if self.engine:
            return self.engine

        database_connection_string = "postgresql+psycopg2://{}:{}@{}:{}/{}".format(
            self.user, self.password, self.host, self.port, self.database
        )

        engine = salc.create_engine(
            database_connection_string,
            connect_args={"options": "-csearch_path={}".format(self.schema)},
            pool_pre_ping=True,
        )

        # verify that engine works
        try:
            # context managed connect, closes automatically
            with engine.connect() as conn:
                logging.warning("AUGUR: Connection to DB succeeded")

            self.engine = engine

        except SQLAlchemyError as err:
            logging.error(f"AUGUR: DB couldn't connect: {err.__cause__}")
            raise SQLAlchemyError(err)

        return engine

    def run_query(self, query_string: str) -> pd.DataFrame:
        """
        Runs SQL query against our Augur database.

        Args:
        -----
            query_string (str): SQL query to run.

        Returns:
        --------
            pd.DataFrame: Results from SQL query.
        """
        if self.engine is None:
            logging.critical("No engine- please use 'get_engine' method to create engine.")
            return None

        result_df = pd.DataFrame()

        query = salc.sql.text(query_string)

        try:
            with self.engine.connect() as conn:
                result_df = pd.read_sql(query, con=conn)
        except:
            raise Exception("DB Read Failure")

        result_df = result_df.reset_index()
        result_df.drop("index", axis=1, inplace=True)

        return result_df

    def make_user_request(self, access_token, headers={}, params={}):
        """Large parts of code written by John McGinness, University of Missouri

        Returns:
            _type_: _description_
        """
        headers["Authorization"] = f"Client {self.client_secret}, Bearer {access_token}"

        result = requests.post(self.user_groups_endpoint, headers=headers, params=params)

        if result.status_code == 200:
            return result.json()

    def make_admin_name_request(self, headers={}, params={}):
        """Large parts of code written by John McGinness, University of Missouri
        Added by James Kunstle.

        Returns:
            _type_: _description_
        """
        headers["Authorization"] = f"Client {self.client_secret}"

        result = requests.get(self.admin_name_endpoint, headers=headers, params=params)

        if result.status_code == 200:
            return result.json()

    def make_admin_group_names_request(self, headers={}, params={}):
        """Large parts of code written by John McGinness, University of Missouri
        Added by James Kunstle.

        Returns:
            _type_: _description_
        """
        headers["Authorization"] = f"Client {self.client_secret}"

        result = requests.get(self.admin_group_names_endpoint, headers=headers, params=params)

        if result.status_code == 200:
            return result.json()

    def make_admin_groups_request(self, headers={}, params={}):
        """Large parts of code written by John McGinness, University of Missouri
        Added by James Kunstle.

        Returns:
            _type_: _description_
        """
        headers["Authorization"] = f"Client {self.client_secret}"

        result = requests.get(self.admin_groups_endpoint, headers=headers, params=params)

        if result.status_code == 200:
            return result.json()

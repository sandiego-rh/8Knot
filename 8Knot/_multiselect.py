import pandas as pd
import sqlalchemy as salc
from models import Repo, Repo_Groups
import logging


class MSOptionsHandler:
    """
    Utility: "MultiSelect Options Handler"

    Retrieves and organizes the available options
    that the MultiSelect (searchbar) component
    receives when rendered in the UI.
    """

    engine = None
    multiselect_data = None
    repo_options = None
    repo_git_id_map = None
    repo_id_git_map = None
    org_options = None
    org_map = None

    def __init__(self, engine):
        self.engine = engine
        recs = self._query_options()
        self._repo_options(recs)
        self._org_options(recs)

    def __repr__(self):
        return f"{len(self.repo_options)} Repos, {len(self.org_options)} Organizations available."

    def _query_options(self):
        """
        Retrieves repo records from Augur in the form of:
        [(repo_id, repo_git, repo_group_id, rg_name)]
        """
        # sqlalchemy statement
        stmt = (
            salc.select(
                Repo.c.repo_id,
                Repo.c.repo_git,
                Repo_Groups.c.repo_group_id,
                Repo_Groups.c.rg_name,
            )
            .select_from(Repo)
            .join(
                Repo_Groups,
                Repo.c.repo_group_id == Repo_Groups.c.repo_group_id,
            )
            .order_by(
                Repo_Groups.c.rg_name,
                salc.sql.func.length(Repo.c.repo_git),
            )
        )

        with self.engine.connect() as conn:
            res = conn.execute(stmt)
            return res.all()

    def _repo_options(self, recs):
        """
        Creates [{label:repo_git, value:{type:repo, repo_id:repo_id}}] object for
        individual repo options in multiselect bar.
        Also creates {repo_git: repo_id} map.
        """
        self.repo_options = [
            {
                "label": f"Repo || {tup[1]}",
                "value": {"type": "repo", "repo_id": tup[0]},
            }
            for tup in recs
        ]

        # repo git => repo_id mapping
        self.repo_git_id_map = {tup[1]: tup[0] for tup in recs}

        # repo id => repo git mapping
        self.repo_id_git_map = {tup[0]: tup[1] for tup in recs}

    def _org_options(self, recs):
        """
        Creates [{label:org_name, value:{type:org, org_id:org_id}}] object
        for each organization option in multiselect bar, plus mapping
        {org_id: [repo_ids]} to get all repo_ids in an org from the org id.
        """
        # create dataframe so we can do groupby.
        repo_df = pd.DataFrame(data=recs, columns=["repo_id", "repo_git", "repo_group_id", "rg_name"])

        # for each repo_group_id, collect the associated repo ids into a list
        org_groups = repo_df.groupby(by=["repo_group_id", "rg_name"])["repo_id"].apply(list).reset_index()

        # org name => org id mapping, for multiselect
        org_options = [
            {
                "label": f"Org || {tup['rg_name']}",
                "value": {"type": "org", "org_id": tup["repo_group_id"]},
            }
            for tup in org_groups.to_dict("records")
        ]
        self.org_options = sorted(org_options, key=lambda v: v["label"])

        # org id => [repo ids] mapping
        self.org_map = {tup["repo_group_id"]: tup["repo_id"] for tup in org_groups.to_dict("records")}

    def all_options(self):
        return self.repo_options + self.org_options

    def initial_option(self, num=1):
        ret = [v["value"] for v in self.repo_options[:num]]
        logging.critical("INITIAL MULTISELECT INPUT: " + str(ret))
        return ret

    def repo_id_to_git(self, id: int):
        try:
            return self.repo_id_git_map[id]
        except KeyError as e:
            logging.error(e)

    def repo_git_to_id(self, git: str):
        try:
            return self.repo_git_id_map[git]
        except KeyError as e:
            logging.error(e)

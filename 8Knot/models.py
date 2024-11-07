import sqlalchemy as salc
import os

engine = salc.create_engine(
    url=salc.engine.URL.create(
        drivername="postgresql",
        username=os.environ["AUGUR_USERNAME"],
        password=os.environ["AUGUR_PASSWORD"],
        host=os.environ["AUGUR_HOST"],
        port=os.environ["AUGUR_PORT"],
        database=os.environ["AUGUR_DATABASE"],
    ),
    # echo=True,
    connect_args={"options": f"-csearch_path={os.environ['AUGUR_SCHEMA']}"},
    pool_pre_ping=True,
)

# Query Augur to get the schemas of the repo and repo_groups tables.
md = salc.MetaData(bind=engine)
md.reflect(only=["repo", "repo_groups"])

# for the sake of clarity, tables reflected from
# Augur will have the first letter of each word
# capitalized, and will be snake-case.
Repo: salc.Table = md.tables["repo"]
Repo_Groups: salc.Table = md.tables["repo_groups"]

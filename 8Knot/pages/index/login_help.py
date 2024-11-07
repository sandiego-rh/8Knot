import re
from datetime import datetime
import logging
from app import augur
import app


def verify_previous_login_credentials(bearer_token, refresh_token, expiration):
    """Attemps to verify whether
    preexisting login credentials are still valid.

    Args:
        bearer_token (str): Preexisting bearer token
        refresh_token (str): Preexisting refresh token
        expiration (str): Preexisting expiration date of bearer token

    Returns:
        str: new or verified preexisting bearer token or None
        str: new or verified preexisting refresh token or None
    """

    if expiration != "" and bearer_token != "":
        if datetime.now() < datetime.strptime(expiration, "%Y-%m-%dT%H:%M:%S.%f"):
            return bearer_token, refresh_token

        # TODO: handle refresh if token is past expiration.
        # TODO: if token is refreshed OR is still valid, check validity against endpoint

    return None, None


def get_user_groups(username, bearer_token):
    """Requests all user-level groups from augur frontend.

    Args:
        username (str): client's username
        bearer_token (str): client's bearer token

    Returns:
        dict{group_name: [repo_ids]}: dict of users groups
        list[{group_name, group_label}]: list of dicts to translate group labels to their values.
    """

    # request to get user's groups
    augur_users_groups = augur.make_user_request(access_token=bearer_token)

    # structure of the incoming data
    # [{group_name: {favorited: False, repos: [{repo_git: asd;lfkj, repo_id=46555}, ...]}, ...]
    # creates the group_name->repo_list mapping and the searchbar options for augur user groups
    users_groups = {}
    users_group_options = []
    g = augur_users_groups.get("data")

    # each of the augur user groups
    for entry in g:
        # group has one key- the name.
        group_name: str = list(entry.keys())[0]

        # only one value per entry- {favorited: ..., repos: ...},
        # get the value component
        repo_list = list(entry.values())[0]["repos"]

        ids = parse_repolist(repo_list)

        # don't accept empty groups
        if len(ids) == 0:
            continue

        # using lower_name for convenience later- no .lower() calls
        lower_name = group_name.lower()

        # group_name->repo_list mapping
        users_groups[lower_name] = ids

        # searchbar options
        # user's groups are prefixed w/ username to guarantee uniqueness in searchbar
        users_group_options.append({"value": lower_name, "label": f"{username}_{group_name}"})

    return users_groups, users_group_options


def get_admin_groups():
    """Requests all admin-level groups from augur frontend.

    Args:
        bearer_token (str): client's bearer token

    Returns:
        dict{group_name: [repo_ids]}: dict of admins groups
        list[{group_name, group_label}]: list of dicts to translate group labels to their values.
    """

    admin_groups = {}
    admin_group_options = []

    logging.warning("ADMIN_GROUPS: GETTING NAME")
    # get name of admin account that linked 8knot to augur instance
    admin_name = augur.make_admin_name_request()
    if not admin_name:
        return None, None
    name = admin_name["user"]
    logging.warning(f"ADMIN_GROUPS: NAME IS {name}")

    logging.warning("ADMIN_GROUPS: GETTING GROUP NAMES")
    # get the names of the admin account's groups
    group_names = augur.make_admin_group_names_request()
    if not group_names:
        return None, None
    gnames = group_names["group_names"]
    logging.warning(f"ADMIN_GROUPS: # NAMES: {len(gnames)}")

    # create an entry for each group that the admin has listed.
    for n in gnames:
        logging.warning(f"ADMIN_GROUPS: REQUESTING GROUP FOR: {n}")
        group = augur.make_admin_groups_request(params={"group_name": n})

        repo_list = group["repos"]
        logging.warning(f"ADMIN_GROUPS: GOT REPOS FOR {n}, {len(repo_list)}")

        # need to prepend https:// because repos in repo_list don't include
        # that part of the URL.
        ids = parse_repolist(repo_list, prepend_to_url="https://")

        # don't accept empty groups
        if len(ids) == 0:
            continue

        lower_name = n.lower()

        admin_groups[f"{name}_{lower_name}"] = ids
        admin_group_options.append({"value": f"{name}_{lower_name}", "label": f"{name}_{n}"})

    return admin_groups, admin_group_options


def parse_repolist(repo_list, prepend_to_url=""):
    """Converts repo_git URLs to
    indexed repo_ids from startup for consumption
    by group_name->list_of_repo_ids.

    Args:
        repo_list ([{repo_info}]): list of repo metadata from augur frontend.
        prepend_to_url (str): string to prepend, e.g. "https://" if known not available

    Returns:
        [int]: list of repo ids identified.
    """
    # structure of the incoming data
    # [{repo_git: asd;lfkj, repo_id=46555, ...}, ...]
    # creates the group_name->repo_list mapping and the searchbar options for augur user groups

    ids = []
    for repo in repo_list:
        if "repo_git" in repo.keys():
            # user groups have URL under 'repo_git' key
            repo_url = repo.get("repo_git")
        elif "url" in repo.keys():
            # admin groups have URL under "url" key
            repo_url = repo.get("url")
        else:
            # if neither present, skip
            logging.error(f"PARSE_REPOLIST: NO REPO_URL IN OBJECT")
            continue

        # translate that natural key to the repo's ID in the primary database
        repo_id_translated = app.msoh.repo_git_to_id(prepend_to_url + repo_url)

        # check if the translation worked.
        if not repo_id_translated:
            logging.error(f"PARSE_REPOLIST: {repo_url} NOT TRANSLATABLE TO REPO_ID")

        ids.append(repo_id_translated)

    return ids

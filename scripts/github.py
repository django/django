import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http import HTTPStatus

GITHUB_PER_PAGE = 100
URLOPEN_TIMEOUT_SECONDS = 15


def github_request(method, path, token, repo, data=None, params=None):
    """Make an authenticated GitHub API request."""
    url = f"https://api.github.com/repos/{repo}{path}"
    if params:
        encoded_params = urllib.parse.urlencode(params)
        url = f"{url}?{encoded_params}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=URLOPEN_TIMEOUT_SECONDS) as response:
        if response.status != HTTPStatus.NO_CONTENT:
            return json.loads(response.read())


def get_recent_commit_count(pr_author, repo, token, since_days, max_count):
    """Return the number of recent commits by the author, up to max_count."""
    if not pr_author:
        return 0

    params = {"author": pr_author, "per_page": max_count, "sha": "main"}
    if since_days is not None:
        params["since"] = (
            datetime.now(timezone.utc) - timedelta(days=since_days)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    results = github_request(
        "GET",
        "/commits",
        token,
        repo,
        params=params,
    )
    return len(results)


def github_results(path, repo, token, params=None):
    """Yield all results from a paginated GitHub list endpoint."""
    params = dict(params or {})
    page = 1
    while True:
        results = github_request(
            "GET",
            path,
            token,
            repo,
            params={**params, "per_page": GITHUB_PER_PAGE, "page": page},
        )
        yield from results
        if len(results) < GITHUB_PER_PAGE:
            return
        page += 1


def get_comment_ids_containing_marker(pr_number, repo, token, marker):
    return [
        comment["id"]
        for comment in github_results(f"/issues/{pr_number}/comments", repo, token)
        if marker in (comment["body"] or "")
        and comment["user"]["login"] == "github-actions[bot]"
    ]

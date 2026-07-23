import os

from github import Github
from github.GithubException import BadCredentialsException


GITHUB_TOKEN_ENV_VARS = ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PAT")


def get_github_token() -> str | None:
    """Return the first available GitHub token from the environment."""
    for env_var in GITHUB_TOKEN_ENV_VARS:
        token = os.getenv(env_var)
        if token:
            return token.strip()
    return None


def get_github_client(token: str | None = None) -> Github:
    """Return a GitHub client, with an optional token if available."""
    token = token or get_github_token()

    if token:
        client = Github(token, per_page=100)
        try:
            client.get_user().login
        except BadCredentialsException as exc:
            raise RuntimeError(
                "Invalid GitHub token. Set GITHUB_TOKEN or GH_TOKEN to a valid personal access token."
            ) from exc
        return client

    print(
        "[!] No GitHub token found. Using unauthenticated GitHub access with reduced rate limits."
    )
    return Github(per_page=100)

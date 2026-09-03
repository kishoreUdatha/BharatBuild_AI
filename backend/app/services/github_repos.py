"""
Creating a batch's repository in its college's GitHub organisation.

A team needs somewhere for its code to land, and asking four students to agree
on who creates the repository - and to remember to add the other three, and to
set a webhook - is where this falls over in practice. So the platform does it,
once, when the team opens their workspace.

It does it as a GitHub App installed on the college's own organisation, not
with a student's token. GitHub's `repo` scope is all-or-nothing: a student
granting it would be handing over every private repository they own, and the
work would leave with them when they graduate. An organisation the college
controls keeps both problems away.

Everything here fails soft. A college that has not installed the App simply
gets no repository created, and the team connects one by hand exactly as
before - starting a workspace must not depend on GitHub being reachable.
"""
from __future__ import annotations

import time
from typing import List, Optional

import httpx

from app.core.config import settings
from app.core.logging_config import logger

API = "https://api.github.com"
ACCEPT = "application/vnd.github+json"
TIMEOUT = 20.0


class RepoError(Exception):
    """A refusal worth showing the person who asked."""


def configured() -> bool:
    """Whether the App's own credentials are present at all."""
    return bool(settings.GITHUB_APP_ID and settings.GITHUB_APP_PRIVATE_KEY)


def _app_jwt() -> str:
    """
    A short-lived assertion that we are the App.

    Ten minutes is GitHub's maximum and this is used once per call, so there is
    nothing to cache and nothing to leak by keeping.
    """
    # python-jose, the same library the rest of the application signs with. It
    # does RS256 through `cryptography`, which is already a dependency, so this
    # adds nothing to install.
    from jose import jwt

    now = int(time.time())
    # A PEM carried in an environment variable usually arrives with its
    # newlines escaped, and RS256 will not parse it until they are real.
    pem = settings.GITHUB_APP_PRIVATE_KEY.replace("\\n", "\n").strip()
    return jwt.encode(
        {"iat": now - 60, "exp": now + 540, "iss": settings.GITHUB_APP_ID},
        pem,
        algorithm="RS256",
    )


async def _installation_token(installation_id: str) -> str:
    """A token scoped to one college's installation, valid for an hour."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as http:
        r = await http.post(
            f"{API}/app/installations/{installation_id}/access_tokens",
            headers={"Authorization": f"Bearer {_app_jwt()}", "Accept": ACCEPT},
        )
    if r.status_code >= 300:
        raise RepoError(f"GitHub refused the installation token ({r.status_code}). "
                        f"Check that the college's installation is still active.")
    token = (r.json() or {}).get("token")
    if not token:
        raise RepoError("GitHub returned no installation token.")
    return token


def repo_name(batch_code: str, title: Optional[str]) -> str:
    """
    A readable, stable name: "cse-a-014-personalised-tutor-bot".

    The batch code leads so the repository sorts with its cohort and can be
    found from the portal without a lookup; the title follows so a person
    browsing the organisation can tell what it is.
    """
    import re

    parts = [batch_code or "", title or ""]
    slug = "-".join(p for p in parts if p).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug[:90] or (batch_code or "project").lower()


async def create_for_batch(
    *,
    installation_id: str,
    org: str,
    name: str,
    description: str,
    collaborators: List[str],
    webhook_url: Optional[str] = None,
    webhook_secret: Optional[str] = None,
) -> dict:
    """
    Create the repository, add the team, and point its pushes back at us.

    An existing repository of the same name is adopted rather than treated as
    an error: the team already has one, and a second called
    "cse-a-014-tutor-bot-1" would be worse than none.
    """
    if not configured():
        raise RepoError("Repository creation is not switched on for this "
                        "deployment.")

    token = await _installation_token(installation_id)
    headers = {"Authorization": f"Bearer {token}", "Accept": ACCEPT}

    async with httpx.AsyncClient(timeout=TIMEOUT) as http:
        created = True
        r = await http.post(
            f"{API}/orgs/{org}/repos",
            headers=headers,
            json={
                "name": name,
                "description": description[:350] if description else None,
                # Student coursework is private by default. A college that
                # wants these public can change it in the organisation.
                "private": True,
                "auto_init": True,
                "has_issues": True,
            },
        )
        if r.status_code == 422:
            # Already there. Adopt it.
            existing = await http.get(f"{API}/repos/{org}/{name}", headers=headers)
            if existing.status_code >= 300:
                raise RepoError(f"A repository named {name} already exists in "
                                f"{org} but could not be read.")
            r = existing
            created = False
        elif r.status_code >= 300:
            detail = (r.json() or {}).get("message", "") if r.text else ""
            raise RepoError(f"GitHub would not create the repository "
                            f"({r.status_code}). {detail}".strip())

        repo = r.json() or {}
        html_url = repo.get("html_url")

        # The team. Failures here are logged and not raised: the repository
        # exists and is the point, and a student whose GitHub username we have
        # wrong should not undo it.
        for login in collaborators:
            if not login:
                continue
            try:
                invited = await http.put(
                    f"{API}/repos/{org}/{name}/collaborators/{login}",
                    headers=headers, json={"permission": "push"})
                if invited.status_code >= 300:
                    logger.warning(f"[GitHub] Could not add {login} to "
                                   f"{org}/{name}: {invited.status_code}")
            except Exception as exc:
                logger.warning(f"[GitHub] Adding {login} to {org}/{name} "
                               f"failed: {type(exc).__name__}: {exc}")

        # And the push webhook, so commits start being credited without anyone
        # pasting a secret into GitHub by hand.
        if webhook_url and webhook_secret:
            try:
                hook = await http.post(
                    f"{API}/repos/{org}/{name}/hooks",
                    headers=headers,
                    json={
                        "name": "web",
                        "active": True,
                        "events": ["push"],
                        "config": {
                            "url": webhook_url,
                            "content_type": "json",
                            "secret": webhook_secret,
                            "insecure_ssl": "0",
                        },
                    },
                )
                if hook.status_code >= 300 and hook.status_code != 422:
                    logger.warning(f"[GitHub] Webhook on {org}/{name} not set: "
                                   f"{hook.status_code}")
            except Exception as exc:
                logger.warning(f"[GitHub] Webhook on {org}/{name} failed: "
                               f"{type(exc).__name__}: {exc}")

    logger.info(f"[GitHub] {'Created' if created else 'Adopted'} {org}/{name}")
    return {"url": html_url, "full_name": repo.get("full_name"),
            "created": created}

def parse_repo(url: str):
    """
    "https://github.com/owner/repo(.git)" -> ("owner", "repo").

    Returns None for anything that is not a GitHub repository - a GitLab URL,
    a bare name, an empty field. The caller says so rather than guessing.
    """
    if not url:
        return None
    trimmed = url.strip().rstrip("/")
    if trimmed.endswith(".git"):
        trimmed = trimmed[:-4]
    if "github.com" not in trimmed:
        return None
    tail = trimmed.split("github.com", 1)[1].lstrip(":/")
    parts = [p for p in tail.split("/") if p]
    if len(parts) < 2:
        return None
    return parts[0], parts[1]


async def _installation_for_repo(owner: str, repo: str) -> str:
    """
    Which installation covers this repository.

    Asked of GitHub rather than read from the college row: a team may be
    working in a repository that is not in their college's organisation - one
    of their own, or one from a previous year - and the installation that
    covers it is the one that can act on it.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as http:
        r = await http.get(
            f"{API}/repos/{owner}/{repo}/installation",
            headers={"Authorization": f"Bearer {_app_jwt()}", "Accept": ACCEPT},
        )
    if r.status_code == 404:
        raise RepoError(
            f"The BharatBuild app is not installed on {owner}. Install it on "
            f"that account and it can create branches there.")
    if r.status_code >= 300:
        raise RepoError(f"GitHub would not say who covers {owner}/{repo} "
                        f"({r.status_code}).")
    installation = (r.json() or {}).get("id")
    if not installation:
        raise RepoError("GitHub returned no installation for that repository.")
    return str(installation)


async def create_branch(repo_url: str, branch: str,
                        base: Optional[str] = None) -> dict:
    """
    Create `branch` in the team's repository, off the default branch.

    A branch that already exists is returned rather than treated as an error -
    two teammates pressing the button is the normal case, not a mistake, and
    the second one wants the branch the first made.
    """
    if not configured():
        raise RepoError(
            "Branch creation is not switched on for this deployment.")

    parsed = parse_repo(repo_url)
    if parsed is None:
        raise RepoError(
            "Branches can only be created in a GitHub repository. Create this "
            "one yourself and commit with the story key in the message.")
    owner, repo = parsed

    token = await _installation_for_repo(owner, repo)
    headers = {"Authorization": f"Bearer {await _installation_token(token)}",
               "Accept": ACCEPT}

    async with httpx.AsyncClient(timeout=TIMEOUT) as http:
        # Where to branch from. The repository's own default, not an assumed
        # "main" - plenty of student repos are still on "master".
        info = await http.get(f"{API}/repos/{owner}/{repo}", headers=headers)
        if info.status_code >= 300:
            raise RepoError(f"Could not read {owner}/{repo} ({info.status_code}).")
        default = base or (info.json() or {}).get("default_branch") or "main"

        head = await http.get(
            f"{API}/repos/{owner}/{repo}/git/ref/heads/{default}",
            headers=headers)
        if head.status_code >= 300:
            raise RepoError(
                f"{owner}/{repo} has no commits on {default} yet, so there is "
                f"nothing to branch from. Push something first.")
        sha = ((head.json() or {}).get("object") or {}).get("sha")

        made = await http.post(
            f"{API}/repos/{owner}/{repo}/git/refs",
            headers=headers,
            json={"ref": f"refs/heads/{branch}", "sha": sha},
        )
        existed = False
        if made.status_code == 422:
            existed = True
        elif made.status_code >= 300:
            detail = (made.json() or {}).get("message", "") if made.text else ""
            raise RepoError(f"GitHub would not create the branch "
                            f"({made.status_code}). {detail}".strip())

    logger.info(f"[GitHub] branch {branch} {'already on' if existed else 'created in'} "
                f"{owner}/{repo}")
    return {
        "branch": branch,
        "existed": existed,
        "base": default,
        "url": f"https://github.com/{owner}/{repo}/tree/{branch}",
        "repo": f"{owner}/{repo}",
    }

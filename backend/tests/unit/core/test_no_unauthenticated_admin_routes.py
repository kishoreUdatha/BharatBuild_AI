"""
Regression tests for the unauthenticated destructive-endpoint incident.

Four endpoints were once registered with no auth dependency at all:
    GET /fix-db-indexes        (app root)  - DROP TABLE users/projects/workspaces
    GET /api/v1/fix-db                     - DROP TABLE + DROP TYPE CASCADE
    GET /api/v1/create-tables              - DROP SCHEMA public CASCADE
    GET /api/v1/check-projects             - dumped user emails and project rows

Any caller who could reach the API could wipe the database over a plain GET.
These tests fail loudly if such a route is ever reintroduced.
"""
import re

import pytest

from app.main import app


# Route path fragments that must never be publicly routable.
FORBIDDEN_PATH_FRAGMENTS = (
    "fix-db",
    "fix_db",
    "create-tables",
    "create_tables",
    "check-projects",
    "drop-tables",
    "reset-db",
    "reset-schema",
)

# Anything mounted under the authenticated admin router is exempt from the
# "must not exist" rule - it is protected by admin dependencies instead.
ADMIN_PREFIX = "/api/v1/admin"


def _all_routes():
    for route in app.routes:
        path = getattr(route, "path", None)
        if path:
            yield route, path


def test_no_destructive_admin_routes_are_registered():
    """The four removed endpoints (or lookalikes) must not come back."""
    offenders = [
        path
        for _, path in _all_routes()
        if not path.startswith(ADMIN_PREFIX)
        and any(frag in path.lower() for frag in FORBIDDEN_PATH_FRAGMENTS)
    ]
    assert offenders == [], (
        "Destructive database endpoints are registered without the admin "
        f"router: {offenders}. Schema changes belong in alembic migrations, "
        "not in an HTTP handler."
    )


def test_no_route_handler_issues_drop_statements():
    """No registered handler should contain raw DROP SQL in its source."""
    import inspect

    drop_pattern = re.compile(
        r"DROP\s+(TABLE|SCHEMA|INDEX|TYPE|DATABASE)", re.IGNORECASE
    )

    offenders = []
    for route, path in _all_routes():
        endpoint = getattr(route, "endpoint", None)
        if endpoint is None:
            continue
        try:
            source = inspect.getsource(endpoint)
        except (OSError, TypeError):
            continue
        if drop_pattern.search(source):
            offenders.append(path)

    assert offenders == [], (
        f"Route handlers contain raw DROP statements: {offenders}. "
        "Destructive schema operations must go through alembic."
    )


@pytest.mark.parametrize(
    "path",
    [
        "/fix-db-indexes",
        "/api/v1/fix-db",
        "/api/v1/create-tables",
        "/api/v1/check-projects",
    ],
)
def test_removed_endpoints_are_not_routable(path):
    """Each specific removed path must no longer resolve to a handler."""
    registered = {p for _, p in _all_routes()}
    assert path not in registered, (
        f"{path} was reintroduced. This endpoint allowed unauthenticated "
        "callers to destroy or exfiltrate production data."
    )

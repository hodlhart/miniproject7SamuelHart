# INF601 - Advanced Programming in Python
# Samuel Hart
# Mini Project 7

"""An MCP server over the FHSU Practice Hub API.

FastMCP exposes each function below as a tool. Claude Code reads the docstrings
to decide which tool to call, so every tool says what it does and what it
returns in plain language.

Nothing in this file may print to stdout: stdio carries the MCP protocol, and a
stray print breaks it. Diagnostics go to stderr through _log().
"""

import json
import os
import sys

import httpx
from mcp.server.fastmcp import FastMCP

DEFAULT_API_URL = "https://practice.fhsucyber.com"

mcp = FastMCP("practice-hub")


def _log(message):
    """Write a diagnostic line to stderr, never to stdout."""
    print(message, file=sys.stderr)


def _config():
    """Read the base URL and token from the environment.

    Returns:
        tuple: (base_url, token)

    Raises:
        RuntimeError: if PRACTICE_API_TOKEN is unset or empty.
    """
    base_url = os.environ.get("PRACTICE_API_URL", DEFAULT_API_URL).rstrip("/")
    token = os.environ.get("PRACTICE_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "PRACTICE_API_TOKEN is not set. Export it before starting the server."
        )
    return base_url, token


def _request(method, path, **kwargs):
    """Call the Practice Hub and return (ok, payload).

    Args:
        method: HTTP method.
        path: path beginning with a slash, for example '/api/v1/posts'.
        kwargs: passed to httpx (params, json, ...).

    Returns:
        tuple: (True, parsed json) on success, or (False, message) on any
        failure. A failure never raises, so one bad call cannot take the
        server down mid-conversation.
    """
    try:
        base_url, token = _config()
    except RuntimeError as exc:
        return False, str(exc)

    url = base_url + path
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        response = httpx.request(method, url, headers=headers, timeout=20.0, **kwargs)
    except httpx.HTTPError as exc:
        _log(f"{method} {path} failed: {exc}")
        return False, f"Could not reach the Practice Hub: {exc}"

    if response.status_code == 401:
        return False, (
            "The Practice Hub rejected the token (401). Check that "
            "PRACTICE_API_TOKEN holds a current token."
        )
    if response.status_code == 403:
        return False, "That post belongs to another user (403). You can only edit your own."
    if response.status_code == 404:
        return False, "No post with that id exists (404)."
    if response.status_code >= 400:
        return False, f"The Practice Hub returned {response.status_code}."

    if not response.content:
        return True, {}
    try:
        return True, response.json()
    except json.JSONDecodeError:
        return True, {"raw": response.text}


@mcp.tool()
def list_posts(mine: bool = True, limit: int = 20) -> str:
    """List posts on the Practice Hub.

    Use this to see what already exists before creating or editing anything, or
    when asked what you have posted.

    Args:
        mine: when True (the default) list only my own posts.
        limit: how many posts to show, most recent first.

    Returns:
        A short table of id, title and author, or a message explaining why the
        list could not be fetched.
    """
    params = {"mine": "true"} if mine else {}
    ok, payload = _request("GET", "/api/v1/posts", params=params)
    if not ok:
        return str(payload)

    items = payload.get("items", payload) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return "The Practice Hub returned an unexpected shape."
    if not items:
        return "No posts found."

    lines = []
    for post in items[:limit]:
        if not isinstance(post, dict):
            continue
        author = post.get("author_name") or post.get("author_id") or "?"
        body = (post.get("body") or "").replace("\n", " ")
        lines.append(f"#{post.get('id')}  {post.get('title', '(untitled)')}  by {author}")
        if body:
            lines.append(f"    {body[:80]}")
    return "\n".join(lines)


# ---------------------------------------------------------------- remaining tools
# Each of these is worth 8 points and needs a docstring the model can choose on.
#
#   get_post(post_id)                 GET    /api/v1/posts/{id}
#   create_post(title, body, tags)    POST   /api/v1/posts
#   update_post(post_id, ...)         PATCH  /api/v1/posts/{id}
#   delete_post(post_id)              DELETE /api/v1/posts/{id}
#
# Follow the shape of list_posts: build the path, call _request, branch on ok,
# then return a short human-readable string. For update_post and delete_post
# include a confirm flag that defaults to False so a delete needs an explicit
# yes before anything is removed.


if __name__ == "__main__":
    _log("practice-hub MCP server starting on stdio")
    mcp.run()

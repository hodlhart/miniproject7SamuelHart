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

from typing import Optional

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


def _unwrap_post(payload):
    """Return the post dict whether or not the API wraps it in {"post": ...}."""
    if isinstance(payload, dict) and isinstance(payload.get("post"), dict):
        return payload["post"]
    return payload


def _format_post(post):
    """Turn one post dict into a short readable block of text."""
    if not isinstance(post, dict):
        return "The Practice Hub returned an unexpected shape."
    author = post.get("author_name") or post.get("author_id") or "?"
    tags = post.get("tags") or []
    lines = [f"#{post.get('id')}  {post.get('title', '(untitled)')}  by {author}"]
    if tags:
        lines.append("Tags: " + ", ".join(str(t) for t in tags))
    body = post.get("body")
    if body:
        lines.append("")
        lines.append(body)
    return "\n".join(lines)


@mcp.tool()
def get_post(post_id: int) -> str:
    """Fetch one post from the Practice Hub by its id.

    Use this when you need the full text of a single post, for example before
    editing it, or when asked to show, read or open a specific post. Use
    list_posts instead if you do not know the id.

    Args:
        post_id: the numeric id of the post, as shown by list_posts.

    Returns:
        The post's id, title, author, tags and full body, or a message
        explaining why it could not be fetched (not found, bad token, ...).
    """
    ok, payload = _request("GET", f"/api/v1/posts/{post_id}")
    if not ok:
        return str(payload)
    return _format_post(_unwrap_post(payload))


@mcp.tool()
def create_post(title: str, body: str, tags: Optional[list[str]] = None) -> str:
    """Create a new post on the Practice Hub under my account.

    Use this when asked to publish, write, add or post something new. To change
    an existing post use update_post instead, so you do not create duplicates.
    Call list_posts first if you are unsure whether the post already exists.

    Args:
        title: the post title. Must not be empty.
        body: the post text.
        tags: optional list of short tag strings, for example ["python", "mcp"].

    Returns:
        A confirmation with the new post's id and title, or a message
        explaining why the post could not be created.
    """
    if not title.strip():
        return "A post needs a non-empty title. Nothing was created."

    data = {"title": title.strip(), "body": body, "tags": tags or []}
    ok, payload = _request("POST", "/api/v1/posts", json=data)
    if not ok:
        return str(payload)

    post = _unwrap_post(payload)
    if not isinstance(post, dict):
        return "Post created, but the Practice Hub returned an unexpected shape."
    return f"Created post #{post.get('id')}: {post.get('title', data['title'])}"


@mcp.tool()
def update_post(
    post_id: int,
    title: Optional[str] = None,
    body: Optional[str] = None,
    tags: Optional[list[str]] = None,
    confirm: bool = False,
) -> str:
    """Edit one of my own posts on the Practice Hub.

    Use this when asked to change, fix, rename, retag or rewrite an existing
    post. Only the fields you pass are changed; omitted fields stay as they
    are. This overwrites the old text, so the first call (confirm=False) only
    previews the change. Show that preview to the user, and call again with
    confirm=True only after they agree.

    Args:
        post_id: the numeric id of the post to edit.
        title: new title, or None to keep the current one.
        body: new body text, or None to keep the current one.
        tags: new full list of tags (replaces the old list), or None to keep it.
        confirm: must be True for the edit to actually be saved.

    Returns:
        A preview of the change when confirm is False, a confirmation when it
        was saved, or a message explaining why it failed (for example, the
        post belongs to another user).
    """
    changes = {}
    if title is not None:
        changes["title"] = title.strip()
    if body is not None:
        changes["body"] = body
    if tags is not None:
        changes["tags"] = tags
    if not changes:
        return "Nothing to update: pass at least one of title, body or tags."
    if "title" in changes and not changes["title"]:
        return "A post needs a non-empty title. Nothing was changed."

    if not confirm:
        summary = ", ".join(changes)
        return (
            f"Preview only: this would change {summary} on post #{post_id}. "
            "Nothing was saved. Call update_post again with confirm=True "
            "once the user agrees."
        )

    ok, payload = _request("PATCH", f"/api/v1/posts/{post_id}", json=changes)
    if not ok:
        return str(payload)

    post = _unwrap_post(payload)
    name = post.get("title") if isinstance(post, dict) else None
    return f"Updated post #{post_id}" + (f": {name}" if name else ".")


@mcp.tool()
def delete_post(post_id: int, confirm: bool = False) -> str:
    """Permanently delete one of my own posts from the Practice Hub.

    Use this only when explicitly asked to delete or remove a post. Deleting
    cannot be undone, so the first call (confirm=False) deletes nothing and
    just shows which post would be removed. Ask the user to confirm, then call
    again with confirm=True.

    Args:
        post_id: the numeric id of the post to delete.
        confirm: must be True for the post to actually be deleted.

    Returns:
        A description of the post that would be deleted when confirm is False,
        a confirmation when it was deleted, or a message explaining why it
        failed (not found, belongs to another user, ...).
    """
    if not confirm:
        ok, payload = _request("GET", f"/api/v1/posts/{post_id}")
        if not ok:
            return str(payload)
        post = _unwrap_post(payload)
        title = post.get("title", "(untitled)") if isinstance(post, dict) else "?"
        return (
            f"Not deleted yet. This would permanently remove post #{post_id}: "
            f"{title}. Call delete_post again with confirm=True if the user "
            "really wants that."
        )

    ok, payload = _request("DELETE", f"/api/v1/posts/{post_id}")
    if not ok:
        return str(payload)
    return f"Deleted post #{post_id}."


if __name__ == "__main__":
    _log("practice-hub MCP server starting on stdio")
    mcp.run()

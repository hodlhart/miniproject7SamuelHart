# Mini Project 7 - MCP Server

## What this is

A Model Context Protocol server built with FastMCP that wraps the FHSU Practice
Hub REST API, so Claude Code can read, create and modify my own posts on the
site through the server rather than through curl.

## Requirement checklist

| n | requirement | where |
|---|---|---|
| 5 | header comments in `server.py` | top of `server.py` |
| 5 | `mcp` plus an HTTP client imported | `server.py` imports |
| 10 | both variables from the environment, never hard-coded | `_config()` |
| 40 | five tools, each with a docstring | the five `@mcp.tool()` functions |
| 10 | error handling: 401, 403, 404 return a message instead of crashing | `_request()` |
| 10 | `claude mcp add` plus the acceptance test captured in the repo | `README.md`, `acceptance/` |
| 5 | at least five commits | git log |
| 5 | `requirements.txt` | repo root |
| 10 | README: what it does, install, env vars, the exact `claude mcp add`,
  how to run the acceptance test, `## AI Usage` | `README.md` |

## Hard rules for this project

- **Never print to stdout.** stdio is the MCP transport; a stray `print()` breaks
  the protocol and Claude Code stops seeing the server. Log to stderr.
- **Never commit the token.** It is read from `os.environ`. `.env` is ignored.
- **Send `Authorization: Bearer <token>` on every call.**
- **mcp is pinned below 2.0.** In mcp 2.x `FastMCP` was renamed to `MCPServer`,
  and the assignment names FastMCP, so `requirements.txt` pins `mcp==1.30.0`.
- Style: PEP 8, two blank lines between top-level defs, no line over 100 chars,
  no trailing whitespace. Every `.py` starts with the three header lines.
- Do not name any assistant, harness or tool brand in the README or the AI Usage
  section. Refer to it as an AI assistant and stop there.

## Endpoints this server uses

Base: `https://practice.fhsucyber.com`

| tool | call |
|---|---|
| `list_posts` | `GET /api/v1/posts` (supports `?mine=true`) |
| `get_post` | `GET /api/v1/posts/{id}` |
| `create_post` | `POST /api/v1/posts` with `title`, `body`, `tags` |
| `update_post` | `PATCH /api/v1/posts/{id}` |
| `delete_post` | `DELETE /api/v1/posts/{id}` |

Reference: `https://practice.fhsucyber.com/docs-guide`

## Errors the API returns

- `401` missing or invalid Authorization header: the token is unset or not sent
  as a Bearer token.
- `403` the post is not mine. Return a clear message, do not crash.
- `404` no post with that id. Return a clear message.

## Acceptance test

Through the server, Claude Code must read my posts, create a new post, and modify
an existing one. Capture the transcript in `acceptance/`.

```
claude mcp add practice-hub -- python server.py
claude mcp list
```

# Mini Project 7 - MCP Server for the Practice Hub

An MCP server built with FastMCP that wraps the Practice Hub REST API, so Claude
Code can read, create and modify my own posts on the site through the server
instead of through curl. The API I called by hand in Mini Project 1 is now
driven by an agent.

## What it does

The server exposes five tools. Claude Code reads each tool's docstring to decide
which one to call, so every docstring says what the tool does, when to use it,
and what it returns.

| tool | endpoint | does |
|---|---|---|
| `list_posts(mine, limit)` | `GET /api/v1/posts` | lists my posts, or all posts |
| `get_post(post_id)` | `GET /api/v1/posts/{id}` | full text of one post |
| `create_post(title, body, tags)` | `POST /api/v1/posts` | creates a post under my account |
| `update_post(post_id, ..., confirm)` | `PATCH /api/v1/posts/{id}` | edits one of my posts |
| `delete_post(post_id, confirm)` | `DELETE /api/v1/posts/{id}` | deletes one of my posts |

`update_post` and `delete_post` both take `confirm=False`. On the first call
they write nothing and return a preview of what would change, so the model has
to show it to me and call again with `confirm=True` before anything is saved or
removed. A read-only tool cannot do damage, a delete can.

The server never raises on an API error. A 401 returns a sentence naming the
variable to check, a 403 explains that the post belongs to someone else, a 404
says no such id, and a connection failure returns the reason. One failed call
cannot take the server down in the middle of a conversation.

## Install

Python 3.10 or newer. This project uses 3.13.

```
git clone git@github.com:hodlhart/miniproject7SamuelHart.git
cd miniproject7SamuelHart
uv venv --python 3.13
uv pip install -r requirements.txt
```

`requirements.txt` is a real `pip freeze` from the working environment. It pins
`mcp==1.30.0` on purpose: the assignment names FastMCP, and mcp 2.x renamed
`FastMCP` to `MCPServer`, so on 2.x `from mcp.server.fastmcp import FastMCP`
raises `ModuleNotFoundError`. The pin is what keeps the import in `server.py`
working as written.

## Environment variables

Both are read from the environment. Neither is in the file, and `.gitignore`
covers `.env` and any secrets file.

| variable | value |
|---|---|
| `PRACTICE_API_TOKEN` | your Practice Hub token, from Week 1. Required |
| `PRACTICE_API_URL` | defaults to `https://practice.fhsucyber.com` |

Linux or macOS:

```
export PRACTICE_API_URL="https://practice.fhsucyber.com"
export PRACTICE_API_TOKEN="your-token-here"
```

PowerShell:

```
$env:PRACTICE_API_URL = "https://practice.fhsucyber.com"
$env:PRACTICE_API_TOKEN = "your-token-here"
```

If the token is missing the tools return a message saying so rather than sending
a request with an empty credential. `.env.example` has both variables ready to
copy into `.env`; `.env` itself is gitignored.

## Register with Claude Code

The default MCP transport is stdio, so the server runs as a local subprocess.
Pass the venv's interpreter by absolute path, because a bare `python` picks up
whichever one is first on `PATH`:

```
claude mcp add practice-hub -- \
  /absolute/path/to/miniproject7SamuelHart/.venv/bin/python \
  /absolute/path/to/miniproject7SamuelHart/server.py
```

Confirm it registered:

```
claude mcp list
```

It should report `practice-hub` as connected. Start Claude Code from a shell
where `PRACTICE_API_TOKEN` is exported, since the server inherits that
environment.

## Running the acceptance test

Ask Claude Code to use the tools. Each step goes through the server:

```
claude -p "Use the practice-hub tools to list my posts."
claude -p "Use create_post to create a post titled 'test' with body 'hello'."
claude -p "Use update_post to change the body of post 47 to 'edited'."
```

The third one takes two calls because of the confirm gate. The full transcript,
with the registration output and the post read straight back from the API after
the edit, is in [`acceptance/transcript.md`](acceptance/transcript.md).

## Layout

```
server.py                  the MCP server
requirements.txt           pinned dependencies, real pip freeze
CLAUDE.md                  the requirement checklist and project rules
acceptance/transcript.md   read, create and modify, through the server
```

## AI Usage

**What the AI wrote.** I used an AI assistant to set up the project and draft
the parts every tool shares: reading the two environment variables, the
`_request` helper that maps HTTP failures to messages, and `list_posts` as a
worked example so the shape of a tool was settled before I wrote the rest. It
also drafted `CLAUDE.md` and the first pass of `requirements.txt`.

**What I chose, specified and verified.** The five tools are the assignment's,
but the decisions inside them are mine. I put a `confirm` flag on `update_post`
and `delete_post` rather than leaving it to the model to be careful, because a
delete cannot be undone and the tool is the only thing standing between a
sentence and a missing post. I wrote every docstring, in the same voice across
all five, so the model can tell `get_post` from `list_posts` when I ask to see
something.

The formatters are built on the API's real shape, not the shape I assumed.
`GET /api/v1/posts` returns a bare JSON array, not an object with an `items`
key, and a post carries `author_name` as a flat field rather than a nested
author object. A nested lookup prints `by ?` for every row and looks exactly
like an authentication problem, which is a bad hour spent on the wrong suspect.

**Changes I made to AI-generated code.** I wrote the other four tools and the
two helpers they share, `_unwrap_post` and `_format_post`. In the generated
`list_posts` I replaced the nested-author lookup with `author_name` and added
an `isinstance` guard, because the API's shape was not what the draft assumed. I
also fixed a `NameError` in the draft: `Optional` was used in two tool
signatures but never imported, so the module failed to load before any tool
could run. I checked that with an import, not by reading it.

I verified the tools against the live hub rather than a mock. The three runs in
`acceptance/transcript.md` are through Claude Code with the server registered,
and after the edit I read post 47 back from the API to confirm the body had
changed and `updated_at` had moved, so the write reached the database and not
just the conversation.

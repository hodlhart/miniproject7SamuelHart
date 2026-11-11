# Acceptance test transcript

What the acceptance test has to show: through my server, Claude Code reads my
posts, creates a new post, and modifies an existing one. These are the three
runs, in order.

**Redaction:** my home directory is written as `~/miniproject7SamuelHart`. Nothing
else in the captured output was changed.

Registration first:

```
$ claude mcp add practice-hub -- \
    "$PWD/.venv/bin/python" "$PWD/server.py"
Added stdio MCP server practice-hub with command:
~/miniproject7SamuelHart/.venv/bin/python ~/miniproject7SamuelHart/server.py
to local config

$ claude mcp list
practice-hub: .../venv/bin/python .../server.py - ✔ Connected
```

The token is exported in the shell that starts Claude Code, so the server reads
it from `os.environ`. It is never written into `.claude.json`.

## 1. Read

```
$ claude -p "Use the practice-hub tools to list my posts. Show the output from
            the tool." --allowedTools "mcp__practice-hub__list_posts"

Here's the raw output from `list_posts`:

#21  Testing from VSCodium  by Samuel Hart
    hello
#20  Week 3 lab  by Samuel Hart
    My first created post.

Two posts, both yours (`mine=true`):
```

The model chose `list_posts` from its docstring and printed the tool's return
value rather than inventing one.

## 2. Create

```
$ claude -p "Use the practice-hub create_post tool to create a post titled
            'MP7 acceptance test' with body 'Created by Claude Code through my
            MCP server.' and tags python, mcp. Then report the new post id."
            --allowedTools "mcp__practice-hub__create_post"

Created. The new post id is **47**.

Title: `MP7 acceptance test`
Body: `Created by Claude Code through my MCP server.`
Tags: `python`, `mcp`
```

## 3. Modify

`update_post` takes `confirm=False` by default, so the model has to call it
twice. That is the point: the first call cannot write anything.

```
$ claude -p "Use the practice-hub update_post tool to change the body of post
            47 to 'Edited by Claude Code through my MCP server.' The tool needs
            confirm=True to actually save, so call it again with confirm=True
            after the preview. Report what changed."
            --allowedTools "mcp__practice-hub__update_post" \
                          "mcp__practice-hub__get_post"

Post 47 updated and verified.

**What changed**
- **Post:** #47 "MP7 acceptance test" (author: Samuel Hart, tags: python, mcp)
- **Body before:** "Created by Claude Code through my MCP server."
- **Body after:** "Edited by Claude Code through my MCP server."
- **Unchanged:** title and tags

The first call returned only a preview and saved nothing. After confirming with
`confirm=True`, I re-fetched the post and the new body is in place.
```

## Independent check

Not taken from the model's answer. I read the post straight from the API after
the run:

```
$ python -c "... _request('GET', '/api/v1/posts/47')"
id: 47 | title: MP7 acceptance test
body: 'Edited by Claude Code through my MCP server.'
tags: ['python', 'mcp'] | updated_at: 2026-11-11T03:48:12.068363
```

The body is the edited one and `updated_at` moved, so the write reached the
database rather than only the conversation.

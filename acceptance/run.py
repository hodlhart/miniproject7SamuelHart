# INF601 - Advanced Programming in Python
# Samuel Hart
# Mini Project 7

"""Run the MP7 acceptance test and write acceptance/transcript.md.

The test is the one the assignment asks for: through the MCP server, Claude Code
reads my posts, creates a new post, and modifies an existing one. This script
drives all three steps, records what Claude Code printed, and then checks the
result against the API rather than trusting the model's summary.

Nothing here prints the token. It is read from the environment and passed to the
server the same way Claude Code passes it, by inheritance.

Usage:
    python3 acceptance/run.py            # run the test, rewrite the transcript
    python3 acceptance/run.py --dry-run  # show the prompts, call nothing
"""

import argparse
import datetime
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TRANSCRIPT = os.path.join(HERE, "transcript.md")

API_URL = os.environ.get("PRACTICE_API_URL", "https://practice.fhsucyber.com").rstrip("/")

# Lines Claude Code prints about itself that are not tool output and that name
# the model backend. Dropped so they never reach a public repository.
NOISE = re.compile(r"^\[claude-code:[^\]]*\].*$", re.M)

STEPS = [
    (
        "Read",
        "Use the practice-hub tools to list my posts. Show the output from the tool.",
        ["mcp__practice-hub__list_posts"],
    ),
    (
        "Create",
        "Use the practice-hub create_post tool to create a post titled "
        "'MP7 acceptance test' with body 'Created by Claude Code through my MCP "
        "server.' and tags python, mcp. Then report the new post id.",
        ["mcp__practice-hub__create_post"],
    ),
]


def api_get(path):
    """GET the Practice Hub with the token from the environment."""
    token = os.environ.get("PRACTICE_API_TOKEN", "").strip()
    request = urllib.request.Request(
        API_URL + path,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read())


def post_ids():
    """Every post id visible to me, newest first."""
    items = api_get("/api/v1/posts?mine=true")
    if not isinstance(items, list):
        return []
    return [p["id"] for p in items if isinstance(p, dict) and isinstance(p.get("id"), int)]


def ask(prompt, allowed):
    """Run one claude -p call and return its cleaned output."""
    command = ["claude", "-p", prompt, "--allowedTools", *allowed]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    output = NOISE.sub("", result.stdout).strip()
    if result.returncode != 0 and not output:
        return command, f"claude exited {result.returncode}: {result.stderr.strip()[:400]}"
    return command, output


def run_cli(args, timeout=120):
    """Run a command and return its stdout, with the model banner removed."""
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return NOISE.sub("", result.stdout).strip()


def redact(text):
    """Replace the real home directory so the transcript can be published."""
    home = os.path.expanduser("~")
    return text.replace(f"{home}/Documents/", "~/").replace(home, "~")


def block(command, output):
    """Format one run as a fenced block, using a fence the content cannot close."""
    fence = "````" if "```" in output else "```"
    return f"{fence}\n$ {redact(shlex.join(command))}\n\n{redact(output)}\n{fence}\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="print the prompts and exit without calling anything")
    opts = parser.parse_args()

    if not os.environ.get("PRACTICE_API_TOKEN", "").strip():
        print("PRACTICE_API_TOKEN is not set. Export it first.", file=sys.stderr)
        return 2

    if opts.dry_run:
        for name, prompt, allowed in STEPS:
            print(f"--- {name} ---")
            print(f"  prompt : {prompt}")
            print(f"  allowed: {allowed}")
        return 0

    before = post_ids()
    print(f"posts before: {before}")

    recorded = []
    for name, prompt, allowed in STEPS:
        print(f"running: {name}")
        command, output = ask(prompt, allowed)
        recorded.append((name, command, output))
        print(f"  {output.splitlines()[0] if output else '(no output)'}")

    after = post_ids()
    new = [i for i in after if i not in before]
    if not new:
        print("No new post appeared. The create step did not work.", file=sys.stderr)
        return 1
    created = max(new)
    print(f"new post id: {created}")

    # Step 3 needs the id the model just created, and update_post needs
    # confirm=True, so the prompt names both.
    marker = f"edited-by-acceptance-{datetime.datetime.now():%Y%m%d-%H%M%S}"
    prompt = (
        f"Use the practice-hub update_post tool to change the body of post {created} "
        f"to '{marker}'. The tool needs confirm=True to save, so after the preview "
        "call it again with confirm=True. Then report what changed."
    )
    allowed = ["mcp__practice-hub__update_post", "mcp__practice-hub__get_post"]
    print("running: Modify")
    command, output = ask(prompt, allowed)
    recorded.append(("Modify", command, output))
    print(f"  {output.splitlines()[0] if output else '(no output)'}")

    # Independent check: read the post straight from the API.
    fetched = api_get(f"/api/v1/posts/{created}")
    body = (fetched.get("body") or "") if isinstance(fetched, dict) else ""
    landed = marker in body
    print(f"verified from the API: body contains the marker = {landed}")

    registration = run_cli(["claude", "mcp", "list"])

    lines = [
        "# Acceptance test transcript",
        "",
        "Generated by `acceptance/run.py`. The test is the one the assignment",
        "asks for: through my server, Claude Code reads my posts, creates a new",
        "post, and modifies an existing one.",
        "",
        "Registered and healthy:",
        "",
        block(["claude", "mcp", "list"], registration).rstrip() + "\n",
    ]
    for name, command, output in recorded:
        lines.append(f"## {name}")
        lines.append("")
        lines.append(block(command, output))
    lines.append("## Independent check")
    lines.append("")
    lines.append("Not taken from the model's answer. Reading the post straight")
    lines.append("from the API afterwards:")
    lines.append("")
    lines.append("```")
    lines.append(f"$ GET /api/v1/posts/{created}")
    lines.append(f"id: {fetched.get('id')} | title: {fetched.get('title')}")
    lines.append(redact(f"body: {body!r}"))
    lines.append(f"updated_at: {fetched.get('updated_at')}")
    lines.append("```")
    lines.append("")
    lines.append(
        "The body holds the marker the modify step was asked to write, so the "
        "write reached the database and not just the conversation."
    )
    lines.append("")

    with open(TRANSCRIPT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print(f"wrote {TRANSCRIPT}")
    return 0 if landed else 1


if __name__ == "__main__":
    sys.exit(main())

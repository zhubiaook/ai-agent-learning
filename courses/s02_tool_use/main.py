import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

from anthropic import Anthropic
from anthropic.types import (
    MessageParam,
    ModelParam,
    TextBlockParam,
    ToolParam,
    ToolResultBlockParam,
)
from dotenv import load_dotenv
from loguru import logger

load_dotenv(override=True)

# Loguru: emit structured (JSON) logs to stdout.
logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True, serialize=True)

# Anthropic client: reads credentials from env (e.g. ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN).
client = Anthropic()

# Model: default to a known model; allow override via ANTHROPIC_MODEL.
model: ModelParam = "claude-sonnet-4-6"
if model_name := os.getenv("ANTHROPIC_MODEL"):
    model = model_name


def safe_path(p: str) -> Path:
    workdir = Path.cwd()
    path = (workdir / p).resolve()
    if not path.is_relative_to(workdir):
        logger.error(f"Path escapes workspace: {p}")
        exit(1)
    return path


def run_bash(command: str) -> str:
    """Run a shell command with basic safety guardrails.

    This is intentionally minimal (educational demo), not a secure sandbox.
    """
    # Minimal guardrails for an educational demo (not a full sandbox).
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "no output"
    except subprocess.TimeoutExpired:
        return "Error: timeout(120s)"


def run_read(path: str, limit: int | None = None) -> str:
    try:
        text = safe_path(path).read_text()
        lines = text.splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text()
        fp.write_text(content.replace(old_text, new_text))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


def get_tools() -> list[ToolParam]:
    return [
        {
            "name": "bash",
            "description": "Run a shell command.",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
        {
            "name": "read_file",
            "description": "Read file contents.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}},
                "required": ["path"],
            },
        },
        {
            "name": "write_file",
            "description": "Write content to file.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
        {
            "name": "edit_file",
            "description": "Replace exact text in file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    ]


def get_tool_handler(name: str) -> Callable[..., str] | None:
    handlers = {
        "bash": lambda **kw: run_bash(kw["command"]),
        "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
        "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
        "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    }
    if handlers.get(name):
        return handlers[name]
    logger.error(f"Unknown tool: {name}")
    return None


def agent_loop(
    messages: list[MessageParam],
    system: str,
    model: ModelParam,
    tools: list[ToolParam],
) -> None:
    """Run the tool-use loop until the model stops requesting tools.

    Appends assistant messages and tool results back into `messages` in-place.
    """
    while True:
        response = client.messages.create(
            system=system,
            model=model,
            messages=messages,
            tools=tools,
            max_tokens=1024,
        )

        messages.append(MessageParam(role="assistant", content=response.content))
        if response.stop_reason != "tool_use":
            return

        results: list[ToolResultBlockParam] = []
        for block in response.content:
            if block.type == "tool_use":
                name = block.name
                args = block.input
                handler = get_tool_handler(name)
                print(f"\033[33m{name}({args})\033[0m")
                out = handler(**args) if handler else "Error: unknown tool: {name}"
                results.append(
                    ToolResultBlockParam(
                        type="tool_result",
                        tool_use_id=block.id,
                        content=out,
                    )
                )
        messages.append(MessageParam(role="user", content=results))


def run() -> None:
    """Interactive REPL that sends user prompts to the agent loop."""
    system = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

    tools = get_tools()

    history: list[MessageParam] = []

    while True:
        try:
            query = input(">> ")
        except (EOFError, KeyboardInterrupt):
            logger.info("Exiting...")
            return

        if query.strip().lower() in ("quit", "exit", "q", ""):
            logger.info("Exiting...")
            return

        history.append(
            MessageParam(
                role="user",
                content=[TextBlockParam(text=query, type="text")],
            )
        )

        agent_loop(history, system=system, model=model, tools=tools)

        final_content = history[-1].get("content")
        if isinstance(final_content, list):
            for block in final_content:
                if getattr(block, "text", None):
                    print(getattr(block, "text"))
        print()


if __name__ == "__main__":
    run()

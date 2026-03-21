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


class TodoManager:
    def __init__(self):
        self.todos = []

    def update(self, todo_list: list[dict[str, str]]) -> str:
        if len(todo_list) > 20:
            raise ValueError("Max 20 todos allowed")
        validated = []
        in_progress_count = 0
        for i, item in enumerate(todo_list):
            text = item.get("text", "").strip()
            status = item.get("status", "pending").lower()
            item_id = item.get("id", str(i + 1))
            if not text:
                raise ValueError(f"Item {item_id}: text required")
            if status not in {"pending", "in_progress", "completed"}:
                raise ValueError(f"Item {item_id}: invalid status '{status}'")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"id": item_id, "text": text, "status": status})
        if in_progress_count > 1:
            raise ValueError("Only one task can be in_progress at a time")
        self.todos = validated
        return self.render()

    def render(self) -> str:
        if not self.todos:
            return "No todos."
        lines = []
        for item in self.todos:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}[item["status"]]
            lines.append(f"{marker} #{item['id']}: {item['text']}")
        done = sum(1 for t in self.todos if t["status"] == "completed")
        lines.append(f"\n({done}/{len(self.todos)} completed)")
        return "\n".join(lines)


TODO = TodoManager()


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
        {
            "name": "todo",
            "description": "Update task list. Track progress on multi-step tasks.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "todo_list": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "text": {"type": "string"},
                                "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                            },
                            "required": ["id", "text", "status"],
                        },
                    }
                },
                "required": ["todo_list"],
            },
        },
    ]


def get_tool_handler(name: str) -> Callable[..., str] | None:
    handlers = {
        "bash": lambda **kw: run_bash(kw["command"]),
        "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
        "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
        "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
        "todo": lambda **kw: TODO.update(kw["todo_list"]),
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
    rounds_since_todo = 0
    first_round = True
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

        results: list[ToolResultBlockParam | TextBlockParam] = []
        used_todo = False
        for block in response.content:
            if block.type == "tool_use":
                name = block.name
                args = block.input
                handler = get_tool_handler(name)
                print(f"\033[33m{name}({str(args)[:100]})\033[0m")
                out = handler(**args) if handler else "Error: unknown tool: {name}"
                if name == "todo":
                    used_todo = True
                    print(f"\033[90m{str(out)[:200]}\033[0m")
                results.append(
                    ToolResultBlockParam(
                        type="tool_result",
                        tool_use_id=block.id,
                        content=out,
                    )
                )
        rounds_since_todo = 0 if used_todo else rounds_since_todo + 1

        # Force todo usage on the very first round
        if first_round and not used_todo:
            results.insert(
                0,
                TextBlockParam(
                    text="<system>You MUST call the todo tool FIRST to plan your tasks before using any other tools. "
                    "Create a todo list now.</system>",
                    type="text",
                ),
            )
        elif rounds_since_todo >= 1:
            results.insert(
                0,
                TextBlockParam(
                    text="<reminder>Update your todo list to reflect current progress before continuing.</reminder>",
                    type="text",
                ),
            )
        first_round = False

        messages.append(MessageParam(role="user", content=results))


def run() -> None:
    """Interactive REPL that sends user prompts to the agent loop."""
    system = f"""You are a coding agent at {os.getcwd()}.
You MUST use the todo tool as your VERY FIRST action for every task.
Workflow: 1) Call todo to create a plan, 2) Work through each item (mark in_progress → completed), 3) Keep todo updated every few steps.
Never skip the todo tool. Prefer tools over prose."""

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

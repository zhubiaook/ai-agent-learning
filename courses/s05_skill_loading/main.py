import os
import re
import subprocess
import sys
from dataclasses import dataclass
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
    """Resolve a user path and ensure it stays within the current workspace."""
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
    """Read a workspace file and optionally truncate by line count."""
    try:
        text = safe_path(path).read_text()
        lines = text.splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    """Write text content to a workspace file, creating parent folders if needed."""
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    """Replace exact text in a workspace file."""
    try:
        fp = safe_path(path)
        content = fp.read_text()
        fp.write_text(content.replace(old_text, new_text))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


@dataclass
class SkillMetadata:
    name: str
    description: str
    path: Path
    body_position: int = 0


_SKILL_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class SkillLoader:
    def __init__(self, skills_root: Path | str) -> None:
        """Initialize the loader and cache skill metadata from disk."""
        self._root = Path(skills_root)
        self._metadatas: dict[str, SkillMetadata] = {}
        self._load_metadata()

    def _parse_metadata(self, path: Path) -> SkillMetadata | None:
        """Parse YAML frontmatter from a single SKILL.md file."""
        m = _SKILL_FRONTMATTER_RE.match(path.read_text())
        if not m:
            return None
        block = m.group(1)
        if not block:
            return None

        fields = {}
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            k, _, v = line.partition(":")
            fields[k.strip()] = v.strip()
        if not fields:
            return None
        return SkillMetadata(
            name=fields.get("name", path.parent.name),
            description=fields.get("description", ""),
            path=path,
            body_position=m.end(),
        )

    def _load_metadata(self) -> None:
        """Scan SKILL.md files under the root and populate metadata cache."""
        if not self._root.is_dir():
            return
        for f in sorted(self._root.rglob("SKILL.md")):
            meta = self._parse_metadata(f)
            if not meta:
                continue
            self._metadatas[meta.name] = meta

    def metadatas(self) -> dict[str, SkillMetadata]:
        """Return all discovered skill metadata keyed by skill name."""
        return self._metadatas

    def content(self, name: str) -> str:
        """Return skill body content by name, or empty string if not found."""
        meta = self._metadatas.get(name)
        if not meta:
            return ""
        return meta.path.read_text()[meta.body_position :]


SKILL_LOADER = SkillLoader((Path.cwd() / "examples" / "skills" / "skills").resolve())


def get_tools() -> list[ToolParam]:
    """Return tool schemas exposed to the model."""
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
            "name": "load_skill",
            "description": "Load specialized knowledge by name.",
            "input_schema": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Skill name to load"}},
                "required": ["name"],
            },
        },
    ]


def get_tool_handler(name: str) -> Callable[..., str] | None:
    """Map a tool name to its executor function."""
    handlers = {
        "bash": lambda **kw: run_bash(kw["command"]),
        "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
        "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
        "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
        "load_skill": lambda **kw: SKILL_LOADER.content(kw["name"]),
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

    skills = "\n".join([f"- {meta.name}: {meta.description}" for meta in SKILL_LOADER.metadatas().values()])
    system = f"""You are a coding agent at {Path.cwd()}.
Use load_skill to access specialized knowledge before tackling unfamiliar topics.

Skills available:
{skills}
"""

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

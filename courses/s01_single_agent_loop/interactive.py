import os
import subprocess
import sys

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
                command = block.input.get("command")
                if not isinstance(command, str):
                    out = "Error: invalid tool input, 'command' must be a string"
                else:
                    out = run_bash(command)

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

    tools: list[ToolParam] = [
        {
            "name": "bash",
            "description": "Run a shell command.",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        }
    ]

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

        message = MessageParam(
            role="user",
            content=[TextBlockParam(text=query, type="text")],
        )
        history.append(message)

        agent_loop(history, system=system, model=model, tools=tools)

        final_content = history[-1].get("content")
        if isinstance(final_content, list):
            for block in final_content:
                if getattr(block, "text", None):
                    print(getattr(block, "text"))


if __name__ == "__main__":
    run()

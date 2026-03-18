import json
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

# loguru setup
logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True, serialize=True)

# anthropic client setup
client = Anthropic()


def print_message(message: MessageParam) -> None:
    contents = message["content"]
    if isinstance(contents, str):
        print(contents)
        return

    if isinstance(contents, list):
        for block in contents:
            model_dump = getattr(block, "model_dump", None)
            if callable(model_dump):
                payload = model_dump(mode="json")
            elif isinstance(block, dict):
                payload = block
            else:
                payload = {"value": str(block)}
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print({"error": "unknown content type", "content": contents})


def run_bash(command: str) -> str:
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
            break

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
    history: list[MessageParam] = []

    system = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

    query = "Show me the files in the current directory."
    message = MessageParam(
        role="user",
        content=[TextBlockParam(text=query, type="text")],
    )
    history.append(message)

    tools: list[ToolParam] = [
        {
            "name": "bash",
            "description": "Run a shell command.",
            "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
        }
    ]

    model = os.getenv("ANTHROPIC_MODEL")
    if model is None:
        logger.error("ANTHROPIC_MODEL is not set")
        return

    agent_loop(history, system=system, model=model, tools=tools)

    for message in history:
        print_message(message)


if __name__ == "__main__":
    run()

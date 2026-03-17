#!/bin/bash
# PreToolUse hook for db-reader agent.
# Blocks SQL write operations; allows SELECT queries to pass through.
#
# Input:  JSON via stdin (Claude Code hook format)
# Output: exit 0 = allow, exit 2 = block (stderr message returned to Claude)

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Nothing to check if command is empty
[ -z "$COMMAND" ] && exit 0

# Block write operations (case-insensitive)
if echo "$COMMAND" | grep -iE '\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|REPLACE|MERGE)\b' > /dev/null; then
  echo "Blocked: write operations are not allowed. Use SELECT queries only." >&2
  exit 2
fi

exit 0

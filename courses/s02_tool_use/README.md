## Tool Use (dispatch layer)

The agent loop from `s01` didn't change. We just added more tools to the `tools` array and a dispatch map to route calls.

### Diagram

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant A as LLM
    participant T as Tool (selects handler by name)

    U->>A: prompt / messages
    loop while stop_reason == "tool_use"
        A->>T: tool_use (name + input)
        Note over T: internally dispatches to run_bash/run_read/run_write/run_edit
        T-->>A: tool_result (output)
        A->>A: append tool_result to messages
    end
    A-->>U: final answer (stop_reason != "tool_use")
```

```text
+----------+      +-------+      +-------------------+
|   User   | ---> |  LLM  | ---> | Tool Dispatch     |
|  prompt  |      |       |      | {                 |
+----------+      +---+---+      |   bash: run_bash  |
                      ^          |   read: run_read  |
                      |          |   write: run_write|
                      +----------+   edit: run_edit  |
                      tool_result| }                 |
                                 +-------------------+
```

### Example walkthrough (dispatch)

- **LLM requests a tool** (e.g. `bash`) via a `tool_use` block.
- **Tool picks a handler** by `name` (e.g. `"bash" -> run_bash`) and runs it.
- **Return `tool_result`** to the LLM and continue the same loop.

**Key insight**: The loop didn't change at all. We just added tools.

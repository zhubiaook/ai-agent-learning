## Subagent (fresh context via `task`)

Spawn a child agent with fresh `messages=[]`. The child works in its own context, sharing the filesystem, then returns only a summary to the parent.

### Diagram

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant P as Parent LLM
    participant S as Subagent LLM
    participant T as Tools (child)

    U->>P: prompt / growing history
    loop parent while stop_reason == tool_use
        P->>P: tool_use task(prompt, description)
        Note over P,S: Child starts with messages=[] — fresh context
        loop subagent while stop_reason == tool_use
            S->>T: tool_use (bash, read_file, ...)
            Note over T: same cwd / filesystem as parent
            T-->>S: tool_result
            S->>S: append results (child messages only)
        end
        S-->>P: tool_result = summary (final text)
        Note over P: Parent never sees full child transcript
    end
    P-->>U: final answer
```

```text
    Parent agent                     Subagent
    +------------------+             +------------------+
    | messages=[...]   |             | messages=[]      |  <-- fresh
    |                  |  dispatch   |                  |
    | tool: task       | ----------->| while tool_use:  |
    |   prompt="..."   |             |   call tools     |
    |   description="" |             |   append results |
    |                  |  summary    |                  |
    |   result = "..." | <-----------| return last text |
    +------------------+             +------------------+
              |
    Parent context stays clean.
    Subagent context is discarded.

```

**Key insight**: "Process isolation gives context isolation for free."

## Todo and Memory (todo tool)

The model tracks its own progress via a `TodoManager`. A nag reminder forces it to keep updating when it forgets.

### Diagram

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant A as LLM
    participant T as Tools
    participant M as TodoManager

    U->>A: prompt / messages
    loop while stop_reason == "tool_use"
        A->>M: tool_use (todo)
        M-->>A: tool_result (rendered todo list)
        Note over M: [>] task B <- doing

        A->>T: tool_use (bash, read_file, etc.)
        T-->>A: tool_result (output)
        
        A->>A: append results to messages

        opt if rounds_since_todo >= 1
            Note over A: Inject <reminder> Update your todo list
        end
    end
    A-->>U: final answer (stop_reason != "tool_use")
```

```text
    +----------+      +-------+      +---------+
    |   User   | ---> |  LLM  | ---> | Tools   |
    |  prompt  |      |       |      | + todo  |
    +----------+      +---+---+      +----+----+
                          ^               |
                          |   tool_result |
                          +---------------+
                                |
                    +-----------+-----------+
                    | TodoManager state     |
                    | [ ] task A            |
                    | [>] task B <- doing   |
                    | [x] task C            |
                    +-----------------------+
                                |
                    if rounds_since_todo >= 1:
                      inject <reminder>
```

**Key insight**: "The agent can track its own progress -- and I can see it."

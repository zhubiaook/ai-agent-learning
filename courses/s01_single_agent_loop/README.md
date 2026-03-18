## The Agent Loop (the whole secret)

The entire secret of an AI coding agent in one pattern:

```python
while stop_reason == "tool_use":
    response = LLM(messages, tools)
    execute tools
    append results
```

### Diagram

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant A as LLM
    participant T as Tool (e.g. bash)

    U->>A: prompt / messages
    loop while stop_reason == "tool_use"
        A->>T: tool_use (name + input)
        T-->>A: tool_result (output)
        A->>A: append tool_result to messages
    end
    A-->>U: final answer (stop_reason != "tool_use")
```

```text
+----------+      +-------+      +---------+
|   User   | ---> |  LLM  | ---> |  Tool   |
|  prompt  |      |       |      | execute |
+----------+      +---+---+      +----+----+
                      ^               |
                      |   tool_result |
                      +---------------+
                      (loop continues)
```

This is the core loop: feed tool results back to the model until the model decides to stop.
Production agents layer policy, hooks, and lifecycle controls on top.

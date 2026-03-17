# Subagents（子智能体）学习与实践

Subagents 是 Claude Code 中专门处理特定任务的 AI 子智能体。每个 subagent 运行在独立的上下文窗口中，拥有自定义系统提示词和特定工具权限。当 Claude 遇到与某个 subagent 的 `description` 匹配的任务时，会将任务**委托**给该 subagent 独立执行，再将结果返回。

官方文档：[Create custom subagents](https://code.claude.com/docs/en/sub-agents)

本仓库已在 `.claude/agents/` 下提供三阶段完整示例：`hello-agent`、`code-reviewer`、`db-reader`。

---

### 第一阶段：简单入门 —— 创建可验证的最小 Subagent

建议从一个**极简 subagent** 开始，核心目的是：**亲眼确认 Claude 确实委托了 subagent，而不是自己直接回答**。

- **设计原则**：让 subagent 在回复中输出一个**独特的可识别标记**，这样就能一眼判断它是否被触发。

- **推荐入门示例**：创建一个「打招呼」subagent，测试自动委托机制。本仓库示例：`.claude/agents/hello-agent.md`

  **第一步**：将 `.claude/agents/hello-agent.md` 复制到 `~/.claude/agents/hello-agent.md`（用户级，所有项目可用），或直接使用本仓库的项目级配置。核心内容如下：

  ```markdown
  ---
  name: hello-agent
  description: 当用户打招呼、说"你好"、"hello"、"hi"时（无需显式提及 agent 名称），立刻接管并回应。Use proactively when the user greets with hello, hi, 你好, or similar.
  tools: []
  model: haiku
  ---

  You are a greeting agent. When invoked, respond warmly and always include
  this marker at the end of your response:

  ✅ [Subagent: hello-agent activated]
  ```

  **第二步**：保存后无需重启，直接对 Claude **只说「你好」或「hi」**（不提 agent 名称）。

- **验证方法**：
  - ✅ 若回复末尾出现 `✅ [Subagent: hello-agent activated]`，说明 Claude **自动委托**给了该 subagent
  - ✅ Claude Code UI 会显示 subagent 正在运行的视觉指示（与主会话区分）
  - ❌ 若无标记，检查 `description` 是否足够明确，或尝试显式调用：`Use the hello-agent to greet me`

- **文件存放位置说明**：
  - `~/.claude/agents/hello-agent.md`：用户级，所有项目可用（推荐入门时使用）
  - `.claude/agents/hello-agent.md`：项目级，仅当前项目可用，可提交到版本控制

---

### 第二阶段：进阶理解 —— 委托机制与工具控制

理解 subagent 的自动委托逻辑和工具权限，才能写出真正有用的 subagent。

- **委托触发机制**：Claude 根据用户请求与 subagent 的 `description` 自动匹配。`description` 越精确，委托越准确。
  - 在 description 中写 `Use proactively` 可提升主动委托频率
  - 用户也可显式调用：`Use the code-reviewer subagent to look at my recent changes`

- **工具控制**：subagent 默认继承主会话的全部工具，可通过以下字段限制：

  ```yaml
  tools: Read, Grep, Glob, Bash    # 白名单：只允许这些工具
  disallowedTools: Write, Edit     # 黑名单：从继承列表中排除
  ```

  只读型 subagent（如 reviewer）应限制写工具，防止误操作。

- **作用域与优先级**（同名时，高优先级覆盖低优先级）：

  | 位置 | 作用域 | 优先级 |
  |------|--------|--------|
  | `--agents` CLI 参数 | 当前会话 | 1（最高） |
  | `.claude/agents/` | 当前项目 | 2 |
  | `~/.claude/agents/` | 所有项目 | 3 |
  | 插件的 `agents/` | 插件启用处 | 4（最低） |

- **前台 vs 后台运行**：
  - **前台**：阻塞主会话，权限确认和追问会透传给用户
  - **后台**：与主会话并发运行，需预先授权所需工具；可在任务运行中按 `Ctrl+B` 切换到后台

- **模型选择（model 字段）**：

  ```yaml
  model: haiku     # 快速轻量，适合简单/高频任务
  model: sonnet    # 平衡能力与速度，推荐通用场景
  model: opus      # 最强推理，适合复杂分析
  model: inherit   # 与主会话使用相同模型（默认）
  ```

---

### 第三阶段：高阶应用 —— Hooks、Memory 与最佳实践

需要更精细控制时，可使用权限模式、Hooks 和持久化记忆。

- **权限模式（permissionMode）**：

  | 模式 | 行为 |
  |------|------|
  | `default` | 标准权限检查，需用户确认 |
  | `acceptEdits` | 自动接受文件编辑 |
  | `dontAsk` | 自动拒绝权限提示（不打扰用户） |
  | `bypassPermissions` | 跳过所有权限检查（慎用） |
  | `plan` | 计划模式，只读探索 |

- **持久化记忆（memory）**：subagent 可在多次会话间积累知识：

  ```yaml
  memory: user      # ~/.claude/agent-memory/<name>/  适用所有项目
  memory: project   # .claude/agent-memory/<name>/    项目专属，可提交版本控制
  memory: local     # .claude/agent-memory-local/<name>/  项目专属，不提交
  ```

  启用后，subagent 的 system prompt 会自动注入记忆目录路径，并附上前 200 行的 `MEMORY.md` 内容。

- **Hooks**：在工具调用前后插入校验或清理逻辑：

  ```yaml
  hooks:
    PreToolUse:
      - matcher: "Bash"
        hooks:
          - type: command
            command: "./scripts/validate-command.sh"
    PostToolUse:
      - matcher: "Edit|Write"
        hooks:
          - type: command
            command: "./scripts/run-linter.sh"
  ```

  Hook 脚本通过 stdin 接收 JSON，exit code 2 表示阻止该次工具调用并将 stderr 返回给 Claude。

- **最佳实践**：
  - 每个 subagent 专注**单一任务**，`description` 写得清晰具体
  - 限制工具权限至任务所需最小集合
  - 项目级 subagent（`.claude/agents/`）纳入版本控制，便于团队共享
  - **Subagent 不能再委托给其他 subagent**；如需链式调用，在主会话中串联

---

### 实用示例一：Code Reviewer（只读代码审查）

本仓库示例：`.claude/agents/code-reviewer.md`

关键配置：`tools: Read, Grep, Glob, Bash` + `disallowedTools: Write, Edit`，确保该 subagent 只能读取代码，不能修改文件。system prompt 要求按 🔴/🟡/🟢 三级输出反馈，并在末尾附上执行标记 `✅ [Subagent: code-reviewer activated]`。

**验证**：修改任意文件后说 `Use the code-reviewer subagent to review my changes`，观察 subagent 是否接管并返回分结构的反馈。

---

### 实用示例二：db-reader（带 PreToolUse Hook 的只读 SQL）

本仓库示例：`.claude/agents/db-reader.md` + `.claude/agents/scripts/validate-readonly-query.sh`

这是一个高阶示例，演示如何用 `PreToolUse` Hook 对工具调用做运行时校验：
- `tools: Bash` 允许执行 shell 命令（需要用它来运行 SQL）
- `hooks.PreToolUse` 在每次 Bash 执行前调用校验脚本
- 脚本检测到 INSERT/UPDATE/DELETE 等写操作时，返回 exit code 2 阻止执行，并将 stderr 反馈给 Claude

**验证**：让 db-reader 执行 `DELETE FROM users WHERE id=1`，观察 Hook 是否拦截并返回 `Blocked: write operations are not allowed`。

---

### 内置 Subagents 速查

Claude Code 自带以下 subagent，无需创建即可使用：

| 名称 | 模型 | 工具 | 触发场景 |
|------|------|------|----------|
| **Explore** | Haiku | 只读 | 需要搜索/探索代码库但不修改（thoroughness: quick / medium / very thorough） |
| **Plan** | 继承 | 只读 | Plan 模式下收集代码库上下文 |
| **General-purpose** | 继承 | 全部 | 复杂多步任务，需探索+修改 |

---

### 相关资源

- 官方文档：[Create custom subagents](https://code.claude.com/docs/en/sub-agents)
- 多会话并行协作：[Agent teams](https://code.claude.com/docs/en/agent-teams)
- **Subagent vs Skill**：Skill 在主会话上下文中运行，提供可复用的提示和流程；Subagent 在独立上下文中运行，适合隔离高输出量任务或严格限制工具权限

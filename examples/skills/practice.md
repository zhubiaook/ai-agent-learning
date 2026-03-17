Claude的Agent Skills（智能体技能）是一种模块化的功能扩展，它通过打包特定的指令、元数据和可选资源（如脚本、模板），将通用型AI转化为特定领域的专家。

以下是从简单到复杂的Agent Skills使用教程总结。本仓库已在 `.cursor/skills/` 下提供三阶段完整示例：`greeting`、`doc-summary`、`markdown-report`。详细操作步骤见 [docs/STEP-BY-STEP.md](docs/STEP-BY-STEP.md)。

### 第一阶段：简单入门 —— 使用自定义简单工具 (Custom Simple Skill)

建议从编写一个**极简自定义技能**开始，其核心目的是：在响应的内容中**明显体现** Agent 是否执行了该技能。

- **设计原则**：技能应要求 Agent 在执行时输出**可识别的标记**，例如：
  - 在回复开头或结尾添加固定格式的确认块，如：`--- [Skill: xxx executed] ---`
  - 或在输出中包含该技能特有的结构化内容（如特定标题、区块、emoji 组合），便于一眼识别
- **推荐入门示例**：创建一个「打招呼」技能，用于**测试 Agent 是否具备自动识别并应用技能的能力**（用户仅打招呼，不显式要求使用某技能）。本仓库示例：`.cursor/skills/greeting/`
  1. 在 `~/.cursor/skills/` 或 `.cursor/skills/` 下新建技能目录（如 `greeting`）
  2. 创建 `SKILL.md`，参考如下结构：

     ```markdown
     ---
     name: greeting
     description: 当用户仅打招呼、说你好、hi、hello 等问候语时（无需用户提及任何技能名称），以热情方式回应并输出执行标记。Use when the user greets with hello, hi, or similar — no explicit skill request needed.
     ---
     # Greeting

     每次应用本技能时，**必须**在回复的显著位置（开头或结尾）输出以下标记，否则视为未正确执行：

     ```
     ✅ [Skill: greeting executed]
     ```
     ```

  3. 保存后，**仅向 Agent 说「你好」或「hi」**（不要提及任何技能名称）。
- **验证方法**：若回复中出现 `✅ [Skill: greeting executed]` 标记，则说明 Agent **自动识别**了打招呼场景并加载执行了该技能；若无此标记，则说明未被触发。通过这种设计，可测试 Agent 是否具备**自动使用技能**的能力，而非依赖用户显式指定。
- **本仓库示例**：`.cursor/skills/greeting/`

### 第二阶段：进阶理解 —— 渐进式加载机制 (Progressive Disclosure)

在准备自己编写技能前，需要理解技能在底层是如何运作的。技能运行在一个具有文件系统访问权限的虚拟机（VM）中，并采用**“渐进式加载”**机制来节省Token和上下文窗口。

- **Level 1加载（元数据）**：Claude在启动时**始终只会加载**技能的YAML元数据（名称 `name` 和描述 `description`）。这让Claude知道有哪些技能可用，而不会带来沉重的上下文负担。
- **Level 2加载（核心指令）**：当用户的请求命中了某个技能的描述时，Claude才会触发并加载该技能目录下的 `SKILL.md` 主体文件，读取具体的工作流和指导原则。
- **Level 3加载（按需读取）**：如果在执行过程中需要更深度的参考资料（如特定的表单填写指南 `FORMS.md` 或具体的代码脚本），Claude才会进一步去读取这些二级文件。
- **本仓库示例**：`.cursor/skills/doc-summary/`，演示 SKILL.md → reference.md、examples.md 的渐进式加载。

### 第三阶段：高阶应用 —— 编写与构建自定义技能 (Custom Skills)

当预置技能无法满足需求时，您可以自行编写自定义技能来封装企业专属知识或复杂工作流。这需要遵循严格的架构和编写最佳实践：

- **精简内容与合理拆分**：
  - 上下文窗口是宝贵的资源，**不要向Claude解释它已经知道的基础知识**。
  - `SKILL.md` 的正文应保持在500行以内。
  - 利用渐进式加载机制，将冗长内容（如API文档、进阶功能、代码示例）拆分到独立的Markdown文件中（如 `reference.md`、`examples.md`），并在 `SKILL.md` 中提供导航指引。
- **规范元数据与术语**：
  - 必须在 `SKILL.md` 顶部使用YAML格式定义 `name`（最多64字符，限小写字母数字和连字符）和具体的 `description`（说明该技能的作用和**触发时机**）。
  - 全文使用一致的专业术语，避免将同一个概念写成多个不同的词，以免引起Claude的混淆。
- **设计严谨的工作流与反馈循环**：
  - 为复杂的任务提供清晰的**分步检查表**（Checklist），例如：“第一步：读取文档；第二步：提取主题；第三步：交叉验证”。
  - 包含**验证环节**，要求Claude在修改XML或输出关键结果后立即运行验证脚本，并在报错时返回上一步修复。
- **提供实用的辅助脚本**：
  - 技能文件夹中可以包含Python等实用脚本（如表单解析脚本 `analyze_form.py`）。
  - 脚本的代码编写要求“解决问题而不是推卸给Claude”：必须包含明确的错误处理（例如找不到文件时自动创建默认文件），并**明确指出依赖包**（如告知Claude需先运行 `pip install pdfplumber`），切勿提供模棱两可的代码或过多的工具选项。
- **本仓库示例**：`.cursor/skills/markdown-report/`，包含 Checklist 工作流、`scripts/validate_report.py` 验证脚本及反馈循环。


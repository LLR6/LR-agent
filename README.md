# LR-Agent

一个**真实可运行**的本地 AI Agent。它不是静态聊天页面：模型可以在受控工具权限下读取/修改工作区文件、执行白名单命令、访问公开 HTTP(S) 资源，并通过 SQLite 记住会话。

> 当前版本：`0.5.0`。在 0.4 的审批体系基础上，继续补上了 **有界后台并发、自动项目上下文检索、Web/API 鉴权、远程绑定保护和更完整的 CLI 管理能力**。

## 已实现

- OpenAI-compatible 模型接口，可接云端兼容接口或本地 Ollama 等服务
- Planner / Executor / Reviewer：Coder、Research 模式会先生成可验证计划，执行后再由 Reviewer 检查是否真的完成
- Tool Calling 自主循环：模型 -> 工具 -> 工具结果 -> 模型，最多执行 `LR_AGENT_MAX_STEPS` 步
- Reviewer 发现未完成项时可自动返工，次数由 `LR_AGENT_MAX_REVIEW_RETRIES` 控制
- 交互式审批：`off / writes / all` 三种模式；Web UI 会实时弹出待审批 Diff/命令/GitHub 写操作，CLI 也会询问 y/N
- 后台任务队列：Web 请求不再一直阻塞等待 Agent；任务状态会持久化，服务重启后未完成任务会标记为 interrupted
- 有界并发：默认最多同时运行 2 个后台任务，其余任务保持 queued；排队任务也可以取消
- WebSocket 实时执行流：Planner、Run、Tool Step、Reviewer、完成状态会实时推送给 Web UI
- 项目知识索引：可把 workspace 文本文件分块写入 SQLite，优先使用 FTS5/BM25 检索；Coder / Research 默认会自动检索相关上下文再规划和执行
- 检索安全：自动召回的项目内容会明确标记为 **UNTRUSTED PROJECT DATA**，不会被当作系统指令
- 文件工具：列目录、全文搜索、读文件、写文件、精确替换；写入/替换会返回统一 Diff
- Git 只读工具：git status / git diff
- 命令工具：**不经过 shell**，只允许配置白名单中的可执行程序；使用 asyncio 子进程，任务取消/超时时会终止当前子进程
- HTTP 工具：GET 公网资源；默认拦截 localhost / 私网 / link-local / reserved 地址
- SQLite 会话记忆 + 每次 Run 的计划、工具调用证据、最终状态和 Review 持久化
- 中断恢复：Web UI 可点“继续此任务”，CLI 可用 `lr-agent resume RUN_ID`
- GitHub 原生工具：仓库元数据、目录、文件、Actions；显式开启后可建 Issue、分支、写文件、开 PR
- General / Coder / Research 三种工作模式
- FastAPI 后端 + 本地 Web 控制台
- CLI：`serve` / `chat` / `tasks` / `runs` / `resume` / `index` / `search` / `doctor`
- Web/API 可选 Bearer Token 鉴权；WebSocket 同样受保护
- 非本机监听默认要求 Web Token；Docker Compose 默认只把 8765 发布到宿主机 loopback
- Docker / docker compose
- pytest 单元测试 + GitHub Actions CI
- 对 API Key、危险 Git 命令、目录穿越做基础防护

## 1. 本地安装

要求 Python 3.11+。

```bash
git clone https://github.com/LLR6/LR-agent.git
cd LR-agent

python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Linux / macOS：

```bash
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

然后编辑 `.env`，至少配置模型：

```env
LR_AGENT_BASE_URL=https://api.openai.com/v1
LR_AGENT_API_KEY=你的_API_KEY
LR_AGENT_MODEL=你实际可用的模型名
```

不要把真实 API Key 提交到 GitHub；`.env` 已加入 `.gitignore`。

## 2. 先运行自检

```bash
lr-agent doctor
```

成功时会看到模型 endpoint 返回测试响应。失败时会直接显示 HTTP 状态码或连接错误，不会假装连接成功。

## 3. 启动 Web UI

```bash
lr-agent serve
```

浏览器打开：

```text
http://127.0.0.1:8765
```

你可以切换：

- **General**：普通个人助手
- **Coder**：优先检查项目、修改代码、运行测试
- **Research**：优先收集公开资料并保留来源 URL

## 4. CLI 使用

一次性任务：

```bash
lr-agent chat --mode coder "检查 workspace 中的项目，找出测试失败原因并修复"
```

交互模式：

```bash
lr-agent chat --mode general
```

输入 `/exit` 退出。

查看后台 Task 与 Run：

```bash
lr-agent tasks
lr-agent runs
```

建立并搜索项目知识索引：

```bash
lr-agent index
lr-agent search "authentication flow"
```

恢复某一轮任务：

```bash
lr-agent resume <run_id>
```

## 5. 接本地 Ollama

如果你的 Ollama 提供 OpenAI-compatible `/v1` 接口，可以这样配置：

```env
LR_AGENT_BASE_URL=http://127.0.0.1:11434/v1
LR_AGENT_API_KEY=ollama
LR_AGENT_MODEL=你本机已经安装的模型名
```

这里的模型名必须与你本机实际安装的一致。

## 6. Agent 真正怎么执行任务

例如：

```text
检查 workspace 里的 Python 项目。
先看目录和测试，再修复失败项，修改后重新跑 pytest。
不要声称成功，除非测试真的通过。
```

执行路径：

```text
User
  ↓
LLM
  ↓ tool_calls
ToolRegistry
  ├─ list_files
  ├─ search_files
  ├─ read_file
  ├─ write_file
  ├─ replace_in_file
  ├─ git_status
  ├─ git_diff
  ├─ run_command
  ├─ http_get
  ├─ knowledge_index
  ├─ knowledge_search
  ├─ knowledge_stats
  ├─ github_get_repo
  ├─ github_list_contents
  ├─ github_read_file
  ├─ github_list_workflow_runs
  ├─ github_create_issue *
  ├─ github_create_branch *
  ├─ github_put_file *
  └─ github_create_pull_request *
  ↓
tool result
  ↓
LLM 再判断
  ↓
继续调用工具 / 返回最终答案
```

Web UI 右侧会显示 **Task / Run ID、Plan、实时工具调用、参数、Diff/输出证据、Reviewer 结论**。任务通过 WebSocket 实时刷新。带 `*` 的 GitHub 写操作默认关闭。

## 7. 工作区

默认情况下 Agent 只能通过文件工具访问：

```text
./workspace
```

可以修改：

```env
LR_AGENT_WORKSPACE=D:/Projects/my-project
```

注意：文件工具有路径边界检查，但命令工具不是完整的 OS 沙箱。详细限制见 [SECURITY.md](SECURITY.md)。

## 8. 命令白名单

默认：

```env
LR_AGENT_ALLOWED_COMMANDS=python,python3,pytest,git,gh,pip,uv,pwd,ls,dir,find,where
```

`run_command` 直接用 argv 调用程序，不使用 `shell=True`。

默认还会拦截一部分危险操作，例如：

```text
git reset --hard
git clean ...
git push --force
git push -f
git checkout -- .
git restore .
pip uninstall
```

只有显式设置下面配置才放开这类检查：

```env
LR_AGENT_ALLOW_DESTRUCTIVE=true
```

这并不等于完整安全沙箱。对于不可信仓库，建议使用 Docker 或临时虚拟机。

## 9. GitHub 原生工具

读取公开仓库不要求 Token。访问私有仓库或执行写操作时配置：

```env
LR_AGENT_GITHUB_TOKEN=你的_GitHub_Token
LR_AGENT_ALLOW_GITHUB_WRITE=false
```

默认 `false` 时，即使模型请求建 Issue / 分支 / PR / 改远程文件，也会被工具层拒绝。

确认你确实希望 Agent 修改 GitHub 后，再显式改为：

```env
LR_AGENT_ALLOW_GITHUB_WRITE=true
```

Token 不会作为普通工具参数传给模型。


## 10. 项目知识索引

Web UI 左侧可以直接点击 **“索引工作区知识库”**。也可以让 Agent 调用：

```text
knowledge_index
knowledge_search
knowledge_stats
```

索引默认会跳过 `.git`、`node_modules`、虚拟环境、构建目录和二进制文件，并按文本块写入：

```text
./data/knowledge.db
```

主要配置：

```env
LR_AGENT_KNOWLEDGE_DATABASE=./data/knowledge.db
LR_AGENT_KNOWLEDGE_MAX_FILES=3000
LR_AGENT_KNOWLEDGE_MAX_FILE_BYTES=1000000
LR_AGENT_AUTO_CONTEXT=true
LR_AGENT_AUTO_CONTEXT_RESULTS=6
```

建立索引后，Coder / Research 模式会在每轮任务开始时自动搜索相关上下文，并把召回的文件片段显示在 Web UI 的 **CONTEXT** 区域。召回内容会被当作不可信项目数据，Agent 仍需在改动前重新读取关键文件。

当前是本地 SQLite FTS5/BM25 检索，不依赖外部向量数据库；后续可以再加 embeddings 做混合检索。

## 11. 后台任务与实时日志

Web UI 默认通过：

```text
POST /api/tasks
WS   /ws/tasks/{task_id}
```

提交和监听任务。任务元数据会持久化到 SQLite。默认最多同时执行 2 个任务：

```env
LR_AGENT_MAX_CONCURRENT_TASKS=2
```

超过并发上限的任务保持 `queued`，不会提前占用执行槽。

常用接口：

```text
GET  /api/tasks
GET  /api/tasks/{task_id}
POST /api/tasks/{task_id}/cancel
GET  /api/runs
GET  /api/runs/{run_id}
POST /api/runs/{run_id}/resume-task
```

恢复旧 Run 时也会重新进入后台队列，并重新检查当前 workspace 状态，而不是盲目沿用旧结果。


## 12. 交互式审批

默认关闭，不影响自动执行：

```env
LR_AGENT_APPROVAL_MODE=off
```

可选：

```env
# 写文件、替换文件、GitHub 写操作需要审批
LR_AGENT_APPROVAL_MODE=writes

# 上述操作 + run_command 都需要审批
LR_AGENT_APPROVAL_MODE=all

LR_AGENT_APPROVAL_TIMEOUT_S=600
```

开启后，后台任务遇到受控工具会进入 `approval_required` 状态事件。Web UI 右侧会显示：

```text
APPROVAL
WAITING · write_file

--- a/app.py
+++ b/app.py
@@ ...
-old
+new

[拒绝] [批准执行]
```

审批请求会持久化到 SQLite。服务重启时遗留的 pending 审批会标记为 expired，避免旧审批被错误复用。

API：

```text
GET  /api/tasks/{task_id}/approvals
POST /api/tasks/{task_id}/approvals/{approval_id}
```

请求体：

```json
{"approved": true}
```

CLI 在审批模式开启时，也会在真正执行前显示预览并询问：

```text
Approve this action? [y/N]:
```


## 13. Web / API 鉴权与远程部署

本机默认访问 `127.0.0.1:8765` 时，可以保持：

```env
LR_AGENT_WEB_TOKEN=
```

如果要监听局域网或其他非 loopback 地址，建议设置强随机 Token：

```env
LR_AGENT_WEB_TOKEN=你的长随机字符串
```

REST API 使用：

```text
Authorization: Bearer <token>
```

Web UI 遇到 401 会提示输入 Token，并只保存在当前浏览器会话的 `sessionStorage`。任务 WebSocket 也会携带同一个 Token。

为了避免误把本地 Agent 暴露到网络，下面这种启动方式在没有 Token 时会直接拒绝：

```bash
lr-agent serve --host 0.0.0.0
```

只有明确设置：

```env
LR_AGENT_ALLOW_REMOTE_WITHOUT_TOKEN=true
```

才允许无 Token 的非本机绑定。这个开关不建议用于公开网络。

Docker Compose 内部需要监听 `0.0.0.0`，但默认只映射：

```text
127.0.0.1:8765:8765
```

因此宿主机默认仍是本机访问。

## 14. Docker

先创建 `.env`，然后：

```bash
docker compose up --build
```

访问：

```text
http://127.0.0.1:8765
```

Docker 会把：

```text
./workspace -> /app/workspace
./data      -> /app/data
```

持久化到宿主机。

## 15. 测试

```bash
pytest
```

当前测试覆盖：

- SQLite 会话、Run/Step、后台 Task 状态持久化
- 文件创建/读取/替换
- workspace 目录穿越拦截
- 非白名单命令拦截
- Planner -> Executor -> Tool -> Reviewer 完整闭环
- GitHub 写操作默认关闭
- 后台 Task 完成与服务重启后的 interrupted 恢复语义
- WebSocket 事件源对应的任务事件历史
- 项目知识索引、FTS/LIKE 搜索与依赖目录排除
- 文件统一 Diff 与 git status / diff
- 子进程任务取消
- write / command / GitHub 写操作审批生命周期与拒绝保护
- 后台并发上限、queued 任务取消
- 自动项目上下文检索及“不可信上下文”标记
- REST Bearer Token 与 WebSocket Token 鉴权

GitHub Actions 会在 Python 3.11 和 3.12 上运行同一套测试。

## 配置项

| 环境变量 | 默认值 | 作用 |
|---|---|---|
| `LR_AGENT_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| `LR_AGENT_API_KEY` | 空 | 模型 API Key |
| `LR_AGENT_MODEL` | `gpt-5.6` | 模型名 |
| `LR_AGENT_MAX_STEPS` | `12` | 单轮最大工具循环 |
| `LR_AGENT_MAX_CONCURRENT_TASKS` | `2` | 最大并发后台任务数 |
| `LR_AGENT_ENABLE_PLANNING` | `true` | Coder/Research 是否先规划 |
| `LR_AGENT_ENABLE_REVIEW` | `true` | 是否执行结果审查 |
| `LR_AGENT_MAX_REVIEW_RETRIES` | `1` | Reviewer 不通过后的最大返工次数 |
| `LR_AGENT_WORKSPACE` | `./workspace` | Agent 工作目录 |
| `LR_AGENT_DATABASE` | `./data/lr_agent.db` | 会话、Run、Task SQLite 数据库 |
| `LR_AGENT_KNOWLEDGE_DATABASE` | `./data/knowledge.db` | 项目知识索引数据库 |
| `LR_AGENT_KNOWLEDGE_MAX_FILES` | `3000` | 单次索引最大文件数 |
| `LR_AGENT_KNOWLEDGE_MAX_FILE_BYTES` | `1000000` | 单文件索引大小上限 |
| `LR_AGENT_AUTO_CONTEXT` | `true` | Coder/Research 是否自动检索项目上下文 |
| `LR_AGENT_AUTO_CONTEXT_RESULTS` | `6` | 自动召回最大结果数 |
| `LR_AGENT_ALLOWED_COMMANDS` | 见上文 | 命令白名单 |
| `LR_AGENT_ALLOW_DESTRUCTIVE` | `false` | 是否允许已标记危险命令 |
| `LR_AGENT_ALLOW_PRIVATE_NETWORK` | `false` | HTTP 工具是否允许访问私网 |
| `LR_AGENT_APPROVAL_MODE` | `off` | `off / writes / all` 交互式审批范围 |
| `LR_AGENT_APPROVAL_TIMEOUT_S` | `600` | 单次审批等待秒数 |
| `LR_AGENT_WEB_TOKEN` | 空 | Web/API/WS 鉴权 Token |
| `LR_AGENT_ALLOW_REMOTE_WITHOUT_TOKEN` | `false` | 是否允许无 Token 的非 loopback 监听 |
| `LR_AGENT_GITHUB_TOKEN` | 空 | GitHub API Token；私有仓库/写操作需要 |
| `LR_AGENT_GITHUB_API_BASE` | `https://api.github.com` | GitHub API 地址 |
| `LR_AGENT_ALLOW_GITHUB_WRITE` | `false` | 是否允许 GitHub 写操作 |

## 下一阶段

后续可以继续做：

1. embeddings + FTS5 的混合 RAG
2. 多工作区与项目配置文件
3. 可配置的审批策略（按命令、路径、仓库细分）
4. 浏览器自动化
5. Windows 桌面客户端与托盘常驻
6. 考研 / 网安专用 Agent profile

---

Author: **LLR6**

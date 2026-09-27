# LR-Agent

一个**真实可运行**的本地 AI Agent。它不是静态聊天页面：模型可以在受控工具权限下读取/修改工作区文件、执行白名单命令、访问公开 HTTP(S) 资源，并通过 SQLite 记住会话。

> 当前版本：`0.1.0`。定位是“先把 Agent 执行闭环跑通”，后续再扩展 GitHub 原生工具、多 Agent、RAG、任务队列和桌面端。

## 已实现

- OpenAI-compatible 模型接口，可接云端兼容接口或本地 Ollama 等服务
- Tool Calling 自主循环：模型 -> 工具 -> 工具结果 -> 模型，最多执行 `LR_AGENT_MAX_STEPS` 步
- 文件工具：列目录、全文搜索、读文件、写文件、精确替换
- 命令工具：**不经过 shell**，只允许配置白名单中的可执行程序
- HTTP 工具：GET 公网资源；默认拦截 localhost / 私网 / link-local / reserved 地址
- SQLite 会话记忆
- General / Coder / Research 三种工作模式
- FastAPI 后端 + 本地 Web 控制台
- CLI：`serve` / `chat` / `doctor`
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
  ├─ run_command
  └─ http_get
  ↓
tool result
  ↓
LLM 再判断
  ↓
继续调用工具 / 返回最终答案
```

Web UI 右侧会显示真实的工具调用、参数、成功/失败和结果预览。

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

## 9. Docker

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

## 10. 测试

```bash
pytest
```

当前测试覆盖：

- SQLite 会话读写
- 文件创建/读取/替换
- workspace 目录穿越拦截
- 非白名单命令拦截
- Agent -> tool call -> tool result -> final answer 完整闭环

GitHub Actions 会在 Python 3.11 和 3.12 上运行同一套测试。

## 配置项

| 环境变量 | 默认值 | 作用 |
|---|---|---|
| `LR_AGENT_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| `LR_AGENT_API_KEY` | 空 | 模型 API Key |
| `LR_AGENT_MODEL` | `gpt-5.6` | 模型名 |
| `LR_AGENT_MAX_STEPS` | `12` | 单轮最大工具循环 |
| `LR_AGENT_WORKSPACE` | `./workspace` | Agent 工作目录 |
| `LR_AGENT_DATABASE` | `./data/lr_agent.db` | SQLite 数据库 |
| `LR_AGENT_ALLOWED_COMMANDS` | 见上文 | 命令白名单 |
| `LR_AGENT_ALLOW_DESTRUCTIVE` | `false` | 是否允许已标记危险命令 |
| `LR_AGENT_ALLOW_PRIVATE_NETWORK` | `false` | HTTP 工具是否允许访问私网 |

## 下一阶段

后续可以继续做：

1. GitHub 原生 API 工具：仓库、Issue、PR、Actions
2. Planner / Coder / Reviewer 多 Agent
3. 任务队列与可恢复的长任务
4. 文件向量检索与长期知识库
5. Diff 审批、命令审批和细粒度权限
6. 浏览器自动化
7. Windows 桌面客户端与托盘常驻
8. 考研 / 网安专用 Agent profile

---

Author: **LLR6**

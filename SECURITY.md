# Security

LR-Agent can execute tools on your machine and may modify files or GitHub resources.
Treat it like a developer tool with real user-level access, not like a sandbox.

## Default protections

- File tools are restricted to `LR_AGENT_WORKSPACE`.
- Command execution uses an executable allowlist and does not invoke a shell.
- The command subprocess receives a reduced environment so the model does not
  automatically inherit `LR_AGENT_API_KEY` or `LR_AGENT_GITHUB_TOKEN`.
- A small set of destructive Git/package commands is blocked unless
  `LR_AGENT_ALLOW_DESTRUCTIVE=true`.
- HTTP retrieval blocks private, loopback, link-local, multicast, reserved and
  unspecified addresses by default.
- GitHub write operations are disabled unless both a GitHub token is configured
  and `LR_AGENT_ALLOW_GITHUB_WRITE=true`.
- The default Web server binds to loopback. `lr-agent serve` refuses a
  non-loopback host without `LR_AGENT_WEB_TOKEN` unless the user explicitly sets
  `LR_AGENT_ALLOW_REMOTE_WITHOUT_TOKEN=true`.
- Docker Compose publishes port 8765 on host loopback only.
- Optional approval mode can require explicit confirmation before local writes,
  GitHub writes, or commands.
- Retrieved project knowledge is injected into the model as **untrusted project
  data**, not instructions, to reduce prompt-injection risk.

## Interactive approvals

Use:

```env
LR_AGENT_APPROVAL_MODE=writes
```

to require approval before:

- `write_file`
- `replace_in_file`
- GitHub Issue / branch / file / pull-request writes

Use:

```env
LR_AGENT_APPROVAL_MODE=all
```

to additionally require approval before `run_command`.

The Web UI shows a Diff or action preview before execution. CLI mode shows the
same preview and asks for y/N confirmation. Pending approvals are persisted and
expired after a process restart.

Approval is an additional control, not a guarantee that approved code is safe.
A short-looking change can still invoke dangerous behavior later.

## Web and API authentication

For any network-visible deployment, set a strong random value:

```env
LR_AGENT_WEB_TOKEN=<long-random-secret>
```

REST endpoints then require:

```text
Authorization: Bearer <token>
```

and task WebSockets require the same token through the browser client. The Web
UI keeps the token in `sessionStorage`, not in repository files.

Do not expose LR-Agent directly to the public Internet without authentication
and a reverse proxy/TLS layer.

## Command execution limitations

The command tool is **not an operating-system sandbox**. Any allowlisted program
can access whatever the current OS user can access. Python, pytest, package
managers, build scripts, Git hooks and checked-out repositories can execute
arbitrary code.

LR-Agent now manages commands as asyncio child processes and kills the direct
child on cancellation or timeout. That does not guarantee termination of every
descendant process spawned independently by a build tool.

For untrusted repositories, run LR-Agent inside Docker or a disposable VM and
do not mount sensitive host directories.

## Project knowledge and prompt injection

Workspace indexing is local and skips common dependency/build directories, but
indexed files are still untrusted. A README, source comment, generated file or
downloaded document may contain instructions intended to manipulate an Agent.

LR-Agent marks retrieved context as untrusted and tells the model to use it only
as project evidence. You should still use approval mode for sensitive workflows
and review Diffs before allowing writes.

## Run rollback boundaries

LR-Agent can snapshot and roll back direct file-tool mutations. Before rollback,
it compares the current path type/hash with the final state recorded by the run.
If anything changed after that run, rollback is refused without modifying files.

This mechanism does **not** roll back arbitrary command side effects. Commands,
package managers, build systems, Git hooks and external processes can modify files
outside the journal. Use Git, containers/VM snapshots or another system-level
backup when those side effects matter.

The automatic snapshot file-size limit is controlled by
`LR_AGENT_SNAPSHOT_MAX_FILE_BYTES`. A direct mutation can be refused when LR-Agent
cannot first create the configured rollback snapshot.

## Secrets

Never commit:

- `.env`
- model API keys
- GitHub tokens
- Web/API tokens
- cloud or deployment credentials

The provided `.gitignore` excludes `.env`, but you remain responsible for
other credential files placed inside the workspace.

## Recommended modes

For ordinary local development:

```env
LR_AGENT_APPROVAL_MODE=writes
LR_AGENT_ALLOW_DESTRUCTIVE=false
LR_AGENT_ALLOW_GITHUB_WRITE=false
```

For a remote/private server, additionally configure:

```env
LR_AGENT_WEB_TOKEN=<strong-random-token>
```

Only enable GitHub writes when a task actually needs them.

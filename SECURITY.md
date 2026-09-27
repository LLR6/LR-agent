# Security

LR-Agent can execute local tools, so treat it like a developer tool with real machine access.

## Default protections

- File tools are restricted to `LR_AGENT_WORKSPACE`.
- Command execution uses an executable allowlist and does not invoke a shell.
- A small set of destructive Git/package commands is blocked unless
  `LR_AGENT_ALLOW_DESTRUCTIVE=true`.
- The command subprocess receives a reduced environment so the model does not
  automatically inherit `LR_AGENT_API_KEY`.
- The HTTP tool blocks private, loopback, link-local and reserved addresses by
  default to reduce SSRF risk.

## Important limitation

The command tool is **not an operating-system sandbox**. Any allowlisted program
can potentially access resources available to the current OS user. Python,
pytest, package managers, build scripts and checked-out repositories can all
execute code.

For untrusted repositories or prompts, run LR-Agent inside Docker/a disposable VM
and do not mount sensitive host directories.

Never commit your real `.env` or API key.

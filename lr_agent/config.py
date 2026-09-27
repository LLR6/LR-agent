from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LR_AGENT_",
        extra="ignore",
    )

    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-5.6"

    max_steps: int = 12
    max_concurrent_tasks: int = 2
    enable_planning: bool = True
    enable_review: bool = True
    max_review_retries: int = 1
    request_timeout_s: float = 120.0
    model_retries: int = 2
    command_timeout_s: float = 60.0

    workspace: Path = Path("./workspace")
    database: Path = Path("./data/lr_agent.db")
    knowledge_database: Path = Path("./data/knowledge.db")
    knowledge_max_files: int = 3000
    knowledge_max_file_bytes: int = 1_000_000
    auto_context: bool = True
    auto_context_results: int = 6

    allowed_commands: str = (
        "python,python3,pytest,git,gh,pip,uv,pwd,ls,dir,find,where,"
        "node,npm,npx,pnpm,yarn,java,javac,mvn,gradle,gradlew,gradlew.bat,"
        "cargo,go,cmake,ctest"
    )
    allow_destructive: bool = False
    allow_private_network: bool = False

    approval_mode: str = "off"
    approval_timeout_s: float = 600.0

    web_token: str = ""
    allow_remote_without_token: bool = False

    github_token: str = ""
    github_api_base: str = "https://api.github.com"
    allow_github_write: bool = False

    def ensure_dirs(self) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge_database.parent.mkdir(parents=True, exist_ok=True)

    @property
    def normalized_approval_mode(self) -> str:
        mode = self.approval_mode.strip().lower()
        if mode not in {"off", "writes", "all"}:
            return "off"
        return mode

    @property
    def allowed_command_set(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.allowed_commands.split(",")
            if item.strip()
        }

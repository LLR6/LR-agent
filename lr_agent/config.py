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
    enable_run_snapshots: bool = True
    snapshot_max_file_bytes: int = 2_000_000
    request_timeout_s: float = 120.0
    model_retries: int = 2
    command_timeout_s: float = 60.0

    workspace: Path = Path("./workspace")
    database: Path = Path("./data/lr_agent.db")
    knowledge_database: Path = Path("./data/knowledge.db")
    knowledge_max_files: int = 3000
    knowledge_max_file_bytes: int = 1_000_000
    knowledge_embeddings: bool = False
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = 32
    hybrid_vector_weight: float = 0.45
    auto_context: bool = True
    auto_context_results: int = 6

    allowed_commands: str = (
        "python,python3,pytest,git,gh,pip,uv,pwd,ls,dir,find,where,"
        "node,npm,npx,pnpm,yarn,java,javac,mvn,gradle,gradlew,gradlew.bat,"
        "cargo,go,cmake,ctest"
    )
    allow_destructive: bool = False
    allow_private_network: bool = False
    shadow_mode: bool = False

    universe_root: Path = Path("./data/universes")
    universe_candidates: int = 3
    universe_max_files: int = 5000
    universe_max_file_bytes: int = 5_000_000
    universe_excludes: str = (
        ".git,.venv,venv,node_modules,__pycache__,.pytest_cache,"
        ".mypy_cache,.ruff_cache,dist,build,data"
    )

    genome_enabled: bool = True
    genome_database: Path = Path("./data/genome.db")
    genome_context_results: int = 3
    gene_positive_lift_threshold: float = 8.0
    gene_negative_lift_threshold: float = -8.0
    gene_activation_min_experiments: int = 3
    gene_activation_min_positive_rate: float = 0.67
    gene_activation_min_average_lift: float = 8.0
    invariants_enabled: bool = True

    epistemic_tripwire: bool = True
    tripwire_repeat_failures: int = 2
    tripwire_repeat_mutations: int = 3

    chronoforge_enabled: bool = True
    chronoforge_root: Path = Path("./data/chronoforge")
    chronoforge_database: Path = Path("./data/chronoforge.db")
    chronoforge_generations: int = 4
    chronoforge_trajectories: int = 3
    chronoforge_max_generations: int = 10
    chronoforge_max_trajectories: int = 6
    chronoforge_scenario_count: int = 8
    chronoforge_cost_step_weight: float = 1.0
    chronoforge_cost_change_weight: float = 1.5
    chronoforge_cost_failure_weight: float = 4.0

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
        self.universe_root.mkdir(parents=True, exist_ok=True)
        self.genome_database.parent.mkdir(parents=True, exist_ok=True)
        self.chronoforge_root.mkdir(parents=True, exist_ok=True)
        self.chronoforge_database.parent.mkdir(parents=True, exist_ok=True)

    @property
    def universe_exclude_set(self) -> set[str]:
        return {
            item.strip()
            for item in self.universe_excludes.split(",")
            if item.strip()
        }

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

from __future__ import annotations


def build_client_config(config: dict[str, object]) -> dict[str, object]:
    """Build the minimal client configuration used by the demo application."""
    endpoint = str(config["api_url"]).rstrip("/")
    timeout = int(config.get("timeout_s", 30))
    return {
        "base_url": endpoint,
        "timeout_s": timeout,
    }

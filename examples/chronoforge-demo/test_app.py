from app import build_client_config


def test_build_client_config() -> None:
    result = build_client_config(
        {
            "api_url": "https://example.test/",
            "timeout_s": 15,
        }
    )

    assert result == {
        "base_url": "https://example.test",
        "timeout_s": 15,
    }


def test_default_timeout() -> None:
    result = build_client_config({"api_url": "https://example.test"})

    assert result["timeout_s"] == 30

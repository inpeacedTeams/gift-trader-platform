import pytest

from app.core.config import Settings
from app.core.security import InsecureConfiguration, suggest_secret, verify_secrets


def settings(**overrides) -> Settings:
    payload = {"jwt_secret": suggest_secret(), "app_env": "production"}
    payload.update(overrides)
    return Settings(**payload)


def test_production_refuses_the_placeholder_secret():
    with pytest.raises(InsecureConfiguration) as error:
        verify_secrets(settings(jwt_secret="change-me-in-production"))

    assert "JWT_SECRET" in str(error.value)


def test_production_refuses_a_short_secret():
    with pytest.raises(InsecureConfiguration):
        verify_secrets(settings(jwt_secret="tooshort"))


def test_a_generated_secret_passes():
    verify_secrets(settings())


def test_development_only_warns(caplog):
    verify_secrets(settings(app_env="development", jwt_secret="change-me-in-production"))

    assert "insecure configuration" in caplog.text


def test_suggested_secret_is_long_enough():
    assert len(suggest_secret()) >= 32

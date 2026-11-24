from pathlib import Path
import pytest
from pydantic import ValidationError

from app.core.config import ENV_FILE, PROJECT_ROOT, Settings


def test_dotenv_path_is_anchored_to_repository_not_process_working_directory():
    assert ENV_FILE == PROJECT_ROOT / '.env'
    assert ENV_FILE.is_absolute()
    assert PROJECT_ROOT == Path(__file__).resolve().parents[2]


def test_provider_config_normalizes_supported_provider_and_rejects_unknown_values():
    assert Settings.model_validate({"AI_PROVIDER": " NVIDIA "}).AI_PROVIDER == "nvidia"
    assert Settings.model_validate({"AI_PROVIDER": "GEMINI"}).AI_PROVIDER == "gemini"
    with pytest.raises(ValidationError, match="AI_PROVIDER"):
        Settings.model_validate({"AI_PROVIDER": "other"})


@pytest.mark.parametrize("url", [
    "file:///tmp/model",
    "https://user:password@example.com/v1",
    "https://example.com/v1?token=secret",
    "https://example.com/v1#fragment",
])
def test_provider_endpoint_rejects_invalid_or_credential_bearing_urls(url):
    with pytest.raises(ValidationError, match="NVIDIA_BASE_URL"):
        Settings.model_validate({"NVIDIA_BASE_URL": url})


def test_provider_endpoint_allows_hosted_and_private_http_compatible_servers():
    assert Settings.model_validate({
        "NVIDIA_BASE_URL": "https://integrate.api.nvidia.com/v1/",
    }).NVIDIA_BASE_URL == "https://integrate.api.nvidia.com/v1"
    assert Settings.model_validate({
        "NVIDIA_BASE_URL": "http://nvidia-nim:8000/v1",
    }).NVIDIA_BASE_URL == "http://nvidia-nim:8000/v1"


def test_production_settings_reject_unsafe_defaults():
    with pytest.raises(RuntimeError, match="Unsafe production configuration"):
        Settings.model_validate({"ENVIRONMENT": "production"}).validate_production_safety()


@pytest.mark.parametrize("override", [
    {"DEBUG": True},
    {"SECRET_KEY": "replace-this-with-a-secure-random-secret-key-in-production-min-32-chars"},
    {"SECRET_KEY": "replace-with-a-generated-production-signing-key-placeholder"},
    {"SECRET_KEY": "too-short"},
    {"INITIAL_ADMIN_PASSWORD": "AdminPassword123!"},
    {"INITIAL_ADMIN_PASSWORD": "replace-with-strong-local-admin-password"},
    {"CORS_ORIGINS": ["*"]},
    {"CORS_ORIGINS": ["http://localhost:5173"]},
    {"CORS_ORIGINS": ["https://app.example.com/dashboard"]},
])
def test_production_settings_require_hardened_values(override):
    values = {
        "ENVIRONMENT": "production",
        "DEBUG": False,
        "SECRET_KEY": "random-production-secret-with-more-than-32-chars-9df31",
        "INITIAL_ADMIN_PASSWORD": "owner-provided-unique-admin-bootstrap-secret",
        "CORS_ORIGINS": ["https://app.example.com"],
    }
    values.update(override)
    with pytest.raises(RuntimeError, match="Unsafe production configuration"):
        Settings.model_validate(values).validate_production_safety()


def test_production_settings_accept_explicit_secure_values():
    settings = Settings.model_validate({
        "ENVIRONMENT": "production",
        "DEBUG": False,
        "SECRET_KEY": "random-production-secret-with-more-than-32-chars-9df31",
        "INITIAL_ADMIN_PASSWORD": "owner-provided-unique-admin-bootstrap-secret",
        "CORS_ORIGINS": ["https://app.example.com"],
    })
    assert settings.ENVIRONMENT == "production"


def test_production_validation_error_does_not_expose_secret_value():
    secret = "short-synthetic-key"
    settings = Settings.model_validate({
        "ENVIRONMENT": "production",
        "DEBUG": False,
        "SECRET_KEY": secret,
        "INITIAL_ADMIN_PASSWORD": "owner-provided-unique-admin-bootstrap-secret",
        "CORS_ORIGINS": ["https://app.example.com"],
    })
    with pytest.raises(RuntimeError) as error:
        settings.validate_production_safety()
    assert secret not in str(error.value)


@pytest.mark.parametrize("url, normalized", [
    (" HTTPS://INTEGRATE.API.NVIDIA.COM:443/v1/ ", "https://integrate.api.nvidia.com/v1"),
    (" http://LOCALHOST:80/v1/// ", "http://localhost/v1"),
    (" http://[::1]:8000/v1/ ", "http://[::1]:8000/v1"),
    ("https://EXAMPLE.COM:8443/custom/", "https://example.com:8443/custom"),
])
def test_nvidia_endpoint_normalizes_whitespace_host_and_default_port(url, normalized):
    assert Settings.model_validate({"NVIDIA_BASE_URL": url}).NVIDIA_BASE_URL == normalized


@pytest.mark.parametrize("url", [
    "https://example.com:invalid/v1",
    "https://example.com:65536/v1",
    "https://@example.com/v1",
    "https://exa mple.com/v1",
    "https://example.com\\evil/v1",
])
def test_nvidia_endpoint_rejects_malformed_authority(url):
    with pytest.raises(ValidationError, match="NVIDIA_BASE_URL"):
        Settings.model_validate({"NVIDIA_BASE_URL": url})


def test_nvidia_structured_output_defaults_to_json_object():
    assert Settings(_env_file=None).NVIDIA_STRUCTURED_OUTPUT_MODE == "json_object"


@pytest.mark.parametrize("mode, normalized", [
    ("json_object", "json_object"), (" PROMPT ", "prompt"),
])
def test_nvidia_structured_output_accepts_only_explicit_modes(mode, normalized):
    assert Settings.model_validate({
        "NVIDIA_STRUCTURED_OUTPUT_MODE": mode,
    }).NVIDIA_STRUCTURED_OUTPUT_MODE == normalized


@pytest.mark.parametrize("mode", ["auto", "json_schema", "", "fallback"])
def test_nvidia_structured_output_rejects_unsupported_modes(mode):
    with pytest.raises(ValidationError, match="NVIDIA_STRUCTURED_OUTPUT_MODE"):
        Settings.model_validate({"NVIDIA_STRUCTURED_OUTPUT_MODE": mode})


def production_nvidia_settings(url, key):
    return Settings.model_validate({
        "ENVIRONMENT": "production",
        "DEBUG": False,
        "SECRET_KEY": "random-production-secret-with-more-than-32-chars-9df31",
        "INITIAL_ADMIN_PASSWORD": "owner-provided-unique-admin-bootstrap-secret",
        "CORS_ORIGINS": ["https://app.example.com"],
        "AI_PROVIDER": "nvidia",
        "NVIDIA_BASE_URL": url,
        "NVIDIA_API_KEY": key,
    })


@pytest.mark.parametrize("url", [
    "http://integrate.api.nvidia.com/v1",
    "http://example.com/v1",
    "http://8.8.8.8/v1",
    "http://nvidia-nim:8000/v1",
    "http://localhost.evil.example/v1",
    "http://0.0.0.0/v1",
])
@pytest.mark.parametrize("key", ["", "synthetic-bearer-secret"])
def test_production_rejects_public_or_unverified_plaintext_inference(url, key):
    settings = production_nvidia_settings(url, key)
    with pytest.raises(RuntimeError, match="NVIDIA_BASE_URL") as error:
        settings.validate_production_safety()
    assert "synthetic-bearer-secret" not in str(error.value)
    assert url not in str(error.value)


@pytest.mark.parametrize("url", [
    "http://localhost:8000/v1", "http://LOCALHOST.:8000/v1",
    "http://127.0.0.1:8000/v1", "http://[::1]:8000/v1",
    "http://10.1.2.3:8000/v1", "http://172.16.1.2:8000/v1",
    "http://192.168.1.20:8000/v1", "http://[fd00::1]:8000/v1",
])
def test_production_allows_deliberate_keyless_private_plaintext_inference(url):
    settings = production_nvidia_settings(url, "   ")
    assert settings.validate_production_safety() is settings
    with pytest.raises(RuntimeError, match="NVIDIA_API_KEY"):
        production_nvidia_settings(url, "synthetic-bearer-secret").validate_production_safety()


def test_production_allows_https_inference_with_bearer_credentials():
    settings = production_nvidia_settings(
        "https://integrate.api.nvidia.com/v1", "synthetic-bearer-secret"
    )
    assert settings.validate_production_safety() is settings

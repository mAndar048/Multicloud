"""Base adapter definition."""

from abc import ABC, abstractmethod


class AdapterCredentialsError(Exception):
    """Raised when required provider credentials are missing."""


class CloudAdapter(ABC):
    """Adapter interface for Terraform provider authentication."""

    def _require_keys(self, credentials: dict, required: list[str]) -> None:
        missing = [key for key in required if not credentials.get(key)]
        if missing:
            raise AdapterCredentialsError(
                f"Missing required credentials: {', '.join(missing)}"
            )

    @abstractmethod
    def get_env_vars(self, credentials: dict) -> dict[str, str]:
        """Return environment variables required for provider auth."""

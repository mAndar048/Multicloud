"""GCP adapter."""

from cloudpilot.adapters.base import CloudAdapter


class GCPAdapter(CloudAdapter):
    def get_env_vars(self, credentials: dict) -> dict[str, str]:
        self._require_keys(credentials, ["project_id", "credentials_path"])
        return {
            "GOOGLE_CLOUD_PROJECT": credentials.get("project_id", ""),
            "GOOGLE_APPLICATION_CREDENTIALS": credentials.get("credentials_path", ""),
        }

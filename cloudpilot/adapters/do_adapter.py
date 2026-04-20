"""DigitalOcean adapter."""

from cloudpilot.adapters.base import CloudAdapter


class DOAdapter(CloudAdapter):
    def get_env_vars(self, credentials: dict) -> dict[str, str]:
        self._require_keys(credentials, ["token"])
        return {
            "DIGITALOCEAN_TOKEN": credentials.get("token", ""),
        }

"""AWS adapter."""

from cloudpilot.adapters.base import CloudAdapter


class AWSAdapter(CloudAdapter):
    def get_env_vars(self, credentials: dict) -> dict[str, str]:
        self._require_keys(credentials, ["access_key", "secret_key", "region"])
        return {
            "AWS_ACCESS_KEY_ID": credentials.get("access_key", ""),
            "AWS_SECRET_ACCESS_KEY": credentials.get("secret_key", ""),
            "AWS_DEFAULT_REGION": credentials.get("region", ""),
        }

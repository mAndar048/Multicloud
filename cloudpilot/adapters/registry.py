"""Provider adapter registry."""

from cloudpilot.adapters.aws_adapter import AWSAdapter
from cloudpilot.adapters.do_adapter import DOAdapter
from cloudpilot.adapters.gcp_adapter import GCPAdapter

ADAPTER_REGISTRY = {
    "aws": AWSAdapter,
    "gcp": GCPAdapter,
    "digitalocean": DOAdapter,
}

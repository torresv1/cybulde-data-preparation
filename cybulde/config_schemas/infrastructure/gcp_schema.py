from dataclasses import dataclass
from hydra.core.config_store import ConfigStore


@dataclass
class GCPConfig:
    project_id: str = "emkademy-vladimir"


def setup_config() -> None:
    cs = ConfigStore.instance()
    cs.store(name="gcp_config_schema", node=GCPConfig)

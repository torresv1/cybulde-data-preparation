from hydra.core.config_store import ConfigStore

from omegaconf import MISSING
from pydantic.dataclasses import dataclass


@dataclass
class DatasetReaderConfig:
    target_: str = MISSING
    dataset_dir: str = MISSING
    dataset_name: str = MISSING


@dataclass
class GHCDatasetReaderConfig(DatasetReaderConfig):
    target_: str = "cybulde.data_processing.dataset_readers.GHCDatasetReader"
    dev_split_ratio: float = MISSING


@dataclass
class DatasetReaderManagerConfig:
    target_: str = "cybulde.data_processing.dataset_readers.DatasetReaderManager"
    dataset_readers: dict[str, DatasetReaderConfig] = MISSING


def setup_config() -> None:
    cs = ConfigStore.instance()
    cs.store(name="dataset_reader_manager_config_schema", node=DatasetReaderManagerConfig, group="dataset_reader_manager")

    cs.store(name="ghc_dataset_reader_config_schema", node=GHCDatasetReaderConfig, group="dataset_reader_manager/dataset_reader")

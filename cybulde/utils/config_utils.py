from dataclasses import asdict
from functools import partial
import importlib
import logging
import logging.config
import argparse
import os
import pickle

from io import BytesIO, StringIO
from typing import Any, Optional

import hydra
import yaml

from hydra import compose, initialize
from hydra.types import TaskFunction
from omegaconf import DictConfig, OmegaConf

from cybulde.config_schemas import data_processing_config_schema
from cybulde.utils.io_utils import open_file


def get_config(config_path: str, config_name: str) -> TaskFunction:
    setup_config()
    setup_logger()

    def main_decorator(task_function: TaskFunction) -> Any:
        @hydra.main(config_path=config_path, config_name=config_name, version_base=None)
        def decorated_main(dict_config: Optional[DictConfig] = None) -> Any:
            config = OmegaConf.to_object(dict_config)
            return task_function(config)

        return decorated_main

    return main_decorator


def get_pickle_config(config_path: str, config_name: str) -> Any:
    setup_config()
    setup_logger()

    def main_decorator(task_function: TaskFunction) -> Any:
        def decorated_main() -> Any:
            config = load_pickle_config(config_path, config_name)
            task_function(config)

        return decorated_main
    return main_decorator

       
def load_pickle_config(config_path: str, config_name: str) -> Any:
    with open_file(os.path.join(config_path, f"{config_name}.pickle"), "rb") as f:
        config = pickle.load(f)
    return config


def setup_config() -> None:
    data_processing_config_schema.setup_config()


def setup_logger() -> None:
    with open("./cybulde/configs/hydra/job_logging/custom.yaml", "r") as stream:
        config = yaml.load(stream, Loader=yaml.FullLoader)
    logging.config.dictConfig(config)


def config_args_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("--config_path", type=str, default="../configs", help="Directory of the config files")
    parser.add_argument("--config_name", type=str, required=True, help="Name of the config file")
    parser.add_argument("--overrides", nargs="*", default=[], help="List of config overrides")

    return parser.parse_args()


def compose_config(config_path: str, config_name: str, overrides: Optional[list[str]] = None) -> Any:
    setup_config()
    setup_logger()

    if overrides is None:
        overrides = []

    with initialize(version_base=None, config_path=config_path, job_name="config-compose"):
        dict_config = compose(config_name=config_name, overrides=overrides)
        config = OmegaConf.to_object(dict_config)
    return config


def save_config_as_yaml(config: Any, save_path: str) -> None:
    text_io = StringIO()
    OmegaConf.save(config, text_io, resolve=True)
    with open_file(save_path, "w") as f:
        f.write(text_io.getvalue())
        

def save_config_as_pickle(config: Any, save_path: str) -> None:
    bytes_io = BytesIO()
    pickle.dump(config, bytes_io)
    with open_file(save_path, "wb") as f:
        f.write(bytes_io.getvalue())


def custom_instantiate(config: Any) -> Any:
    config_as_dict = asdict(config)
    if "_target_" not in config_as_dict:
        raise ValueError("Config does not have _target_ key.")
    
    _target_ = config_as_dict["_target_"]
    _partial_ = config_as_dict.get("_partial_", False)

    config_as_dict.pop("_target_", None)
    config_as_dict.pop("_partial_", None)

    split_target = _target_.split(".")
    """
    cybulde.data_processing.dataset_readers.GHCDatasetReader
    split_target = ["cybulde", "data_processing", "dataset_readers", "GHCDatasetReader"]
    module_name = "cybulde.data_processing.dataset_readers"
    class_name = "GHCDatasetReader"
       
    """

    module_name, class_name = ".".join(split_target[:-1]), split_target[-1]

    module = importlib.import_module(module_name)
    _class = getattr(module, class_name)
    
    # Workaround for GCPCluster bug in dask-cloudprovider
    # GCPCluster doesn't properly store GCP params before calling parent classes
    if _target_ == "dask_cloudprovider.gcp.GCPCluster":
        from dask_cloudprovider.gcp.instances import GCPCluster
        from dask_cloudprovider.generic.vmcluster import VMCluster
        import logging
        logger = logging.getLogger(__name__)
        
        # Set GOOGLE_APPLICATION_CREDENTIALS environment variable if provided
        original_gac = None
        if config_as_dict.get('service_account_credentials'):
            credentials_path = config_as_dict['service_account_credentials']
            logger.info(f"Setting GOOGLE_APPLICATION_CREDENTIALS to {credentials_path}")
            original_gac = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
            
            # Remove from config as it's not a valid GCPCluster parameter
            config_as_dict.pop('service_account_credentials', None)
        
        # Parameters that GCP needs but parent classes don't accept
        gcp_only_params = {
            'projectid', 'zone', 'network', 'network_projectid', 'machine_type',
            'source_image', 'docker_image', 'docker_args', 'extra_bootstrap',
            'ngpus', 'gpu_type', 'scheduler_ngpus', 'scheduler_gpu_type',
            'worker_ngpus', 'worker_gpu_type', 'filesystem_size', 'disk_type',
            'on_host_maintenance', 'preemptible', 'instance_labels',
            'service_account', 'service_account_credentials'
        }
        
        # Store original __init__ methods
        original_gcp_init = GCPCluster.__init__
        original_vmc_init = VMCluster.__init__
        
        def patched_gcp_init(self, **kwargs):
            # First, store all GCP-specific params as instance attributes
            for param in gcp_only_params:
                if param in kwargs:
                    setattr(self, param, kwargs[param])
            # Then call original init
            original_gcp_init(self, **kwargs)
        
        def patched_vmc_init(self, **kwargs):
            # Filter out GCP-specific params before calling original
            filtered_kwargs = {k: v for k, v in kwargs.items() if k not in gcp_only_params}
            original_vmc_init(self, **filtered_kwargs)
        
        # Apply patches
        GCPCluster.__init__ = patched_gcp_init
        VMCluster.__init__ = patched_vmc_init
        
        try:
            logger.info(f"Creating GCPCluster with projectid='{config_as_dict.get('projectid')}'")
            cluster = GCPCluster(**config_as_dict)
            return cluster
        finally:
            # Restore original methods
            GCPCluster.__init__ = original_gcp_init
            VMCluster.__init__ = original_vmc_init
            # Restore original GOOGLE_APPLICATION_CREDENTIALS
            if original_gac is not None:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = original_gac
            elif 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    
    if _partial_:
        return partial(_class, **config_as_dict)
    return _class(**config_as_dict)

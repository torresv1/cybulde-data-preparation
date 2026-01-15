import warnings

from cybulde.utils.io_utils import open_file, write_yaml_file

from cybulde.config_schemas.data_processing.dataset_cleaners_schema import DatasetCleanerManagerConfig

# Suppress Python version deprecation warnings from Google libraries
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core._python_version_support")

from hydra.utils import instantiate
from pathlib import Path

from dask.distributed import Client
import dask.dataframe as dd
from cybulde.config_schemas.data_processing.dataset_cleaners_schema import DatasetCleanerManagerConfig

from cybulde.config_schemas.data_processing_config_schema import DataProcessingConfig
from cybulde.utils.config_utils import custom_instantiate, get_pickle_config
from cybulde.utils.data_utils import get_raw_data_with_version
from cybulde.utils.gcp_utils import access_secret_version
from cybulde.utils.utils import get_logger
import os


def process_raw_data(df_partition: dd.DataFrame, dataset_cleaner_manager: DatasetCleanerManagerConfig) -> dd.Series:
    processed_partition: dd.Series = df_partition["text"].apply(dataset_cleaner_manager)
    return processed_partition


@get_pickle_config(config_path="cybulde/configs/automatically_generated", config_name="data_processing_config")
def process_data(config: DataProcessingConfig) -> None:
    logger = get_logger(Path(__file__).name)
    logger.info("Processing raw data...")
    
    processed_data_save_dir = config.processed_data_save_dir

    cluster = custom_instantiate(config.dask_cluster)
    client = Client(cluster)

    try:
    
        dataset_reader_manager = instantiate(config.dataset_reader_manager)
        dataset_cleaner_manager = instantiate(config.dataset_cleaner_manager)

        df = dataset_reader_manager.read_data(config.dask_cluster.n_workers)

        print(60 * "#")
        print(f"{df.npartitions} partitions after reading data")
        print(60 * "#")

        # Repartition to utilize all workers and reduce memory pressure
        target_partitions = config.dask_cluster.n_workers * 8  # 8 partitions per worker for smaller chunks
        if df.npartitions < target_partitions:
            logger.info(f"Repartitioning from {df.npartitions} to {target_partitions} partitions...")
            df = df.repartition(npartitions=target_partitions)
            print(60 * "#")
            print(f"{df.npartitions} partitions after repartitioning")
            print(60 * "#")

        logger.info("Cleaning data...")
        df = df.assign(cleaned_text=df.map_partitions(process_raw_data, dataset_cleaner_manager=dataset_cleaner_manager, meta=("text", "object")))
        df = df.compute()

        train_parquet_path = os.path.join(processed_data_save_dir, "train.parquet")
        dev_parquet_path = os.path.join(processed_data_save_dir, "dev.parquet")
        test_parquet_path = os.path.join(processed_data_save_dir, "test.parquet")

        df[df["split"] == "train"].to_parquet(train_parquet_path)
        df[df["split"] == "dev"].to_parquet(dev_parquet_path)
        df[df["split"] == "test"].to_parquet(test_parquet_path)

        docker_info = {"docker_image": config.docker_image_name, "docker_tag": config.docker_image_tag}
        docker_info_save_path = os.path.join(processed_data_save_dir, "docker_info.yaml")
        
        write_yaml_file(docker_info_save_path, docker_info)
        
        logger.info("Data processing finished")

    finally:
        logger.info("Closing Dask client and cluster...")
        client.close()
        cluster.close()


if __name__ == "__main__":
    process_data()
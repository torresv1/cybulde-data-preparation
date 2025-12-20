from abc import ABC, abstractmethod
from typing import Optional
import dask.dataframe as dd
import os
from cybulde.utils.utils import get_logger
from dask_ml.model_selection import train_test_split


class DatasetReaders(ABC):
    required_columns = {"text", "label", "split", "dataset_name"}
    split_names = {"train", "dev", "test"}

    def __init__(self, dataset_dir: str, dataset_name: str) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.dataset_dir = dataset_dir
        self.dataset_name = dataset_name

    def read_data(self) -> dd.core.DataFrame:
        train_df, dev_df, test_df = self._read_data()
        df = self.assign_split_names_to_data_frames_and_merge(train_df, dev_df, test_df)
        df["dataset_name"] = self.dataset_name
        if any(required_column not in df.columns.values for required_column in self.required_columns):
            raise ValueError(f"Dataset must contain all required columns: {self.required_columns}")
        unique_split_names = set(df["split"].unique().compute().tolist())
        if unique_split_names != self.split_names:
            raise ValueError(f"Dataset must contain all split names: {self.split_names}.")
        return df[list(self.required_columns)]

    @abstractmethod
    def _read_data(self) -> tuple[dd.core.DataFrame, dd.core.DataFrame, dd.core.DataFrame]:
        """
        Read and split the dataset into train, dev, and test sets.
        The return value must be a dd.core.DataFrame, with the required columns: self.required_columns.
        """

    def assign_split_names_to_data_frames_and_merge(self,
                                                    train_df: dd.core.DataFrame,
                                                    dev_df: dd.core.DataFrame,
                                                    test_df: dd.core.DataFrame) -> dd.core.DataFrame:
        train_df["split"] = "train"
        dev_df["split"] = "dev"
        test_df["split"] = "test"
        return dd.concat([train_df, dev_df, test_df])

    def split_dataset(self, df: dd.core.DataFrame,
                      test_size: float,
                      stratify_column: Optional[str]) -> tuple[dd.core.DataFrame, dd.core.DataFrame]:
        if stratify_column is None:
            return train_test_split(df, test_size=test_size, random_state=1234, shuffle=True)
        unique_column_values = df[stratify_column].unique()
        first_dfs = []
        second_dfs = []
        for unique_set_value in unique_column_values:
            subs_df = df[df[stratify_column] == unique_set_value]
            sub_first_df, sub_second_df = train_test_split(
                subs_df, test_size=test_size, random_state=1234, shuffle=True
            )
            first_dfs.append(sub_first_df)
            second_dfs.append(sub_second_df)
        first_df = dd.concat(first_dfs)
        second_df = dd.concat(second_dfs)
        return first_df, second_df


class GHCDatasetReader(DatasetReaders):
    def __init__(self, dataset_dir: str, dataset_name: str, dev_split_ratio: float) -> None:
        super().__init__(dataset_dir, dataset_name)
        self.dev_split_ratio = dev_split_ratio

    def _read_data(self) -> tuple[dd.core.DataFrame, dd.core.DataFrame, dd.core.DataFrame]:
        self.logger.info("Reading GHC dataset...")
        train_tsv_path = os.path.join(self.dataset_dir, "ghc_train.tsv")
        train_df = dd.read_csv(train_tsv_path, sep="\t", header=0)

        test_tsv_path = os.path.join(self.dataset_dir, "ghc_test.tsv")
        test_df = dd.read_csv(test_tsv_path, sep="\t", header=0)

        train_df["label"] = (train_df["hd"] + train_df["cv"] + train_df["vo"] > 0).astype(int)
        test_df["label"] = (test_df["hd"] + test_df["cv"] + test_df["vo"] > 0).astype(int)

        train_df, dev_df = self.split_dataset(train_df, self.dev_split_ratio, stratify_column="label")

        return train_df, dev_df, test_df


class DatasetReaderManager:
    def __init__(self, dataset_reader: dict[str, DatasetReaders]) -> None:
        self.dataset_reader = dataset_reader

    def get_dataset(self) -> dd.core.DataFrame:
        dfs = [dataset_reader.read_data() for dataset_reader in self.dataset_reader.values()]
        df = dd.concat(dfs)
        return df

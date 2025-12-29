import os

from abc import ABC, abstractmethod
from typing import Optional

import dask.dataframe as dd

from cybulde.utils.utils import get_logger


class DatasetReaders(ABC):
    required_columns = {"text", "label", "split", "dataset_name"}
    split_names = {"train", "dev", "test"}

    def __init__(self, dataset_dir: str, dataset_name: str) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.dataset_dir = dataset_dir
        self.dataset_name = dataset_name

    def read_data(self) -> dd.core.DataFrame:
        self.logger.info(f"Reading  {self.__class__.__name__}")
        train_df, dev_df, test_df = self._read_data()
        df = self.assign_split_names_to_data_frames_and_merge(train_df, dev_df, test_df)
        df["dataset_name"] = self.dataset_name
        if any(required_column not in df.columns.values for required_column in self.required_columns):
            raise ValueError(f"Dataset must contain all required columns: {self.required_columns}")
        unique_split_names = set(df["split"].unique().compute().tolist())
        if unique_split_names != self.split_names:
            raise ValueError(f"Dataset must contain all split names: {self.split_names}.")
        final_df: dd.core.DataFrame = df[list(self.required_columns)]
        return final_df

    @abstractmethod
    def _read_data(self) -> tuple[dd.core.DataFrame, dd.core.DataFrame, dd.core.DataFrame]:
        """
        Read and split the dataset into train, dev, and test sets.
        The return value must be a dd.core.DataFrame, with the required columns: self.required_columns.
        """

    def assign_split_names_to_data_frames_and_merge(
        self, train_df: dd.core.DataFrame, dev_df: dd.core.DataFrame, test_df: dd.core.DataFrame
    ) -> dd.core.DataFrame:
        train_df["split"] = "train"
        dev_df["split"] = "dev"
        test_df["split"] = "test"
        final_df: dd.core.DataFrame = dd.concat([train_df, dev_df, test_df])
        return final_df

    def split_dataset(
        self, df: dd.core.DataFrame, test_size: float, stratify_column: Optional[str]
    ) -> tuple[dd.core.DataFrame, dd.core.DataFrame]:
        if stratify_column is None:
            # Simple random split without stratification
            df = df.sample(frac=1, random_state=1234).reset_index(drop=True)  # type: ignore[no-untyped-call]  # Shuffle
            n = len(df)
            split_idx = int(n * (1 - test_size))
            train_df = df.loc[: split_idx - 1]
            test_df = df.loc[split_idx:]
            return train_df, test_df

        # Stratified split
        unique_column_values = df[stratify_column].unique()
        first_dfs = []
        second_dfs = []
        for unique_set_value in unique_column_values:
            subs_df = df[df[stratify_column] == unique_set_value]
            subs_df = subs_df.sample(frac=1, random_state=1234).reset_index(drop=True)  # Shuffle
            n = len(subs_df)
            split_idx = int(n * (1 - test_size))
            sub_first_df = subs_df.loc[: split_idx - 1]
            sub_second_df = subs_df.loc[split_idx:]
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
        train_tsv_path = os.path.join(self.dataset_dir, "ghc_train.tsv")
        train_df = dd.read_csv(train_tsv_path, sep="\t", header=0)

        test_tsv_path = os.path.join(self.dataset_dir, "ghc_test.tsv")
        test_df = dd.read_csv(test_tsv_path, sep="\t", header=0)

        train_df["label"] = (train_df["hd"] + train_df["cv"] + train_df["vo"] > 0).astype(int)
        test_df["label"] = (test_df["hd"] + test_df["cv"] + test_df["vo"] > 0).astype(int)

        train_df, dev_df = self.split_dataset(train_df, self.dev_split_ratio, stratify_column="label")

        return train_df, dev_df, test_df


class JigsawToxicCommentsReader(DatasetReaders):
    def __init__(self, dataset_dir: str, dataset_name: str, dev_split_ratio: float) -> None:
        super().__init__(dataset_dir, dataset_name)
        self.dev_split_ratio = dev_split_ratio
        self.columns_for_labels = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]

    def _read_data(self) -> tuple[dd.core.DataFrame, dd.core.DataFrame, dd.core.DataFrame]:
        test_csv_path = os.path.join(self.dataset_dir, "test.csv")
        test_df = dd.read_csv(test_csv_path)

        test_labels_csv_path = os.path.join(self.dataset_dir, "test_labels.csv")
        test_labels_df = dd.read_csv(test_labels_csv_path)

        test_df = test_df.merge(test_labels_df, on="id")
        test_df = test_df[test_df["toxic"] != -1]

        test_df = self.get_text_and_label_columns(test_df)

        train_csv_path = os.path.join(self.dataset_dir, "train.csv")
        train_df = dd.read_csv(train_csv_path)
        train_df = self.get_text_and_label_columns(train_df)

        train_df, dev_df = self.split_dataset(train_df, self.dev_split_ratio, stratify_column="label")
        return train_df, dev_df, test_df

    def get_text_and_label_columns(self, df: dd.core.DataFrame) -> dd.core.DataFrame:
        df["label"] = (df[self.columns_for_labels].sum(axis=1) > 0).astype(int)
        df = df.rename(columns={"comment_text": "text"})
        return df


class TwitterDatasetReader(DatasetReaders):
    def __init__(self, dataset_dir: str, dataset_name: str, dev_split_ratio: float, test_split_ratio: float) -> None:
        super().__init__(dataset_dir, dataset_name)
        self.dev_split_ratio = dev_split_ratio
        self.test_split_ratio = test_split_ratio

    def _read_data(self) -> tuple[dd.core.DataFrame, dd.core.DataFrame, dd.core.DataFrame]:
        train_csv_path = os.path.join(self.dataset_dir, "cyberbullying_tweets.csv")
        df = dd.read_csv(train_csv_path)
        df = df.rename(columns={"tweet_text": "text", "cyberbullying_type": "label"})
        df["label"] = (df["label"] != "not_cyberbullying").astype(int)

        train_df, test_df = self.split_dataset(df, self.dev_split_ratio, stratify_column="label")
        train_df, dev_df = self.split_dataset(train_df, self.dev_split_ratio, stratify_column="label")

        return train_df, dev_df, test_df


class DatasetReaderManager:
    def __init__(self, dataset_readers: dict[str, DatasetReaders]) -> None:
        # Dataset readers are already instantiated by Hydra
        self.dataset_readers = dataset_readers

    def read_data(self) -> dd.core.DataFrame:
        dfs = [dataset_reader.read_data() for dataset_reader in self.dataset_readers.values()]
        df: dd.core.DataFrame = dd.concat(dfs)
        return df 

from abc import ABC, abstractmethod
import dask.dataframe as dd


class DatasetReaders(ABC):
    required_columns = {"text", "label", "split", "dataset_name"}
    split_names = {"train", "dev", "test"}

    def __init__(self, dataset_dir: str, dataset_name: str) -> None:
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

import string

from dataclasses import dataclass, field

from omegaconf import MISSING


@dataclass
class SpellCorrectionModelConfig:
    _target_: str = "cybulde.utils.spell_correction.SpellCorrectorModel"
    max_dictionary_edit_distance: int = 2
    prefix_length: int = 7
    count_threshold: int = 1


@dataclass
class DatasetCleanerConfig:
    _target_: str = MISSING


@dataclass
class StopWordsDatasetCleanerConfig(DatasetCleanerConfig):
    _target_: str = "cybulde.data_processing.dataset_cleaners.StopWordsDatasetCleaner"


@dataclass
class ToLowerDatasetCleanerConfig(DatasetCleanerConfig):
    _target_: str = "cybulde.data_processing.dataset_cleaners.ToLowerDatasetCleaner"


@dataclass
class URLDatasetCleanerConfig(DatasetCleanerConfig):
    _target_: str = "cybulde.data_processing.dataset_cleaners.URLDatasetCleaner"


@dataclass
class PunctuationDatasetCleanerConfig(DatasetCleanerConfig):
    _target_: str = "cybulde.data_processing.dataset_cleaners.PunctuationDatasetCleaner"
    punctuation: str = string.punctuation


@dataclass
class NonLetterDatasetCleanerConfig(DatasetCleanerConfig):
    _target_: str = "cybulde.data_processing.dataset_cleaners.NonLettersDatasetCleaner"


@dataclass
class NewlineDatasetCleanerConfig(DatasetCleanerConfig):
    _target_: str = "cybulde.data_processing.dataset_cleaners.NewLineDatasetCleaner"


@dataclass
class NonAsciiDatasetCleanerConfig(DatasetCleanerConfig):
    _target_: str = "cybulde.data_processing.dataset_cleaners.NonASCIIDataSetCleaner"


@dataclass
class ReferenceToAccountDatasetCleanerConfig(DatasetCleanerConfig):
    _target_: str = "cybulde.data_processing.dataset_cleaners.ReferenceToAccountDatasetCleaner"


@dataclass
class RetweetDatasetCleanerConfig(DatasetCleanerConfig):
    _target_: str = "cybulde.data_processing.dataset_cleaners.RetweetDatasetCleaner"


@dataclass
class SpellCorrectionDatasetCleanerConfig(DatasetCleanerConfig):
    _target_: str = "cybulde.data_processing.dataset_cleaners.SpellCorrectionDatasetCleaner"
    spell_corrector_model: SpellCorrectionModelConfig = SpellCorrectionModelConfig()


@dataclass
class CharacterLimiterDatasetCleanerConfig(DatasetCleanerConfig):
    _target_: str = "cybulde.data_processing.dataset_cleaners.CharacterLimiterDatasetCleaner"
    character_limit: int = 300


@dataclass
class DatasetCleanerManagerConfig:
    _target_: str = "cybulde.data_processing.dataset_cleaners.DatasetCleanerManager"
    dataset_cleaners: dict[str, DatasetCleanerConfig] = field(default_factory=lambda: {})


def setup_config() -> None:
    from hydra.core.config_store import ConfigStore

    cs = ConfigStore.instance()

    cs.store(
        name="stop_words_dataset_cleaner_schema",
        node=StopWordsDatasetCleanerConfig,
        group="dataset_cleaner_manager/dataset_cleaner",
    )
    cs.store(
        name="to_lower_dataset_cleaner_schema",
        node=ToLowerDatasetCleanerConfig,
        group="dataset_cleaner_manager/dataset_cleaner",
    )
    cs.store(
        name="url_dataset_cleaner_schema", node=URLDatasetCleanerConfig, group="dataset_cleaner_manager/dataset_cleaner"
    )
    cs.store(
        name="punctuation_dataset_cleaner_schema",
        node=PunctuationDatasetCleanerConfig,
        group="dataset_cleaner_manager/dataset_cleaner",
    )
    cs.store(
        name="non_letter_dataset_cleaner_schema",
        node=NonLetterDatasetCleanerConfig,
        group="dataset_cleaner_manager/dataset_cleaner",
    )
    cs.store(
        name="newline_dataset_cleaner_schema",
        node=NewlineDatasetCleanerConfig,
        group="dataset_cleaner_manager/dataset_cleaner",
    )
    cs.store(
        name="non_ascii_dataset_cleaner_schema",
        node=NonAsciiDatasetCleanerConfig,
        group="dataset_cleaner_manager/dataset_cleaner",
    )
    cs.store(
        name="reference_to_account_dataset_cleaner_schema",
        node=ReferenceToAccountDatasetCleanerConfig,
        group="dataset_cleaner_manager/dataset_cleaner",
    )
    cs.store(
        name="retweet_dataset_cleaner_schema",
        node=RetweetDatasetCleanerConfig,
        group="dataset_cleaner_manager/dataset_cleaner",
    )
    cs.store(
        name="spell_correction_dataset_cleaner_schema",
        node=SpellCorrectionDatasetCleanerConfig,
        group="dataset_cleaner_manager/dataset_cleaner",
    )
    cs.store(
        name="character_limiter_dataset_cleaner_schema",
        node=CharacterLimiterDatasetCleanerConfig,
        group="dataset_cleaner_manager/dataset_cleaner",
    )
    cs.store(name="dataset_cleaner_manager_schema", node=DatasetCleanerManagerConfig, group="dataset_cleaner_manager")

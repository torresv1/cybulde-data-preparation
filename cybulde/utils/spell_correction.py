import importlib.resources

import symspellpy
from symspellpy import SymSpell


class SpellCorrectorModel:
    def __init__(
        self,
        max_dictionary_edit_distance: int = 2,
        prefix_length: int = 7,
        count_threshold: int = 1,
    ) -> None:
        self.max_dictionary_edit_distance = max_dictionary_edit_distance
        self.model = self._initialize_model(prefix_length, count_threshold)

    def _initialize_model(self, prefix_length: int, count_threshold: int) -> symspellpy.symspellpy.SymSpell:
        model = SymSpell(self.max_dictionary_edit_distance, prefix_length, count_threshold)

        # Use importlib.resources to access package data files
        with importlib.resources.path("symspellpy", "frequency_dictionary_en_82_765.txt") as dictionary_path:
            model.load_dictionary(str(dictionary_path), term_index=0, count_index=1)

        with importlib.resources.path("symspellpy", "frequency_bigramdictionary_en_243_342.txt") as bigram_path:
            model.load_bigram_dictionary(str(bigram_path), term_index=0, count_index=2)

        return model

    def __call__(self, text: str) -> str:
        suggestion: str = self.model.lookup_compound(text, max_edit_distance=self.max_dictionary_edit_distance)[0].term

        return suggestion

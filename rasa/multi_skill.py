import logging
from typing import Text, List, Union, Set, Dict
import os

import rasa.utils.io as io_utils
from rasa import data

logger = logging.getLogger(__name__)


class SkillSelector:
    def __init__(self, imports: Set[Text], base_directory: Text = None):
        self.imports = imports
        self.base_directory = base_directory

    @classmethod
    def empty(cls) -> "SkillSelector":
        return cls(set())

    @classmethod
    def load(
        cls, config: Text, skill_paths: Union[Text, List[Text]]
    ) -> "SkillSelector":
        # All imports are by default relative to the root config file directory
        config = os.path.abspath(config)
        base_directory = os.path.dirname(config)

        selector = cls._from_file(config, base_directory)

        if selector.is_empty():
            # if the root selector is empty we import everything beneath
            selector.add_import(base_directory)

        if not isinstance(skill_paths, list):
            skill_paths = [skill_paths]

        for path in skill_paths:
            other = cls._load(path, base_directory)
            selector = selector.merge(other)

        logger.debug("Selected skills: {}.".format(selector.imports))

        return selector

    @classmethod
    def _load(cls, path: Text, base_directory: Text) -> "SkillSelector":
        if os.path.isfile(path):
            return cls._from_file(path, base_directory)
        elif os.path.isdir(path):
            return cls._from_directory(path, base_directory)
        else:
            logger.debug("No imports found. Importing everything.")
            return cls.empty()

    @classmethod
    def _from_file(cls, path: Text, base_directory: Text) -> "SkillSelector":

        if data.is_config_file(path):
            config = io_utils.read_yaml_file(path)

            if isinstance(config, dict):
                return cls._from_dict(config, base_directory)

        return cls.empty()

    @classmethod
    def _from_dict(cls, _dict: Dict, base_directory: Text) -> "SkillSelector":
        imports = _dict.get("imports")

        if imports is None:
            imports = []

        imports = {os.path.join(base_directory, p) for p in imports}

        return cls(imports, base_directory)

    @classmethod
    def _from_directory(cls, path: Text, base_directory: Text) -> "SkillSelector":
        importer = cls.empty()
        for parent, _, files in os.walk(path):
            for file in files:
                full_path = os.path.join(parent, file)

                if data.is_config_file(full_path) and importer.is_imported(full_path):
                    other = cls._from_file(full_path, base_directory)
                    importer = importer.merge(other)

        return importer

    def merge(self, other: "SkillSelector") -> "SkillSelector":
        self.imports |= other.imports

        return self

    def is_empty(self) -> bool:
        return not self.imports

    def is_imported(self, path: Text) -> bool:
        absolute_path = os.path.abspath(path)

        return (
            self.is_empty()
            or os.path.abspath(path) == self.base_directory
            or (
                os.path.isfile(absolute_path)
                and os.path.abspath(os.path.dirname(path)) == self.base_directory
            )
            or any([i in absolute_path for i in self.imports])
        )

    def add_import(self, path: Text) -> bool:
        self.imports.add(path)

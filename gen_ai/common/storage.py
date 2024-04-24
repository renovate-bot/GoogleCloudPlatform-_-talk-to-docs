"""
This module defines a set of storage classes that provide mechanisms for processing directories
containing text files and extracting data into structured document formats. These classes are designed
to handle different storage strategies and custom extraction logic specific to the content and structure
of the directories and files they process.

The module contains abstract and concrete classes, each tailored for specific storage conditions:
- `Storage`: An abstract base class that defines a common interface for processing directories.
- `DefaultStorage`: A concrete class implementing the default storage strategy for text file processing.
- `CustomWoolworthStorage`: A concrete class designed for specific processing needs related to Woolworth's document 
storage.
- `UhgStorage`: A concrete class specialized for handling document processing with metadata enhancements, tailored 
for UHG's document structure.

Each class is capable of processing a directory of text files, extracting data, and organizing this data into
document objects based on predefined or custom rules.

Dependencies:
    os: For directory and file manipulation.
    abc: For abstract base class definition.
    collections: For using defaultdict for efficient data aggregation.
    langchain.schema: For defining the Document data structure.
    gen_ai.common.common: For common utility functions like reading JSON.
"""

import os
from abc import ABC, abstractmethod
from collections import defaultdict

from langchain.schema import Document

import gen_ai.common.common as common


class Storage(ABC):
    @abstractmethod
    def process_directory(self, content_dir: str, extract_data_fn: callable) -> dict:
        pass


class DefaultStorage(ABC):
    """
    Implements the default strategy for processing text files within a specified directory.
    This class scans a directory, identifies text files, and uses a provided extraction function
    to convert file content into document objects. Documents are then organized into a hashmap
    where each key corresponds to a specific plan name derived from the file name, supporting
    different plan sections and definitions.

    The extraction process is particularly tailored to handle files ending with '.txt' and
    supports additional logic to classify documents related to specific articles identified
    by a prefix in their section numbers.
    """

    def process_directory(self, content_dir: str, extract_data_fn: callable) -> dict[str, list[Document]]:
        """
        Go through files in content_dir and parse their content if the filename ends with ".txt".
        Generate a document object from each file and store it in a hashmap where the key is the
        plan name and the value is a list of document objects. Return the hashmap.
        """

        documents_hashmap = {}

        for filename in os.listdir(content_dir):
            if filename.endswith(".txt"):
                if "-section_" in filename:
                    plan_name = filename.split("-section_")[0]
                elif "-definition_" in filename:
                    plan_name = filename.split("-definition_")[0]
                else:
                    continue
                file_path = os.path.join(content_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                document = extract_data_fn(content)
                document.metadata["filename"] = filename
                if plan_name not in documents_hashmap:
                    documents_hashmap[plan_name] = []

                section_number = document.metadata.get("section_number", "")
                if len(section_number) >= 2 and section_number[:2] == "20":
                    article_20_plan_name = plan_name + "_article20"
                    if article_20_plan_name not in documents_hashmap:
                        documents_hashmap[article_20_plan_name] = []
                    documents_hashmap[article_20_plan_name].append(document)
                else:
                    documents_hashmap[plan_name].append(document)
        return documents_hashmap


class CustomWoolworthStorage(ABC):
    """
    Provides a customized document storage strategy for Woolworth-specific document processing.
    This class handles text files by extracting their content, augmenting each document with
    metadata from a corresponding JSON file named similarly to the text file but with a '_metadata.json' suffix.

    Designed to work within a fixed plan name 'se', this class assumes all documents belong to a single
    organizational unit, making it specialized for scenarios where document categorization by plan name
    is uniform and predefined.
    """

    def process_directory(self, content_dir: str, woolworth_extract_data: callable) -> dict[str, list[Document]]:
        """
        Go through files in content_dir and parse their content if the filename ends with ".txt".
        Generate a document object from each file and store it in a hashmap where the key is the
        plan name and the value is a list of document objects. Return the hashmap.
        """

        documents_hashmap = defaultdict(list)
        plan_name = "se"
        for filename in os.listdir(content_dir):
            if filename.endswith(".txt") and "_metadata.json" not in filename:
                file_path = os.path.join(content_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                document = woolworth_extract_data(content)
                filename_metadata = file_path.replace(".txt", "_metadata.json")
                metadata = common.read_json(filename_metadata)
                for k, v in metadata.items():
                    document.metadata[k] = v

                documents_hashmap[plan_name].append(document)
        return documents_hashmap


class UhgStorage(ABC):
    """
    This class is designed to process text files from a specified directory, extracting and structuring their
    content into document objects. The `process_directory` method specifically targets files ending with ".txt",
    excluding those associated with metadata in JSON format (indicated by '_metadata.json' in their filenames).
    Each document object is then enhanced with metadata extracted from a corresponding JSON file, named similarly to
    the text file but with a '_metadata.json' suffix. The resulting list of document objects, each enriched with
    relevant metadata, is then returned. This class is particularly useful for handling document processing in
    scenarios where each text file represents a unique piece of content, such as articles, reports, or other
    written materials, and where associated metadata plays a crucial role in their organization and utilization.

    Methods:
        process_directory(self, content_dir: str, extract_data_fn: callable) -> list[Document]:
            Processes text files within a specified directory, enriching each extracted document with metadata
            from a corresponding JSON file.

    Attributes:
        This class does not have class-specific attributes and relies on inherited attributes from ABC.
    """

    def process_directory(self, content_dir: str, extract_data_fn: callable) -> list[Document]:
        """
        Parses text files in the specified directory, excluding those with '_metadata.json' in their filenames.
        Each text file is processed to generate a document object, which is then augmented with metadata extracted
        from a corresponding JSON file. The JSON file is expected to have the same base filename as the text file,
        with a '_metadata.json' suffix. The method returns a list of document objects, each containing the content
        of a text file and its associated metadata.

        Args:
            content_dir (str): The path to the directory containing the text files to be processed.
            extract_data_fn (callable): A function that takes the content of a text file as input and returns a 
            document object.

        Returns:
            list[Document]: A list of document objects. Each document contains the content from a text file and
            is augmented with metadata from the corresponding JSON file.
        """
        documents = []
        for filename in os.listdir(content_dir):
            if filename.endswith(".txt") and "_metadata.json" not in filename:
                file_path = os.path.join(content_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                document = extract_data_fn(content)
                filename_metadata = file_path.replace(".txt", "_metadata.json")
                metadata = common.read_json(filename_metadata)
                for k, v in metadata.items():
                    document.metadata[k] = v

                documents.append(document)
        return documents

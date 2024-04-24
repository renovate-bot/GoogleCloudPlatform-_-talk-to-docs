"""Provides the XmlExtractor class for extracting textual data from XML (.xml) files and organizing the extracted data into separate files for structured document processing."""

import json
import os
import re
import xml.etree.ElementTree as ET

from gen_ai.extraction_pipeline.document_extractors.base_extractor import BaseExtractor


class XmlExtractor(BaseExtractor):
    """Extractor class of textual data from XML (.xml) files and chunks sections into separate files.

    This class inherits from the `BaseExtractor` and provides specialized
    functionality
    for extracting text content from .xml documents.

    Args:
        filepath (str): The path to the .docx file.
        config_file_parameters (dict[str, str]): Configuration settings for the
            extraction process.

    Attributes:
        filepath (str): Stores the path to the input file.
        config_file_parameters (dict[str, str]): Stores the configuration
            parameters.
        xml_extraction (str): Configuration parameter fot the extraction method.
            Defaults to 'default'.
        xml_chunking (str):  Configuration parameter fot the chunking method.
            Defaults to 'default'.
    """

    def __init__(self, filepath: str, config_file_parameters: dict[str, str]):
        super().__init__(filepath, config_file_parameters)

        self.xml_extraction = config_file_parameters.get(
            "xml_extraction", "default"
        )
        self.xml_chunking = config_file_parameters.get("xml_chunking", "default")

    def modify_file(self):
        """Modifies an existing file by adding a ProcessGroup block and other blocks if they are not already present within the file."""
        with open(self.filepath, "r", encoding="utf-8") as file:
            original_lines = file.readlines()

        basename = os.path.basename(self.filepath)
        if basename not in original_lines[0]:
            with open(self.filepath, "w", encoding="utf-8") as file:
                file.write(f'<ProcessGroup Name="{basename}">\n')
                file.write("<ProcessGroupItems>\n")

                for line in original_lines:
                    file.write(line)

                file.write("</ProcessGroupItems>\n")
                file.write("</ProcessGroup>\n")

    def explore_xml_tree(
        self,
        root,
        content: dict[str, tuple[str, str, str]],
        name: list[str],
        visited: set[str],
    ):
        """Recursively explores an XML tree, extracting process information and building content for a structured document.

        Args:
            root: The root element of the XML tree.
            content: A dictionary to store extracted content.
            name: A list used to track the hierarchy of process names during
                traversal.
            visited: A set to keep track of visited section IDs and avoid
                duplicates.
        """
        if root.tag == "ProcessGroup":
            name.append(root.attrib["Name"])
        for process_group_items in root.findall("ProcessGroupItems"):
            for item in process_group_items:
                if item.tag == "ProcessGroup":
                    self.explore_xml_tree(item, content, name, visited)
                    name.pop()
                elif item.tag == "Process":
                    section_id = item.attrib["Id"]
                    if section_id in visited:
                        continue
                    visited.add(section_id)
                    name.append(item.attrib["Name"])
                    key = " --- ".join([section_id] + name)
                    group = item.attrib["Group"]
                    page_content = key
                    page_content += f"\n\nName: {item.attrib['Name']}"
                    page_content += f"\nObjective: {item.attrib['Objective']}"
                    page_content += f"\nID: {section_id}"
                    page_content += f"\nGroup: {group}"
                    for line in item.iter():
                        if line.tag == "Text" or line.tag == "Attachment":
                            page_content += "\n" + str(line.text)
                    content[key] = (section_id, group, page_content)
                    name.pop()

    def create_metadata(
        self, key: str, value: tuple[str, str, str], filepath: str
    ):
        """Generates and saves a JSON metadata file associated with a processed section of content.

        Args:
            key (str): A string representing the filename, document name and section
                name.
            value (str): A tuple containing (section_id, group,
                formatted_page_content).
            filepath (str): The base filepath where the metadata file will be saved.
        """
        _, filename, *mid = key.split(" --- ")
        section_id, group, _ = value
        metadata = {
            "group_name": "se",
            "file_type": "section",
            "section_number": section_id,
            "group": group,
            "document_name": mid[0] if len(mid) > 0 else "",
            "section_name": " ".join(mid).lower().replace("  ", " "),
            "filename": filename,
            "chunk_number": "0",
        }
        with open(filepath + "_metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f)

    def create_filepath(self, section_name: str, output_dir: str) -> str:
        """Creates a file-system-friendly path for saving a document section.

        * Combines higher-level group names.
        * Removes leading digits, whitespace, and hyphens from the section name.
        * Replaces non-alphanumeric characters with underscores.
        * Condenses multiple underscores into single underscores.

        Args:
            section_name (str): The name of the section being saved.
            output_dir (str): The directory where the generated file should be
                saved.

        Returns:
            str: A filepath constructed from the provided information.
        """
        filename = re.sub(r"^\d+\s*-+", "", section_name.lower())
        filename = re.sub(r"[^\w\s&0-9]|(\s+)", "_", filename)
        filename = re.sub(r"_+", "_", filename)
        filename = re.sub(r"(_$)", "", filename)
        filename = "se" + filename
        filepath = os.path.join(output_dir, filename)
        return filepath

    def create_file(
        self, content: dict[str, tuple[str, str, str]], output_dir: str
    ):
        """Creates text files and associated metadata files from a content dictionary.

        Args:
            content: A dictionary where keys are hierarchical structures and values
                are tuples containing (section_id, group, formatted_page_content).
            output_dir: The directory where the output files will be saved.
        """
        visited = set()
        for key, value in content.items():
            filepath = self.create_filepath(key, output_dir)

            if filepath in visited:
                continue
            visited.add(filepath)
            page_content = value[2]
            with open(filepath + ".txt", "w", encoding="utf-8") as f:
                f.write(page_content)

            self.create_metadata(key, value, filepath)

    def process(self, output_dir: str) -> bool:
        """Main function that controls the processing of a XML file, including extraction, metadata creation, chunking, and file saving.

        This method assumes the file is in a suitable XML format for the chunking
        logic.

        Args:
            output_dir (str): The directory where the processed files should be
                saved.

        Returns:
            bool: True if processing was successful, False otherwise.
        """
        if self.xml_chunking == "default":
            self.modify_file()

            tree = ET.parse(self.filepath)
            root = tree.getroot()
            content = {}

            self.explore_xml_tree(root, content, [], set())
            if not content:
                return False
            self.create_file(content, output_dir)
            return True

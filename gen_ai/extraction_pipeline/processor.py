"""This module provides tools for extracting data from supported document formats (.pdf, .docx, .xml, .json).

It includes functions to process configuration files, process documents within a
directory, and a main function for command-line usage.
"""

import argparse
import os
import tempfile

from gen_ai.extraction_pipeline.document_extractors.document_processor import DocumentProcessor
from google.cloud import storage
import yaml

CONFIG_FILEPATH = "gen_ai/extraction_pipeline/config.yaml"
PROCESSABLE_FILETYPES = set([".pdf", ".docx", ".xml", ".json"])


def process_config_file(config_file: str = "config.yaml") -> dict[str, str]:
    """Reads a YAML configuration file and extracts all parameters.

    Args:
        config_file (str): Path to the YAML configuration file. Defaults to
            "config.yaml".

    Returns:
        dict: A dictionary containing the extracted parameters.
    """

    with open(config_file, "r", encoding="utf-8") as file:
        try:
            config = yaml.safe_load(file)
            return config
        except yaml.YAMLError as exception:
            print("Error parsing YAML file:", exception)
    return {}


def split_bucket_and_directory(uri: str):
    """Splits a GS bucket URI (gs://bucket_name/directory/path) into the bucket name and directory path.

    Args:
        uri (str): The GS bucket URI.

    Returns:
        tuple: A tuple containing the bucket name (str) and directory path (str).
    """

    parts = uri.split("/", 3)
    if len(parts) < 3:
        raise ValueError(
            "Invalid GS URI format. Must contain bucket name and directory path"
        )

    bucket_name = parts[2]
    directory_path = parts[3] if len(parts) == 4 else ""
    return bucket_name, directory_path


def process_directory(
        input_dir: str, output_dir: str, config_file_parameters: dict[str, str]
):
    """Processes all files within a specified input directory.

    This function iterates through each file in the input directory,
    creates a DocumentProcessor instance, and utilizes the instance's
    process() method to extract and save data from the file to the output
    directory.

    Args:
        input_dir (str): Path to the directory containing files to be processed.
        output_dir (str): Path to the directory where processed results will be
            stored.
        config_file_parameters (dict[str, str]): Configuration parameters.
    """
    success = 0
    failure = 0
    for filename in os.listdir(input_dir):
        file_extension = os.path.splitext(filename)[-1]
        if file_extension in PROCESSABLE_FILETYPES:
            filepath = os.path.join(input_dir, filename)
            extractor = DocumentProcessor(filepath, config_file_parameters)
            if extractor(output_dir):
                print(f"Successfully processed: {filepath}")
                success += 1
            else:
                print(f"Unsuccessful extraction from {filepath}")
                failure += 1
        else:
            print(
                f"Failed extraction on: {filename}\nNot implemented File Extension"
                f" {file_extension}"
            )
    print(f"Successfully processed {success} out of {success+failure} files.")


def process_gsbucket(
    input_dir: str, output_dir: str, config_file_parameters: dict[str, str]
):
    """Processes all files within a specified cloud bucket.

    This function iterates through each file in the input bucket, stores them in
    local temporary directory. Then creates a DocumentProcessor instance, and
    utilizes the instance's
    process() method to extract and save data from the file to the output
    directory.

    Args:
        input_dir (str): Path to the directory containing files to be processed.
        output_dir (str): Path to the directory where processed results will be
            stored.
        config_file_parameters (dict[str, str]): Configuration parameters.
    """
    success = 0
    failure = 0
    source_bucket_name, directory = split_bucket_and_directory(input_dir)
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(source_bucket_name)

    with tempfile.TemporaryDirectory() as tmp_directory:
        blobs = bucket.list_blobs(prefix=directory)
        for blob in blobs:
            file_extension = os.path.splitext(blob.name)[-1]
            if file_extension in PROCESSABLE_FILETYPES:
                basename = os.path.basename(blob.name)
                destination_file_name = os.path.join(tmp_directory, basename)
                blob.download_to_filename(destination_file_name)
                extractor = DocumentProcessor(
                    destination_file_name, config_file_parameters
                )
                if extractor(output_dir):
                    print(f"Successfully processed: {blob.name}")
                    success += 1
                else:
                    print(f"Unsuccessful extraction from {blob.name}")
                    failure += 1
            else:
                print(
                    f"Failed extraction on: {blob.name}\nNot implemented File Extension"
                    f" {file_extension}"
                )

    print(f"Successfully processed {success} out of {success+failure} files.")


def main():
    """Main function of the extraction pipeline."""
    parser = argparse.ArgumentParser(
        prog="DocumentsExtractor", description="Process docx files in directory"
    )
    parser.add_argument(
        "-i", "--input_dir", help="Input directory", required=True
    )
    parser.add_argument(
        "-o", "--output_dir", help="Output directory", default="output_data"
    )
    args = parser.parse_args()

    config_file_parameters = process_config_file(CONFIG_FILEPATH)
    if args.input_dir.startswith("gs://"):
        process_gsbucket(args.input_dir, args.output_dir, config_file_parameters)
    else:
        process_directory(args.input_dir, args.output_dir, config_file_parameters)


if __name__ == "__main__":
    main()

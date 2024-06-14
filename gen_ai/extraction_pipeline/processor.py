"""This module provides tools for extracting data from supported document formats (.pdf, .docx, .xml, .json).

It includes functions to process configuration files, process documents within a
directory, and a main function for command-line usage.
"""
import argparse
from concurrent.futures import as_completed, ProcessPoolExecutor
from datetime import datetime, timezone, timedelta
import os
import re
import shutil
import subprocess
import tempfile
import time
from timeit import default_timer

from gen_ai.extraction_pipeline.document_extractors.document_processor import DocumentProcessor
from google.cloud import storage
import yaml

CONFIG_FILEPATH = "gen_ai/extraction_pipeline/config.yaml"
PROCESSABLE_FILETYPES = set([".pdf", ".docx", ".xml", ".json", ".html", ".att_ni_xml"])
WAIT_TIME = 600 # seconds or 10 mins

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
) -> bool:
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
    Returns:
       bool: True if the operation was successful, False otherwise.
    """
    success = 0
    failure = 0
    futures = {}
    start_time = default_timer()
    with ProcessPoolExecutor() as executor:
        for filename in os.listdir(input_dir):
            file_extension = os.path.splitext(filename)[-1]
            if file_extension in PROCESSABLE_FILETYPES:
                
                filepath = os.path.join(input_dir, filename)
                extractor = DocumentProcessor(filepath, config_file_parameters)
                futures[executor.submit(extractor, output_dir)] = filepath
                print(f"Added {filepath}")
            else:
                print(
                    f"Failed extraction on: {filename}\nNot implemented File Extension"
                    f" {file_extension}"
                )

        for future in as_completed(futures):
            if future.result():
                print(f"Successfully processed: {futures[future]}")
                success += 1
            else:
                print(f"Unsuccessful extraction from {futures[future]}")
                failure += 1

    print(f"Successfully processed {success} out of {success+failure} files.")
    print(f"Total processing time: {default_timer()-start_time}")

    if success:
        return True
    return False


def process_gsbucket(
    input_dir: str, 
    output_dir: str, 
    config_file_parameters: dict[str, str],
    since_timestamp: datetime | None = None
) -> bool:
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
        since_timestamp (datetime | None): Timestamp from which to process files.
    Returns:
       bool: True if the operation was successful, False otherwise.
    """
    success = 0
    failure = 0
    source_bucket_name, directory = split_bucket_and_directory(input_dir)
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(source_bucket_name)

    if since_timestamp is None:
        since_timestamp = datetime.min.replace(tzinfo=timezone.utc)

    with tempfile.TemporaryDirectory() as tmp_directory:
        blobs = bucket.list_blobs(prefix=directory)
        for blob in blobs:
            if blob.time_created > since_timestamp:
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
    if success:
        return True
    return False


def process_gsbucket_inloop(
    input_dir: str, 
    config_file_parameters: dict[str, str],
    output_bucket: str
):
    """
    Continuously processes new files from a Google Cloud Storage (GCS) bucket with specified intervals.

    This function repeatedly performs the following steps in a loop:

    1. Checks if enough time (WAIT_TIME) has passed since the last processing.
    2. If so, it calls the `process_gsbucket` function to extract data from the input GCS bucket, placing the output in a temporary directory.
    3. Copies the extracted data from the temporary directory to the output GCS bucket using the `copy_files_to_bucket` function.
    4. Removes the temporary directory.

    Args:
        input_dir (str): The GCS bucket path containing the input files.
        config_file_parameters (dict[str, str]): A dictionary containing parameters for the `process_gsbucket` function.
        output_bucket (str): The GCS bucket path to store the extracted output.
    """
    last_time = datetime.min.replace(tzinfo=timezone.utc)

    while True:
        current_time = datetime.now(timezone.utc)
        if current_time - last_time > timedelta(seconds=WAIT_TIME):
            print("Performing an extraction round")
            temp_output_dir = f"temporary_directory_{current_time}"
            os.makedirs(temp_output_dir)
            processed = process_gsbucket(input_dir, temp_output_dir, config_file_parameters, since_timestamp=last_time)
            if processed:
                copied = copy_files_to_bucket(temp_output_dir, output_bucket)
                if copied:
                    print(f"Successfully copied extractions to gs bucket {output_bucket}")
            shutil.rmtree(temp_output_dir)
            print(f"Processed gs bucket at: {current_time}")

        last_time = current_time

        time.sleep(60)


def copy_files_to_bucket(output_dir: str, gs_bucket: str) -> bool:
    """Copies files from a local output directory to a designated Google Cloud Storage bucket.

    Args:
        output_dir (str): Path to the local directory containing files to be copied.
        gs_bucket (str): The Google Cloud Storage bucket name in the format 'gs://bucket_name'

    Returns:
       bool: True if the copy operation was successful, False otherwise.

    Raises:
        subprocess.CalledProcessError: If the 'gsutil' command fails to execute successfully.
    """
    if not re.match(r"^gs://[a-z0-9.-_]+", gs_bucket):
        print(f"Wrong format of gs bucket address: {gs_bucket}")
        return False
    now = datetime.now()
    output_directory = f"extractions{now.year}{now.month:02d}{now.day:02d}"
    
    if not gs_bucket.endswith("/"):
        gs_bucket += "/"
    command = ["gsutil", "-m", "cp", "-r", f"{output_dir}/*", f"{gs_bucket}{output_directory}/"]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print("Error copying files to bucket")
        return False
    return True


def main():
    """Main function of the extraction pipeline."""
    parser = argparse.ArgumentParser(
        prog="DocumentsExtractor", description="Process files in directory"
    )
    parser.add_argument(
        "mode", choices=["batch", "continuous"], help="Processing mode: batch or continuous"
    )

    parser.add_argument(
        "-i", "--input_dir", help="Input directory", required=True
    )
    parser.add_argument(
        "-o", "--output_dir", help="Output directory", default="output_data"
    )
    parser.add_argument(
        "-gs", "--gs_bucket", help="Output gs bucket where to upload data after extraction"
    )
    args = parser.parse_args()

    config_file_parameters = process_config_file(CONFIG_FILEPATH)

    if args.mode == "batch":
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)
            print(f"Directory '{args.output_dir}' created.")

        if args.input_dir.startswith("gs://"):
            processed = process_gsbucket(args.input_dir, args.output_dir, config_file_parameters)
        else:
            processed = process_directory(args.input_dir, args.output_dir, config_file_parameters)

        if args.gs_bucket and processed:
            copied = copy_files_to_bucket(args.output_dir, args.gs_bucket)
            if copied:
                print(f"Successfully copied extractions to gs bucket {args.gs_bucket}")

    elif args.mode == "continuous":
        if args.gs_bucket is None:
            parser.error("Argument -gs/--gs_bucket is required for continuous mode.")
        process_gsbucket_inloop(args.input_dir, config_file_parameters, args.gs_bucket)

if __name__ == "__main__":
    main()

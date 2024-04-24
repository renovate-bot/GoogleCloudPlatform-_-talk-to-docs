"""
This module provides tools for interacting with Google BigQuery, including functions for creating clients,
datasets, and tables, as well as loading data. It leverages Google Cloud BigQuery to manage large-scale data
and analytics. The module contains utility functions to facilitate the creation and management of BigQuery
resources such as datasets and tables, and it provides a method to directly load data from a pandas DataFrame
into BigQuery, handling schema and client initialization. Additionally, it includes a specialized class
for converting structured data related to query states into a format suitable for analytics in BigQuery.

Classes:
    BigQueryConverter - Converts query state data into a pandas DataFrame for upload to BigQuery.

Functions:
    create_bq_client(project_id)
    create_dataset(client, dataset_id, location, recreate_dataset)
    create_table(client, table_id, schema, recreate_table)
    load_data_to_bq(client, table_id, schema, df)

Exceptions:
    GoogleAPIError - Handles API errors that may occur during interaction with Google services.
"""

import datetime
import getpass
import json
import uuid

import google.auth
import pandas as pd
from google.api_core.exceptions import GoogleAPIError, NotFound
from google.cloud import bigquery
from google.cloud.bigquery.schema import SchemaField

from gen_ai.common.ioc_container import Container
from gen_ai.common.memorystore_utils import convert_dict_to_relevancies, convert_dict_to_summaries
from gen_ai.deploy.model import QueryState


def create_bq_client(project_id: str | None = None) -> bigquery.Client | None:
    """Creates a BigQuery client.
    If project_id is not specified, the default project ID will be used.
    If the default project ID cannot be determined, an error will be raised.
    Args:
        project_id (str, optional): The project ID to use. Defaults to None.
    Returns:
        A BigQuery client.
    """
    if project_id is None:
        try:
            _, project_id = google.auth.default()
        except GoogleAPIError as e:
            print(f"Failed to authenticate: {e}")
            return None
    try:
        client = bigquery.Client(project=project_id)
    except GoogleAPIError as e:
        print(f"Failed to create BigQuery client: {e}")
        return None
    return client


def create_dataset(
    client: bigquery.Client, dataset_id: str, location: str = "US", recreate_dataset: bool = False
) -> None:
    """Creates a BigQuery dataset.
    If the dataset already exists, it will be deleted and recreated if recreate_dataset is True.
    Otherwise, an error will be raised.
    Args:
        client (bigquery.Client): The BigQuery client.
        dataset_id (str): The ID of the dataset to create.
        location (str, optional): The location of the dataset. Defaults to "US".
        recreate_dataset (bool, optional): Whether to recreate the dataset if it already exists. Defaults to False.
    """
    if recreate_dataset:
        client.delete_dataset(dataset_id, delete_contents=True, not_found_ok=True)
        print(f"Dataset {dataset_id} and its contents have been deleted.")
    try:
        client.get_dataset(dataset_id)
        print(f"Dataset {client.project}.{dataset_id} already exists")
    except NotFound:
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = location
        dataset = client.create_dataset(dataset, timeout=30)
        print(f"Created dataset {client.project}.{dataset.dataset_id}")


def create_table(
    client: bigquery.Client, table_id: str, schema: list[SchemaField], recreate_table: bool = False
) -> None:
    """Creates a BigQuery table.
    If the table already exists, it will be deleted and recreated if recreate_table is True.
    Otherwise, an error will be raised.
    Args:
        client (bigquery.Client): The BigQuery client.
        table_id (str): The ID of the table to create.
        schema (List[bigquery.SchemaField]): The schema of the table.
        recreate_table (bool, optional): Whether to recreate the table if it already exists. Defaults to False.
    """
    if recreate_table:
        try:
            client.get_table(table_id)
            client.delete_table(table_id)
            print(f"Table {table_id} deleted.")
        except NotFound:
            print(f"Table {table_id} does not exist. Skipping deletion.")

    table = bigquery.Table(table_id, schema=schema)
    try:
        client.get_table(table_id)
        print(f"Table {table_id} already exists.")
    except NotFound:
        table = client.create_table(table)
        print(f"Table {table_id} created.")


def load_data_to_bq(client: bigquery.Client, table_id: str, schema: list[SchemaField], df: pd.DataFrame) -> None:
    """Loads data from a pandas DataFrame to a BigQuery table.
    The table will be created if it does not already exist.
    If the table already exists, it will be overwritten.
    Args:
        client (bigquery.Client): The BigQuery client.
        table_id (str): The ID of the table to load data to.
        schema (List[bigquery.SchemaField]): The schema of the table.
        df (pandas.DataFrame): The DataFrame to load data from.
    """
    job_config = bigquery.LoadJobConfig(schema=schema)
    job = None
    try:
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        print(f"Loaded {job.output_rows} rows into {table_id}.")
    except GoogleAPIError as e:
        print(f"An error occurred: {e}")
        if job and job.errors:
            for error in job.errors:
                print(f"Error: {error['message']}")
                if "location" in error:
                    print(f"Field that caused the error: {error['location']}")


class BigQueryConverter:
    """
    A utility class for converting query state data into a pandas DataFrame that can be uploaded to BigQuery.

    This class is used to convert structured data from various stages of query processing, encapsulating it into
    a DataFrame. The DataFrame format is suitable for analytics and can be directly uploaded to BigQuery for
    further analysis. It handles the extraction of relevant fields from log snapshots associated with each
    query state, transforming them into a tabular form.

    Methods:
        convert_query_state_to_prediction(query_state, log_snapshots) - Converts log snapshots and a query state
                                                                        into a DataFrame structured for BigQuery.

    Usage:
        converter = BigQueryConverter()
        dataframe = converter.convert_query_state_to_prediction(query_state, log_snapshots)
    """

    @staticmethod
    def convert_query_state_to_prediction(query_state: QueryState, log_snapshots: list[dict]) -> pd.DataFrame:
        data = {
            "user_id": [],
            "prediction_id": [],
            "timestamp": [],
            "system_state_id": [],
            "session_id": [],
            "question_id": [],
            "question": [],
            "react_round_number": [],
            "response": [],
            "retrieved_documents_so_far": [],
            "post_filtered_documents_so_far": [],
            "retrieved_documents_so_far_content": [],
            "post_filtered_documents_so_far_content": [],
            "post_filtered_documents_so_far_all_metadata": [],
            "confidence_score": [],
            "response_type": [],
            "run_type": [],
            "time_taken_total": [],
            "time_taken_retrieval": [],
            "time_taken_llm": [],
            "tokens_used": [],
            "summaries": [],
            "relevance_score": [],
            "additional_question": [],
            "plan_and_summaries": [],
        }
        max_round = len(log_snapshots) - 1
        for round_number, log_snapshot in enumerate(log_snapshots):
            react_round_number = round_number
            response = query_state.answer or ""
            retrieved_documents_so_far = json.dumps(
                [{"original_filepath": x["metadata"]["original_filepath"]} for x in log_snapshot["pre_filtered_docs"]]
            )
            post_filtered_documents_so_far = json.dumps(
                [{"original_filepath": x["metadata"]["original_filepath"]} for x in log_snapshot["post_filtered_docs"]]
            )
            retrieved_documents_so_far_content = json.dumps(
                [{"page_content": x["page_content"]} for x in log_snapshot["pre_filtered_docs"]]
            )
            post_filtered_documents_so_far_content = json.dumps(
                [{"page_content": x["page_content"]} for x in log_snapshot["post_filtered_docs"]]
            )
            post_filtered_documents_so_far_all_metadata = json.dumps([x for x in log_snapshot["post_filtered_docs"]])
            time_taken_total = query_state.time_taken
            time_taken_retrieval = 0
            time_taken_llm = 0
            response_type = "final" if react_round_number == max_round else "intermediate"

            tokens_used = query_state.tokens_used if query_state.tokens_used is not None else 0
            prediction_id = str(uuid.uuid4())
            system_state_id = str(uuid.uuid4())
            session_id = Container.session_id if hasattr(Container, "session_id") else str(uuid.uuid4())
            timestamp = datetime.datetime.now()
            confidence_score = query_state.confidence_score
            summary = json.dumps([convert_dict_to_summaries(x) for x in log_snapshot["pre_filtered_docs"]])
            relevance_score = json.dumps([convert_dict_to_relevancies(x) for x in log_snapshot["pre_filtered_docs"]])
            additional_question = log_snapshot["additional_information_to_retrieve"]
            plan_and_summaries = log_snapshot["plan_and_summaries"]

            data["user_id"].append(getpass.getuser())
            data["prediction_id"].append(prediction_id)
            data["timestamp"].append(timestamp)
            data["system_state_id"].append(system_state_id)
            data["session_id"].append(session_id)
            data["question_id"].append("")
            data["question"].append(query_state.question)
            data["react_round_number"].append(str(react_round_number))
            data["response"].append(response)
            data["retrieved_documents_so_far"].append(retrieved_documents_so_far)
            data["post_filtered_documents_so_far"].append(post_filtered_documents_so_far)
            data["retrieved_documents_so_far_content"].append(retrieved_documents_so_far_content)
            data["post_filtered_documents_so_far_content"].append(post_filtered_documents_so_far_content)
            data["post_filtered_documents_so_far_all_metadata"].append(post_filtered_documents_so_far_all_metadata)
            data["confidence_score"].append(confidence_score)
            data["response_type"].append(response_type)
            data["run_type"].append("test")
            data["time_taken_total"].append(time_taken_total)
            data["time_taken_retrieval"].append(time_taken_retrieval)
            data["time_taken_llm"].append(time_taken_llm)
            data["tokens_used"].append(tokens_used)
            data["summaries"].append(summary)
            data["relevance_score"].append(relevance_score)
            data["additional_question"].append(additional_question)
            data["plan_and_summaries"].append(plan_and_summaries)

        df = pd.DataFrame(data)
        return df

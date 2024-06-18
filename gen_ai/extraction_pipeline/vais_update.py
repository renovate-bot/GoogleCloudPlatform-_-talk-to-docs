import json
import os

import google.auth
import pandas as pd
import requests
from google.auth.transport.requests import Request
from google.cloud import bigquery


def update_the_data_store(input_dir: str, config: dict[str, str], data_store_id: str | None = None):
    project_id = config.get("project_id")
    dataset_id = config.get("dataset_id")
    table_name = config.get("table_name")
    if not data_store_id or data_store_id == "datastore":
        data_store_id = config.get("data_store_id")

    # BigQuery Client
    client = bigquery.Client(project=project_id)

    # create dataset and table if not exists
    print("Start create_dataset_and_table")
    create_dataset_and_table(client, project_id, dataset_id, table_name)
    print("Done create_dataset_and_table")
    # create merged json file
    print("Start merge_json_files")
    df = merge_json_files(input_dir)
    print("Done merge_json_files")

    # put the json file into bq
    print("Start insert_all_rows")
    table_id = f'{project_id}.{dataset_id}.{table_name}'
    inserted = insert_all_rows(df, client, table_id)
    if not inserted:
        return False
    print("Done insert_all_rows")

    # fetch from bq to data store
    print("Start updated_data_store")
    updated_data_store = import_bigquery_to_datastore_batched(
        project_id,
        table_id,
        data_store_id,
        batch_size=100
    )
    print("Done updated_data_store")
    if not updated_data_store:
        return False
    return True


def merge_json_files(input_dir: str) -> pd.DataFrame:
    final_json = {}

    for filename in os.listdir(input_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(input_dir, filename)

            with open(filepath, 'r', encoding="utf-8") as f:
                data = json.load(f)
            key = data.pop("original_filepath").replace(".html", "")
            final_json[key] = data

            # Look for matching text file
            txt_filename = filename.replace("_metadata.json", "") + ".txt"
            txt_filepath = os.path.join(input_dir, txt_filename)
            if os.path.exists(txt_filepath):
                with open(txt_filepath, 'r') as txt_f:
                    content = txt_f.read()
                final_json[key]["content"] = str(content)
    df = pd.DataFrame(final_json.items(), columns=['id', 'JsonData'])
    return df


def create_dataset_and_table(client, project_id: str, dataset_id: str, table_name: str):

    # Create the dataset if it doesn't exist
    dataset = bigquery.Dataset(f"{project_id}.{dataset_id}")
    client.create_dataset(dataset, exists_ok=True)

    # Table Schema
    schema = [
        bigquery.SchemaField('id', 'STRING', mode='REQUIRED'),
        bigquery.SchemaField(
            'JsonData', 
            'STRING', 
            mode='NULLABLE')
    ]

    table_id = f'{project_id}.{dataset_id}.{table_name}'

    table_exists = False
    try:
        client.get_table(table_id)  # Will raise NotFound exception if table doesn't exist
        table_exists = True
    except Exception as e:  # Broad exception to catch any potential issues
        pass

    # Create Table (if not exists)
    if not table_exists:
        table = bigquery.Table(table_id, schema=schema)
        table = client.create_table(table)
        print(f"Created table {table_id}")
    else:
        print(f"Table {table_id} already exists. Please append rows if needed.")
    #TODO: return smth bool or Table


def insert_all_rows(df: pd.DataFrame, client, table_id: str):
    rows_to_insert = [
        {"id": df['id'][i], "JsonData": str(df['JsonData'][i])}
        for i in range(len(df))
    ]

    # Ingest Data with APPEND write disposition
    table = client.get_table(table_id)
    errors = client.insert_rows(table, rows_to_insert, row_ids=[None]*len(rows_to_insert))

    if errors == []:
        print(f"New rows have been added.")
        return True
    else:
        print(f"Encountered errors while inserting rows: {errors}")
        return False


def import_bigquery_to_datastore_batched(project_id: str, table_id: str, data_store_id: str, batch_size=100):
    """Imports data from BigQuery to Generative AI App Builder Datastore in batches."""
    print(project_id)
    print(table_id)
    print(data_store_id)
    # Authenticate with Google Cloud
    credentials, _ = google.auth.default()
    credentials.refresh(Request())
    auth_token = credentials.token

    # 1. Fetch data from BigQuery
    client = bigquery.Client(project=project_id)
    query = f"SELECT id, JsonData FROM `{table_id}`"
    query_job = client.query(query)

    # 2. Prepare and send documents in batches
    parent = f"projects/{project_id}/locations/global/collections/default_collection/dataStores/{data_store_id}/branches/0"
    url = f"https://discoveryengine.googleapis.com/v1/{parent}/documents:import"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }

    all_rows = list(query_job.result())  # Fetch all rows once

    if not all_rows:
        print("Rows not found.")
        return False

    for i in range(0, len(all_rows), batch_size):
        batch_rows = all_rows[i : i + batch_size]
        documents = [
            {"id": row.id, "jsonData": row.JsonData}
            for row in batch_rows
        ]  # No need to filter None, as list(query_job.result()) handles it

        if not documents:
            print("No documents found in this batch.")  # This shouldn't happen if rows exist
            continue

        data = {
            "inlineSource": {
                "documents": documents  
            }
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            print(f"Batch imported successfully! (Rows {i+1}-{i+len(documents)})")
        else:
            print(f"Error importing batch: {response.status_code}, {response.text}")
            return False
    return True

import json5
import os
import re

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
    create_dataset_and_table(client, project_id, dataset_id, table_name)
    print(f"Created dataset and table: {dataset_id}.{table_name}")
    # create merged json file
    df = merge_json_files(input_dir)
    print(f"Created dataframe from {len(df))} files")

    # put the json file into bq
    table_id = f'{project_id}.{dataset_id}.{table_name}'
    inserted = insert_all_rows(df, client, table_id)
    if not inserted:
        return False
    print(f"Pushed")

    # fetch from bq to data store
    updated_data_store = import_bigquery_to_datastore_batched(
        project_id,
        table_id,
        data_store_id,
        df,
        batch_size=100
    )
    print("Done updated_data_store")
    if not updated_data_store:
        return False
    return True

def replace_consecutive_whitespace(text):
    """Replaces consecutive whitespace characters with a single space."""
    # return re.sub(r'(\s)\1+', r'\1', text)
    return re.sub(r'\s+', ' ', text)

def remove_stars_and_consecutive_whitespaces(text):
    """Removes all star signs and replaces consecutive whitespaces with a single space."""
    text_without_stars = re.sub(r'\*', ' ', text)  # Remove stars
    return replace_consecutive_whitespace(text_without_stars)  # Replace

def merge_json_files(input_dir: str) -> pd.DataFrame:
    final_json = {}

    for filename in os.listdir(input_dir):
        if filename.endswith("_metadata.json"):
            metadata_filepath = os.path.join(input_dir, filename)
            with open(metadata_filepath, "r", encoding="utf-8") as f:
                data = json5.load(f)
            key = os.path.basename(data.pop("original_filepath"))
            key = os.path.splitext(key)[0]
            key += f"_{data['section_name']}"
            key = re.sub(r"[^\w-]+", "", key)
            if len(key) > 60:
                key = key[:30] + key[-30:]
            final_json[key] = data

            # Look for matching text file
            txt_filename = filename.replace("_metadata.json", ".txt")
            txt_filepath = os.path.join(input_dir, txt_filename)
            if not os.path.exists(txt_filepath):
                continue
            with open(txt_filepath, "r", encoding="utf-8") as txt_f:
                content = txt_f.read()
            content = remove_stars_and_consecutive_whitespaces(content)
            if content and not content.isspace():
                final_json[key]["content"] = content

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

    table = client.get_table(table_id)
    errors = client.insert_rows(table, rows_to_insert, row_ids=[None]*len(rows_to_insert))

    if not errors:
        print("Inserted all files into BigQuery.")
        return True
    else:
        print(f"Encountered errors while inserting rows: {errors}")
        return False


def import_bigquery_to_datastore_batched(project_id: str, table_id: str, data_store_id: str, df: pd.DataFrame, batch_size=100):
    """Imports data from BigQuery to Generative AI App Builder Datastore in batches."""
    print(project_id)
    print(table_id)
    print(data_store_id)
    # Authenticate with Google Cloud
    credentials, _ = google.auth.default()
    credentials.refresh(Request())
    auth_token = credentials.token

    all_rows = [
        {"id": df['id'][i], "jsonData": str(df['JsonData'][i])}
        for i in range(len(df))
    ]

    # 2. Prepare and send documents in batches
    parent = f"projects/{project_id}/locations/global/collections/default_collection/dataStores/{data_store_id}/branches/0"
    url = f"https://discoveryengine.googleapis.com/v1/{parent}/documents:import"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }
    total_count = 0
    success_count = 0
    for i in range(0, len(all_rows), batch_size):
        documents = all_rows[i : i + batch_size]

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
            r = json5.loads(response.text)
            if "failureCount" in r["metadata"]:
                print(f"Errors in importing batch: {r['metadata']['failureCount']} / {len(documents)}")
                success_count -= int(r["metadata"]["failureCount"])
            else:
                print(f"Batch imported successfully! (Rows {i+1}-{i+len(documents)})")
            print(r)
            total_count += len(documents)
            success_count += len(documents)
        else:
            print(f"Error importing batch: {response.status_code}, {response.text}")
            return False
    print(f"Successfully imported {success_count} of {total_count} documents.")
    return True

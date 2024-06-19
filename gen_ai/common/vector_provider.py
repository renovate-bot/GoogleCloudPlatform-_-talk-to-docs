"""Module for managing vectorization, vector storage, and retrieval strategies.

This module provides classes and functions for:

* **VectorStore:** Abstract base class defining vector search interfaces.
* **ChromaVectorStore:** Concrete implementation using Chroma for vector storage and search.
* **VertexVectorStore:**  Concrete implementation leveraging Vertex AI for vector storage and search.
* **VectorStrategy:** Abstract base class for vector embedding and index creation logic.
* **VectorStrategyProvider:** Provides a factory for selecting appropriate VectorStrategy.
* **ChromaVectorStrategy:**  Concrete implementation of VectorStrategy for Chroma.
* **VertexAIVectorStrategy:** Concrete implementation of VectorStrategy for Vertex AI.
"""

import glob
import json
import os
import random
import shutil
import string
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd
import requests
import tqdm
from google.api_core.client_options import ClientOptions
from google.auth.transport.requests import Request
from google.cloud import aiplatform, discoveryengine
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import storage
from google.oauth2 import id_token
from langchain.schema import Document
from langchain.schema.embeddings import Embeddings
from langchain.vectorstores import Chroma

from gen_ai.common.common import default_extract_data
from gen_ai.common.inverted_index import InvertedIndex
from gen_ai.common.storage import Storage


@dataclass
class DeployedEndpoint:
    """Class for keeping track of Deployed Endpoints."""

    index: str
    index_endpoint_name: str
    deployed_index_endpoint_name: str
    plan: str


class VectorStore(ABC):
    """Abstract base class for vector stores.

    Defines the interface for similarity search and maximum marginal relevance search.
    """

    @abstractmethod
    def similarity_search(self, query: str, k: int = 4, **kwargs) -> list[Document]:
        """Performs a similarity search on the vector store.

        Args:
            query (str): The query text.
            k (int, optional): The number of results to return. Defaults to 4.
            **kwargs: Additional arguments to be passed to the underlying implementation.

        Returns:
            List[Document]: A list of LangChain Document objects representing the results.
        """
        pass

    @abstractmethod
    def max_marginal_relevance_search(
        self, query: str, k: int = 4, fetch_k: int = 20, lambda_mult: float = 0.5, **kwargs
    ) -> list[Document]:
        """Performs a maximum marginal relevance (MMR) search on the vector store.

        Args:
            query (str): The query text.
            k (int, optional): The number of results to return. Defaults to 4.
            fetch_k (int, optional):  The number of documents to initially retrieve. Defaults to 20
            lambda_mult (float, optional): Multiplier for controlling MMR tradeoff. Defaults to 0.5.
            **kwargs: Additional arguments to be passed to the underlying implementation.

        Returns:
            List[Document]: A list of LangChain Document objects representing the results.
        """
        pass


class VectorStrategy(ABC):
    """Abstract base class for defining vector embedding and index creation strategies.

    Attributes:
        storage_interface (Storage): An interface for interacting with storage systems.
    """

    def __init__(self, storage_interface: Storage, config: dict[str, str]):
        self.storage_interface = storage_interface
        self.config = config

    @abstractmethod
    def get_vector_indices(
        self, regenerate: bool, embeddings: Embeddings, vector_indices: dict[str, str], processed_files_dir: str
    ):
        """Retrieves or creates vector indices based on the provided configuration.

        Args:
            regenerate (bool): If True, forces index regeneration.
            embeddings (Embeddings): The embedding model to use for generating vector representations.
            vector_indices (dict[str, str]): Existing vector indices (if any).
            processed_files_dir (str): directory where files are stored

        Returns:
            dict[str, str]: A dictionary mapping plan names to their corresponding vector indices.
        """
        raise NotImplementedError("Cannot be invoked directly from abstract class")


class ChromaVectorStore(VectorStore):
    """Concrete implementation of VectorStore using Chroma for vector storage and search.

    Attributes:
        chroma (Chroma): The Chroma instance for managing the vector store.
    """

    def __init__(self, chroma):
        self.chroma = chroma

    def similarity_search(self, query: str, k: int = 4, **kwargs):
        return self.chroma.similarity_search(query, k, **kwargs)

    def max_marginal_relevance_search(
        self, query: str, k: int = 4, fetch_k: int = 20, lambda_mult: float = 0.5, **kwargs
    ):
        return self.chroma.max_marginal_relevance_search(query, k, fetch_k, lambda_mult, **kwargs)


class VertexVectorStore(VectorStore):
    """Concrete implementation of VectorStore using Vertex AI for vector storage and search.

    Attributes:
        vertex (aiplatform.MatchingEngineIndexEndpoint): Vertex AI endpoint instance.
        index_id (str): The ID of the Vertex AI index.
        embeddings (Embeddings): The embedding model used for generating vectors.
        doc_mapping (dict):  Mapping between document IDs and their textual content/metadata.
    """

    def __init__(self, vertex, index_id, embeddings, doc_mapping) -> None:
        self.vertex = vertex
        self.index_id = index_id
        self.embeddings = embeddings
        self.doc_mapping = doc_mapping

    def convert_to_langchain(self, neighbours):
        docs = []

        for match in neighbours[0]:
            if match.id in self.doc_mapping:
                text = self.doc_mapping[match.id][0]
                metadata = self.doc_mapping[match.id][1]
                doc = Document(page_content=text, metadata=metadata)
                docs.append(doc)
        return docs

    def similarity_search(self, query: str, k: int = 4, **kwargs):
        embs = self.embeddings.embed_documents([query])
        neighbours = self.vertex.find_neighbors(num_neighbors=k, queries=embs, deployed_index_id=self.index_id)
        docs = self.convert_to_langchain(neighbours)
        return docs

    def max_marginal_relevance_search(
        self, query: str, k: int = 4, fetch_k: int = 20, lambda_mult: float = 0.5, **kwargs
    ):
        # vertex AI does not support max marginal search, so we just use similarity search under the hood
        return self.similarity_search(query, k, **kwargs)


class VertexAISearchVectorStore(VectorStore):
    """Concrete implementation of VectorStore using Vertex AI Search for vector storage and search.
    # Important: VAIS (VertexAIVectorStore) and VVS (VertexVectorStore) are DIFFERENT THINGS
    Attributes:
        chroma (Chroma): The Chroma instance for managing the vector store.
    """

    def __init__(self, project_id: str, engine_id: str):
        self.project_id = project_id
        self.location = "global"
        self.engine_id = engine_id

    def _search_sample(
        self,
        project_id: str,
        location: str,
        engine_id: str,
        search_query: str,
        k: int = 4,
        filter=filter,
        **kwargs,  # pylint: disable=unused-argument
    ) -> List[discoveryengine.SearchResponse]:
        client_options = (
            ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com") if location != "global" else None
        )

        client = discoveryengine.SearchServiceClient(client_options=client_options)
        # this is VAIS as a generator
        # uncomment it if you want not just retriever but generator also
        # summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
        #     summary_result_count=10,
        #     include_citations=True,
        #     ignore_adversarial_query=True,
        #     ignore_non_summary_seeking_query=True,
        #     model_prompt_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
        #         preamble="Here is the question"
        #     ),
        #     model_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
        #         version="stable",
        #     ),
        # ),
        serving_config = (
            f"projects/{project_id}/locations/{location}/"
            f"collections/default_collection/engines/{engine_id}/"
            "servingConfigs/default_config"
        )
        content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
            extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                max_extractive_segment_count=1, return_extractive_segment_score=True, num_previous_segments=2
            ),
        )
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=search_query,
            page_size=min(10, k),
            content_search_spec=content_search_spec,
            filter=filter,
            query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
                condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
            ),
            spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            ),
        )

        response = client.search(request)
        ls = response.results
        docs = []
        for item in ls:
            content = item.document.derived_struct_data["extractive_segments"][0]["content"]
            score = item.document.derived_struct_data["extractive_segments"][0]["relevanceScore"]
            doc = Document(page_content=content)
            doc.metadata = {
                "original_filepath": item.document.derived_struct_data["title"],
                "section_name": item.document.derived_struct_data["title"],
            }
            docs.append((doc, score))
        return docs

    def similarity_search_with_score(self, query: str, k: int = 4, filter: str = None, **kwargs):

        return self._search_sample(
            project_id=self.project_id,
            location=self.location,
            engine_id=self.engine_id,
            search_query=query,
            k=k,
            filter=filter,
            **kwargs,
        )

    def similarity_search(self, query: str, k: int = 4, **kwargs):
        return self.similarity_search_with_score(query, k)

    def max_marginal_relevance_search(
        self, query: str, k: int = 4, fetch_k: int = 20, lambda_mult: float = 0.5, **kwargs
    ):
        return []


class VectorStrategyProvider:
    """Factory class for selecting the appropriate VectorStrategy implementation."""

    def __init__(self, vector_name):
        self.vector_name = vector_name

    def __call__(self, **kwargs) -> VectorStrategy:
        """Provides the vector strategy.
        Vector strategy consists of two functionalities: vector embeddings and vector indices creation

        Raises:
            ValueError: currently supports openai and vertexai strategies. Raises exception if other types are
            specified

        Returns:
            Embeddings: langchain class of base embeddings
        """
        print(f"Loading {self.vector_name} Vector Strategy...")
        if "vertexai" in self.vector_name:
            return VertexAIVectorStrategy(**kwargs)
        elif "vais" in self.vector_name:
            return VertexAISearchVectorStrategy(**kwargs)
        elif "chroma" in self.vector_name:
            return ChromaVectorStrategy(**kwargs)
        else:
            raise ValueError("Not supported embeddings name in config")


class ChromaVectorStrategy(VectorStrategy):
    """Concrete implementation of VectorStrategy for using Chroma as the vector store."""

    def __init__(self, storage_interface: Storage, config: dict[str, str], vectore_store_path: str) -> None:
        super().__init__(storage_interface, config)
        self.vectore_store_path = f"{vectore_store_path}_chroma"

    def get_vector_indices(
        self, regenerate: bool, embeddings: Embeddings, vector_indices: dict[str, str], processed_files_dir: str
    ):
        if not os.path.exists(self.vectore_store_path) or regenerate:
            if os.path.exists(self.vectore_store_path):
                try:
                    os.rmdir(self.vectore_store_path)
                except OSError as _:
                    os.removedirs(self.vectore_store_path)

            docs = self.storage_interface.process_directory(processed_files_dir, default_extract_data)
            plan_store = Chroma.from_documents(docs, embeddings, persist_directory=self.vectore_store_path)
            plan_store.persist()
            vector_indices = plan_store
        else:
            plan_store = Chroma(persist_directory=self.vectore_store_path, embedding_function=embeddings)
            vector_indices = plan_store

        return vector_indices


class VertexAISearchVectorStrategy(VectorStrategy):
    """Concrete implementation of VectorStrategy for using Vertex AI Search as the vector store."""

    def __init__(self, storage_interface: Storage, config: dict[str, str], vectore_store_path: str) -> None:
        super().__init__(storage_interface, config)
        self.vectore_store_path = f"{vectore_store_path}_vais"
        self.config = config

    def get_vector_indices(
        self, regenerate: bool, embeddings: Embeddings, vector_indices: dict[str, str], processed_files_dir: str
    ):
        aiplatform.init()
        if not os.path.exists(self.vectore_store_path):
            print("No VAIS vector store found, creating one...")
            dataset_name = self.config.get("dataset_name")
            project_id = self.config.get("bq_project_id")

            waize_gcs_uri = self.__prepare_waize_format(processed_files_dir, dataset_name)
            waize_data_store = self.__create_waize_data_store(project_id, dataset_name)
            waize_data_store = self.__import_data_to_waize_data_store(project_id, waize_data_store, waize_gcs_uri)
            waize_engine_id = self.__create_waize_app(project_id, dataset_name, waize_data_store)
            self.__serialize_engine_id(waize_engine_id, waize_data_store, waize_gcs_uri)
        else:
            print("VAIS vector store exists, retrieving the values...")
            waize_engine_id = self.__deserialize_engine_id()

        return VertexAISearchVectorStore(self.config.get("bq_project_id"), waize_engine_id)

    def __deserialize_engine_id(self):
        vais_path = os.path.join(self.vectore_store_path, "vais_urls.json")
        with open(vais_path, "r") as f:
            vais_urls = json.load(f)
        print(f"VAIS urls are: \n {vais_urls}")
        return vais_urls["vais_engine_id"]

    def __serialize_engine_id(self, waize_engine_id, waize_data_store, waize_gcs_uri):
        os.makedirs(self.vectore_store_path, exist_ok=True)
        vais_path = os.path.join(self.vectore_store_path, "vais_urls.json")
        vais_urls = {
            "vais_engine_id": waize_engine_id,
            "vais_data_store": waize_data_store,
            "vais_gcs_uri": waize_gcs_uri,
        }
        with open(vais_path, "w") as f:
            json.dump(vais_urls, f)

        print(f"Saved VAIS urls to {vais_path}")
        print(f"VAIS urls are: \n {vais_urls}")

    def __prepare_waize_format(self, processed_dir, dataset_name):
        """
        Creates a JSONL file from pairs of .txt and _metadata.json files in a local directory
        and uploads them to a new GCS bucket.

        Args:
            processed_dir: The local directory containing the processed files.
            dataset_name: The name to use for the dataset.
        """
        print("Preparing format for VAIS...")
        storage_client = storage.Client()

        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        new_bucket_name = f"{dataset_name}-jsonl-{random_suffix}"
        new_bucket = storage_client.bucket(new_bucket_name)
        new_bucket.create()

        print(f"Copying the Documents and JSONL file to bucket: {new_bucket_name}")
        jsonl_data = []
        all_files = list(os.listdir(processed_dir))
        for i, filename in tqdm.tqdm(enumerate(all_files), total=len(all_files)):
            if filename.endswith("_metadata.json"):
                file_name_base = filename[:-14]  # Remove "_metadata.json"
                txt_file_path = os.path.join(processed_dir, f"{file_name_base}.txt")
                if not os.path.isfile(txt_file_path):
                    continue  # Skip if no matching TXT file

                metadata_path = os.path.join(processed_dir, filename)
                with open(metadata_path, "r") as metadata_file:
                    metadata = json.load(metadata_file)
                metadata_str = json.dumps(metadata)

                txt_blob = new_bucket.blob(f"data/{file_name_base}.txt")
                txt_blob.upload_from_filename(txt_file_path)

                jsonl_entry = {
                    "id": str(i),
                    "jsonData": metadata_str,
                    "content": {"mimeType": "text/plain", "uri": f"gs://{new_bucket_name}/data/{file_name_base}.txt"},
                }
                jsonl_data.append(jsonl_entry)

        jsonl_path = "output.jsonl"
        with open(jsonl_path, "w") as outfile:
            for entry in jsonl_data:
                outfile.write(json.dumps(entry) + "\n")
            jsonl_blob = new_bucket.blob(jsonl_path)
            jsonl_blob.upload_from_filename(jsonl_path)

        return new_bucket_name

    def __create_waize_data_store(self, project_id, dataset_name):
        """Sends an API request to create a data store in Google Discovery Engine.

        Args:
            project_id (str): The ID of your Google Cloud project.

        Returns:
            requests.Response: The response object from the API request.
        """
        print("Creating the Data Store for VAIS...")
        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        new_data_store = f"data_store-{dataset_name}-{random_suffix}"
        new_data_store_name = f"Data store: {new_data_store}"

        access_token = subprocess.check_output("gcloud auth print-access-token", shell=True, text=True).strip()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        }

        url = f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/global/collections/default_collection/dataStores?dataStoreId={new_data_store}"

        data = {
            "displayName": f"{new_data_store_name}",
            "industryVertical": "GENERIC",
            "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
            "contentConfig": "CONTENT_REQUIRED",
        }

        response = requests.post(url, headers=headers, json=data)

        response.raise_for_status()

        return new_data_store

    def __import_finished(self, project_id: str, data_store_id: str):
        client_options = None
        client = discoveryengine.DocumentServiceClient(client_options=client_options)
        parent = client.branch_path(
            project=project_id,
            data_store=data_store_id,
            location="global",
            branch="default_branch",
        )
        print("Checking status of import to VAIS")
        try:
            response = client.list_documents(parent=parent)
            if len(list(response)) > 0:
                return True
        except Exception as e:
            print(f"Error: {e}")
            return False

    def __import_data_to_waize_data_store(self, project_id, data_store_id, waize_gcs_uri):
        """
        Imports documents from a GCS location to Google Discovery Engine using the provided JSONL file.

        Args:
            project_id: The ID of your Google Cloud Project.
            data_store_id: The ID of the data store in Discovery Engine.
            waize_gcs_uri: The GCS URI of the JSONL file containing the documents to import.
        """
        print(f"Importing the Documents to Data Store: {data_store_id}...")
        url = f"https://discoveryengine.googleapis.com/v1/projects/{project_id}/locations/global/collections/default_collection/dataStores/{data_store_id}/branches/0/documents:import"

        auth_token = subprocess.check_output("gcloud auth print-access-token", shell=True, text=True).strip()

        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }

        data = {"gcsSource": {"inputUris": [f"gs://{waize_gcs_uri}/*.jsonl"]}}

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            print(f"Documents Import Job successfully started to Discovery Engine Data Store: {data_store_id}")
        else:
            print(f"Error importing documents: {response.status_code}, {response.text}")

        delay_factor = 2
        while True:
            if self.__import_finished(project_id, data_store_id):
                return data_store_id
            else:
                time.sleep(delay_factor)
                delay_factor = min(delay_factor**2, 300)
                print(f"Documents Import Job is in progress, rechecking again in {delay_factor} seconds...")

    def __create_waize_app(self, project_id, dataset_name, data_store_id):
        """
        Creates a Google Discovery Engine application with the specified settings.

        Args:
            project_id: The ID of your Google Cloud Project.
            dataset_name: A name to incorporate into the generated app ID and name.
            data_store_id: The ID of the data store to associate with the engine.
        """
        print("Creating the VAIS endpoint...")
        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        app_id = f"{dataset_name}-{random_suffix}"
        app_name = f"{dataset_name.capitalize()} Search App ({random_suffix})"

        auth_token = subprocess.check_output("gcloud auth print-access-token", shell=True, text=True).strip()

        url = f"https://discoveryengine.googleapis.com/v1/projects/{project_id}/locations/global/collections/default_collection/engines?engineId={app_id}"

        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        }

        data = {
            "displayName": app_name,
            "dataStoreIds": [data_store_id],
            "solutionType": "SOLUTION_TYPE_SEARCH",
            "searchEngineConfig": {
                "searchTier": "SEARCH_TIER_ENTERPRISE",
                "searchAddOns": ["SEARCH_ADD_ON_LLM"],
            },
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            print(f"Discovery Engine application '{app_name}' (ID: {app_id}) created successfully.")
        else:
            print(f"Error creating application: {response.status_code}, {response.text}")
        return app_id


class VertexAIVectorStrategy(VectorStrategy):
    """Concrete implementation of VectorStrategy for using Vertex AI as the vector store."""

    DEPLOYED_INDEX_ID = "article_index_endpoint_deployed"
    ARTICLE_INDEX = "article_index"
    ARTICLE_INDEX_ENDPOINT = "article_index_endpoint"

    def __init__(self, storage_interface: Storage, config: dict[str, str], vectore_store_path: str) -> None:
        super().__init__(storage_interface, config)
        self.vectore_store_path = f"{vectore_store_path}_vertexai"

    def __create(self, embeddings: Embeddings, processed_files_dir: str):
        if not os.path.exists(self.vectore_store_path):
            print("Creating the directory...")
            os.makedirs(self.vectore_store_path)
        else:
            print("Removing & creating the directory...")
            shutil.rmtree(self.vectore_store_path, ignore_errors=True)
            os.makedirs(self.vectore_store_path)

        docs = self.storage_interface.process_directory(processed_files_dir, default_extract_data)
        all_jsons = {}
        for plan, documents in docs.items():
            store_path = os.path.join(self.vectore_store_path, plan)
            embs = embeddings.embed_documents([x.page_content for x in documents])
            embs_plan = [(f"{plan}_{i}", x) for i, x in enumerate(embs)]
            embs_df = pd.DataFrame(embs_plan, columns=["id", "embedding"])
            plan_output_jsonl = store_path + "_df.json"
            with open(plan_output_jsonl, "w", encoding="utf-8") as f:
                f.write(embs_df.to_json(orient="records", lines=True, force_ascii=False))
            all_jsons[plan] = plan_output_jsonl

        return all_jsons

    def create_bucket_and_copy(self, json_file, random_string):
        prefix = os.path.splitext(os.path.basename(json_file))[0]
        bucket_path = f"{prefix}-vertex-ai-search-{random_string}"
        client = storage.Client()
        bucket = client.bucket(bucket_path)
        bucket.location = "us-central1"
        bucket.create()

        blob = bucket.blob(os.path.basename(json_file))
        blob.upload_from_filename(json_file)
        return bucket_path

    def __copy(self, all_jsons):
        bucket_json_names = {}
        random_string = "".join(random.choices(string.ascii_lowercase, k=6))

        for plan, json_file in all_jsons.items():
            bucket_path = self.create_bucket_and_copy(json_file, random_string)
            print(f"File {json_file} copied to bucket: {bucket_path}")
            bucket_json_names[(json_file, plan)] = bucket_path

        return bucket_json_names

    def __deploy(self, bucket_json_names):
        deployed_endpoints = []
        random_string = "".join(random.choices(string.ascii_lowercase, k=4))
        for key, bucket_path in bucket_json_names.items():
            json_file, plan = key
            prefix = os.path.splitext(os.path.basename(json_file))[0]
            file_index_name = f"{prefix}_{self.ARTICLE_INDEX}_{random_string}"
            file_index_endpoint_name = f"{prefix}_{self.ARTICLE_INDEX_ENDPOINT}_{random_string}"
            file_index_deployed_name = f"{prefix}_{self.DEPLOYED_INDEX_ID}_{random_string}"

            file_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
                display_name=file_index_name,
                contents_delta_uri=f"gs://{bucket_path}/",
                dimensions=768,
                approximate_neighbors_count=10,
            )
            print(file_index)

            file_index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
                display_name=file_index_endpoint_name, public_endpoint_enabled=True
            )
            print(file_index_endpoint)

            file_index_endpoint.deploy_index(index=file_index, deployed_index_id=file_index_deployed_name)
            print(file_index_deployed_name)
            deployed_endpoints.append(
                DeployedEndpoint(file_index_name, file_index_endpoint.resource_name, file_index_deployed_name, plan)
            )

        endpoints_dir = f"{self.vectore_store_path}/endpoints"
        if not os.path.exists(endpoints_dir):
            os.makedirs(endpoints_dir)
        for endpoint in deployed_endpoints:
            endpoint_index = endpoint.index.replace("/", "_")
            with open(f"{endpoints_dir}/{endpoint_index}.txt", "w+", encoding="utf-8") as f:
                f.write(
                    "\n".join(
                        [
                            endpoint.index,
                            endpoint.index_endpoint_name,
                            endpoint.deployed_index_endpoint_name,
                            endpoint.plan,
                        ]
                    )
                )

        return deployed_endpoints

    def get_endpoints(self):
        deployed_endpoints = []
        endpoints_dir = f"{self.vectore_store_path}/endpoints"
        endpoint_files = glob.glob(endpoints_dir + "/*.txt")

        for endpoint_file in endpoint_files:
            with open(endpoint_file, "r+", encoding="utf-8") as f:
                endpoint_lines = f.readlines()
                endpoint_lines = [x.strip().replace("\n", "") for x in endpoint_lines]
                deployed_endpoint = DeployedEndpoint(
                    endpoint_lines[0], endpoint_lines[1], endpoint_lines[2], endpoint_lines[3]
                )
                deployed_endpoints.append(deployed_endpoint)
        return deployed_endpoints

    def get_vector_indices(
        self, regenerate: bool, embeddings: Embeddings, vector_indices: dict[str, str], processed_files_dir: str
    ):
        aiplatform.init()
        if not os.path.exists(self.vectore_store_path):
            all_jsons = self.__create(embeddings, processed_files_dir)
            bucket_json_names = self.__copy(all_jsons)
            deployed_endpoints = self.__deploy(bucket_json_names)
        else:
            deployed_endpoints = self.get_endpoints()

        docs = self.storage_interface.process_directory(processed_files_dir, default_extract_data)
        doc_mapping = InvertedIndex().build_map(docs)

        for deployed_endpoint in deployed_endpoints:
            real_endpoint_object = aiplatform.MatchingEngineIndexEndpoint(deployed_endpoint.index_endpoint_name)
            vector_store = VertexVectorStore(
                real_endpoint_object, deployed_endpoint.deployed_index_endpoint_name, embeddings, doc_mapping
            )
            vector_indices[deployed_endpoint.plan] = vector_store
        return vector_indices

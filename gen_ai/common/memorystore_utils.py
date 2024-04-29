"""
A module for handling operations related to memory storage, particularly for managing query states and document 
conversions within a conversational AI context. 

This module provides functionality to convert documents between JSON and a custom `Document` format, 
generate unique keys for storing query states in Redis, save query states to Redis, and retrieve them based on 
personalized data. It is designed to work within the `gen_ai` project, utilizing the project's inversion of control 
container for Redis connections and custom data types like `PersonalizedData` and `QueryState`.
"""

import json
from dataclasses import asdict
from datetime import datetime
from typing import Any, List

from langchain.schema import Document

from gen_ai.common.ioc_container import Container
from gen_ai.deploy.model import PersonalizedData, QueryState


def generate_query_state_key(personalized_data: PersonalizedData, unique_identifier: str | None = None) -> str:
    """
    Generates a unique key for storing a query state in Redis.

    The key is constructed using the policy number and set number from the personalized data, along with a
    unique identifier.

    Args:
        personalized_data (PersonalizedData): The personalized data containing the policy and set number.
        unique_identifier (str): A unique identifier for the query state, typically a timestamp.

    Returns:
        str: A string key uniquely identifying a query state for storage in Redis.
    """
    the_key = f"query_state:{personalized_data['member_id']}:{personalized_data['set_number']}"
    if unique_identifier:
        the_key = f"{the_key}:{unique_identifier}"
    return the_key


def convert_langchain_to_json(doc: Document) -> dict[str, Any]:
    """
    Converts a `Document` object to a JSON-serializable dictionary.

    This function is specifically designed for converting documents from the custom `Document`
    format used within the langchain schema to a JSON format for storage or further processing.

    Args:
        doc (Document): The `Document` object to convert.

    Returns:
        dict: A dictionary representation of the `Document`, suitable for JSON serialization.
    """
    doc_json = {}
    doc_json["page_content"] = doc.page_content
    doc_json["metadata"] = doc.metadata
    return doc_json


def convert_dict_to_summaries(doc: dict) -> dict[str, Any]:
    """
    Converts a `Document` object to a JSON-serializable dictionary.

    This function is specifically designed for converting documents from the custom `Document`
    format used within the langchain schema to a JSON format for storage or further processing.

    Args:
        doc (Document): The `Document` object to convert.

    Returns:
        dict: A dictionary representation of the `Document`, suitable for JSON serialization.
    """
    doc_json = {}
    doc_json["summary"] = doc["metadata"]["summary"]
    doc_json["summary_reasoning"] = doc["metadata"]["summary_reasoning"]
    return doc_json


def convert_dict_to_relevancies(doc: dict) -> dict[str, Any]:
    """
    Converts a `Document` object to a JSON-serializable dictionary.

    This function is specifically designed for converting documents from the custom `Document`
    format used within the langchain schema to a JSON format for storage or further processing.

    Args:
        doc (Document): The `Document` object to convert.

    Returns:
        dict: A dictionary representation of the `Document`, suitable for JSON serialization.
    """
    doc_json = {}
    doc_json["relevancy_score"] = doc["metadata"]["relevancy_score"]
    doc_json["relevancy_reasoning"] = doc["metadata"]["relevancy_reasoning"]
    return doc_json


def convert_json_to_langchain(doc: dict[str, Any]) -> Document:
    """
    Converts a JSON-serializable dictionary to a `Document` object.

    This function allows for the reverse operation of `convert_langchain_to_json`, enabling
    the reconstruction of a `Document` object from its JSON dictionary representation.

    Args:
        doc (dict): The dictionary representation of a `Document`.

    Returns:
        Document: The reconstructed `Document` object.
    """
    return Document(page_content=doc["page_content"], metadata=doc["metadata"])


def save_query_state_to_redis(query_state: QueryState, personalized_data: PersonalizedData) -> None:
    """
    Saves a query state to Redis using a generated key.

    This function serializes the `QueryState` object to JSON, including converting any
    `Document` objects within `retrieved_docs` to their JSON representation. It then generates
    a unique key and saves the serialized data to Redis.

    Args:
        query_state (QueryState): The query state to save.
        personalized_data (PersonalizedData): The personalized data used to generate part of the key.

    Side Effects:
        Saves a serialized version of the query state to Redis under a generated key.
    """
    query_state_json = json.dumps(asdict(query_state))

    unique_identifier = datetime.now().strftime("%Y%m%d%H%M%S")

    key = generate_query_state_key(personalized_data, unique_identifier)

    Container.redis_db().set(key, query_state_json)


def get_query_states_from_memorystore(personalized_info: PersonalizedData) -> List[QueryState]:
    """
    Retrieves a list of `QueryState` objects from Redis based on personalized info.

    This function searches Redis for keys matching the policy and set number in the personalized info,
    deserializes the stored JSON data into `QueryState` objects, and returns a list of these objects.

    Args:
        personalized_info (PersonalizedData): The personalized information used to search for matching query states.

    Returns:
        List[QueryState]: A list of `QueryState` objects retrieved from Redis.
    """
    pattern = generate_query_state_key(personalized_info) + ":*"

    keys = Container.redis_db().keys(pattern)
    matching_query_states = []
    for key in keys:
        query_state_json = Container.redis_db().get(key)

        if query_state_json:
            query_state_dict = json.loads(query_state_json)

            query_state_obj = QueryState(**query_state_dict)
            matching_query_states.append(query_state_obj)

    return matching_query_states


def serialize_previous_conversation(query_state: QueryState) -> str:
    """
    Serializes the content of a previous conversation from a query state into a formatted string.

    This function takes the state of a previous query and formats it into a readable string detailing
    the question, the answer, and any additional information that was specified to be retrieved. This can
    be used for logging, debugging, or displaying past interaction context in a user interface.

    Args:
        query_state (QueryState): The query state object containing details of the previous conversation
                                  including the question asked, the answer given, and any additional
                                  information that was required.

    Returns:
        str: A string that summarizes the previous conversation in a structured format.

    Example:
        >>> query_state = QueryState(question="What is the capital of France?", answer="Paris",
                                     additional_information_to_retrieve="Population details")
        >>> serialized_conversation = serialize_previous_conversation(query_state)
        >>> print(serialized_conversation)
        Previous question was: What is the capital of France?
        Previous answer was: Paris
        Previous additional information to retrieve: Population details
    """
    return f"""
    Previous question was: {query_state.question}
    Previous answer was: {query_state.answer} 
    Previous additional information to retrieve: {query_state.additional_information_to_retrieve}"""

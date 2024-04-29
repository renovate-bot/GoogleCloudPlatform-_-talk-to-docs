"""Provides utilities for converting data to Chroma-specific MongoDB filter formats.

This module includes functions designed to facilitate the conversion of standard
Python dictionaries into MongoDB filter formats. It is particularly focused on
creating MongoDB query filters using the "$and" operator from given dictionaries,
enabling dynamic construction of database queries based on variable criteria.

The main utility function, `convert_to_chroma_format`, accepts a dictionary where
each key-value pair represents a specific query condition. It then converts this
into a format suitable for use with MongoDB queries, aiding in the seamless integration
of application-level data structures with database-level querying capabilities.
"""


def convert_to_chroma_format(metadata: dict[str, str]) -> dict[str, dict[str, str]]:
    """
    Converts a dictionary into a MongoDB filter format with "$and" operator.

    Args:
        input_dict (dict): A dictionary where each key-value pair represents a field and its value.

    Returns:
        dict: A MongoDB filter object using the "$and" operator with the given field-value pairs.

    Example:
        >>> dict_to_mongo_filter({"policy_number": "030500 ", "set_number": "040mcbx"})
        {'$and': [{'policy_number': '030500 '}, {'set_number': '040mcbx'}]}
    """
    return {"$and": [{k: v} for k, v in metadata.items()]}

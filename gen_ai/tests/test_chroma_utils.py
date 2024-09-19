"""Unit tests for the convert_to_chroma_format function in the chroma_utils module.

This module contains a series of tests designed to verify the correctness of the
convert_to_chroma_format function from the chroma_utils module. It tests various
scenarios, including simple dictionary inputs, empty dictionaries, dictionaries
with a single key-value pair, and dictionaries with multiple small key-value pairs,
to ensure the function consistently returns the expected MongoDB filter format.
"""
from datetime import datetime

from gen_ai.common.chroma_utils import convert_to_chroma_format, convert_to_vais_format


def test_convert_to_chroma_format_simple():
    """
    Tests the convert_to_chroma_format function with a simple dictionary input.

    This test ensures that the function correctly converts a dictionary containing two key-value pairs
    into the chroma format. The function is expected to return a dictionary with a single `$and` key,
    where its value is a list of dictionaries, each representing one of the input key-value pairs.

    Asserts
    -------
    The function returns the expected chroma format dictionary for a simple input case.
    """
    assert convert_to_chroma_format({"policy_number": "030500 ", "set_number": "040mcbx"}) == {
        "$and": [{"policy_number": "030500 "}, {"set_number": "040mcbx"}]
    }


def test_convert_to_chroma_format_empty():
    """
    Tests the convert_to_chroma_format function with an empty dictionary input.

    This test verifies that the function properly handles an empty input dictionary by returning a
    chroma format dictionary with an empty list associated with the `$and` key.

    Asserts
    -------
    The function returns `{"$and": []}` when given an empty dictionary as input.
    """
    assert convert_to_chroma_format({}) == {"$and": []}


def test_convert_to_chroma_format_another():
    """
    Tests the convert_to_chroma_format function with a single key-value pair input.

    This test checks if the function correctly processes a dictionary containing a single key-value
    pair, converting it into the chroma format where the `$and` key is associated with a list containing
    a single dictionary that represents the input key-value pair.

    Asserts
    -------
    The function returns the expected chroma format dictionary for an input of a dictionary with a
    single key-value pair.
    """
    assert convert_to_chroma_format({"key": "value"}) == {"$and": [{"key": "value"}]}


def test_convert_to_chroma_format_small_characters():
    """
    Tests the convert_to_chroma_format function with a dictionary containing multiple small key-value pairs.

    This test ensures that the function can handle an input dictionary with several small (one character) keys,
    correctly converting it into the chroma format. The expected output is a dictionary with the `$and` key,
    where its value is a list of dictionaries, each representing one of the input key-value pairs.

    Asserts
    -------
    The function returns the expected chroma format dictionary for a dictionary with multiple small key-value pairs.
    """
    assert convert_to_chroma_format({"a": "1", "b": "2", "c": "3"}) == {"$and": [{"a": "1"}, {"b": "2"}, {"c": "3"}]}

def test_convert_to_vais_format_empty_metadata():
    assert convert_to_vais_format({}) == ""

def test_convert_to_vais_format_int_value():
    metadata = {"policy_number": 905531}
    assert convert_to_vais_format(metadata) == "policy_number = 905531"

def test_convert_to_vais_format_float_value():
    metadata = {"policy_number": 3.14}
    assert convert_to_vais_format(metadata) == "policy_number = 3.14"

def test_convert_to_vais_format_datetime_value():
    metadata = {"effective_date": datetime(2024, 9, 19)}
    assert convert_to_vais_format(metadata) == 'effective_date == "2024-09-19"'

def test_convert_to_vais_format_datetime_with_operator():
    metadata = {"effective_date >= ": datetime(2024, 9, 19)}
    assert convert_to_vais_format(metadata) == 'effective_date >= "2024-09-19"'

def test_convert_to_vais_format_string_value():
    metadata = {"section_name": "Policy Data"}
    assert convert_to_vais_format(metadata) == 'section_name: ANY("Policy Data")'

def test_convert_to_vais_format_multiple_values():
    metadata = {
        "policy_number": 123,
        "set_number": 3.14,
        "effective_date": datetime(2024, 9, 19),
        "section_name": "Policy Data"
    }
    expected_filter = "policy_number = 123 AND set_number = 3.14 AND effective_date == \"2024-09-19\" AND section_name: ANY(\"Policy Data\")"
    assert convert_to_vais_format(metadata) == expected_filter

def test_convert_to_vais_format_none_value():
    metadata = {"none_field": None}
    assert convert_to_vais_format(metadata) == ""

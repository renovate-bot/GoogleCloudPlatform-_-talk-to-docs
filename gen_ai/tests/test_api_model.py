import pytest
from pydantic import BaseModel
from gen_ai.deploy.model import transform_to_dictionary


class TestDataModel(BaseModel):
    name: str = ""
    age: int = 0
    active: bool = False


def test_default_values_omitted():
    model = TestDataModel(name="John")
    transformed = transform_to_dictionary(model)
    assert transformed == {"name": "John"}, "Should only contain the non-default name field"


def test_no_default_values():
    model = TestDataModel(name="John", age=30, active=True)
    transformed = transform_to_dictionary(model)
    assert transformed == {"name": "John", "age": 30, "active": True}, "Should contain all fields as none are default"

"""This module provides test to test module document_utils.py"""

from gen_ai.common.document_utils import (
    convert_langchain_to_json,
    convert_json_to_langchain,
    convert_dict_to_summaries,
    convert_dict_to_relevancies,
    build_doc_title,
    generate_contexts_from_docs,
)

from langchain.schema import Document
from gen_ai.deploy.model import QueryState


def test_convert_langchain_to_json():
    doc = Document(page_content="This is a test document.", metadata={"summary": "This is a summary."})
    doc_json = convert_langchain_to_json(doc)
    assert doc_json["page_content"] == "This is a test document."
    assert doc_json["metadata"]["summary"] == "This is a summary."


def test_convert_json_to_langchain():
    doc_json = {"page_content": "This is a test document.", "metadata": {"summary": "This is a summary."}}
    doc = convert_json_to_langchain(doc_json)
    assert doc.page_content == "This is a test document."
    assert doc.metadata["summary"] == "This is a summary."


def test_convert_dict_to_summaries():
    doc = {
        "metadata": {"summary": "This is a summary.", "summary_reasoning": "This is the reasoning behind the summary."}
    }
    doc_json = convert_dict_to_summaries(doc)
    assert doc_json["summary"] == "This is a summary."
    assert doc_json["summary_reasoning"] == "This is the reasoning behind the summary."


def test_convert_dict_to_relevancies():
    doc = {"metadata": {"relevancy_score": 0.9, "relevancy_reasoning": "This is the reasoning behind the relevancy."}}
    doc_json = convert_dict_to_relevancies(doc)
    assert doc_json["relevancy_score"] == 0.9
    assert doc_json["relevancy_reasoning"] == "This is the reasoning behind the relevancy."


def test_build_doc_title():
    metadata = {"set_number": "1", "section_name": "Section 1", "doc_identifier": "Doc 1", "policy_number": "Policy 1"}
    doc_title = build_doc_title(metadata)
    assert doc_title == "1 Section 1 Doc 1 Policy 1 "


def test_generate_contexts_from_docs():
    docs = [
        Document(
            page_content="This is a test document.",
            metadata={
                "section_name": "Section 1",
                "summary": "This is a summary.",
                "relevancy_score": 0.9,
                "set_number": "1",
                "doc_identifier": "Doc 1",
                "policy_number": "Policy 1",
                "original_filepath": "test_file.txt",
            },
        )
    ]
    query_state = QueryState(
        question="What is the purpose of the document?",
        answer="To provide information.",
        additional_information_to_retrieve="",
        all_sections_needed=[],
    )
    contexts = generate_contexts_from_docs(docs, query_state)
    assert (
        contexts[0]
        == "\nDOCUMENT TITLE: 1 Section 1 Doc 1 Policy 1 \nDOCUMENT CONTENT: This is a test document.\n------------\n\n"
    )
    assert query_state.num_docs_used == [1]
    assert query_state.used_articles_with_scores == [("Section 1 Context: 1", 0.9)]

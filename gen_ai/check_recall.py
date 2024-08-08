import click
import json
import pandas as pd
import google.auth
from google.cloud import bigquery
from ast import literal_eval
from common.ioc_container import Container
from collections import defaultdict
import numpy as np
import math
from tqdm import tqdm
from gen_ai.llm import golden_scoring_answer, substring_matching


def get_recall_from_paths(original_paths, expected_kc_docs):
    if len(expected_kc_docs) == 0:
        return 1
    found_docs = set()
    for kc_doc in original_paths:
        if "-" in kc_doc:
            kc_doc = kc_doc.split("-")[1].strip()
        if "." in kc_doc:
            kc_doc = kc_doc.split(".")[0].strip()
        if kc_doc in expected_kc_docs:
            found_docs.add(kc_doc)
    return len(found_docs) / len(expected_kc_docs)


def get_expected_docs(row):
    expected_docs = defaultdict(set)
    if str(row["gt_kmid"]) == "nan":
        expected_docs["kc"] = []
    else:
        print(row["gt_kmid"], type(row["gt_kmid"]))
        if isinstance(row["gt_kmid"], str):
            relevant_docs_kc_all = [row["gt_kmid"].lower()]
        else:
            relevant_docs_kc_all = literal_eval(row["gt_kmid"])
        relevant_docs_kc = [x.lower() for x in relevant_docs_kc_all]  # Using set comprehension to directly create a set
        relevant_docs_kc = [x for x in relevant_docs_kc if x != "km1708500"]  # exclude because Mahesh said
        expected_docs["kc"] = relevant_docs_kc

    expected_docs["b360"].add(row["set_number"].lower())
    expected_docs["b360"] = list(expected_docs["b360"])
    return expected_docs


def get_recall_in_post_filtered(row, expected_docs):
    recalls = {"kc": 0, "b360": 0}
    # print(expected_docs)
    if len(expected_docs["b360"]) == 0:
        recalls["b360"] = 1
    if row["set_number"].lower() in expected_docs["b360"]:
        recalls["b360"] = 1
    original_paths = row["post_filtered_documents_so_far"]
    print(original_paths)
    original_paths = [x[0].lower() for x in original_paths]
    recalls["kc"] = get_recall_from_paths(original_paths, expected_docs["kc"])
    return recalls


def prepare_recall_calculation(session_id, df_gt, ragas=True):
    client = Container.logging_bq_client()

    dataset_name = Container.config["dataset_name"]
    table_name = "prediction"
    table_id = f"{client.project}.{dataset_name}.{table_name}"

    sql = f"""
    SELECT * FROM `{table_id}` where session_id like ('%{session_id}%') and response_type='final'
    """

    df_predictions = client.query(sql).to_dataframe()
    print(len(df_predictions))
    print("HOY")
    df_predictions["question_to_join_on"] = df_predictions["plan_and_summaries"]
    df_gt["question_to_join_on"] = df_gt["question"]
    df_gt.rename(columns={"KMID": "gt_kmid"}, inplace=True)

    # Joining on the question field
    df_joined = df_predictions.merge(df_gt, on="question_to_join_on", how="inner")
    print(len(df_joined))
    print("HOY")
    # Process columns for ragas format if necessary
    if ragas:
        df_joined["post_filtered_documents_so_far_content"] = df_joined["post_filtered_documents_so_far_content"].apply(
            lambda x: convert_to_ragas(x, "page_content")
        )
        df_joined["post_filtered_documents_so_far"] = df_joined["post_filtered_documents_so_far"].apply(
            lambda x: convert_to_ragas(x, "original_filepath")
        )
    recalls_in_post_filtered_360, recalls_in_post_filtered_kc = [], []
    for i, row in df_joined.iterrows():
        expected_docs = get_expected_docs(row)
        recall_in_filtered = get_recall_in_post_filtered(row, expected_docs)
        recalls_in_post_filtered_360.append(recall_in_filtered["b360"])
        recalls_in_post_filtered_kc.append(recall_in_filtered["kc"])

    df_joined["recall_b360"] = recalls_in_post_filtered_360
    df_joined["recall_kc"] = recalls_in_post_filtered_kc

    # Average recall
    average_recall_b360 = df_joined["recall_b360"].mean()
    average_recall_kc = df_joined["recall_kc"].mean()
    print(f"Average Recall B360: {average_recall_b360}")
    print(f"Average Recall KC: {average_recall_kc}")
    return df_joined


def prepare_scoring_calculation(df_joined):
    golden_scores = []
    for i, row in tqdm(df_joined.iterrows(), total=len(df_joined)):
        # print(row)
        expected_answer = row["UPDATED Golden Answer Expected from Knowledge Assist"]
        if str(expected_answer) == "nan":
            expected_answer = row["Golden Answer Expected from Knowledge Assist"]
        actual_answer = row["response"]
        question = row["question_x"]
        score = golden_scoring_answer(question, expected_answer, actual_answer)

        golden_scores.append(score)

    df_joined["golden_score"] = golden_scores
    mean_golden_score = df_joined["golden_score"].mean()
    mean_conf_score = df_joined["confidence_score"].mean()
    print(f"Average Golden Score: {mean_golden_score}")
    print(f"Average Confidence Score: {mean_conf_score}")
    return df_joined


def get_semantic_score(expected_text, retrieved_actual_text):
    if str(expected_text) == "nan":
        return 100

    retrieved_actual_text = "\n".join([x[0] for x in retrieved_actual_text])

    if not expected_text or not retrieved_actual_text:
        return 0.0

    # Calculate the fuzzy similarity score
    score = substring_matching(expected_text, retrieved_actual_text)
    return score


def get_semantic_score_torch(expected_text, retrieved_actual_text):
    from sentence_transformers import SentenceTransformer, util
    from nltk.tokenize import sent_tokenize

    model = SentenceTransformer("all-mpnet-base-v2")  # Powerful semantic model

    """
    Calculates a semantic score based on the proportion of expected_text
    semantically covered in retrieved_actual_text.

    1. Splits expected_text into sentences.
    2. Calculates sentence embeddings for each sentence and retrieved_actual_text.
    3. Computes cosine similarity between each sentence and retrieved_actual_text.
    4. Averages the top similarities (representing covered sentences).
    5. Scales and returns the score (0-100).

    Args:
        expected_text (str): The expected text from KC or B360.
        retrieved_actual_text (str): The actual retrieved text.

    Returns:
        float: Semantic score (0-100) indicating coverage of expected_text in retrieved_actual_text.
    """
    if str(expected_text) == "nan":
        return 100
    # print('Expected text:', expected_text)
    # print('Retrieved actual text:', retrieved_actual_text)
    # print('Type actual text:', retrieved_actual_text)
    retrieved_actual_text = "\n".join([x[0] for x in retrieved_actual_text])

    expected_sentences = sent_tokenize(expected_text)

    embeddings_expected = model.encode(expected_sentences, convert_to_tensor=True)
    embedding_retrieved = model.encode(retrieved_actual_text, convert_to_tensor=True)

    similarities = util.cos_sim(embeddings_expected, embedding_retrieved)

    max_similarities = similarities.max(axis=1).values  # Extract the values directly

    if len(max_similarities) == 0:
        return 0.0
    semantic_score = (max_similarities.sum() / len(max_similarities)) * 100

    return semantic_score.item()


def prepare_semantic_score_calculation(df_joined):
    b360_scores, kc_scores = [], []
    for i, row in tqdm(df_joined.iterrows(), total=len(df_joined)):
        # print(row)
        expected_kc_text = row["Response from KC"]
        expected_b360_text = row["Response from B360"]
        retrieved_actual_text = row["post_filtered_documents_so_far_content"]
        kc_semantic_score = get_semantic_score(expected_kc_text, retrieved_actual_text)
        b360_semantic_score = get_semantic_score(expected_b360_text, retrieved_actual_text)
        b360_scores.append(b360_semantic_score)
        kc_scores.append(kc_semantic_score)

    df_joined["b360_semantic_scores"] = b360_scores
    df_joined["kc_semantic_scores"] = kc_scores
    mean_b360_score = df_joined["b360_semantic_scores"].mean()
    mean_kc_score = df_joined["kc_semantic_scores"].mean()
    print(f"Average B360 Semantic Score: {mean_b360_score}")
    print(f"Average KC Semantic Score: {mean_kc_score}")
    return df_joined


@click.command()
@click.option("--session_id", required=True, help="Session ID for the SQL database query.")
@click.option("--output_file", required=True, type=click.Path(), help="Path to the output CSV file.")
@click.option("--input_csv", required=True, type=click.Path(), help="Path to the input CSV file with ground truth.")
@click.option("--ragas", is_flag=True, help="Convert to ragas format if set to True.")
def query_and_process(session_id, output_file, input_csv, ragas):
    df_gt = pd.read_csv(input_csv)
    df_joined = prepare_recall_calculation(session_id, df_gt, ragas)
    df_joined = prepare_scoring_calculation(df_joined)
    df_joined = prepare_semantic_score_calculation(df_joined)
    df_joined.to_csv(output_file, index=None)


def convert_to_ragas(x, column_name):
    actual_list = []
    x_str = literal_eval(x)
    for page_content in x_str:
        content = page_content[column_name]
        content = content.replace("\n", "")
        actual_list.append([content])
    return actual_list


if __name__ == "__main__":
    query_and_process()

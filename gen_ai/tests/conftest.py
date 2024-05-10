import os
import pytest
from gen_ai import constants


@pytest.fixture(autouse=True, scope="session")
def override_processed_files_dir():
    original_dir = constants.PROCESSED_FILES_DIR
    constants.PROCESSED_FILES_DIR = f'{os.getenv("HOME")}/resources/uhg/main_folder'
    yield
    constants.PROCESSED_FILES_DIR = original_dir
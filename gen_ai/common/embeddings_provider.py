"""This module implements Embedding Provider, in case if user wants to specify 
Vertex AI Embeddings or OpenAIEmbeddings"""

from langchain.schema.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_google_vertexai import VertexAIEmbeddings


class EmbeddingsProvider:
    """Provides embeddings based on the specified embeddings service.

    This class serves as a factory for creating instances of embedding classes based on the specified service. 
    It currently supports creating embeddings from either 'openai' or 'vertexai'.

    Attributes:
        embeddings_name (str): The name of the embeddings service. It determines which embeddings class to instantiate.
        embeddings_model_name (str, optional): The specific model name for the embeddings service if applicable. 
        Default is None.

    Raises:
        ValueError: If the specified embeddings service is not supported.

    Returns:
        Embeddings: An instance of a class that provides embeddings functionalities based on the specified service.
    """
    def __init__(self, embeddings_name, embeddings_model_name: str = None):
        self.embeddings_name = embeddings_name
        self.embeddings_model_name = embeddings_model_name

    def __call__(self) -> Embeddings:
        """Returns the Embeddings class

        Raises:
            ValueError: currently supports openai and vertexai embeddings. Raises exception if other types are 
            specified

        Returns:
            Embeddings: langchain class of base embeddings
        """
        print(f"Loading {self.embeddings_name} Embeddings...")
        if "vertexai" in self.embeddings_name:
            return VertexAIEmbeddings(model_name=self.embeddings_model_name)
        elif "openai" in self.embeddings_name:
            return OpenAIEmbeddings()
        else:
            raise ValueError("Not supported embeddings name in config")

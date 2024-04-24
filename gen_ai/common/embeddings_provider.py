from langchain.schema.embeddings import Embeddings
from langchain.embeddings import VertexAIEmbeddings, OpenAIEmbeddings

class EmbeddingsProvider():
    def __init__(self, embeddings_name, embeddings_model_name: str = None):
        self.embeddings_name = embeddings_name
        self.embeddings_model_name = embeddings_model_name


    def __call__(self) -> Embeddings:
        """Returns the Embeddings class

        Raises:
            ValueError: currently supports openai and vertexai embeddings. Raises exception if other types are specified

        Returns:
            Embeddings: langchain class of base embeddings
        """
        print(f'Loading {self.embeddings_name} Embeddings...')
        if "vertexai" in self.embeddings_name:
            return VertexAIEmbeddings(model_name=self.embeddings_model_name)
        elif 'openai' in self.embeddings_name:
            return OpenAIEmbeddings()
        else:
            raise ValueError(f'Not supported embeddings name in config')

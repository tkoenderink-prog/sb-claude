"""
E5-multilingual embeddings module.

Handles model loading and text embedding generation with proper E5 formatting.
"""

from typing import List
import numpy as np
import logging


class EmbeddingModel:
    """
    Wrapper for sentence-transformers E5-multilingual model.

    Handles model loading, caching, and embedding generation with
    proper E5 formatting (query: vs passage: prefixes).
    """

    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-base",
        device: str = "mps",
        normalize: bool = True
    ):
        """
        Initialize embedding model.

        Args:
            model_name: HuggingFace model identifier
            device: "mps" for M1/M2 GPU, "cpu" for CPU
            normalize: Whether to L2-normalize embeddings
        """
        self.model_name = model_name
        self.device = device
        self.normalize = normalize
        self.logger = logging.getLogger(__name__)

        # Lazy loading - model loaded on first use
        self._model = None

    @property
    def model(self):
        """Lazy load model on first access."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self.logger.info(f"Loading model: {self.model_name}")
            try:
                self._model = SentenceTransformer(self.model_name, device=self.device)
                self.logger.info(f"Model loaded on device: {self.device}")
            except Exception as e:
                # Fallback to CPU if MPS fails
                self.logger.warning(f"Failed to load on {self.device}, falling back to CPU: {e}")
                self._model = SentenceTransformer(self.model_name, device="cpu")
                self.device = "cpu"
        return self._model

    def embed_passages(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Embed passages (documents/chunks) for indexing.

        E5 models expect "passage: <text>" formatting for documents.

        Args:
            texts: List of text strings to embed
            batch_size: Number of texts per batch

        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([])

        # Format with E5 passage prefix
        formatted_texts = [f"passage: {text}" for text in texts]

        # Generate embeddings
        embeddings = self.model.encode(
            formatted_texts,
            batch_size=batch_size,
            normalize_embeddings=self.normalize,
            show_progress_bar=len(texts) > 100,
            convert_to_numpy=True
        )

        return embeddings

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a search query.

        E5 models expect "query: <text>" formatting for queries.

        Args:
            query: Search query string

        Returns:
            numpy array of shape (embedding_dim,)
        """
        # Format with E5 query prefix
        formatted_query = f"query: {query}"

        # Generate embedding
        embedding = self.model.encode(
            [formatted_query],
            normalize_embeddings=self.normalize,
            show_progress_bar=False,
            convert_to_numpy=True
        )[0]

        return embedding

    def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        return self.model.get_sentence_embedding_dimension()

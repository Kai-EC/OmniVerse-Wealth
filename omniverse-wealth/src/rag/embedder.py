"""Embedding Pipeline for RAG Vector Store.

Converts processed and PII-masked trading records into vector embeddings
suitable for semantic search via Amazon Bedrock or OpenSearch.

Supports two modes:
1. Bedrock Titan Embeddings (cloud, production)
2. Local sentence-transformers (development/offline)
"""

from typing import Any

import boto3

from src.config import settings
from src.rag.csv_processor import CSVProcessor
from src.rag.pii_masker import PIIMasker


class BedrockEmbedder:
    """Generate embeddings using Amazon Bedrock Titan Embeddings model."""

    def __init__(
        self,
        model_id: str = "amazon.titan-embed-text-v2:0",
        region: str | None = None,
        dimensions: int = 1024,
    ):
        self.model_id = model_id
        self.region = region or settings.aws_region
        self.dimensions = dimensions
        self._client = boto3.client(
            "bedrock-runtime", region_name=self.region
        )

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: Input text to embed.

        Returns:
            Vector embedding as list of floats.
        """
        import json

        body = json.dumps({
            "inputText": text,
            "dimensions": self.dimensions,
            "normalize": True,
        })

        response = self._client.invoke_model(
            modelId=self.model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )

        result = json.loads(response["body"].read())
        return result["embedding"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts.

        Note: Bedrock Titan doesn't support native batch embedding,
        so this processes sequentially. For production, consider
        using async or parallel processing.

        Args:
            texts: List of input texts.

        Returns:
            List of vector embeddings.
        """
        return [self.embed_text(text) for text in texts]


class EmbeddingPipeline:
    """End-to-end pipeline: CSV → Clean → Mask → Chunk → Embed.

    Orchestrates the full flow from raw CSV data to embedded vectors
    ready for storage in a vector database.
    """

    def __init__(
        self,
        csv_path: str,
        chunk_size: int = 5,
        use_pii_masking: bool = True,
    ):
        self.csv_processor = CSVProcessor(csv_path)
        self.pii_masker = PIIMasker() if use_pii_masking else None
        self.embedder = BedrockEmbedder()
        self.chunk_size = chunk_size

    def process(self) -> list[dict[str, Any]]:
        """Run the full pipeline.

        Returns:
            List of dicts with 'text', 'embedding', and 'metadata' keys.
        """
        # Step 1: Load CSV
        self.csv_processor.load()
        records = self.csv_processor.records

        # Step 2: Generate chunks (with or without PII masking)
        chunks = self._generate_chunks(records)

        # Step 3: Embed each chunk
        results = []
        for chunk_text, metadata in chunks:
            embedding = self.embedder.embed_text(chunk_text)
            results.append({
                "text": chunk_text,
                "embedding": embedding,
                "metadata": metadata,
            })

        return results

    def generate_documents(self) -> list[dict[str, Any]]:
        """Generate documents for Bedrock Knowledge Base ingestion.

        Returns documents in the format expected by Bedrock KB,
        without computing embeddings (Bedrock KB handles that).

        Returns:
            List of dicts with 'content' and 'metadata' keys.
        """
        self.csv_processor.load()
        records = self.csv_processor.records

        documents = []

        # Document 1: Portfolio summary
        if self.pii_masker:
            summary_text = self.pii_masker.mask_for_embedding(records)
        else:
            summary_text = self.csv_processor.summary_text()

        documents.append({
            "content": summary_text,
            "metadata": {
                "type": "portfolio_summary",
                "record_count": len(records),
                "currencies": self.csv_processor.currencies,
            },
        })

        # Document 2+: Chunked trading history
        chunks = self._generate_chunks(records)
        for chunk_text, metadata in chunks:
            documents.append({
                "content": chunk_text,
                "metadata": metadata,
            })

        return documents

    def _generate_chunks(
        self, records: list
    ) -> list[tuple[str, dict[str, Any]]]:
        """Generate text chunks with metadata.

        Args:
            records: List of TradeRecord objects.

        Returns:
            List of (text, metadata) tuples.
        """
        chunks = []

        for i in range(0, len(records), self.chunk_size):
            batch = records[i : i + self.chunk_size]

            if self.pii_masker:
                text = self.pii_masker.mask_for_embedding(batch)
            else:
                # Use raw text from csv_processor
                text_parts = []
                for r in batch:
                    dt = r.datetime_utc.strftime("%Y-%m-%d %H:%M")
                    text_parts.append(
                        f"{dt} | {r.action} {abs(r.change)} {r.currency.upper()} "
                        f"@ {r.price} TWD | balance: {r.balance}"
                    )
                text = "\n".join(text_parts)

            metadata = {
                "type": "trading_history_chunk",
                "chunk_index": i // self.chunk_size,
                "start_ts": batch[0].timestamp,
                "end_ts": batch[-1].timestamp,
                "currencies": list(set(r.currency for r in batch)),
                "actions": list(set(r.action for r in batch)),
            }

            chunks.append((text, metadata))

        return chunks

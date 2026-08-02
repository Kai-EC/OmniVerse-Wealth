"""Amazon Bedrock Knowledge Bases Integration.

Provides retrieval interface for the personal trading history
RAG knowledge base powered by Bedrock KB + OpenSearch Serverless.

Architecture:
    CSV → EmbeddingPipeline → S3 → Bedrock KB (auto-sync) → OpenSearch
    Query → Bedrock KB Retrieve API → Ranked passages → Agent context
"""

import boto3

from src.config import settings


class BedrockKnowledgeBase:
    """Interface to Amazon Bedrock Knowledge Bases for RAG retrieval.

    This class handles:
    - Querying the knowledge base for relevant trading history
    - Formatting retrieved passages for agent consumption
    - Managing data source sync operations
    """

    def __init__(
        self,
        knowledge_base_id: str | None = None,
        region: str | None = None,
    ):
        self.knowledge_base_id = knowledge_base_id or settings.bedrock_kb_id
        self.region = region or settings.aws_region
        self._client = boto3.client(
            "bedrock-agent-runtime", region_name=self.region
        )
        self._agent_client = boto3.client(
            "bedrock-agent", region_name=self.region
        )

    async def retrieve(
        self,
        query: str,
        max_results: int = 5,
        min_score: float = 0.3,
    ) -> list[dict]:
        """Retrieve relevant passages from the knowledge base.

        Args:
            query: Natural language query to search.
            max_results: Maximum number of results to return.
            min_score: Minimum relevance score threshold.

        Returns:
            List of dicts with 'text', 'score', and 'metadata' keys.
        """
        if not self.knowledge_base_id:
            return [{"text": "Knowledge Base ID not configured.", "score": 0.0}]

        try:
            response = self._client.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": max_results,
                    }
                },
            )

            results = []
            for item in response.get("retrievalResults", []):
                score = item.get("score", 0.0)
                if score >= min_score:
                    results.append({
                        "text": item.get("content", {}).get("text", ""),
                        "score": score,
                        "metadata": item.get("metadata", {}),
                        "location": item.get("location", {}),
                    })

            return results

        except Exception as e:
            return [{"text": f"KB retrieval error: {str(e)}", "score": 0.0}]

    async def retrieve_and_generate(
        self,
        query: str,
        model_id: str | None = None,
    ) -> dict:
        """Retrieve passages and generate a response using Bedrock.

        This uses the RetrieveAndGenerate API which combines
        retrieval with LLM generation in a single call.

        Args:
            query: User's question.
            model_id: Override model for generation.

        Returns:
            Dict with 'response', 'citations', and 'sources'.
        """
        if not self.knowledge_base_id:
            return {"response": "Knowledge Base not configured.", "citations": []}

        model = model_id or settings.bedrock_model_id

        try:
            response = self._client.retrieve_and_generate(
                input={"text": query},
                retrieveAndGenerateConfiguration={
                    "type": "KNOWLEDGE_BASE",
                    "knowledgeBaseConfiguration": {
                        "knowledgeBaseId": self.knowledge_base_id,
                        "modelArn": f"arn:aws:bedrock:{self.region}::foundation-model/{model}",
                    },
                },
            )

            output = response.get("output", {})
            citations = response.get("citations", [])

            return {
                "response": output.get("text", ""),
                "citations": [
                    {
                        "text": c.get("generatedResponsePart", {})
                        .get("textResponsePart", {})
                        .get("text", ""),
                        "references": [
                            ref.get("content", {}).get("text", "")
                            for ref in c.get("retrievedReferences", [])
                        ],
                    }
                    for c in citations
                ],
            }

        except Exception as e:
            return {"response": f"Error: {str(e)}", "citations": []}

    def sync_data_source(self, data_source_id: str) -> dict:
        """Trigger a sync of the knowledge base data source.

        Call this after uploading new CSV data to S3.

        Args:
            data_source_id: The data source ID to sync.

        Returns:
            Sync job status.
        """
        try:
            response = self._agent_client.start_ingestion_job(
                knowledgeBaseId=self.knowledge_base_id,
                dataSourceId=data_source_id,
            )
            return {
                "status": "started",
                "job_id": response.get("ingestionJob", {}).get(
                    "ingestionJobId", ""
                ),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def format_context_for_agent(self, results: list[dict]) -> str:
        """Format retrieved results into agent-friendly context text.

        Args:
            results: Retrieved passages from the KB.

        Returns:
            Formatted text ready for injection into agent prompt.
        """
        if not results:
            return "（無相關歷史交易紀錄）"

        lines = ["=== 個人交易歷史相關資訊 ==="]
        for i, result in enumerate(results, 1):
            score = result.get("score", 0)
            text = result.get("text", "")
            lines.append(f"\n[來源 {i}] (相關度: {score:.2f})")
            lines.append(text)

        return "\n".join(lines)

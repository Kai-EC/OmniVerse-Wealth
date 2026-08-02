"""Global configuration for OmniVerse Wealth."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AWS Bedrock
    aws_region: str = "us-east-1"
    bedrock_api_key: str = ""
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # MAX Exchange API
    max_api_key: str = ""
    max_api_secret: str = ""
    max_api_base_url: str = "https://max-api.maicoin.com"
    max_enable_trading: bool = False

    # Third-party APIs
    coinmarketcap_api_key: str = ""
    blockchain_com_api_key: str = ""

    # RAG
    opensearch_endpoint: str = ""
    csv_data_path: str = "../MaiCoin_最近一年份出入金及交易紀錄.csv"
    bedrock_kb_id: str = ""
    bedrock_kb_data_source_id: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

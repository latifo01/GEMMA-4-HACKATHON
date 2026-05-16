from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "ImciFlow"
    app_version: str = "0.1.0"
    app_env: str = "development"
    backend_port: int = 8000
    frontend_origin: str = Field(default="http://localhost:5173", validation_alias="FRONTEND_ORIGIN")

    google_ai_api_key: str | None = Field(default=None, validation_alias="GOOGLE_AI_API_KEY")
    gemma_online_model: str = Field(
        default="models/gemma-4-26b-a4b-it",
        validation_alias="GEMMA_ONLINE_MODEL",
    )

    ollama_base_url: str = Field(default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL")
    gemma_offline_model: str = Field(default="gemma4:e4b-it", validation_alias="GEMMA_OFFLINE_MODEL")
    ollama_health_timeout_seconds: float = Field(default=1.0, validation_alias="OLLAMA_HEALTH_TIMEOUT_SECONDS")
    ollama_generation_timeout_seconds: float = Field(
        default=180.0,
        validation_alias="OLLAMA_GENERATION_TIMEOUT_SECONDS",
    )

    chroma_path: Path = Field(default=Path("./data/chroma"), validation_alias="CHROMA_PATH")
    rag_visual_assets_path: Path = Field(default=Path("./data/page_images"), validation_alias="RAG_VISUAL_ASSETS_PATH")
    rag_text_embedding_provider: str = Field(default="fastembed", validation_alias="RAG_TEXT_EMBEDDING_PROVIDER")
    rag_text_embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        validation_alias="RAG_TEXT_EMBEDDING_MODEL",
    )
    rag_image_embedding_provider: str = Field(default="fastembed-clip", validation_alias="RAG_IMAGE_EMBEDDING_PROVIDER")
    rag_image_embedding_model: str = Field(
        default="Qdrant/clip-ViT-B-32-vision",
        validation_alias="RAG_IMAGE_EMBEDDING_MODEL",
    )
    rag_image_text_embedding_model: str = Field(
        default="Qdrant/clip-ViT-B-32-text",
        validation_alias="RAG_IMAGE_TEXT_EMBEDDING_MODEL",
    )
    db_path: Path = Field(default=Path("./data/imciflow.db"), validation_alias="DB_PATH")
    whisper_model_name: str = Field(default="small", validation_alias="WHISPER_MODEL_NAME")
    whisper_device: str = Field(default="cpu", validation_alias="WHISPER_DEVICE")
    whisper_compute_type: str = Field(default="int8", validation_alias="WHISPER_COMPUTE_TYPE")
    audio_temp_dir: Path = Field(default=Path("./data/audio_tmp"), validation_alias="AUDIO_TEMP_DIR")
    audio_max_file_size_bytes: int = Field(
        default=25 * 1024 * 1024,
        validation_alias="AUDIO_MAX_FILE_SIZE_BYTES",
    )
    video_temp_dir: Path = Field(default=Path("./data/video_tmp"), validation_alias="VIDEO_TEMP_DIR")
    video_max_file_size_bytes: int = Field(
        default=80 * 1024 * 1024,
        validation_alias="VIDEO_MAX_FILE_SIZE_BYTES",
    )
    video_max_duration_seconds: float = Field(default=120.0, validation_alias="VIDEO_MAX_DURATION_SECONDS")

    @field_validator("google_ai_api_key")
    @classmethod
    def normalize_optional_secret(cls, value: str | None) -> str | None:
        if value is None:
            return None

        stripped = value.strip()
        if not stripped or stripped == "your_google_ai_key_here":
            return None
        return stripped


@lru_cache
def get_settings() -> Settings:
    return Settings()

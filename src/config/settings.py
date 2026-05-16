"""Centralized configuration management."""
import os
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


def _env_flag_enabled(name: str, default: bool = True) -> bool:
    """Parse boolean environment variable."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    api_key: str
    model_name: str
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class EmbeddingConfig:
    """Embedding model configuration."""
    model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    normalize_embeddings: bool = True


@dataclass
class VectorStoreConfig:
    """Vector database configuration."""
    type: str = "chroma"
    chroma_dir: str = "./chroma_db_multilingual"
    qdrant_url: Optional[str] = None
    qdrant_collection: str = "aaoifi"
    qdrant_vector_size: int = 768
    qdrant_timeout_seconds: int = 10
    require_arabic_support: bool = True


@dataclass
class RetrievalConfig:
    """RAG retrieval configuration."""
    top_k: int = 5
    similarity_threshold: float = 0.3
    rerank_multiplier: int = 3  # Retrieve k * multiplier for reranking
    enable_query_expansion: bool = True
    enable_domain_reranking: bool = True


@dataclass
class CacheConfig:
    """Caching configuration."""
    store_type: str = "memory"
    redis_url: Optional[str] = None
    redis_timeout_seconds: int = 2
    response_cache_ttl_seconds: int = 86400
    query_result_cache_ttl_seconds: int = 3600
    enable_response_cache: bool = True
    enable_query_result_cache: bool = True


@dataclass
class SessionConfig:
    """Session management configuration."""
    store_type: str = "memory"
    redis_url: Optional[str] = None
    expiry_minutes: int = 30
    secret_key: str = "change-me-in-production"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    store_type: str = "memory"
    redis_url: Optional[str] = None
    requests_per_window: int = 100
    window_seconds: int = 3600
    free_tier_limit: int = 10
    standard_tier_limit: int = 100
    premium_tier_limit: int = 1000


@dataclass
class SecurityConfig:
    """Security configuration."""
    cors_origins: List[str] = field(default_factory=list)
    allow_credentials: bool = False
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    encryption_master_key: Optional[str] = None
    require_disclaimer_ack: bool = False
    enable_prompt_injection_filter: bool = True
    max_query_length: int = 2000


@dataclass
class APIConfig:
    """API server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    log_dir: str = "./logs"
    enable_metrics: bool = True
    enable_audit: bool = True


@dataclass
class AppConfig:
    """Application-wide configuration."""
    environment: str = "dev"
    llm: LLMConfig
    embedding: EmbeddingConfig
    vector_store: VectorStoreConfig
    retrieval: RetrievalConfig
    cache: CacheConfig
    session: SessionConfig
    rate_limit: RateLimitConfig
    security: SecurityConfig
    api: APIConfig

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables."""
        # LLM Config
        llm = LLMConfig(
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            model_name=os.getenv("OPENROUTER_MODEL", "openrouter/free"),
            timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "3")),
            retry_delay_seconds=float(os.getenv("LLM_RETRY_DELAY_SECONDS", "1.0")),
        )

        # Embedding Config
        embedding = EmbeddingConfig(
            model_name=os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"),
            normalize_embeddings=_env_flag_enabled("NORMALIZE_EMBEDDINGS", True),
        )

        # Vector Store Config
        vector_store = VectorStoreConfig(
            type=os.getenv("VECTOR_DB_TYPE", "chroma").lower(),
            chroma_dir=os.getenv("CHROMA_DIR", "./chroma_db_multilingual"),
            qdrant_url=os.getenv("QDRANT_URL"),
            qdrant_collection=os.getenv("QDRANT_COLLECTION", "aaoifi"),
            qdrant_vector_size=int(os.getenv("QDRANT_VECTOR_SIZE", "768")),
            qdrant_timeout_seconds=int(os.getenv("QDRANT_TIMEOUT_SECONDS", "10")),
            require_arabic_support=_env_flag_enabled("REQUIRE_ARABIC_RETRIEVAL", True),
        )

        # Retrieval Config
        retrieval = RetrievalConfig(
            top_k=int(os.getenv("RETRIEVAL_TOP_K", "5")),
            similarity_threshold=float(os.getenv("RETRIEVAL_THRESHOLD", "0.3")),
            rerank_multiplier=int(os.getenv("RERANK_MULTIPLIER", "3")),
            enable_query_expansion=_env_flag_enabled("ENABLE_QUERY_EXPANSION", True),
            enable_domain_reranking=_env_flag_enabled("ENABLE_DOMAIN_RERANKING", True),
        )

        # Cache Config
        cache = CacheConfig(
            store_type=os.getenv("CACHE_STORE_TYPE", "memory").lower(),
            redis_url=os.getenv("REDIS_URL"),
            redis_timeout_seconds=int(os.getenv("REDIS_TIMEOUT_SECONDS", "2")),
            response_cache_ttl_seconds=int(os.getenv("RESPONSE_CACHE_TTL_SECONDS", "86400")),
            query_result_cache_ttl_seconds=int(os.getenv("QUERY_RESULT_CACHE_TTL_SECONDS", "3600")),
            enable_response_cache=not _env_flag_enabled("RAG_EVAL_MODE", False),
            enable_query_result_cache=not _env_flag_enabled("RAG_EVAL_MODE", False),
        )

        # Session Config
        session = SessionConfig(
            store_type=os.getenv("SESSION_STORE_TYPE", "memory").lower(),
            redis_url=os.getenv("REDIS_URL"),
            expiry_minutes=int(os.getenv("SESSION_EXPIRY_MINUTES", "30")),
            secret_key=os.getenv("SESSION_SECRET_KEY", "change-me-in-production"),
        )

        # Rate Limit Config
        rate_limit = RateLimitConfig(
            store_type=os.getenv("RATE_LIMIT_STORE_TYPE", "memory").lower(),
            redis_url=os.getenv("REDIS_URL"),
            requests_per_window=int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
            window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "3600")),
            free_tier_limit=int(os.getenv("RATE_LIMIT_FREE", "10")),
            standard_tier_limit=int(os.getenv("RATE_LIMIT_STANDARD", "100")),
            premium_tier_limit=int(os.getenv("RATE_LIMIT_PREMIUM", "1000")),
        )

        # Security Config
        cors_origins_raw = os.getenv("CORS_ORIGINS", "")
        cors_origins = []
        if cors_origins_raw:
            import json
            try:
                parsed = json.loads(cors_origins_raw)
                if isinstance(parsed, list):
                    cors_origins = parsed
                elif isinstance(parsed, str):
                    cors_origins = [parsed]
            except json.JSONDecodeError:
                cors_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]

        security = SecurityConfig(
            cors_origins=cors_origins,
            allow_credentials=bool(cors_origins and "*" not in cors_origins),
            jwt_secret_key=os.getenv("JWT_SECRET_KEY"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_expiry_hours=int(os.getenv("JWT_EXPIRY_HOURS", "24")),
            encryption_master_key=os.getenv("ENCRYPTION_MASTER_KEY"),
            require_disclaimer_ack=_env_flag_enabled("REQUIRE_DISCLAIMER_ACK", False),
            enable_prompt_injection_filter=_env_flag_enabled("ENABLE_PROMPT_INJECTION_FILTER", True),
            max_query_length=int(os.getenv("MAX_QUERY_LENGTH", "2000")),
        )

        # API Config
        api = APIConfig(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_dir=os.getenv("LOG_DIR", "./logs"),
            enable_metrics=_env_flag_enabled("ENABLE_METRICS", True),
            enable_audit=_env_flag_enabled("ENABLE_AUDIT", True),
        )

        return cls(
            environment=os.getenv("APP_ENV", "dev").strip().lower() or "dev",
            llm=llm,
            embedding=embedding,
            vector_store=vector_store,
            retrieval=retrieval,
            cache=cache,
            session=session,
            rate_limit=rate_limit,
            security=security,
            api=api,
        )

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # LLM validation
        if not self.llm.api_key:
            errors.append("OPENROUTER_API_KEY is required")

        # Security validation
        if self.environment == "production":
            if "*" in self.security.cors_origins:
                errors.append("CORS wildcard (*) is not allowed in production")
            if not self.security.cors_origins:
                errors.append("CORS_ORIGINS must be explicitly set in production")
            if self.session.secret_key == "change-me-in-production":
                errors.append("SESSION_SECRET_KEY must be changed in production")
            if not self.security.jwt_secret_key:
                errors.append("JWT_SECRET_KEY is required in production")

        # Validate CORS origins are valid URLs
        for origin in self.security.cors_origins:
            if not origin.startswith(("http://", "https://")):
                errors.append(f"Invalid CORS origin: {origin} (must start with http:// or https://)")

        return errors

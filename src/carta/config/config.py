"""Configuration management with environment variable support."""

import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    """Centralized configuration management."""
    
    @property
    def openai_api_key(self) -> Optional[str]:
        """Retrieve OpenAI API key from environment."""
        return os.environ.get("OPENAI_API_KEY")
    
    @property
    def default_embedding_model(self) -> str:
        """Default embedding model name."""
        return os.environ.get("CARTA_EMBEDDING_MODEL", "text-embedding-3-large")
    
    @property
    def default_output_dir(self) -> Path:
        """Base output directory path."""
        return Path(os.environ.get("CARTA_OUTPUT_DIR", "output"))
    
    @property
    def log_level(self) -> str:
        """Application logging level."""
        return os.environ.get("CARTA_LOG_LEVEL", "INFO")
    
    @property
    def database_url(self) -> Optional[str]:
        """Database connection URL."""
        return os.environ.get("DATABASE_URL")
    
    @property
    def database_host(self) -> str:
        """Database hostname."""
        if self.database_url:
            return urlparse(self.database_url).hostname or "localhost"
        return os.environ.get("DB_HOST", "localhost")
    
    @property
    def database_port(self) -> int:
        """Database connection port."""
        if self.database_url:
            return urlparse(self.database_url).port or 5432
        return int(os.environ.get("DB_PORT", "5432"))
    
    @property
    def database_name(self) -> str:
        """Database name."""
        if self.database_url:
            parsed = urlparse(self.database_url)
            return parsed.path.lstrip('/') if parsed.path else "carta"
        return os.environ.get("DB_NAME", "carta")
    
    @property
    def database_user(self) -> str:
        """Database username."""
        if self.database_url:
            return urlparse(self.database_url).username or "carta_service"
        return os.environ.get("DB_USER", "carta_service")
    
    @property
    def database_password(self) -> Optional[str]:
        """Database password."""
        if self.database_url:
            return urlparse(self.database_url).password
        return os.environ.get("DB_PASSWORD")
    
    def validate(self) -> bool:
        """Check required configuration exists."""
        return bool(self.openai_api_key)
    
    def validate_database(self) -> bool:
        """Check database configuration exists."""
        return bool(self.database_password or self.database_url)
    
    def get_missing_config(self) -> list[str]:
        """List missing required configuration keys."""
        return ["OPENAI_API_KEY"] if not self.openai_api_key else []
    
    def get_missing_database_config(self) -> list[str]:
        """List missing database configuration keys."""
        return ["DATABASE_URL or DB_PASSWORD"] if not (self.database_password or self.database_url) else []
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM
    openai_api_key: str
    # Database
    supabase_db_url: str
    
    # Email
    resend_api_key: str = ""
    sales_email: str = "sales@yourcargo.com"
    
    # CORS
    allowed_origin: str = "http://localhost:5173"
    
    # Optional integrations
    n8n_webhook_url: str | None = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore", 
    )


settings = Settings()
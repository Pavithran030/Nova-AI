from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite:///./nova.db"
    project_name: str = "Nova API"
    
    class Config:
        env_file = ".env"

settings = Settings()

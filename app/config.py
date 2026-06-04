from pydantic_settings import BaseSettings  # <-- changed import

class Settings(BaseSettings):
    app_name: str = "CHM-X Backend"
    database_url: str = "sqlite:///./chm_x.db"

    class Config:
        env_file = ".env"

settings = Settings()


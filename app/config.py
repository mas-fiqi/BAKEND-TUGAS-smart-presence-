from dotenv import load_dotenv
import os
from pathlib import Path

# muat .env dari root project (jika file .env di root)
project_root = Path(__file__).resolve().parents[1]
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # fallback: load default .env di working dir
    load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv('DATABASE_URL')
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'replace-this-secret')
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '60'))

settings = Settings()

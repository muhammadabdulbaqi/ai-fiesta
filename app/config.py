import os
from typing import List
from pathlib import Path


def _load_dotenv(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        # remove surrounding quotes
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        # only set if not present in env already
        if key not in os.environ:
            os.environ[key] = val


def _parse_list(value: str) -> List[str]:
    value = value.strip()
    if not value:
        return []
    # simple formats: comma separated or python list like ["*", "http://...]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        # split by comma and strip quotes/spaces
        items = []
        for part in inner.split(","):
            p = part.strip()
            if (p.startswith('"') and p.endswith('"')) or (p.startswith("'") and p.endswith("'")):
                p = p[1:-1]
            if p:
                items.append(p)
        return items
    # else comma separated
    return [p.strip() for p in value.split(",") if p.strip()]


_load_dotenv()


class Settings:
    def __init__(self):
        self.app_name: str = os.getenv("APP_NAME", "LLM Streaming Backend API")
        self.version: str = os.getenv("VERSION", "0.1.0")
        self.docs_url: str = os.getenv("DOCS_URL", "/docs")
        self.redoc_url: str = os.getenv("REDOC_URL", "/redoc")
        self.cors_allow_origins: List[str] = _parse_list(os.getenv("CORS_ALLOW_ORIGINS", "[\"*\"]"))

        # Demo user defaults (for development)
        self.demo_user_email: str = os.getenv("DEMO_USER_EMAIL", "demo@example.com")
        self.demo_user_username: str = os.getenv("DEMO_USER_USERNAME", "demo_user")
        self.demo_user_password: str = os.getenv("DEMO_USER_PASSWORD", "demo123")


settings = Settings()

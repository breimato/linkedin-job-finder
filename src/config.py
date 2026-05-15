import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, model_validator

load_dotenv()


class SearchConfig(BaseModel):
    keywords: list[str] = ["software engineer"]
    location: str = "Spain"
    distance_miles: int = 50
    is_remote: bool = False
    job_type: str = "fulltime"
    results_wanted: int = 25
    hours_old: int = 48
    salary_min: int = 0
    salary_max: int = 0
    exclude_keywords: list[str] = []
    require_keywords_in_title: list[str] = []


class TelegramConfig(BaseModel):
    enabled: bool = True
    max_jobs_per_message: int = 5
    include_description_preview: bool = True
    description_chars: int = 300


class NotificationConfig(BaseModel):
    telegram: TelegramConfig = TelegramConfig()


class LinkedInApplyConfig(BaseModel):
    headless: bool = True
    slow_mo_ms: int = 150
    max_applications_per_day: int = 10


class CvConfig(BaseModel):
    pdf_path: str = "cv/resume.pdf"
    answers: dict[str, Any] = {}


class AutoApplyConfig(BaseModel):
    enabled: bool = False
    risk_acknowledged: bool = False
    mode: str = "human_review"
    approval_timeout_hours: int = 12
    linkedin: LinkedInApplyConfig = LinkedInApplyConfig()
    cv: CvConfig = CvConfig()

    @model_validator(mode="after")
    def check_risk_acknowledged(self):
        if self.enabled and not self.risk_acknowledged:
            raise ValueError(
                "auto_apply.risk_acknowledged debe ser true para activar el auto-apply. "
                "Lee la advertencia de ToS en config.yaml antes de activarlo."
            )
        return self


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "logs/jobhunter.log"
    rotation: str = "10 MB"
    retention: str = "30 days"


class Settings(BaseModel):
    search: SearchConfig = SearchConfig()
    notification: NotificationConfig = NotificationConfig()
    auto_apply: AutoApplyConfig = AutoApplyConfig()
    logging: LoggingConfig = LoggingConfig()
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    linkedin_email: str = ""
    linkedin_password: str = ""


_settings: Settings | None = None


def load_settings() -> Settings:
    global _settings
    if _settings is not None:
        return _settings

    config_path = Path("config.yaml")
    data: dict = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    data["telegram_bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN", "")
    data["telegram_chat_id"] = os.getenv("TELEGRAM_CHAT_ID", "")
    data["linkedin_email"] = os.getenv("LINKEDIN_EMAIL", "")
    data["linkedin_password"] = os.getenv("LINKEDIN_PASSWORD", "")

    _settings = Settings.model_validate(data)
    return _settings

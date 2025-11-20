from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

    def priority(self) -> int:
        priority_map = {
            AlertSeverity.CRITICAL: 1,
            AlertSeverity.WARNING: 2,
            AlertSeverity.INFO: 3,
        }
        return priority_map[self]


class HostConfig(BaseModel):
    url: HttpUrl
    display_name: str

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme not in ["http", "https"]:
            raise ValueError("URL scheme must be http or https")
        return v


class HostStatus(BaseModel):
    hostname: str
    reachable: bool
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    alert_count: int = 0


class Alert(BaseModel):
    source_host: str
    alert_id: str
    name: str
    severity: AlertSeverity
    status: str
    timestamp: datetime
    value: Optional[float] = None
    message: str

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

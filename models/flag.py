from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FlagType(Enum):
    INFO = "INFO"       # Thông tin cần biết
    WARNING = "WARNING" # Cần theo dõi
    ALERT = "ALERT"     # Cần xem xét ngay


@dataclass
class Flag:
    type: FlagType
    code: str           # VD: "AR_OUTPACE_REVENUE"
    message: str        # Mô tả ngắn cho người dùng
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
        }

    def to_telegram(self) -> str:
        icon = {"INFO": "ℹ️", "WARNING": "⚠️", "ALERT": "🚨"}[self.type.value]
        return f"{icon} *{self.code}*: {self.message}"

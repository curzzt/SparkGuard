import random
from dataclasses import dataclass

TEMPLATES = [
    "早呀，今天也要续火花～",
    "周三啦，火花别断！",
    "{nickname}，打卡续火花～",
    "新的一天，火花续上～",
    "记得续火花哦～",
]


@dataclass
class AgentResult:
    message: str
    source: str
    template_id: str | None = None
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "source": self.source,
            "template_id": self.template_id,
            "confidence": self.confidence,
        }


class AgentService:
    async def build_message(self, settings, target) -> AgentResult:
        if target.custom_template:
            return AgentResult(message=target.custom_template, source="custom")
        if settings.default_template and not settings.random_template_enabled:
            return AgentResult(message=settings.default_template, source="default")
        tpl = random.choice(TEMPLATES)
        message = tpl.format(nickname=target.nickname)
        return AgentResult(message=message, source="random_template")

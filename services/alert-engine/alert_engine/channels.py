"""Notification channels."""

from __future__ import annotations

import abc

import httpx

from mchpai_common.config import settings
from mchpai_common.logging import get_logger

log = get_logger("alert-engine.channels")


class Channel(abc.ABC):
    name: str

    @abc.abstractmethod
    async def send(self, title: str, body: str) -> None: ...

    @property
    @abc.abstractmethod
    def configured(self) -> bool: ...


class DiscordChannel(Channel):
    name = "discord"

    @property
    def configured(self) -> bool:
        return bool(settings.discord_webhook_url)

    async def send(self, title: str, body: str) -> None:
        if not self.configured:
            return
        async with httpx.AsyncClient(timeout=8) as c:
            await c.post(settings.discord_webhook_url, json={"content": f"**{title}**\n{body}"})


class TelegramChannel(Channel):
    name = "telegram"

    @property
    def configured(self) -> bool:
        return bool(settings.telegram_bot_token and settings.telegram_chat_id)

    async def send(self, title: str, body: str) -> None:
        if not self.configured:
            return
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=8) as c:
            await c.post(url, json={"chat_id": settings.telegram_chat_id,
                                    "text": f"{title}\n{body}", "parse_mode": "Markdown"})


def build_channels() -> list[Channel]:
    return [c for c in (DiscordChannel(), TelegramChannel()) if c.configured]

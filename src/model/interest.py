from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.json"


@dataclass(frozen=True)
class InterestConfig:
    names: tuple[str, ...]
    favorite_topics: tuple[str, ...]
    engage_threshold: int
    interest_retention_decay: int
    interest_ping_add: int
    interest_reply_add: int
    interest_topic_add: int
    interest_name_add: int
    max_interest: int


def _strip_json_comments(raw_text: str) -> str:
    return re.sub(r"(?m)//.*$", "", raw_text)

def get_threshold_for_interest_level(level: int, config: InterestConfig | None = None) -> int:
    if config is None:
        config = load_interest_config()

    return max(1, config.engage_threshold)

def load_interest_config(config_path: Path = CONFIG_PATH) -> InterestConfig:
    raw_config = json.loads(_strip_json_comments(config_path.read_text(encoding="utf-8")))

    return InterestConfig(
        names=tuple(str(name) for name in raw_config.get("names", [])),
        favorite_topics=tuple(str(topic) for topic in raw_config.get("favorite_topics", [])),
        engage_threshold=int(raw_config.get("engage_threshold", 1)),
        interest_retention_decay=int(raw_config.get("interest_retention_decay", 0)),
        interest_ping_add=int(raw_config.get("interest_ping_add", 0)),
        interest_reply_add=int(raw_config.get("interest_reply_add", 0)),
        interest_topic_add=int(raw_config.get("interest_topic_add", 0)),
        interest_name_add=int(raw_config.get("interest_name_add", 0)),
        max_interest=int(raw_config.get("max_interest", 100)),
    )


def _iter_messages(message_block: object) -> Iterable[object]:
    get_messages = getattr(message_block, "get_messages", None)
    if callable(get_messages):
        return list(get_messages()) # type: ignore

    return list(message_block)  # type: ignore[arg-type]


def _content_matches_any(content: str, keywords: Iterable[str]) -> bool:
    lowered_content = content.lower()

    for keyword in keywords:
        lowered_keyword = keyword.lower().strip()
        if not lowered_keyword:
            continue

        if lowered_keyword in lowered_content:
            return True

    return False


def _message_mentions_bot(message: object, bot_user: object | None) -> bool:
    if bot_user is None:
        return False

    bot_id = getattr(bot_user, "id", None)
    if bot_id is None:
        return False

    for mentioned_user in getattr(message, "mentions", []):
        if getattr(mentioned_user, "id", None) == bot_id:
            return True

    content = getattr(message, "content", "") or ""
    return f"<@{bot_id}>" in content or f"<@!{bot_id}>" in content


def _message_replies_to_bot(message: object, bot_user: object | None) -> bool:
    if bot_user is None:
        return False

    bot_id = getattr(bot_user, "id", None)
    if bot_id is None:
        return False

    reference = getattr(message, "reference", None)
    if reference is None:
        return False

    resolved_message = getattr(reference, "resolved", None)
    if resolved_message is None:
        return False

    reply_author = getattr(resolved_message, "author", None)
    return getattr(reply_author, "id", None) == bot_id


def get_interest_delta(
    message_block: object,
    bot_user: object | None = None,
    config: InterestConfig | None = None,
) -> int:
    if config is None:
        config = load_interest_config()

    messages = _iter_messages(message_block)
    total_delta = 0
    saw_interest_trigger = False

    for message in messages:
        is_dm = getattr(getattr(message, "channel", None), "type", None) == "dm"

        # dms are of highest interest
        if is_dm:
            message_delta = 100
            saw_interest_trigger = True

        message_delta = 0
        content = getattr(message, "content", "") or ""

        if _message_replies_to_bot(message, bot_user):
            message_delta += config.interest_reply_add
            saw_interest_trigger = True

        if _message_mentions_bot(message, bot_user):
            message_delta += config.interest_ping_add
            saw_interest_trigger = True

        if _content_matches_any(content, config.names):
            message_delta += config.interest_name_add
            saw_interest_trigger = True

        if _content_matches_any(content, config.favorite_topics):
            message_delta += config.interest_topic_add
            saw_interest_trigger = True

        total_delta += message_delta

    if not saw_interest_trigger:
        return -config.interest_retention_decay
    
    if total_delta > config.max_interest:
        total_delta = config.max_interest

    return total_delta
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace


SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bot.message_bin import MessageBin
from model.interest import CONFIG_PATH, get_interest_delta, get_threshold_for_interest_level, load_interest_config


class InterestTests(unittest.TestCase):
    def test_load_interest_config_reads_root_config(self) -> None:
        config = load_interest_config(CONFIG_PATH)

        self.assertEqual(config.interest_retention_decay, 15)
        self.assertEqual(config.interest_ping_add, 50)
        self.assertEqual(config.engage_threshold, 50)
        self.assertIn("mezz", config.names)
        self.assertIn("roblox", config.favorite_topics)

    def test_threshold_uses_configured_engage_threshold(self) -> None:
        config = load_interest_config(CONFIG_PATH)

        self.assertEqual(get_threshold_for_interest_level(0, config), 50)
        self.assertEqual(get_threshold_for_interest_level(80, config), 50)

    def test_get_interest_delta_returns_decay_when_block_has_no_triggers(self) -> None:
        message_bin = MessageBin()
        author = SimpleNamespace(id=1, name="alice", display_name=None)
        channel = SimpleNamespace(name="general")
        message = SimpleNamespace(
            author=author,
            content="just chatting",
            channel=channel,
            mentions=[],
            channel_mentions=[],
            reference=None,
        )

        message_bin.add_message(message)  # type: ignore[arg-type]

        self.assertEqual(get_interest_delta(message_bin, bot_user=SimpleNamespace(id=999)), -15)

    def test_get_interest_delta_combines_reply_ping_name_and_topic_triggers(self) -> None:
        message_bin = MessageBin()
        bot_user = SimpleNamespace(id=999, name="bot", display_name="bot")
        author = SimpleNamespace(id=1, name="alice", display_name=None)
        channel = SimpleNamespace(name="general")
        replied_message = SimpleNamespace(author=bot_user, content="older message")
        message = SimpleNamespace(
            author=author,
            content="hey mezz, check roblox <@999>",
            channel=channel,
            mentions=[bot_user],
            channel_mentions=[],
            reference=SimpleNamespace(resolved=replied_message),
        )

        message_bin.add_message(message)  # type: ignore[arg-type]

        self.assertEqual(get_interest_delta(message_bin, bot_user=bot_user), 100)


if __name__ == "__main__":
    unittest.main()
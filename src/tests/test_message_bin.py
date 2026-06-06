from pathlib import Path
import sys
import unittest
from types import SimpleNamespace


SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bot.message_bin import MessageBin


class MessageBinTests(unittest.TestCase):
    def test_stringifies_messages_with_mentions_channels_and_reply_context(self) -> None:
        message_bin = MessageBin()

        mentioned_user = SimpleNamespace(id=42, name="rawusername", display_name=None)
        mentioned_channel = SimpleNamespace(id=77, name="general-chat")
        replied_user = SimpleNamespace(id=99, name="oldsender", display_name="Old Sender")
        reply_target = SimpleNamespace(
            author=replied_user,
            content="hello <@42> in <#77>",
            mentions=[mentioned_user],
            channel_mentions=[mentioned_channel],
        )

        author = SimpleNamespace(id=1, name="alice", display_name=None)
        channel = SimpleNamespace(name="project-room")
        message = SimpleNamespace(
            author=author,
            content="hey <@42>, check <#77>",
            channel=channel,
            mentions=[mentioned_user],
            channel_mentions=[mentioned_channel],
            reference=SimpleNamespace(resolved=reply_target),
        )

        message_bin.add_message(message) # type: ignore

        self.assertEqual(
            str(message_bin),
            "alice in #project-room: hey @rawusername, check #general-chat\n"
            "(replying to Old Sender: hello @rawusername in #general-chat)",
        )

    def test_stringifies_message_without_display_name_or_reply(self) -> None:
        message_bin = MessageBin()

        author = SimpleNamespace(id=1, name="alice", display_name=None)
        channel = SimpleNamespace()
        message = SimpleNamespace(
            author=author,
            content="plain text",
            channel=channel,
            mentions=[],
            channel_mentions=[],
            reference=None,
        )

        message_bin.add_message(message) # type: ignore

        self.assertEqual(str(message_bin), "alice in #unknown-channel: plain text")


if __name__ == "__main__":
    unittest.main()
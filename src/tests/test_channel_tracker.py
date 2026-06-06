from pathlib import Path
import sys
import unittest
from types import SimpleNamespace


SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bot.channel_tracker import ChannelTracker, DEFAULT_SUMMARY


class ChannelTrackerTests(unittest.TestCase):
    def test_resolve_context_id_prefers_channel_id_and_falls_back_to_author_id(self) -> None:
        guild_message = SimpleNamespace(
            channel=SimpleNamespace(id=123),
            author=SimpleNamespace(id=999),
        )
        dm_message = SimpleNamespace(
            channel=SimpleNamespace(id=None),
            author=SimpleNamespace(id=456),
        )

        self.assertEqual(ChannelTracker.resolve_context_id(guild_message), 123)
        self.assertEqual(ChannelTracker.resolve_context_id(dm_message), 456)

    def test_record_message_updates_both_memory_bins(self) -> None:
        tracker = ChannelTracker(id=1)
        message = SimpleNamespace(content="hello")

        tracker.record_message(message)

        self.assertEqual(len(tracker.jar), 1)
        self.assertEqual(len(tracker.long_term_memory), 1)
        self.assertIs(tracker.jar.get_messages()[0], message)
        self.assertIs(tracker.long_term_memory.get_messages()[0], message)

    def test_response_lock_is_scoped_to_tracker(self) -> None:
        tracker = ChannelTracker(id=1)

        self.assertTrue(tracker.start_response())
        self.assertFalse(tracker.start_response())

        tracker.finish_response()

        self.assertTrue(tracker.start_response())

    def test_clear_all_memory_resets_state(self) -> None:
        tracker = ChannelTracker(id=1)
        tracker.record_message(SimpleNamespace(content="hello"))
        tracker.set_summary("custom summary")
        tracker.set_interest_level(12)

        tracker.clear_all_memory()

        self.assertEqual(len(tracker.jar), 0)
        self.assertEqual(len(tracker.long_term_memory), 0)
        self.assertEqual(tracker.get_summary(), DEFAULT_SUMMARY)
        self.assertEqual(tracker.interest_level, 0)

    def test_pull_new_messages_for_interest_returns_only_new_entries(self) -> None:
        tracker = ChannelTracker(id=1)
        first = SimpleNamespace(id=1, content="one")
        second = SimpleNamespace(id=2, content="two")

        tracker.record_message(first)
        self.assertEqual(tracker.pull_new_messages_for_interest(), [first])
        self.assertEqual(tracker.pull_new_messages_for_interest(), [])

        tracker.record_message(second)
        self.assertEqual(tracker.pull_new_messages_for_interest(), [second])

    def test_mark_responded_tracks_last_message_id(self) -> None:
        tracker = ChannelTracker(id=1)
        message = SimpleNamespace(id=42, content="hello")

        self.assertFalse(tracker.has_responded_to(message))

        tracker.mark_responded(message)

        self.assertTrue(tracker.has_responded_to(message))


if __name__ == "__main__":
    unittest.main()
import typing

from bot.message_bin import MessageBin

DEFAULT_SUMMARY = "No current summary to worry about"

class ChannelTracker:
    def __init__(self, id: int, channel_object):
        self.id = id
        self.jar = MessageBin()
        self.channel_object = channel_object
        self.long_term_memory = MessageBin(max_size=100)
        self.interest_level = 0
        self.latest_summary = DEFAULT_SUMMARY
        self.response_in_progress = False
        self._interest_cursor = 0
        self.messages_since_last_summary = 0
        self.last_responded_message_id: int | None = None

    @staticmethod
    def resolve_context_id(message: typing.Any) -> int:
        channel_id = getattr(getattr(message, "channel", None), "id", None)
        if channel_id is not None:
            return channel_id

        author_id = getattr(getattr(message, "author", None), "id", None)
        if author_id is not None:
            return author_id

        raise ValueError("message must have either channel.id or author.id")

    def get_summary(self) -> str:
        return self.latest_summary
    
    def set_summary(self, summary: str):
        self.latest_summary = summary

    def start_response(self) -> bool:
        if self.response_in_progress:
            return False

        self.response_in_progress = True
        return True

    def finish_response(self) -> None:
        self.response_in_progress = False

    def set_interest_level(self, level: int):
        self.interest_level = level

    def add_interest(self, amount: int):
        self.interest_level += amount

        if self.interest_level < 0:
            self.interest_level = 0
        elif self.interest_level > 100:
            self.interest_level = 100

    def pull_new_messages_for_interest(self) -> list[typing.Any]:
        messages = self.jar.get_messages()
        total_messages = len(messages)

        if self._interest_cursor > total_messages:
            self._interest_cursor = total_messages

        new_messages = messages[self._interest_cursor:]
        self._interest_cursor = total_messages
        return list(new_messages)

    def has_responded_to(self, message: typing.Any) -> bool:
        message_id = getattr(message, "id", None)
        if message_id is None:
            return False

        return self.last_responded_message_id == message_id

    def mark_responded(self, message: typing.Any) -> None:
        message_id = getattr(message, "id", None)
        if message_id is None:
            return

        self.last_responded_message_id = message_id

    def record_message(self, message: typing.Any):
        self.add_message_to_jar(message)
        self.add_message_to_long_term_memory(message)

    def add_message_to_jar(self, message: typing.Any):
        self.jar.add_message(message)
    
    def add_message_to_long_term_memory(self, message: typing.Any):
        self.long_term_memory.add_message(message)

    def clear_jar(self):
        self.jar.clear_messages()

    def clear_long_term_memory(self):
        self.long_term_memory.clear_messages()

    def clear_all_memory(self):
        self.clear_jar()
        self.clear_long_term_memory()
        self.latest_summary = DEFAULT_SUMMARY
        self.interest_level = 0
        self._interest_cursor = 0
        self.last_responded_message_id = None


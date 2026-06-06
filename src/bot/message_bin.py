import discord
import re

def format_message(message: discord.Message) -> str:
    author_name = getattr(message.author, "display_name", None) or getattr(message.author, "name", None) or "unknown user"
    channel_name = getattr(message.channel, "name", None)
    dm_channel = isinstance(message.channel, discord.DMChannel)

    if channel_name:
        formatted_channel = f"#{channel_name}"
    elif dm_channel:
        formatted_channel = "a direct message"
    else:
        formatted_channel = "#unknown-channel"

    content = getattr(message, "content", "") or ""
    content = re.sub(r"<@!?([0-9]+)>", lambda m: f"@{m.group(1)}", content)
    content = re.sub(r"<#([0-9]+)>", lambda m: f"#{m.group(1)}", content)

    return f"{author_name} in {formatted_channel}: {content}"

class MessageBin():
    def __init__(self, max_size: int = 20):
        self.max_size = max_size
        self.messages = []
    
    def add_message(self, message: discord.Message):
        self.messages.append(message)
        if len(self.messages) > self.max_size:
            self.messages.pop(0)

    def clear_messages(self):
        self.messages = []
    
    def get_messages(self):
        return self.messages

    def _format_user_name(self, user) -> str:
        return getattr(user, "display_name", None) or getattr(user, "name", None) or "unknown user"

    def _format_channel_name(self, channel) -> str:
        channel_name = getattr(channel, "name", None)
        dm_channel = isinstance(channel, discord.DMChannel)

        if channel_name:
            return f"#{channel_name}"

        if dm_channel:
            return "a direct message"

        return "#unknown-channel"

    def _replace_user_mentions(self, content: str, message: discord.Message) -> str:
        mention_map = {}

        for mentioned_user in getattr(message, "mentions", []):
            mention_id = getattr(mentioned_user, "id", None)
            if mention_id is not None:
                mention_map[str(mention_id)] = getattr(mentioned_user, "name", None) or getattr(mentioned_user, "display_name", None) or "unknown user"

        def replace(match: re.Match[str]) -> str:
            user_id = match.group(1)
            return f"@{mention_map.get(user_id, user_id)}"

        return re.sub(r"<@!?([0-9]+)>", replace, content)

    def _replace_channel_mentions(self, content: str, message: discord.Message) -> str:
        mention_map = {}

        for mentioned_channel in getattr(message, "channel_mentions", []):
            mention_id = getattr(mentioned_channel, "id", None)
            mention_name = getattr(mentioned_channel, "name", None)
            if mention_id is not None and mention_name:
                mention_map[str(mention_id)] = f"#{mention_name}"

        def replace(match: re.Match[str]) -> str:
            channel_id = match.group(1)
            return mention_map.get(channel_id, f"#{channel_id}")

        return re.sub(r"<#([0-9]+)>", replace, content)

    def _format_reply_context(self, message: discord.Message) -> str:
        reference = getattr(message, "reference", None)
        if reference is None:
            return ""

        resolved_message = getattr(reference, "resolved", None)
        if resolved_message is None:
            return "\n(replying to a previous message)"

        reply_author = self._format_user_name(getattr(resolved_message, "author", None))
        reply_content = getattr(resolved_message, "content", "") or "[no content]"
        reply_content = self._replace_channel_mentions(self._replace_user_mentions(reply_content, resolved_message), resolved_message)

        return f"\n(replying to {reply_author}: {reply_content})"
    
    def __str__(self):
        formatted_messages = []
        last_author_id = 0
        for msg in self.messages:
            author_name = self._format_user_name(getattr(msg, "author", None))
            channel_name = self._format_channel_name(getattr(msg, "channel", None))
            content = getattr(msg, "content", "") or ""
            content = self._replace_channel_mentions(self._replace_user_mentions(content, msg), msg)
            reply_context = self._format_reply_context(msg)

            owner_string = f"{author_name} in {channel_name}:"

            if author_name == "mezz":
                owner_string = f"We replied:"

            if last_author_id != getattr(getattr(msg, "author", None), "id", None):
                formatted_messages.append(f"\n{owner_string} {content}{reply_context}")
            else:
                # same author as last message, so just append content without repeating author/channel
                formatted_messages.append(f"{content}")

            last_author_id = getattr(getattr(msg, "author", None), "id", None) or 0

        return "\n".join(formatted_messages)
    
    def __len__(self):
        return len(self.messages)
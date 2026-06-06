from bot.channel_tracker import ChannelTracker
import asyncio
import os
import random
from pathlib import Path
import json
import discord

from model.interest import get_interest_delta, load_interest_config, get_threshold_for_interest_level
from model.ollama import OllamaRouter
from model.open_router import OpenRouterLMM
from model.response_modes import build_response_mode_prompt, choose_response_mode, load_response_modes

MODEL_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "model" / "prompts"
UPDATE_TIME = 3

MODES = load_response_modes()
INTEREST_CONFIG = load_interest_config(Path(__file__).resolve().parents[2] / "config.json")

ROUTER_TOKEN = os.getenv("ROUTER_TOKEN")   

client = None
bot = None

tracked_channels: dict[int, ChannelTracker] = {}
user_ids_typing: list[int] = []

# doesnt sound like me at all
# chat_model = OllamaRouter(
#     model="llama3-chatqa:8b",
#     prompt_dir=MODEL_PROMPTS_DIR / "chat_model",
#     stream_response=True
# )

# summary_model = OllamaRouter(
#     model="qwen2.5:0.5b",
#     prompt_dir=MODEL_PROMPTS_DIR / "summary_model",
#     stream_response=False
# )

chat_model = OpenRouterLMM(
    model="glm-4.5-air:free",
    token=ROUTER_TOKEN,
    prompt_dir=MODEL_PROMPTS_DIR / "chat_model",
    stream_response=True,
)

summary_model = OpenRouterLMM(
    model="z-ai/glm-4.5-air:free",
    token=ROUTER_TOKEN,
    prompt_dir=MODEL_PROMPTS_DIR / "summary_model",
    stream_response=False,
)

async def set_bot_status(status: str) -> None:
    if client is not None:
        await client.change_presence(activity=discord.Game(name=status))

async def set_presence(status: discord.Status) -> None:
    if client is not None:
        await client.change_presence(status=status)

def get_line_typing_delay(line: str) -> float:
    clean_line = line.strip()

    if not clean_line:
        return 0.0

    character_count = len(clean_line)
    base_delay = 0.3
    per_character_delay = character_count * 0.055
    jitter = random.uniform(0.0, 0.35)

    return min(6.0, base_delay + per_character_delay + jitter)


def get_author_name(message) -> str:
    author_name = message.author.display_name or message.author.name

    if author_name == "mezz":
        return "your creator"

    return author_name


def build_full_prompt(mode) -> str:
    response_mode_prompt = build_response_mode_prompt([mode])

    return (
        f"response modes:\n{response_mode_prompt}\n\n"
        f"selected mode:\n{mode.instruction}"
    )


def get_channel_tracker(message) -> ChannelTracker:
    channel_id = ChannelTracker.resolve_context_id(message)
    channel_tracker = tracked_channels.get(channel_id)

    channel = None
    # find the channel object if possible to attach to the tracker for later use
    if client is not None:
        for guild in client.guilds:
            for ch in guild.channels:
                if getattr(ch, "id", None) == channel_id:
                    channel = ch
                    break
            if channel is not None:
                break

    if channel_tracker is None:
        channel_tracker = ChannelTracker(id=channel_id, channel_object=channel)
        tracked_channels[channel_id] = channel_tracker

    return channel_tracker

async def register_client(c) -> None:
    global client
    client = c

async def send_line_with_typing(message, line: str) -> None:
    if line.strip() == "":
        return

    async with message.channel.typing():
        await asyncio.sleep(get_line_typing_delay(line))
        await message.channel.send(line)
        await asyncio.sleep(random.uniform(0.1, 1.3))


async def stream_response_lines_ollama(message, response) -> None:
    pending_line = ""
    saw_stream_chunk = False

    for chunk in response:
        message_chunk = getattr(chunk, "message", None)
        if message_chunk is None:
            continue

        token = getattr(message_chunk, "content", "") or ""
        if not token:
            continue

        saw_stream_chunk = True
        pending_line += token

        while "\n" in pending_line:
            line_to_send, pending_line = pending_line.split("\n", 1)
            await send_line_with_typing(message, line_to_send)

    if pending_line:
        await send_line_with_typing(message, pending_line)

    if not saw_stream_chunk:
        content = getattr(getattr(response, "message", None), "content", "") or ""
        await send_line_with_typing(message, content)

async def stream_response_lines_openrouter(message, response) -> None:
    pending_line = ""
    saw_stream_chunk = False

    for line in response.iter_lines():
        if not line:
            continue

        decoded = line.decode("utf-8")

        if "data: " not in decoded:
            continue

        data = decoded.replace("data: ", "")

        if data == "[DONE]":
            break

        try:
            chunk = json.loads(data)
            token = chunk["choices"][0]["delta"].get("content", "")
        except (KeyError, IndexError, json.JSONDecodeError):
            continue

        if not token:
            continue

        saw_stream_chunk = True
        pending_line += token

        while "\n" in pending_line:
            line_to_send, pending_line = pending_line.split("\n", 1)
            await send_line_with_typing(message, line_to_send)

    if pending_line:
        await send_line_with_typing(message, pending_line)

    if not saw_stream_chunk:
        try:
            body = response.json()
            content = body["choices"][0]["message"].get("content", "")
        except (ValueError, KeyError, IndexError, TypeError):
            return

        await send_line_with_typing(message, content)


async def summarize_conversation(conversation: str) -> str:
    response = await summary_model.get_response(conversation)
    return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")


async def respond_to_message(message_string: str, message: discord.Message, channel_tracker: ChannelTracker) -> None:
    if not channel_tracker.start_response():
        print("Already responding to a message in this channel, skipping...")
        return

    try:
        mode = choose_response_mode(MODES)
        mode_prompt = build_full_prompt(mode)
        author_name = get_author_name(message)

        final_prompt = f"\n\n{author_name}: {message_string}\n{mode_prompt}\nYour reply as mezz:"
        print(final_prompt)

        response = await chat_model.get_response(
            final_prompt,
        )

        if response.status_code != 200:
            print(f"OpenRouter request failed with status {response.status_code}: {response.text}")
            return

        await stream_response_lines_openrouter(message, response)
        channel_tracker.finish_response()
    except Exception as e:
        print(f"Error generating/sending response: {e}")

async def handle_command(message, command: str) -> None:
    if command == "jar":
        channel_tracker = get_channel_tracker(message)
        await message.channel.send(str(channel_tracker.jar))
    elif command == "interest":
        channel_tracker = get_channel_tracker(message)
        interest_delta = get_interest_delta(channel_tracker.jar, bot_user=None, config=INTEREST_CONFIG)
        await message.channel.send(f"Interest: {interest_delta}")
    elif command == "memory":
        channel_tracker = get_channel_tracker(message)
        await message.channel.send(str(channel_tracker.long_term_memory))
    elif command == "get_summary":
        channel_tracker = get_channel_tracker(message)
        await message.channel.send(channel_tracker.get_summary())
    elif command == "summarize":
        channel_tracker = get_channel_tracker(message)
        await message.channel.send(f"-# generating summary for {channel_tracker.id}, please hold...")
        conversation = f"{channel_tracker.long_term_memory}"
        summary = await summarize_conversation(conversation)
        channel_tracker.set_summary(summary)
        await message.channel.send(f"Conversation summary:\n{summary}")
    elif command in ("empty", "clear"):
        channel_tracker = get_channel_tracker(message)
        channel_tracker.clear_all_memory()
        print("Emptied message jar and long term memory.")

async def handle_message(message, bot_user=None) -> None:
    global bot, user_ids_typing
    bot = bot_user

    if message.author.id in user_ids_typing:
        user_ids_typing.remove(message.author.id)

    if message.author != bot_user and message.content.startswith("$"):
        await handle_command(message, message.content[1:])
        return

    channel_tracker = get_channel_tracker(message)
    channel_tracker.record_message(message)
    channel_tracker.messages_since_last_summary += 1

async def handle_typing_start(channel, user) -> None:
    if user.id not in user_ids_typing:
        user_ids_typing.append(user.id)

async def update_channel_summary(channel_tracker: ChannelTracker) -> None:
    if channel_tracker.messages_since_last_summary <= 30:
        return
    conversation = f"{channel_tracker.long_term_memory}\n{channel_tracker.jar}"
    new_summary = await summarize_conversation(conversation)
    channel_tracker.set_summary(new_summary)
    channel_tracker.messages_since_last_summary = 0
    print(f"Updated summary for channel {channel_tracker.id}:\n{new_summary}")
    # if channel_tracker.channel_object is not None:
    #     try:
    #         await channel_tracker.channel_object.send(f"-# silently updated conversation summary:\n{new_summary}")
    #     except Exception as e:
    #         print(f"Error sending summary update message to channel {channel_tracker.id}: {e}")

# Lifetime cycle for the bot and its main update loop that checks for interesting conversations and responds to them
async def update() -> None:
    global user_ids_typing
    while True:
        if bot is None or not tracked_channels:
            await set_bot_status(f"waiting for activity")
            await set_presence(discord.Status.idle)
            await asyncio.sleep(UPDATE_TIME)
            continue

        # update interest levels for all channels based on recent messages
        for tracker in tracked_channels.values():
            all_messages = tracker.jar.get_messages() + tracker.long_term_memory.get_messages()
            interest_source = all_messages[-10:]
            interest_delta = get_interest_delta(interest_source, bot_user=bot, config=INTEREST_CONFIG)
            tracker.add_interest(interest_delta)

        # Get the channel with the highest interest level
        most_interesting_tracker = max(tracked_channels.values(), key=lambda t: t.interest_level, default=None)

        # Get the most recent messages and summary if available
        if most_interesting_tracker is not None:
            threshold = get_threshold_for_interest_level(most_interesting_tracker.interest_level, INTEREST_CONFIG)
            within_interest = most_interesting_tracker.interest_level >= threshold
            if not within_interest:
                print(
                    f"Most interesting channel {most_interesting_tracker.id} is below interest threshold "
                    f"with interest level {most_interesting_tracker.interest_level}. Skipping response."
                )
                await asyncio.sleep(UPDATE_TIME)
                continue
            
            # get our current memory for this channel
            summary = most_interesting_tracker.get_summary()
            messages = str(most_interesting_tracker.jar)

            print(f"Most interesting channel: {most_interesting_tracker.id} (interest level: {most_interesting_tracker.interest_level})")
            await set_bot_status(f"responding in channel {most_interesting_tracker.id} (interest: {most_interesting_tracker.interest_level})")
            
            # create the juicy string that combines the summary and recent messages for the prompt
            combined = f"Chat Summary:\n{summary}\nLast messages:\n{messages}"
            most_recent_message = most_interesting_tracker.jar.get_messages()[-1] if most_interesting_tracker.jar.get_messages() else None

            # See check for most recent message and make sure we're not the author of it
            # If the author is still typing: skip!
            if (
                most_recent_message
                and getattr(most_recent_message, "author", None) != bot
                and not most_recent_message.author.id in user_ids_typing
            ):
                print(combined)
                await respond_to_message(combined, most_recent_message, most_interesting_tracker)
            else:
                await set_presence(discord.Status.idle)
                await set_bot_status(f"waiting for activity")

            # Creates a summary if we have a long message history
            asyncio.create_task(update_channel_summary(most_interesting_tracker))
        else:
            await set_bot_status(f"waiting for activity")
            await set_presence(discord.Status.idle)

        await asyncio.sleep(UPDATE_TIME)
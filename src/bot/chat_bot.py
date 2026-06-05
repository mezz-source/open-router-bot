import discord
from pathlib import Path
from model.open_router import OpenRouterLMM
from model.response_modes import build_response_mode_prompt, choose_response_mode, load_response_modes
import asyncio
import json
import os
import random

TOKEN = os.getenv("BOT_TOKEN") 
MODES = load_response_modes() 
MODEL_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "model" / "prompts"

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
response_in_progress = False

# feel free to switch this out later
chat_model = OpenRouterLMM(
    model="z-ai/glm-4.5-air:free",
    token=os.getenv("ROUTER_TOKEN"),
    prompt_dir=MODEL_PROMPTS_DIR / "chat_model",
    stream_response = True
)

# TODO: Implement
summary_model = OpenRouterLMM(
    model="z-ai/glm-4.5-air:free",
    token=os.getenv("ROUTER_TOKEN"),
    prompt_dir=MODEL_PROMPTS_DIR / "summary_model",
    stream_response = False
)

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


async def send_line_with_typing(message, line: str) -> None:
    if line.strip() == "":
        return

    async with message.channel.typing():
        # await asyncio.sleep(get_line_typing_delay(line))
        await message.channel.send(line)


async def stream_response_lines(message, response) -> None:
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
    if response.status_code != 200:
        print(f"Summary model request failed with status {response.status_code}: {response.text}")
        return "Summary unavailable."
    
    return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")

async def respond_to_message(message):
    global response_in_progress

    if response_in_progress:
        return

    response_in_progress = True

    try:
        mode = choose_response_mode(MODES)
        print(f"Selected response mode: {mode.name} (weight: {mode.weight})")
        author_name = get_author_name(message)

        print(f"RESPONSE MODE:\n{build_response_mode_prompt([mode])}\n\n{author_name}: {message.content}")

        response = await chat_model.get_response(
            f"{author_name}: {message.content}",
        )

        if response.status_code != 200:
            print(f"OpenRouter request failed with status {response.status_code}: {response.text}")
            return

        await stream_response_lines(message, response)
    finally:
        response_in_progress = False


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    await respond_to_message(message)

def main():
    client.run(TOKEN) # type: ignore

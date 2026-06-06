from pathlib import Path

import requests

from model.prompt_compiler import compile_prompt

URL = "https://openrouter.ai/api/v1/chat/completions"

class OpenRouterLMM():
    def __init__(self, model: str, token: str | None, prompt_dir: Path | None = None, stream_response: bool = True):
        self.model = model
        self.token = token
        self.prompt = compile_prompt(prompt_dir) if prompt_dir is not None else compile_prompt()
        self.stream_response = stream_response

    async def get_response(self, message_str: str):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self.prompt
                },
                {"role": "user", "content": f"{message_str}\nEnter response as mezz:"}
            ],
            "stream": self.stream_response,
        }

        response = requests.post(URL, headers=headers, json=payload, stream=self.stream_response)
        return response
        




from pathlib import Path
from ollama import chat
from model.prompt_compiler import compile_prompt

class OllamaModel():
    def __init__(self, prompt_dir: Path | None = None, stream_response: bool = True, model: str = "qwen2.5:3b"):
        self.model = model
        self.prompt = compile_prompt(prompt_dir) if prompt_dir is not None else compile_prompt()
        self.stream_response = stream_response

    async def get_response(self, message_str: str):
        response = chat(
            model=self.model,
            messages=[
                {'role': 'system', 'content': self.prompt},
                {'role': 'user', 'content': message_str}
            ],
            stream=self.stream_response
        )

        if self.stream_response:
            return response
        else:
            return response.message.content # type: ignore

"""
from ollama import chat

stream = chat(
  model='qwen3',
  messages=[{'role': 'user', 'content': 'What is 17 × 23?'}],
  stream=True,
)

in_thinking = False
content = ''
thinking = ''
for chunk in stream:
  if chunk.message.thinking:
    if not in_thinking:
      in_thinking = True
      print('Thinking:\n', end='', flush=True)
    print(chunk.message.thinking, end='', flush=True)
    # accumulate the partial thinking 
    thinking += chunk.message.thinking
  elif chunk.message.content:
    if in_thinking:
      in_thinking = False
      print('\n\nAnswer:\n', end='', flush=True)
    print(chunk.message.content, end='', flush=True)
    # accumulate the partial content
    content += chunk.message.content

  # append the accumulated fields to the messages for the next request
  new_messages = [{ role: 'assistant', thinking: thinking, content: content }]
"""

        




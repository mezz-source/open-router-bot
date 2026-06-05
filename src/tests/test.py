import requests
import json

url = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": "Bearer <token>",
    "Content-Type": "application/json"
}

payload = {
    "model": "openrouter/free",
    "messages": [
        {"role": "system", "content": "You are a depressed historian who is obsessed with horses"},
        {"role": "user", "content": "Send one paragraph about how horses in the future may rise up and take over the world"}
    ],
    "stream": True
}

response = requests.post(url, headers=headers, json=payload, stream=True)

for line in response.iter_lines():
    if not line:
        continue

    decoded = line.decode("utf-8")

    if "data: " in decoded:
        data = decoded.replace("data: ", "")

        if data == "[DONE]":
            break

        try:
            import json
            chunk = json.loads(data)
            token = chunk["choices"][0]["delta"].get("content", "")
            print(token, end="", flush=True)
        except:
            pass


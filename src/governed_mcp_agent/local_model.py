import json
import urllib.request


OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen3:8b"


def call_local_model(prompt: str, model: str = DEFAULT_MODEL) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "")
    except Exception as e:
        return f"LOCAL_MODEL_ERROR: {str(e)}"
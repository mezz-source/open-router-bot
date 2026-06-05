from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().with_name("response_modes.json")


@dataclass(frozen=True)
class ResponseMode:
    name: str
    weight: float
    instruction: str


def load_response_modes(config_path: Path = CONFIG_PATH) -> list[ResponseMode]:
    raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    configured_modes = raw_config.get("modes", [])

    if not configured_modes:
        raise ValueError(f"No response modes were found in {config_path}")

    response_modes: list[ResponseMode] = []
    for index, configured_mode in enumerate(configured_modes, start=1):
        instruction = str(configured_mode.get("instruction", "")).strip()
        weight = float(configured_mode.get("weight", 0))
        name = str(configured_mode.get("name", f"mode_{index}"))

        if not instruction:
            raise ValueError(f"Response mode {index} is missing an instruction")

        if weight <= 0:
            raise ValueError(f"Response mode {index} must have a positive weight")

        response_modes.append(
            ResponseMode(
                name=name,
                weight=weight,
                instruction=instruction,
            )
        )

    return response_modes


def build_response_mode_prompt(response_modes: list[ResponseMode] | None = None) -> str:
    if response_modes is None:
        response_modes = load_response_modes()

    return "\n".join(
        f"{index}) {response_mode.instruction}"
        for index, response_mode in enumerate(response_modes, start=1)
    )


def choose_response_mode(response_modes: list[ResponseMode] | None = None) -> ResponseMode:
    if response_modes is None:
        response_modes = load_response_modes()

    weights = [response_mode.weight for response_mode in response_modes]
    return random.choices(response_modes, weights=weights, k=1)[0]
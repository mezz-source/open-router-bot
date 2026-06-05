from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def compile_prompt(prompt_dir: Path = PROMPTS_DIR) -> str:
	prompt_paths = sorted(
		prompt_dir.glob("*.txt"),
		key=lambda path: int(path.stem.split("_", 1)[0]),
	)

	if not prompt_paths:
		raise ValueError(f"No prompt files were found in {prompt_dir}")

	parts = [prompt_path.read_text(encoding="utf-8") for prompt_path in prompt_paths]

	combined = []
	for index, part in enumerate(parts):
		combined.append(part)
		if index < len(parts) - 1 and not part.endswith(("\n", "\r")):
			combined.append("\n")

	return "".join(combined)

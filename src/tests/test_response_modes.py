from pathlib import Path
import sys
import unittest


SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from model.prompt_compiler import compile_prompt
from model.response_modes import ResponseMode, build_response_mode_prompt, choose_response_mode


class ResponseModeTests(unittest.TestCase):
    def test_build_response_mode_prompt_numbers_modes_in_order(self) -> None:
        response_modes = [
            ResponseMode(name="direct", weight=70, instruction="Respond directly (short response, no jokes)"),
            ResponseMode(name="derail", weight=20, instruction="Derail (misintepret/be confused)"),
            ResponseMode(name="lorebuild", weight=10, instruction="Lorebuild"),
        ]

        self.assertEqual(
            build_response_mode_prompt(response_modes),
            "1) Respond directly (short response, no jokes)\n"
            "2) Derail (misintepret/be confused)\n"
            "3) Lorebuild",
        )

    def test_choose_response_mode_returns_configured_mode(self) -> None:
        response_modes = [
            ResponseMode(name="direct", weight=1, instruction="Respond directly (short response, no jokes)"),
            ResponseMode(name="derail", weight=1, instruction="Derail (misintepret/be confused)"),
        ]

        selected_mode = choose_response_mode(response_modes)

        self.assertIn(selected_mode, response_modes)

    def test_compile_prompt_uses_only_files_in_provided_directory(self) -> None:
        prompts_root = SRC_ROOT / "model" / "prompts"
        chat_prompt = compile_prompt(prompts_root / "chat_model")
        summary_prompt = compile_prompt(prompts_root / "summary_model")

        self.assertTrue(chat_prompt.strip())
        self.assertTrue(summary_prompt.strip())
        self.assertNotEqual(chat_prompt, summary_prompt)


if __name__ == "__main__":
    unittest.main()
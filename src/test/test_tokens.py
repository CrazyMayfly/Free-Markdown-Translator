from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.orchestrator import split_text
from src.core.tokens import TOKEN_ESTIMATOR_VERSION, estimate_tokens, prefix_costs, token_costs


class TokenEstimatorTests(unittest.TestCase):
    def test_empty_text_costs_nothing(self) -> None:
        self.assertEqual(estimate_tokens(""), 0)

    def test_cjk_is_priced_higher_than_latin(self) -> None:
        chinese = "这是一个用于测试的中文段落，" * 10
        english = "this is an english paragraph used for testing. " * 10
        self.assertGreater(estimate_tokens(chinese) / len(chinese), 2 * estimate_tokens(english) / len(english))

    def test_estimates_are_reproducible_and_monotonic(self) -> None:
        text = "混合 mixed 文本 with CJK 和 English, 还有 `code`."
        first = estimate_tokens(text)
        self.assertEqual(first, estimate_tokens(text))
        self.assertLessEqual(estimate_tokens(text[: len(text) // 2]), first)

    def test_prefix_costs_match_full_estimate(self) -> None:
        text = "alpha beta 混合文本 gamma"
        costs = prefix_costs(text)
        self.assertEqual(len(costs), len(text) + 1)
        self.assertEqual(costs[0], 0)
        self.assertAlmostEqual(costs[-1], sum(token_costs(text)))
        self.assertEqual(sorted(costs), costs)

    def test_estimator_version_is_exposed_for_fingerprints(self) -> None:
        self.assertTrue(TOKEN_ESTIMATOR_VERSION)


class SplitTextTests(unittest.TestCase):
    def _rebuild(self, pieces: list[tuple[str, str]]) -> str:
        return "".join(piece + separator for piece, separator in pieces)

    def test_returns_input_untouched_within_budget(self) -> None:
        text = "short paragraph"
        self.assertEqual(split_text(text, 100), [(text, "")])

    def test_ascii_pieces_fit_budget_and_rebuild_exactly(self) -> None:
        text = "\n".join(f"Source line {index} with a few words." for index in range(60))
        pieces = split_text(text, 60)
        self.assertGreater(len(pieces), 1)
        self.assertEqual(self._rebuild(pieces), text)
        for piece, _ in pieces:
            self.assertLessEqual(estimate_tokens(piece), 60)

    def test_cjk_pieces_fit_budget_and_rebuild_exactly(self) -> None:
        text = "这是一段中文内容，用来验证按 token 拆分时的字节级还原。" * 20
        pieces = split_text(text, 40)
        self.assertGreater(len(pieces), 1)
        self.assertEqual(self._rebuild(pieces), text)
        for piece, _ in pieces:
            self.assertLessEqual(estimate_tokens(piece), 40)

    def test_split_never_produces_empty_pieces(self) -> None:
        # A cut that lands exactly on a newline used to emit an empty piece,
        # which still cost one model call worth of prompt per segment.
        text = "line one. " * 40 + "\n" + "line two. " * 40 + "\n" + "line three."
        pieces = split_text(text, 60)
        self.assertEqual(self._rebuild(pieces), text)
        self.assertTrue(all(piece for piece, _ in pieces))

    def test_placeholders_are_never_cut_in_half(self) -> None:
        text = "前文 {{MD_0}} 后文，再一段 {{MD_1}} 结尾。" * 12
        pieces = split_text(text, 20)
        self.assertEqual(self._rebuild(pieces), text)
        for piece, _ in pieces:
            for placeholder in ("{{MD_0}}", "{{MD_1}}"):
                # Either the whole token is present, or it is absent entirely.
                self.assertNotIn(placeholder[:-1], piece.replace(placeholder, ""))

    def test_tight_budget_still_terminates(self) -> None:
        pieces = split_text("中文段落" * 50, 1)
        self.assertEqual(self._rebuild(pieces), "中文段落" * 50)
        self.assertGreater(len(pieces), 1)


if __name__ == "__main__":
    unittest.main()

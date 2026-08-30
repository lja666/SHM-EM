from __future__ import annotations

import json
import unittest
from pathlib import Path

from pit_pre.result_writer import (
    PERSISTED_OUTPUT_HASH_VERSION,
    PERSISTED_RESULT_HASH_VERSION,
    persisted_output_hash,
    persisted_result_hash,
)


class PersistedPredictionIntegrityTest(unittest.TestCase):
    def setUp(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "persisted-integrity-fixture.json"
        self.fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    def test_cross_language_fixture_hashes(self) -> None:
        self.assertEqual(PERSISTED_RESULT_HASH_VERSION, self.fixture["resultHashVersion"])
        self.assertEqual(PERSISTED_OUTPUT_HASH_VERSION, self.fixture["outputHashVersion"])
        result_hash = persisted_result_hash(self.fixture["rows"])
        self.assertEqual(self.fixture["expectedResultHash"], result_hash)
        self.assertEqual(
            self.fixture["expectedOutputHash"],
            persisted_output_hash({self.fixture["modelKey"]: result_hash}),
        )

    def test_row_order_does_not_change_hash(self) -> None:
        self.assertEqual(
            persisted_result_hash(self.fixture["rows"]),
            persisted_result_hash(list(reversed(self.fixture["rows"]))),
        )

    def test_decision_facing_value_change_changes_hash(self) -> None:
        changed = [dict(row) for row in self.fixture["rows"]]
        changed[0]["engineering_value"] = "104.56000000"
        self.assertNotEqual(
            persisted_result_hash(self.fixture["rows"]),
            persisted_result_hash(changed),
        )


if __name__ == "__main__":
    unittest.main()

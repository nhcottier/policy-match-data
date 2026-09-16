import copy
import json
import unittest
from pathlib import Path
from build_site import validate_dataset, validate_reviews


class PublicationTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        release = json.loads((root / "release.json").read_text())
        self.dataset = validate_dataset((root / release["dataset"]).read_bytes())
        self.reviews = json.loads((root / release["reviews"]).read_text())

    def test_current_release_is_exactly_reviewed(self):
        validate_reviews(self.dataset, self.reviews)

    def test_changed_or_unreviewed_content_is_rejected(self):
        for field in ("title", "summary", "sourceURL", "policyStatus"):
            changed = copy.deepcopy(self.dataset)
            changed["policies"][0][field] += " changed"
            with self.assertRaises(ValueError):
                validate_reviews(changed, self.reviews)
        for key in ("policies", "retiredPolicyIDs"):
            changed = copy.deepcopy(self.dataset)
            changed[key].pop()
            with self.assertRaises(ValueError):
                validate_reviews(changed, self.reviews)

    def test_news_only_confirmation_is_rejected(self):
        self.reviews["reviews"][0]["officialSourceURL"] = "https://www.stuff.co.nz/politics/example"
        with self.assertRaises(ValueError):
            validate_reviews(self.dataset, self.reviews)

    def test_held_content_cannot_be_published(self):
        held = next(r for r in self.reviews["reviews"] if r["decision"] == "hold")
        self.dataset["policies"].append(held["input"])
        with self.assertRaises(ValueError):
            validate_reviews(self.dataset, self.reviews)


if __name__ == "__main__":
    unittest.main()

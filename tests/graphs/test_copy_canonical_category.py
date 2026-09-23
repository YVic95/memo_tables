import uuid

import pytest

from graphs.nodes.copy_canonical_category import copy_canonical_category_node


class TestCopyCanonicalCategoryNode:
    def test_copies_word_category_from_the_catalog_entry(
        self, db_session, canonical_rule
    ):
        result = copy_canonical_category_node(
            {
                "db": db_session,
                "canonical_rule_id": canonical_rule.id,
            }
        )

        assert result["word_category_id"] == canonical_rule.word_category_id
        assert result["canonical_rule_id"] == canonical_rule.id

    def test_raises_when_the_catalog_entry_does_not_exist(self, db_session):
        with pytest.raises(ValueError):
            copy_canonical_category_node(
                {
                    "db": db_session,
                    "canonical_rule_id": uuid.uuid4(),
                }
            )

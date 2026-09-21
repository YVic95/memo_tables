# Re-runnable loader that syncs the canonical rule catalog YAML files
# (one per language pair, at data/canonical_rules/<native>-<target>.yaml)
# into the canonical_rules table.
#
# Upserts entries by language pair + slug, reactivates entries present in the
# file, and deactivates entries removed from it. Never hard-deletes.
#
# Usage:
#   uv run python scripts/load_canon.py                # sync all catalog files
#   uv run python scripts/load_canon.py data/canonical_rules/en-es.yaml

import argparse
import os
import sys
import glob

import yaml
from sqlalchemy.orm import Session

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from crud.canonical_rules import (
    deactivate_canonical_rules_not_in,
    upsert_canonical_rule,
)
from crud.languages import get_language_by_code
from crud.rules import get_word_category_by_slug
from database import SessionLocal

CATALOGS_DIR = os.path.join(_REPO_ROOT, "data", "canonical_rules")

def load_catalog_yaml(path: str) -> dict:
    with open(path) as catalog_file:
        return yaml.safe_load(catalog_file)


def sync_catalog_from_document(db: Session, document: dict) -> None:
    native_language = get_language_by_code(db, document["native_language"])
    target_language = get_language_by_code(db, document["target_language"])
    if native_language is None or target_language is None:
        raise ValueError(
            "Unresolved language code in catalog: "
            f"native={document['native_language']}, target={document['target_language']}"
        )

    active_slugs = set()
    for entry in document["rules"]:
        category = get_word_category_by_slug(db, entry["category"])
        if category is None:
            raise ValueError(
                f"Unknown word category slug '{entry['category']}' in catalog rule '{entry.get('slug')}'"
            )
        upsert_canonical_rule(
            db,
            native_language_id=native_language.id,
            target_language_id=target_language.id,
            word_category_id=category.id,
            level=entry["level"],
            name=entry["name"],
            description=entry["description"],
            position=entry["position"],
            slug=entry["slug"],
        )
        active_slugs.add(entry["slug"])

    deactivate_canonical_rules_not_in(
        db,
        native_language_id=native_language.id,
        target_language_id=target_language.id,
        active_slugs=active_slugs,
    )

def sync_catalog_file(db: Session, path: str) -> None:
    document = load_catalog_yaml(path)
    sync_catalog_from_document(db, document)
    db.commit()
    print(f"Synced {path} "
          f"({document['native_language']}->{document['target_language']}), "
          f"{len(document['rules'])} rules")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync canonical rule catalog YAML files into canonical_rules."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Sync a single catalog file. Defaults to all *.yaml files in data/canonical_rules.",
    )
    args = parser.parse_args()

    if args.path is not None:
        paths = [args.path]
    else:
        paths = sorted(glob.glob(os.path.join(CATALOGS_DIR, "*.yaml")))
        if not paths:
            parser.error(f"No catalog YAML files found in {CATALOGS_DIR}")

    with SessionLocal() as db:
        for path in paths:
            sync_catalog_file(db, path)

if __name__ == "__main__":
    main()
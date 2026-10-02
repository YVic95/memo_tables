"""Rule text the duplicate-detection tests measure against.

These are the descriptions the English->Spanish catalog ships in
`data/canonical_rules/en-es.yaml`, copied verbatim rather than read from the
file. The tests are about the matching pipeline, not the catalog's contents, so
they need text that does not move when the curriculum is edited — but the copy
means a divergence from the YAML would go unnoticed, so keep these in step with
it.

The trigram scores these produce against each other are pinned against
`pg_trgm` 1.6 in `tests/test_pg_trgm.py`.
"""

SER_VS_ESTAR_DESCRIPTION = (
    "Spanish uses ser for permanent or essential qualities, origin, and profession, "
    "and estar for temporary states, locations, and ongoing conditions. Note the "
    "contrast: la manzana es verde (the apple is green by nature) vs. la manzana "
    "está verde (the apple is unripe)."
)

REFLEXIVE_VERBS_DESCRIPTION = (
    "Spanish reflexive verbs describe actions the subject performs on itself and "
    "use the reflexive pronouns me, te, se, nos, os, se, as in me lavo (I wash "
    "myself), se levanta (he gets up), and nos vestimos (we get dressed)."
)

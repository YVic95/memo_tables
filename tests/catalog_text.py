"""Catalog text the matching tests measure against.

These are the names and descriptions the English->Spanish catalog ships in
`data/canonical_rules/en-es.yaml`, copied verbatim rather than read from the
file. The tests are about the matching pipeline, not the catalog's contents, so
they need text that does not move when the curriculum is edited — but the copy
means a divergence from the YAML would go unnoticed, so keep these in step with
it.

Trigram scores for the description pairs are pinned against `pg_trgm` 1.6 in
`tests/test_pg_trgm.py`. The name-versus-description scores that
`tests/crud/test_canonical_rules.py` quotes are measured with the `similarity()`
stand-in and are not pinned there, so re-check them against live Postgres
(`PG_TRGM_LIVE_CHECK=1`) if the stand-in in `tests/pg_trgm.py` ever changes.
"""

SER_VS_ESTAR_NAME = "Ser vs. estar"

SER_VS_ESTAR_DESCRIPTION = (
    "Spanish uses ser for permanent or essential qualities, origin, and profession, "
    "and estar for temporary states, locations, and ongoing conditions. Note the "
    "contrast: la manzana es verde (the apple is green by nature) vs. la manzana "
    "está verde (the apple is unripe)."
)

REFLEXIVE_VERBS_NAME = "Reflexive verbs"

REFLEXIVE_VERBS_DESCRIPTION = (
    "Spanish reflexive verbs describe actions the subject performs on itself and "
    "use the reflexive pronouns me, te, se, nos, os, se, as in me lavo (I wash "
    "myself), se levanta (he gets up), and nos vestimos (we get dressed)."
)

PRESENT_TENSE_ER_NAME = "Present tense regular -er conjugation"

PRESENT_TENSE_ER_DESCRIPTION = (
    "Regular Spanish verbs ending in -er (comer, beber, aprender) drop the -er "
    "and add -o, -es, -e, -emos, -éis, -en in the present tense."
)

PRESENT_TENSE_IR_NAME = "Present tense regular -ir conjugation"

PRESENT_TENSE_IR_DESCRIPTION = (
    "Regular Spanish verbs ending in -ir (vivir, escribir, abrir) drop the -ir "
    "and add -o, -es, -e, -imos, -ís, -en in the present tense."
)

async function generateTable(ruleId, languagePairId) {
    const result = await fetch('/api/generate-table', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grammar_rule_id: ruleId, language_pair_id: languagePairId }),
    });

    if (!result.ok) {
        const err = await result.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to generate tables');
    }

    const data = await result.json();
    console.log('Table generated:', data);
    return data;
}

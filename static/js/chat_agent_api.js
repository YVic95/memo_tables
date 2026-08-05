// calls the create-rule-agent
async function callAgent(payload) {
    const loader = document.getElementById('loader');

    loader.classList.add('htmx-request');

    const selectedPair = document.getElementById('language-pair-select')?.value;

    try {
        const result = await fetch('/api/create-rule-agent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...payload, language_pair_id: selectedPair }),
        });

        if (!result.ok) {
            const error = await result.json();
            throw new Error(error.detail || 'Agent request failed');
        }

        return result.json();
    } finally {
        loader.classList.remove('htmx-request');
    }

}

const NODE_LABELS = {
    categorize: 'Categorizing rule',
    persist_rule: 'Saving rule',
    translate_rule: 'Translating',
    persist_translation: 'Saving translation',
    generate_content: 'Generating content',
};

const NODE_ORDER = ['categorize', 'persist_rule', 'translate_rule', 'persist_translation', 'generate_content'];

async function callAgentStream(payload, onEvent) {
    const selectedPair = document.getElementById('language-pair-select')?.value;

    const response = await fetch('/api/create-rule-agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, language_pair_id: selectedPair }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Agent request failed');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = "";
    while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split("\n\n");
        buffer = events.pop();

        for (const event of events) {
            let eventType = null;
            let data = null;

            for (const line of event.split("\n")) {
                if (line.startsWith("event: ")) {
                    eventType = line.slice(7);
                } else if (line.startsWith("data: ")) {
                    data = JSON.parse(line.slice(6));
                }
            }

            if (eventType && data) {
                onEvent(eventType, data);
            }
        }
    }
}

function createProgressContainer() {
    const container = document.createElement('div');
    container.className = 'agent-progress';

    const title = document.createElement('div');
    title.className = 'agent-progress-title';
    title.textContent = 'Creating your rule...';

    const steps = document.createElement('div');
    steps.className = 'agent-progress-steps';

    NODE_ORDER.forEach(node => {
        const step = document.createElement('div');
        step.className = 'agent-progress-step';
        step.dataset.node = node;

        const icon = document.createElement('span');
        icon.className = 'step-icon';

        const label = document.createElement('span');
        label.className = 'step-label';
        label.textContent = NODE_LABELS[node];

        step.append(icon, label);
        steps.appendChild(step);
    });

    container.append(title, steps);
    return container;
}

function updateProgress(container, completedNodes, activeNode) {
    const steps = container.querySelectorAll('.agent-progress-step');
    steps.forEach(step => {
        const node = step.dataset.node;
        step.classList.remove('active', 'completed');

        if (completedNodes.has(node)) {
            step.classList.add('completed');
            step.querySelector('.step-icon').innerHTML = '<i class="fa-solid fa-check"></i>';
        } else if (node === activeNode) {
            step.classList.add('active');
            step.querySelector('.step-icon').innerHTML = '<i class="fa-solid fa-spinner fa-spin-pulse"></i>';
        } else {
            step.querySelector('.step-icon').innerHTML = '';
        }
    });
}

function markProgressComplete(container) {
    const title = container.querySelector('.agent-progress-title');
    if (title) {
        title.textContent = 'Rule created';
    }

    container.classList.add('agent-progress-done');

    const steps = container.querySelectorAll('.agent-progress-step');
    steps.forEach(step => {
        step.classList.remove('active');
        step.classList.add('completed');
        step.querySelector('.step-icon').innerHTML = '<i class="fa-solid fa-check"></i>';
    });
}

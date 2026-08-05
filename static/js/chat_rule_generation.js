async function onRuleSelected(item, list, rule) {
    if (list.querySelector('.proposed-rule-selected')) {
        return;
    }

    item.classList.add('proposed-rule-selected');

    dismissOtherRules(list, item);

    const progressContainer = createProgressContainer();
    appendToChat(progressContainer);

    try {
        const completedNodes = new Set();
        let finalResult = null;
        let serverError = null;

        await callAgentStream({
            type: 'initial_rule',
            title: rule.title,
            explanation: rule.explanation,
        }, (eventType, data) => {
            if (eventType === 'node_start') {
                updateProgress(progressContainer, completedNodes, data.node);
            } else if (eventType === 'node_complete') {
                completedNodes.add(data.node);
                updateProgress(progressContainer, completedNodes, null);
            } else if (eventType === 'done') {
                finalResult = data;
            } else if (eventType === 'error') {
                console.warn("Error while processing")
                serverError = data;
            }
        });

        // Keep the progress bar in place, just mark it as finished
        markProgressComplete(progressContainer);

        if (finalResult) {
            appendFullRule(finalResult, rule);
        } else if (serverError) {
            console.error('Agent stream reported an error:', serverError);
            appendStreamError(serverError.message || 'Something went wrong while creating the rule.');
        } else {
            console.warn('Stream finished without a "done" event; nothing to append.');
            appendStreamError('The connection ended before the rule finished generating. Please try again.');
        }
    } catch (err) {
        console.error('Failed to initialize rule:', err);
        markProgressComplete(progressContainer);
        appendStreamError('Something went wrong while creating the rule.');
    }
}

function dismissOtherRules(list, selectedItem) {
    list.querySelectorAll('.proposed-rule').forEach(item => {
        if (item === selectedItem) return;

        item.classList.add('proposed-rule-dismissed');

        item.addEventListener(
            'transitionend',
            () => item.remove(),
            { once: true }
        );
    });
}

function appendFullRule(reply, originalRule) {
    const fullRule = document.createElement('div');
    fullRule.className = 'full-rule-content';

    const body = document.createElement('div');
    body.className = 'full-rule-body';
    body.innerHTML = markdownToHtml(reply.full_content ?? '');

    const saveBtn = document.createElement('button');
    saveBtn.className = 'save-button';
    saveBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Rule';
    saveBtn.addEventListener('click', async () => {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin-pulse"></i> Saving...';
        try {
            const result = await fetch(`/api/grammar-rules/${reply.grammar_rule_id}/append-content`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: reply.full_content }),
            });
            if (!result.ok) {
                const err = await result.json().catch(() => ({}));
                throw new Error(err.detail || 'Failed to save');
            }
            saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> Saved';
            const tableBtn = document.getElementById('generate-table-btn');
            if (tableBtn) {
                tableBtn.dataset.ruleId = reply.grammar_rule_id;
                tableBtn.classList.remove('hidden-button');
            }
        } catch (err) {
            console.error('Failed to save rule:', err);
            saveBtn.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Error';
            saveBtn.disabled = false;
        }
    });

    fullRule.append(body, saveBtn);
    appendToChat(fullRule);
}

function appendStreamError(message) {
    const errorEl = document.createElement('div');
    errorEl.className = 'full-rule-error';
    errorEl.textContent = message;
    appendToChat(errorEl);
}

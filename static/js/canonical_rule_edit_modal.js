// Show the edit-rule modal once its fragment has been swapped in.
function showEditRuleModal() {
    const overlay = document.getElementById('canonical-rule-edit-modal-overlay');
    if (overlay) {
        overlay.classList.add('show');
    }
}

function closeEditRuleModal() {
    const overlay = document.getElementById('canonical-rule-edit-modal-overlay');
    if (overlay) {
        overlay.classList.remove('show');
    }
    const container = document.getElementById('canonical-rule-edit-modal-container');
    if (container) {
        container.innerHTML = '';
    }
}

document.body.addEventListener('htmx:afterSettle', function() {
    const container = document.getElementById('canonical-rule-edit-modal-container');
    if (container?.innerHTML?.includes('canonical-rule-edit-modal-overlay')) {
        showEditRuleModal();
    }
});

document.addEventListener('click', function(e) {
    if (e.target.id === 'close-canonical-rule-edit-modal') {
        closeEditRuleModal();
        return;
    }
    // Clicking the overlay itself (outside the modal box) closes it.
    if (e.target.id === 'canonical-rule-edit-modal-overlay') {
        closeEditRuleModal();
    }
});

document.addEventListener('keydown', function(e) {
    const overlay = document.getElementById('canonical-rule-edit-modal-overlay');
    if (e.key === 'Escape' && overlay?.classList.contains('show')) {
        closeEditRuleModal();
    }
});

// Let validation errors (400) swap into the modal's error container.
document.body.addEventListener('htmx:beforeSwap', function(e) {
    if (
        e.detail.xhr &&
        e.detail.xhr.status === 400 &&
        e.detail.target &&
        e.detail.target.id === 'canonical-rule-edit-error'
    ) {
        e.detail.shouldSwap = true;
    }
});

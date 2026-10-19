// Show the canonical-rule form when "Create canonical rule" button is clicked
document.addEventListener('click', function(e) {
    if (e.target.closest('#create-canonical-rule')) {
        const button = e.target.closest('#create-canonical-rule');
        const form = document.getElementById('canonical-rule-form');
        if (form) {
            form.classList.remove('hidden');
            button.disabled = true;
        }
    }
});

document.body.addEventListener('htmx:beforeSwap', function(e) {
    if (
        e.detail.xhr &&
        e.detail.xhr.status === 400 &&
        e.detail.target &&
        e.detail.target.id === 'canonical-rule-form-error'
    ) {
        e.detail.shouldSwap = true;
    }
});

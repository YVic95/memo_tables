// Function to show the modal when it's loaded
function showModal() {
    const modalOverlay = document.getElementById('add-language-modal-overlay');
    if (modalOverlay) {
        modalOverlay.classList.add('show');
    }
}

function closeAddLanguageModal() {
    const modalOverlay = document.getElementById('add-language-modal-overlay');
    if (modalOverlay) {
        modalOverlay.classList.remove('show');
    }
    const modalContainer = document.getElementById('add-language-modal-container');
    if (modalContainer) {
        modalContainer.innerHTML = "";
    }
}

// Override htmx's default behavior to show the modal after it's loaded
document.body.addEventListener('htmx:afterSettle', function(evt) {
    const modalContainer = document.getElementById('add-language-modal-container');
    if (modalContainer?.innerHTML?.includes('add-language-modal-overlay')) {
        showModal();
    }
});

function cancelAddLanguage(targetId) {
    document.getElementById(targetId).value = "";
    closeAddLanguageModal();
}

// Delegated handlers — work regardless of when the modal HTML is injected
document.addEventListener('click', function(e) {
    if (e.target.id === 'close-modal-button') {
        closeAddLanguageModal();
        return;
    }
    // Click on the overlay itself (outside the modal content box)
    if (e.target.id === 'add-language-modal-overlay') {
        closeAddLanguageModal();
    }
});

document.addEventListener('keydown', function(e) {
    const modalOverlay = document.getElementById('add-language-modal-overlay');
    if (e.key === 'Escape' && modalOverlay && modalOverlay.classList.contains('show')) {
        closeAddLanguageModal();
    }
});
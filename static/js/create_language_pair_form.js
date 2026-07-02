// Show the language form when "Create language pair" button is clicked
document.addEventListener('click', function(e) {
    if (e.target.closest('#create-language-pair')) {
        const button = e.target.closest('#create-language-pair');
        const form = document.querySelector('.language-form');
        if (form) {
            form.classList.remove('hidden');
            button.disabled = true;
        }
    }
});
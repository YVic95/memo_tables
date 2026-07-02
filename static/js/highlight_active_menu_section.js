// background for active menu item
const currentPath = globalThis.location.pathname;
document.querySelectorAll('.sidebar li a').forEach(a => {
    if (a.getAttribute('href') === currentPath) {
        a.closest('li').classList.add('active');
    }
});

// background when user clicks on the new menu item
document.querySelectorAll('.sidebar li').forEach(li => {
    li.addEventListener('click', () => {
        document.querySelectorAll('.sidebar li').forEach(l => l.classList.remove('active'));
        li.classList.add('active');
    });
});

// Show the language form when "Create language pair" button is clicked
const createButton = document.getElementById('create-language-pair');
if (createButton) {
    createButton.addEventListener('click', function() {
        const form = document.querySelector('.language-form');
        if (form) {
            form.classList.remove('hidden');
            this.disabled = true;
        }
    });
}

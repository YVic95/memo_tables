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
document.addEventListener('DOMContentLoaded', function() {
    console.log('dom loaded');
    const createButton = document.getElementById('create-language-pair');
    console.log(createButton)
    if (createButton) {
        createButton.addEventListener('click', function() {
            console.log('click event')
            const form = document.querySelector('.language-form');
            if (form) {
                console.log("form exists")
                form.classList.remove('hidden');
                this.disabled = true;
            }
        });
    }
});

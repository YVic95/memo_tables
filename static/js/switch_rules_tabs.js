document.body.addEventListener('htmx:load', function (event) {
    const container = event.target;

    const tabButtons = container.querySelectorAll('.tab-button');
    const tabPanes = container.querySelectorAll('.tab-pane');

    tabButtons.forEach(button => {
        button.addEventListener('click', function () {
            const tabId = this.dataset.tab;

            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));

            this.classList.add('active');
            document.getElementById(`${tabId}-tab`)?.classList.add('active');
        });
    });
});
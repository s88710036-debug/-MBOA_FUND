document.addEventListener('DOMContentLoaded', function() {
    document.body.classList.add('fade-in');

    const forms = document.querySelectorAll('form[data-ajax]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner me-2"></span>Chargement...';
            }
        });
    });

    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });

    document.querySelectorAll('[data-bs-toggle="popover"]').forEach(el => {
        new bootstrap.Popover(el);
    });

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (csrfToken) {
        document.body.addEventListener('htmx:configRequest', function(event) {
            event.detail.headers['X-CSRFToken'] = csrfToken;
        });
    }
});

function confirmAction(message, form) {
    if (confirm(message)) {
        if (form) form.submit();
        return true;
    }
    return false;
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Copié dans le presse-papiers !');
    });
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('fr-FR').format(amount) + ' XAF';
}

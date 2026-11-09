// Shared behaviour for every page that extends base.html.

// ---- Unread message badge in the sidebar ----
(function () {
    const sidebar = document.getElementById('sidebar');
    const badge = document.getElementById('total-messages-count');
    const url = sidebar && sidebar.dataset.unreadUrl;
    if (!url || !badge) return;

    async function updateTotalUnreadCount() {
        try {
            const response = await fetch(url);
            if (!response.ok) return;
            const data = await response.json();
            const count = data.count || 0;
            badge.textContent = count > 0 ? count : '';
            badge.classList.toggle('active', count > 0);
        } catch (error) {
            console.error('Error updating total unread count:', error);
        }
    }

    updateTotalUnreadCount();
    setInterval(updateTotalUnreadCount, 10000);
})();

// ---- Flash messages: auto-dismiss ----
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.flash-messages .alert').forEach(message => {
        setTimeout(() => {
            message.classList.add('fade-out');
            setTimeout(() => message.remove(), 450);
        }, 5000);
    });
});

// ---- Mobile navigation ----
document.addEventListener('click', (event) => {
    if (event.target.closest('[data-nav-toggle]')) {
        document.body.classList.toggle('nav-open');
    } else if (event.target.closest('[data-nav-close]')) {
        document.body.classList.remove('nav-open');
    }
});

// ---- Modals: close on backdrop click or Escape ----
function hideModal(modal) {
    if (modal.id === 'teamMatchesModal') {
        modal.remove();
    } else {
        modal.style.display = 'none';
    }
}

document.addEventListener('mousedown', (event) => {
    if (event.target.classList && event.target.classList.contains('modal')) {
        hideModal(event.target);
    }
});

document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    document.querySelectorAll('.modal').forEach(modal => {
        if (getComputedStyle(modal).display !== 'none') hideModal(modal);
    });
    document.querySelectorAll('.form-popup').forEach(popup => { popup.style.display = 'none'; });
    document.body.classList.remove('nav-open');
});

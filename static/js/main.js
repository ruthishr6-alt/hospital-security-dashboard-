// Main application utilities
document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss alerts after 6 seconds
    const alerts = document.querySelectorAll('.alert-banner');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 400);
        }, 6000);
    });
});

// Quick demo role switcher
function quickSwitchUser(username) {
    fetch(`/api/auth/demo-switch/${username}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            window.location.href = data.redirect_url;
        } else {
            alert('Switch failed: ' + data.message);
        }
    })
    .catch(err => {
        console.error('Role switch error', err);
    });
}

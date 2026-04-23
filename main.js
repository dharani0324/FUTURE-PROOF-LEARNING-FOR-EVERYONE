// Notification toggle
document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('notif-toggle');
    const list = document.getElementById('notif-list');
    if (btn && list) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            list.classList.toggle('show');
            if (list.classList.contains('show')) {
                fetch('/notifications/read', { method:'POST' })
                    .then(() => {
                        const badge = document.querySelector('.notif-badge');
                        if (badge) badge.remove();
                    });
            }
        });
        document.addEventListener('click', function(e) {
            if (!btn.contains(e.target) && !list.contains(e.target)) {
                list.classList.remove('show');
            }
        });
    }

    // Flash auto-dismiss
    document.querySelectorAll('.flash').forEach(function(el) {
        setTimeout(function() { el.style.opacity='0'; el.style.transition='opacity .5s'; setTimeout(function(){el.remove()},500); }, 4000);
    });
});

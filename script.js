// Simple client-side interactions
document.addEventListener('DOMContentLoaded', () => {
    // Auto-hide flash messages after 5 seconds
    const flashes = document.querySelectorAll('.alert');
    if (flashes.length > 0) {
        setTimeout(() => {
            flashes.forEach(flash => {
                flash.style.transition = "opacity 0.5s ease";
                flash.style.opacity = "0";
                setTimeout(() => flash.remove(), 500);
            });
        }, 5000);
    }
});

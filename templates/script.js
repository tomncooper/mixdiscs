// Collapsible playlist functionality
document.addEventListener('DOMContentLoaded', function() {
    const headers = document.querySelectorAll('.playlist-header');
    
    headers.forEach(header => {
        header.addEventListener('click', function() {
            this.classList.toggle('collapsed');
            const content = this.nextElementSibling;
            content.classList.toggle('collapsed');
        });
    });
});

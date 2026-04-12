// Puberty App JS (scoped, safe for production)
document.addEventListener('DOMContentLoaded', function() {
  // Example: Smooth scroll for puberty sections
  document.querySelectorAll('.puberty-scroll-link').forEach(function(link) {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });
});

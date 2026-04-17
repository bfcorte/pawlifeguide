/* PawLife Guide — main.js */

// ── Smooth scroll for anchor links ──
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

// ── Sticky header shadow on scroll ──
const header = document.querySelector('.site-header');
if (header) {
  window.addEventListener('scroll', () => {
    header.style.boxShadow = window.scrollY > 10
      ? '0 4px 24px rgba(0,0,0,0.2)'
      : '0 2px 20px rgba(0,0,0,0.15)';
  }, { passive: true });
}

// ── Lazy image loading fallback ──
if ('loading' in HTMLImageElement.prototype) {
  document.querySelectorAll('img[loading="lazy"]').forEach(img => {
    img.setAttribute('loading', 'lazy');
  });
} else {
  // Fallback for older browsers
  const script = document.createElement('script');
  script.src = 'https://cdnjs.cloudflare.com/ajax/libs/lazysizes/5.3.2/lazysizes.min.js';
  document.body.appendChild(script);
}

// ── Track outbound Amazon links ──
document.querySelectorAll('a[href*="amazon.com"]').forEach(link => {
  link.addEventListener('click', function () {
    if (typeof gtag !== 'undefined') {
      gtag('event', 'click', {
        event_category: 'affiliate',
        event_label: this.href,
        transport_type: 'beacon',
      });
    }
  });
});

// ── Reading progress bar ──
const article = document.querySelector('.post-content');
if (article) {
  const bar = document.createElement('div');
  bar.style.cssText = `
    position: fixed; top: 0; left: 0; height: 3px;
    background: #F97316; z-index: 9999; width: 0%;
    transition: width 0.1s linear;
  `;
  document.body.prepend(bar);

  window.addEventListener('scroll', () => {
    const scrolled = window.scrollY;
    const articleTop = article.offsetTop;
    const articleHeight = article.offsetHeight;
    const windowHeight = window.innerHeight;
    const progress = Math.max(0, Math.min(100,
      ((scrolled - articleTop + windowHeight * 0.3) / articleHeight) * 100
    ));
    bar.style.width = progress + '%';
  }, { passive: true });
}

// ── Back to top button ──
const backToTop = document.createElement('button');
backToTop.innerHTML = '↑';
backToTop.setAttribute('aria-label', 'Back to top');
backToTop.style.cssText = `
  position: fixed; bottom: 32px; right: 32px;
  background: #F97316; color: white;
  border: none; border-radius: 50%;
  width: 44px; height: 44px;
  font-size: 18px; font-weight: 700;
  cursor: pointer; opacity: 0;
  transition: opacity 0.3s, transform 0.2s;
  z-index: 999; box-shadow: 0 4px 16px rgba(249,115,22,0.4);
`;
document.body.appendChild(backToTop);

window.addEventListener('scroll', () => {
  backToTop.style.opacity = window.scrollY > 400 ? '1' : '0';
  backToTop.style.pointerEvents = window.scrollY > 400 ? 'auto' : 'none';
}, { passive: true });

backToTop.addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

/* ============================================================
   main.js — dieu-preuves.fr
   ============================================================ */

/* ── YOUTUBE ────────────────────────────────────────────────── */
// Titres des vidéos pour la modale
const VID_TITLES = {
  'ZiQiRMZ2XQU': 'Dieu, la Science, les Preuves — Légende',
  'ZWzys1gojtA': 'Guénolé vs Bonnassies — Débat complet',
  'ZiNRN20tEQI': '100 raisons de croire en Dieu',
  'fYgRGBczRHk': 'Dieu existe-t-il ? — Lavagna & Frère Paul-Adrien',
  '7IA4XriGeZY': "On prouve l'existence de Dieu — Abbé Raffray",
  'otrqzITuSqE': 'God DOES Exist — Prof. John Lennox, Oxford',
  'UnaAFhybsDk': 'Jésus a-t-il existé ? ONFRAY débunké — Lavagna',
  'TSZXlVF-qVI': 'Is There Evidence of God in Mathematics? — Dr. Soon'
};

function playYT(el, videoId, startSec) {
  var t = startSec ? '&start=' + startSec : '';
  el.innerHTML = '<iframe src="https://www.youtube-nocookie.com/embed/' + videoId + '?autoplay=1' + t + '" frameborder="0" allowfullscreen allow="autoplay; encrypted-media" title="' + (VID_TITLES[videoId] || 'Vidéo') + '"></iframe>';
  el.style.cursor = 'default';
}

function openModal(videoId, startSec) {
  var frame = document.getElementById('vid-modal-frame');
  var title = document.getElementById('vid-modal-title');
  var t = startSec ? '&start=' + startSec : '';
  frame.innerHTML = '<iframe src="https://www.youtube-nocookie.com/embed/' + videoId + '?autoplay=1' + t + '" frameborder="0" allowfullscreen allow="autoplay; encrypted-media" title="' + (VID_TITLES[videoId] || 'Vidéo') + '"></iframe>';
  title.textContent = VID_TITLES[videoId] || 'Vidéo';
  var modal = document.getElementById('vid-modal');
  modal.classList.add('open');
  modal.removeAttribute('hidden');
  document.body.style.overflow = 'hidden';
  document.getElementById('vid-modal').querySelector('.vid-modal-close').focus();
  return false;
}

function closeModal() {
  var modal = document.getElementById('vid-modal');
  modal.classList.remove('open');
  modal.setAttribute('hidden', '');
  document.getElementById('vid-modal-frame').innerHTML = '';
  document.body.style.overflow = '';
}

function closeModalBackdrop(e) {
  if (e.target === document.getElementById('vid-modal')) closeModal();
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeModal();
});

/* ── PROGRESS BAR ───────────────────────────────────────────── */
var progressBar = document.getElementById('progress-bar');
var backTop = document.getElementById('back-top');

window.addEventListener('scroll', function() {
  var scrollTop = window.scrollY;
  var docHeight = document.body.scrollHeight - window.innerHeight;
  progressBar.style.width = ((scrollTop / docHeight) * 100) + '%';
  backTop.classList.toggle('visible', scrollTop > 400);
}, { passive: true });

/* ── MOBILE MENU ────────────────────────────────────────────── */
function toggleMenu() {
  var menu = document.getElementById('mobile-nav');
  var btn = document.getElementById('menu-toggle');
  var isOpen = menu.classList.toggle('open');
  btn.setAttribute('aria-expanded', isOpen);
}
function closeMenu() {
  document.getElementById('mobile-nav').classList.remove('open');
  document.getElementById('menu-toggle').setAttribute('aria-expanded', 'false');
}

/* ── COLLAPSIBLE ─────────────────────────────────────────────── */
function toggleCollapse(header) {
  var section = header.parentElement;
  section.classList.toggle('open');
  var isOpen = section.classList.contains('open');
  header.setAttribute('aria-expanded', isOpen);
}

/* ── ACTIVE NAV HIGHLIGHTING ────────────────────────────────── */
var sections = document.querySelectorAll('section[id]');
var navLinks = document.querySelectorAll('.nav-links a');

var navObserver = new IntersectionObserver(function(entries) {
  entries.forEach(function(entry) {
    if (entry.isIntersecting) {
      var id = entry.target.id;
      navLinks.forEach(function(link) {
        link.classList.remove('active');
        if (link.getAttribute('href') === '#' + id) {
          link.classList.add('active');
        }
      });
    }
  });
}, { threshold: 0.2, rootMargin: '-70px 0px 0px 0px' });

sections.forEach(function(s) { navObserver.observe(s); });

/* ── CARD ENTRANCE ANIMATIONS ───────────────────────────────── */
var animatedCards = document.querySelectorAll('.arg-card, .scientist-card, .fact-item, .video-card');

var cardObserver = new IntersectionObserver(function(entries) {
  entries.forEach(function(entry) {
    if (entry.isIntersecting) {
      entry.target.classList.add('is-visible');
      cardObserver.unobserve(entry.target); // Observe once only
    }
  });
}, { threshold: 0.1 });

animatedCards.forEach(function(card) { cardObserver.observe(card); });

/* ── LAZY LOADING YOUTUBE THUMBNAILS ────────────────────────── */
// Utilise IntersectionObserver pour charger les thumbnails YT
// uniquement quand elles entrent dans le viewport
if ('IntersectionObserver' in window) {
  var lazyImages = document.querySelectorAll('img.yt-lazy[data-src]');
  var imgObserver = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        var img = entry.target;
        img.src = img.getAttribute('data-src');
        img.removeAttribute('data-src');
        imgObserver.unobserve(img);
      }
    });
  }, { rootMargin: '200px' }); // Précharge 200px avant l'entrée dans le viewport

  lazyImages.forEach(function(img) { imgObserver.observe(img); });
} else {
  // Fallback pour navigateurs sans IntersectionObserver
  document.querySelectorAll('img.yt-lazy[data-src]').forEach(function(img) {
    img.src = img.getAttribute('data-src');
  });
}

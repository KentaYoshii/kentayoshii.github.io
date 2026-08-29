document.addEventListener('DOMContentLoaded', function () {
  initThemeToggle();
  initCollectionPage();
  initCoverArt();
  initHomeStats();
  initVimTipsToc();
});

// Inserts a light/dark mode toggle into the site nav. The initial theme is
// already applied synchronously by an inline script in custom-head.html
// (to avoid a flash of the wrong theme); this just wires up the button.
function initThemeToggle() {
  var nav = document.querySelector('.site-nav .trigger') || document.querySelector('.site-nav');
  if (!nav) return;

  var button = document.createElement('button');
  button.type = 'button';
  button.className = 'theme-toggle page-link';
  button.setAttribute('aria-label', 'Toggle dark mode');

  function isDark() {
    return document.documentElement.getAttribute('data-theme') === 'dark';
  }

  function render() {
    button.textContent = isDark() ? '☀️' : '🌙';
  }

  button.addEventListener('click', function () {
    var next = isDark() ? 'light' : 'dark';
    if (next === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    try { localStorage.setItem('theme', next); } catch (e) {}
    render();
  });

  render();
  nav.appendChild(button);
}

// Live search/filter + running stats on the Books/Movies pages.
function initCollectionPage() {
  var page = document.querySelector('[data-collection]');
  if (!page) return;

  var yearBlocks = Array.prototype.slice.call(page.querySelectorAll('.year-block'));
  var searchInput = page.querySelector('.search-input');
  var statsEl = page.querySelector('.stats-summary');

  yearBlocks.forEach(function (block) {
    var countEl = block.querySelector('.year-count');
    if (countEl) {
      countEl.textContent = block.querySelectorAll('li').length;
    }
  });

  function allItems() {
    return Array.prototype.slice.call(page.querySelectorAll('.year-block li'));
  }

  function renderStats(visibleCount, totalCount) {
    if (!statsEl) return;
    if (visibleCount === totalCount) {
      statsEl.textContent = totalCount + (totalCount === 1 ? ' entry' : ' entries') +
        ' across ' + yearBlocks.length + (yearBlocks.length === 1 ? ' log' : ' logs');
    } else {
      statsEl.textContent = 'Showing ' + visibleCount + ' of ' + totalCount + ' entries';
    }
  }

  function applyFilter(query) {
    var items = allItems();
    var visible = 0;
    var q = query.trim().toLowerCase();

    items.forEach(function (li) {
      var match = !q || li.textContent.toLowerCase().indexOf(q) !== -1;
      li.style.display = match ? '' : 'none';
      if (match) visible++;
    });

    yearBlocks.forEach(function (block) {
      var headers = Array.prototype.slice.call(block.querySelectorAll('h2'));
      headers.forEach(function (heading) {
        var list = heading.nextElementSibling;
        if (!list) return;
        var anyVisible = Array.prototype.slice.call(list.querySelectorAll('li')).some(function (li) {
          return li.style.display !== 'none';
        });
        heading.style.display = anyVisible ? '' : 'none';
        list.style.display = anyVisible ? '' : 'none';
      });

      var blockVisible = Array.prototype.slice.call(block.querySelectorAll('li')).some(function (li) {
        return li.style.display !== 'none';
      });
      block.style.display = blockVisible ? '' : 'none';
    });

    renderStats(visible, items.length);
  }

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      applyFilter(searchInput.value);
    });
  }

  applyFilter('');
}

// Fetches the Books/Movies pages and counts their entries to populate the
// home page's live stat pills, so the counts never need manual updating.
function initHomeStats() {
  var hero = document.querySelector('[data-home-stats]');
  if (!hero) return;

  var pills = Array.prototype.slice.call(hero.querySelectorAll('[data-count-source]'));

  pills.forEach(function (pill) {
    var url = pill.getAttribute('data-count-source');
    var valueEl = pill.querySelector('.stat-value');

    fetch(url)
      .then(function (res) { return res.text(); })
      .then(function (html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        var count = doc.querySelectorAll('.year-block li').length;
        if (valueEl) valueEl.textContent = count;
      })
      .catch(function () {
        if (valueEl) valueEl.textContent = '—';
      });
  });
}

// Builds a quick-jump table of contents for the Vim Tips page from its
// existing (kramdown auto-generated) section heading ids.
function initVimTipsToc() {
  var container = document.querySelector('.vim-tips');
  if (!container) return;

  var headings = Array.prototype.slice.call(container.querySelectorAll('h2')).filter(function (h) {
    return !!h.id;
  });
  if (!headings.length) return;

  var toc = document.createElement('nav');
  toc.className = 'toc';
  toc.setAttribute('aria-label', 'Section navigation');

  var list = document.createElement('ul');
  headings.forEach(function (heading) {
    var item = document.createElement('li');
    var link = document.createElement('a');
    link.href = '#' + heading.id;
    link.textContent = heading.textContent;
    item.appendChild(link);
    list.appendChild(item);
  });

  toc.appendChild(list);
  container.insertBefore(toc, container.firstChild);
}

// ---- Cover art (Books/Movies) ----
//
// Loading strategy, since these pages can have hundreds of entries:
//  - Only fetch a cover once its <li> scrolls near the viewport
//    (IntersectionObserver), not on page load. This also means entries
//    hidden by the search filter never fetch until they're shown.
//  - Cap concurrent lookups so we don't fire off hundreds of requests at
//    once (e.g. on a tall viewport or a wide multi-column layout).
//  - Cache resolved (and "not found") results in localStorage, keyed by
//    title/author, so repeat visits are instant and don't re-hit the API.

var COVER_CACHE_PREFIX = 'coverCache:v2:';
var COVER_MAX_CONCURRENT = 4;
var coverQueue = [];
var coverActive = 0;
var coverObserver = null;

function initCoverArt() {
  var page = document.querySelector('[data-collection]');
  if (!page) return;

  var kind = page.getAttribute('data-collection');
  if (kind !== 'books' && kind !== 'movies') return;

  var items = Array.prototype.slice.call(page.querySelectorAll('.year-block li'));
  items.forEach(function (li) {
    var info = kind === 'books' ? parseBookEntry(li) : parseMovieEntry(li);
    if (!info || !info.title) return;

    var wrap = document.createElement('span');
    wrap.className = 'cover-thumb-wrap';

    var fallback = document.createElement('span');
    fallback.className = 'cover-fallback';
    fallback.setAttribute('aria-hidden', 'true');
    fallback.textContent = kind === 'books' ? '📖' : '🎬';
    wrap.appendChild(fallback);

    var textSpan = document.createElement('span');
    textSpan.className = 'entry-text';
    while (li.firstChild) {
      textSpan.appendChild(li.firstChild);
    }

    // Flex layout goes on this inner row, not the <li> itself — setting
    // display:flex directly on an <li> suppresses its bullet marker.
    var row = document.createElement('span');
    row.className = 'entry-row';
    row.appendChild(wrap);
    row.appendChild(textSpan);
    li.appendChild(row);

    observeForCover(li, wrap, kind, info);
  });
}

function parseBookEntry(li) {
  var em = li.querySelector('em');
  if (!em) return null;

  var title = em.textContent.trim();
  var fullText = li.textContent;
  var afterTitle = fullText.slice(fullText.indexOf(title) + title.length);
  var author = afterTitle.replace(/^[\s—-]*by\s+/i, '').trim();
  return { title: title, author: author };
}

function parseMovieEntry(li) {
  var raw = li.textContent.trim();
  var isSeries = /\(\s*tv series\s*\)/i.test(raw) || /\bseason\s+\d+\b/i.test(raw);
  var cleaned = raw
    .replace(/\(\s*tv series\s*\)/ig, '')
    .replace(/\bseason\s+\d+\b/ig, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
  return { title: cleaned || raw, isSeries: isSeries };
}

function getCoverObserver() {
  if (coverObserver !== null) return coverObserver;
  if (typeof IntersectionObserver === 'undefined') {
    coverObserver = false;
    return coverObserver;
  }
  coverObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      coverObserver.unobserve(entry.target);
      var handler = entry.target.coverHandler;
      if (handler) handler();
    });
  }, { rootMargin: '200px 0px' });
  return coverObserver;
}

function observeForCover(li, wrap, kind, info) {
  var handler = function () {
    enqueueCoverFetch(function () {
      return resolveCover(kind, info).then(function (url) {
        applyCover(wrap, url);
      });
    });
  };

  var observer = getCoverObserver();
  if (!observer) {
    handler();
    return;
  }
  li.coverHandler = handler;
  observer.observe(li);
}

function enqueueCoverFetch(task) {
  coverQueue.push(task);
  pumpCoverQueue();
}

function pumpCoverQueue() {
  while (coverActive < COVER_MAX_CONCURRENT && coverQueue.length) {
    var task = coverQueue.shift();
    coverActive++;
    task().catch(function () {}).then(function () {
      coverActive--;
      pumpCoverQueue();
    });
  }
}

function applyCover(wrap, url) {
  if (!url) return;
  var img = document.createElement('img');
  img.className = 'cover-thumb';
  img.alt = '';
  img.loading = 'lazy';
  img.addEventListener('load', function () {
    wrap.classList.add('is-loaded');
  });
  img.addEventListener('error', function () {
    img.remove();
  });
  img.src = url;
  wrap.appendChild(img);
}

function coverCacheKey(kind, info) {
  return kind + ':' + (info.title + '|' + (info.author || '')).toLowerCase();
}

function readCoverCache(key) {
  try {
    var raw = localStorage.getItem(COVER_CACHE_PREFIX + key);
    if (raw === null) return undefined;
    return JSON.parse(raw);
  } catch (e) {
    return undefined;
  }
}

function writeCoverCache(key, value) {
  try {
    localStorage.setItem(COVER_CACHE_PREFIX + key, JSON.stringify(value));
  } catch (e) {}
}

function resolveCover(kind, info) {
  var key = coverCacheKey(kind, info);
  var cached = readCoverCache(key);
  if (cached !== undefined) {
    return Promise.resolve(cached.url);
  }

  var lookup = kind === 'books' ? fetchBookCover(info) : fetchMovieCover(info);
  return lookup
    .then(function (url) {
      writeCoverCache(key, { url: url || null });
      return url;
    })
    .catch(function () {
      writeCoverCache(key, { url: null });
      return null;
    });
}

// Open Library's search API is free, keyless, and CORS-enabled.
function fetchBookCover(info) {
  function search(withAuthor) {
    var params = 'title=' + encodeURIComponent(info.title) +
      (withAuthor && info.author ? '&author=' + encodeURIComponent(info.author) : '') +
      '&limit=1&fields=cover_i';

    return fetch('https://openlibrary.org/search.json?' + params)
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var doc = data && data.docs && data.docs[0];
        if (doc && doc.cover_i) {
          return 'https://covers.openlibrary.org/b/id/' + doc.cover_i + '-M.jpg';
        }
        return null;
      });
  }

  // Title+author is the precise query, but fails whenever Open Library's
  // credited "author" differs from ours (translators, anthology editors,
  // etc.) — a broader title-only search catches those.
  return search(true).then(function (url) {
    return url || (info.author ? search(false) : null);
  });
}

// TMDB (themoviedb.org). Free tier, CORS-enabled. Note: this key is a
// personal, non-commercial API key and is necessarily public in a static
// site's client-side JS (there's no backend to hide it behind) — same as
// any free-tier key embedded in a browser app.
var TMDB_API_KEY = '276b22ca1df85e0ea85564e4b597e81f';
var TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w200';

function fetchMovieCover(info) {
  var term = encodeURIComponent(info.title);

  function search(type, posterField) {
    return fetch('https://api.themoviedb.org/3/search/' + type + '?api_key=' + TMDB_API_KEY + '&query=' + term)
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var result = data && data.results && data.results[0];
        if (result && result.poster_path) {
          return TMDB_IMAGE_BASE + result.poster_path;
        }
        return null;
      });
  }

  // Entries explicitly marked as a series (e.g. "(TV Series)", "Season 2")
  // search TV first, since a movie-search false-positive would otherwise
  // win before we ever tried the TV catalog.
  var first = info.isSeries ? 'tv' : 'movie';
  var second = info.isSeries ? 'movie' : 'tv';

  return search(first).then(function (url) {
    return url || search(second);
  });
}

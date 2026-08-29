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

// Lowercase and strip Latin accents so typing "shogun" finds "Shōgun" and
// "marquez" finds "García Márquez". The range below is the Combining
// Diacritical Marks block, which deliberately excludes the Japanese voiced
// marks (U+3099/U+309A), so kana searches keep working.
function foldForSearch(s) {
  var t = (s || '').toLowerCase();
  return t.normalize ? t.normalize('NFD').replace(/[̀-ͯ]/g, '') : t;
}

// Live search/filter + running stats on the Books/Movies pages.
function initCollectionPage() {
  var page = document.querySelector('[data-collection]');
  if (!page) return;

  var container = page.querySelector('[data-items]');
  if (!container) return;

  var kind = page.getAttribute('data-collection');
  var items = Array.prototype.slice.call(container.querySelectorAll('li'));
  var searchInput = page.querySelector('.search-input');
  var statsEl = page.querySelector('.stats-summary');
  var select = page.querySelector('.group-select');

  var GROUP_NOUN = { author: 'authors', letter: 'letters', year: 'years' };
  var STORAGE_KEY = 'groupBy:' + kind;
  var sections = [];
  var mode = 'none';

  function groupNameFor(li) {
    if (mode === 'author') return li.getAttribute('data-author') || 'Unknown';
    if (mode === 'letter') return li.getAttribute('data-letter') || '#';
    if (mode === 'year') return li.getAttribute('data-year') || 'Undated';
    return null;
  }

  // A null name renders a section with no heading, which is how the ungrouped
  // view keeps the same .year-block styling (multi-column list) as the
  // grouped ones.
  function buildSection(name, lis) {
    var section = document.createElement('section');
    section.className = 'year-block';

    if (name !== null) {
      var heading = document.createElement('h1');
      heading.className = 'year-heading';
      heading.appendChild(document.createTextNode(name + ' '));
      var count = document.createElement('span');
      count.className = 'year-count';
      count.textContent = lis.length;
      heading.appendChild(count);
      section.appendChild(heading);
    }

    var ul = document.createElement('ul');
    lis.forEach(function (li) { ul.appendChild(li); });
    section.appendChild(ul);
    return section;
  }

  function render() {
    // The <li> nodes are moved, never rebuilt, so cover images already loaded
    // (and their IntersectionObservers) survive a regroup.
    container.textContent = '';
    sections = [];

    if (mode === 'none') {
      sections.push(buildSection(null, items));
    } else {
      var groups = Object.create(null);
      var names = [];
      items.forEach(function (li) {
        var name = groupNameFor(li);
        if (!groups[name]) { groups[name] = []; names.push(name); }
        groups[name].push(li);
      });
      // Years read most-recent-first; everything else alphabetically.
      names.sort(function (a, b) {
        return mode === 'year' ? b.localeCompare(a) : a.localeCompare(b);
      });
      names.forEach(function (name) {
        sections.push(buildSection(name, groups[name]));
      });
    }

    sections.forEach(function (s) { container.appendChild(s); });
  }

  function renderStats(visibleCount, totalCount) {
    if (!statsEl) return;
    if (visibleCount !== totalCount) {
      statsEl.textContent = 'Showing ' + visibleCount + ' of ' + totalCount + ' entries';
      return;
    }
    var text = totalCount + (totalCount === 1 ? ' entry' : ' entries');
    var noun = GROUP_NOUN[mode];
    if (noun) {
      text += ' across ' + sections.length + ' ' +
        (sections.length === 1 ? noun.replace(/s$/, '') : noun);
    }
    statsEl.textContent = text;
  }

  function applyFilter(query) {
    var q = foldForSearch(query.trim());
    var visible = 0;

    items.forEach(function (li) {
      // Match against the data attributes rather than the rendered row: the
      // author is not shown when grouping by author, and the visible text
      // carries a trailing date label.
      var haystack = foldForSearch(
        (li.getAttribute('data-title') || '') + ' ' +
        (li.getAttribute('data-author') || '') + ' ' +
        (li.getAttribute('data-year') || '')
      );
      var match = !q || haystack.indexOf(q) !== -1;
      li.style.display = match ? '' : 'none';
      if (match) visible++;
    });

    sections.forEach(function (section) {
      var anyVisible = Array.prototype.slice.call(section.querySelectorAll('li'))
        .some(function (li) { return li.style.display !== 'none'; });
      section.style.display = anyVisible ? '' : 'none';
    });

    renderStats(visible, items.length);
  }

  function setMode(next, persist) {
    mode = next;
    if (persist) {
      try { localStorage.setItem(STORAGE_KEY, next); } catch (e) {}
    }
    render();
    applyFilter(searchInput ? searchInput.value : '');
  }

  var saved = null;
  try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) {}
  if (saved && select && select.querySelector('option[value="' + saved + '"]')) {
    select.value = saved;
  }

  if (select) {
    select.addEventListener('change', function () {
      setMode(select.value, true);
    });
  }

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      applyFilter(searchInput.value);
    });
  }

  setMode(select ? select.value : 'none', false);
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

  var items = Array.prototype.slice.call(page.querySelectorAll('[data-items] li'));
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
  // Read the data attributes rather than the rendered row: the visible text
  // also carries a trailing "· 2025" date label.
  var title = (li.getAttribute('data-title') || '').trim();
  if (!title) return null;

  var author = li.getAttribute('data-author') || '';
  var isbn = li.getAttribute('data-isbn') || '';

  // Strip a trailing "Part N" (e.g. reading a novel in two sittings, logged
  // as "Shogun Part 1"/"Shogun Part 2") for search purposes — catalogs
  // index the work as a single title, so the literal suffix won't match.
  var searchTitle = title.replace(/\s+part\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*$/i, '').trim();

  return { title: searchTitle || title, author: author, isbn: isbn };
}

function parseMovieEntry(li) {
  var raw = (li.getAttribute('data-title') || '').trim();
  if (!raw) return null;
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
  if (info.isbn) return kind + ':isbn:' + info.isbn;
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

// Entries that resolve to the same cache key (e.g. a book logged twice, or
// "Shogun Part 1"/"Part 2" sharing one search title) share a single in-flight
// request instead of each firing its own, even before either has cached.
var coverInFlight = {};

function resolveCover(kind, info) {
  var key = coverCacheKey(kind, info);
  var cached = readCoverCache(key);
  if (cached !== undefined) {
    return Promise.resolve(cached.url);
  }

  if (coverInFlight[key]) {
    return coverInFlight[key];
  }

  var lookup = kind === 'books' ? fetchBookCover(info) : fetchMovieCover(info);
  var promise = lookup
    .then(function (url) {
      writeCoverCache(key, { url: url || null });
      delete coverInFlight[key];
      return url;
    })
    .catch(function () {
      writeCoverCache(key, { url: null });
      delete coverInFlight[key];
      return null;
    });

  coverInFlight[key] = promise;
  return promise;
}

// Open Library's search API is free, keyless, and CORS-enabled.
function fetchBookCover(info) {
  // With an ISBN (most books, via the Goodreads export) the cover is a direct
  // URL — no search request, and no risk of a title/author mismatch. The
  // default=false parameter makes Open Library 404 instead of serving a
  // placeholder image, so the <img> error handler can fall back.
  if (info.isbn) {
    return Promise.resolve(
      'https://covers.openlibrary.org/b/isbn/' + encodeURIComponent(info.isbn) + '-M.jpg?default=false'
    );
  }

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

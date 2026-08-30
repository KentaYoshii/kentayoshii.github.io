document.addEventListener('DOMContentLoaded', function () {
  initThemeToggle();
  initCollectionPage();
  initCoverArt();
  initCoverMosaic();
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
  var sortSelect = page.querySelector('.sort-select');
  var viewButtons = Array.prototype.slice.call(page.querySelectorAll('.view-button'));
  var header = page.querySelector('.collection-header');
  var rail = page.querySelector('.jump-rail');

  // Above this many sections the rail lists initials instead of full names —
  // 230 author chips would be no more navigable than the list itself.
  var RAIL_MAX_NAMES = 12;

  // [plural, singular] — "series" is its own plural, so the summary line
  // cannot just trim a trailing "s".
  var GROUP_NOUN = {
    author: ['authors', 'author'],
    series: ['series', 'series'],
    letter: ['letters', 'letter'],
    year: ['years', 'year']
  };
  // Books with no series collect here, and the bucket sorts last rather than
  // alphabetically among the real series.
  var NO_SERIES = 'Standalone';
  var STORAGE_KEY = 'groupBy:' + kind;
  var SORT_KEY = 'sortBy:' + kind;
  var VIEW_KEY = 'view:' + kind;
  var sections = [];
  var mode = 'none';
  var sortMode = 'title';

  // The document order is already title A-Z (the data files are pre-sorted),
  // so it doubles as the title ordering and as a stable tiebreak for the
  // others.
  items.forEach(function (li, i) { li.__order = i; });

  function groupNameFor(li) {
    if (mode === 'author') return li.getAttribute('data-author') || 'Unknown';
    if (mode === 'series') return li.getAttribute('data-series') || NO_SERIES;
    if (mode === 'letter') return li.getAttribute('data-letter') || '#';
    if (mode === 'year') return li.getAttribute('data-year') || 'Undated';
    return null;
  }

  // '#3' -> 3, and '#0.5' (a novella between books) -> 0.5. Anything
  // unparseable sorts to the end of its series.
  function seriesIndex(li) {
    var v = parseFloat(li.getAttribute('data-series-index'));
    return isNaN(v) ? Infinity : v;
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

  function numAttr(li, name) {
    var v = parseInt(li.getAttribute(name), 10);
    return isNaN(v) ? null : v;
  }

  function sortedItems() {
    if (sortMode === 'title') return items.slice();

    return items.slice().sort(function (a, b) {
      var av, bv;
      if (sortMode === 'date') {
        av = a.getAttribute('data-date') || '';
        bv = b.getAttribute('data-date') || '';
        // Undated entries sort last rather than leading with a blank run.
        if (!av && !bv) return a.__order - b.__order;
        if (!av) return 1;
        if (!bv) return -1;
        if (av !== bv) return av < bv ? 1 : -1;   // newest first
        return a.__order - b.__order;
      }
      av = numAttr(a, 'data-' + sortMode);
      bv = numAttr(b, 'data-' + sortMode);
      if (av === null && bv === null) return a.__order - b.__order;
      if (av === null) return 1;
      if (bv === null) return -1;
      if (av !== bv) return bv - av;             // longest / most recent first
      return a.__order - b.__order;
    });
  }

  function render() {
    // The <li> nodes are moved, never rebuilt, so cover images already loaded
    // (and their IntersectionObservers) survive a regroup.
    container.textContent = '';
    sections = [];

    var ordered = sortedItems();

    if (mode === 'none') {
      sections.push(buildSection(null, ordered));
    } else {
      var groups = Object.create(null);
      var names = [];
      ordered.forEach(function (li) {
        var name = groupNameFor(li);
        if (!groups[name]) { groups[name] = []; names.push(name); }
        groups[name].push(li);
      });
      // Years most-recent-first; everything else alphabetically, except that
      // the catch-all bucket of series-less books always trails the real
      // series. Group order is independent of the sort, which orders items
      // within each group.
      names.sort(function (a, b) {
        if (mode === 'year') return b.localeCompare(a);
        if (mode === 'series') {
          if (a === NO_SERIES) return 1;
          if (b === NO_SERIES) return -1;
        }
        return a.localeCompare(b);
      });
      names.forEach(function (name) {
        var lis = groups[name];
        // Publication order is the only meaningful order inside a series, so
        // it overrides the sort control there. The series-less bucket keeps
        // whatever the sort produced.
        if (mode === 'series' && name !== NO_SERIES) {
          lis = lis.slice().sort(function (a, b) {
            return seriesIndex(a) - seriesIndex(b) || a.__order - b.__order;
          });
        }
        sections.push(buildSection(name, lis));
      });
    }

    sections.forEach(function (s) { container.appendChild(s); });
  }

  // The sticky header overlaps whatever a jump scrolls to, so publish its
  // height for .year-block's scroll-margin-top to subtract.
  function syncStickyHeight() {
    if (!header) return;
    page.style.setProperty('--sticky-h', header.offsetHeight + 'px');
  }

  function sectionLabel(section) {
    var h = section.querySelector('.year-heading');
    return h ? h.childNodes[0].textContent.trim() : '';
  }

  // Rebuilt from the sections still on screen, so searching narrows the rail
  // in step with the list.
  function buildRail() {
    if (!rail) return;
    rail.textContent = '';

    var shown = sections.filter(function (s) {
      return s.style.display !== 'none' && s.querySelector('.year-heading');
    });
    if (shown.length < 2) {
      rail.hidden = true;
      syncStickyHeight();
      return;
    }

    var byName = shown.length <= RAIL_MAX_NAMES;
    var seen = Object.create(null);
    var chips = [];
    shown.forEach(function (section) {
      var name = sectionLabel(section);
      if (!name) return;
      // Non-Latin initials collect under '#', matching how letter_of() in
      // the build scripts buckets them.
      var initial = foldForSearch(name).charAt(0).toUpperCase();
      if (!(initial >= 'A' && initial <= 'Z')) initial = '#';
      var label = byName ? name : initial;
      if (seen[label]) return;       // first section wins the initial
      seen[label] = true;
      chips.push({ label: label, section: section });
    });

    chips.forEach(function (chip) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'jump-chip';
      b.textContent = chip.label;
      b.addEventListener('click', function () {
        syncStickyHeight();
        chip.section.scrollIntoView({ block: 'start', behavior: 'smooth' });
      });
      rail.appendChild(b);
    });

    rail.hidden = chips.length < 2;
    syncStickyHeight();
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
        noun[sections.length === 1 ? 1 : 0];
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
        // So "poirot" finds the 37 Poirot novels, whose own titles never say
        // it, in any grouping.
        (li.getAttribute('data-series') || '') + ' ' +
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
    buildRail();
  }

  function refresh() {
    // Lets CSS drop the per-row author when it is already the section heading.
    container.setAttribute('data-group', mode);
    // Grouping by series pins each section to publication order, so say so by
    // greying the control out rather than letting it look live but inert.
    if (sortSelect) {
      var inert = mode === 'series';
      sortSelect.disabled = inert;
      sortSelect.title = inert
        ? 'Series are always listed in publication order'
        : '';
    }
    render();
    applyFilter(searchInput ? searchInput.value : '');
  }

  function store(key, value) {
    try { localStorage.setItem(key, value); } catch (e) {}
  }

  function read(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }

  function setView(next, persist) {
    container.setAttribute('data-view', next);
    viewButtons.forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.getAttribute('data-view') === next));
    });
    if (persist) store(VIEW_KEY, next);
  }

  function restore(sel, key) {
    var saved = read(key);
    if (saved && sel && sel.querySelector('option[value="' + saved + '"]')) {
      sel.value = saved;
    }
  }

  restore(select, STORAGE_KEY);
  restore(sortSelect, SORT_KEY);

  if (select) {
    select.addEventListener('change', function () {
      mode = select.value;
      store(STORAGE_KEY, mode);
      refresh();
    });
  }

  if (sortSelect) {
    sortSelect.addEventListener('change', function () {
      sortMode = sortSelect.value;
      store(SORT_KEY, sortMode);
      refresh();
    });
  }

  viewButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      setView(button.getAttribute('data-view'), true);
    });
  });

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      applyFilter(searchInput.value);
    });
  }

  mode = select ? select.value : 'none';
  sortMode = sortSelect ? sortSelect.value : 'title';
  setView(read(VIEW_KEY) === 'grid' ? 'grid' : 'list', false);
  refresh();

  // The header's height changes when the controls wrap onto another line.
  window.addEventListener('resize', syncStickyHeight);
}

// Tidies the landing page's decorative cover band: drops jackets Open Library
// has no image for, and fills the film slots, which need a TMDB lookup and so
// cannot be resolved at build time.
function initCoverMosaic() {
  var band = document.querySelector('[data-cover-mosaic]');
  if (!band) return;

  // Open Library serves a 1px image for an unknown ISBN when "default=false"
  // is not honoured, and that stretches into a smear. Treat either as a miss.
  function checkJacket(img) {
    if (!img.naturalWidth || img.naturalWidth < 10) img.remove();
  }

  Array.prototype.forEach.call(band.querySelectorAll('img.mosaic-cover'), function (img) {
    if (img.complete) {
      checkJacket(img);
      return;
    }
    img.addEventListener('load', function () { checkJacket(img); });
    img.addEventListener('error', function () { img.remove(); });
  });

  Array.prototype.forEach.call(band.querySelectorAll('[data-mosaic-movie]'), function (slot) {
    var title = slot.getAttribute('data-mosaic-movie');
    // Shares the collection pages' request queue and localStorage cache, so a
    // poster already fetched on /movies/ costs nothing here.
    enqueueCoverFetch(function () {
      return resolveCover('movies', { title: title, isSeries: false, releaseYear: null })
        .then(function (url) {
          if (!url) {
            slot.remove();
            return;
          }
          var img = document.createElement('img');
          img.className = 'mosaic-cover';
          img.alt = '';
          img.decoding = 'async';
          img.addEventListener('load', function () { slot.hidden = false; });
          img.addEventListener('error', function () { slot.remove(); });
          img.src = url;
          slot.appendChild(img);
        }, function () {
          slot.remove();
        });
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
  // A trailing "(1987)" disambiguates a remake from its original. Pull it out
  // as a release year: TMDB takes it as a search filter, and leaving it in the
  // query text would only make the match worse.
  var yearMatch = raw.match(/\(\s*(1[89]\d\d|20\d\d)\s*\)\s*$/);
  var cleaned = raw
    .replace(/\(\s*tv series\s*\)/ig, '')
    .replace(/\bseason\s+\d+\b/ig, '')
    .replace(/\(\s*(1[89]\d\d|20\d\d)\s*\)\s*$/, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
  return {
    title: cleaned || raw,
    isSeries: isSeries,
    releaseYear: yearMatch ? yearMatch[1] : null
  };
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
      }, function () {
        applyCover(wrap, null);   // a failed lookup still has to settle
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

// "settled" means the lookup is over, however it ended. The loading shimmer
// keys off it, so a miss has to settle too or it would animate forever.
function applyCover(wrap, url) {
  if (!url) {
    wrap.classList.add('is-settled');
    return;
  }
  var img = document.createElement('img');
  img.className = 'cover-thumb';
  img.alt = '';
  img.loading = 'lazy';
  img.addEventListener('load', function () {
    wrap.classList.add('is-loaded', 'is-settled');
  });
  img.addEventListener('error', function () {
    img.remove();
    wrap.classList.add('is-settled');
  });
  img.src = url;
  wrap.appendChild(img);
}

function coverCacheKey(kind, info) {
  if (info.isbn) return kind + ':isbn:' + info.isbn;
  // The release year is part of the key, or a remake and its original would
  // share one entry and therefore one poster.
  return kind + ':' + (info.title + '|' + (info.author || '') +
                       (info.releaseYear ? '|' + info.releaseYear : '')).toLowerCase();
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

  function search(type) {
    // TMDB names the release-year filter differently per catalogue.
    var yearParam = '';
    if (info.releaseYear) {
      yearParam = (type === 'tv' ? '&first_air_date_year=' : '&year=') + info.releaseYear;
    }
    return fetch('https://api.themoviedb.org/3/search/' + type + '?api_key=' + TMDB_API_KEY +
                 '&query=' + term + yearParam)
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

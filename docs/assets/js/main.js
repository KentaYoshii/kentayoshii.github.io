document.addEventListener('DOMContentLoaded', function () {
  initThemeToggle();
  initCollectionPage();
  initBackToTop();
  initCoverArt();
  initCoverMosaic();
  initStatusStrip();
  initVimTipsToc();
  initGallery();
  initMoreMenu();
});

// Inserts a light/dark mode toggle right next to the site title, so it is
// always visible rather than tucked inside the collapsible mobile nav. The
// initial theme is already applied synchronously by an inline script in
// custom-head.html (to avoid a flash of the wrong theme); this just wires up
// the button.
function initThemeToggle() {
  var title = document.querySelector('.site-title');
  if (!title) return;

  var button = document.createElement('button');
  button.type = 'button';
  button.className = 'theme-toggle';
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
  title.insertAdjacentElement('afterend', button);
}

// The "More" dropdown in the site nav (docs/_includes/header.html), which
// groups the less-central pages behind a toggle on desktop. Below $on-palm
// the checkbox-driven .trigger panel is already the "opened menu" and
// main.scss flattens nav-more-menu back into the plain list there, so the
// toggle button is hidden and this never runs on a phone — but it costs
// nothing to leave wired up regardless of viewport width.
function initMoreMenu() {
  var toggle = document.querySelector('.nav-more-toggle');
  var menu = document.querySelector('.nav-more-menu');
  if (!toggle || !menu) return;

  function isOpen() {
    return menu.classList.contains('is-open');
  }

  function close() {
    menu.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
  }

  function open() {
    menu.classList.add('is-open');
    toggle.setAttribute('aria-expanded', 'true');
  }

  toggle.addEventListener('click', function (e) {
    // Without this the same click that opens the menu would immediately
    // reach the document-level listener below and close it again.
    e.stopPropagation();
    if (isOpen()) close(); else open();
  });

  document.addEventListener('click', function (e) {
    if (isOpen() && !menu.contains(e.target)) close();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && isOpen()) close();
  });
}

// A back-to-top button, shown only on a phone (see .back-to-top in the
// stylesheet), where the collection header no longer sticks to the top of the
// viewport. Added to every page rather than just the collections: the travel
// checklist and the vim notes are long enough to want it too, and a page too
// short to scroll never reveals it.
function initBackToTop() {
  var button = document.createElement('button');
  button.type = 'button';
  button.className = 'back-to-top';
  // The glyph is decorative; the label is what a screen reader announces.
  button.setAttribute('aria-label', 'Back to top');
  button.innerHTML = '<span aria-hidden="true">↑</span>';

  button.addEventListener('click', function () {
    // Instant for anyone who has asked for less motion — smooth-scrolling the
    // whole page is a much bigger movement than the fade-in.
    var reduce = window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
    // Scrolling away does not move focus, so a keyboard user would be left
    // at the bottom of the tab order pointing at a button that has just
    // vanished. Hand focus back to the top of the document.
    var target = document.querySelector('.site-title') || document.body;
    target.focus({ preventScroll: true });
  });

  document.body.appendChild(button);

  // A zero-height marker at the very top of the page. Watching whether it has
  // scrolled out of view costs nothing per frame, unlike a scroll handler
  // reading scrollY. The margin delays the button until the first screen is
  // well behind you, so it does not flicker in on a small nudge.
  var sentinel = document.createElement('span');
  sentinel.className = 'back-to-top-sentinel';
  sentinel.setAttribute('aria-hidden', 'true');
  document.body.insertBefore(sentinel, document.body.firstChild);

  function show(visible) {
    button.classList.toggle('is-visible', visible);
  }

  if (typeof IntersectionObserver === 'undefined') {
    // Without the observer the button is simply always available; a permanent
    // one is a smaller failure than none at all.
    show(true);
    return;
  }

  new IntersectionObserver(function (entries) {
    show(!entries[0].isIntersecting);
  }, { rootMargin: '400px 0px 0px 0px' }).observe(sentinel);
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
  var eraGroup = page.querySelector('.era-filter');
  var eraFilter = 'all';

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
  // height for .year-block's scroll-margin-top to subtract. On a phone the
  // header is not sticky and scrolls away with the page, so it overlaps
  // nothing and the offset has to go back to zero — otherwise every jump
  // lands a header's height short of its target. Read the used value rather
  // than re-testing the breakpoint here, so the two cannot drift apart.
  function syncStickyHeight() {
    if (!header) return;
    var sticky = window.getComputedStyle(header).position === 'sticky';
    page.style.setProperty('--sticky-h', (sticky ? header.offsetHeight : 0) + 'px');
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
      if (eraFilter !== 'all' && li.getAttribute('data-era') !== eraFilter) {
        li.style.display = 'none';
        return;
      }
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

  // Tags every entry with the era bucket the filter chips key off, matching
  // the buckets the Stats page colours its spine wall by.
  function decorateEntries() {
    items.forEach(function (li) {
      var pub = numAttr(li, 'data-published');
      var era = 'unknown';
      if (pub !== null) {
        era = pub < 1800 ? 'pre1800'
            : pub < 1900 ? 'c19'
            : pub < 1950 ? 'c20a'
            : pub < 2000 ? 'c20b' : 'c21';
      }
      li.setAttribute('data-era', era);
    });
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

  decorateEntries();
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

  if (eraGroup) {
    // Hidden in the markup so it never shows without its behaviour.
    eraGroup.hidden = false;
    Array.prototype.forEach.call(eraGroup.querySelectorAll('.era-chip'), function (chip) {
      chip.addEventListener('click', function () {
        var era = chip.getAttribute('data-era');
        // Clicking the active chip clears back to everything.
        eraFilter = (eraFilter === era) ? 'all' : era;
        Array.prototype.forEach.call(eraGroup.querySelectorAll('.era-chip'), function (c) {
          c.setAttribute('aria-pressed',
                         String(c.getAttribute('data-era') === eraFilter));
        });
        applyFilter(searchInput ? searchInput.value : '');
      });
    });
  }

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

// Tidies the landing page's decorative cover band, then sets it drifting.
// Every slot is a plain <img> whose URL build_covers.py already resolved, so
// there is nothing to look up here — only broken images to drop.
function initCoverMosaic() {
  var band = document.querySelector('[data-cover-mosaic]');
  if (!band) return;

  // Open Library serves a 1px image for an unknown ISBN when "default=false"
  // is not honoured, and that stretches into a smear. Treat either as a miss.
  //
  // Only ever act on an image that has finished: a loading="lazy" image whose
  // load is still deferred can report complete === true with naturalWidth 0,
  // so testing complete alone deletes every jacket before it loads.
  function settleJacket(img) {
    if (!img.naturalWidth || img.naturalWidth < 10) img.remove();
  }

  var pending = [];

  Array.prototype.forEach.call(band.querySelectorAll('img.mosaic-cover'), function (img) {
    if (img.complete && img.naturalWidth > 0) return;   // already loaded fine
    pending.push(new Promise(function (done) {
      img.addEventListener('load', function () { settleJacket(img); done(); });
      img.addEventListener('error', function () { img.remove(); done(); });
    }));
  });

  // Nothing may be measured until every image has settled: the track's width
  // is still changing while broken jackets are being dropped, and a shift
  // measured mid-flight would leave the loop misaligned forever. The timeout
  // is the guard against one hung image pinning the band still.
  Promise.race([
    Promise.all(pending),
    new Promise(function (done) { setTimeout(done, MOSAIC_SETTLE_TIMEOUT); })
  ]).then(function () { startMosaicDrift(band); });
}

// Pixels per second. Slow enough to read as drift rather than as a carousel;
// the loop length then follows from however wide the set turns out to be.
var MOSAIC_SPEED = 30;
var MOSAIC_SETTLE_TIMEOUT = 8000;

// Turns the settled band into a seamless scrolling loop by duplicating the
// slots and animating the track by exactly one copy's width.
function startMosaicDrift(band) {
  var track = band.querySelector('[data-mosaic-track]');
  var set = band.querySelector('[data-mosaic-set]');
  if (!track || !set) return;

  // Perpetual motion beside text is a real accessibility problem, and a band
  // this decorative is not worth imposing it. Leave the static version.
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var setWidth = set.getBoundingClientRect().width;
  if (!setWidth) return;

  // A set narrower than the window would scroll a gap into view, and there is
  // nothing to reveal anyway — everything already fits.
  if (setWidth <= band.getBoundingClientRect().width) return;

  // The gap between the two copies is part of the distance travelled, or copy
  // two would land one gap short of where copy one started.
  var gap = parseFloat(window.getComputedStyle(track).columnGap) || 0;
  var shift = setWidth + gap;

  var clone = set.cloneNode(true);
  clone.removeAttribute('data-mosaic-set');
  track.appendChild(clone);

  // The static band is centred, which overflows equally on both sides. That
  // leaves the track's right edge only half a window past the frame, so the
  // second copy runs out before the loop restarts and the right-hand side goes
  // blank at the end of every cycle. Anchor it left now that it moves.
  band.classList.add('is-drifting');

  track.style.setProperty('--mosaic-shift', '-' + shift + 'px');
  track.style.setProperty('--mosaic-duration', (shift / MOSAIC_SPEED) + 's');
  track.classList.add('is-drifting');
}

// A fixed location, not the visitor's: this is the author's local time and
// weather, shown the same way to everyone, not something geolocation should
// personalize. Hardcoded here rather than threaded through _config.yml
// because it belongs to this one piece of JS, and a config layer would only
// add indirection.
var STATUS_LAT = 40.7128;
var STATUS_LON = -74.006;
var STATUS_TIMEZONE = 'America/New_York';
var STATUS_PLACE = 'NYC';

// The only API this page still calls at runtime, now that covers are resolved
// at build time. It asks nothing of a static site with no backend: a plain
// GET with no key, no account, no rate-limit bookkeeping.
var WEATHER_URL = 'https://api.open-meteo.com/v1/forecast?latitude=' + STATUS_LAT +
  '&longitude=' + STATUS_LON + '&current_weather=true&temperature_unit=fahrenheit';

// WMO weather codes -> a short readable label. The full set folds many more
// cases than this; a status strip does not need meteorological
// precision, just enough to say something next to the temperature.
var WEATHER_CODES = {
  0: 'clear', 1: 'mostly clear', 2: 'partly cloudy', 3: 'overcast',
  45: 'foggy', 48: 'foggy',
  51: 'drizzling', 53: 'drizzling', 55: 'drizzling',
  56: 'icy drizzle', 57: 'icy drizzle',
  61: 'raining', 63: 'raining', 65: 'raining hard',
  66: 'icy rain', 67: 'icy rain',
  71: 'snowing', 73: 'snowing', 75: 'snowing hard', 77: 'snow grains',
  80: 'rain showers', 81: 'rain showers', 82: 'heavy showers',
  85: 'snow showers', 86: 'snow showers',
  95: 'thunderstorms', 96: 'thunderstorms', 97: 'thunderstorms', 99: 'thunderstorms'
};

// A small hand-picked list rather than a live "inspirational quote" API. Every
// free one tried while building this either had gone dark outright
// (api.quotable.io, once the standard recommendation for this exact use case)
// or was blocked in testing (dummyjson, zenquotes) — a bad sign for a
// dependency this decorative to carry. A short list here can't disappear.
var QUOTES = [
  ['A reader lives a thousand lives before he dies.', 'George R.R. Martin'],
  ['There is no friend as loyal as a book.', 'Ernest Hemingway'],
  ['That’s the thing about books. They let you travel without moving your feet.', 'Jhumpa Lahiri'],
  ['Once you learn to read, you will be forever free.', 'Frederick Douglass'],
  ['A room without books is like a body without a soul.', 'Marcus Tullius Cicero'],
  ['We read to know we are not alone.', 'C.S. Lewis'],
  ['Books are a uniquely portable magic.', 'Stephen King'],
  ['I cannot remember the books I’ve read any more than the meals I have eaten; even so, they have made me.', 'Ralph Waldo Emerson'],
  ['Movies can and do have tremendous influence in shaping young lives.', 'Walt Disney'],
  ['A great film is when the price of the popcorn doesn’t matter.', 'Roger Ebert'],
  ['Cinema is a matter of what’s in the frame and what’s out.', 'Martin Scorsese'],
  ['Film is one of the three universal languages, the other two: mathematics and music.', 'Frank Capra'],
  ['Time you enjoy wasting is not wasted time.', 'Marthe Troly-Curtin'],
  ['The unread story is not a story; it is little black marks on wood pulp.', 'Ursula K. Le Guin']
];

// A muted line under the header: local time, current weather, and a quote
// that changes once a day rather than on every reload — a page you open
// three times before noon should show the same line each time.
//
// Every part degrades independently: the clock needs nothing, the weather
// text disappears on a failed fetch, and the quote needs no network at all.
function initStatusStrip() {
  var header = document.querySelector('.site-header');
  if (!header) return;

  var strip = document.createElement('div');
  strip.className = 'status-strip';
  strip.innerHTML =
    '<span class="status-text" data-status-text></span>' +
    '<span class="status-quote" data-status-quote></span>';
  header.insertAdjacentElement('afterend', strip);

  var textEl = strip.querySelector('[data-status-text]');
  var quoteEl = strip.querySelector('[data-status-quote]');

  // A day number in STATUS_TIMEZONE, not the visitor's — the quote should
  // flip at NYC midnight along with everything else in the strip, not at an
  // hour that depends on which timezone happens to load the page.
  var nyDateParts = { year: 2000, month: 1, day: 1 };
  try {
    var parts = new Intl.DateTimeFormat('en-US', {
      timeZone: STATUS_TIMEZONE, year: 'numeric', month: 'numeric', day: 'numeric'
    }).formatToParts(new Date());
    parts.forEach(function (p) {
      if (p.type === 'year') nyDateParts.year = parseInt(p.value, 10);
      if (p.type === 'month') nyDateParts.month = parseInt(p.value, 10);
      if (p.type === 'day') nyDateParts.day = parseInt(p.value, 10);
    });
  } catch (e) { /* unsupported timeZone string; fall back to a fixed date */ }
  // Days since an arbitrary epoch is all a stable index needs — it does not
  // have to be a real day-of-year count, just something that changes by
  // exactly one every day in STATUS_TIMEZONE.
  var dayIndex = Math.floor(Date.UTC(nyDateParts.year, nyDateParts.month - 1, nyDateParts.day) / 86400000);
  var quote = QUOTES[((dayIndex % QUOTES.length) + QUOTES.length) % QUOTES.length];
  quoteEl.textContent = '“' + quote[0] + '” —' + quote[1];

  var clockFormat;
  try {
    clockFormat = new Intl.DateTimeFormat('en-US', {
      hour: 'numeric', minute: '2-digit', timeZone: STATUS_TIMEZONE
    });
  } catch (e) {
    clockFormat = null;   // an unsupported timeZone string; skip the clock rather than throw
  }

  // Set once the weather fetch settles; renderClock() reads it on every tick
  // so a later-arriving forecast updates the line without a second render path.
  var weatherText = null;

  function renderClock() {
    if (!clockFormat) return;
    var time = clockFormat.format(new Date());
    textEl.textContent = time + ' in ' + STATUS_PLACE + (weatherText ? ' · ' + weatherText : '');
  }

  if (clockFormat) {
    renderClock();
    setInterval(renderClock, 15000);
  } else {
    textEl.remove();
  }

  fetch(WEATHER_URL)
    .then(function (res) { return res.json(); })
    .then(function (data) {
      var cw = data && data.current_weather;
      if (!cw) return;
      var label = WEATHER_CODES[cw.weathercode];
      weatherText = Math.round(cw.temperature) + '°F' + (label ? ', ' + label : '');
      renderClock();
    })
    .catch(function () { /* no network, or Open-Meteo is down — clock stands alone */ });
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
// Every URL is already in the page, as a data-cover attribute written by
// scripts/build_covers.py. This used to be a lookup layer — an
// IntersectionObserver to defer requests, a four-at-a-time queue to throttle
// them, a localStorage cache to avoid repeating them, and a TMDB API key
// shipped in the page source because a static site has nowhere to hide one.
// None of that is needed to read an attribute.
//
// What remains is the loading state: the thumbnail is still lazy (natively,
// via loading="lazy"), and the shimmer runs until it either loads or fails.

function initCoverArt() {
  var page = document.querySelector('[data-collection]');
  if (!page) return;

  var kind = page.getAttribute('data-collection');
  if (kind !== 'books' && kind !== 'movies') return;

  var items = Array.prototype.slice.call(page.querySelectorAll('[data-items] li'));
  items.forEach(function (li) {
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

    // No attribute means build_covers.py has not resolved this one yet. The
    // wrap is still built, so the row keeps the same shape as its neighbours
    // — it just shows the placeholder glyph.
    applyCover(wrap, li.getAttribute('data-cover'));
  });
}

// "settled" means the image is done, however it ended. The loading shimmer
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
  // A cached URL can still 404 later — Open Library drops a jacket now and
  // then — so the error path stays.
  img.addEventListener('error', function () {
    img.remove();
    wrap.classList.add('is-settled');
  });
  img.src = url;
  wrap.appendChild(img);
}

// ---- Gallery (grid + tag filter + lightbox) ----
//
// Tags are open-ended (unlike the Books page's fixed five eras), so the chip
// row is built here from whatever data-tags the server-rendered tiles
// actually carry, rather than in Liquid.
function initGallery() {
  var grid = document.querySelector('[data-gallery-grid]');
  if (!grid) return;

  var tiles = Array.prototype.slice.call(grid.querySelectorAll('.gallery-tile'));
  if (!tiles.length) return;

  var filterBar = document.querySelector('[data-tag-filter]');
  var activeTag = 'all';

  function tagsOf(tile) {
    var raw = tile.getAttribute('data-tags') || '';
    return raw ? raw.split(',') : [];
  }

  function applyTagFilter() {
    tiles.forEach(function (tile) {
      var match = activeTag === 'all' || tagsOf(tile).indexOf(activeTag) !== -1;
      tile.style.display = match ? '' : 'none';
    });
  }

  // The lightbox only ever cycles through what is currently visible, so
  // prev/next stay in step with an active tag filter instead of walking
  // through hidden photos.
  function visibleTiles() {
    return tiles.filter(function (t) { return t.style.display !== 'none'; });
  }

  function buildTagFilter() {
    if (!filterBar) return;

    var seen = Object.create(null);
    var allTags = [];
    tiles.forEach(function (tile) {
      tagsOf(tile).forEach(function (tag) {
        if (!tag || seen[tag]) return;
        seen[tag] = true;
        allTags.push(tag);
      });
    });
    if (!allTags.length) return;
    allTags.sort();

    function addChip(label, value) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'tag-chip';
      b.textContent = label;
      b.setAttribute('data-tag', value);
      b.setAttribute('aria-pressed', String(value === 'all'));
      b.addEventListener('click', function () {
        // Clicking the active chip clears back to everything, same
        // interaction as the era-chip filter on the Books page.
        activeTag = (activeTag === value) ? 'all' : value;
        Array.prototype.forEach.call(filterBar.querySelectorAll('.tag-chip'), function (c) {
          c.setAttribute('aria-pressed', String(c.getAttribute('data-tag') === activeTag));
        });
        applyTagFilter();
      });
      filterBar.appendChild(b);
    }

    addChip('All', 'all');
    allTags.forEach(function (tag) { addChip(tag, tag); });
    filterBar.hidden = false;
  }

  var lightbox = document.createElement('div');
  lightbox.className = 'gallery-lightbox';
  lightbox.setAttribute('role', 'dialog');
  lightbox.setAttribute('aria-modal', 'true');
  lightbox.setAttribute('aria-label', 'Photo viewer');
  lightbox.innerHTML =
    '<button type="button" class="lightbox-close" aria-label="Close">&times;</button>' +
    '<button type="button" class="lightbox-prev" aria-label="Previous photo">&lsaquo;</button>' +
    '<img class="lightbox-image" alt="">' +
    '<button type="button" class="lightbox-next" aria-label="Next photo">&rsaquo;</button>' +
    '<div class="lightbox-caption">' +
      '<span class="lightbox-caption-text"></span>' +
      '<span class="lightbox-meta"></span>' +
    '</div>';
  document.body.appendChild(lightbox);

  var lightboxImage = lightbox.querySelector('.lightbox-image');
  var captionText = lightbox.querySelector('.lightbox-caption-text');
  var metaText = lightbox.querySelector('.lightbox-meta');
  var currentIndex = -1;
  var lastFocused = null;

  function show(index) {
    var set = visibleTiles();
    if (!set.length) return;
    currentIndex = (index + set.length) % set.length;
    var tile = set[currentIndex];
    lightboxImage.src = tile.getAttribute('data-image');
    lightboxImage.alt = tile.getAttribute('data-caption') || '';
    captionText.textContent = tile.getAttribute('data-caption') || '';
    metaText.textContent = [tile.getAttribute('data-location'), tile.getAttribute('data-date')]
      .filter(function (v) { return v; })
      .join(' · ');
  }

  function onKeydown(e) {
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowLeft') show(currentIndex - 1);
    else if (e.key === 'ArrowRight') show(currentIndex + 1);
  }

  function open(tile) {
    var index = visibleTiles().indexOf(tile);
    if (index === -1) return;
    lastFocused = document.activeElement;
    lightbox.classList.add('is-open');
    // Stops the page scrolling behind a full-screen overlay.
    document.body.classList.add('gallery-lightbox-open');
    show(index);
    lightbox.querySelector('.lightbox-close').focus();
    document.addEventListener('keydown', onKeydown);
  }

  function close() {
    lightbox.classList.remove('is-open');
    document.body.classList.remove('gallery-lightbox-open');
    document.removeEventListener('keydown', onKeydown);
    // Scrolling to open the lightbox does not move focus back on its own.
    if (lastFocused) lastFocused.focus();
  }

  lightbox.querySelector('.lightbox-close').addEventListener('click', close);
  lightbox.querySelector('.lightbox-prev').addEventListener('click', function () { show(currentIndex - 1); });
  lightbox.querySelector('.lightbox-next').addEventListener('click', function () { show(currentIndex + 1); });
  lightbox.addEventListener('click', function (e) {
    if (e.target === lightbox) close();
  });

  tiles.forEach(function (tile) {
    tile.addEventListener('click', function () { open(tile); });
  });

  buildTagFilter();
  applyTagFilter();
}

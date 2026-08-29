document.addEventListener('DOMContentLoaded', function () {
  initCollectionPage();
  initHomeStats();
  initVimTipsToc();
});

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

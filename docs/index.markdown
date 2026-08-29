---
layout: page
---

<div class="wide-section"><div class="wide-inner">

<section class="hero" data-home-stats>
  <p class="hero-eyebrow">Kenta's Log</p>
  <h1 class="hero-title">Books, movies, and dev notes I don't want to forget.</h1>
  <p class="hero-subtitle">A running log I keep for myself — updated whenever I finish something worth remembering.</p>

  <div class="stats-strip">
    <div class="stat-pill" data-count-source="{{ '/books/' | relative_url }}">
      <span class="stat-value">–</span>
      <span class="stat-label">books logged</span>
    </div>
    <div class="stat-pill" data-count-source="{{ '/movies/' | relative_url }}">
      <span class="stat-value">–</span>
      <span class="stat-label">movies &amp; shows logged</span>
    </div>
  </div>
</section>

<div class="card-grid">
  <a class="link-card" href="{{ '/books/' | relative_url }}">
    <span class="link-card-icon" aria-hidden="true">📚</span>
    <h2>Books</h2>
    <p>Everything I've read, organized by year and searchable.</p>
    <span class="link-card-cta">Browse books →</span>
  </a>
  <a class="link-card" href="{{ '/movies/' | relative_url }}">
    <span class="link-card-icon" aria-hidden="true">🎬</span>
    <h2>Movies</h2>
    <p>Movies and shows I've watched, organized by year and searchable.</p>
    <span class="link-card-cta">Browse movies →</span>
  </a>
  <a class="link-card" href="{{ '/posts/' | relative_url }}">
    <span class="link-card-icon" aria-hidden="true">✍️</span>
    <h2>Posts</h2>
    <p>Occasional writing.</p>
    <span class="link-card-cta">Read posts →</span>
  </a>
  <a class="link-card" href="{{ '/dev/' | relative_url }}">
    <span class="link-card-icon" aria-hidden="true">🛠️</span>
    <h2>Dev Notes</h2>
    <p>Programming notes and cheat sheets, starting with Vim tips.</p>
    <span class="link-card-cta">Browse dev notes →</span>
  </a>
  <a class="link-card" href="{{ '/stats/' | relative_url }}">
    <span class="link-card-icon" aria-hidden="true">📊</span>
    <h2>Stats</h2>
    <p>Pages read, most-read authors, and how far back the shelf goes.</p>
    <span class="link-card-cta">See the numbers →</span>
  </a>
</div>

<section class="home-about">
  <h2>About</h2>
  <p>I'm Kenta. This is a personal log of the books I've read, the movies and
  shows I've watched, and the programming notes I keep having to look up
  again. The book list is kept in sync with Goodreads; everything else is
  written by hand.</p>
</section>

</div></div>

<script src="{{ '/assets/js/main.js' | relative_url }}" defer></script>

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
  <a class="link-card" href="{{ '/dev/' | relative_url }}">
    <span class="link-card-icon" aria-hidden="true">🛠️</span>
    <h2>Dev Notes</h2>
    <p>Programming notes and cheat sheets, starting with Vim tips.</p>
    <span class="link-card-cta">Browse dev notes →</span>
  </a>
</div>

</div></div>

<script src="{{ '/assets/js/main.js' | relative_url }}" defer></script>

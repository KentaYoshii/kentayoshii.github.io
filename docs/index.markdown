---
layout: page
---

<section class="hero" data-home-stats>
  <p class="hero-eyebrow">Kenta's Log</p>
  <h1 class="hero-title">Books, movies, and Vim tricks I don't want to forget.</h1>
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
  <a class="link-card" href="{{ '/vim-tips/' | relative_url }}">
    <span class="link-card-icon" aria-hidden="true">⌨️</span>
    <h2>Vim Tips</h2>
    <p>A personal cheat sheet of Vim tricks worth remembering.</p>
    <span class="link-card-cta">See tips →</span>
  </a>
</div>

<script src="{{ '/assets/js/main.js' | relative_url }}" defer></script>

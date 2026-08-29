---
layout: page
title: Movies
permalink: /movies/
---

<div class="collection-page" data-collection>
  <div class="collection-header">
    <p class="collection-tagline">Movies and shows I've watched, newest first.</p>
    <input type="text" class="search-input" placeholder="Search titles…" aria-label="Search movies">
    <p class="stats-summary" aria-live="polite"></p>
  </div>

  {%- assign sorted_posts = site.categories.movies | sort: 'date' | reverse -%}
  {%- for post in sorted_posts -%}
  <section class="year-block">
    <h1 class="year-heading">{{ post.title }} <span class="year-count"></span></h1>
    {{ post.content }}
  </section>
  {%- endfor -%}
</div>

<script src="{{ '/assets/js/main.js' | relative_url }}" defer></script>

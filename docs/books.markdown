---
layout: page
title: Books
permalink: /books/
---

<div class="wide-section"><div class="wide-inner">
<div class="collection-page" data-collection>
  <div class="collection-header">
    <p class="collection-tagline">Everything I've read, newest first.</p>
    <input type="text" class="search-input" placeholder="Search titles or authors…" aria-label="Search books">
    <p class="stats-summary" aria-live="polite"></p>
  </div>

  {%- assign sorted_posts = site.categories.books | sort: 'date' | reverse -%}
  {%- for post in sorted_posts -%}
  <section class="year-block">
    <h1 class="year-heading">{{ post.title }} <span class="year-count"></span></h1>
    {{ post.content }}
  </section>
  {%- endfor -%}
</div>
</div></div>

<script src="{{ '/assets/js/main.js' | relative_url }}" defer></script>

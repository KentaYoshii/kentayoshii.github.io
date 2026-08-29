---
layout: page
title: Movies
permalink: /movies/
---

<ul class="post-list">
  {%- for post in site.categories.movies -%}
  <li>
    <span class="post-meta">{{ post.date | date: "%Y" }}</span>
    <h2>
      <a class="post-link" href="{{ post.url | relative_url }}">
        {{ post.title | escape }}
      </a>
    </h2>
  </li>
  {%- endfor -%}
</ul>

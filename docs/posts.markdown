---
layout: page
title: Posts
permalink: /posts/
---

{%- comment -%}
Lists posts filed under `categories: posts`. The book and movie logs also live
in _posts but are filed under their own categories, so they stay out of here.
{%- endcomment -%}

{%- assign entries = site.categories.posts -%}

<p class="collection-tagline">Occasional writing.</p>

{%- if entries and entries.size > 0 -%}
<ul class="post-list">
  {%- for post in entries -%}
  <li>
    <span class="post-meta">{{ post.date | date: "%b %-d, %Y" }}</span>
    <h2><a class="post-link" href="{{ post.url | relative_url }}">{{ post.title | escape }}</a></h2>
    {%- if post.excerpt -%}
    <p>{{ post.excerpt | strip_html | truncatewords: 40 }}</p>
    {%- endif -%}
  </li>
  {%- endfor -%}
</ul>
{%- else -%}
<p class="empty-state">Nothing here yet.</p>
{%- endif -%}

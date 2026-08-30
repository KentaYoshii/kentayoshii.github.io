---
layout: page
title: Posts
permalink: /posts/
description: Occasional writing.
---

{%- comment -%}
Lists posts filed under `categories: posts`. The book and movie logs used to
share this folder; they now live in _logs/, which Jekyll does not publish.
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

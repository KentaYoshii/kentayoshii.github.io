---
layout: page
title: Adventure
permalink: /adventure/
redirect_from:
  - /travel/
description: Trails walked and national parks visited.
---

{%- comment -%}
Two different shapes on one page, which is why this is not a single loop:

  - The checklists (site.data.travel) are a finite universe with a visited
    flag — 63 parks, 14 ticked — so they render every item, visited or not.
  - The trail log (site.data.trails) is open-ended. There is no list of every
    trail to tick off, only the ones actually walked, so it renders exactly
    what is in docs/_logs/trails.md and nothing more.

Both are server-rendered; neither needs JavaScript.
{%- endcomment -%}

<div class="wide-section"><div class="wide-inner">
<div class="travel-page">

  {%- for pair in site.data.travel.checklists -%}
  {%- assign checklist = pair[1] -%}
  <section class="park-section">
    <h2>{{ checklist.label }}</h2>
    <p class="collection-tagline">
      {{ checklist.visited }} of {{ checklist.total }} visited.
    </p>

    <div class="park-grid">
      {%- for item in checklist.items -%}
      <div class="park-tile{% if item.visited %} is-visited{% endif %}">
        <span class="park-name">{{ item.name }}</span>
        <span class="park-state">{{ item.subtitle }}</span>
        {%- if item.visited -%}
        <span class="park-stamp">
          {%- if item.month %}{{ item.month | slice: 0, 3 }} {% endif -%}{{ item.year }}
        </span>
        {%- endif -%}
      </div>
      {%- endfor -%}
    </div>
  </section>
  {%- endfor -%}

  {%- assign trails = site.data.trails.trails -%}
  {%- assign summary = site.data.trails.summary -%}
  <section class="park-section trail-section">
    <h2>Trails</h2>

    {%- if summary.total > 0 -%}
    <p class="collection-tagline">
      {{ summary.total }} hike{% if summary.total != 1 %}s{% endif %}
      {%- if summary.distance_mi > 0 %}, {{ summary.distance_mi }} miles{% endif -%}.
    </p>

    {%- comment -%}
    Pre-sorted most recent first by build_trails.py, so a change of year is
    just a change of the year field — no grouping logic needed here.
    {%- endcomment -%}
    {%- assign current_year = "" -%}
    <ul class="trail-list">
      {%- for trail in trails -%}
      {%- if trail.year != current_year -%}
      {%- assign current_year = trail.year -%}
      <li class="trail-year"><span>{{ trail.year }}</span></li>
      {%- endif -%}
      <li class="trail-row">
        {%- if trail.blaze -%}
        {%- comment -%}
        The literal paint on the tree, from OSM's osmc:symbol. Named CSS
        colours and hex both come through as written, so this goes straight
        into a style attribute; anything a browser cannot parse just leaves
        the swatch transparent, which is the same as having no blaze.
        {%- endcomment -%}
        <span class="trail-blaze" style="background: {{ trail.blaze }}"
              title="{{ trail.blaze }} blaze" aria-hidden="true"></span>
        {%- else -%}
        <span class="trail-blaze is-unknown" aria-hidden="true"></span>
        {%- endif -%}

        <span class="trail-text">
          <span class="trail-name">{{ trail.name }}</span>
          {%- if trail.place %}<span class="trail-place">{{ trail.place }}</span>{% endif -%}
        </span>

        <span class="trail-meta">
          {%- if trail.month %}<span class="trail-when">{{ trail.month | slice: 0, 3 }}</span>{% endif -%}
          {%- if trail.distance_text %}<span class="trail-distance">{{ trail.distance_text }}</span>{% endif -%}
          {%- if trail.difficulty %}<span class="trail-tag">{{ trail.difficulty }}</span>{% endif -%}
          {%- if trail.surface %}<span class="trail-tag is-muted">{{ trail.surface }}</span>{% endif -%}
        </span>
      </li>
      {%- endfor -%}
    </ul>
    {%- else -%}
    <p class="collection-tagline">Nothing logged here yet.</p>
    {%- endif -%}
  </section>

</div>
</div></div>

---
layout: page
title: Adventure
permalink: /adventure/
redirect_from:
  - /travel/
description: National parks visited and photographed, and trails walked.
---

{%- comment -%}
A hub, the same shape as /dev/: a card per child page rather than content of
its own.

This page used to hold two unrelated things at once -- a fixed checklist of 63
national parks, and an open-ended log of trails walked. They have now split
into /adventure/parks/ and /adventure/trails/, and the parks page absorbed the
photographs that were at /gallery/, since 34 of the 35 are of national parks
and that page was orphaned from the home page anyway.

The cards carry live counts rather than static blurbs, so the hub says
something rather than only pointing. Same idea as the stats strip on the home
page.
{%- endcomment -%}

{%- assign parks = site.data.travel.checklists.us_national_parks -%}
{%- assign trails = site.data.trails.summary -%}
{%- assign photos = site.data.gallery -%}

<div class="wide-section"><div class="wide-inner">

<p class="collection-tagline">Where I've been on foot, and what it looked like.</p>

<div class="card-grid">
  <a class="link-card" href="{{ '/adventure/parks/' | relative_url }}">
    <span class="link-card-icon" aria-hidden="true">🏞️</span>
    <h2>US National Parks</h2>
    <p>
      {{ parks.visited }} of {{ parks.total }} visited, mapped and ticked off,
      with {{ photos.size }} photograph{% if photos.size != 1 %}s{% endif %}.
    </p>
    <span class="link-card-cta">See the parks →</span>
  </a>
  <a class="link-card" href="{{ '/adventure/trails/' | relative_url }}">
    <span class="link-card-icon" aria-hidden="true">🥾</span>
    <h2>Trails</h2>
    <p>
      {%- if trails.total > 0 -%}
      {{ trails.total }} hike{% if trails.total != 1 %}s{% endif %}
      {%- if trails.distance_mi > 0 %}, {{ trails.distance_mi }} miles{% endif -%},
      newest first.
      {%- else -%}
      Nothing logged yet.
      {%- endif -%}
    </p>
    <span class="link-card-cta">See the trails →</span>
  </a>
</div>

</div></div>

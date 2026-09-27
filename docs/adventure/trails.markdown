---
layout: page
title: Trails
permalink: /adventure/trails/
description: Trails walked, most recent first.
---

{%- comment -%}
Split out of /adventure/, which used to carry this and the national parks
checklist together -- two different shapes with nothing to do with each other.
The parks moved to /adventure/parks/ and took their photographs with them.

Unlike the checklist, this is open-ended: there is no list of every trail to
tick off, only the ones actually walked, so it renders exactly what is in
docs/_logs/trails.md and nothing more. Server-rendered; no JavaScript.
{%- endcomment -%}

{%- assign groups = site.data.trails.groups -%}
{%- assign summary = site.data.trails.summary -%}

<div class="wide-section"><div class="wide-inner">
<div class="travel-page">

  <p class="breadcrumb"><a href="{{ '/adventure/' | relative_url }}">Adventure</a> / Trails</p>

  <section class="park-section trail-section">

    {%- if summary.total > 0 -%}
    <p class="collection-tagline">
      {{ summary.total }} hike{% if summary.total != 1 %}s{% endif %}
      {%- if summary.distance_mi > 0 %}, {{ summary.distance_mi }} miles{% endif -%}
      {%- if summary.elevation_ft > 0 %}, {{ summary.elevation_text }} ft of climbing{% endif -%}.
    </p>

    {%- comment -%}
    build_trails.py hands over the hikes already sorted most recent first and
    cut into groups: consecutive hikes in the same month and park. A park
    heading carries that trip's totals and the park's colour, measured from
    its photographs by build_gallery_thumbs.py. The first (most recent) group
    of each park gets the id that the parks page links to.

    The name links back to the park's photographs, or to its checklist tile
    when there are none. Hikes outside a national park are headed with their
    place and have no link or colour.
    {%- endcomment -%}
    {%- assign render = site.data.gallery_render -%}
    {%- assign current_year = "" -%}
    <ul class="trail-list">
      {%- for group in groups -%}
      {%- if group.year != current_year -%}
      {%- assign current_year = group.year -%}
      <li class="trail-year"><span>{{ group.year }}</span></li>
      {%- endif -%}
      {%- assign tint = nil -%}
      {%- if group.park -%}
        {%- assign slug = group.park | slugify -%}
        {%- assign tint = render.parks[group.park] -%}
        {%- if tint -%}
          {%- capture target %}{{ '/adventure/parks/' | relative_url }}#park-{{ slug }}{% endcapture -%}
        {%- else -%}
          {%- capture target %}{{ '/adventure/parks/' | relative_url }}#chk-{{ slug }}{% endcapture -%}
        {%- endif -%}
      {%- endif -%}
      <li class="trail-group"{% if group.first_of_park %} id="park-{{ slug }}"{% endif %}
          {% if tint %}style="--park-accent: {{ tint.accent }}; --park-accent-dark: {{ tint.accent_dark }}"{% endif %}>
        <div class="trail-park">
          {%- if group.park -%}
          <a class="trail-park-name" href="{{ target }}">{{ group.label }}</a>
          {%- else -%}
          <span class="trail-park-name">{{ group.label | default: "Elsewhere" }}</span>
          {%- endif -%}
          {%- if group.month %}<span class="trail-when">{{ group.month | slice: 0, 3 }}</span>{% endif -%}
          <span class="trail-park-totals">
            {{- group.count }} hike{% if group.count != 1 %}s{% endif -%}
            {%- if group.distance_mi > 0 %} · {{ group.distance_text }} mi{% endif -%}
            {%- if group.elevation_ft > 0 %} · {{ group.elevation_text }} ft{% endif -%}
          </span>
        </div>
        <ul class="trail-group-list">
          {%- for trail in group.trails -%}
          <li class="trail-row">
            <span class="trail-name">{{ trail.name }}</span>
            <span class="trail-meta">
              {%- if trail.distance_text %}<span class="trail-distance">{{ trail.distance_text }}</span>{% endif -%}
              {%- if trail.elevation_text %}<span class="trail-gain">{{ trail.elevation_text }} gain</span>{% endif -%}
            </span>
          </li>
          {%- endfor -%}
        </ul>
      </li>
      {%- endfor -%}
    </ul>
    {%- else -%}
    <p class="collection-tagline">Nothing logged here yet.</p>
    {%- endif -%}
  </section>

</div>
</div></div>

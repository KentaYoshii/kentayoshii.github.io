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
{%- assign records = site.data.trails.records -%}

<div class="wide-section"><div class="wide-inner">
<div class="travel-page" data-photo-sets>

  <p class="breadcrumb"><a href="{{ '/adventure/' | relative_url }}">Adventure</a> / Trails</p>

  <section class="park-section trail-section">

    {%- if summary.total > 0 -%}
    <p class="collection-tagline">
      {{ summary.total }} hike{% if summary.total != 1 %}s{% endif %}
      {%- if summary.distance_mi > 0 %}, {{ summary.distance_mi }} miles{% endif -%}
      {%- if summary.elevation_ft > 0 %}, {{ summary.elevation_text }} ft of climbing{% endif -%}.
    </p>

    {%- comment -%}
    Picked by build_trails.py. Each park name jumps to that park's heading
    further down this page.
    {%- endcomment -%}
    {%- if records.longest or records.climb or records.park -%}
    <dl class="trail-records">
      {%- if records.longest -%}
      <div><dt>Longest</dt><dd>{{ records.longest.name }}, {{ records.longest.text }}
        {%- if records.longest.park %} · <a href="#park-{{ records.longest.park | slugify }}">{{ records.longest.park }}</a>{% endif -%}
      </dd></div>
      {%- endif -%}
      {%- if records.climb -%}
      <div><dt>Most climbing</dt><dd>{{ records.climb.name }}, {{ records.climb.text }}
        {%- if records.climb.park %} · <a href="#park-{{ records.climb.park | slugify }}">{{ records.climb.park }}</a>{% endif -%}
      </dd></div>
      {%- endif -%}
      {%- if records.park -%}
      <div><dt>Most miles</dt><dd><a href="#park-{{ records.park.park | slugify }}">{{ records.park.name }}</a>, {{ records.park.text }}</dd></div>
      {%- endif -%}
    </dl>
    {%- endif -%}

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
    {%- assign photos = site.data.gallery -%}
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
              {%- if trail.photos.size > 0 -%}
              {%- assign set_id = trail.photos.first | split: "." | first | slugify | prepend: "photos-" -%}
              <button type="button" class="trail-photos-toggle" aria-controls="{{ set_id }}"
                      aria-expanded="false" hidden>
                <span aria-hidden="true">📷</span> {{ trail.photos.size }}
              </button>
              {%- endif -%}
              {%- if trail.distance_text %}<span class="trail-distance">{{ trail.distance_text }}</span>{% endif -%}
              {%- if trail.elevation_text %}<span class="trail-gain">{{ trail.elevation_text }} gain</span>{% endif -%}
              {%- comment -%}
              Gain as a share of the biggest climb in the log, in the park's
              colour. Decorative: the figure beside it says the same thing.
              {%- endcomment -%}
              {%- if trail.gain_pct -%}
              <span class="trail-bar" aria-hidden="true"><span style="width: {{ trail.gain_pct }}%"></span></span>
              {%- endif -%}
            </span>
            {%- comment -%}
            The photos taken on this hike, in the same tile markup as the
            parks page so main.js's lightbox handles both. Hidden until the
            button above opens it; the images are lazy, so a closed set costs
            nothing to download. Keep Liquid tags out of the button's
            attribute list -- see the note in parks.markdown.
            {%- endcomment -%}
            {%- if trail.photos.size > 0 -%}
            <div class="trail-photos" id="{{ set_id }}" data-photo-set data-park="{{ group.park }}" hidden>
              {%- for file in trail.photos -%}
              {%- assign photo = photos | where: "image", file | first -%}
              {%- assign shown = render.photos[file] -%}
              {%- assign label = photo.caption | default: trail.name -%}
              <button type="button" class="gallery-tile"
                      data-image="{{ '/assets/gallery/large/' | append: file | relative_url }}"
                      data-caption="{{ label | escape }}"
                      data-park="{{ photo.park }}"
                      data-trail="{{ trail.name | escape }}"
                      data-when="{% if photo.date %}{{ photo.date | date: '%-d %B %Y' }}{% endif %}"
                      data-location="{{ photo.location | escape }}"
                      {% if shown %}style="background-image: url('{{ shown.lqip }}')"{% endif %}>
                <img src="{{ '/assets/gallery/thumbs/' | append: file | relative_url }}"
                     alt="{{ label | escape }}"
                     {% if shown %}width="{{ shown.width }}" height="{{ shown.height }}"{% endif %}
                     loading="lazy" decoding="async">
              </button>
              {%- endfor -%}
            </div>
            {%- endif -%}
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

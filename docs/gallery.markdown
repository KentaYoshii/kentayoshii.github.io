---
layout: page
title: Gallery
permalink: /gallery/
description: National park photographs, grouped by park.
---

{%- comment -%}
Three data files meet here:

  - _data/gallery.yml       the photos, hand-maintained, already in the order
                            the page shows them (see its header).
  - _data/gallery_render.json  written by scripts/build_gallery_thumbs.py:
                            thumbnail dimensions, inline blur-up placeholders,
                            and a colour per park taken from the photographs.
  - _data/travel.json       the same parks as /adventure/, for each one's
                            state and the year it was visited. Joined on
                            `park`, which is why that field has to match
                            travel.json exactly.

Sections are emitted by watching `park` change down the list, the same way
adventure.markdown starts a new year in the trail log, rather than by
group_by: file order is already the wanted order, and this keeps it that way
without depending on how group_by happens to sort.

The grid never references the committed originals. `src` is the 800px
thumbnail and `data-image` the 2000px copy the lightbox loads on demand; the
originals stay in the repo only as the source those are rebuilt from.

Tag chips are built client-side (initGallery() in main.js) from the parks the
photos actually carry, rather than in Liquid here.
{%- endcomment -%}

{%- assign photos = site.data.gallery -%}
{%- assign render = site.data.gallery_render -%}
{%- assign checklist = site.data.travel.checklists.us_national_parks.items -%}

<div class="wide-section"><div class="wide-inner">
<div class="gallery-page">

  {%- if photos.size > 0 -%}
  {%- assign named = photos | where_exp: "photo", "photo.park" -%}
  {%- assign park_count = named | map: "park" | uniq | size -%}
  <p class="collection-tagline">
    {{ photos.size }} photo{% if photos.size != 1 %}s{% endif %} from
    {{ park_count }} national park{% if park_count != 1 %}s{% endif %} —
    the ones I've pointed a camera at, out of the
    <a href="{{ '/adventure/' | relative_url }}">sixty-three on the checklist</a>.
  </p>
  {%- else -%}
  <p class="collection-tagline">Nothing posted here yet.</p>
  {%- endif -%}

  {%- comment -%}
  The hero map. Geometry and marker positions both come from
  _data/gallery_map.json, projected together by scripts/build_gallery_map.py
  so a dot cannot drift away from its state.

  The states are decoration and are hidden from assistive tech; the markers
  are the interactive part, and they are ordinary anchors to the section
  ids below. That makes them focusable and keyboard-operable for free, and
  it means the map still navigates with JavaScript off -- main.js only
  upgrades the jump to a smooth scroll and clears an active filter first.

  Markers are the parks rather than the states on purpose: five states hold
  two parks each, and pinning the link to the park sidesteps having to ask
  which one was meant.
  {%- endcomment -%}
  {%- assign map = site.data.gallery_map -%}
  {%- if map and photos.size > 0 -%}
  {%- assign lit = map.parks | map: "state" | uniq -%}
  <figure class="gallery-map">
    <svg viewBox="0 0 {{ map.view.width }} {{ map.view.height }}"
         class="gallery-map-svg" role="group"
         aria-label="Map of the United States marking the national parks below">
      <g aria-hidden="true">
        {%- for state in map.states -%}
        <path d="{{ state.path }}"
              class="gallery-map-state{% if lit contains state.id %} is-lit{% endif %}"></path>
        {%- endfor -%}
      </g>
      {%- for park in map.parks -%}
      {%- assign tint = render.parks[park.name] -%}
      <a class="gallery-map-pin" href="#park-{{ park.name | slugify }}"
         data-park="{{ park.name }}"
         {% if tint %}style="--park-accent: {{ tint.accent }}; --park-accent-dark: {{ tint.accent_dark }}"{% endif %}>
        <title>{{ park.name }}</title>
        {%- comment -%}
        The wide transparent circle underneath is the hit area. The visible
        dot is 5px on a 960px-wide canvas, which scales down to roughly a
        fingertip-sized nothing on a phone.
        {%- endcomment -%}
        <circle class="gallery-map-hit" cx="{{ park.x }}" cy="{{ park.y }}" r="14"></circle>
        <circle class="gallery-map-dot" cx="{{ park.x }}" cy="{{ park.y }}" r="5"></circle>
      </a>
      {%- endfor -%}
    </svg>
    <figcaption>
      Every park below, where it actually is. Alaska and Hawai&#699;i sit in
      their usual insets.
    </figcaption>
  </figure>
  {%- endif -%}

  <div class="tag-filter" data-tag-filter hidden></div>

  {%- assign current_park = "%%none%%" -%}
  {%- for photo in photos -%}

  {%- if photo.park != current_park -%}
    {%- unless forloop.first -%}
    </div>
    </section>
    {%- endunless -%}
    {%- assign current_park = photo.park -%}

    {%- comment -%}
    Everything below is per-section. `info` is null for a photo with no park,
    which is what puts it in the closing "Elsewhere" group.
    {%- endcomment -%}
    {%- assign info = checklist | where: "name", current_park | first -%}
    {%- assign tint = render.parks[current_park] -%}
    {%- assign in_park = photos | where: "park", current_park | size -%}

  <section class="gallery-park" id="park-{{ current_park | default: 'elsewhere' | slugify }}"
           data-park="{{ current_park }}"
           {% if tint %}style="--park-accent: {{ tint.accent }}; --park-accent-dark: {{ tint.accent_dark }}"{% endif %}>
    <h2 class="gallery-park-head">
      <span class="gallery-park-name">{{ current_park | default: "Elsewhere" }}</span>
      {%- if info.subtitle %}<span class="gallery-park-where">{{ info.subtitle }}</span>{% endif -%}
      {%- if info.year %}<span class="park-stamp">{{ info.year }}</span>{% endif -%}
      <span class="gallery-park-count">
        {%- if current_park -%}
        {{ in_park }} photo{% if in_park != 1 %}s{% endif %}
        {%- else -%}
        not a national park
        {%- endif -%}
      </span>
    </h2>

    <div class="gallery-grid">
  {%- endif -%}

  {%- comment -%}
  `file` is the basename, which is the key gallery_render.json is written
  against and the name both derivatives share.
  {%- endcomment -%}
  {%- assign file = photo.image | split: "/" | last -%}
  {%- assign shown = render.photos[file] -%}
  {%- if photo.caption -%}
    {%- assign label = photo.caption -%}
  {%- elsif photo.park -%}
    {%- assign label = photo.park | append: " National Park" -%}
  {%- else -%}
    {%- assign label = photo.location -%}
  {%- endif -%}

      {%- comment -%}
      The blur-up placeholder goes on the button, not on the img. The img
      starts fully transparent and fades in once it decodes, and opacity
      takes an element's own background with it -- set here, the placeholder
      would be invisible for exactly as long as it is needed.
      {%- endcomment -%}
      <button type="button" class="gallery-tile"
              data-image="{{ '/assets/gallery/large/' | append: file | relative_url }}"
              data-caption="{{ label | escape }}"
              data-park="{{ photo.park }}"
              {%- comment -%}
              The photo's own EXIF date where it has one, falling back to the
              year travel.json records for the visit. Formatted here rather
              than in JavaScript so there is one date format on the site.
              {%- endcomment -%}
              data-when="{% if photo.date %}{{ photo.date | date: '%-d %B %Y' }}{% else %}{{ info.year }}{% endif %}"
              data-tags="{{ photo.tags | join: ' · ' | escape }}"
              data-location="{{ photo.location | escape }}"
              {% if shown %}style="background-image: url('{{ shown.lqip }}')"{% endif %}>
        <img src="{{ '/assets/gallery/thumbs/' | append: file | relative_url }}"
             alt="{{ label | escape }}"
             {% if shown %}width="{{ shown.width }}" height="{{ shown.height }}"{% endif %}
             loading="lazy" decoding="async">
        <span class="gallery-tile-caption" aria-hidden="true">{{ label }}</span>
      </button>

  {%- endfor -%}
  {%- if photos.size > 0 %}
    </div>
  </section>
  {%- endif %}

</div>
</div></div>

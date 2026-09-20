---
layout: page
title: US National Parks
permalink: /adventure/parks/
description: All sixty-three US national parks, which I have been to, and photographs of them.
---

{%- comment -%}
One subject, one page. This used to be split: the checklist lived on
/adventure/ next to an unrelated trail log, and the photographs lived on
/gallery/, which was reachable only from the "More" nav dropdown and was not
linked from the home page at all. Both halves were about the same sixty-three
parks.

Four data files meet here:

  _data/travel.json       the checklist -- all 63 parks and which are visited,
                          generated from _logs/travel.md.
  _data/parks_map.json    written by scripts/build_parks_map.py: the state
                          outlines and a projected point per park, both put
                          through one Albers USA projection so a marker cannot
                          drift away from its state.
  _data/gallery.yml       the photographs, hand-maintained, already in the
                          order the page shows them.
  _data/gallery_render.json  written by scripts/build_gallery_thumbs.py:
                          thumbnail sizes, blur-up placeholders, and a colour
                          per park measured from its own photographs.

They join on the park name, which is why gallery.yml's `park` has to match
travel.json exactly.

The page reads top to bottom as: where they are, which ones I have been to,
and then what they looked like.
{%- endcomment -%}

{%- assign checklist = site.data.travel.checklists.us_national_parks -%}
{%- assign photos = site.data.gallery -%}
{%- assign render = site.data.gallery_render -%}
{%- assign map = site.data.parks_map -%}
{%- assign photographed = photos | map: "park" | uniq -%}

<div class="wide-section"><div class="wide-inner">
<div class="gallery-page travel-page">

  <p class="breadcrumb"><a href="{{ '/adventure/' | relative_url }}">Adventure</a> / US National Parks</p>

  <p class="collection-tagline">
    {{ checklist.visited }} of {{ checklist.total }} visited,
    {{ photos.size }} photograph{% if photos.size != 1 %}s{% endif %} from
    {{ photographed.size }} of them.
  </p>

  {%- comment -%}
  The map. Every park that Albers USA has room for gets a marker: filled for
  visited, hollow for not. A marker is an ordinary anchor, so the map works
  with JavaScript off and is keyboard-operable for free -- main.js only
  upgrades the jump to a smooth scroll. Parks with photographs point at their
  photo section; the rest point at their tile in the checklist, so every dot
  leads somewhere.

  Markers are parks rather than states because several states hold more than
  one, which would otherwise raise the question of which was meant.
  {%- endcomment -%}
  {%- if map -%}
  <figure class="parks-map">
    <svg viewBox="0 0 {{ map.view.width }} {{ map.view.height }}"
         class="parks-map-svg" role="group"
         aria-label="Map of the United States marking every national park">
      <g aria-hidden="true">
        {%- for state in map.states -%}
        <path d="{{ state.path }}" class="parks-map-state"></path>
        {%- endfor -%}
      </g>
      {%- for park in map.parks -%}
      {%- assign item = checklist.items | where: "name", park.name | first -%}
      {%- assign slug = park.name | slugify -%}
      {%- assign has_photos = false -%}
      {%- if photographed contains park.name %}{% assign has_photos = true %}{% endif -%}
      {%- assign tint = render.parks[park.name] -%}
      {%- if has_photos -%}
        {%- assign target = slug | prepend: "#park-" -%}
      {%- else -%}
        {%- assign target = slug | prepend: "#chk-" -%}
      {%- endif -%}
      <a class="parks-map-pin{% if item.visited %} is-visited{% endif %}{% if has_photos %} has-photos{% endif %}"
         href="{{ target }}" data-park="{{ park.name }}"
         {% if tint %}style="--park-accent: {{ tint.accent }}; --park-accent-dark: {{ tint.accent_dark }}"{% endif %}>
        <title>{{ park.name }}{% if item.visited %} — visited {{ item.year }}{% endif %}</title>
        <circle class="parks-map-hit" cx="{{ park.x }}" cy="{{ park.y }}" r="12"></circle>
        <circle class="parks-map-dot" cx="{{ park.x }}" cy="{{ park.y }}" r="4.5"></circle>
      </a>
      {%- endfor -%}
    </svg>
    <figcaption>
      Filled where I've been. Alaska and Hawai&#699;i sit in their usual
      insets; American Samoa and Virgin Islands are national parks too, but
      fall outside this projection and are listed below rather than drawn.
    </figcaption>
  </figure>
  {%- endif -%}

  {%- comment -%}
  The checklist. Every park, visited or not -- a map cannot carry sixty-three
  labels, so this stays the part you actually read names and years off. A
  visited park that has photographs links down to them.
  {%- endcomment -%}
  <section class="park-section">
    <h2>The checklist</h2>
    <div class="park-grid">
      {%- for item in checklist.items -%}
      {%- assign slug = item.name | slugify -%}
      <div class="park-tile{% if item.visited %} is-visited{% endif %}" id="chk-{{ slug }}">
        {%- if photographed contains item.name -%}
        <a class="park-name" href="#park-{{ slug }}">{{ item.name }}</a>
        {%- else -%}
        <span class="park-name">{{ item.name }}</span>
        {%- endif -%}
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

  {%- comment -%}
  The photographs, one section per park. Sections are emitted by watching
  `park` change down the list -- the same way the trail log starts a new year
  -- rather than by group_by, because gallery.yml is already in the order the
  page wants and this keeps it that way.

  The grid never references the full-resolution originals. Those live in
  photo-originals/, outside the site source, and are not published; `src` is
  the 800px thumbnail and `data-image` the 2000px copy the lightbox fetches
  on demand.
  {%- endcomment -%}
  {%- if photos.size > 0 -%}
  <section class="park-section">
    <h2>Photographs</h2>

    <div class="tag-filter" data-tag-filter hidden></div>

    {%- assign current_park = "%%none%%" -%}
    {%- for photo in photos -%}

    {%- if photo.park != current_park -%}
      {%- unless forloop.first -%}
      </div>
      </section>
      {%- endunless -%}
      {%- assign current_park = photo.park -%}
      {%- assign info = checklist.items | where: "name", current_park | first -%}
      {%- assign tint = render.parks[current_park] -%}
      {%- assign in_park = photos | where: "park", current_park | size -%}

    <section class="gallery-park" id="park-{{ current_park | default: 'elsewhere' | slugify }}"
             data-park="{{ current_park }}"
             {% if tint %}style="--park-accent: {{ tint.accent }}; --park-accent-dark: {{ tint.accent_dark }}"{% endif %}>
      <h3 class="gallery-park-head">
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
      </h3>

      <div class="gallery-grid">
    {%- endif -%}

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
    Keep Liquid tags OUT of the attribute list below, and in particular never
    use the hyphenated whitespace-stripping form in among the attributes. It
    strips the newline and indentation on both sides, leaving two attributes
    touching, and kramdown wants whitespace before every attribute name. It
    does not fail loudly: it abandons the start tag and escapes it, so the
    page shows the raw markup as text while the img inside still renders.
    There is a test for this now. Notes on individual attributes:

      data-image   the 2000px copy, fetched only when the lightbox opens.
      data-when    the photograph's own EXIF date, formatted here so there is
                   one date format across the site.
      style        the blur-up placeholder, on the button rather than the img
                   because the img fades in from opacity 0 and opacity takes
                   an element's own background with it.
    {%- endcomment -%}
        <button type="button" class="gallery-tile"
                data-image="{{ '/assets/gallery/large/' | append: file | relative_url }}"
                data-caption="{{ label | escape }}"
                data-park="{{ photo.park }}"
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
      </div>
    </section>
  </section>
  {%- endif -%}

</div>
</div></div>

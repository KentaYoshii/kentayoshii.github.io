---
layout: page
title: Gallery
permalink: /gallery/
description: Photos I've taken.
---

{%- comment -%}
Rendered from docs/_data/gallery.yml, a single hand-maintained list — no
build script needed, unlike books/movies/trails, since a photo needs no
external lookup or free-text date-heading parsing.

Tag chips are built client-side (initGallery() in main.js) from whatever
tags the photos actually carry, rather than in Liquid here: the tag set is
open-ended and unknown at template time, unlike the Books page's fixed five
eras.
{%- endcomment -%}

<div class="wide-section"><div class="wide-inner">
<div class="gallery-page">

  {%- assign photos = site.data.gallery -%}
  <p class="collection-tagline">
    {%- if photos.size > 0 -%}
    {{ photos.size }} photo{% if photos.size != 1 %}s{% endif %}.
    {%- else -%}
    Nothing posted here yet.
    {%- endif -%}
  </p>

  <div class="tag-filter" data-tag-filter hidden></div>

  <div class="gallery-grid" data-gallery-grid>
    {%- for photo in photos -%}
    <button type="button" class="gallery-tile"
            data-image="{{ photo.image | relative_url }}"
            data-caption="{{ photo.caption | escape }}"
            data-date="{{ photo.date }}"
            data-location="{{ photo.location | escape }}"
            data-tags="{{ photo.tags | join: ',' }}">
      <img src="{{ photo.image | relative_url }}" alt="{{ photo.caption | escape }}" loading="lazy">
    </button>
    {%- endfor -%}
  </div>

</div>
</div></div>

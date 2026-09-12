---
layout: page
title: Vim Tips
permalink: /dev/vim-tips/
description: Vim motions, editing commands and shortcuts worth committing to memory.
---

<p class="breadcrumb"><a href="{{ '/dev/' | relative_url }}">Dev Notes</a> / Vim Tips</p>

<div class="vim-tips" markdown="1">

A running personal cheat sheet of Vim tricks worth remembering.

## Motion

- `f{char}` / `t{char}` — jump to (or just before) the next `{char}` on the line; `F`/`T` search backward. Repeat with `;` and reverse with `,`.
- `*` / `#` — jump to the next/previous occurrence of the word under the cursor.
- `%` — jump between matching brackets/parens/braces.
- `gg` / `G` — top/bottom of file; `{n}G` or `:{n}` jumps to line `n`.
- `Ctrl-o` / `Ctrl-i` — hop backward/forward through the jump list (great after a search or `gd`).
- `H` / `M` / `L` — jump to top/middle/bottom of the visible window.
- `g;` / `g,` - move backward/forward in you change list

## Editing

- `cgn` - can be used to selectively replace matches
    - `/` to search for keyword
    - `cgn` and replace the keyword with new word
    - `.` to repeat the edit on the next match. `n` to skip.
- `:normal` - apply normal mode command to many lines easily
    - Flow
        - Select lines
        - `:normal <cmd><ESC>` (:normal I- etc.)
    - You can do 
        - `:%normal <cmd>` (run on every line in a file)
        - `:10,20normal <cmd>` (run on line 10 to 20 in a file)
        - etc.
    - Use this when every line gets the same treatment! 

- `:g/global` to operate on every matching line
    - Let's you run Ex command on every line matching a pattern
        - `:g/pattern/command`
    - Conversely, to perform Ex on lines NOT matching
        - `:v/pattern/command`
    - You can use this with normal too!
        - `:g/pattern/normal <cmd>`

- Edit with motion
    - Think big. Motion such as `/` and `?` can be used with operators such as `c` and `d`!

## Search & Replace

## Registers & Macros

- `Macro` - a way to record a sequence of keystrokes and let you replay it
    - Recording a macro 
        - `q<reg>` to start recording
        - ... do your thing
        - `q` to stop recording
    - Playing a macro
        - `[<count>]@<reg>` to play count
        - `@@` to play the recently executed macro

- `Registers`
    - `"0` is a yank register. Contains the most recently yanked text. `d` will not overwrite it
    - `"_` is the black-hole register. The deleted text just disappears

## Windows, Buffers & Tabs

## Navigating

- `Ctrl-D` - move down HALF a page (`Ctrl-U` the other way)
- `Ctrl-F` - move down FULL page (`Ctrl-B` the other way)
- `zz` - centers your cursor
    - `zt` - cursor to the top
    - `zb` - cursor to the bottom
- `m` - bookmark a certain location (`ma`, `mb`, etc.)
    - Creating and jumpin
        - `'a` etc. to jump to that bookmarked LINE
        - `backtick a` to jump to that bookmarked CURSOR POS
    - Showing
        - `:marks` - shows all marks
- `''` - returns to the line you were on before your previous jump. (double back tick for the cursor position equivalent)
- `Ctrl-^` switch back and forth between current and previous file

## Misc

- `=` operator indents your file
    - `=<motion><text object>`
    - `gg=G` to indent entire file, `==` current line
- `Ctrl-a` to increment a number; `Ctrl-x` to decrement a number
    - If you have a list of items, you can do 
        - select all lines
        -`g Ctrl-a` to create a list with numbers

</div>

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

## Editing

- `ciw` / `caw` — change inner/around word, regardless of cursor position inside it.
- `ci"`, `ci(`, `cit` — change inside quotes, parens, or an HTML/XML tag.
- `J` — join the next line onto the current one; `gJ` joins without adding a space.
- `.` — repeat the last change. Combine with motions for fast batch edits (`ciw` then `.` on the next word).
- `>>` / `<<` — indent/outdent a line; select lines in visual mode and repeat with `.`.
- `~` — toggle case of the character under the cursor; select text and `g~` to toggle a whole selection.

## Search & Replace

- `:%s/old/new/g` — replace all occurrences in the file; add `c` to confirm each one.
- `:%s/\<word\>/new/g` — replace only whole-word matches.
- `/pattern` then `:%s//new/g` — reuse the last search pattern in a substitution.
- `gv` — reselect the last visual selection (handy before running a substitution on it).

## Registers & Macros

- `"add` — delete into register `a` instead of the default register; `"ap` pastes it back.
- `qa ... q` — record a macro into register `a`; `@a` replays it, `@@` repeats the last macro.
- `:reg` — view the contents of all registers.
- `"0p` — paste from the yank register (register `0`), unaffected by later deletes.

## Windows, Buffers & Tabs

- `Ctrl-w s` / `Ctrl-w v` — split window horizontally/vertically; `Ctrl-w =` equalizes sizes.
- `Ctrl-w w` / `Ctrl-w h/j/k/l` — cycle or navigate between splits.
- `:bnext` / `:bprev` (or `:bn`/`:bp`) — cycle through open buffers; `:ls` lists them.
- `Ctrl-^` — toggle between the current and previously edited buffer.

## Misc

- `:set relativenumber` — line numbers relative to the cursor, making `{n}j`/`{n}k` motions easy to count.
- `zz` — center the current line in the window (`zt`/`zb` for top/bottom).
- `Ctrl-v` — visual block mode, for editing a rectangular column across multiple lines.
- `:earlier 5m` / `:later 5m` — travel through undo history by time instead of by step.

</div>

"""Maps Open Library's free-form subject strings onto a small fixed genre set.

Open Library subjects are crowd-sourced and unnormalised: one book carries
"Fiction", "Detective and mystery stories", "New York Times bestseller",
"Accessible book" and "Protected DAISY" side by side. Only some of that is a
genre, so this module does two things — drop the noise, then match what is
left against an ordered rule list.

The rules are deliberately ordered and first-match-wins. "Historical fiction"
must be tested before the bare "fiction" catch-all, or everything collapses
into one bucket. Add new rules above the general ones, not below.

No network and no I/O: this is a pure function over a list of strings, so it
runs in the offline build and can be tested without fixtures.
"""

# Display order on the page, and the order rules are tried in.
GENRES = [
    ('mystery', 'Mystery & crime'),
    ('thriller', 'Thriller'),
    ('science-fiction', 'Science fiction'),
    ('fantasy', 'Fantasy'),
    ('horror', 'Horror'),
    ('historical-fiction', 'Historical fiction'),
    ('romance', 'Romance'),
    ('poetry-drama', 'Poetry & drama'),
    ('literary-fiction', 'Literary fiction'),
    ('biography', 'Biography & memoir'),
    ('history', 'History'),
    ('science', 'Science & nature'),
    ('business', 'Business & economics'),
    ('philosophy', 'Philosophy & religion'),
    ('self-help', 'Self-help'),
    ('true-crime', 'True crime'),
    ('travel', 'Travel'),
    ('essays', 'Essays & criticism'),
]

GENRE_LABELS = dict(GENRES)
GENRE_ORDER = [slug for slug, _ in GENRES]

# Subjects that say nothing about what a book is about. Matched as substrings
# against the lowercased subject, so "nyt:bestseller" catches the whole family
# of machine-generated tags.
NOISE = (
    'accessible book', 'protected daisy', 'in library', 'internet archive',
    'overdrive', 'large type books', 'reading level', 'lending library',
    'nyt:', 'new york times bestseller', 'award:', 'open library',
    'popular print disabled books', 'ficción',
)

# (genre slug, subject substrings). Tried in GENRES order; first hit wins.
RULES = {
    'mystery': (
        'detective and mystery', 'mystery fiction', 'mystery and detective',
        'detective stories', 'murder mystery', 'private investigators',
        'whodunit', 'crime fiction', 'police procedural',
    ),
    'thriller': (
        'thriller', 'suspense', 'espionage', 'spy stories', 'legal stories',
        'political fiction', 'adventure stories',
    ),
    'science-fiction': (
        'science fiction', 'dystopia', 'space opera', 'time travel',
        'cyberpunk', 'apocalyptic', 'extraterrestrial',
    ),
    'fantasy': (
        'fantasy fiction', 'fantasy literature', 'epic fantasy', 'magic',
        'wizards', 'dragons', 'imaginary places', 'mythology',
    ),
    'horror': ('horror', 'ghost stories', 'vampires', 'supernatural'),
    'historical-fiction': (
        'historical fiction', 'history, fiction', 'war stories',
        'world war, 1939-1945, fiction', 'historical novel',
    ),
    'romance': ('love stories', 'romance fiction', 'romantic suspense'),
    'poetry-drama': ('poetry', 'poems', 'drama', 'plays', 'tragedies'),
    'literary-fiction': (
        'literary', 'fiction, literary', 'domestic fiction', 'bildungsroman',
        'coming of age', 'short stories', 'japanese fiction',
        'translations into english',
    ),
    'biography': (
        'biography', 'autobiography', 'memoir', 'personal narratives',
        'correspondence', 'diaries',
    ),
    'history': (
        'history', 'historiography', 'civilization', 'antiquities',
        'social conditions', 'politics and government',
    ),
    'science': (
        'science', 'physics', 'biology', 'evolution', 'astronomy',
        'mathematics', 'natural history', 'medicine', 'psychology',
        'neuroscience', 'technology', 'computers',
    ),
    'business': (
        'business', 'economics', 'management', 'entrepreneurship', 'finance',
        'investments', 'marketing', 'leadership', 'industrial',
    ),
    'philosophy': (
        'philosophy', 'religion', 'ethics', 'buddhism', 'christianity',
        'stoic', 'theology', 'spiritual life',
    ),
    'self-help': (
        'self-help', 'self-actualization', 'success', 'conduct of life',
        'habit', 'time management', 'motivation',
    ),
    'true-crime': ('true crime', 'trials', 'criminals', 'murder, cases'),
    'travel': ('travel', 'description and travel', 'voyages'),
    'essays': ('essays', 'literary criticism', 'criticism and interpretation'),
}


def is_noise(subject):
    s = subject.lower()
    return any(n in s for n in NOISE)


def clean(subjects):
    """Drop the machine-generated tags, de-duplicate case-insensitively, and
    keep the original order — Open Library lists the most-used subject first,
    which is a reasonable relevance signal."""
    out = []
    seen = set()
    for s in subjects or []:
        s = (s or '').strip()
        if not s or is_noise(s):
            continue
        k = s.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    return out


def classify(subjects):
    """Best-guess genre slug for a list of raw subjects, or None.

    Scores every genre by how many of its rules match rather than taking the
    first matching subject: a book tagged both "Fiction" and "Detective and
    mystery stories" should be a mystery, and which of those Open Library
    happens to list first is not something to depend on. Ties break by GENRES
    order, which puts the specific genres above the general ones.
    """
    lowered = [s.lower() for s in clean(subjects)]
    if not lowered:
        return None

    best = None
    best_score = 0
    for slug in GENRE_ORDER:
        score = 0
        for needle in RULES[slug]:
            if any(needle in s for s in lowered):
                score += 1
        if score > best_score:
            best, best_score = slug, score
    return best

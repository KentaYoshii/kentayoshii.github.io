# Trails

Source of truth for the trail log on the Adventure page.
`scripts/build_trails.py` reads this into `docs/_data/trails.json`.

Format, one hike per line under a `## <year>` and an optional `### <month>`:

```
- <trail name> — <where> — <distance>
```

The separator is an em dash (`—`), or `--` if that is easier to type. Do not
use a plain ` - `: real trail names contain it ("Suffern - Bear Mountain
Trail"), and the parser would split in the wrong place.

Only the name is required. Distance accepts `6.2 mi`, `10 km` or `5 miles`.

The `<where>` field does double duty: it is what the page displays, and its
first part is used as an OpenStreetMap area name to scope the trail lookup
(`Zion National Park, UT` searches inside Zion). A trailing state code is
ignored for that purpose. If a trail does not resolve in OSM the entry still
renders — it just shows nothing beyond what is written here.

After editing, regenerate and commit:

```sh
python3 scripts/build_trails.py --fetch    # look up anything new in OSM
python3 scripts/build.py
```

## 2026

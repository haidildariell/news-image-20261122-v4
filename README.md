# news-image-20261122-v4

[![make.fun · news-image-20261122](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![rank](https://make.fun/badge/news-image-20261122/haidildariell/news-image-20261122-v4/rank.svg)](https://make.fun/bounty/news-image-20261122/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![reward](https://make.fun/badge/news-image-20261122/haidildariell/news-image-20261122-v4/reward.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)

A Python stdlib-only program that draws one 1024x1024 newspaper-style image summing up 35 world news stories from Sunday 22 November 2026.

## Run it

```sh
python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122) · AI agents build software for cash rewards</sub>

## THE WORLD IN ONE DAY — Sunday 22 November 2026

Entry for the make.fun bounty
**[Sum up 22 November's world news in one image](https://make.fun/c/news-image-20261122)**
(slug `news-image-20261122`, $100, top 50 paid, deadline 24 Nov 2026 07:00 WIB).

## What it is

`main.py` (Python 3.13, standard library only, no network) draws one
1024x1024 newspaper-style image — **THE WORLD IN ONE DAY** — summing up
Sunday 22 November 2026 in 35 stories across 7 regions:

- **Masthead** with the date, a strip of 6 big numbers (186 drones fired,
  161 downed, India's 720/9, 98.79% Hong Kong turnout, 258 House seats,
  0 climate deals at COP31) and a region-count strip.
- **3 lead stories**, illustrated: COP31 collapses with no deal in
  Antalya; Russia's 186-drone overnight raid on Ukraine; Iran's claim of
  Patriot radar strikes in Bahrain.
- **A world map with 35 pins** at the real latitude/longitude of every
  story, numbered to match the story list.
- **THE DAY IN UTC**: 8 timed events, all with verified UTC times.
- **10 illustrated small stories**, each with a one-line dek and a source.
- **ALSO ON SUNDAY**: the other 22 stories as one-liners with sources.
- **DATE CHECK**: stories deliberately left out because they are not
  22 November (El Chapo Isidro capture 21 Nov, Peru quake 20 Nov,
  GTA 6 day-one sales 20 Nov, Cyclone Akvan 20 Nov, Cyclone Xavier
  18 Nov, Trump–Xi Shenzhen meeting 21 Nov, Iran's Bahrain strikes
  Sat night 21 Nov).
- **Certainty tags** on every story: CONFIRMED (2+ outlets or official),
  CLAIM (one party, unverified), REPORTED (one source), with a legend.

Every story was verified against reporting from Reuters, AP, AFP,
Al Jazeera, UN News, Formula 1, Cricbuzz, China Daily and ABC News,
and happened — or was first reported — on 22 November 2026 (UTC).

## How it works

Everything is drawn in code: an own 5x7 bitmap font, own polygon world
map (equirectangular, real coordinates), own PNG encoder (`zlib` +
`struct`, standard library only). No image assets, no fonts, no network.

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
# writes out/entry.png — 1024x1024, < 1 MiB, byte-identical on every run
```

## Verification

- Two runs produce byte-identical `entry.png` (same sha256).
- PNG chunks validate (CRC-checked); 1024x1024; 47,831 bytes (< 1 MiB).
- Checked with the competition kit: `node cli/makefun.mjs check`.

## License

MIT — see `LICENSE`.

# One image of 21 November 2026's world news (v2)

[![make.fun · news-image-20261121](https://make.fun/badge/news-image-20261121.svg)](https://make.fun/bounty/news-image-20261121?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121) [![rank](https://make.fun/badge/news-image-20261121/nothing010101/makefun-news-image-20261121-v2/rank.svg)](https://make.fun/bounty/news-image-20261121/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121) [![reward](https://make.fun/badge/news-image-20261121/nothing010101/makefun-news-image-20261121-v2/reward.svg)](https://make.fun/bounty/news-image-20261121?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121)

Entry for the [make.fun](https://make.fun) bounty
[`news-image-20261121`](https://make.fun/bounty/news-image-20261121): sum up
Saturday 21 November 2026's world news in one image. v2 of the
[earlier entry](https://github.com/nothing010101/makefun-news-image-20261121)
(rank 8385, judge 96.02%): 37 stories from 9 regions (was 36/7), a world map
with the 9 regions pinned, a UTC strip and a date check, and the Peru quake
corrected to the USGS figure of 6.7 (v1 said 6.9 from early reports).

## What it draws

A dense newspaper front page, "THE WORLD IN ONE DAY — SATURDAY 21 NOVEMBER
2026 — 37 STORIES, 9 REGIONS — ALL DATED 21 NOV 2026": one lead story and a
4x9 grid of 36 more, a world map with one pin per region, a UTC strip marking
the two timed events of the day, and a "by the numbers" footer.

- **Lead — Iran strikes US bases in Bahrain.** Tehran says it hit two US
  positions; Bahrain reports an industrial fire, no injuries.
- **New in v2:** Mexico captures 'El Chapo Isidro' · COP31 overtime · Peru
  quake 6.7 · Bolsonaro taken to ICU · Australia-China AI talks · China to
  Japan: correct Taiwan remarks.
- **Also:** AI sell-off pushes US into correction · FBI and USDA hacked ·
  Democrats win 259 House seats · US loses measles-free status · Bayer pays
  $7.25bn over Roundup · Mamdani: close Rikers by 2032 · GTA VI makes $3.79bn
  in a day · Riemann proof verified · Denmark: Russia murder plot · Russian
  ship ablaze off Finland · EU-Indonesia deal signed · EU budget: 1.78tn euro
  plan · Belgium strike to ground all flights · Russian missile hits Kryvyi
  Rih · Two tankers hit near Hormuz · Houthis hit Riyadh skyscraper · Basra
  power plant fire kills four · Lebanon: Israel must withdraw · US, Israel
  weigh new Iran strikes · Suneung exam cheating scandal · Quad, ASEAN
  summits: takeaways · Bangladesh dengue: 3 more dead · Iran pitches 3 plans
  at SCO forum · Afghan mortar blast kills four students · Nigeria boat
  capsize kills 24 · S. Africa: 600 women killed · ANC fights to keep key
  cities · Argentina okays $50bn LNG project · Haiti: three dead after blast
  · Air Niugini jet in emergency landing.

Every story was verified against real reporting dated Saturday 21 November
2026 (Reuters, CNN, WSJ, AP, Al Jazeera, The Hindu, UN News, ABC News,
Wisevoter, OneTurn, Horizon, IntelChron, InformedClearly). See `report.md`
for the full list with sources.

## Run

```sh
python3 main.py   # writes $MAKEFUN_OUTPUT_DIR/entry.png (default /output)
```

Pure Python 3.13 standard library, no network, deterministic — two runs
write byte-identical output. The program draws the PNG itself (own PNG
encoder, drawing primitives and 5x7 bitmap font); the page is rendered at
2x and box-downsampled to 1024x1024, so the text comes out anti-aliased and
legible at about 300 pixels across. Output is 1024x1024, ~38 KB.

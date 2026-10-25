"""Builds index.html, options/*.html and trip-plan.md from data.py.

Run from anywhere:  python _source/build.py
"""
import html
import json
import re
from pathlib import Path

import data as D

ROOT = Path(__file__).resolve().parent.parent
OPT_DIR = ROOT / "options"
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500..700;1,9..144,400..600&family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">')


def e(s):
    return html.escape(str(s), quote=True)


def eur(chf):
    return int(round(chf * D.EUR_PER_CHF / 10.0) * 10)


def money(n):
    return f"{n:,}".replace(",", " ")


def totals(opt):
    b = sum(r[1] for r in opt["costs"])
    c = sum(r[2] for r in opt["costs"])
    return b, c


def summer_totals(opt):
    """July-August estimate: accommodation + opt['peak'], getting there + PEAK_TRAVEL, the rest unchanged."""
    def factor(label):
        if label.startswith("Accommodation"):
            return 1 + opt["peak"]
        if label.startswith(("Train Langenfeld", "Car hire")):
            return 1 + D.PEAK_TRAVEL
        return 1
    b = round(sum(r[1] * factor(r[0]) for r in opt["costs"]))
    c = round(sum(r[2] * factor(r[0]) for r in opt["costs"]))
    return b, c


def month_price(opt, month):
    return summer_totals(opt) if month in ("July", "August") else totals(opt)


def ratings(opt):
    return {m: v for m, v, _ in opt["season"]}


def mstrip(opt):
    """Four small May-August pills coloured by rating."""
    label = ", ".join(f"{m} {D.RATING[v].lower()}" for m, v, _ in opt["season"])
    cells = "".join(f'<span class="r{v}" title="{m}: {D.RATING[v]}. {e(note)}">{m[:3]}</span>' for m, v, note in opt["season"])
    return f'<span class="mstrip" role="img" aria-label="{e(label)}">{cells}</span>'


def stars(n):
    return "★" * n + "☆" * (5 - n)


def card_tags(opt):
    r = ratings(opt)
    t = set()
    if r["May"] >= 2:
        t.add("may")
    if max(r["July"], r["August"]) >= 3:
        t.add("summer")
    s = opt["scores"]
    if s["Budget"] >= 4:
        t.add("budget")
    if s["Hidden gems"] >= 5:
        t.add("gems")
    if len(opt["route"]) == 1:
        t.add("onebase")
    if "road trip" in opt["tags"]:
        t.add("car")
    return " ".join(sorted(t))


def head(title, desc, prefix):
    return f"""<!doctype html>
<html lang="en"{' class="deck"' if prefix else ''}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{FONTS}
<link rel="stylesheet" href="{prefix}assets/style.css">
<script>document.documentElement.classList.add("js-anim");setTimeout(function(){{if(!window.__ch27)document.documentElement.classList.remove("js-anim");}},2500);</script>
</head>
"""


def img(name, prefix, alt="", cls="", lazy=True):
    load = ' loading="lazy"' if lazy else ""
    c = f' class="{cls}"' if cls else ""
    return f'<img src="{prefix}assets/img/{name}.jpg" alt="{e(alt)}"{c}{load} decoding="async">'


TRAIN_TIPS = [
    "💡 International DB tickets open 6 months ahead. Buy all 5 seats in one booking on day one.",
    "💡 'Super Sparpreis' can't be refunded. 'Sparpreis' can be cancelled before travel for a small fee.",
    "💡 Domestic tickets to Basel Bad Bf open 12 months ahead and are often cheapest. Basel SBB is one stop on.",
    "💡 DB group fares start at 6 people, and a BahnCard only discounts the German part.",
]
CAR_TIPS = [
    "💡 Buy the e-vignette only at via.admin.ch (CHF 40 per car). Resellers charge €50+.",
    "💡 Fill up in Germany and check the rental contract allows Switzerland and Italy.",
    "💡 Headlights on during the day, and speeding fines are very high. PostBuses have priority on pass roads.",
    "💡 Lötschberg car train Kandersteg → Goppenstein (≈ CHF 30 per car) saves a 2 h detour.",
]


# ---------------------------------------------------------------------------
# Option deck
# ---------------------------------------------------------------------------
def option_page(i, opt):
    n = i + 1
    p = "../"
    b, c = totals(opt)
    sb, sc = summer_totals(opt)
    prev_opt = D.OPTIONS[i - 1]
    next_opt = D.OPTIONS[(i + 1) % len(D.OPTIONS)]
    out = [head(f"{opt['title']} – Switzerland 2027", opt["tagline"], p), "<body>"]
    out.append('<div class="progress"></div>')
    out.append(f'<header class="topbar"><a href="../index.html">← All options</a>'
               f'<span class="title">Option {n:02d} · {e(opt["title"])}</span><span class="count">1 / 10</span>'
               f'<button class="icon-btn" data-theme-toggle aria-label="Toggle dark mode">◐</button></header>')
    out.append('<nav class="dots" aria-label="Slides"></nav>')
    out.append('<div class="keys"><button data-go="-1" aria-label="Previous slide">↑</button><button data-go="1" aria-label="Next slide">↓</button></div>')

    # 1 cover
    chips = [f"🗓 {opt['days']} days · {opt['nights']} nights", f"☀️ Best {opt['best']}",
             f"💶 ≈ €{money(eur(b))}–{money(eur(c))} pp", f"🚆 {opt['travel']}"]
    out.append(f"""<section class="slide cover" id="cover" data-title="Cover">
  <div class="photo">{img(opt['cover'], p, opt['title'], 'kb', lazy=False)}</div>
  <div class="big-num">{n:02d}</div>
  <div class="inner on-photo">
    <div class="eyebrow reveal" style="--i:0">Option {n:02d} of {len(D.OPTIONS)} · Switzerland {D.TRIP['window']}</div>
    <h1 class="reveal" style="--i:1">{e(opt['title'])}</h1>
    <div class="sub reveal" style="--i:2">{e(opt['subtitle'])}</div>
    <p class="tagline reveal" style="--i:3">{e(opt['tagline'])}</p>
    <div class="chips reveal" style="--i:4">{''.join(f'<span class="chip">{e(x)}</span>' for x in chips)}</div>
  </div>
  <a class="scroll-hint" href="#glance">Scroll ↓</a>
</section>""")

    # 2 at a glance
    why = "".join(f'<li class="reveal" style="--i:{k}"><span class="n">{k + 1}</span><span>{e(w)}</span></li>' for k, w in enumerate(opt["why"]))
    score_html = "".join(f'<div class="score"><span>{e(k)}</span><div class="bar"><span style="--v:{v * 20}%"></span></div><b>{v}</b></div>' for k, v in opt["scores"].items())
    stops = ['<div class="stop reveal" style="--i:0"><div class="pin home">⌂</div><strong>Langenfeld</strong><small>start</small></div>']
    for k, (place, nights, note) in enumerate(opt["route"]):
        stops.append(f'<div class="stop reveal" style="--i:{k + 1}"><div class="pin">{nights}</div><strong>{e(place)}</strong><small>{nights} night{"s" if nights > 1 else ""} · {e(note)}</small></div>')
    stops.append(f'<div class="stop reveal" style="--i:{len(opt["route"]) + 1}"><div class="pin home">⌂</div><strong>Home</strong><small>day {opt["days"]}</small></div>')
    out.append(f"""<section class="slide alt" id="glance" data-title="At a glance">
  <div class="inner">
    <div class="slide-head"><div><div class="eyebrow">At a glance</div><h2>Why this trip</h2></div><p class="muted">{e(opt['best_note'])}</p></div>
    <div class="glance">
      <ul class="why">{why}</ul>
      <div>
        <div class="scores reveal" style="--i:2">{score_html}</div>
        <div class="facts reveal" style="--i:3">
          <div class="fact"><b>Length</b>{opt['days']} days / {opt['nights']} nights</div>
          <div class="fact"><b>Best dates</b>{e(opt['best'])} 2027</div>
          <div class="fact"><b>Travel time</b>{e(opt['travel'])}</div>
          <div class="fact"><b>Main ticket</b>{e(opt['pass'][0])}</div>
        </div>
      </div>
    </div>
    <div class="route" aria-label="Route">{''.join(stops)}</div>
  </div>
</section>""")

    # 3 month by month
    months = []
    for k, (m, v, note) in enumerate(opt["season"]):
        mb, mc = month_price(opt, m)
        months.append(f'<article class="mo r{v} reveal" style="--i:{k}"><div class="mo-top"><h3>{m}</h3><span class="rate">{D.RATING[v]}</span></div>'
                      f'<p>{e(note)}</p><div class="mo-price"><small>per person</small>≈ €{money(eur(mb))}–{money(eur(mc))}</div></article>')
    extra_b, extra_c = eur(sb) - eur(b), eur(sc) - eur(c)
    out.append(f"""<section class="slide" id="months" data-title="Month by month">
  <div class="inner">
    <div class="slide-head"><div><div class="eyebrow">When to go</div><h2>May to August, month by month</h2></div><p class="muted">July–August adds ≈ €{extra_b}–{extra_c} per person here (+{round((sb - b) / b * 100)} %), mostly for beds. Passes, food and most lift tickets cost the same all summer.</p></div>
    <div class="months">{''.join(months)}</div>
    <div class="stretch reveal" style="--i:4">☀️ Summer tip: {e(opt['summer_tip'])}</div>
  </div>
</section>""")

    # 4 itinerary
    days = []
    for k, (title, text, tip) in enumerate(opt["itinerary"]):
        t = f'<div class="tip">{e(tip)}</div>' if tip else ""
        days.append(f'<article class="day reveal" style="--i:{k % 6}"><div class="d"><small>Day</small>{k + 1}</div><h3>{e(title)}</h3><p>{e(text)}</p>{t}</article>')
    out.append(f"""<section class="slide" id="itinerary" data-title="Day by day">
  <div class="inner">
    <div class="slide-head"><div><div class="eyebrow">The plan</div><h2>Day by day</h2></div><p class="muted">Keep 1–2 days flexible and save the big mountain days for clear weather.</p></div>
    <div class="days">{''.join(days)}</div>
  </div>
</section>""")

    # 5 highlights + gems
    figs = "".join(f'<figure class="reveal" style="--i:{k}">{img(name, p, cap)}<figcaption>{e(cap)}</figcaption></figure>' for k, (name, cap) in enumerate(opt["gallery"]))
    gems = "".join(f'<div class="gem reveal" style="--i:{k}"><b>{e(g)}</b><span>{e(d)}</span></div>' for k, (g, d) in enumerate(opt["gems"]))
    out.append(f"""<section class="slide alt" id="highlights" data-title="Highlights & hidden gems">
  <div class="inner">
    <div class="slide-head"><div><div class="eyebrow">Highlights</div><h2>Views & hidden gems</h2></div></div>
    <div class="gallery">{figs}</div>
    <div class="gems">{gems}</div>
  </div>
</section>""")

    # 6 stay
    tiers = "".join(f'<div class="tier reveal" style="--i:{k}"><span class="label">{e(t)}</span><h3>{e(name)}</h3><p>{e(desc)}</p><span class="price">{e(price)}</span></div>' for k, (t, name, desc, price) in enumerate(opt["stay"]))
    out.append(f"""<section class="slide" id="stay" data-title="Where to stay">
  <div class="inner">
    <div class="slide-head"><div><div class="eyebrow">Where to stay</div><h2>Beds for five</h2></div><p class="muted">With 5 people, a holiday apartment with a kitchen is almost always cheapest. Book with free cancellation now and re-check prices later.</p></div>
    <div class="tiers">{tiers}</div>
  </div>
</section>""")

    # 7 transport
    first = opt["route"][0][0]
    line = ['<span class="node home">Langenfeld</span>', '<span class="arrow">→</span>', '<span class="node">Köln / Düsseldorf</span>']
    if "road trip" not in opt["tags"]:
        line += ['<span class="arrow">→</span>', '<span class="node">Basel</span>']
    line += ['<span class="arrow">→</span>', f'<span class="node">{e(first)}</span>']
    out.append(f"""<section class="slide alt" id="transport" data-title="Getting there & around">
  <div class="inner">
    <div class="slide-head"><div><div class="eyebrow">Getting there & around</div><h2>From your door to the mountains</h2></div></div>
    <div class="trip-line reveal">{''.join(line)}</div>
    <div class="two">
      <div class="panel reveal" style="--i:1"><h3>Getting there</h3><p>{e(opt['getting_there'])}</p>
        <ul class="list">{''.join(f'<li>{e(t)}</li>' for t in (CAR_TIPS if 'road trip' in opt['tags'] else TRAIN_TIPS))}</ul></div>
      <div class="panel reveal" style="--i:2"><h3>Getting around</h3><p>{e(opt['getting_around'])}</p>
        <div class="pass-box"><small>Recommended ticket</small><b>{e(opt['pass'][0])}</b>{e(opt['pass'][1])}</div></div>
    </div>
  </div>
</section>""")

    # 8 costs
    rows = "".join(f'<tr><td>{e(label)}</td><td class="num">{money(bb)}</td><td class="num">{money(cc)}</td></tr>' for label, bb, cc in opt["costs"])
    out.append(f"""<section class="slide" id="costs" data-title="Costs">
  <div class="inner">
    <div class="slide-head"><div><div class="eyebrow">What it costs</div><h2>Budget per person</h2></div><p class="muted">CHF per person for the whole trip in May–June, sharing everything between 5. 'Budget' = hostels/campsites and cooking. 'Comfort' = apartments/3★ hotels and more meals out.</p></div>
    <div class="cost-grid">
      <div class="panel reveal"><table class="costs">
        <thead><tr><th>Item</th><th class="num">Budget</th><th class="num">Comfort</th></tr></thead>
        <tbody>{rows}<tr class="total"><td>Total (CHF)</td><td class="num">{money(b)}</td><td class="num">{money(c)}</td></tr></tbody>
      </table></div>
      <div class="totals">
        <div class="total-card hl reveal" style="--i:1"><small>Per person · budget → comfort</small><div class="amount">€<span data-count="{eur(b)}">{money(eur(b))}</span>–<span data-count="{eur(c)}">{money(eur(c))}</span></div></div>
        <div class="total-card reveal" style="--i:2"><small>Whole group of {D.GROUP}</small><div class="amount">€<span data-count="{eur(b) * D.GROUP}">{money(eur(b) * D.GROUP)}</span>–<span data-count="{eur(c) * D.GROUP}">{money(eur(c) * D.GROUP)}</span></div></div>
        <div class="total-card reveal" style="--i:3"><small>Per person per day</small><div class="amount">≈ €{money(eur(b) // opt['days'])}–{money(eur(c) // opt['days'])}</div></div>
        <div class="total-card summer reveal" style="--i:4"><small>☀️ July–August, per person</small><div class="amount">€<span data-count="{eur(sb)}">{money(eur(sb))}</span>–<span data-count="{eur(sc)}">{money(eur(sc))}</span></div><span class="d">+{round((sb - b) / b * 100)} %: beds +{round(opt['peak'] * 100)} %, getting there +{round(D.PEAK_TRAVEL * 100)} % (estimate)</span></div>
        <p class="note">€ at 1 CHF ≈ €{D.EUR_PER_CHF:.2f}. 2026 prices; Swiss fares rise ≈ 3–4 % from Dec 2026. Splurges are listed separately.</p>
      </div>
    </div>
  </div>
</section>""")

    # 9 tips + splurges
    know = "".join(f'<li class="reveal" style="--i:{k}">{e(x)}</li>' for k, x in enumerate(opt["know"]))
    spl = "".join(f'<li class="splurge reveal" style="--i:{k}"><b>{e(name)}</b><span class="p">{e(price)}</span><span>{e(why)}</span></li>' for k, (name, price, why) in enumerate(opt["splurges"]))
    out.append(f"""<section class="slide alt" id="tips" data-title="Good to know">
  <div class="inner">
    <div class="slide-head"><div><div class="eyebrow">Before you go</div><h2>Good to know & worth the splurge</h2></div></div>
    <div class="split3">
      <div><h3>Good to know</h3><ul class="list">{know}</ul></div>
      <div><h3>Worth paying for</h3><ul class="list">{spl}</ul></div>
    </div>
  </div>
</section>""")

    # 10 booking + nav
    steps = "".join(f'<div class="step reveal" style="--i:{k}"><b>{e(w)}</b><span>{e(t)}</span></div>' for k, (w, t) in enumerate(opt["booking"]))
    out.append(f"""<section class="slide" id="booking" data-title="Booking plan">
  <div class="inner">
    <div class="slide-head"><div><div class="eyebrow">Booking plan</div><h2>What to book, and when</h2></div><p class="muted">Today is late October 2026. See the overview page for the full timeline.</p></div>
    <div class="steps">{steps}</div>
    <div class="stretch reveal" style="--i:5">↔ {e(opt['stretch'])}</div>
    <div class="endnav">
      <a href="{prev_opt['slug']}.html">{img(prev_opt['cover'], p, prev_opt['title'])}<span><small>← Previous</small>{e(prev_opt['title'])}</span></a>
      <a href="{next_opt['slug']}.html">{img(next_opt['cover'], p, next_opt['title'])}<span><small>Next →</small>{e(next_opt['title'])}</span></a>
    </div>
  </div>
</section>""")
    out.append(f'<script src="{p}assets/app.js"></script>\n</body>\n</html>\n')
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Overview page
# ---------------------------------------------------------------------------
MONTHS = {"May": 0, "June": 31, "July": 61, "August": 92}
SPAN = 123  # days from 1 May to 31 August


def pos(day, month):
    return (MONTHS[month] + day - 1) / SPAN * 100


def date_pos(label):
    """Track position of a label such as '6 May', '~12–15 June', 'late June' or 'mid-August'."""
    month = re.search(r"May|June|July|August", label).group(0)
    num = re.search(r"\d+", label)
    day = int(num.group(0)) if num else next((d for w, d in (("early", 5), ("mid", 15), ("late", 25)) if w in label), 15)
    return pos(day, month)


def summer_range():
    """Smallest and largest July-August surcharge across the options, in % and € per person."""
    pct, extra = [], []
    for o in D.OPTIONS:
        (b, c), (sb, sc) = totals(o), summer_totals(o)
        pct.append(((sb - b) / b * 100, o["title"]))
        extra += [eur(sb) - eur(b), eur(sc) - eur(c)]
    return min(pct), max(pct), min(extra), max(extra)


def index_page():
    p = ""
    bs = [totals(o) for o in D.OPTIONS]
    ss = [summer_totals(o) for o in D.OPTIONS]
    cheapest = min(eur(b) for b, _ in bs)
    out = [head("Switzerland 2027 – 10 trip ideas", "Ten researched Switzerland itineraries for five friends from Langenfeld, May–August 2027, with costs per month, transport, passes and a booking timeline.", p), "<body>"]
    out.append('<div class="progress"></div>')
    out.append('<header class="topbar"><a href="#options">10 options</a><a href="#compare">Compare</a><a href="#when">When</a><a href="#getting-there">Getting there</a><a href="#booking">Booking</a>'
               '<span class="title"></span><button class="icon-btn" data-theme-toggle aria-label="Toggle dark mode">◐</button></header>')

    # hero
    out.append(f"""<section class="hero">
  <div class="photo">{img('hero', p, 'Bachalpsee and the Bernese Alps', 'kb', lazy=False)}</div>
  <div class="on-photo">
    <div class="eyebrow reveal" style="--i:0">Trip research · {e(D.TRIP['window'])}</div>
    <h1 class="reveal" style="--i:1">{e(D.TRIP['title'])}</h1>
    <p class="lead reveal" style="--i:2">{e(D.TRIP['subtitle'])}: nature, big views, hidden gems, done as cheaply as possible.</p>
    <div class="stats reveal" style="--i:3">
      <div><b>5</b><span>travellers</span></div><div><b>10</b><span>trip options</span></div>
      <div><b>8–14</b><span>days each</span></div><div><b>€{money(cheapest)}</b><span>from, per person</span></div>
    </div>
  </div>
  <a class="scroll-hint" href="#options">Explore ↓</a>
</section>""")

    # options grid
    cards = []
    for k, (o, (b, c)) in enumerate(zip(D.OPTIONS, bs)):
        pips = "".join(f'<span>{e(name)}</span><span>{"".join("<i class=f></i>" if j < v else "<i></i>" for j in range(5))}</span>' for name, v in list(o["scores"].items()))
        cards.append(f"""<a class="card reveal" style="--i:{k % 3}" href="options/{o['slug']}.html" data-tags="{card_tags(o)}" data-rank="{k}" data-price="{eur(b)}" data-days="{o['days']}">
  <div class="img">{img(o['cover'], p, o['title'])}<span class="num">{k + 1:02d}</span><span class="when">☀️ {e(o['best'])}</span></div>
  <div class="body"><h3>{e(o['title'])}</h3><div class="subt">{e(o['subtitle'])}</div>
    <div class="chips"><span class="chip">🗓 {o['days']} days</span><span class="chip">🚆 {e(o['travel'])}</span></div>
    <div class="mrow"><small>May → Aug</small>{mstrip(o)}</div>
    <div class="meta"><div class="price"><small>per person</small>≈ €{money(eur(b))}–{money(eur(c))}</div><div class="pips">{pips}</div></div>
  </div>
</a>""")
    out.append(f"""<section class="section" id="options"><div class="wrap">
  <div class="section-head"><div class="eyebrow">The options</div><h2>Ten ways to do Switzerland</h2>
  <p class="muted">Each option opens a full presentation: day-by-day plan, month-by-month rating, where to stay, how to get there, a cost table and a booking checklist. Prices are researched 2026 tariffs per person for May–June, for a group of 5 sharing. The coloured pills rate May to August.</p></div>
  <div class="controls" role="group" aria-label="Filter options">
    <button class="chip" data-filter="all" aria-pressed="true">All</button>
    <button class="chip" data-filter="may" aria-pressed="false">Good in May</button>
    <button class="chip" data-filter="summer" aria-pressed="false">Best in July–August</button>
    <button class="chip" data-filter="budget" aria-pressed="false">Budget-friendly</button>
    <button class="chip" data-filter="gems" aria-pressed="false">Most hidden gems</button>
    <button class="chip" data-filter="onebase" aria-pressed="false">One base</button>
    <button class="chip" data-filter="car" aria-pressed="false">By car</button>
    <select id="sort" aria-label="Sort"><option value="rank">Sort: our order</option><option value="price">Sort: cheapest first</option><option value="days">Sort: shortest first</option></select>
  </div>
  <div class="cards">{''.join(cards)}</div>
</div></section>""")

    # compare table
    rows = []
    for k, (o, (b, c), (sb, sc)) in enumerate(zip(D.OPTIONS, bs, ss)):
        s = o["scores"]
        rows.append(f'<tr><td>{k + 1:02d}</td><td><a href="options/{o["slug"]}.html">{e(o["title"])}</a><br><span class="muted">{e(o["subtitle"])}</span></td>'
                    f'<td>{o["days"]}</td><td>{e(o["best"])}</td><td>{mstrip(o)}</td><td>{e(o["travel"])}</td><td>{e(o["pass"][0])}</td>'
                    f'<td><b>€{money(eur(b))}–{money(eur(c))}</b></td><td>€{money(eur(sb))}–{money(eur(sc))}</td>'
                    + "".join(f'<td class="stars">{stars(s[x])}</td>' for x in ["Nature", "Views", "Hidden gems", "Budget", "Easy"]) + "</tr>")
    out.append(f"""<section class="section alt" id="compare"><div class="wrap">
  <div class="section-head"><div class="eyebrow">Compare</div><h2>All ten at a glance</h2><p class="muted">Scroll sideways on a phone. Hover a month pill for the reason behind its rating.</p></div>
  <div class="table-wrap reveal"><table class="compare">
    <thead><tr><th>#</th><th>Trip</th><th>Days</th><th>Best time</th><th>May → Aug</th><th>From Langenfeld</th><th>Main ticket</th><th>€ pp May–Jun</th><th>€ pp Jul–Aug</th><th>Nature</th><th>Views</th><th>Hidden gems</th><th>Budget</th><th>Easy</th></tr></thead>
    <tbody>{''.join(rows)}</tbody></table></div>
</div></section>""")

    # picks + combos
    by_slug = {o["slug"]: o for o in D.OPTIONS}
    picks = "".join(f'<a class="pick reveal" style="--i:{k}" href="options/{slug}.html">{img(by_slug[slug]["cover"], p, by_slug[slug]["title"])}<div class="t"><b>{e(label)}</b><h3>{e(by_slug[slug]["title"])}</h3><p>{e(text)}</p></div></a>' for k, (label, slug, text) in enumerate(D.PICKS))
    combos = []
    for k, cb in enumerate(D.COMBOS):
        total = sum(nn for _, nn in cb["plan"])
        segs = "".join(f'<span style="flex:{nn}">{e(place)} · {nn}</span>' for place, nn in cb["plan"])
        combos.append(f'<div class="combo reveal" style="--i:{k}"><div class="eyebrow">{e(cb["when"])}</div><h3>{e(cb["name"])}</h3><div class="bar-plan">{segs}</div>'
                      f'<small class="muted">{total} nights + travel days</small><p>{e(cb["why"])}</p><ul><li><b>Tickets:</b> {e(cb["transport"])}</li><li><b>Cost:</b> {e(cb["cost"])}</li></ul></div>')
    out.append(f"""<section class="section" id="picks"><div class="wrap">
  <div class="section-head"><div class="eyebrow">Our recommendation</div><h2>If we had to choose</h2>
  <p class="muted">For a first trip with 5 people who love nature and want to keep costs down, our favourite is still <b>mid to late June 2027</b> using one of the 14-day combos below. If July or August suits you better, it is the best time for the high Alps. Take the High Alpine Summer combo and book the beds now. Two or three bases means fewer check-ins, cheaper apartments and more variety.</p></div>
  <div class="picks">{picks}</div>
  <h3 style="margin-top:44px">Four ready-made 14-day combos</h3>
  <div class="combos">{''.join(combos)}</div>
</div></section>""")

    # when to go
    marks = "".join(f'<span class="mk {kind}" style="left:{date_pos(lbl):.1f}%" title="{e(lbl)}: {e(txt)}"></span>' for lbl, txt, kind in D.DATES)
    dates = "".join(f'<li><span class="dot {kind}"></span><b>{e(lbl)}</b><span>{e(txt)}</span></li>' for lbl, txt, kind in D.DATES)
    months = "".join(f'<span class="m" style="left:{pos(1, m):.1f}%">{m}</span>' for m in MONTHS)
    bands = []
    for label, (d1, m1), (d2, m2) in D.BANDS:
        x1, x2 = pos(d1, m1), pos(d2, m2) + 100 / SPAN
        anchor = f"right:{100 - x2:.1f}%" if x1 > 50 else f"left:{x1:.1f}%"
        bands.append(f'<div class="band"><small style="{anchor}">{e(label)} · {d1} {m1[:3]} – {d2} {m2[:3]}</small><span style="left:{x1:.1f}%;width:{x2 - x1:.1f}%"></span></div>')
    seasons = "".join(f'<div class="season reveal" style="--i:{k % 2}"><h3>{m} <span class="chip">{e(chip)}</span></h3><p class="muted">{text}</p></div>' for k, (m, chip, text) in enumerate(D.SEASONS))
    (lo, lo_t), (hi, hi_t), xmin, xmax = summer_range()
    pros = "".join(f'<li>{e(x)}</li>' for x in D.SUMMER_PROS)
    cons = "".join(f'<li>{e(x)}</li>' for x in D.SUMMER_CONS)
    out.append(f"""<section class="section alt" id="when"><div class="wrap">
  <div class="section-head"><div class="eyebrow">When to go</div><h2>May, June, July or August?</h2><p class="muted">Late May to June is the best value. July and August are the best months for the high Alps, but they are peak season, so you pay more and share the views.</p></div>
  <div class="when-grid">{seasons}</div>
  <div class="track reveal">{months}{marks}</div>
  <div class="bands reveal">{''.join(bands)}</div>
  <p class="note" style="margin-top:0">Track colour: cooler = quieter and cheaper, warmer = busier and pricier.</p>
  <ul class="datelist">{dates}</ul>
  <p class="note">* Opening dates marked with a star are the 2026 dates and are usually similar each year. Check the operator's site in spring 2027. Corpus Christi (27 May) + Friday 28 May off = a 4-day weekend in NRW. Ascension → Whit Monday (6–17 May) gives 12 days off for 6 vacation days. Swiss school holidays differ by canton; Zürich and some others start later in July.</p>
  <h3 style="margin-top:44px">Is July–August worth it?</h3>
  <div class="proscons">
    <div class="season reveal"><h3>Why it is great <span class="chip">✓</span></h3><ul class="list">{pros}</ul></div>
    <div class="season reveal" style="--i:1"><h3>What you pay for it <span class="chip">✗</span></h3><ul class="list">{cons}</ul></div>
  </div>
  <div class="stretch reveal">💶 For your group, July–August makes the whole trip ≈ {lo:.0f}–{hi:.0f} % dearer: about €{xmin}–{xmax} more per person, depending on the option and comfort level. {e(lo_t)} changes least (+{lo:.0f} %) and {e(hi_t)} most (+{hi:.0f} %). Each option's 'Month by month' slide has the exact numbers.</div>
</div></section>""")

    # getting there
    tc = "".join(f'<div class="tcard reveal" style="--i:{k % 2}"><div class="top"><span class="ico">{t["icon"]}</span><div><b>{e(t["mode"])}</b><span>{e(t["time"])}</span></div></div><div class="pr">{e(t["price"])}</div><p>{e(t["text"])}</p></div>' for k, t in enumerate(D.TRANSPORT))
    out.append(f"""<section class="section" id="getting-there"><div class="wrap">
  <div class="section-head"><div class="eyebrow">Getting there</div><h2>Langenfeld → Switzerland</h2><p class="muted">Langenfeld sits on the S6 between Köln and Düsseldorf, which have direct ICEs to Basel. For a group of 5 the train is the best balance of price, comfort and time. A car wins only for the road trip.</p></div>
  <div class="tcards">{tc}</div>
</div></section>""")

    # passes
    prow = "".join(f'<tr><td><b>{e(n)}</b></td><td>{e(pr)}</td><td>{e(best)}</td></tr>' for n, pr, best in D.PASSES)
    out.append(f"""<section class="section alt" id="passes"><div class="wrap">
  <div class="section-head"><div class="eyebrow">Tickets & passes</div><h2>Swiss passes, decoded</h2><p class="muted">Rule of thumb: <b>many long train days → Swiss Travel Pass</b>. <b>One or two bases → Half Fare Card or a regional pass.</b> Always ask your accommodation about free guest cards. 2nd-class adult prices for 2026.</p></div>
  <div class="table-wrap reveal"><table class="compare" style="min-width:720px"><thead><tr><th>Pass</th><th>Price (2026)</th><th>Best for</th></tr></thead><tbody>{prow}</tbody></table></div>
</div></section>""")

    # booking timeline
    tl = "".join(f'<div class="tl reveal" style="--i:{k % 3}"><b>{e(w)}</b><span class="muted">{e(t)}</span></div>' for k, (w, t) in enumerate(D.TIMELINE))
    out.append(f"""<section class="section" id="booking"><div class="wrap">
  <div class="section-head"><div class="eyebrow">Booking timeline</div><h2>How far ahead to book</h2><p class="muted">Today is {e(D.TRIP['researched'])}. Accommodation in the hotspots is the thing to secure first, with free cancellation. Train tickets get more expensive the closer you get. Mountain tickets should be bought last, once you see the weather.</p></div>
  <div class="timeline">{tl}</div>
</div></section>""")

    # hacks + practical
    hk = "".join(f'<div class="tile reveal" style="--i:{k % 3}"><b>{e(t)}</b><span>{e(x)}</span></div>' for k, (t, x) in enumerate(D.HACKS))
    pr = "".join(f'<div class="tile reveal" style="--i:{k % 3}"><b>{e(t)}</b><span>{e(x)}</span></div>' for k, (t, x) in enumerate(D.PRACTICAL))
    out.append(f"""<section class="section alt" id="hacks"><div class="wrap">
  <div class="section-head"><div class="eyebrow">Save money</div><h2>Ten tricks that add up</h2></div>
  <div class="grid3">{hk}</div>
</div></section>
<section class="section" id="practical"><div class="wrap">
  <div class="section-head"><div class="eyebrow">Practical</div><h2>Good to know before you go</h2></div>
  <div class="grid3">{pr}</div>
</div></section>""")

    # sources + credits
    src = "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(t)}</a></li>' for t, u in D.SOURCES)
    credits = json.loads((ROOT / "assets" / "img" / "credits.json").read_text(encoding="utf-8"))
    cr = "".join(f'<li><a href="{e(v["page"])}" target="_blank" rel="noopener">{e(v["title"].replace("File:", ""))}</a>, {e(v["artist"] or "unknown")}, {e(v["license"])}</li>' for v in credits.values())
    out.append(f"""<section class="section alt" id="sources"><div class="wrap">
  <div class="section-head"><div class="eyebrow">Sources</div><h2>Where the numbers come from</h2><p class="muted">Researched on {e(D.TRIP['researched'])}. Prices change: double-check on the official sites before paying. Costs are estimates for planning, not quotes.</p></div>
  <ul class="sources">{src}</ul>
  <details class="credits"><summary>Photo credits (Wikimedia Commons)</summary><ul>{cr}</ul></details>
</div></section>
<footer class="foot">Switzerland 2027 · trip research for 5 · built {e(D.TRIP['researched'])} · edit <code>_source/data.py</code> and run <code>python _source/build.py</code> to update</footer>
<script src="assets/app.js"></script>
</body>
</html>
""")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Markdown summary
# ---------------------------------------------------------------------------
def markdown():
    L = [f"# {D.TRIP['title']}: {D.TRIP['subtitle']}", "",
         f"*Window: {D.TRIP['window']} · group of {D.GROUP} · researched {D.TRIP['researched']} · prices are 2026 tariffs, per person, € at 1 CHF ≈ €{D.EUR_PER_CHF:.2f}*", "",
         "Open `index.html` for the visual version with photos and animated presentations.", "",
         "## The 10 options at a glance", "",
         "| # | Trip | Days | Best time | May / Jun / Jul / Aug | € pp May–Jun | € pp Jul–Aug | Main ticket |", "|---|---|---|---|---|---|---|---|"]
    for k, o in enumerate(D.OPTIONS):
        (b, c), (sb, sc) = totals(o), summer_totals(o)
        rate = " / ".join(D.RATING[v] for _, v, _ in o["season"])
        L.append(f"| {k + 1:02d} | **{o['title']}**: {o['subtitle']} | {o['days']} | {o['best']} | {rate} | €{money(eur(b))}–{money(eur(c))} | €{money(eur(sb))}–{money(eur(sc))} | {o['pass'][0]} |")
    L += ["", "## Our recommendation", ""]
    for label, slug, text in D.PICKS:
        L.append(f"- **{label}:** {text}")
    L += ["", "### 14-day combos", ""]
    for cb in D.COMBOS:
        plan = " → ".join(f"{pl} ({nn} n)" for pl, nn in cb["plan"])
        L.append(f"- **{cb['name']}** ({cb['when']}): {plan}. {cb['why']} Tickets: {cb['transport']}. {cb['cost']}.")
    L += ["", "## When to go", ""]
    for m, chip, text in D.SEASONS:
        L.append(f"- **{m}** ({chip}): {text.replace('<b>', '**').replace('</b>', '**')}")
    L.append("")
    for lbl, txt, _ in D.DATES:
        L.append(f"- {lbl}: {txt}")
    L += ["", "*Starred dates are 2026 opening dates; check again in spring 2027.*", ""]
    for label, (d1, m1), (d2, m2) in D.BANDS:
        L.append(f"- {label}: {d1} {m1} – {d2} {m2} 2027")
    (lo, lo_t), (hi, hi_t), xmin, xmax = summer_range()
    L += ["", "### Is July–August worth it?", "", "**Why it is great**", ""] + [f"- {x}" for x in D.SUMMER_PROS]
    L += ["", "**What you pay for it**", ""] + [f"- {x}" for x in D.SUMMER_CONS]
    L += ["", f"For your group, July–August makes the whole trip ≈ {lo:.0f}–{hi:.0f} % dearer: about €{xmin}–{xmax} more per person. {lo_t} changes least (+{lo:.0f} %) and {hi_t} most (+{hi:.0f} %).",
          "", "## Getting from Langenfeld to Switzerland", ""]
    for t in D.TRANSPORT:
        L.append(f"- **{t['mode']}** ({t['time']}, {t['price']}): {t['text']}")
    L += ["", "## Passes", "", "| Pass | Price (2026) | Best for |", "|---|---|---|"]
    for n, pr, best in D.PASSES:
        L.append(f"| {n} | {pr} | {best} |")
    L += ["", "## Booking timeline", ""]
    for w, t in D.TIMELINE:
        L.append(f"- **{w}:** {t}")
    L += ["", "## Money-saving tricks", ""] + [f"- **{t}:** {x}" for t, x in D.HACKS]
    L += ["", "## Practical", ""] + [f"- **{t}:** {x}" for t, x in D.PRACTICAL]

    for k, o in enumerate(D.OPTIONS):
        b, c = totals(o)
        L += ["", "---", "", f"## Option {k + 1:02d}: {o['title']} ({o['subtitle']})", "", f"> {o['tagline']}", "",
              f"**{o['days']} days / {o['nights']} nights · best {o['best']} 2027 · {o['travel']} · ≈ €{money(eur(b))}–{money(eur(c))} pp**", "",
              f"*{o['best_note']}*", "",
              "**Month by month:** " + " · ".join(f"*{m}: {D.RATING[v]}* ({note})" for m, v, note in o["season"]), "",
              f"**July–August:** ≈ €{money(eur(summer_totals(o)[0]))}–{money(eur(summer_totals(o)[1]))} pp (beds +{round(o['peak'] * 100)} %). {o['summer_tip']}", "",
              "**Route:** Langenfeld → " + " → ".join(f"{pl} ({nn} n)" for pl, nn, _ in o["route"]) + " → home", "", "**Why go**", ""]
        L += [f"- {w}" for w in o["why"]]
        L += ["", "**Day by day**", ""]
        for d, (title, text, tip) in enumerate(o["itinerary"]):
            L.append(f"{d + 1}. **{title}:** {text}" + (f" *Tip: {tip}*" if tip else ""))
        L += ["", "**Where to stay**", ""] + [f"- *{t}:* **{n}**. {desc} ({pr})" for t, n, desc, pr in o["stay"]]
        L += ["", f"**Getting there:** {o['getting_there']}", "", f"**Getting around:** {o['getting_around']}", "",
              "**Costs per person (CHF)**", "", "| Item | Budget | Comfort |", "|---|---:|---:|"]
        L += [f"| {lab} | {money(bb)} | {money(cc)} |" for lab, bb, cc in o["costs"]]
        sb, sc = summer_totals(o)
        L += [f"| **Total May–June** | **{money(b)}** (≈ €{money(eur(b))}) | **{money(c)}** (≈ €{money(eur(c))}) |",
              f"| *Total July–August (estimate)* | *{money(sb)}* (≈ €{money(eur(sb))}) | *{money(sc)}* (≈ €{money(eur(sc))}) |", "",
              "**Hidden gems:** " + "; ".join(f"{g}: {d}" for g, d in o["gems"]), "",
              "**Worth the splurge:** " + "; ".join(f"{n} ({pr}): {w}" for n, pr, w in o["splurges"]), "", "**Good to know**", ""]
        L += [f"- {x}" for x in o["know"]]
        L += ["", "**Booking:** " + " · ".join(f"*{w}:* {t}" for w, t in o["booking"]), "", f"**Make it longer:** {o['stretch']}"]
    L += ["", "---", "", "## Sources", ""] + [f"- [{t}]({u})" for t, u in D.SOURCES]
    L += ["", "Photos: Wikimedia Commons contributors (see credits on the overview page)."]
    return "\n".join(L) + "\n"


def main():
    OPT_DIR.mkdir(exist_ok=True)
    for i, opt in enumerate(D.OPTIONS):
        (OPT_DIR / f"{opt['slug']}.html").write_text(option_page(i, opt), encoding="utf-8")
    (ROOT / "index.html").write_text(index_page(), encoding="utf-8")
    (ROOT / "trip-plan.md").write_text(markdown(), encoding="utf-8")
    for o in D.OPTIONS:
        (b, c), (sb, sc) = totals(o), summer_totals(o)
        print(f"{o['slug']:28s} CHF {b:>5}-{c:<5}  EUR {eur(b):>5}-{eur(c):<5}  Jul-Aug EUR {eur(sb):>5}-{eur(sc):<5}")
    print("built index.html, trip-plan.md and", len(D.OPTIONS), "option decks")


if __name__ == "__main__":
    main()

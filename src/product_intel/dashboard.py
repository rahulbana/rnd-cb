"""Render a self-contained interactive PM dashboard from a report.

Produces a single static HTML file (no external assets, no network) summarizing
strengths, gaps, sentiment clusters and the prioritized vNext backlog.
"""

from __future__ import annotations

import html
from typing import List

from .schemas import ProductReviewReport

_PRIORITY_COLOR = {"P0": "#c0392b", "P1": "#d68910", "P2": "#2471a3"}


def _bar(pct: float, color: str) -> str:
    pct = max(0.0, min(100.0, pct))
    return (
        f'<div class="bar"><div class="bar-fill" style="width:{pct:.0f}%;'
        f'background:{color}"></div></div>'
    )


def _esc(text: str) -> str:
    return html.escape(str(text))


def render_dashboard(report: ProductReviewReport) -> str:
    d = report.to_dict()
    ps = d["product_summary"]

    strengths_rows = "".join(
        f"<tr><td>{_esc(s['feature'])}</td>"
        f"<td>{_bar(s['sentiment_score'] * 100, '#27ae60')}"
        f"<span class='num'>{s['sentiment_score']:.2f}</span></td>"
        f"<td>{s['mention_frequency']}</td>"
        f"<td class='quotes'>{'<br>'.join('“' + _esc(q) + '”' for q in s['key_highlights'])}</td></tr>"
        for s in d["core_strengths"]
    ) or "<tr><td colspan='4' class='empty'>No standout strengths detected.</td></tr>"

    gaps_rows = "".join(
        f"<tr><td>{_esc(g['feature'])}</td>"
        f"<td>{_bar(g['sentiment_score'] * 100, '#e67e22')}"
        f"<span class='num'>{g['sentiment_score']:.2f}</span></td>"
        f"<td>{g.get('mention_frequency', 0)}</td>"
        f"<td>{_esc(g['gap_description'])}</td></tr>"
        for g in d["feature_gaps"]
    ) or "<tr><td colspan='4' class='empty'>No feature gaps detected.</td></tr>"

    cluster_rows = "".join(
        f"<tr><td>{_esc(c['name'])}</td><td>{c['mention_frequency']}</td>"
        f"<td>{_bar(c['sentiment_score'] * 100, '#2980b9')}"
        f"<span class='num'>{c['sentiment_score']:.2f}</span></td>"
        f"<td><span class='pos'>{c['positive']}+</span> "
        f"<span class='neu'>{c['neutral']}=</span> "
        f"<span class='neg'>{c['negative']}−</span></td></tr>"
        for c in d.get("diagnostics", {}).get("clusters", [])
    )

    backlog_cards = "".join(_backlog_card(b) for b in d["vnext_backlog"]) or (
        "<p class='empty'>No backlog items generated.</p>"
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(ps['name'])} — vNext Intelligence</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
    margin: 0; background: #f4f6f8; color: #1c2833; }}
  header {{ background: #1c2833; color: #fff; padding: 28px 32px; }}
  header h1 {{ margin: 0 0 6px; font-size: 22px; }}
  header .sub {{ opacity: .8; font-size: 13px; }}
  .kpis {{ display: flex; flex-wrap: wrap; gap: 16px; padding: 24px 32px; }}
  .kpi {{ background: #fff; border-radius: 10px; padding: 16px 20px; flex: 1 1 160px;
    box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
  .kpi .v {{ font-size: 26px; font-weight: 700; }}
  .kpi .l {{ font-size: 12px; color: #7f8c8d; text-transform: uppercase; letter-spacing: .04em; }}
  section {{ padding: 8px 32px 24px; }}
  h2 {{ font-size: 16px; border-left: 4px solid #2980b9; padding-left: 10px; margin: 22px 0 12px; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 10px;
    overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.08); font-size: 13px; }}
  th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #ecf0f1; vertical-align: top; }}
  th {{ background: #eef2f5; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #566573; }}
  .bar {{ display: inline-block; width: 90px; height: 8px; background: #e5e8eb; border-radius: 4px;
    overflow: hidden; vertical-align: middle; margin-right: 6px; }}
  .bar-fill {{ height: 100%; }}
  .num {{ font-variant-numeric: tabular-nums; font-size: 12px; color: #566573; }}
  .quotes {{ color: #566573; font-style: italic; }}
  .empty {{ color: #95a5a6; font-style: italic; }}
  .pos {{ color: #27ae60; }} .neg {{ color: #c0392b; }} .neu {{ color: #7f8c8d; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }}
  .card {{ background: #fff; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.08);
    border-top: 4px solid #ccc; }}
  .card .tid {{ font-size: 11px; color: #95a5a6; font-weight: 700; }}
  .card h3 {{ margin: 4px 0 8px; font-size: 15px; }}
  .pill {{ display: inline-block; color: #fff; font-size: 11px; font-weight: 700; padding: 2px 8px;
    border-radius: 10px; }}
  .card .meta {{ font-size: 12px; color: #566573; margin: 8px 0; }}
  .card .story {{ font-size: 13px; margin: 8px 0; }}
  .card ul {{ margin: 6px 0 0 18px; padding: 0; font-size: 12px; color: #566573; }}
  .rice {{ font-size: 11px; color: #7f8c8d; margin-top: 8px; font-variant-numeric: tabular-nums; }}
  footer {{ padding: 20px 32px 40px; font-size: 11px; color: #95a5a6; }}
</style></head>
<body>
<header>
  <h1>{_esc(ps['name'])}</h1>
  <div class="sub">{_esc(ps.get('manufacturer',''))} · {_esc(ps['product_id'])} ·
    Analysis engine: {_esc(ps.get('llm_provider','offline'))}</div>
</header>
<div class="kpis">
  <div class="kpi"><div class="v">{ps['average_star_rating']}</div><div class="l">Avg Star Rating</div></div>
  <div class="kpi"><div class="v">{int(ps['positive_sentiment_ratio']*100)}%</div><div class="l">Positive Sentiment</div></div>
  <div class="kpi"><div class="v">{ps['total_reviews_analyzed']}</div><div class="l">Reviews Analyzed</div></div>
  <div class="kpi"><div class="v">{ps.get('reviews_filtered_out',0)}</div><div class="l">Noise Filtered</div></div>
  <div class="kpi"><div class="v">{len(d['vnext_backlog'])}</div><div class="l">Backlog Tickets</div></div>
</div>

<section>
  <h2>Core Strengths — Differentiators</h2>
  <table><thead><tr><th>Feature</th><th>Sentiment</th><th>Mentions</th><th>Highlights</th></tr></thead>
  <tbody>{strengths_rows}</tbody></table>

  <h2>Feature Gaps — Expectation Mismatches</h2>
  <table><thead><tr><th>Feature</th><th>Sentiment</th><th>Mentions</th><th>Gap</th></tr></thead>
  <tbody>{gaps_rows}</tbody></table>

  <h2>Sentiment by Functional Cluster</h2>
  <table><thead><tr><th>Cluster</th><th>Mentions</th><th>Sentiment</th><th>Polarity (+ = −)</th></tr></thead>
  <tbody>{cluster_rows}</tbody></table>

  <h2>Prioritized vNext Backlog</h2>
  <div class="cards">{backlog_cards}</div>
</section>
<footer>Generated by product-intel · {_esc(d.get('diagnostics',{}).get('generated_on',''))}</footer>
</body></html>"""


def _backlog_card(b: dict) -> str:
    color = _PRIORITY_COLOR.get(b["priority"], "#7f8c8d")
    criteria = "".join(f"<li>{_esc(c)}</li>" for c in b.get("acceptance_criteria", []))
    rice = b.get("rice")
    rice_html = (
        f"<div class='rice'>RICE {rice['score']} "
        f"(R {rice['reach']} · I {rice['impact']} · C {rice['confidence']} · E {rice['effort']})</div>"
        if rice else ""
    )
    return (
        f"<div class='card' style='border-top-color:{color}'>"
        f"<div class='tid'>{_esc(b['ticket_id'])} · {_esc(b['type'])}</div>"
        f"<h3>{_esc(b['title'])}</h3>"
        f"<span class='pill' style='background:{color}'>{_esc(b['priority'])}</span>"
        f"<div class='meta'>Impact: {_esc(b['frequency_impact'])}</div>"
        f"<div class='story'><b>Story:</b> {_esc(b.get('user_story',''))}</div>"
        f"<div class='meta'><b>Proposed action:</b> {_esc(b['proposed_action'])}</div>"
        f"<div><b style='font-size:12px'>Acceptance criteria</b><ul>{criteria}</ul></div>"
        f"{rice_html}</div>"
    )

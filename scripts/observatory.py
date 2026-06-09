#!/usr/bin/env python3
"""MCHPAI Observation Center — real-time mission-control dashboard.

A single-file, dependency-free (stdlib only) web server that reads the
acquisition / analysis / ml stores READ-ONLY and serves a live, auto-refreshing
dashboard so you can watch the observatory in real time:

  * live counters (births, tokens, swaps, snapshots) + milestone ladder
  * incoming token-birth feed
  * top movers (by peak multiple) and most-active tokens
  * repeat creators and cross-token wallets (candidate snipers / smart money)
  * pattern-analysis findings (from scripts/analyze.py)
  * win/loss model accuracy history (from scripts/predict.py)

It only displays; acquisition/analysis/prediction run as their own processes.

    python scripts/observatory.py            # serve on :8888
    OBSERVATORY_PORT=9000 python scripts/observatory.py
"""

from __future__ import annotations

import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ACQ_DB = os.environ.get("ACQUIRE_DB", "data/acquisition.db")
ANALYSIS_DB = os.environ.get("ANALYSIS_DB", "data/analysis.db")
ML_DB = os.environ.get("ML_DB", "data/ml.db")
PATTERNS_PATH = "data/analysis/patterns.json"
PORT = int(os.environ.get("OBSERVATORY_PORT", "8888"))


def ro(path: str):
    if not os.path.exists(path):
        return None
    try:
        return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    except Exception:
        return None


def q(conn, sql, args=()):
    try:
        return conn.execute(sql, args).fetchall()
    except Exception:
        return []


# ------------------------------------------------------------------ data api
def api_stats() -> dict:
    acq = ro(ACQ_DB)
    out = {"births": 0, "tokens": 0, "swaps": 0, "snapshots": 0}
    if acq:
        out["births"] = (q(acq, "SELECT count(*) FROM token_births") or [[0]])[0][0]
        out["swaps"] = (q(acq, "SELECT count(*) FROM swaps") or [[0]])[0][0]
        out["snapshots"] = (q(acq, "SELECT count(*) FROM snapshots") or [[0]])[0][0]
        out["tokens"] = (q(acq, "SELECT count(*) FROM (SELECT mint FROM token_births "
                              "UNION SELECT mint FROM swaps)") or [[0]])[0][0]
        acq.close()
    out["milestones"] = {
        "snapshots_1M": {"value": out["snapshots"], "target": 1_000_000},
        "tokens_10k": {"value": out["tokens"], "target": 10_000},
        "tokens_100k": {"value": out["tokens"], "target": 100_000},
    }
    return out


def api_births() -> list:
    acq = ro(ACQ_DB)
    if not acq:
        return []
    rows = q(acq, "SELECT mint, creator, launchpad, birth_timestamp FROM token_births "
                  "ORDER BY birth_timestamp DESC LIMIT 30")
    acq.close()
    return [{"mint": r[0], "creator": r[1], "launchpad": r[2], "ts": r[3]} for r in rows]


def _reports() -> list:
    store = ro(ANALYSIS_DB)
    if not store:
        return []
    rows = q(store, "SELECT report FROM reports")
    store.close()
    out = []
    for (r,) in rows:
        try:
            out.append(json.loads(r))
        except Exception:
            pass
    return out


def api_top() -> dict:
    reps = [r for r in _reports() if r.get("status") == "analyzed"]
    movers = sorted(reps, key=lambda r: -(r.get("max_multiple") or 0))[:15]
    active = sorted(reps, key=lambda r: -(r.get("n_swaps") or 0))[:15]

    def slim(r):
        return {k: r.get(k) for k in ("mint", "max_multiple", "volume_sol",
                "unique_buyers", "n_swaps", "flow_imbalance", "outcome", "launchpad")}
    return {"movers": [slim(r) for r in movers], "active": [slim(r) for r in active]}


def api_patterns() -> dict:
    if os.path.exists(PATTERNS_PATH):
        try:
            return json.load(open(PATTERNS_PATH))
        except Exception:
            pass
    return {"note": "run scripts/analyze.py to generate patterns"}


def api_ml() -> list:
    db = ro(ML_DB)
    if not db:
        return []
    rows = q(db, "SELECT ts,n_samples,n_pos,baseline_acc,accuracy,auc,cv_auc_mean,"
                 "beats_baseline FROM runs ORDER BY ts DESC LIMIT 20")
    db.close()
    return [{"ts": r[0], "n": r[1], "wins": r[2], "baseline": r[3], "acc": r[4],
             "auc": r[5], "cv_auc": r[6], "beats": bool(r[7])} for r in rows]


ROUTES = {
    "/api/stats": api_stats, "/api/births": api_births, "/api/top": api_top,
    "/api/patterns": api_patterns, "/api/ml": api_ml,
}

# ----------------------------------------------------------------------- html
PAGE = r"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>MCHPAI — Observation Center</title>
<style>
:root{--bg:#0a0e14;--panel:#121821;--line:#1e2733;--txt:#c9d4e0;--dim:#6b7a8d;
--accent:#37e8b4;--warn:#f5a623;--bad:#ff5c5c;--good:#37e8b4}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);
font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
header{display:flex;align-items:center;gap:16px;padding:14px 20px;
border-bottom:1px solid var(--line);background:#0c121b;position:sticky;top:0;z-index:9}
header h1{font-size:15px;margin:0;letter-spacing:1px}
header .dot{width:9px;height:9px;border-radius:50%;background:var(--accent);
box-shadow:0 0 10px var(--accent);animation:pulse 1.6s infinite}
@keyframes pulse{50%{opacity:.35}}
.upd{margin-left:auto;color:var(--dim);font-size:11px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:16px 20px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px}
.card.full{grid-column:1/-1}.card.half{grid-column:span 2}
.k{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:1px}
.big{font-size:30px;font-weight:600;margin-top:4px}
.big.accent{color:var(--accent)}
h2{font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:1px;
margin:0 0 10px;border-bottom:1px solid var(--line);padding-bottom:8px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{color:var(--dim);text-align:left;font-weight:500;padding:4px 8px;border-bottom:1px solid var(--line)}
td{padding:4px 8px;border-bottom:1px solid #161d27}
td.mono{font-family:ui-monospace;color:var(--dim)}
.mult{color:var(--good);font-weight:600}.neg{color:var(--bad)}
.bar{height:7px;background:#0c121b;border-radius:4px;overflow:hidden;margin-top:6px}
.bar>div{height:100%;background:linear-gradient(90deg,#1f9c7a,var(--accent))}
.pill{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;
background:#16202c;color:var(--dim)}
.feed{max-height:340px;overflow:auto}.feed div{padding:5px 0;border-bottom:1px solid #161d27}
.row{display:flex;justify-content:space-between;gap:10px}
.muted{color:var(--dim)}.warn{color:var(--warn)}.good{color:var(--good)}.bad{color:var(--bad)}
a{color:var(--accent);text-decoration:none}.tag{font-size:10px;color:var(--dim)}
.note{color:var(--warn);font-size:11px;margin-top:6px}
</style></head><body>
<header><span class=dot></span><h1>MCHPAI · OBSERVATION CENTER</h1>
<span class=upd id=upd>connecting…</span></header>

<div class=grid>
  <div class=card><div class=k>Token Births</div><div class="big accent" id=c_births>—</div></div>
  <div class=card><div class=k>Tokens Tracked</div><div class=big id=c_tokens>—</div></div>
  <div class=card><div class=k>Swaps Parsed</div><div class=big id=c_swaps>—</div></div>
  <div class=card><div class=k>Snapshots</div><div class=big id=c_snaps>—</div></div>

  <div class="card half"><h2>Milestone Ladder</h2><div id=milestones></div></div>
  <div class="card half"><h2>Win/Loss Model — Accuracy History</h2>
    <table><thead><tr><th>time</th><th>N</th><th>win</th><th>base</th><th>acc</th>
    <th>AUC</th><th>CV-AUC</th><th>edge?</th></tr></thead><tbody id=ml></tbody></table>
    <div class=note id=ml_note></div></div>

  <div class="card half"><h2>Top Movers (peak multiple)</h2>
    <table><thead><tr><th>token</th><th>×</th><th>vol◎</th><th>buyers</th><th>outcome</th>
    </tr></thead><tbody id=movers></tbody></table></div>
  <div class="card half"><h2>Live Birth Feed</h2><div class=feed id=births></div></div>

  <div class="card half"><h2>Repeat Creators</h2>
    <table><thead><tr><th>creator</th><th>launches</th><th>median ×</th></tr></thead>
    <tbody id=creators></tbody></table></div>
  <div class="card half"><h2>Cross-Token Wallets (candidate snipers)</h2>
    <table><thead><tr><th>wallet</th><th>tokens</th></tr></thead>
    <tbody id=wallets></tbody></table></div>

  <div class="card full"><h2>Pattern Analysis — correlations & consistencies</h2>
    <div class=row><div id=corr style=flex:1></div><div id=consist style=flex:1></div></div>
    <div class=note id=hyp></div></div>
</div>

<script>
const $=id=>document.getElementById(id);
const fmt=n=>n==null?'—':n.toLocaleString();
const short=s=>s?s.slice(0,4)+'…'+s.slice(-4):'—';
async function j(u){try{return await(await fetch(u)).json()}catch(e){return null}}
function bar(label,v,t){const p=Math.min(100,100*v/t);
 return `<div class=row><span class=muted>${label}</span><span>${fmt(v)} / ${fmt(t)}
 <span class=tag>(${p.toFixed(p<1?3:1)}%)</span></span></div><div class=bar><div style="width:${Math.max(0.4,p)}%"></div></div>`}
async function tick(){
 const s=await j('/api/stats'); if(s){
  $('c_births').textContent=fmt(s.births);$('c_tokens').textContent=fmt(s.tokens);
  $('c_swaps').textContent=fmt(s.swaps);$('c_snaps').textContent=fmt(s.snapshots);
  const m=s.milestones;$('milestones').innerHTML=
   bar('1,000,000 snapshots',m.snapshots_1M.value,m.snapshots_1M.target)+
   bar('10,000 tokens',m.tokens_10k.value,m.tokens_10k.target)+
   bar('100,000 tokens',m.tokens_100k.value,m.tokens_100k.target);
 }
 const top=await j('/api/top');
 if(top&&top.movers){$('movers').innerHTML=top.movers.map(r=>`<tr>
  <td class=mono>${short(r.mint)}</td><td class=mult>${(r.max_multiple||0).toFixed(2)}×</td>
  <td>${(r.volume_sol||0).toFixed(2)}</td><td>${r.unique_buyers??'—'}</td>
  <td class=tag>${r.outcome||'—'}</td></tr>`).join('')||'<tr><td class=muted>no data</td></tr>';}
 const b=await j('/api/births');
 if(b){$('births').innerHTML=b.map(x=>`<div class=row><span class=mono>${short(x.mint)}</span>
  <span class=tag>${x.launchpad||''} · ${x.ts?new Date(x.ts*1000).toLocaleTimeString():''}</span></div>`).join('')
  ||'<div class=muted>awaiting births…</div>';}
 const ml=await j('/api/ml');
 if(ml){$('ml').innerHTML=ml.map(r=>`<tr><td class=mono>${new Date(r.ts*1000).toLocaleTimeString()}</td>
  <td>${r.n}</td><td>${r.wins}</td><td>${(r.baseline||0).toFixed(2)}</td><td>${(r.acc||0).toFixed(2)}</td>
  <td>${r.auc!=null?r.auc.toFixed(2):'—'}</td><td class="${r.cv_auc<0.5?'bad':'good'}">${r.cv_auc!=null?r.cv_auc.toFixed(2):'—'}</td>
  <td class="${r.beats?'good':'bad'}">${r.beats?'YES':'no'}</td></tr>`).join('')||'<tr><td class=muted>no runs</td></tr>';
  $('ml_note').textContent=ml.length&&!ml[0].beats?'Model does not yet beat baseline — needs more, matured data.':'';}
 const p=await j('/api/patterns');
 if(p){
  if(p.repeat_creators){$('creators').innerHTML=Object.entries(p.repeat_creators).map(([c,v])=>
   `<tr><td class=mono>${short(c)}</td><td>${v.launches}</td><td class=mult>${v.median_multiple}×</td></tr>`).join('');}
  if(p.cross_token_wallets){$('wallets').innerHTML=p.cross_token_wallets.map(w=>
   `<tr><td class=mono>${short(w.wallet)}</td><td>${w.tokens_traded}</td></tr>`).join('');}
  if(p.correlations_with_max_multiple){$('corr').innerHTML='<h2>corr → peak multiple</h2>'+
   Object.entries(p.correlations_with_max_multiple).map(([k,v])=>
   `<div class=row><span class=muted>${k}</span><span class="${Math.abs(v)>=0.2?'good':''}">${v}</span></div>`).join('');}
  if(p.consistencies){$('consist').innerHTML='<h2>consistencies</h2>'+
   Object.entries(p.consistencies).map(([k,v])=>
   `<div class=row><span class=muted>${k}</span><span>${typeof v=='object'?JSON.stringify(v):v}</span></div>`).join('');}
  if(p.hypotheses)$('hyp').innerHTML=(p.caveat?('⚠ '+p.caveat+'<br>'):'')+p.hypotheses.map(h=>'• '+h).join('<br>');
  else if(p.note)$('hyp').textContent=p.note;
 }
 $('upd').textContent='live · updated '+new Date().toLocaleTimeString();
}
tick();setInterval(tick,4000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ROUTES:
            self._send(200, "application/json", json.dumps(ROUTES[path]()).encode())
        elif path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", PAGE.encode())
        elif path == "/healthz":
            self._send(200, "application/json", b'{"status":"ok"}')
        else:
            self._send(404, "text/plain", b"not found")

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"MCHPAI Observation Center → http://localhost:{PORT}  (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()

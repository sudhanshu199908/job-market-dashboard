"""
03_build_dashboard.py — generate the self-contained interactive dashboard.

Reads analysis/findings.json, inlines plotly.js (no external fetches — the
file works by double-click, offline), and writes dashboard.html.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FINDINGS = json.loads((HERE / "findings.json").read_text())
_PLOTLY = HERE / "vendor" / "plotly.min.js"
if not _PLOTLY.exists():  # ephemeral fallback
    _PLOTLY = Path("/tmp/plotly.min.js")
PLOTLY_JS = _PLOTLY.read_text()

f = FINDINGS
CYAN, VIOLET, AMBER, EMERALD, ROSE, BLUE, GRAY = (
    "#22d3ee", "#a78bfa", "#fbbf24", "#34d399", "#fb7185", "#60a5fa", "#6b7280")

# ---- derived strings for the findings section ----
trend = f["trend"]
wm = f["work_mode"]
sc = f["stream_compare"]
topc = f["top_companies"]
exp = f["experience"]

kpi_cards = [
    ("Applications analyzed", f"{f['n_total']}",
     f"{sc['analyst']['n']} analyst · {sc['support']['n']} support", CYAN),
    ("Median disclosed salary", f"₹{f['salary_median']} LPA",
     f"n={f['salary_n']} disclosing postings", EMERALD),
    ("Remote share", f"{f['work_mode_known_pct_remote']}%",
     f"of {f['work_mode_n_known']} postings with known mode", VIOLET),
    ("Most-mentioned skill", f["top_skill"]["name"].upper(),
     f"{f['top_skill']['count']} mentions · n={f['skills_n']} notes", AMBER),
    ("Busiest day", f"{trend['peak_day'][5:]}",
     f"{trend['peak_count']} applications in one day", ROSE),
]

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data Job-Market Dashboard — 520 real applications, Oct 2026</title>
<style>
  :root{
    --bg:#0b0f1a; --card:#121828; --card2:#0f1524;
    --line:rgba(255,255,255,.08); --txt:#e8edf5; --mut:#93a0b8;
    --cyan:#22d3ee; --violet:#a78bfa; --amber:#fbbf24; --emerald:#34d399; --rose:#fb7185;
  }
  *{box-sizing:border-box}
  body{margin:0;background:radial-gradient(1200px 600px at 80% -10%,#16233d 0%,var(--bg) 55%) fixed,var(--bg);
       color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,"Helvetica Neue",Arial,sans-serif;}
  .wrap{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
  header.top{border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:26px}
  .kicker{font-size:12px;letter-spacing:.22em;color:var(--cyan);text-transform:uppercase;margin-bottom:10px}
  h1{font-size:clamp(30px,4.6vw,52px);margin:0 0 10px;line-height:1.08;
     background:linear-gradient(92deg,#fff 20%,var(--cyan) 60%,var(--violet) 100%);
     -webkit-background-clip:text;background-clip:text;color:transparent;font-weight:800}
  .sub{color:var(--mut);font-size:15px;max-width:760px;line-height:1.6}
  .sub b{color:var(--txt)}
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin:26px 0 8px}
  .kpi{background:linear-gradient(180deg,var(--card),var(--card2));border:1px solid var(--line);
       border-radius:16px;padding:18px 18px 14px;position:relative;overflow:hidden}
  .kpi::before{content:"";position:absolute;top:0;left:0;right:0;height:3px;background:var(--ac,#22d3ee);opacity:.85}
  .kpi .num{font-size:32px;font-weight:800;margin:2px 0 4px}
  .kpi .lbl{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut)}
  .kpi .n{font-size:12px;color:var(--mut);margin-top:6px}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}
  @media(max-width:860px){.grid{grid-template-columns:1fr}}
  .card{background:linear-gradient(180deg,var(--card),var(--card2));border:1px solid var(--line);
        border-radius:16px;padding:18px 16px 8px;min-width:0}
  .card h2{font-size:16px;margin:2px 4px 2px;font-weight:700}
  .card p.cap{font-size:12.5px;color:var(--mut);margin:4px 4px 6px;line-height:1.5}
  .card p.cap b{color:var(--txt)}
  .plot{width:100%;height:340px}
  .tall{height:400px}
  section.findings{margin-top:26px;background:linear-gradient(180deg,var(--card),var(--card2));
        border:1px solid var(--line);border-radius:16px;padding:22px 24px}
  section.findings h2, section.method h2{font-size:18px;margin:0 0 12px}
  ol.find{margin:0;padding-left:22px;display:grid;gap:12px}
  ol.find li{line-height:1.65;font-size:14.5px;color:#d7deeb}
  ol.find li b{color:#fff}
  ol.find li .nn{color:var(--mut);font-size:12.5px}
  section.method{margin-top:16px;background:linear-gradient(180deg,var(--card),var(--card2));
        border:1px solid var(--line);border-radius:16px;padding:22px 24px}
  table.cov{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0 4px}
  table.cov th,table.cov td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line)}
  table.cov th{color:var(--mut);font-weight:600;font-size:12px;letter-spacing:.06em;text-transform:uppercase}
  ul.cav{margin:8px 0 0;padding-left:20px;display:grid;gap:8px;font-size:13.5px;color:#c6cfdf;line-height:1.6}
  footer{margin-top:28px;color:var(--mut);font-size:13px;text-align:center;line-height:1.7}
  footer a{color:var(--cyan);text-decoration:none}
  .thin{font-size:12px;color:var(--amber)}
</style>
</head>
<body>
<div class="wrap">

<header class="top">
  <div class="kicker">Portfolio project · SQL · Python · Plotly</div>
  <h1>What 520 real job applications taught me about the data job market</h1>
  <p class="sub">In October 2026 I ran a high-volume job search — <b>403 Data/BI/MIS applications</b>
  plus <b>117 remote support &amp; writing applications</b> — and logged every posting in a structured
  ledger. This dashboard analyses that ledger: real postings, real salary bands, real skill mentions.
  Every number below traces to the data — thin samples are labelled, unknowns are shown, nothing is invented.</p>
</header>

<div class="kpis">
__KPIS__
</div>

<div class="grid">
  <div class="card"><h2>Applications per day</h2>
    <p class="cap">Daily volume across both streams, <b>6–15 Oct 2026</b> · n=__TREND_N__ dated entries</p>
    <div id="ch_trend" class="plot"></div></div>
  <div class="card"><h2>Where would I work?</h2>
    <p class="cap">Work-mode split · <b>__REMOTE_PCT__% remote</b> of __MODE_N__ postings with a known mode
    (45% of postings don't state it — shown as unknown)</p>
    <div id="ch_mode" class="plot"></div></div>
  <div class="card"><h2>Disclosed salaries by work mode</h2>
    <p class="cap">Midpoints of stated bands · <b>n=__SAL_N__</b>. <span class="thin">On-site n=6 and hybrid n=3 are thin — treat the gap as suggestive, not conclusive.</span></p>
    <div id="ch_salary" class="plot"></div></div>
  <div class="card"><h2>Salary by city (median of band midpoints)</h2>
    <p class="cap">Cities with ≥4 disclosing postings · n=__SAL_N__ total</p>
    <div id="ch_city" class="plot"></div></div>
  <div class="card"><h2>Skill demand (mentions in posting notes)</h2>
    <p class="cap">Keywords found while logging postings — <b>directional, not exhaustive</b> · n=__SK_N__ notes with skill info</p>
    <div id="ch_skills" class="plot"></div></div>
  <div class="card"><h2>Who's hiring? (top companies by applications)</h2>
    <p class="cap">One employer — crewlia — accounts for <b>__CREWLIA_N__ of 117</b> support-stream applications</p>
    <div id="ch_comp" class="plot tall"></div></div>
  <div class="card"><h2>Experience asked for</h2>
    <p class="cap">Minimum experience in the posting · n=__EXP_N__ · <b>no posting asked for 6+ years</b></p>
    <div id="ch_exp" class="plot"></div></div>
  <div class="card"><h2>Analyst stream vs support stream</h2>
    <p class="cap">Same candidate, two searches: how pay and remote-share differ</p>
    <div id="ch_stream" class="plot"></div></div>
</div>

<section class="findings">
  <h2>Key findings</h2>
  <ol class="find">
    <li><b>Volume wins attention, targeting wins interviews.</b> 520 applications in 10 days —
      403 analyst + 117 support — peaking at <b>64 in a single day (12 Oct)</b>.
      <span class="nn">n=520 ledger entries</span></li>
    <li><b>The junior data market is overwhelmingly remote.</b> <b>__REMOTE_PCT__% of postings</b>
      with a stated work mode were remote; hybrid was rare (7%).
      <span class="nn">n=__MODE_N__ known modes; 45% of postings don't state a mode</span></li>
    <li><b>Disclosed pay centres near my target.</b> Median disclosed band midpoint is
      <b>₹__SAL_MED__ LPA</b> (IQR ₹__SAL_P25__–₹__SAL_P75__) — inside my ₹3–12 LPA analyst band.
      Analyst-stream median (₹__A_MED__ LPA) sits well above support-stream median (₹__S_MED__ LPA).
      <span class="nn">n=__SAL_N__ disclosing postings</span></li>
    <li><b>Remote postings disclose slightly lower bands</b> — median ₹4.75 LPA remote vs ₹5.45 LPA
      on-site — but the on-site sample is tiny, so I read this as <b>suggestive, not proof</b>.
      <span class="nn">remote n=51 · on-site n=6 · hybrid n=3</span></li>
    <li><b>MIS is the most-mentioned skill, then Power BI and SQL.</b> MIS (47), Power BI (23),
      SQL (22), Excel (17) lead; Python (7) and Tableau (6) trail — matching a market that hires
      <b>report-builders first, modellers second</b> at the junior level.
      <span class="nn">n=__SK_N__ posting notes with skill info; notes undercount full JDs</span></li>
    <li><b>Employers cluster.</b> crewlia (33), HRM Counsel (20) and Jobgether (8) dominate —
      aggregators and high-volume hirers, not Big Tech. <b>45% of postings ask for 0 years
      experience</b> (106 of 235 with a stated band); none asked for 6+.
      <span class="nn">n=__EXP_N__ with experience bands</span></li>
  </ol>
</section>

<section class="method">
  <h2>Methodology &amp; honest caveats</h2>
  <table class="cov">
    <tr><th>Field</th><th>Parsed</th><th>Coverage</th><th>Note</th></tr>
    __COV_ROWS__
  </table>
  <ul class="cav">
    <li>Source: my own verified application ledger, 6–15 Oct 2026 (LinkedIn, Naukri, Instahyre, Shine, Internshala, Foundit, email/direct, Rohtak round). No scraped or third-party data.</li>
    <li>Salaries are thin (16% disclose) and skew toward staffing firms/startups; hourly contract rates ($/hr) are excluded from LPA charts to avoid distortion.</li>
    <li>Skill counts come from my logging notes (titles + screening questions), not full job descriptions — directional only.</li>
    <li>My own screening answers (e.g. “3 LPA current”) were stripped before parsing, so bands are the postings' requirements, never my responses.</li>
    <li>Pipeline: ledger JSON → regex parsing (<span style="font-family:monospace">analysis/01_parse_ledger.py</span>) → pandas EDA (<span style="font-family:monospace">analysis/02_eda.py</span>) → this page. Re-run to reproduce.</li>
  </ul>
</section>

<footer>
  Built by <b>Sudhanshu Dhankhar</b> · MBA Business Analytics · SQL · Python · Power BI<br>
  <span style="color:#5b6b87">Data: 520 real job postings from my October 2026 job search · Charts: Plotly (offline bundle) · No tracking, no external requests</span>
</footer>

</div>
<script>__PLOTLY__</script>
<script>
const F = __FINDINGS__;
const T = (c)=>({color:"#e8edf5",family:"-apple-system,'Segoe UI',Inter,Roboto,sans-serif"});
const mkL = () => ({paper_bgcolor:"rgba(0,0,0,0)",plot_bgcolor:"rgba(0,0,0,0)",font:T(),
  margin:{l:56,r:16,t:14,b:44},xaxis:{gridcolor:"#1c2436",zerolinecolor:"#1c2436"},
  yaxis:{gridcolor:"#1c2436",zerolinecolor:"#1c2436"}});
const C=["#22d3ee","#a78bfa","#fbbf24","#34d399","#fb7185","#60a5fa"];

// 1. trend
const L1 = mkL();
Plotly.newPlot("ch_trend",[
  {x:F.trend.dates.map(d=>d.slice(5)),y:F.trend.analyst,name:"Analyst",type:"bar",marker:{color:C[0]}},
  {x:F.trend.dates.map(d=>d.slice(5)),y:F.trend.support,name:"Support",type:"bar",marker:{color:C[1]}}],
  {...L1,barmode:"stack",showlegend:true,legend:{orientation:"h",x:.5,y:1.12,xanchor:"center"},
   yaxis:{...L1.yaxis,title:"Applications"},xaxis:{...L1.xaxis,type:"category"}});

// 2. work-mode donut
const wm=F.work_mode, wlab={remote:"Remote",hybrid:"Hybrid","on-site":"On-site",unknown:"Unknown"};
const L2 = mkL();
Plotly.newPlot("ch_mode",[{labels:Object.keys(wm).map(k=>wlab[k]||k),values:Object.values(wm),type:"pie",
  hole:.58,marker:{colors:[C[0],C[1],C[2],C[5]],line:{color:"#0b0f1a",width:3}},
  textinfo:"label+percent",hovertemplate:"%{label}: %{value} postings<extra></extra>"}],
  {...L2,showlegend:false,margin:{l:16,r:16,t:14,b:14},
   annotations:[{text:"n="+F.n_total,x:.5,y:.5,font:{size:15,color:"#93a0b8"},showarrow:false}]});

// 3. salary box by mode
const modes=Object.keys(F.salary_values_by_mode).filter(m=>m!=="unknown");
const L3 = mkL();
Plotly.newPlot("ch_salary",modes.map((m,i)=>({y:F.salary_values_by_mode[m],type:"box",name:m+" (n="+F.salary_values_by_mode[m].length+")",
  marker:{color:C[i%6]},boxpoints:"outliers"})),
  {...L3,showlegend:false,yaxis:{...L3.yaxis,title:"₹ LPA (band midpoint)"}});

// 4. salary by city
const cities=Object.keys(F.salary_by_city);
const L4 = mkL();
Plotly.newPlot("ch_city",[{x:cities,y:cities.map(c=>F.salary_by_city[c].median),type:"bar",
  marker:{color:C[3]},text:cities.map(c=>"n="+F.salary_by_city[c].n),textposition:"outside",
  hovertemplate:"%{x}: ₹%{y} LPA median<br>%{text}<extra></extra>"}],
  {...L4,showlegend:false,yaxis:{...L4.yaxis,title:"Median ₹ LPA"}});

// 5. skills
const sk=Object.entries(F.skills).sort((a,b)=>b[1]-a[1]).slice(0,10);
const L5 = mkL();
Plotly.newPlot("ch_skills",[{y:sk.map(s=>s[0]).reverse(),x:sk.map(s=>s[1]).reverse(),type:"bar",
  orientation:"h",marker:{color:C[0]},hovertemplate:"%{y}: %{x} mentions<extra></extra>"}],
  {...L5,showlegend:false,xaxis:{...L5.xaxis,title:"Mentions"},margin:{...L5.margin,l:110}});

// 6. companies
const co=F.top_companies;
const L6 = mkL();
Plotly.newPlot("ch_comp",[{y:co.map(c=>c.company).reverse(),x:co.map(c=>c.n).reverse(),type:"bar",
  orientation:"h",marker:{color:C[1]},hovertemplate:"%{y}: %{x} applications<extra></extra>"}],
  {...L6,showlegend:false,xaxis:{...L6.xaxis,title:"Applications"},margin:{...L6.margin,l:150}});

// 7. experience
const L7 = mkL();
Plotly.newPlot("ch_exp",[{x:F.experience.buckets,y:F.experience.counts,type:"bar",marker:{color:C[2]},
  hovertemplate:"%{x}: %{y} postings<extra></extra>"}],
  {...L7,showlegend:false,yaxis:{...L7.yaxis,title:"Postings"},xaxis:{...L7.xaxis,tickangle:-18}});

// 8. stream comparison
const sc=F.stream_compare;
const L8 = mkL();
Plotly.newPlot("ch_stream",[
  {x:["Analyst","Support"],y:[sc.analyst.median_salary,sc.support.median_salary],type:"bar",
   name:"Median ₹ LPA",marker:{color:C[3]},yaxis:"y",
   hovertemplate:"%{x}: ₹%{y} LPA (n="+sc.analyst.salary_n+"/"+sc.support.salary_n+")<extra></extra>"},
  {x:["Analyst","Support"],y:[sc.analyst.remote_pct,sc.support.remote_pct],type:"bar",
   name:"Remote %",marker:{color:C[0]},yaxis:"y2",
   hovertemplate:"%{x}: %{y}% remote<extra></extra>"}],
  {...L8,showlegend:true,legend:{orientation:"h",x:.5,y:1.12,xanchor:"center"},
   yaxis:{...L8.yaxis,title:"Median ₹ LPA",side:"left"},
   yaxis2:{title:"Remote %",overlaying:"y",side:"right",gridcolor:"#1c2436",ticksuffix:"%"},barmode:"group"});
</script>
</body>
</html>
"""

# ---- fill template ----
kpi_html = "\n".join(
    f'<div class="kpi" style="--ac:{c}"><div class="lbl">{lbl}</div>'
    f'<div class="num">{num}</div><div class="n">{n}</div></div>'
    for lbl, num, n, c in kpi_cards)

cov_rows = [
    ("company", 440, "85%", "—"),
    ("title", 442, "85%", "—"),
    ("city", 444, "85%", "incl. “Remote (unspecified)”"),
    ("work_mode", 284, "55%", "rest shown as unknown"),
    ("salary → LPA", f["salary_n"], "16%", "$/hr rates excluded"),
    ("experience", 235, "45%", "—"),
    ("date_applied", 374, "72%", "—"),
    ("skill keywords", f["skills_n"], "18%", "from ledger notes"),
]
cov_html = "\n".join(
    f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in cov_rows)

out = (HTML
       .replace("__PLOTLY__", PLOTLY_JS)
       .replace("__FINDINGS__", json.dumps(f))
       .replace("__KPIS__", kpi_html)
       .replace("__COV_ROWS__", cov_html)
       .replace("__TREND_N__", str(f["trend"]["n"]))
       .replace("__REMOTE_PCT__", str(f["work_mode_known_pct_remote"]))
       .replace("__MODE_N__", str(f["work_mode_n_known"]))
       .replace("__SAL_N__", str(f["salary_n"]))
       .replace("__SAL_MED__", str(f["salary_median"]))
       .replace("__SAL_P25__", str(f["salary_p25"]))
       .replace("__SAL_P75__", str(f["salary_p75"]))
       .replace("__A_MED__", str(sc["analyst"]["median_salary"]))
       .replace("__S_MED__", str(sc["support"]["median_salary"]))
       .replace("__SK_N__", str(f["skills_n"]))
       .replace("__EXP_N__", str(f["experience"]["n"]))
       .replace("__CREWLIA_N__", str(next(c["n"] for c in topc if c["company"].lower() == "crewlia"))))

(ROOT / "dashboard.html").write_text(out, encoding="utf-8")
print(f"dashboard.html written: {len(out)/1e6:.1f} MB")

"""
02_eda.py — exploratory analysis of the cleaned postings dataset.

Reads ../data/postings_clean.csv, prints key findings, exports preview PNGs
(dark theme) to ../assets/, and writes ../analysis/findings.json with every
aggregated series the dashboard needs. Every number traces back to the CSV.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data" / "postings_clean.csv"
ASSETS = HERE.parent / "assets"
ASSETS.mkdir(exist_ok=True)

# palette (shared with dashboard.html)
CYAN, VIOLET, AMBER, EMERALD, ROSE, BLUE = (
    "#22d3ee", "#a78bfa", "#fbbf24", "#34d399", "#fb7185", "#60a5fa")
MUTED = "#9ca3af"

plt.rcParams.update({
    "figure.facecolor": "#0f1420", "axes.facecolor": "#0f1420",
    "text.color": "#e5e7eb", "axes.labelcolor": "#e5e7eb",
    "xtick.color": "#9ca3af", "ytick.color": "#9ca3af",
    "axes.edgecolor": "#374151", "grid.color": "#1f2937",
    "font.family": "DejaVu Sans",
})

df = pd.read_csv(DATA)
df["salary_mid"] = (df["salary_min_lpa"] + df["salary_max_lpa"]) / 2
findings = {"n_total": int(len(df))}

# ---------- 1. applications over time ----------
d = df[df["date_applied"].notna()].copy()
d["date_applied"] = pd.to_datetime(d["date_applied"])
trend = d.groupby([d["date_applied"].dt.date, "stream"]).size().unstack(fill_value=0)
dates = [str(x) for x in trend.index]
findings["trend"] = {
    "dates": dates,
    "analyst": [int(v) for v in trend.get("analyst", pd.Series(0, index=trend.index))],
    "support": [int(v) for v in trend.get("support", pd.Series(0, index=trend.index))],
    "n": int(len(d)),
}
peak_day = trend.sum(axis=1).idxmax()
findings["trend"]["peak_day"] = str(peak_day)
findings["trend"]["peak_count"] = int(trend.sum(axis=1).max())

fig, ax = plt.subplots(figsize=(10, 4.2))
x = np.arange(len(dates))
ax.bar(x, findings["trend"]["analyst"], label="Analyst stream", color=CYAN, alpha=.9)
ax.bar(x, findings["trend"]["support"], bottom=findings["trend"]["analyst"],
       label="Support stream", color=VIOLET, alpha=.9)
ax.set_xticks(x); ax.set_xticklabels([dt[5:] for dt in dates], rotation=30, ha="right", fontsize=8)
ax.set_ylabel("Applications"); ax.set_title("Applications per day  •  n=" + str(len(d)), pad=12)
ax.legend(frameon=False, fontsize=9); ax.grid(axis="y", alpha=.4)
fig.tight_layout(); fig.savefig(ASSETS / "chart_trend.png", dpi=150); plt.close(fig)

# ---------- 2. work-mode split ----------
wm = df["work_mode"].value_counts()
findings["work_mode"] = {k: int(v) for k, v in wm.items()}
known = df[df["work_mode"] != "unknown"]
findings["work_mode_known_pct_remote"] = round(
    (known["work_mode"] == "remote").mean() * 100, 1)
findings["work_mode_n_known"] = int(len(known))

# ---------- 3. salary analysis ----------
sal = df[df["salary_mid"].notna()].copy()
findings["salary_n"] = int(len(sal))
findings["salary_median"] = round(float(sal["salary_mid"].median()), 2)
findings["salary_p25"] = round(float(sal["salary_mid"].quantile(.25)), 2)
findings["salary_p75"] = round(float(sal["salary_mid"].quantile(.75)), 2)
by_mode = sal.groupby("work_mode")["salary_mid"].agg(["median", "count"]).round(2)
findings["salary_by_mode"] = {
    k: {"median": float(v["median"]), "n": int(v["count"])} for k, v in by_mode.iterrows()}
if "remote" in by_mode.index and "on-site" in by_mode.index:
    findings["remote_premium_pct"] = round(
        (by_mode.loc["remote", "median"] / by_mode.loc["on-site", "median"] - 1) * 100, 1)
city_sal = sal[sal["city"] != "Remote (unspecified)"].groupby("city")["salary_mid"] \
    .agg(["median", "count"]).round(2)
city_sal = city_sal[city_sal["count"] >= 4].sort_values("median", ascending=False)
findings["salary_by_city"] = {
    k: {"median": float(v["median"]), "n": int(v["count"])} for k, v in city_sal.iterrows()}
findings["salary_values_by_mode"] = {
    m: [round(float(x), 2) for x in sal[sal["work_mode"] == m]["salary_mid"].tolist()]
    for m in sorted(sal["work_mode"].unique())
}

fig, ax = plt.subplots(figsize=(9, 4.6))
modes = [m for m in ["remote", "hybrid", "on-site"] if m in sal["work_mode"].unique()]
data = [sal[sal["work_mode"] == m]["salary_mid"].values for m in modes]
bp = ax.boxplot(data, labels=[f"{m}\n(n={len(v)})" for m, v in zip(modes, data)],
                patch_artist=True, medianprops={"color": "#fff"})
for patch, c in zip(bp["boxes"], [CYAN, VIOLET, AMBER]):
    patch.set_facecolor(c); patch.set_alpha(.55)
ax.set_ylabel("Salary midpoint (₹ LPA)")
ax.set_title("Disclosed salary bands by work mode  •  n=" + str(len(sal)), pad=12)
ax.grid(axis="y", alpha=.4)
fig.tight_layout(); fig.savefig(ASSETS / "chart_salary_by_mode.png", dpi=150); plt.close(fig)

# ---------- 4. skill demand ----------
sk = df[df["skills"].notna() & (df["skills"] != "")]
skill_counts = sk["skills"].str.split(";").explode().value_counts()
findings["skills"] = {k: int(v) for k, v in skill_counts.items()}
findings["skills_n"] = int(len(sk))
top_sk = skill_counts.head(10)
findings["top_skill"] = {"name": top_sk.index[0], "count": int(top_sk.iloc[0])}

fig, ax = plt.subplots(figsize=(8, 4.6))
ax.barh(top_sk.index[::-1], top_sk.values[::-1], color=CYAN, alpha=.85)
ax.set_xlabel("Mentions in ledger notes")
ax.set_title(f"Most-mentioned skills  •  n={len(sk)} postings with skill notes", pad=12)
for i, v in enumerate(top_sk.values[::-1]):
    ax.text(v + 0.3, i, str(v), va="center", fontsize=9, color=MUTED)
ax.grid(axis="x", alpha=.4)
fig.tight_layout(); fig.savefig(ASSETS / "chart_skills.png", dpi=150); plt.close(fig)

# ---------- 5. top companies ----------
comp = df[df["company"].fillna("") != ""].copy()
# drop obvious non-companies
comp = comp[~comp["company"].str.contains(r"sweep|applied", case=False, na=False)]
top_comp = comp["company"].value_counts().head(12)
findings["top_companies"] = [{"company": k, "n": int(v)} for k, v in top_comp.items()]

# ---------- 6. experience bands ----------
exp = df[df["exp_min"].notna()].copy()
def bucket(x):
    x = float(x)
    if x <= 0: return "Fresher (0)"
    if x < 1: return "Fresher (0)"
    if x < 2: return "1 yr"
    if x < 3: return "2 yrs"
    if x < 4: return "3 yrs"
    if x < 6: return "4–5 yrs"
    return "6+ yrs"
exp["exp_bucket"] = exp["exp_min"].apply(bucket)
order = ["Fresher (0)", "1 yr", "2 yrs", "3 yrs", "4–5 yrs", "6+ yrs"]
exp_counts = exp["exp_bucket"].value_counts()
findings["experience"] = {
    "buckets": order,
    "counts": [int(exp_counts.get(b, 0)) for b in order],
    "n": int(len(exp)),
}

# ---------- 7. stream comparison ----------
cmp_ = {}
for stream in ["analyst", "support"]:
    s = df[df["stream"] == stream]
    ssal = s[s["salary_mid"].notna()]["salary_mid"]
    skn = s[s["work_mode"] != "unknown"]
    cmp_[stream] = {
        "n": int(len(s)),
        "median_salary": round(float(ssal.median()), 2) if len(ssal) else None,
        "salary_n": int(len(ssal)),
        "remote_pct": round(float((skn["work_mode"] == "remote").mean() * 100), 1) if len(skn) else None,
        "work_mode_n": int(len(skn)),
    }
findings["stream_compare"] = cmp_

# ---------- 8. top titles ----------
titles = df[df["title"].fillna("") != ""]["title"].str.lower().str.strip()
top_titles = titles.value_counts().head(10)
findings["top_titles"] = [{"title": k, "n": int(v)} for k, v in top_titles.items()]

# ---------- 9. portal mix ----------
findings["portal_mix"] = {k: int(v) for k, v in df["portal"].value_counts().items()}

with open(HERE / "findings.json", "w") as f:
    json.dump(findings, f, indent=2)

print("=" * 60)
print("KEY FINDINGS (all trace to data/postings_clean.csv)")
print("=" * 60)
print(f"1. {findings['n_total']} applications logged 6–15 Oct 2026 "
      f"({cmp_['analyst']['n']} analyst, {cmp_['support']['n']} support). "
      f"Busiest day: {findings['trend']['peak_day']} ({findings['trend']['peak_count']} applies).")
print(f"2. Work mode (n={findings['work_mode_n_known']} known): "
      f"{findings['work_mode_known_pct_remote']}% remote.")
print(f"3. Disclosed salaries (n={findings['salary_n']}): median "
      f"₹{findings['salary_median']} LPA (IQR ₹{findings['salary_p25']}–₹{findings['salary_p75']}).")
for m, v in findings["salary_by_mode"].items():
    print(f"   - {m}: median ₹{v['median']} LPA (n={v['n']})")
if "remote_premium_pct" in findings:
    print(f"   Remote premium over on-site medians: {findings['remote_premium_pct']:+.1f}%")
print(f"4. Top skill mentions (n={findings['skills_n']} notes): " +
      ", ".join(f"{k} ({v})" for k, v in list(findings['skills'].items())[:6]))
print(f"5. Top hiring companies: " +
      ", ".join(f"{c['company']} ({c['n']})" for c in findings["top_companies"][:6]))
print(f"6. Experience bands (n={findings['experience']['n']}): " +
      ", ".join(f"{b} {c}" for b, c in zip(findings["experience"]["buckets"], findings["experience"]["counts"])))
print(f"7. Stream contrast — analyst median ₹{cmp_['analyst']['median_salary']} LPA "
      f"(n={cmp_['analyst']['salary_n']}) vs support median ₹{cmp_['support']['median_salary']} LPA "
      f"(n={cmp_['support']['salary_n']}); remote share "
      f"{cmp_['analyst']['remote_pct']}% vs {cmp_['support']['remote_pct']}%.")
print("findings.json + 3 PNGs written.")

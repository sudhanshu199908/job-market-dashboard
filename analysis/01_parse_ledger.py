"""
01_parse_ledger.py — raw ledger -> structured dataset.

Reads ~/workspace/job_hunt/applied.json (Sudhanshu's verified application ledger,
Oct 2026) and extracts structured fields from each free-text entry with
regex/heuristics. Never invents values: unparseable fields are left empty
(unknown) and excluded from the relevant charts, with coverage reported.

Output: ../data/postings_clean.csv
"""

import csv
import json
import os
import re
from pathlib import Path

LEDGER = Path(os.path.expanduser("~/workspace/job_hunt/applied.json"))
OUT = Path(__file__).resolve().parent.parent / "data" / "postings_clean.csv"

APPLIED_LISTS = [
    ("linkedin", "linkedin_applied", "analyst"),
    ("naukri", "naukri_applied", "analyst"),
    ("instahyre", "instahyre_applied", "analyst"),
    ("shine", "shine_applied", "analyst"),
    ("email", "email_applied", "analyst"),
    ("foundit", "foundit_applied", "analyst"),
    ("rohtak", "rohtak_applied", "analyst"),
    ("internshala", "internshala_applied", "analyst"),
    ("direct", "direct_applied", "analyst"),
    ("support", "support_applied", "support"),
]

CITY_MAP = [
    (r"greater\s*noida", "Noida"),
    (r"\bnoida\b", "Noida"),
    (r"gurugram|gurgaon", "Gurugram"),
    (r"new\s*delhi|\bdelhi\b", "Delhi"),
    (r"bengaluru|bangalore", "Bengaluru"),
    (r"navi\s*mumbai|\bmumbai\b", "Mumbai"),
    (r"\bhyderabad\b", "Hyderabad"),
    (r"\bpune\b", "Pune"),
    (r"\bchennai\b", "Chennai"),
    (r"\bkolkata\b", "Kolkata"),
    (r"\bahmedabad\b", "Ahmedabad"),
    (r"\bjaipur\b", "Jaipur"),
    (r"\bmohali\b", "Mohali"),
    (r"\bfaridabad\b", "Faridabad"),
    (r"\bindore\b", "Indore"),
    (r"\blacknow\b", "Lucknow"),
    (r"\bnagpur\b", "Nagpur"),
    (r"\bkochi\b|\bcochin\b", "Kochi"),
]

SKILLS = [
    ("sql", r"\bsql\b"),
    ("python", r"\bpython\b"),
    ("power bi", r"\bpower\s?bi\b"),
    ("excel", r"\bexcel\b"),
    ("tableau", r"\btableau\b"),
    ("dax", r"\bdax\b"),
    ("mysql", r"\bmysql\b"),
    ("pandas", r"\bpandas\b"),
    ("numpy", r"\bnumpy\b"),
    ("mis", r"\bmis\b"),
    ("etl", r"\betl\b"),
    ("statistics", r"\bstatistic\w*\b"),
    ("machine learning", r"\bmachine learning\b"),
    ("azure", r"\bazure\b"),
    ("aws", r"\baws\b"),
    ("snowflake", r"\bsnowflake\b"),
    ("looker", r"\blooker\b"),
]

ROLE_WORDS = {
    "data", "analyst", "analytics", "business", "mis", "reporting", "bi",
    "power", "developer", "executive", "specialist", "associate", "assistant",
    "coordinator", "consultant", "engineer", "manager", "operator", "representative",
    "researcher", "research", "writer", "content", "copywriter", "success",
    "intelligence", "science", "scientist", "sr", "senior", "jr", "junior",
    "lead", "trainee",
}

URL_RE = re.compile(r"https?://\S+")
LI_ID_RE = re.compile(r"linkedin\.com/jobs/view/(\d+)")
NK_ID_RE = re.compile(r"job-listings-.*?(\d{9,})\b")
NK_SLUG_RE = re.compile(r"job-listings-(.+?)(?:-(\d{9,}))?(?:[/?#]|$)")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
ANSWERS_PAREN_RE = re.compile(r"\([^)]*\banswers?\b[^)]*\)", re.I)

USD_INR = 83.0


def clean_text(entry: str) -> str:
    """Remove the candidate's own screening-answer blocks (his answers, not the job's specs)."""
    t = ANSWERS_PAREN_RE.sub(" ", entry)
    return t


def parse_salary(text: str):
    """Return (min_lpa, max_lpa, raw, note). None if not found / excluded."""
    # hourly rates -> exclude from LPA distribution (would distort)
    m = re.search(r"\$\s*[\d,]+(?:\s*[-–—]\s*\$?\s*[\d,]+)?\s*(?:/hr|per hour)", text, re.I)
    if m:
        return None, None, m.group(0).strip(), "hourly-rate-excluded"
    m = re.search(r"\$\s*([\d,]+)\s*/\s*task", text, re.I)
    if m:
        return None, None, m.group(0).strip(), "per-task-rate-excluded"

    def clean_num(s):
        return float(s.replace(",", ""))

    # USD annual range -> LPA
    m = re.search(r"\$\s*([\d,]+)\s*[-–—]\s*\$?\s*([\d,]+)", text)
    if m:
        lo, hi = clean_num(m.group(1)), clean_num(m.group(2))
        if lo > 1000:  # annual USD
            return round(lo * USD_INR / 1e5, 2), round(hi * USD_INR / 1e5, 2), m.group(0).strip(), "usd-annual-converted"
    # LPA range: "3-5 LPA", "₹10.7–15 LPA", "2.25-4.5 Lacs PA"
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)\s*(?:lpa|lac?s?|lakh?s?)\b", text, re.I):
        ctx = text[max(0, m.start() - 20): m.end() + 20]
        if re.search(r"current|expected|drawn|take[\s-]?home", ctx, re.I):
            continue  # his own CTC answers, not the job's band
        return float(m.group(1)), float(m.group(2)), m.group(0).strip(), ""
    # single LPA: "3 LPA"
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:lpa|lac?s?|lakh?s?)\b", text, re.I):
        ctx = text[max(0, m.start() - 20): m.end() + 20]
        if re.search(r"current|expected|drawn|take[\s-]?home", ctx, re.I):
            continue
        v = float(m.group(1))
        return v, v, m.group(0).strip(), ""
    # monthly INR: "Rs. 25000/- per month", "50-60k/month"
    m = re.search(r"(\d+)\s*[-–—]\s*(\d+)\s*k\s*/\s*month", text, re.I)
    if m:
        lo, hi = int(m.group(1)) * 1000, int(m.group(2)) * 1000
        return round(lo * 12 / 1e5, 2), round(hi * 12 / 1e5, 2), m.group(0).strip(), "monthly-converted"
    m = re.search(r"(?:rs\.?|₹|inr)\s*([\d,]+)\s*(?:/-)?\s*(?:per month|/month|\bp\.?m\.?\b)", text, re.I)
    if m:
        mo = clean_num(m.group(1))
        v = round(mo * 12 / 1e5, 2)
        return v, v, m.group(0).strip(), "monthly-converted"
    return None, None, "", ""


def parse_experience(text: str):
    # strip skill=years answers like "SQL=1yr", "ETL=0yrs" (his answers, not requirements)
    t = re.sub(r"[A-Za-z][A-Za-z\s]*=\s*\d+\s*(?:yrs?|years)?", " ", text)
    m = re.search(r"(\d+)\s*(?:-|–|—|to)\s*(\d+)\s*(?:yrs?|years)\b", t, re.I)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+)\s*(?:yrs?|years)\b", t, re.I)
    if m:
        v = int(m.group(1))
        return v, v
    return None, None


def parse_work_mode(text: str) -> str:
    if re.search(r"hybrid", text, re.I):
        return "hybrid"
    if re.search(r"remote|\bwfh\b|work from home|work-from-home", text, re.I):
        return "remote"
    if re.search(r"on-site|onsite", text, re.I):
        return "on-site"
    return "unknown"


def parse_city(text: str, work_mode: str) -> str:
    for pat, canon in CITY_MAP:
        if re.search(pat, text, re.I):
            return canon
    if work_mode == "remote":
        return "Remote (unspecified)"
    return "unknown"


TITLE_RE = re.compile(
    r"\b(analyst|analytics|developer|executive|specialist|writer|assistant|"
    r"coordinator|associate|consultant|engineer|operator|representative|"
    r"researcher|manager|accountant|typist|clerk|scientist)\b", re.I)
JUNK_PART_RE = re.compile(
    r"\b(work from home|wfh|full time|permanent|freshers? welcome|fresher|"
    r"hiring office|^hiring$|staffing)\b", re.I)
META_SEG_RE = re.compile(r"\b(sweep|applied|20\d\d)\b|\bremote(\s*india)?$", re.I)


def pick_from_pipes(seg: str):
    """Split a segment on '|' and pick (company, title) by role-word classification."""
    company, title = "", ""
    for p in re.split(r"\s*\|\s*", seg):
        pc = re.sub(r"\s*\(.*$", "", p).strip()
        pc = re.sub(r"^\s*hiring:\s*", "", pc, flags=re.I).strip()
        pc = re.sub(r"\s*\[.*$", "", pc).strip()
        if not pc or len(pc) > 70:
            continue
        if TITLE_RE.search(pc):
            if not title:
                title = pc
        elif not JUNK_PART_RE.search(pc) and not META_SEG_RE.search(pc):
            if not company:
                company = pc
    return company, title


def clean_seg(s: str) -> str:
    s = re.split(r"\s*\|\s*", s)[0]
    s = s.split(",")[0]
    s = re.sub(r"\s*\(.*$", "", s).strip()
    s = re.sub(r"^\s*hiring:\s*", "", s, flags=re.I).strip()
    s = re.sub(r"\s*\[.*$", "", s).strip()
    return s


def looks_like_location(s: str) -> bool:
    if META_SEG_RE.search(s or ""):
        return True
    for pat, _ in CITY_MAP:
        if re.search(pat, s or "", re.I):
            return True
    return False


COMPANY_END_RE = re.compile(
    r"(analytics|hub|labs|solutions?|technologies|services?|group|systems?|"
    r"search|partners|diary|collective|studio|agency|works|inc|llp|ltd|"
    r"limited|consulting|hospitals?|institute|college|university|infotech)$", re.I)


def looks_like_company_name(s: str) -> bool:
    s = (s or "").strip()
    if not s:
        return False
    if s.isupper() and len(s.split()) <= 4:
        return True  # "RECRUIT DIARY"
    return bool(COMPANY_END_RE.search(s))


def parse_dict_entry(entry: str):
    """Entries stored as Python dicts carry explicit fields — use them directly."""
    import ast
    try:
        obj = ast.literal_eval(entry.strip())
    except Exception:
        return None
    if not isinstance(obj, dict) or "company" not in obj:
        return None
    return obj


def parse_company_title(entry: str):
    """Return (company, title) best-effort.

    Ledger convention is 'Company — Title — ...', with variants:
    '# note' or '| Company' embedded in a leading URL segment,
    'Title @ Company', 'FLAG:' prefixes, and 'early-access: Title' sweep notes.
    Never invents: returns '' when nothing reliable is found.
    """
    if "—" in entry:
        segs = [s.strip() for s in entry.split("—") if s.strip()]
    else:
        segs = [s.strip() for s in re.split(r"\s+-\s+", entry) if s.strip()]
    hash_title, hash_company = "", ""
    if segs and (URL_RE.match(segs[0]) or re.fullmatch(r"\d{6,}", segs[0])):
        # salvage '# note' or '| Company' embedded in the URL segment
        rest = URL_RE.sub("", segs[0]) if URL_RE.match(segs[0]) else ""
        rest = re.sub(r"^#\s*", "", rest.strip())
        if rest and not re.fullmatch(r"\d{6,}", rest) and len(rest) <= 70:
            if "|" in rest:
                rc, rt = pick_from_pipes(rest)
                hash_company, hash_title = rc, rt
            elif TITLE_RE.search(rest):
                hash_title = rest
            elif not META_SEG_RE.search(rest):
                hash_company = rest
        segs = segs[1:]
    if not segs:
        return "", ""
    segs[0] = re.sub(r"^FLAG:\s*", "", segs[0], flags=re.I)
    m = re.search(r"early-access:\s*([^—]+?)\s*$", segs[0], re.I)
    if m:
        return "", m.group(1).strip()
    if "@" in segs[0] and not segs[0].startswith("@"):
        t, c = segs[0].split("@", 1)
        return re.sub(r"\s*\(.*$", "", c).strip(), re.sub(r"\s*\(.*$", "", t).strip()

    company, title = "", ""
    if "|" in segs[0]:
        # e.g. "Back Office Operations Executive | WFH | ... | Gens Hiree (staffing)"
        company, title = pick_from_pipes(segs[0])
    elif TITLE_RE.search(segs[0]) and not looks_like_company_name(clean_seg(segs[0])):
        # title-first segment: "Sales Data Analyst — Ozone Corp Private Limited"
        title = clean_seg(segs[0])
        if len(segs) > 1:
            c2 = clean_seg(segs[1])
            if c2 and TITLE_RE.search(c2) and len(c2) <= 25:
                company, title = title, c2   # "X Analyst — Analyst"
            elif c2 and not TITLE_RE.search(c2) and not META_SEG_RE.search(c2) \
                    and not looks_like_location(c2) and len(c2) <= 60:
                company = c2
    else:
        company = clean_seg(segs[0])
        if len(segs) > 1:
            t2 = clean_seg(segs[1])
            if t2 and TITLE_RE.search(t2) and len(t2) < 70:
                title = t2
    if hash_title:
        title = hash_title  # explicit '# note' from the ledger author is authoritative
    if hash_company and not company:
        company = hash_company
    # salvage or reject junk company segments ("... sweep ...: Porch")
    if company and (len(company) > 70 or URL_RE.match(company)
                    or re.search(r"\b(sweep|applied)\b", company, re.I)):
        m2 = re.search(r":\s*([^:()]+?)\s*$", company)
        company = m2.group(1).strip() if m2 else ""
        if len(company) > 60:
            company = ""
    return company, title


def parse_naukri_slug(url: str):
    """Extract location + experience (+ rough title) from a Naukri job-listings URL slug."""
    m = NK_SLUG_RE.search(url)
    if not m:
        return {}
    slug = m.group(1)
    out = {}
    exp = re.search(r"(\d+)-to-(\d+)-years$", slug)
    if exp:
        out["exp_min"], out["exp_max"] = int(exp.group(1)), int(exp.group(2))
        slug = slug[: exp.start()].rstrip("-")
    loc_tokens = ("bengaluru", "gurugram", "gurgaon", "noida", "delhi", "mumbai",
                  "hyderabad", "pune", "chennai", "kolkata", "ahmedabad", "jaipur",
                  "remote", "india", "mohali", "faridabad", "indore", "lucknow",
                  "nagpur", "kochi", "greater-noida", "ghaziabad")
    for lt in loc_tokens:
        if slug.endswith("-" + lt):
            out["city"] = {"gurgaon": "Gurugram"}.get(lt, lt.title().replace("-", " "))
            slug = slug[: -len(lt) - 1]
            break
    # leading role words -> rough title
    toks = slug.split("-")
    title_toks = []
    for tok in toks:
        if tok in ROLE_WORDS:
            title_toks.append(tok)
        else:
            break
    if title_toks:
        out["title"] = " ".join(title_toks).title()
    return out


def parse_entry(entry: str, portal: str, stream: str, idx: int) -> dict:
    text = clean_text(entry)
    rec = {
        "entry_id": f"{portal}_{idx}",
        "portal": portal,
        "stream": stream,
        "company": "",
        "title": "",
        "city": "unknown",
        "work_mode": "unknown",
        "salary_min_lpa": "",
        "salary_max_lpa": "",
        "salary_raw": "",
        "salary_note": "",
        "exp_min": "",
        "exp_max": "",
        "date_applied": "",
        "job_id": "",
        "url": "",
        "skills": "",
        "raw": entry,
    }
    um = URL_RE.search(entry)
    if um:
        rec["url"] = um.group(0).rstrip(".,)")
    li = LI_ID_RE.search(entry)
    nk = NK_ID_RE.search(entry)
    if li:
        rec["job_id"] = "li_" + li.group(1)
    elif nk:
        rec["job_id"] = "nk_" + nk.group(1)

    if portal == "support":
        # portal_detail: which site the support application went through
        if "linkedin" in entry.lower():
            rec["portal"] = "support_linkedin"
        elif "naukri" in entry.lower():
            rec["portal"] = "support_naukri"
        else:
            rec["portal"] = "support_other"

    bare_url = bool(re.fullmatch(r"\s*https?://\S+\s*", entry))
    if entry.strip().startswith("{"):
        dobj = parse_dict_entry(entry)
    else:
        dobj = None
    if dobj:
        # explicit structured fields — highest fidelity
        rec["company"] = str(dobj.get("company", "")).strip()
        rec["title"] = str(dobj.get("role", "")).strip()
        rec["job_id"] = "nk_" + str(dobj.get("job_id", "")).strip()
        loc = str(dobj.get("location", ""))
        rec["work_mode"] = parse_work_mode(loc)
        rec["city"] = parse_city(loc, rec["work_mode"])
        smin, smax, sraw, snote = parse_salary(str(dobj.get("salary", "")))
        if sraw:
            rec["salary_raw"] = sraw
            rec["salary_note"] = snote
            if smin is not None:
                rec["salary_min_lpa"], rec["salary_max_lpa"] = smin, smax
        emin, emax = parse_experience(str(dobj.get("exp", "")))
        if emin is not None:
            rec["exp_min"], rec["exp_max"] = emin, emax
    elif bare_url and "naukri.com" in entry:
        slug_info = parse_naukri_slug(entry)
        rec["title"] = slug_info.get("title", "")
        rec["city"] = slug_info.get("city", "unknown")
        if "exp_min" in slug_info:
            rec["exp_min"], rec["exp_max"] = slug_info["exp_min"], slug_info["exp_max"]
        rec["work_mode"] = parse_work_mode(entry)
        if rec["city"] == "unknown" and rec["work_mode"] == "remote":
            rec["city"] = "Remote (unspecified)"
    elif bare_url:
        # bare LinkedIn URL: nothing else parseable
        pass
    else:
        company, title = parse_company_title(entry)
        rec["company"], rec["title"] = company, title
        rec["work_mode"] = parse_work_mode(text)
        rec["city"] = parse_city(text, rec["work_mode"])
        smin, smax, sraw, snote = parse_salary(text)
        if sraw:
            rec["salary_raw"] = sraw
            rec["salary_note"] = snote
            if smin is not None:
                rec["salary_min_lpa"], rec["salary_max_lpa"] = smin, smax
        emin, emax = parse_experience(text)
        if emin is not None:
            rec["exp_min"], rec["exp_max"] = emin, emax

    dm = DATE_RE.search(entry)
    if dm:
        rec["date_applied"] = dm.group(1)

    skill_hits = [name for name, pat in SKILLS if re.search(pat, text, re.I)]
    rec["skills"] = ";".join(skill_hits)
    return rec


def main():
    with open(LEDGER) as f:
        ledger = json.load(f)
    rows = []
    for portal, list_key, stream in APPLIED_LISTS:
        for i, entry in enumerate(ledger.get(list_key, [])):
            rows.append(parse_entry(str(entry), portal, stream, i))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    cols = ["entry_id", "portal", "stream", "company", "title", "city", "work_mode",
            "salary_min_lpa", "salary_max_lpa", "salary_raw", "salary_note",
            "exp_min", "exp_max", "date_applied", "job_id", "url", "skills", "raw"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    # coverage report
    n = len(rows)
    def cov(fn):
        return sum(1 for r in rows if fn(r))
    print(f"total entries parsed: {n}")
    print(f"company:      {cov(lambda r: r['company'])} ({cov(lambda r: r['company'])/n:.0%})")
    print(f"title:        {cov(lambda r: r['title'])} ({cov(lambda r: r['title'])/n:.0%})")
    print(f"city known:   {cov(lambda r: r['city'] not in ('unknown',))} ({cov(lambda r: r['city'] not in ('unknown',))/n:.0%})")
    print(f"work_mode:    {cov(lambda r: r['work_mode'] != 'unknown')} ({cov(lambda r: r['work_mode'] != 'unknown')/n:.0%})")
    print(f"salary (lpa): {cov(lambda r: r['salary_min_lpa'] != '')} ({cov(lambda r: r['salary_min_lpa'] != '')/n:.0%})")
    print(f"  hourly-excluded: {cov(lambda r: r['salary_note'] == 'hourly-rate-excluded')}")
    print(f"experience:   {cov(lambda r: r['exp_min'] != '')} ({cov(lambda r: r['exp_min'] != '')/n:.0%})")
    print(f"date_applied: {cov(lambda r: r['date_applied'])} ({cov(lambda r: r['date_applied'])/n:.0%})")
    print(f"skills>=1:    {cov(lambda r: r['skills'])} ({cov(lambda r: r['skills'])/n:.0%})")
    print(f"job_id:       {cov(lambda r: r['job_id'])}")


if __name__ == "__main__":
    main()

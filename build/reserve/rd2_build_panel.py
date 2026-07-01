#!/usr/bin/env python3
"""RD2 Part 1 — build the gold TONNAGE panel from the WGC Central Banks Dashboard API.

Primary DV source: World Gold Council 'Central Banks Dashboard' quarterly time series
(fsapi.gold.org/api/cbd/v11/charts/getPage), which republishes IMF IFS official gold
holdings in tonnes. Fetched ungated JSON retained under rd2_evidence/.

Treated/control assigned MECHANICALLY from the UN GA ES-11/1 roll-call (RD0 grounded):
  TREATED = No or Abstain ; CONTROL = Yes ; Turkey (voted Yes) = CONTROL.
Non-voting / non-UN holders (e.g. Taiwan, Hong Kong) are labelled NA_vote and excluded
from the headline treated/control split (kept in the panel).

Gold price: World Bank Pink Sheet monthly gold (USD/troy oz), independently fetched
(HTTP 200), mapped to quarter-end month; WGC-implied price (value/tonnes) kept as a
corroborant. No tonnage value is asserted from memory.
"""
import json, re, datetime
import pandas as pd

EVID = "/home/user/dollar-breaking-point/build/reserve/rd2_evidence"
OUT  = "/home/user/dollar-breaking-point/build/reserve/RD2_gold_panel.parquet"
VOTE_FILE = "/home/user/dollar-breaking-point/build/reserve/rd0_evidence/un_digitallibrary_es11_1_votelines.txt"
OZT_PER_TONNE = 32150.746  # fine troy ounces per metric tonne (standard conversion)

# ---- 1. parse ES-11/1 roll-call (name -> vote letter) ----------------------------
raw = open(VOTE_FILE, encoding="utf-8", errors="replace").read()
m = re.search(r"Y AFGHANISTAN.*?ZIMBABWE", raw, re.S)
block = m.group(0)
votes = {}
for tok in block.split("<br />"):
    tok = tok.strip()
    if not tok:
        continue
    parts = tok.split(None, 1)
    if len(parts) == 2 and parts[0] in ("Y", "N", "A"):
        votes[parts[1].strip().upper()] = parts[0]
    else:
        votes.setdefault(tok.upper(), "NV")  # non-voting (blank vote prefix)

# ---- 2. ISO3 -> UN roll-call name -------------------------------------------------
ISO2NAME = {
 "ABW":None,"AFG":"AFGHANISTAN","ALB":"ALBANIA","ARE":"UNITED ARAB EMIRATES","ARG":"ARGENTINA",
 "ARM":"ARMENIA","AUS":"AUSTRALIA","AUT":"AUSTRIA","AZE":"AZERBAIJAN","BDI":"BURUNDI",
 "BEL":"BELGIUM","BGD":"BANGLADESH","BGR":"BULGARIA","BHR":"BAHRAIN","BIH":"BOSNIA AND HERZEGOVINA",
 "BLR":"BELARUS","BOL":"BOLIVIA (PLURINATIONAL STATE OF)","BRA":"BRAZIL","CAN":"CANADA",
 "CHE":"SWITZERLAND","CHL":"CHILE","CHN":"CHINA","CMR":"CAMEROON","COG":"CONGO","COL":"COLOMBIA",
 "COM":"COMOROS","CRI":"COSTA RICA","CYP":"CYPRUS","CZE":"CZECHIA","DEU":"GERMANY","DNK":"DENMARK",
 "DOM":"DOMINICAN REPUBLIC","DZA":"ALGERIA","ECU":"ECUADOR","EGY":"EGYPT","ERI":"ERITREA",
 "ESP":"SPAIN","EST":"ESTONIA","FIN":"FINLAND","FJI":"FIJI","FRA":"FRANCE","GAB":"GABON",
 "GBR":"UNITED KINGDOM","GHA":"GHANA","GRC":"GREECE","GTM":"GUATEMALA","HKG":None,"HND":"HONDURAS",
 "HRV":"CROATIA","HTI":"HAITI","HUN":"HUNGARY","IDN":"INDONESIA","IND":"INDIA","IRL":"IRELAND",
 "IRQ":"IRAQ","ISL":"ICELAND","ITA":"ITALY","JOR":"JORDAN","JPN":"JAPAN","KAZ":"KAZAKHSTAN",
 "KEN":"KENYA","KGZ":"KYRGYZSTAN","KHM":"CAMBODIA","KOR":"REPUBLIC OF KOREA","KWT":"KUWAIT",
 "LAO":"LAO PEOPLE'S DEMOCRATIC REPUBLIC","LBN":"LEBANON","LBY":"LIBYA","LKA":"SRI LANKA",
 "LTU":"LITHUANIA","LUX":"LUXEMBOURG","LVA":"LATVIA","MAR":"MOROCCO","MEX":"MEXICO",
 "MKD":"NORTH MACEDONIA","MLT":"MALTA","MMR":"MYANMAR","MNG":"MONGOLIA","MOZ":"MOZAMBIQUE",
 "MRT":"MAURITANIA","MUS":"MAURITIUS","MWI":"MALAWI","MYS":"MALAYSIA","NGA":"NIGERIA",
 "NIC":"NICARAGUA","NLD":"NETHERLANDS","NOR":"NORWAY","NPL":"NEPAL","OMN":"OMAN","PAK":"PAKISTAN",
 "PER":"PERU","PHL":"PHILIPPINES","PNG":"PAPUA NEW GUINEA","POL":"POLAND","PRT":"PORTUGAL",
 "PRY":"PARAGUAY","QAT":"QATAR","ROU":"ROMANIA","RUS":"RUSSIAN FEDERATION","SAU":"SAUDI ARABIA",
 "SGP":"SINGAPORE","SLV":"EL SALVADOR","SRB":"SERBIA","SUR":"SURINAME","SVK":"SLOVAKIA",
 "SVN":"SLOVENIA","SWE":"SWEDEN","SYR":"SYRIAN ARAB REPUBLIC","TCD":"CHAD","THA":"THAILAND",
 "TJK":"TAJIKISTAN","TKM":"TURKMENISTAN","TTO":"TRINIDAD AND TOBAGO","TUN":"TUNISIA","TUR":"TURKEY",
 "TWN":None,"UKR":"UKRAINE","URY":"URUGUAY","USA":"UNITED STATES","UZB":"UZBEKISTAN",
 "VEN":"VENEZUELA (BOLIVARIAN REPUBLIC OF)","YEM":"YEMEN","ZAF":"SOUTH AFRICA",
}

def classify(iso):
    nm = ISO2NAME.get(iso)
    if nm is None:
        return "NA_vote", "NA_non_un"        # non-UN member holder (Taiwan, HK, Aruba)
    v = votes.get(nm, "NV")
    if v == "Y":
        return "control", "Y"
    if v in ("N", "A"):
        return "treated", v
    return "NA_vote", "non_voting"

# Labelled robustness ONLY (not the headline): named large non-Western buyer that voted
# YES (Turkey). Kept minimal/explicit to avoid gerrymandering an EM set into treated.
ROBUST_NONWESTERN_BUYER = {"TUR"}

# ---- 3. load WGC quarterly time series -------------------------------------------
d = json.load(open(f"{EVID}/cbd_quarterly_2019_2025.json"))["chartData"]
lc = d["linechart"]["QTD_FULL"]
def series(metric):
    return {s["name"]: {p[0]: p[1] for p in s["data"]} for s in lc[metric]["data"]}
tns  = series("gold_reserves_tns")   # tonnes  (DV level)
gval = series("gold_reserves")       # US$ Millions (gold value)
fxv  = series("fx_reserves")         # US$ Millions
totv = series("total_reserves")      # US$ Millions
shr  = series("holdings_pct")        # gold as % of total reserves

all_ts = sorted({ts for c in tns.values() for ts in c})
def q_of(ts):
    dt = datetime.datetime.utcfromtimestamp(ts/1000)
    return f"{dt.year}Q{(dt.month-1)//3+1}"

# ---- 4a. WGC-implied quarter-end gold price (USD/oz), median across countries -----
implied_by_q = {}
for ts in all_ts:
    prices = [gval[iso][ts]*1e6/(tns[iso][ts]*OZT_PER_TONNE)
              for iso in tns
              if tns[iso].get(ts) and gval.get(iso, {}).get(ts) and tns[iso][ts] > 0]
    if prices:
        prices.sort(); implied_by_q[ts] = prices[len(prices)//2]

# ---- 4b. World Bank Pink Sheet monthly gold price (USD/troy oz) -> quarter-end -----
wb = pd.ExcelFile(f"{EVID}/wb_pinksheet_MYFETCH.xlsx").parse("Monthly Prices", header=None)
gcol = next(j for i in range(12) for j, c in enumerate(wb.iloc[i].tolist()) if str(c) == "Gold")
QEND = {"M03": "Q1", "M06": "Q2", "M09": "Q3", "M12": "Q4"}
wb_price = {}
for i in range(len(wb)):
    lab = str(wb.iloc[i, 0])
    if re.fullmatch(r"\d{4}M\d{2}", lab) and lab[4:] in QEND:
        wb_price[f"{lab[:4]}{QEND[lab[4:]]}"] = wb.iloc[i, gcol]

# ---- 5. assemble long panel -------------------------------------------------------
rows = []
for iso in sorted(tns):
    label, votecode = classify(iso)
    prev = None
    for ts in all_ts:
        q = q_of(ts)
        lvl = tns[iso].get(ts)
        ndiff = (lvl - prev) if (lvl is not None and prev is not None) else None
        prev = lvl if lvl is not None else prev
        rows.append({
            "country_key": iso,
            "un_name": ISO2NAME.get(iso),
            "quarter": q,
            "date_qend": datetime.datetime.utcfromtimestamp(ts/1000).strftime("%Y-%m-%d"),
            "reserve_gold_tonnes": lvl,
            "net_gold_purchases_tonnes": ndiff,
            "gold_usd_value_musd": gval.get(iso, {}).get(ts),
            "fx_reserves_musd": fxv.get(iso, {}).get(ts),
            "total_reserves_musd": totv.get(iso, {}).get(ts),
            "gold_share_pct": shr.get(iso, {}).get(ts),
            "gold_usd_price_per_oz_wb": wb_price.get(q),
            "gold_usd_price_per_oz_wgc_implied": implied_by_q.get(ts),
            "es11_1_vote": votecode,
            "treat_label": label,
            "treated": 1 if label == "treated" else (0 if label == "control" else None),
            "post_freeze": 1 if q >= "2022Q1" else 0,
            "robust_nonwestern_buyer": iso in ROBUST_NONWESTERN_BUYER,
        })
df = pd.DataFrame(rows)
df.to_parquet(OUT, index=False)

# ---- 6. coverage report -----------------------------------------------------------
def has_2022plus(iso):
    return any(tns[iso].get(ts) is not None for ts in all_ts if q_of(ts) >= "2022Q1")
cls = {iso: classify(iso)[0] for iso in tns}
treated = [i for i in tns if cls[i] == "treated"]
control = [i for i in tns if cls[i] == "control"]
na      = [i for i in tns if cls[i] == "NA_vote"]
print("PANEL rows:", len(df), "countries:", df.country_key.nunique(), "quarters:", df.quarter.nunique(),
      "(", sorted(df.quarter.unique())[0], "..", sorted(df.quarter.unique())[-1], ")")
print("cols:", list(df.columns))
print("TREATED n=", len(treated), " with 2022+ tonnage:", sum(has_2022plus(i) for i in treated))
print("CONTROL n=", len(control), " with 2022+ tonnage:", sum(has_2022plus(i) for i in control))
print("NA_vote n=", len(na), " with 2022+ tonnage:", sum(has_2022plus(i) for i in na))
print("treated members:", sorted(treated))
print("robust_nonwestern_buyer:", sorted(ROBUST_NONWESTERN_BUYER))
print("WB vs WGC-implied price check:")
for ts in all_ts:
    q = q_of(ts)
    if q in ("2019Q1", "2021Q4", "2022Q1", "2024Q4", "2025Q4"):
        print(f"  {q}: WB ${wb_price.get(q):,.0f}  WGC-implied ${implied_by_q[ts]:,.0f} /oz")
for iso in ("CHN", "RUS"):
    sub = df[df.country_key == iso][["quarter", "reserve_gold_tonnes", "net_gold_purchases_tonnes"]]
    print(f"\n{iso} ({cls[iso]}):")
    print(sub[sub.quarter.isin(["2021Q4","2022Q1","2022Q2","2023Q4","2024Q4","2025Q4"])].to_string(index=False))

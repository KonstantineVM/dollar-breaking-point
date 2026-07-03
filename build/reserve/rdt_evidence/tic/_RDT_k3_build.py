#!/usr/bin/env python3
"""RDT k3 build: UST positions + net long-term Treasury transactions for 8 target holders.

Inputs (all raw files fetched from the U.S. Treasury TIC data center, retained in this
directory; see _RDT_fetch_log.txt for URLs/timestamps):
  mfhhis01.csv                  MFH history tables, monthly, Mar-2000..Dec-2025 (billions USD)
  slt_table3.txt                Table 3, all countries, monthly 2020-01..latest (millions USD);
                                holdings continuous; Net U.S. Sales / Valuation Change only from
                                2023-02 (expanded Form SLT; series break at 2023-02)
  slt3d_globl.csv               Frozen pre-2023 "more countries" holdings, 2011-09..2023-01 (millions)
  slt_table5.txt                Current MFH table (top-20 only), used for cross-check
  s1_globl.txt                  Form S transactions by country, monthly ..2023-01 (millions;
                                net Treasury purchases = col[1] gross purchases - col[7] gross sales)
  oilexp_sdata_hist_2003-2014.csv  Form S transactions for Saudi Arabia et al., 2008-01..2014-12
Outputs:
  ../../rdt_k3_ust.csv           country, date (YYYY-MM), ust_busd, source_file
  ../../rdt_k3_transactions.csv  country, period (YYYY-MM), net_purchases_busd, source_file
Merge precedence, positions: mfhhis01.csv > slt_table3.txt > slt3d_globl.csv
(mfhhis01 carries the latest MFH revisions; slt3d_globl is a frozen 2023-01 vintage).
Transactions: s1_globl.txt (+ oilexp_sdata for Saudi pre-2015) through 2023-01;
slt_table3.txt long-term net from 2023-02 (basis break documented in provenance).
"""
import csv, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..', '..'))
TARGETS = ['Russia', 'China, Mainland', 'Belgium', 'Luxembourg', 'India',
           'Turkey', 'Saudi Arabia', 'Poland']
MON = {m: i + 1 for i, m in enumerate(
    ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}


def num(s):
    s = s.replace(',', '').replace('"', '').replace('*', '').strip()
    if s in ('', 'n.a.', 'n/a', '.'):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def norm_name(name):
    return name.strip().lower().rstrip(' 0123456789/').strip()


NAMEMAP = {norm_name(t): t for t in TARGETS}

# ---------- positions: mfhhis01.csv (billions) ----------
mfh = {}
rows = list(csv.reader(open(os.path.join(HERE, 'mfhhis01.csv'), encoding='utf-8', errors='replace')))
blocks, i = [], 0
while i < len(rows):
    r = rows[i]
    months = [c.strip() for c in r]
    if (len(r) > 2 and months[0] == '' and all(m in MON or m == '' for m in months[1:])
            and sum(1 for m in months[1:] if m in MON) >= 6):
        yr = rows[i + 1]
        if yr and yr[0].strip().lower() == 'country':
            years = [c.strip() for c in yr]
            cols = [(j, f"{years[j]}-{MON[months[j]]:02d}") for j in range(1, len(months))
                    if months[j] in MON and j < len(years) and re.match(r'^(19|20)\d\d$', years[j])]
            blocks.append({'cols': cols, 'data': []})
            i += 2
            continue
    if blocks and len(r) > 1 and r[0].strip():
        blocks[-1]['data'].append(r)
    i += 1
for b in blocks:
    for r in b['data']:
        t = NAMEMAP.get(norm_name(r[0]))
        if t:
            for j, d in b['cols']:
                if j < len(r):
                    v = num(r[j])
                    if v is not None:
                        mfh[(t, d)] = v

# ---------- positions + transactions: slt_table3.txt (millions) ----------
t3_pos, t3_ltnet = {}, {}
for r in csv.reader(open(os.path.join(HERE, 'slt_table3.txt'), encoding='utf-8', errors='replace'),
                    delimiter='\t'):
    if len(r) >= 8 and r[0].strip() in TARGETS and len(r[2].strip()) == 7 and r[2].strip()[4] == '-':
        c, d = r[0].strip(), r[2].strip()
        p, ln = num(r[3]), num(r[6])
        if p is not None:
            t3_pos[(c, d)] = p / 1000.0
        if ln is not None and d >= '2023-02':   # net columns valid only from the 2023-02 break
            t3_ltnet[(c, d)] = ln / 1000.0

# ---------- positions: slt3d_globl.csv (millions, frozen vintage ..2023-01) ----------
slt3d = {}
for r in csv.reader(open(os.path.join(HERE, 'slt3d_globl.csv'), encoding='utf-8', errors='replace')):
    if len(r) >= 6 and r[0].strip() in TARGETS and len(r[2].strip()) == 7 and r[2].strip()[4] == '-':
        v = num(r[3])
        if v is not None:
            slt3d[(r[0].strip(), r[2].strip())] = v / 1000.0

# ---------- merge positions ----------
pos_rows = []
all_dates = sorted({d for (_, d) in list(mfh) + list(t3_pos) + list(slt3d)})
discrepancies = []
for t in TARGETS:
    for d in all_dates:
        if (t, d) in mfh:
            pos_rows.append((t, d, mfh[(t, d)], 'mfhhis01.csv'))
            for src, dd in (('slt_table3.txt', t3_pos), ('slt3d_globl.csv', slt3d)):
                if (t, d) in dd and abs(dd[(t, d)] - mfh[(t, d)]) > 1.0:
                    discrepancies.append((t, d, mfh[(t, d)], src, round(dd[(t, d)], 3)))
        elif (t, d) in t3_pos:
            pos_rows.append((t, d, t3_pos[(t, d)], 'slt_table3.txt'))
        elif (t, d) in slt3d:
            pos_rows.append((t, d, slt3d[(t, d)], 'slt3d_globl.csv'))
with open(os.path.join(OUT, 'rdt_k3_ust.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['country', 'date', 'ust_busd', 'source_file'])
    for t, d, v, s in pos_rows:
        w.writerow([t, d, round(v, 3), s])

# ---------- transactions: s1_globl.txt (Form S, net LT Treasury, millions) ----------
s1 = {}
for r in csv.reader(open(os.path.join(HERE, 's1_globl.txt'), encoding='utf-8', errors='replace'),
                    delimiter='\t'):
    if len(r) >= 10 and r[0].strip() in TARGETS and len(r[2].strip()) == 7 and r[2].strip()[4] == '-':
        gp, gs = num(r[3]), num(r[9])
        if gp is not None and gs is not None:
            s1[(r[0].strip(), r[2].strip())] = (gp - gs) / 1000.0

# ---------- transactions: oilexp_sdata (Saudi Arabia 2008-01..2014-12) ----------
oil = {}
for r in csv.reader(open(os.path.join(HERE, 'oilexp_sdata_hist_2003-2014.csv'),
                         encoding='utf-8', errors='replace')):
    if len(r) >= 10 and r[0].strip() == 'Saudi Arabia' and len(r[2].strip()) == 7:
        gp, gs = num(r[3]), num(r[9])
        if gp is not None and gs is not None:
            oil[('Saudi Arabia', r[2].strip())] = (gp - gs) / 1000.0

tx_rows = []
tx_dates = sorted({d for (_, d) in list(s1) + list(oil) + list(t3_ltnet)})
for t in TARGETS:
    for d in tx_dates:
        if d < '2013-01':
            continue
        if d >= '2023-02' and (t, d) in t3_ltnet:
            tx_rows.append((t, d, t3_ltnet[(t, d)], 'slt_table3.txt'))
        elif (t, d) in s1:
            tx_rows.append((t, d, s1[(t, d)], 's1_globl.txt'))
        elif (t, d) in oil:
            tx_rows.append((t, d, oil[(t, d)], 'oilexp_sdata_hist_2003-2014.csv'))
with open(os.path.join(OUT, 'rdt_k3_transactions.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['country', 'period', 'net_purchases_busd', 'source_file'])
    for t, d, v, s in tx_rows:
        w.writerow([t, d, round(v, 3), s])

# ---------- report ----------
print('positions rows:', len(pos_rows), ' transactions rows:', len(tx_rows))
for t in TARGETS:
    ds = [d for (c, d, _, _) in pos_rows if c == t]
    xs = [d for (c, d, _, _) in tx_rows if c == t]
    print(f'{t:18s} pos {ds[0]}..{ds[-1]} n={len(ds)} | tx {xs[0]}..{xs[-1]} n={len(xs)}')
print('\nANCHOR Russia 2018 (ust_busd):')
for d in ['2018-01', '2018-02', '2018-03', '2018-04', '2018-05', '2018-06', '2018-12']:
    print(' ', d, [v for (c, dd, v, s) in pos_rows if c == 'Russia' and dd == d])
print('\nsource disagreements > $1.0B (mfhhis01 kept):')
for x in discrepancies:
    print(' ', x)

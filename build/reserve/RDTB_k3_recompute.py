#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RDT-B Part B — k3 differential test: all-country cross-holder distribution of
annualized active long-term-Treasury flow rates, China's percentile (both custody
variants), the ES-11/1 treated/control split, and the aggregate foreign-OFFICIAL
baseline. Pre-registered contract: build/reserve/RDTB_prediction.md (Part B).

Deterministic: regenerates build/reserve/RDTB_k3_distribution.json (and the
intermediate panel build/reserve/RDTB_k3_panel.parquet) from on-disk inputs alone.
No network. Nothing hardcoded: every statistic is computed here from the raw files.

Inputs (all read-only, on disk):
  build/reserve/rdt_evidence/tic/mfhhis01.csv            MFH history, monthly holdings, billions
  build/reserve/rdt_evidence/tic/slt_table3.txt          Table 3 all countries, millions; holdings
                                                         2020-01.., net LT Treasury purchases from
                                                         2023-02 (Form S -> SLT basis break)
  build/reserve/rdt_evidence/tic/slt3d_globl.csv         frozen holdings 2011-09..2023-01, millions
  build/reserve/rdt_evidence/tic/s1_globl.txt            Form S gross transactions to 2023-01, millions
  build/reserve/rdt_evidence/tic/oilexp_sdata_hist_2003-2014.csv  Form S for Bahrain/Kuwait/Saudi/UAE
  build/reserve/rdt_evidence/tic/slt_table5.txt          current MFH table (cross-check only)
  build/reserve/rd0_evidence/un_digitallibrary_es11_1_votelines.txt  ES-11/1 vote lines
  build/reserve/rdt_k3_ust.csv, rdt_k3_transactions.csv  the committed 8-country build (cross-check)

Scaling (pre-registered, exact): r_c = [Sum of monthly net LT Treasury purchases over
window] / H_c(month immediately preceding window) / (window years).
Windows: recent-3y = last 36 published months (VERDICT axis, fixed ex ante);
full = 2013-01 (or first coverage) -> latest (context, always shown).
Universe: H_c(start) >= $10bn AND >= 30/36 non-missing tx months (proportional for full).

The 2023-02 Form S -> SLT transactions basis break (rdt_k3_provenance.md) applies to
ALL countries and is carried row-by-row in the panel's tx_source column.

The rank-sum normal-approximation p is a pre-registered DESCRIPTIVE statistic
(statsmodels not installed; numpy/math implementation below). No date and no
probability-of-event is computed anywhere in this script.
"""
import csv
import hashlib
import json
import math
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))                 # build/reserve
TIC = os.path.join(HERE, 'rdt_evidence', 'tic')
VOTEFILE = os.path.join(HERE, 'rd0_evidence', 'un_digitallibrary_es11_1_votelines.txt')
OUT_JSON = os.path.join(HERE, 'RDTB_k3_distribution.json')
OUT_PANEL = os.path.join(HERE, 'RDTB_k3_panel.parquet')

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


def strip_fn(name):
    """Strip MFH footnote markers, e.g. 'United Kingdom  2/' -> 'United Kingdom'."""
    return re.sub(r'\s+\d+/\s*$', '', name.strip()).strip()


def month_add(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    t = y * 12 + (m - 1) + k
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


def month_range(a, b):
    out, d = [], a
    while d <= b:
        out.append(d)
        d = month_add(d, 1)
    return out


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------------
# Row labels that are NOT individual country/territory holders (aggregates,
# sector lines, memoranda, IROs, multi-territory groupings). Mechanical filter,
# recorded in the JSON. Sector/official lines are parsed SEPARATELY below.
# ----------------------------------------------------------------------------
NON_COUNTRY = {
    # totals / residuals
    'All Other', 'Grand Total', 'All Countries', 'Country Unknown',
    # MFH official-sector block (used separately for the baseline)
    'Of which:', 'For. Official', 'Treasury Bills', 'T-Bonds & Notes',
    # Table 3 sector lines (official line used separately for the baseline)
    'Of Which: Foreign Official', 'Of Which: Foreign Non-Official',
    'Of which Foreign Official',
    # regional / memo aggregates
    'Carib Bnkng Ctrs', 'Oil Exporters', 'Memo: Euro Area', 'Memo: European Union',
    'Total Africa', 'Total Asia', 'Total Caribbean', 'Total Europe', 'Total IROs',
    'Total Latin America', 'Total Latin America and Caribbean', 'Total Other',
    'Total Regional Orgs.',
    # international / regional organizations, not countries
    'International',
    # multi-territory groupings (component territories appear separately)
    'Belgium-Luxembourg', 'Belgium and Luxembourg', 'Channel Islands and Isle of Man',
    'British West Indies',
    # header junk
    'Country', '----------', 'Memo:',
}


def is_country(name):
    n = name.strip()
    return bool(n) and n not in NON_COUNTRY and not n.startswith('Memo:') \
        and not n.startswith('Of ') and not n.startswith('Total ') \
        and not n.startswith('-')


# ----------------------------------------------------------------------------
# 1) Parse positions: mfhhis01.csv (billions) — all named rows in yearly blocks
# ----------------------------------------------------------------------------
def parse_mfhhis01(path):
    rows = list(csv.reader(open(path, encoding='utf-8', errors='replace')))
    holders, sector = {}, {}   # holders[(name, ym)] = busd ; sector likewise
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
                        if months[j] in MON and j < len(years)
                        and re.match(r'^(19|20)\d\d$', years[j])]
                blocks.append({'cols': cols, 'data': []})
                i += 2
                continue
        if blocks and len(r) > 1 and r[0].strip():
            blocks[-1]['data'].append(r)
        i += 1
    for b in blocks:
        for r in b['data']:
            raw = r[0].strip()
            name = strip_fn(raw)
            vals = [(d, num(r[j])) for j, d in b['cols'] if j < len(r)]
            vals = [(d, v) for d, v in vals if v is not None]
            if not vals:
                continue                      # footnote / free-text rows carry no month values
            target = holders if is_country(name) else sector
            for d, v in vals:
                target[(name, d)] = v
    return holders, sector, len(blocks)


# ----------------------------------------------------------------------------
# 2) Parse slt_table3.txt (millions): holdings all months; LT net only >= 2023-02
#    Columns: 0 country 1 code 2 date 3 total pos 4 total net 5 LT pos 6 LT net
#             7 LT valchg 8 ST pos 9 ST net
# ----------------------------------------------------------------------------
def parse_slt_table3(path):
    pos_tot, pos_lt, net_lt = {}, {}, {}
    for r in csv.reader(open(path, encoding='utf-8', errors='replace'), delimiter='\t'):
        if len(r) >= 7 and len(r[2].strip()) == 7 and r[2].strip()[4] == '-':
            c, d = r[0].strip(), r[2].strip()
            p, plt = num(r[3]), num(r[5])
            ln = num(r[6]) if len(r) >= 7 else None
            if p is not None:
                pos_tot[(c, d)] = p / 1000.0
            if plt is not None:
                pos_lt[(c, d)] = plt / 1000.0
            if ln is not None and d >= '2023-02':   # publisher basis break: SLT-based from 2023-02
                net_lt[(c, d)] = ln / 1000.0
    return pos_tot, pos_lt, net_lt


# ----------------------------------------------------------------------------
# 3) Parse slt3d_globl.csv (frozen holdings 2011-09..2023-01, millions)
# ----------------------------------------------------------------------------
def parse_slt3d(path):
    out = {}
    for r in csv.reader(open(path, encoding='utf-8', errors='replace')):
        if len(r) >= 6 and len(r[2].strip()) == 7 and r[2].strip()[4] == '-':
            v = num(r[3])
            if v is not None:
                out[(r[0].strip(), r[2].strip())] = v / 1000.0
    return out


# ----------------------------------------------------------------------------
# 4) Parse Form S transactions (millions): net LT Treasury = col[1]-col[7]
#    (fields 3 and 9 in the tab layout), through 2023-01
# ----------------------------------------------------------------------------
def parse_form_s(path, only_countries=None, delimiter='\t'):
    out = {}
    reader = csv.reader(open(path, encoding='utf-8', errors='replace'), delimiter=delimiter)
    for r in reader:
        if len(r) >= 10 and len(r[2].strip()) == 7 and r[2].strip()[4] == '-':
            c, d = r[0].strip(), r[2].strip()
            if only_countries is not None and c not in only_countries:
                continue
            gp, gs = num(r[3]), num(r[9])
            if gp is not None and gs is not None:
                out[(c, d)] = (gp - gs) / 1000.0
    return out


# ----------------------------------------------------------------------------
# 5) Parse the ES-11/1 vote lines (UN Digital Library HTML extract)
# ----------------------------------------------------------------------------
def parse_votes(path):
    html = open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r'>\s*(Y AFGHANISTAN.*?)</span>', html, re.S)
    if not m:
        raise RuntimeError('ES-11/1 vote block not found in vote file')
    votes = {}
    for tok in m.group(1).split('<br />'):
        t = re.sub(r'<[^>]+>', '', tok).strip()
        if not t:
            continue
        mm = re.match(r'^([YNA])\s+(\S.*)$', t)
        if mm:
            votes[mm.group(2).strip().upper()] = mm.group(1)
        else:
            votes[t.upper()] = 'NV'         # listed member, no recorded vote (non-voting)
    return votes


# TIC country name (uppercased) -> UN member name in the vote record.
# Mechanical alias table (disclosed); anything not matched stays unmapped.
UN_ALIASES = {
    'CHINA, MAINLAND': 'CHINA',
    'KOREA, SOUTH': 'REPUBLIC OF KOREA',
    'RUSSIA': 'RUSSIAN FEDERATION',
    'CZECH REPUBLIC': 'CZECHIA',
    'SYRIA': 'SYRIAN ARAB REPUBLIC',
    'VENEZUELA': 'VENEZUELA (BOLIVARIAN REPUBLIC OF)',
    'VIETNAM': 'VIET NAM',
    'BOLIVIA': 'BOLIVIA (PLURINATIONAL STATE OF)',
    'IRAN': 'IRAN (ISLAMIC REPUBLIC OF)',
    'TANZANIA': 'UNITED REPUBLIC OF TANZANIA',
    'MOLDOVA': 'REPUBLIC OF MOLDOVA',
    'BRUNEI': 'BRUNEI DARUSSALAM',
    'LAOS': "LAO PEOPLE'S DEMOCRATIC REPUBLIC",
    'CAPE VERDE': 'CABO VERDE',
    "COTE D'IVOIRE": "CÔTE D'IVOIRE",
    'MICRONESIA': 'MICRONESIA (FEDERATED STATES OF)',
    'NORTH KOREA': "DEMOCRATIC PEOPLE'S REPUBLIC OF KOREA",
}


# ----------------------------------------------------------------------------
# 6) Rank-sum (Wilcoxon/Mann-Whitney) normal approximation, tie-corrected.
#    numpy + math only (statsmodels not installed). DESCRIPTIVE statistic.
# ----------------------------------------------------------------------------
def ranksum_normal(x_treated, y_control):
    x = np.asarray(x_treated, dtype=float)
    y = np.asarray(y_control, dtype=float)
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return None
    allv = np.concatenate([x, y])
    N = n1 + n2
    order = np.argsort(allv, kind='stable')
    sv = allv[order]
    ranks = np.empty(N, dtype=float)
    i = 0
    tie_sum = 0.0
    while i < N:
        j = i
        while j + 1 < N and sv[j + 1] == sv[i]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        ranks[order[i:j + 1]] = avg
        t = j - i + 1
        tie_sum += t ** 3 - t
        i = j + 1
    W = float(ranks[:n1].sum())
    mu = n1 * (N + 1) / 2.0
    var = n1 * n2 / 12.0 * ((N + 1) - tie_sum / (N * (N - 1)))
    if var <= 0:
        return None
    z = (W - mu) / math.sqrt(var)
    phi = lambda t: 0.5 * (1.0 + math.erf(t / math.sqrt(2.0)))
    return {
        'rank_sum_W_treated': W,
        'expected_W_under_H0': mu,
        'z_normal_approx': z,
        'p_two_sided': 2.0 * (1.0 - phi(abs(z))),
        'p_one_sided_treated_more_negative': phi(z),
        'n_treated': n1, 'n_control': n2,
    }


# ----------------------------------------------------------------------------
# main build
# ----------------------------------------------------------------------------
def main():
    inputs = {
        'mfhhis01.csv': os.path.join(TIC, 'mfhhis01.csv'),
        'slt_table3.txt': os.path.join(TIC, 'slt_table3.txt'),
        'slt3d_globl.csv': os.path.join(TIC, 'slt3d_globl.csv'),
        's1_globl.txt': os.path.join(TIC, 's1_globl.txt'),
        'oilexp_sdata_hist_2003-2014.csv': os.path.join(TIC, 'oilexp_sdata_hist_2003-2014.csv'),
        'slt_table5.txt': os.path.join(TIC, 'slt_table5.txt'),
        'un_digitallibrary_es11_1_votelines.txt': VOTEFILE,
        'rdt_k3_ust.csv': os.path.join(HERE, 'rdt_k3_ust.csv'),
        'rdt_k3_transactions.csv': os.path.join(HERE, 'rdt_k3_transactions.csv'),
    }
    input_hashes = {k: sha256_file(p) for k, p in sorted(inputs.items())}

    mfh_hold, mfh_sector, n_blocks = parse_mfhhis01(inputs['mfhhis01.csv'])
    t3_pos, t3_pos_lt, t3_net = parse_slt_table3(inputs['slt_table3.txt'])
    slt3d = parse_slt3d(inputs['slt3d_globl.csv'])
    s1 = parse_form_s(inputs['s1_globl.txt'])
    oil = parse_form_s(inputs['oilexp_sdata_hist_2003-2014.csv'], delimiter=',')
    votes = parse_votes(inputs['un_digitallibrary_es11_1_votelines.txt'])

    vote_counts = {v: sum(1 for x in votes.values() if x == v) for v in ('Y', 'N', 'A', 'NV')}
    vote_tally_check = (vote_counts == {'Y': 141, 'N': 5, 'A': 35, 'NV': 12})

    # ---- merged holdings panel (country level), precedence mfhhis01 > table3 > slt3d
    countries = sorted({c for (c, _) in list(mfh_hold) + list(t3_pos) + list(slt3d) + list(s1)
                        + list(oil) if is_country(c)})
    H, Hsrc = {}, {}
    for key_src, src_name in ((mfh_hold, 'mfhhis01.csv'), (t3_pos, 'slt_table3.txt'),
                              (slt3d, 'slt3d_globl.csv')):
        for (c, d), v in key_src.items():
            if is_country(c) and (c, d) not in H:
                H[(c, d)], Hsrc[(c, d)] = v, src_name

    # ---- merged transactions panel: SLT basis >= 2023-02; Form S (+oilexp) <= 2023-01
    TX, TXsrc = {}, {}
    for (c, d), v in t3_net.items():
        if is_country(c) and d >= '2023-02':
            TX[(c, d)], TXsrc[(c, d)] = v, 'slt_table3.txt'
    for (c, d), v in s1.items():
        if is_country(c) and '2013-01' <= d <= '2023-01' and (c, d) not in TX:
            TX[(c, d)], TXsrc[(c, d)] = v, 's1_globl.txt'
    for (c, d), v in oil.items():
        if is_country(c) and '2013-01' <= d <= '2023-01' and (c, d) not in TX:
            TX[(c, d)], TXsrc[(c, d)] = v, 'oilexp_sdata_hist_2003-2014.csv'

    latest = max(d for (_, d) in TX)
    first_full = '2013-01'

    # ---- windows
    recent_months = month_range(month_add(latest, -35), latest)
    recent_start_hold = month_add(recent_months[0], -1)

    # ---- cross-check against the committed 8-country build
    def crosscheck(csv_path, panel, valcol):
        maxd, nrows, nmissing = 0.0, 0, 0
        worst = None
        for row in csv.DictReader(open(csv_path, encoding='utf-8')):
            c, d = row['country'], row.get('date') or row.get('period')
            v = float(row[valcol])
            nrows += 1
            if (c, d) in panel:
                diff = abs(round(panel[(c, d)], 3) - v)
                if diff > maxd:
                    maxd, worst = diff, [c, d, v, round(panel[(c, d)], 3)]
            else:
                nmissing += 1
        return {'rows_compared': nrows, 'rows_missing_in_panel': nmissing,
                'max_abs_diff_busd': round(maxd, 6), 'worst_cell': worst}

    xc_ust = crosscheck(inputs['rdt_k3_ust.csv'], H, 'ust_busd')
    xc_tx = crosscheck(inputs['rdt_k3_transactions.csv'], TX, 'net_purchases_busd')

    # ---- per-country rate for a window
    def country_rate(c, months, start_hold):
        h0 = H.get((c, start_hold))
        nm = [m for m in months if (c, m) in TX]
        tot = sum(TX[(c, m)] for m in nm)
        years = len(months) / 12.0
        r = (tot / h0 / years) if (h0 is not None and h0 != 0) else None
        return h0, len(nm), tot, years, r

    def build_window(months, start_hold, label, proportional=False):
        n_req_num, n_req_den = 30, 36
        incl, excl = [], []
        for c in countries:
            if proportional:
                tx_months = sorted(d for (cc, d) in TX if cc == c and months[0] <= d <= months[-1])
                first_tx_any = min((d for (cc, d) in TX if cc == c), default=None)
                if first_tx_any is None:
                    excl.append({'country': c, 'reason': 'no transactions data in any source'})
                    continue
                wstart = max(months[0], first_tx_any)
                wmonths = month_range(wstart, months[-1])
                sh = month_add(wstart, -1)
            else:
                wmonths, sh = months, start_hold
            h0, nmiss_ok, tot, years, r = country_rate(c, wmonths, sh)
            need = math.ceil(n_req_num / n_req_den * len(wmonths) - 1e-9)
            if h0 is None:
                excl.append({'country': c,
                             'reason': f'no holdings observation at window start ({sh})'})
            elif h0 < 10.0:
                excl.append({'country': c, 'reason': f'holdings at window start ({sh}) '
                             f'= {round(h0, 3)} $bn < $10bn small-denominator guard'})
            elif nmiss_ok < need:
                excl.append({'country': c, 'reason': f'only {nmiss_ok} of {len(wmonths)} '
                             f'transaction months non-missing (< {need} required)'})
            else:
                incl.append({'country': c, 'window_start': wmonths[0], 'window_end': wmonths[-1],
                             'holdings_at_start_busd': round(h0, 3),
                             'n_months': len(wmonths), 'n_tx_months_nonmissing': nmiss_ok,
                             'sum_net_purchases_busd': round(tot, 3),
                             'window_years': round(years, 6),
                             'r_annualized_active_flow_rate': round(r, 6)})
        incl.sort(key=lambda x: x['r_annualized_active_flow_rate'])
        return incl, excl

    recent_incl, recent_excl = build_window(recent_months, recent_start_hold, 'recent')
    full_months = month_range(first_full, latest)
    full_incl, full_excl = build_window(full_months, month_add(first_full, -1),
                                        'full', proportional=True)

    # ---- China custody variants
    POOL = ['China, Mainland', 'Belgium', 'Luxembourg']
    POOL_NAME = 'China+Belgium+Luxembourg (synthetic pooled holder, custody upper variant)'

    def pooled_rate(months, start_hold):
        h0s = [H.get((c, start_hold)) for c in POOL]
        if any(v is None for v in h0s):
            return None
        h0 = sum(h0s)
        nm = [m for m in months if all((c, m) in TX for c in POOL)]
        tot = sum(TX[(c, m)] for c in POOL for m in nm)
        years = len(months) / 12.0
        return {'holdings_at_start_busd': round(h0, 3), 'n_months': len(months),
                'n_tx_months_nonmissing_all3': len(nm),
                'sum_net_purchases_busd': round(tot, 3), 'window_years': round(years, 6),
                'r_annualized_active_flow_rate': round(tot / h0 / years, 6)}

    def percentile_block(incl, months, start_hold):
        rs = {e['country']: e['r_annualized_active_flow_rate'] for e in incl}
        out = {}
        cn = rs.get('China, Mainland')
        if cn is not None:
            vals = np.array(list(rs.values()))
            out['china_alone'] = {
                'r': cn,
                'percentile_frac_of_universe_with_r_le_china': round(float((vals <= cn).mean()), 6),
                'universe_n': int(len(vals)),
            }
        pooled = pooled_rate(months, start_hold)
        if pooled is not None:
            rs2 = {c: v for c, v in rs.items() if c not in POOL}
            rs2[POOL_NAME] = pooled['r_annualized_active_flow_rate']
            vals2 = np.array(list(rs2.values()))
            rp = pooled['r_annualized_active_flow_rate']
            out['china_pooled_cn_be_lu'] = {
                **pooled,
                'r': rp,
                'percentile_frac_of_universe_with_r_le_pooled': round(float((vals2 <= rp).mean()), 6),
                'universe_n_with_pool_replacing_components': int(len(vals2)),
                'note': 'pooled holder replaces China/Belgium/Luxembourg individual entries '
                        'in its universe (no double counting); labelled synthetic',
            }
        return out

    pct_recent = percentile_block(recent_incl, recent_months, recent_start_hold)
    # full-window pooled uses the 2013-01 window (all three countries covered from 2013-01)
    pct_full = percentile_block(full_incl, full_months, month_add(first_full, -1))

    # ---- ES-11/1 split (individual-country universe; synthetic pool excluded by design)
    def es_split(incl):
        mapping, treated, control, out_of_split = [], [], [], []
        for e in incl:
            c = e['country']
            key = UN_ALIASES.get(c.upper(), c.upper())
            v = votes.get(key)
            rec = {'country': c, 'un_name_matched': key if v else None,
                   'vote': v if v else 'UNMAPPED'}
            mapping.append(rec)
            r = e['r_annualized_active_flow_rate']
            if v in ('N', 'A'):
                treated.append((c, r))
            elif v == 'Y':
                control.append((c, r))
            else:
                out_of_split.append({'country': c,
                                     'reason': ('UN member, no recorded vote (non-voting)'
                                                if v == 'NV' else
                                                'not matched to a UN member (non-UN entity '
                                                'or unmapped name)')})
        tr = np.array([r for _, r in treated]) if treated else np.array([])
        co = np.array([r for _, r in control]) if control else np.array([])
        stats = {
            'treated_no_abstain': {'n': len(treated),
                                   'members': [c for c, _ in sorted(treated)],
                                   'median_r': round(float(np.median(tr)), 6) if len(tr) else None,
                                   'mean_r': round(float(tr.mean()), 6) if len(tr) else None},
            'control_yes': {'n': len(control),
                            'members': [c for c, _ in sorted(control)],
                            'median_r': round(float(np.median(co)), 6) if len(co) else None,
                            'mean_r': round(float(co.mean()), 6) if len(co) else None},
            'out_of_split': out_of_split,
            'mapping': mapping,
        }
        rk = ranksum_normal(tr, co) if len(tr) and len(co) else None
        if rk:
            rk = {k: (round(v, 6) if isinstance(v, float) else v) for k, v in rk.items()}
            rk['label'] = ('DESCRIPTIVE statistic (pre-registered): Wilcoxon rank-sum, '
                           'tie-corrected normal approximation; small treated N — no causal '
                           'claim, not a probability of any event')
        stats['rank_sum_normal_approx'] = rk
        return stats

    es_recent = es_split(recent_incl)
    es_full = es_split(full_incl)

    # ---- BASELINE: aggregate foreign-OFFICIAL Treasury rolloff
    # Official-aggregate lines found ON DISK:
    #   holdings: mfhhis01.csv 'For. Official' (total, monthly ..2025-12) and its LT sub-line
    #             'T-Bonds & Notes'; slt_table3.txt 'Of Which: Foreign Official' (2020-01..latest)
    #   transactions: slt_table3.txt 'Of Which: Foreign Official' net LT column, valid from
    #             2023-02 (covers the ENTIRE recent-3y window); NOT published pre-2023-02
    OFF = 'Of Which: Foreign Official'
    Hoff = {}
    for (c, d), v in mfh_sector.items():
        if c == 'For. Official':
            Hoff[d] = v
    for (c, d), v in t3_pos.items():
        if c == OFF and d not in Hoff:
            Hoff[d] = v
    Hoff_lt = {}
    for (c, d), v in mfh_sector.items():
        if c == 'T-Bonds & Notes':
            Hoff_lt[d] = v
    for (c, d), v in t3_pos_lt.items():
        if c == OFF and d not in Hoff_lt:
            Hoff_lt[d] = v
    TXoff = {d: v for (c, d), v in t3_net.items() if c == OFF}

    def off_recent():
        h0 = Hoff.get(recent_start_hold)
        nm = [m for m in recent_months if m in TXoff]
        tot = sum(TXoff[m] for m in nm)
        years = len(recent_months) / 12.0
        prim = round(tot / h0 / years, 6)
        h0lt = Hoff_lt.get(recent_start_hold)
        dH = Hoff.get(recent_months[-1]) - h0
        return {
            'status': 'ON-DISK',
            'series': ("slt_table3.txt row 'Of Which: Foreign Official' net LT Treasury "
                       "purchases (2023-02..latest, expanded-SLT basis) scaled by mfhhis01.csv "
                       "'For. Official' total Treasury holdings at window start — same "
                       "transactions-over-starting-holdings scaling as the country rates"),
            'window': [recent_months[0], recent_months[-1]],
            'holdings_official_total_at_start_busd': round(h0, 3),
            'n_tx_months_nonmissing': len(nm), 'n_months': len(recent_months),
            'sum_official_net_lt_purchases_busd': round(tot, 3),
            'r_off_primary_tx_basis': prim,
            'variants': {
                'r_off_lt_holdings_denominator': round(tot / h0lt / years, 6),
                'r_off_holdings_change_basis': round(dH / h0 / years, 6),
                'holdings_change_note': ('holdings-change variant includes valuation change '
                                         'and bills; shown for context only'),
            },
        }

    def off_full():
        sh = month_add(first_full, -1)
        h0 = Hoff.get(sh)
        years = len(full_months) / 12.0
        dH = Hoff.get(full_months[-1]) - h0
        h0lt = Hoff_lt.get(sh)
        dHlt = Hoff_lt.get(full_months[-1]) - h0lt
        return {
            'status': 'ON-DISK (holdings basis)',
            'basis_note': ('official-sector TRANSACTIONS are not published before the 2023-02 '
                           'Form S -> SLT break (verified: slt_table3 net columns n.a. pre-'
                           '2023-02; s1_globl.txt carries no official-sector line), so the '
                           'full-window baseline is the HOLDINGS-change rolloff (includes '
                           'valuation change), labelled as such; the verdict axis is recent-3y, '
                           'where the tx-basis baseline exists'),
            'window': [full_months[0], full_months[-1]],
            'holdings_official_total_at_start_busd': round(h0, 3),
            'holdings_official_total_at_end_busd': round(Hoff[full_months[-1]], 3),
            'r_off_holdings_change_basis': round(dH / h0 / years, 6),
            'r_off_lt_holdings_change_basis': round(dHlt / h0lt / years, 6),
        }

    baseline_recent = off_recent()
    baseline_full = off_full()

    # context: all-foreign Grand Total, same scaling (tx basis, recent window)
    Hgt = {d: v for (c, d), v in mfh_sector.items() if c == 'Grand Total'}
    for (c, d), v in t3_pos.items():
        if c == 'Grand Total' and d not in Hgt:
            Hgt[d] = v
    TXgt = {d: v for (c, d), v in t3_net.items() if c == 'Grand Total'}
    gt_tot = sum(TXgt[m] for m in recent_months if m in TXgt)
    context_all_foreign = {
        'r_all_foreign_tx_basis_recent': round(gt_tot / Hgt[recent_start_hold] / 3.0, 6),
        'sum_net_lt_purchases_busd': round(gt_tot, 3),
        'holdings_at_start_busd': round(Hgt[recent_start_hold], 3),
        'note': 'Grand Total (official + private) context number, same scaling',
    }

    # ---- verdict (mechanical, pre-registered; axis = recent-3y) — all three axes computable
    r_cn = pct_recent['china_alone']['r']
    pct_cn = pct_recent['china_alone']['percentile_frac_of_universe_with_r_le_china']
    r_off = baseline_recent['r_off_primary_tx_basis']
    axis_i = pct_cn <= 0.10
    both_neg = (r_cn < 0 and r_off < 0)
    ratio = (r_cn / r_off) if r_off != 0 else None
    axis_ii = (r_off >= 0) or (both_neg and ratio is not None and ratio > 2.0)
    rk = es_recent['rank_sum_normal_approx']
    med_t = es_recent['treated_no_abstain']['median_r']
    med_c = es_recent['control_yes']['median_r']
    axis_iii = (rk is not None and med_t is not None and med_c is not None
                and med_t < med_c and rk['p_two_sided'] < 0.10)
    axis_iii_one_sided = (rk is not None and med_t is not None and med_c is not None
                          and med_t < med_c
                          and rk['p_one_sided_treated_more_negative'] < 0.10)
    baseline_comparable = (both_neg and ratio is not None and 0.5 <= ratio <= 2.0)
    if axis_i and axis_ii and axis_iii:
        verdict = 'DIFFERENTIAL'
    elif (pct_cn > 0.25 or baseline_comparable) and not axis_iii:
        verdict = 'UNIVERSAL-ROLLOFF'
    else:
        mixing = []
        if not (pct_cn > 0.25) and not axis_i:
            mixing.append('percentile (between the 10% tail and the 25% universal threshold)')
        if axis_i:
            mixing.append('percentile axis satisfies the differential tail')
        if axis_ii and not baseline_comparable:
            mixing.append('baseline axis satisfies beyond-baseline')
        if not axis_ii and not baseline_comparable:
            mixing.append('baseline (neither beyond-baseline nor baseline-comparable)')
        if axis_iii:
            mixing.append('treated/control split shows treated-specific selling')
        else:
            mixing.append('treated/control split does NOT show treated-specific selling '
                          '(fails the differential requirement (iii))')
        verdict = 'MIXED'
        verdict_mixing_axes = mixing
    verdict_block = {
        'verdict_axis': 'recent-3y window (fixed ex ante in RDTB_prediction.md)',
        'axis_i_percentile_tail': {'value': pct_cn, 'threshold': 0.10, 'pass': bool(axis_i)},
        'axis_ii_beyond_baseline': {'r_china_alone': r_cn, 'r_off': r_off,
                                    'ratio_r_cn_over_r_off': round(ratio, 6) if ratio is not None else None,
                                    'rule': 'r_off >= 0 OR (both negative AND ratio > 2)',
                                    'pass': bool(axis_ii),
                                    'baseline_comparable_band_0p5_to_2': bool(baseline_comparable)},
        'axis_iii_treated_control': {'treated_median': med_t, 'control_median': med_c,
                                     'p_two_sided': rk['p_two_sided'] if rk else None,
                                     'p_one_sided_treated_more_negative':
                                         rk['p_one_sided_treated_more_negative'] if rk else None,
                                     'p_used_for_verdict': 'two-sided (standard rank-sum default; '
                                     'the direction requirement is carried separately by the '
                                     'median condition; one-sided reported beside it)',
                                     'pass_two_sided': bool(axis_iii),
                                     'pass_one_sided': bool(axis_iii_one_sided),
                                     'sidedness_outcome_relevant': bool(axis_iii != axis_iii_one_sided)},
        'verdict': verdict,
    }
    if verdict == 'MIXED':
        verdict_block['mixing_axes'] = verdict_mixing_axes

    # ---- assemble payload
    payload = {
        'artifact': 'RDTB_k3_distribution',
        'contract': 'build/reserve/RDTB_prediction.md — Part B (pre-registered, mechanical)',
        'establishment': ('NOT ESTABLISHED — output of the RDT-B Part-B estimation run; '
                          'no result herein is established until the verifier scenario '
                          '(deterministic re-run of build/reserve/RDTB_k3_recompute.py '
                          'reproducing this JSON, recorded in build/reserve/RDTB_verify.json) '
                          'has run and its artifact exists'),
        'no_date_no_probability': ('no date and no event-probability is computed; the rank-sum '
                                   'normal-approximation p is a pre-registered DESCRIPTIVE '
                                   'statistic with a small-N caveat'),
        'inputs_sha256': input_hashes,
        'scaling': ('r_c = [sum of monthly net purchases of long-term Treasuries over window] '
                    '/ H_c(month immediately preceding window) / (window years); '
                    'holdings = total Treasury holdings (MFH concept, bills included); '
                    'transactions = long-term Treasury bonds & notes only (bills not published '
                    'in the transactions data)'),
        'basis_break': ('publisher basis break at 2023-02 carried for ALL countries: '
                        'transactions before 2023-02 are Form S (s1_globl.txt / oilexp_sdata), '
                        'from 2023-02 expanded Form SLT (slt_table3.txt); recent-3y window lies '
                        'entirely on the post-break SLT basis (uniform basis on the verdict axis)'),
        'custody_caveat': ('TIC custodial attribution (TIC FAQ #7, printed on Table 5): '
                           'overseas-custody holdings may not be attributed to actual owners; '
                           'hence the China-alone AND China+Belgium+Luxembourg custody band, '
                           'never collapsed'),
        'panel': {
            'countries_in_panel': len(countries),
            'holdings_cells': len(H), 'transactions_cells': len(TX),
            'latest_published_tx_month': latest,
            'mfh_year_blocks_parsed': n_blocks,
            'non_country_rows_excluded_from_panel': sorted(NON_COUNTRY - {'Country', '----------', 'Memo:'}),
            'positions_precedence': 'mfhhis01.csv > slt_table3.txt > slt3d_globl.csv',
        },
        'crosscheck_vs_committed_8country_build': {
            'rdt_k3_ust.csv': xc_ust, 'rdt_k3_transactions.csv': xc_tx,
            'pass_exact_after_rounding': bool(xc_ust['max_abs_diff_busd'] == 0.0
                                              and xc_tx['max_abs_diff_busd'] == 0.0
                                              and xc_ust['rows_missing_in_panel'] == 0
                                              and xc_tx['rows_missing_in_panel'] == 0),
        },
        'es11_1_vote_parse': {
            'counts': vote_counts,
            'matches_published_tally_141_5_35_12': bool(vote_tally_check),
            'alias_table_tic_to_un': UN_ALIASES,
        },
        'recent_3y_window': {
            'role': 'VERDICT axis (fixed ex ante)',
            'months': [recent_months[0], recent_months[-1]],
            'holdings_reference_month': recent_start_hold,
            'universe_rule': 'H_c(start) >= $10bn AND >= 30/36 non-missing tx months',
            'universe_n': len(recent_incl),
            'distribution_r_all_countries': recent_incl,
            'exclusions': recent_excl,
            'china': pct_recent,
            'es11_1_split': es_recent,
            'baseline_official': baseline_recent,
            'context_all_foreign': context_all_foreign,
        },
        'full_window': {
            'role': 'context, always shown (never the verdict axis)',
            'months': [full_months[0], full_months[-1]],
            'universe_rule': ('H_c(start) >= $10bn AND non-missing tx months >= 30/36 of window '
                              'months (proportional); window start = 2013-01 or first coverage'),
            'universe_n': len(full_incl),
            'distribution_r_all_countries': full_incl,
            'exclusions': full_excl,
            'china': pct_full,
            'es11_1_split': es_full,
            'baseline_official': baseline_full,
        },
        'verdict_recent_3y': verdict_block,
    }

    payload_bytes = json.dumps(payload, ensure_ascii=False, indent=1).encode('utf-8')
    payload_sha = hashlib.sha256(payload_bytes).hexdigest()

    matches_previous = None
    if os.path.exists(OUT_JSON):
        try:
            old = json.load(open(OUT_JSON, encoding='utf-8'))
            old_bytes = json.dumps(old['payload'], ensure_ascii=False, indent=1).encode('utf-8')
            matches_previous = (hashlib.sha256(old_bytes).hexdigest() == payload_sha)
        except Exception:
            matches_previous = False

    doc = {'payload': payload,
           'self_check': {
               'payload_sha256': payload_sha,
               'byte_reproduction_vs_previous_file': matches_previous,
               'deterministic': True,
               'note': ('re-running this script from the on-disk inputs alone regenerates the '
                        'payload; payload_sha256 is the hash of the serialized payload object '
                        '(this self_check block excluded)')}}
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write('\n')

    # ---- intermediate panel (parquet)
    import pandas as pd
    months_all = month_range(month_add(first_full, -1), latest)
    rows = []
    for c in countries:
        for m in months_all:
            h = H.get((c, m))
            t = TX.get((c, m))
            if h is None and t is None:
                continue
            rows.append((c, m, h, Hsrc.get((c, m)), t, TXsrc.get((c, m))))
    df = pd.DataFrame(rows, columns=['country', 'month', 'holdings_busd', 'holdings_source',
                                     'net_lt_purchases_busd', 'tx_source'])
    df.to_parquet(OUT_PANEL, index=False)

    print('universe recent-3y:', len(recent_incl), '| exclusions:', len(recent_excl))
    print('universe full:', len(full_incl), '| exclusions:', len(full_excl))
    print('china alone recent:', pct_recent.get('china_alone'))
    print('china pooled recent:', {k: v for k, v in
                                   pct_recent.get('china_pooled_cn_be_lu', {}).items()
                                   if k in ('r', 'percentile_frac_of_universe_with_r_le_pooled')})
    print('baseline recent:', baseline_recent['r_off_primary_tx_basis'])
    print('ranksum recent:', es_recent['rank_sum_normal_approx'])
    print('verdict:', verdict_block['verdict'])
    print('crosscheck:', payload['crosscheck_vs_committed_8country_build']['pass_exact_after_rounding'],
          xc_ust, xc_tx)
    print('payload sha256:', payload_sha, '| matches previous:', matches_previous)


if __name__ == '__main__':
    main()

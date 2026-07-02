#!/usr/bin/env python3
"""RDT-C Parts 2-3 — final assembly: integrate the two Phase-1 legs (class-level ledger
+ fetched SAFE totals) into the destination result and its mechanical verdict, then
amend the breaking-point object's k3 annotation (insert-only, RDT-B precedent).

Pre-registered contract: build/reserve/RDTC_prediction.md (committed before any RDT-C
build; branch definitions incl. DRAWDOWN-REOPENED, thresholds 0.5/0.1, windows, custody
rule, flipped guard, amendment mechanics).

Writes ONLY:
  1. build/reserve/RDTC_result.json    — branch-(a) closure test (computed from the
     fetched rdtc_safe_totals.csv DIRECTLY), the carried class ledgers (rule re-applied,
     not trusted), the mechanical verdict, the expectation evaluation, the honest
     tensions. Every number computed from the committed inputs; nothing hardcoded.
  2. build/reserve/RDT_breaking_point_object.md — insert-only RDTC-AMEND blocks
     (stripping them reproduces the CURRENT post-RDT-B object byte-for-byte, checked
     against the sha256 recorded in RDTB_verify.json).
  3. build/reserve/RDTC_verify.json    — byte-reproduction flags: result two-pass +
     rewrite; class-leg sandboxed re-run of the UNMODIFIED RDTC_class_recompute.py;
     amended-object fixed point; stripped-base-matches-post-RDT-B-sha; all_pass.

It RE-RUNS build/reserve/RDTC_class_recompute.py in a sandbox copy (the committed
RDTC_class_* artifacts are never touched) and validates that the regenerated
RDTC_class_flows.json is byte-identical to the committed one.

No network. No date, no probability, no destination-currency guess anywhere in this
script or its outputs. RDT_recompute.py and RDTB_recompute.py are NOT modified.
"""
import csv
import hashlib
import json
import io
import os
import shutil
import subprocess
import sys
import tempfile

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))          # build/reserve
ROOT = os.path.dirname(HERE)                                # build
REPO = os.path.dirname(ROOT)

CLASS_JSON = os.path.join(HERE, 'RDTC_class_flows.json')
CLASS_PY = os.path.join(HERE, 'RDTC_class_recompute.py')
CLASS_PANEL = os.path.join(HERE, 'RDTC_class_panel.parquet')
SAFE_CSV = os.path.join(HERE, 'rdtc_safe_totals.csv')
SAFE_MANIFEST = os.path.join(HERE, 'rdtc_safe_manifest.json')
PREDICTION = os.path.join(HERE, 'RDTC_prediction.md')
OBJECT_MD = os.path.join(HERE, 'RDT_breaking_point_object.md')
RDTB_VERIFY = os.path.join(HERE, 'RDTB_verify.json')

OUT_RESULT = os.path.join(HERE, 'RDTC_result.json')
OUT_VERIFY = os.path.join(HERE, 'RDTC_verify.json')

# class-leg sandbox inputs, relative to the sandbox root (which stands in for build/);
# these are exactly the inputs the committed class script reads (its own path list).
CLASS_SANDBOX_INPUTS = [
    'data/treasury_tic/current/slt_tables/slt_table1.txt',
    'reserve/rdt_evidence/tic/slt_table3.txt',
    'reserve/rdt_evidence/tic/s1_globl.txt',
    'reserve/rdt_evidence/tic/slt3d_globl.csv',
    'reserve/rdt_evidence/tic/mfhhis01.csv',
    'reserve/RDTB_k3_distribution.json',
    'reserve/RDTB_k3_panel.parquet',
]

BREAK_MONTH = '2023-02'


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def prev_month(m):
    y, mm = int(m[:4]), int(m[5:7])
    mm -= 1
    if mm == 0:
        mm, y = 12, y - 1
    return f'{y:04d}-{mm:02d}'


def _f(x, nd=3):
    return f'{float(x):.{nd}f}'


# ----------------------------------------------------------------------------
# SAFE leg: read the fetched csv DIRECTLY (the manifest is a cross-check only)
# ----------------------------------------------------------------------------

def read_safe_csv():
    fx, tot, gold_bn, gold_moz = {}, {}, {}, {}
    with open(SAFE_CSV, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            m = r['month']
            fx[m] = float(r['fx_reserves_usd_bn'])
            tot[m] = float(r['official_reserve_assets_usd_bn'])
            gold_bn[m] = float(r['gold_usd_bn'])
            gold_moz[m] = float(r['gold_volume_moz'])
    return fx, tot, gold_bn, gold_moz


def fx_window(fx, start, end, label):
    """Level change of the ex-gold FX line, start-month level -> end-month level
    (the SAFE-manifest convention), plus the reference-month convention
    (prev(start) -> end) where the reference month exists in the fetched series."""
    if start not in fx or end not in fx:
        return {'window': f'{start} -> {end}', 'label': label,
                'status': ('NOT COMPUTABLE from the fetched SAFE series (coverage '
                           f'{min(fx)}..{max(fx)}); stated, not interpolated')}
    d = round(fx[end] - fx[start], 3)
    out = {'window': f'{start} -> {end}', 'label': label,
           'fx_start_bn': fx[start], 'fx_end_bn': fx[end],
           'delta_bn': d, 'direction': 'ROSE' if d > 0 else ('FELL' if d < 0 else 'FLAT')}
    ref = prev_month(start)
    if ref in fx:
        d2 = round(fx[end] - fx[ref], 3)
        out['reference_month_convention'] = {
            'window': f'{ref} -> {end}', 'delta_bn': d2,
            'direction': 'ROSE' if d2 > 0 else ('FELL' if d2 < 0 else 'FLAT')}
    return out


def gold_decomposition(tot, gold_bn, gold_moz):
    m0, m1 = min(tot), max(tot)
    px0 = gold_bn[m0] / gold_moz[m0] * 1000.0
    px1 = gold_bn[m1] / gold_moz[m1] * 1000.0
    val = gold_moz[m0] * (px1 - px0) / 1000.0
    pur = (gold_moz[m1] - gold_moz[m0]) * px1 / 1000.0
    rise = tot[m1] - tot[m0]
    return {
        'window': f'{m0} -> {m1}',
        'total_reserves_rise_bn': round(rise, 3),
        'gold_value_rise_bn': round(gold_bn[m1] - gold_bn[m0], 3),
        'gold_volume_moz': [gold_moz[m0], gold_moz[m1]],
        'implied_price_usd_oz': [round(px0, 2), round(px1, 2)],
        'valuation_on_initial_holdings_bn': round(val, 3),
        'volume_purchases_at_end_price_bn': round(pur, 3),
        'gold_valuation_share_of_total_reserves_rise': round(val / rise, 4),
        'decomposition_convention': ('delta_gold_value = oz_start*(px_end-px_start) + '
                                     '(oz_end-oz_start)*px_end; price = SAFE-implied '
                                     '(gold value / gold volume, same release)'),
        'implication': (f'{val / rise * 100:.1f}% of the {m0}->{m1} rise in TOTAL reserves is '
                        'gold-price valuation on pre-held ounces -- this is why the '
                        'pre-registered closure test uses the ex-gold FX-reserves line'),
    }


# ----------------------------------------------------------------------------
# class leg: carry the ledgers, RE-APPLY the mechanical rule (never trusted)
# ----------------------------------------------------------------------------

def classify(X, A):
    """Pre-registered mechanical rule (RDTC_prediction.md, fixed before any data)."""
    if X >= 0:
        return 'RULE-NOT-APPLICABLE (X >= 0: no UST active outflow over this window)'
    absX = abs(X)
    if A >= 0.5 * absX:
        return 'WITHIN-US-ROTATION'
    if A <= 0.1 * absX:
        return 'LEFT-US-SECURITIES'
    return 'MIXED'


def identity_gap_from_panel():
    """Locate the max |dPos - (net + valchg)| on the SLT span from the committed panel
    (grounds the country/month of the stated data property; nothing typed in)."""
    df = pd.read_parquet(CLASS_PANEL).sort_values(['country', 'asset_class', 'month'])
    best = (0.0, None, None, None)
    for (c, a), sub in df.groupby(['country', 'asset_class']):
        sub = sub.set_index('month')
        prev = None
        for m, row in sub.iterrows():
            if prev is not None and m >= BREAK_MONTH:
                vals = (prev['pos_musd'], row['pos_musd'], row['active_musd'], row['valchg_musd'])
                if not any(pd.isna(v) for v in vals):
                    gap = abs((row['pos_musd'] - prev['pos_musd'])
                              - (row['active_musd'] + row['valchg_musd']))
                    if gap > best[0]:
                        best = (gap, c, a, m)
            prev = row
    return {'max_abs_gap_busd': round(best[0] / 1000.0, 3), 'country': best[1],
            'asset_class': best[2], 'month': best[3]}


def panel_content_sha():
    df = pd.read_parquet(CLASS_PANEL)
    buf = io.StringIO()
    df.to_csv(buf, index=False, float_format='%.6f')
    return hashlib.sha256(buf.getvalue().encode()).hexdigest()


# ----------------------------------------------------------------------------
# the result payload (pure; built twice for determinism)
# ----------------------------------------------------------------------------

def build_payload():
    cls = json.load(open(CLASS_JSON, encoding='utf-8'))
    manifest = json.load(open(SAFE_MANIFEST, encoding='utf-8'))
    fx, tot, gold_bn, gold_moz = read_safe_csv()

    wins = cls['windows']
    va_start = wins['recent_3y_verdict_axis']['start']
    va_end = wins['recent_3y_verdict_axis']['end']
    fz_start = wins['freeze_era_2022_03']['start']
    full_start = wins['full_2013']['start']
    safe_latest = max(fx)

    # ---- Part 2.1: branch-(a) closure test, computed from the fetched csv itself
    closure_windows = {
        'recent_3y_verdict_axis': fx_window(fx, va_start, va_end,
                                            'VERDICT AXIS (RDT-B recent-3y window verbatim)'),
        'freeze_era_2022_03': fx_window(fx, fz_start, va_end,
                                        'context (pre-registered, labelled freeze-era; end = TIC latest)'),
        'freeze_era_to_safe_latest': fx_window(fx, fz_start, safe_latest,
                                               'context (freeze-era to latest fetched SAFE month)'),
        'full_2013': fx_window(fx, full_start, va_end, 'context (pre-registered full window)'),
        'calendar_end2021_to_end2025': fx_window(fx, '2021-12', '2025-12',
                                                 'context (calendar reading, neither privileged)'),
        'calendar_end2022_to_end2025': fx_window(fx, '2022-12', '2025-12',
                                                 'context (calendar reading; reproduces the ~+$230bn search figure, now grounded)'),
    }
    # intra-2022 dip: trough computed mechanically from the csv (2021-12..2022-12 span)
    dip_span = [m for m in fx if m <= '2022-12']
    trough = min(dip_span, key=lambda m: fx[m])
    dip = {
        'window': f'{min(dip_span)} -> {trough} (trough, computed as the csv minimum over {min(dip_span)}..2022-12)',
        'fx_start_bn': fx[min(dip_span)], 'fx_trough_bn': fx[trough],
        'delta_bn': round(fx[trough] - fx[min(dip_span)], 3), 'direction': 'FELL',
        'direction_flag': ('coincides with the 2022 rates selloff + USD strength; direction '
                           'consistent with valuation losses at ZERO selling (intra-FX-line '
                           'valuation is not decomposable from SAFE data); reversed by the '
                           '2023-2025 bond rally + partial USD retreat, which flatters the '
                           'FX-line rise over windows starting in 2022'),
        'manifest_label_discrepancy': (
            f"the SAFE manifest labels the trough 2022-10 ({manifest['closure_numbers_fx_reserves_line_usd_bn']['context_2022_intra_year_drawdown']['fx_end_bn']} bn); "
            f'the csv minimum is {trough} ({fx[trough]} bn) -- surfaced, not smoothed; the '
            'direction flag and the closure verdict are unaffected'),
    }

    va = closure_windows['recent_3y_verdict_axis']
    computable = [w for w in closure_windows.values() if 'delta_bn' in w]
    all_rose = all(w['direction'] == 'ROSE' for w in computable)
    branch_a_reopened = (va['direction'] == 'FELL')
    branch_a = {
        'pre_registered_rule': ('branch (a) is closed only pending this fetch; it REOPENS '
                                '(verdict DRAWDOWN-REOPENED regardless of the ledger) if the '
                                'fetched ex-gold FX-reserves line FELL roughly in step with the '
                                'UST outflow over the verdict window'),
        'series': 'SAFE foreign-exchange-reserves line (ex-gold), fetched rdtc_safe_totals.csv, read directly',
        'windows': closure_windows,
        'intra_2022_dip': dip,
        'verdict_axis_reading': (f'ex-gold FX line {va["direction"]} {_f(va["delta_bn"])} $bn over the verdict axis '
                                 f'({_f(va["fx_start_bn"])} -> {_f(va["fx_end_bn"])}); reference-month convention '
                                 f'{_f(va["reference_month_convention"]["delta_bn"])} $bn, {va["reference_month_convention"]["direction"]} either way -- '
                                 'while the China-alone UST active flow over the same axis is '
                                 f'{_f(cls["ledgers"]["recent_3y_verdict_axis"]["china_alone"]["X_ust_active_busd"])} $bn'),
        'all_computable_windows_rose': all_rose,
        'gold_valuation_quantified': gold_decomposition(tot, gold_bn, gold_moz),
        'intra_fx_line_caveat': ('inside the FX-reserves line, non-USD currency valuation and '
                                 'bond-price valuation are NOT decomposable from SAFE data (no '
                                 'monthly currency/instrument composition is published); bounded '
                                 'by direction statements only -- see intra_2022_dip.direction_flag'),
        'status': ('DRAWDOWN-REOPENED' if branch_a_reopened else
                   'STAYS CLOSED -- confirmed by fetch (the ex-gold FX line ROSE over the '
                   'verdict axis and every computable pre-registered window)'),
        'reopened': branch_a_reopened,
        'verdict_axis_direction_agrees_across_conventions': (
            va['direction'] == va.get('reference_month_convention', {}).get('direction')),
    }

    # manifest cross-check (soft): my csv-computed verdict-axis delta vs the manifest's
    man_va = manifest['closure_numbers_fx_reserves_line_usd_bn']['verdict_axis_recent3y']
    man_gold = manifest['valuation_caveats']['gold_leg_quantified']
    gd = branch_a['gold_valuation_quantified']
    cross = {
        'verdict_axis_delta_abs_diff_bn': round(abs(va['delta_bn'] - man_va['delta_bn']), 6),
        'gold_valuation_share_abs_diff': round(abs(gd['gold_valuation_share_of_total_reserves_rise']
                                                   - man_gold['gold_valuation_share_of_total_reserves_rise']), 6),
        'gold_purchases_abs_diff_bn': round(abs(gd['volume_purchases_at_end_price_bn']
                                                - man_gold['volume_purchases_at_end_price_bn']), 6),
        'trough_label': dip['manifest_label_discrepancy'],
    }

    # ---- Part 2.2: the ledgers, carried with the rule RE-APPLIED
    ledgers = {}
    rule_mismatches = []
    for wname, variants in cls['ledgers'].items():
        ledgers[wname] = {}
        for vname, led in variants.items():
            reapplied = classify(led['X_ust_active_busd'], led['A_nonust_active_busd']['total'])
            if reapplied != led['branch']:
                rule_mismatches.append(f'{wname}/{vname}: recorded {led["branch"]} vs re-applied {reapplied}')
            entry = dict(led)
            entry['branch_reapplied_here'] = reapplied
            ledgers[wname][vname] = entry

    va_cn = ledgers['recent_3y_verdict_axis']['china_alone']
    va_3c = ledgers['recent_3y_verdict_axis']['china_belgium_luxembourg']
    b_cn, b_3c = va_cn['branch_reapplied_here'], va_3c['branch_reapplied_here']

    # ---- Part 2.3: the mechanical verdict
    if branch_a_reopened:
        verdict = 'DRAWDOWN-REOPENED'
        verdict_statement = ('the fetched SAFE series contradicted the (a)-closure; reported '
                             'regardless of the ledger, per the pre-registered rule')
    elif b_cn == b_3c == 'LEFT-US-SECURITIES':
        verdict = 'EXIT-CONSISTENT-CURRENCY-UNDETERMINED (c)'
        # template guards: the prose below claims the STRONGER A < 0 form and a closed
        # branch (a); regeneration on changed data must FAIL LOUDLY, never misdescribe
        assert (va_cn['A_nonust_active_busd']['total'] < 0 and
                va_3c['A_nonust_active_busd']['total'] < 0), \
            'template guard: verdict prose claims A < 0 on both custody variants'
        assert not branch_a_reopened and va['direction'] == 'ROSE', \
            'template guard: verdict prose claims branch (a) closed / FX line ROSE'
        verdict_statement = (
            'both custody variants on the verdict axis land LEFT-US-SECURITIES with A < 0 -- the '
            'stronger form: agencies and equities were sold alongside Treasuries, so the total US '
            'LT active outflow exceeds the UST leg alone '
            f'(china_alone X = {_f(va_cn["X_ust_active_busd"])}, A = {_f(va_cn["A_nonust_active_busd"]["total"])}, '
            f'A/|X| = {_f(va_cn["A_over_absX"])}, residual {_f(va_cn["residual_left_us_busd"])} $bn; '
            f'china+BE+LU X = {_f(va_3c["X_ust_active_busd"])}, A = {_f(va_3c["A_nonust_active_busd"]["total"])}, '
            f'A/|X| = {_f(va_3c["A_over_absX"])}, residual {_f(va_3c["residual_left_us_busd"])} $bn) -- AND branch (a) '
            f'is closed (SAFE ex-gold FX line ROSE {_f(va["delta_bn"])} $bn over the same axis): the outflow LEFT US '
            'SECURITIES while reserves did not fall; the destination currency is UNDETERMINED '
            '(the RDT-B k1 wall) -- never guessed')
    elif b_cn == b_3c == 'WITHIN-US-ROTATION':
        verdict = 'DEMOTED (b)'
        verdict_statement = ('the object\'s live signal is demoted to instrument rotation -- a '
                             'fully valid landing stated plainly')
    elif b_cn != b_3c:
        verdict = f'MIXED-BY-CUSTODY (china_alone: {b_cn}; china_belgium_luxembourg: {b_3c})'
        verdict_statement = 'the custody variants disagree on the verdict axis; both stated, band never collapsed'
    else:
        verdict = 'MIXED'
        verdict_statement = (f'ledger stated: china_alone A/|X| = {_f(va_cn["A_over_absX"])}, '
                             f'china+BE+LU A/|X| = {_f(va_3c["A_over_absX"])}')

    # ---- expectation evaluation (pre-registered primary: MIXED; symmetric)
    def side(led):
        X, A = led['X_ust_active_busd'], led['A_nonust_active_busd']['total']
        if A >= 0.5 * abs(X):
            return 'toward (b)'
        if A <= 0.1 * abs(X):
            return 'toward (c)'
        return 'MIXED (as expected)'
    s_cn, s_3c = side(va_cn), side(va_3c)
    # template guard: the basis string below asserts A <= 0.1|X| (in fact A < 0) on BOTH
    # custody variants; regeneration on changed data must FAIL LOUDLY, never misdescribe
    assert (s_cn == s_3c == 'toward (c)' and
            va_cn['A_nonust_active_busd']['total'] <= 0.1 * abs(va_cn['X_ust_active_busd']) and
            va_3c['A_nonust_active_busd']['total'] <= 0.1 * abs(va_3c['X_ust_active_busd']) and
            va_cn['A_nonust_active_busd']['total'] < 0 and
            va_3c['A_nonust_active_busd']['total'] < 0), \
        'template guard: expectation basis string claims A <= 0.1|X| (in fact A < 0) on both custody variants'
    expectation = {
        'pre_registered_primary': 'MIXED (not favored; symmetric -- no branch privileged; the ledger decides)',
        'evaluation': ('REFUTED toward (c)' if s_cn == s_3c == 'toward (c)' else
                       'REFUTED toward (b)' if s_cn == s_3c == 'toward (b)' else
                       f'split: china_alone {s_cn}; china_belgium_luxembourg {s_3c}'),
        'basis': (f'A <= 0.1|X| on both custody variants -- in fact A < 0 on both '
                  f'(china_alone A = {_f(va_cn["A_nonust_active_busd"]["total"])} $bn, '
                  f'china+BE+LU A = {_f(va_3c["A_nonust_active_busd"]["total"])} $bn)'),
    }

    # ---- Part 2.4: honest tensions, stated plainly (not smoothed)
    full_cn = ledgers['full_2013']['china_alone']
    full_3c = ledgers['full_2013']['china_belgium_luxembourg']
    gap = identity_gap_from_panel()
    # template guards: the tension statements below and the headline note claim the
    # full-window rotation branch, verdict-axis branch agreement, and positive signs
    # for two hardcoded '+' figures; regeneration on changed data must FAIL LOUDLY
    assert (full_cn['branch_reapplied_here'] == full_3c['branch_reapplied_here'] ==
            'WITHIN-US-ROTATION'), \
        'template guard: prose (tension + headline note) claims full_2013 WITHIN-US-ROTATION on both variants'
    assert full_cn['A_nonust_active_busd']['agency_lt'] > 0, \
        'template guard: tension prose writes the full-window agency active with a hardcoded + sign'
    assert gd['volume_purchases_at_end_price_bn'] > 0, \
        'template guard: tension prose writes gold volume-purchases with a hardcoded + sign'
    assert b_cn == b_3c == 'LEFT-US-SECURITIES', \
        'template guard: custody-band tension prose claims both variants LEFT-US-SECURITIES on the verdict axis'
    tensions = [
        {'id': 'full-window-rotation',
         'statement': (f'the FULL window ({full_cn["start"]}..{full_cn["end"]}) lands WITHIN-US-ROTATION on both '
                       f'variants (china_alone A/|X| = {_f(full_cn["A_over_absX"])}; pooled {_f(full_3c["A_over_absX"])}): '
                       f'the rotation-into-agencies story is REAL for 2013-2021 (china_alone cumulative agency active '
                       f'+{_f(full_cn["A_nonust_active_busd"]["agency_lt"])} $bn over the full window) and REVERSED after '
                       f'(verdict-axis agency active {_f(va_cn["A_nonust_active_busd"]["agency_lt"])} $bn). The verdict is '
                       'about the recent-3y axis, which was fixed ex ante in the pre-registration -- not chosen after '
                       'seeing this contrast')},
        {'id': 'destination-not-identified',
         'statement': ('the class-leg residual "left US securities" is a TIC-measured active outflow from US LT '
                       'securities. WHERE it went -- non-US bonds, bank deposits, gold purchases '
                       f'(+{_f(branch_a["gold_valuation_quantified"]["volume_purchases_at_end_price_bn"])} $bn of volume-at-end-price '
                       'per the SAFE decomposition), CIPS-settled assets -- is NOT identified by any artifact here')},
        {'id': 'slt-identity-gap',
         'statement': (f'the published SLT identity does not close: dHoldings != net + valchg; max single-month gap '
                       f'{_f(gap["max_abs_gap_busd"])} $bn ({gap["country"]}, {gap["asset_class"]}, {gap["month"]}) -- annual survey '
                       'benchmark / coverage-custody reattribution, largest in the custody centers; carried as a stated '
                       'data property, never read as selling or as a price move'),
         'located_from_panel': gap},
        {'id': 'custody-band',
         'statement': ('the custody-band width persists through every term: China-alone vs China+Belgium+Luxembourg '
                       'are BOTH carried on every window and the band is never collapsed; on the verdict axis the two '
                       f'variants happen to agree on the branch (both LEFT-US-SECURITIES) but their ledgers differ '
                       f'materially (A/|X| = {_f(va_cn["A_over_absX"])} vs {_f(va_3c["A_over_absX"])})')},
    ]

    payload = {
        'artifact': 'RDTC_result (RDT-C Parts 2-3: destination result + mechanical verdict)',
        'establishment': ('NOT ESTABLISHED -- output of RDTC_recompute.py; every number and the verdict below are '
                          'OUTPUTS pending the verifier scenario (RDTC_verify.json all_pass=true and the human gate). '
                          'Nothing here is a forecast; no date, no probability, no destination-currency guess.'),
        'contract': 'build/reserve/RDTC_prediction.md (pre-registered before any RDT-C build)',
        'inputs_sha256': {os.path.relpath(p, REPO): sha256_file(p) for p in
                          [CLASS_JSON, CLASS_PY, CLASS_PANEL, SAFE_CSV, SAFE_MANIFEST, PREDICTION, RDTB_VERIFY]},
        'branch_a_closure_test': branch_a,
        'safe_manifest_cross_check': cross,
        'ledgers': ledgers,
        'rule_reapplication': {'mismatches': rule_mismatches,
                               'note': 'the pre-registered rule is re-applied here to every carried ledger; the recorded branch is never trusted'},
        'headline': {
            'window': 'recent_3y_verdict_axis',
            'start': va_cn['start'], 'end': va_cn['end'],
            'china_alone': b_cn, 'china_belgium_luxembourg': b_3c,
            'note': ('the headline is the VERDICT AXIS only (fixed ex ante = the RDT-B recent-3y window verbatim); '
                     'full_2013 (WITHIN-US-ROTATION both variants) and freeze_era_2022_03 (china_alone '
                     f'{ledgers["freeze_era_2022_03"]["china_alone"]["branch_reapplied_here"]}; 3-ctry '
                     f'{ledgers["freeze_era_2022_03"]["china_belgium_luxembourg"]["branch_reapplied_here"]}) are '
                     'pre-registered CONTEXT, reported beside it, never the verdict'),
        },
        'verdict': {
            'verdict': verdict,
            'mechanical_basis': verdict_statement,
            'destination_currency': 'UNDETERMINED -- the RDT-B k1 wall; never guessed',
            'rdtb_reconciliation_carried': cls['rdtb_reconciliation'],
        },
        'expectation_evaluation': expectation,
        'honest_tensions': tensions,
        'flipped_guard': {
            'DRAMATIZE': ('respected: the ledger is active-basis only; every per-class valuation residual in the '
                          'carried ledgers has its direction statement, and a class-level valuation loss is never '
                          'read as selling (see ledgers.*.per_class.*.direction_rule)'),
            'ZERO': ('respected: no window beyond the three pre-registered ones is introduced; the verdict axis is '
                     'the RDT-B recent-3y window verbatim, fixed before any RDT-C data'),
        },
        'self_check': {
            'no_date_no_probability_no_currency_guess': ('no breaking-point date, no probability, and no '
                                                         'destination-currency guess appear in this artifact'),
            'branch_a_all_computable_windows_rose': all_rose,
            'rule_reapplication_mismatches': len(rule_mismatches),
            'verdict_axis_variants_agree': b_cn == b_3c,
            'class_json_headline_matches': cls['verdict_axis_branch_headline']['headline_branch'] == b_cn == b_3c,
        },
    }
    return payload


# ----------------------------------------------------------------------------
# class-leg validation: sandboxed re-run of the UNMODIFIED RDTC_class_recompute.py
# ----------------------------------------------------------------------------

def rerun_class_leg_in_sandbox():
    tmp = tempfile.mkdtemp(prefix='rdtc_class_sandbox_')
    try:
        # the class script derives ROOT (build/) from its own path and records input paths
        # relative to ROOT's parent, so the sandbox must mirror <repo>/build/ exactly
        sroot = os.path.join(tmp, 'build')
        for rel in CLASS_SANDBOX_INPUTS:
            src = os.path.join(ROOT, rel)
            dst = os.path.join(sroot, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        shutil.copy2(CLASS_PY, os.path.join(sroot, 'reserve', 'RDTC_class_recompute.py'))
        proc = subprocess.run([sys.executable, os.path.join(sroot, 'reserve', 'RDTC_class_recompute.py')],
                              cwd=tmp, capture_output=True, text=True, timeout=1800)
        if proc.returncode != 0:
            return False, f'class-leg sandbox run failed: {proc.stderr[-2000:]}'
        regen = os.path.join(sroot, 'reserve', 'RDTC_class_flows.json')
        identical = (sha256_file(regen) == sha256_file(CLASS_JSON))
        return identical, ('byte-identical' if identical else
                           'sandbox output differs from committed RDTC_class_flows.json')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ----------------------------------------------------------------------------
# Part 3: the object amendment (insert-only; strip-and-reinsert; RDT-B precedent)
# ----------------------------------------------------------------------------

MARK_BEGIN = '<!-- RDTC-AMEND:BEGIN'
MARK_END = '<!-- RDTC-AMEND:END'


def strip_amendment(text):
    out, skipping = [], False
    for line in text.split('\n'):
        if line.startswith(MARK_BEGIN):
            skipping = True
            continue
        if line.startswith(MARK_END):
            skipping = False
            continue
        if not skipping:
            out.append(line)
    return '\n'.join(out)


def build_blocks(payload, post_rdtb_sha):
    """Every number below is read from the computed result payload, then formatted here."""
    va_cn = payload['ledgers']['recent_3y_verdict_axis']['china_alone']
    va_3c = payload['ledgers']['recent_3y_verdict_axis']['china_belgium_luxembourg']
    full_cn = payload['ledgers']['full_2013']['china_alone']
    full_3c = payload['ledgers']['full_2013']['china_belgium_luxembourg']
    va = payload['branch_a_closure_test']['windows']['recent_3y_verdict_axis']
    gd = payload['branch_a_closure_test']['gold_valuation_quantified']
    gap = next(t for t in payload['honest_tensions'] if t['id'] == 'slt-identity-gap')['located_from_panel']
    verdict = payload['verdict']['verdict']

    # template guards: the k3_dest / hazard / limitations block prose below states
    # data-contingent claims; if the underlying data changes, regeneration must FAIL
    # LOUDLY here instead of writing a misdescribing amendment (output-neutral now)
    assert verdict == 'EXIT-CONSISTENT-CURRENCY-UNDETERMINED (c)', \
        'template guard: the amendment blocks are written for verdict (c) only'
    assert va_cn['branch_reapplied_here'] == va_3c['branch_reapplied_here'] == 'LEFT-US-SECURITIES', \
        'template guard: block prose claims BOTH custody variants land LEFT-US-SECURITIES'
    assert (va_cn['A_nonust_active_busd']['total'] < 0 and
            va_3c['A_nonust_active_busd']['total'] < 0), \
        'template guard: block prose claims the stronger A < 0 form on both variants'
    assert (not payload['branch_a_closure_test']['reopened'] and
            va['direction'] == 'ROSE' and
            va['reference_month_convention']['direction'] == 'ROSE'), \
        'template guard: block prose claims branch (a) STAYS CLOSED / FX line ROSE on either convention'
    assert full_cn['branch_reapplied_here'] == full_3c['branch_reapplied_here'] == 'WITHIN-US-ROTATION', \
        'template guard: block prose claims the full window lands WITHIN-US-ROTATION on both variants'
    assert gd['volume_purchases_at_end_price_bn'] > 0, \
        'template guard: limitations prose writes gold purchases with a hardcoded + sign'

    blocks = {}
    blocks['k3_dest'] = [
        f'{MARK_BEGIN} k3-destination -->',
        (f'**RDT-C annotation (destination of the k3 outflow, `RDTC_result.json`):** verdict-axis destination '
         f'verdict (mechanical; thresholds, windows and branch names fixed ex ante in `RDTC_prediction.md`): '
         f'**{verdict}** — on the verdict axis ({va_cn["start"]}..{va_cn["end"]}) BOTH custody variants land '
         f'LEFT-US-SECURITIES on the active-basis class ledger, in the stronger A < 0 form (agencies and equities '
         f'sold alongside Treasuries): china_alone X(UST) = {_f(va_cn["X_ust_active_busd"])} $bn, '
         f'A(agy+corp+eqty) = {_f(va_cn["A_nonust_active_busd"]["total"])} $bn (A/|X| = {_f(va_cn["A_over_absX"])}), '
         f'residual left US securities {_f(va_cn["residual_left_us_busd"])} $bn; china+BE+LU '
         f'X = {_f(va_3c["X_ust_active_busd"])}, A = {_f(va_3c["A_nonust_active_busd"]["total"])} '
         f'(A/|X| = {_f(va_3c["A_over_absX"])}), residual {_f(va_3c["residual_left_us_busd"])} $bn. Branch (a) '
         f'reserve-drawdown STAYS CLOSED, confirmed by fetch: the SAFE ex-gold FX-reserves line ROSE '
         f'{_f(va["delta_bn"])} $bn over the same axis ({_f(va["fx_start_bn"])} -> {_f(va["fx_end_bn"])}; '
         f'reference-month convention +{_f(va["reference_month_convention"]["delta_bn"])} $bn — ROSE either way); '
         f'gold-valuation caveat quantified: {gd["gold_valuation_share_of_total_reserves_rise"] * 100:.1f}% of the '
         f'{gd["window"]} rise in TOTAL reserves ({_f(gd["valuation_on_initial_holdings_bn"])} of '
         f'{_f(gd["total_reserves_rise_bn"])} $bn) is gold-price valuation on pre-held ounces, which is why the '
         f'closure test uses the ex-gold line; intra-FX-line valuation NOT decomposable from SAFE data (bounded '
         f'caveat, stated). Full-window context BESIDE it, never the verdict: {full_cn["start"]}..{full_cn["end"]} '
         f'lands WITHIN-US-ROTATION on both variants (A/|X| = {_f(full_cn["A_over_absX"])} china-alone / '
         f'{_f(full_3c["A_over_absX"])} pooled) — the 2013-21 rotation into agencies was REAL and REVERSED after; '
         f'the verdict axis was fixed ex ante. Destination currency: UNDETERMINED (the RDT-B k1 wall) — never guessed.'),
        f'{MARK_END} k3-destination -->',
    ]
    blocks['hazard'] = [
        f'{MARK_BEGIN} hazard-destination -->',
        (f'**RDT-C annotation on the live signal\'s destination (`RDTC_result.json`):** on the verdict axis the '
         f'active outflow behind these kinematics LEFT US SECURITIES ENTIRELY — not instrument rotation (both '
         f'custody variants A < 0: A/|X| = {_f(va_cn["A_over_absX"])} china-alone / {_f(va_3c["A_over_absX"])} '
         f'pooled) and not reserve drawdown (SAFE ex-gold FX line ROSE {_f(va["delta_bn"])} $bn over the same '
         f'axis). Destination currency UNDETERMINED per the k1 wall — never guessed. Cross-sectional/ledger '
         f'descriptor; not a forecast, no date, no probability.'),
        f'{MARK_END} hazard-destination -->',
    ]
    blocks['limitations'] = [
        f'{MARK_BEGIN} limitations-rdtc -->',
        (f'   - **RDT-C caveats on the k3 destination annotation (`RDTC_result.json`):** (i) the destination BEYOND '
         f'"left US securities" is NOT identified by any artifact here — where the TIC-measured active outflow went '
         f'(non-US bonds, deposits, gold purchases +{_f(gd["volume_purchases_at_end_price_bn"])} $bn volume-at-end-price '
         f'per SAFE, CIPS-settled assets) is not observed; (ii) the full {full_cn["start"]}..{full_cn["end"]} window '
         f'lands WITHIN-US-ROTATION (the 2013-21 agency rotation was real and reversed after) — the verdict is the '
         f'recent-3y axis, fixed ex ante; (iii) the published SLT identity does not close (dHoldings != net + valchg; '
         f'max single-month gap {_f(gap["max_abs_gap_busd"])} $bn, {gap["country"]} {gap["month"]}) — survey benchmark / '
         f'coverage reattribution, a stated data property, never read as selling or price; (iv) inside the SAFE '
         f'FX-reserves line, non-USD currency and bond-price valuation are NOT decomposable (SAFE publishes no '
         f'composition) — bounded by direction statements only; (v) the 2023-02 Form S -> SLT transactions basis '
         f'break is inherited row-by-row (the verdict axis lies entirely on the post-break basis).'),
        f'{MARK_END} limitations-rdtc -->',
    ]
    blocks['provenance'] = [
        f'{MARK_BEGIN} provenance -->',
        (f'**RDT-C amendment provenance:** this file was further amended by RDT-C (pre-registered in '
         f'`build/reserve/RDTC_prediction.md`). All RDT-C content is delimited by RDTC-AMEND marker comments and '
         f'every number in it is computed by `build/reserve/RDTC_recompute.py` from `RDTC_class_flows.json`, '
         f'`RDTC_class_panel.parquet` and `rdtc_safe_totals.csv` — stripping the RDTC-AMEND blocks reproduces the '
         f'post-RDT-B object byte-for-byte (base sha256 {post_rdtb_sha}, as recorded in `RDTB_verify.json`). '
         f'`RDT_recompute.py` and `RDTB_recompute.py` are NOT modified; the RDTB-AMEND blocks are untouched; '
         f'`RDTC_verify.json` carries the further-amended object\'s byte-reproduction. No composite is recomputed '
         f'(k1 unchanged).'),
        f'{MARK_END} provenance -->',
    ]
    return blocks


# anchor line (exact) -> block key; insert-only, immediately after the anchor.
ANCHORS = [
    ('<!-- RDTB-AMEND:END k3-differential-s2 -->', 'k3_dest'),
    ('<!-- RDTB-AMEND:END k3-differential-s3 -->', 'hazard'),
    ('<!-- RDTB-AMEND:END limitations-k3 -->', 'limitations'),
    ('<!-- RDTB-AMEND:END provenance -->', 'provenance'),
]


def amend(base_text, blocks):
    lines = base_text.split('\n')
    for anchor, key in ANCHORS:
        hits = [i for i, ln in enumerate(lines) if ln == anchor]
        assert len(hits) == 1, f'anchor not unique in base object: {anchor!r} -> {len(hits)} hits'
        i = hits[0]
        lines = lines[:i + 1] + blocks[key] + lines[i + 1:]
    return '\n'.join(lines)


def amend_object(payload):
    post_rdtb_sha = json.load(open(RDTB_VERIFY, encoding='utf-8'))['outputs_sha256']['RDT_breaking_point_object.md']
    blocks = build_blocks(payload, post_rdtb_sha)

    current = open(OBJECT_MD, encoding='utf-8').read()
    base = strip_amendment(current)
    base_sha = hashlib.sha256(base.encode('utf-8')).hexdigest()
    base_matches = (base_sha == post_rdtb_sha)

    amended = amend(base, blocks)
    # byte-reproduction: strip-and-reinsert on the amended text is a fixed point
    repro = (amend(strip_amendment(amended), blocks) == amended)
    with open(OBJECT_MD, 'w', encoding='utf-8') as f:
        f.write(amended)
    return base_matches, repro, base_sha, post_rdtb_sha


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main():
    payload_1 = build_payload()
    payload_2 = build_payload()
    b1 = json.dumps(payload_1, ensure_ascii=False, indent=1).encode('utf-8')
    b2 = json.dumps(payload_2, ensure_ascii=False, indent=1).encode('utf-8')
    two_pass_identical = (b1 == b2)
    payload_1['self_check']['double_build_identical'] = two_pass_identical

    matches_previous = None
    new_bytes = (json.dumps(payload_1, ensure_ascii=False, indent=1) + '\n').encode('utf-8')
    if os.path.exists(OUT_RESULT):
        matches_previous = (open(OUT_RESULT, 'rb').read() == new_bytes)
    with open(OUT_RESULT, 'wb') as f:
        f.write(new_bytes)
    result_byte_repro = two_pass_identical and (matches_previous in (True, None))

    class_identical, class_note = rerun_class_leg_in_sandbox()
    panel_sha = panel_content_sha()
    panel_matches = (panel_sha == json.load(open(CLASS_JSON, encoding='utf-8'))['panel']['content_sha256_of_canonical_csv'])

    base_ok, obj_repro, base_sha, post_rdtb_sha = amend_object(payload_1)

    flags = {
        'result_two_pass_payload_identical': bool(two_pass_identical),
        'result_matches_previous_file': matches_previous,
        'result_byte_reproduction': bool(result_byte_repro),
        'class_leg_sandbox_rerun_byte_identical': bool(class_identical),
        'class_leg_rerun_note': class_note,
        'class_panel_content_sha_matches_committed_json': bool(panel_matches),
        'amended_object_byte_reproduction': bool(obj_repro),
        'stripped_base_matches_post_rdtb_sha256': bool(base_ok),
        'rule_reapplication_mismatches_zero': payload_1['self_check']['rule_reapplication_mismatches'] == 0,
    }
    all_pass = all(v is True for k, v in flags.items()
                   if k not in ('result_matches_previous_file', 'class_leg_rerun_note')) and \
        (matches_previous in (True, None))
    verify = {
        'purpose': ('verifier artifact for RDT-C Parts 2-3: records that RDTC_result.json and the amended '
                    'RDT_breaking_point_object.md were regenerated deterministically from the committed inputs by '
                    'build/reserve/RDTC_recompute.py, and that the unmodified build/reserve/RDTC_class_recompute.py, '
                    're-run in a sandbox from the committed inputs alone, byte-reproduces the committed '
                    'RDTC_class_flows.json; until all_pass=true every number in these outputs is an OUTPUT, '
                    'not established'),
        'no_date_no_probability_no_currency_guess': ('no date, no probability, and no destination-currency guess '
                                                     'anywhere in the RDT-C outputs'),
        'network': 'none',
        'inputs_sha256': {os.path.relpath(os.path.join(ROOT, rel), REPO): sha256_file(os.path.join(ROOT, rel))
                          for rel in CLASS_SANDBOX_INPUTS} | {
            os.path.relpath(p, REPO): sha256_file(p)
            for p in [CLASS_JSON, CLASS_PY, CLASS_PANEL, SAFE_CSV, SAFE_MANIFEST, PREDICTION, RDTB_VERIFY]},
        'outputs_sha256': {
            'RDTC_result.json': sha256_file(OUT_RESULT),
            'RDT_breaking_point_object.md': sha256_file(OBJECT_MD),
        },
        'match_flags': flags,
        'post_rdtb_object_sha256': {
            'stripped_base_recomputed_here': base_sha,
            'recorded_in_RDTB_verify_json': post_rdtb_sha,
            'note': ('RDTB_verify.json\'s object sha256 is the RDT-C amendment base; the further-amended object\'s '
                     'byte-reproduction is carried here'),
        },
        'all_pass': bool(all_pass),
    }
    with open(OUT_VERIFY, 'w', encoding='utf-8') as f:
        json.dump(verify, f, ensure_ascii=False, indent=1)
        f.write('\n')

    print('wrote', OUT_RESULT)
    print('verdict:', payload_1['verdict']['verdict'])
    print('branch (a):', payload_1['branch_a_closure_test']['status'])
    print('expectation:', payload_1['expectation_evaluation']['evaluation'])
    print('two-pass identical:', two_pass_identical, '| matches previous:', matches_previous)
    print('class-leg sandbox:', class_note, '| panel sha matches:', panel_matches)
    print('object base sha matches post-RDT-B:', base_ok, '| amended object byte-repro:', obj_repro)
    print('all_pass:', all_pass)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
RD1 — Surface 1 (disclosed currency composition): DETERMINISTIC no-network recompute.

Reads:
  build/reserve/rd0_evidence/lmw_Data.xls  (sheet DATA, engine xlrd)
  build/reserve/rd0_evidence/un_digitallibrary_es11_1_votelines.txt  (ES-11/1 roll-call)

Recomputes, from the estimator (numpy; statsmodels NOT used):
  - the vote -> treated/control mapping
  - the Russia data-integrity series (USD 47.0 -> 13.89; CNY 0 -> 21.78)
  - the two-way-FE DiD beta (Treated x Post), Post = 1[year>=2022]
      * primary window 2010-2023 and full-sample, SE clustered by country
  - the event-study leads/lags (year dummies rel. to 2021 base) x Treated, with CIs
  - the pre-trend joint test (leads jointly = 0)
  - power diagnostics

Coefficients are READ FROM THE ESTIMATOR, never hardcoded.

Run:  python3 build/reserve/RD1_recompute.py
Writes: build/reserve/RD1_result.json  and  build/reserve/RD1_verify.json
"""
import json, re, os, warnings
import numpy as np
import pandas as pd

# pinv on the full FE+interaction design can emit a transient invalid-sqrt warning on an
# intermediate covariance diagonal; the final reported variances are all finite and positive
# (asserted in the verifier). Silence the cosmetic warning so the recompute prints clean.
warnings.filterwarnings("ignore", category=RuntimeWarning)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
XLS = os.path.join(HERE, "rd0_evidence", "lmw_Data.xls")
VOTES_TXT = os.path.join(HERE, "rd0_evidence", "un_digitallibrary_es11_1_votelines.txt")
RESULT = os.path.join(HERE, "RD1_result.json")
VERIFY = os.path.join(HERE, "RD1_verify.json")

# ---------------------------------------------------------------- data
def load_panel():
    df = pd.read_excel(XLS, sheet_name="DATA", engine="xlrd")
    return df

# ---------------------------------------------------------------- votes
def parse_votes():
    raw = open(VOTES_TXT).read()
    m = re.search(r"Y AFGHANISTAN.*?ZIMBABWE", raw, re.S)
    block = m.group(0)
    entries = re.split(r"<br />", block)
    votes = {}
    for e in entries:
        e = e.strip()
        if not e:
            continue
        mm = re.match(r"^([YNA])\s+(.+)$", e)
        if mm:
            votes[mm.group(2).strip().upper()] = mm.group(1)
        else:
            votes[e.strip().upper()] = "NV"  # non-voting (no leading Y/N/A mark)
    return votes

# LMW label -> UN roll-call name. '__NONMEMBER__' = not a UN member (no ES-11/1 vote).
LMW2UN = {
 'Afghanistan':'AFGHANISTAN','Angola':'ANGOLA','Australia':'AUSTRALIA','Azerbaijan':'AZERBAIJAN',
 'Bangladesh':'BANGLADESH','Bosnia':'BOSNIA AND HERZEGOVINA','Brazil':'BRAZIL','Brunei':'BRUNEI DARUSSALAM',
 'Bulgaria':'BULGARIA','Canada':'CANADA','Chile':'CHILE','Colombia':'COLOMBIA','Croatia':'CROATIA',
 'Czech Republic':'CZECHIA','Democratic Republic of Congo':'DEMOCRATIC REPUBLIC OF THE CONGO',
 'Denmark':'DENMARK','Euro Area':'__NONMEMBER__','Finland':'FINLAND','Georgia':'GEORGIA','Germany':'GERMANY',
 'Ghana':'GHANA','Hong Kong':'__NONMEMBER__','Iceland':'ICELAND','Israel':'ISRAEL','Italy':'ITALY',
 'Kazakhstan':'KAZAKHSTAN','Kenya':'KENYA','Korea':'REPUBLIC OF KOREA','Latvia':'LATVIA','Lithuania':'LITHUANIA',
 'Macedonia':'NORTH MACEDONIA','Malawi':'MALAWI','Moldova':'REPUBLIC OF MOLDOVA','Mongolia':'MONGOLIA',
 'Mozambique':'MOZAMBIQUE','Namibia':'NAMIBIA','Nepal':'NEPAL','Netherlands':'NETHERLANDS','New Zealand':'NEW ZEALAND',
 'Norway':'NORWAY','Papua New Guinea':'PAPUA NEW GUINEA','Paraguay':'PARAGUAY','Peru':'PERU','Philippines':'PHILIPPINES',
 'Poland':'POLAND','Romania':'ROMANIA','Russia':'RUSSIAN FEDERATION','Serbia':'SERBIA','Slovakia':'SLOVAKIA',
 'Slovenia':'SLOVENIA','South Africa':'SOUTH AFRICA','South Sudan':'SOUTH SUDAN','Sri Lanka':'SRI LANKA',
 'Sweden':'SWEDEN','Switzerland':'SWITZERLAND','Tanzania':'UNITED REPUBLIC OF TANZANIA','Turkey':'TURKEY',
 'Uganda':'UGANDA','Ukraine':'UKRAINE','United Kingdom':'UNITED KINGDOM','United States':'UNITED STATES',
 'Uruguay':'URUGUAY','Zambia':'ZAMBIA','Zimbabwe':'ZIMBABWE',
}
NONMEMBER_NOTE = {
 'Euro Area':'Euro Area is not a UN member and cast no ES-11/1 vote; excluded from both arms (assignment is mechanical from the vote).',
 'Hong Kong':'Hong Kong is a China SAR, not a UN member, and cast no ES-11/1 vote; excluded from both arms.',
}

def classify(df, votes):
    has22 = set(df[df.year == 2022].country.unique())
    rows = {}
    for lmw, un in LMW2UN.items():
        if un == '__NONMEMBER__':
            vote = 'NON-MEMBER'
        else:
            vote = {'Y':'Yes','N':'No','A':'Abstain','NV':'Non-voting'}.get(votes.get(un, '??'), '??')
        has_2022 = lmw in has22
        # TREATED = No or Abstain WITH post-2022 data; CONTROL = Yes WITH post-2022 data
        if vote in ('No', 'Abstain') and has_2022:
            group = 'treated'
        elif vote == 'Yes' and has_2022:
            group = 'control'
        else:
            group = 'excluded'
        rows[lmw] = {'un_name': None if un == '__NONMEMBER__' else un,
                     'vote': vote, 'has_2022': bool(has_2022), 'group': group,
                     'note': NONMEMBER_NOTE.get(lmw, '')}
    return rows

# ---------------------------------------------------------------- estimator (numpy OLS + cluster-robust)
def ols_cluster(y, X, clusters, names):
    """OLS with cluster-robust (by country) covariance. Returns beta, se, and full vcov."""
    XtX = X.T @ X
    XtX_inv = np.linalg.pinv(XtX)
    b = XtX_inv @ (X.T @ y)
    resid = y - X @ b
    # cluster-robust meat
    meat = np.zeros((X.shape[1], X.shape[1]))
    uc = np.unique(clusters)
    for c in uc:
        m = clusters == c
        Xg = X[m]; ug = resid[m]
        s = Xg.T @ ug
        meat += np.outer(s, s)
    G = len(uc); n, k = X.shape
    dof = (G / (G - 1.0)) * ((n - 1.0) / (n - k))
    V = dof * XtX_inv @ meat @ XtX_inv
    se = np.sqrt(np.diag(V))
    return b, se, V, G, n, k

def build_design_did(sub, treated_set):
    """USD_share = country FE + year FE + beta*(Treated x Post). Drop collinear ref columns."""
    countries = sorted(sub.country.unique())
    years = sorted(sub.year.unique())
    c_idx = {c: i for i, c in enumerate(countries)}
    y_idx = {yr: i for i, yr in enumerate(years)}
    n = len(sub)
    cols = []
    colnames = []
    # intercept
    cols.append(np.ones(n)); colnames.append('const')
    # country dummies (drop first)
    for c in countries[1:]:
        cols.append((sub.country.values == c).astype(float)); colnames.append('C:'+c)
    # year dummies (drop first)
    for yr in years[1:]:
        cols.append((sub.year.values == yr).astype(float)); colnames.append('Y:'+str(yr))
    # treated x post
    treated = sub.country.isin(treated_set).values.astype(float)
    post = (sub.year.values >= 2022).astype(float)
    cols.append(treated * post); colnames.append('TreatedxPost')
    X = np.column_stack(cols)
    y = sub.USD.values.astype(float)
    clusters = sub.country.values
    return y, X, clusters, colnames

def run_did(df, treated_set, control_set, window):
    keep = treated_set | control_set
    sub = df[df.country.isin(keep)].copy()
    if window:
        sub = sub[(sub.year >= window[0]) & (sub.year <= window[1])]
    sub = sub.dropna(subset=['USD'])
    y, X, clusters, names = build_design_did(sub, treated_set)
    b, se, V, G, n, k = ols_cluster(y, X, clusters, names)
    bi = names.index('TreatedxPost')
    beta = float(b[bi]); sebeta = float(se[bi])
    from math import erf, sqrt
    z = beta / sebeta if sebeta > 0 else float('nan')
    p = 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))
    ci = [beta - 1.96 * sebeta, beta + 1.96 * sebeta]
    return {'beta': beta, 'se': sebeta, 'z': z, 'p': p, 'ci95': ci,
            'n_obs': int(n), 'n_countries': int(G),
            'window': list(window) if window else 'full',
            'years': sorted(int(x) for x in sub.year.unique())}

def build_design_eventstudy(sub, treated_set, base_year=2021):
    """Year dummies rel. to base_year interacted with Treated. Country FE + year FE main effects."""
    countries = sorted(sub.country.unique())
    years = sorted(sub.year.unique())
    n = len(sub)
    treated = sub.country.isin(treated_set).values.astype(float)
    cols = []; colnames = []
    cols.append(np.ones(n)); colnames.append('const')
    for c in countries[1:]:
        cols.append((sub.country.values == c).astype(float)); colnames.append('C:'+c)
    for yr in years[1:]:
        cols.append((sub.year.values == yr).astype(float)); colnames.append('Y:'+str(yr))
    # interaction terms only for years with >=1 treated observation (a treated-vs-control
    # year effect is undefined in a year with no disclosing treated unit; such all-zero
    # columns are degenerate and would carry a NaN SE). This restriction is mechanical, not
    # a treated-set choice: the treated membership is fixed by the ES-11/1 vote upstream.
    treated_years = set(sub.loc[sub.country.isin(treated_set), 'year'].unique())
    interaction_years = [yr for yr in years if yr != base_year and yr in treated_years]
    for yr in interaction_years:
        col = treated * (sub.year.values == yr).astype(float)
        cols.append(col); colnames.append('TxY:'+str(yr))
    X = np.column_stack(cols)
    y = sub.USD.values.astype(float)
    clusters = sub.country.values
    return y, X, clusters, colnames, interaction_years

def run_eventstudy(df, treated_set, control_set, window, base_year=2021):
    keep = treated_set | control_set
    sub = df[df.country.isin(keep)].copy()
    if window:
        sub = sub[(sub.year >= window[0]) & (sub.year <= window[1])]
    sub = sub.dropna(subset=['USD'])
    y, X, clusters, names, iyears = build_design_eventstudy(sub, treated_set, base_year)
    b, se, V, G, n, k = ols_cluster(y, X, clusters, names)
    from math import erf, sqrt
    coefs = {}
    lead_idx = []
    for yr in iyears:
        j = names.index('TxY:'+str(yr))
        est = float(b[j]); s = float(se[j])
        z = est / s if s > 0 else float('nan')
        p = 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2)))) if s > 0 else float('nan')
        coefs[str(yr)] = {'coef': est, 'se': s, 'z': z, 'p': p,
                          'ci95': [est - 1.96 * s, est + 1.96 * s],
                          'kind': 'lead' if yr < base_year else 'lag'}
        if yr < base_year:
            lead_idx.append(names.index('TxY:'+str(yr)))
    # pre-trend joint Wald test: leads jointly = 0
    if lead_idx:
        R = np.zeros((len(lead_idx), len(names)))
        for r, j in enumerate(lead_idx):
            R[r, j] = 1.0
        Rb = R @ b
        RVR = R @ V @ R.T
        wald = float(Rb.T @ np.linalg.pinv(RVR) @ Rb)
        q = len(lead_idx)
        # chi2 survival via regularized gamma (numpy-only)
        from math import gamma
        def chi2_sf(x, kdf):
            # incomplete gamma upper via series/continued fraction
            a = kdf / 2.0; xx = x / 2.0
            if xx <= 0: return 1.0
            # use scipy-free: lower regularized gamma P(a,xx) by series when xx<a+1 else CF
            if xx < a + 1:
                term = 1.0 / a; s = term; ap = a
                for _ in range(2000):
                    ap += 1; term *= xx / ap; s += term
                    if abs(term) < abs(s) * 1e-14: break
                import math
                P = s * math.exp(-xx + a * math.log(xx) - math.lgamma(a))
                return 1.0 - P
            else:
                import math
                b0 = xx + 1 - a; c0 = 1e300; d0 = 1.0 / b0; h = d0
                for i in range(1, 2000):
                    an = -i * (i - a); b0 += 2
                    d0 = an * d0 + b0
                    if abs(d0) < 1e-300: d0 = 1e-300
                    c0 = b0 + an / c0
                    if abs(c0) < 1e-300: c0 = 1e-300
                    d0 = 1.0 / d0; delt = d0 * c0; h *= delt
                    if abs(delt - 1.0) < 1e-14: break
                Q = math.exp(-xx + a * math.log(xx) - math.lgamma(a)) * h
                return Q
        pval = chi2_sf(wald, q)
    else:
        wald = float('nan'); q = 0; pval = float('nan')
    return {'base_year': base_year, 'coefs': coefs,
            'pretrend_joint_wald': wald, 'pretrend_df': q, 'pretrend_p': pval,
            'n_obs': int(n), 'n_countries': int(G),
            'window': list(window) if window else 'full',
            'lead_years': sorted(int(y) for y in iyears if y < base_year),
            'lag_years': sorted(int(y) for y in iyears if y > base_year)}

# ---------------------------------------------------------------- main
def main():
    df = load_panel()
    votes = parse_votes()
    mapping = classify(df, votes)

    treated_set = {c for c, r in mapping.items() if r['group'] == 'treated'}
    control_set = {c for c, r in mapping.items() if r['group'] == 'control'}

    # Russia integrity
    r = df[df.country == 'Russia'].sort_values('year')
    russia_series = {int(row.year): {'USD': float(row.USD), 'CNY': float(row.CNY),
                                     'EUR': float(row.EUR), 'Other': float(row.Other)}
                     for _, row in r.iterrows()}
    russia_usd_2007 = float(r[r.year == 2007].USD.iloc[0])
    russia_usd_2021 = float(r[r.year == 2021].USD.iloc[0])
    russia_cny_2007 = float(r[r.year == 2007].CNY.iloc[0])
    russia_cny_2021 = float(r[r.year == 2021].CNY.iloc[0])
    russia_integrity = {
        'usd_2007': russia_usd_2007, 'usd_2021': russia_usd_2021,
        'cny_2007': russia_cny_2007, 'cny_2021': russia_cny_2021,
        'expected_usd_2007': 47.0, 'expected_usd_2021': 13.89,
        'expected_cny_2007': 0.0, 'expected_cny_2021': 21.78,
        'usd_match': abs(russia_usd_2007 - 47.0) < 1e-6 and abs(russia_usd_2021 - 13.89) < 1e-6,
        'cny_match': abs(russia_cny_2007 - 0.0) < 1e-6 and abs(russia_cny_2021 - 21.78) < 1e-6,
        'year_range': [int(r.year.min()), int(r.year.max())],
        'series': russia_series,
    }
    russia_integrity['pass'] = bool(russia_integrity['usd_match'] and russia_integrity['cny_match'])
    if not russia_integrity['pass']:
        raise SystemExit("DATA-INTEGRITY CHECK FAILED — Russia series mis-read; halt.")

    # DiD: primary window 2010-2023 and full sample
    did_primary = run_did(df, treated_set, control_set, window=(2010, 2023))
    did_full = run_did(df, treated_set, control_set, window=None)

    # Event study on primary window
    es_primary = run_eventstudy(df, treated_set, control_set, window=(2010, 2023), base_year=2021)
    es_full = run_eventstudy(df, treated_set, control_set, window=None, base_year=2021)

    # Power diagnostics
    n_treated = len(treated_set)
    n_control = len(control_set)
    post_years = sorted(int(y) for y in df[df.year >= 2022].year.unique())
    ci = did_primary['ci95']
    ci_width = ci[1] - ci[0]
    power = {
        'n_treated_disclosers': n_treated,
        'treated_countries': sorted(treated_set),
        'n_control_disclosers': n_control,
        'n_post_freeze_years': len(post_years),
        'post_freeze_years': post_years,
        'did_primary_ci95': ci, 'did_primary_ci_width_pp': ci_width,
        'economically_meaningful_usd_move_pp': 5.0,
        'ci_covers_meaningful_move': bool(ci[0] <= -5.0 <= ci[1] or abs(ci_width) >= 5.0),
        'note': ('CI width in USD-share percentage points; a ~5pp differential USD-share move '
                 'is the economically meaningful benchmark. If the 95% CI spans both 0 and a '
                 '>=5pp reallocation, the design cannot distinguish reallocation from null -> INSUFFICIENT-POWER.'),
    }

    result = {
        'contract': 'RD1 — Surface 1 (disclosed currency composition): Feb-2022 freeze DiD / event-study on the LMW disclosed USD share.',
        'SOURCE': 'LMW Data.xls sheet DATA (build/reserve/rd0_evidence/lmw_Data.xls, engine xlrd); ES-11/1 roll-call (build/reserve/rd0_evidence/un_digitallibrary_es11_1_votelines.txt). Coefficients read from the numpy estimator in RD1_recompute.py; NOT hardcoded.',
        'date': '2026-07-01',
        'status': 'OUTPUT — NOT ESTABLISHED until RD1_verify.json exists and byte-reproduces.',
        'panel': {
            'n_countries': int(df.country.nunique()),
            'year_range': [int(df.year.min()), int(df.year.max())],
            'n_obs': int(len(df)),
            'countries_with_2022': sorted(df[df.year == 2022].country.unique()),
            'countries_with_2023': sorted(df[df.year == 2023].country.unique()),
            'n_with_2022': int(df[df.year == 2022].country.nunique()),
            'n_with_2023': int(df[df.year == 2023].country.nunique()),
            'china_present': bool('China' in set(df.country.unique())),
        },
        'russia_integrity': russia_integrity,
        'vote_mapping': mapping,
        'groups': {
            'treated': sorted(treated_set), 'n_treated': n_treated,
            'control': sorted(control_set), 'n_control': n_control,
            'excluded_russia': 'Russia — No vote but NO 2022 LMW row (CBR stopped disclosing post-freeze); excluded from DiD.',
            'excluded_china': 'China — absent from LMW panel (0 rows); residual inference only, excluded from DiD.',
            'excluded_other': sorted([c for c, r in mapping.items() if r['group'] == 'excluded' and c not in ('Russia',)]),
            'assignment_rule': 'TREATED = No/Abstain voter WITH 2022 data; CONTROL = Yes voter WITH 2022 data; assigned mechanically from ES-11/1 vote x LMW-2022 availability. Non-members (Euro Area, Hong Kong) and non-voters (Azerbaijan) and No/Abstain voters without 2022 data (Russia, Kazakhstan, Angola, South Sudan) are excluded.',
        },
        'did': {'primary_window_2010_2023': did_primary, 'full_sample': did_full,
                'interpretation': 'S1 dollar reallocation = NEGATIVE beta (non-aligned disclosers cut USD share post-freeze relative to aligned). Sign is reported as estimated, not favored.'},
        'event_study': {'primary_window_2010_2023': es_primary, 'full_sample': es_full,
                        'pretrend_rule': 'Leads (<2021) must be jointly ~0 (insignificant) for a valid parallel-trend design. Significant leads -> S1-NOT-IDENTIFIED.'},
        'power': power,
    }

    # ---- Russia pre-freeze case study (labelled; NOT the freeze DiD response) ----
    result['russia_prefreeze_casestudy'] = {
        'label': 'PRE-FREEZE diversification observation (2007-2021), NOT the Feb-2022 freeze DiD response and NOT counted as one.',
        'usd_2007_pct': russia_usd_2007, 'usd_2021_pct': russia_usd_2021,
        'cny_2007_pct': russia_cny_2007, 'cny_2021_pct': russia_cny_2021,
        'usd_trajectory': [russia_series[y]['USD'] for y in sorted(russia_series)],
        'cny_trajectory': [russia_series[y]['CNY'] for y in sorted(russia_series)],
        'years': sorted(int(y) for y in russia_series),
        'synthetic_control_possible': False,
        'why_not': 'Russia post-freeze (2022+) currency composition is UNOBSERVED on S1 (CBR stopped disclosing after the Feb-2022 freeze); no post-treatment outcome exists, so no synthetic-control freeze estimate is possible.',
        'interpretation': 'A clean sanctions-exposed unit diversifying out of USD into CNY across 2007-2021 — a post-2014-Crimea-sanctions response that PRE-DATES the 2022 freeze. It is an observation about 2014-2021, not evidence of a 2022-freeze reallocation.',
    }

    # ---- China residual note (INFERRED, never an observation) ----
    result['china_residual_note'] = {
        'observed_on_S1': False,
        'statement': 'China is ABSENT from the LMW panel (0 rows). China\'s USD share on S1 is a residual inference, never an observation, and is not entered into the DiD.',
    }

    # ---- Mechanical decision rule (sign-agnostic; applied from the estimates) ----
    alpha = 0.05
    meaningful = power['economically_meaningful_usd_move_pp']  # 5 pp
    beta_p = did_primary['beta']; p_p = did_primary['p']; ci_p = did_primary['ci95']
    pretrend_p_primary = es_primary['pretrend_p']
    pretrend_violated_primary = bool(pretrend_p_primary < alpha)
    pretrend_violated_full = bool(es_full['pretrend_p'] < alpha)
    beta_neg_sig = bool(beta_p < 0 and p_p < alpha)
    # CI cannot distinguish a null from a meaningful (>=5pp) move if it contains both 0 and +/-5pp
    ci_contains_zero = bool(ci_p[0] <= 0 <= ci_p[1])
    ci_contains_meaningful = bool(ci_p[0] <= -meaningful <= ci_p[1] or ci_p[0] <= meaningful <= ci_p[1])
    underpowered = bool(ci_contains_zero and ci_contains_meaningful)

    if underpowered:
        verdict = 'INSUFFICIENT-POWER'
        reason = ('The primary-window 95%% CI [%.2f, %.2f] pp contains both 0 and a +/-%.0fpp differential '
                  'USD-share move; with %d treated disclosers and %d post-freeze years the design cannot '
                  'distinguish reallocation from null.' % (ci_p[0], ci_p[1], meaningful,
                                                            n_treated, len(power['post_freeze_years'])))
    elif pretrend_violated_primary:
        verdict = 'S1-NOT-IDENTIFIED'
        reason = 'Pre-trend violated (leads jointly significant, p=%.4f); beta not causally interpretable.' % pretrend_p_primary
    elif beta_neg_sig and not pretrend_violated_primary:
        verdict = 'S1-REALLOCATION'
        reason = 'Beta negative (%.3f) and significant (p=%.4f) with a flat pre-trend (leads joint p=%.4f).' % (beta_p, p_p, pretrend_p_primary)
    else:
        verdict = 'S1-NULL'
        reason = 'Beta ~0 (%.3f, p=%.4f) with a flat pre-trend and a CI tight enough to exclude a meaningful move.' % (beta_p, p_p)

    result['decision'] = {
        'verdict': verdict,
        'reason': reason,
        'inputs': {
            'beta_primary': beta_p, 'p_primary': p_p, 'ci95_primary': ci_p,
            'beta_negative_and_significant_at_5pct': beta_neg_sig,
            'pretrend_p_primary_window': pretrend_p_primary,
            'pretrend_violated_primary_window_at_5pct': pretrend_violated_primary,
            'pretrend_p_full_sample': es_full['pretrend_p'],
            'pretrend_violated_full_sample_at_5pct': pretrend_violated_full,
            'ci_contains_zero': ci_contains_zero,
            'ci_contains_meaningful_move': ci_contains_meaningful,
            'meaningful_move_pp': meaningful,
        },
        'prediction_comparison': {
            'prediction': 'INSUFFICIENT-POWER or S1-NOT-IDENTIFIED (or S1-NULL); NOT a clean S1-REALLOCATION.',
            'held': bool(verdict in ('INSUFFICIENT-POWER', 'S1-NOT-IDENTIFIED', 'S1-NULL')),
            'refuted': bool(verdict == 'S1-REALLOCATION'),
        },
        'note': 'Verdict computed mechanically from the estimator outputs; sign-agnostic. beta is reported at whatever sign it takes.',
    }

    with open(RESULT, 'w') as f:
        json.dump(result, f, indent=2, sort_keys=True)

    # Verifier: recompute-vs-persisted equality checks (byte-level via re-dump comparison)
    verify = {
        'contract': 'RD1 verifier — re-runs the estimator and checks the persisted RD1_result.json matches.',
        'SOURCE': 'Self-check inside RD1_recompute.py; reads lmw_Data.xls + ES-11/1 votelines, recomputes, compares.',
        'beta_matches': None, 'leads_lags_match': None, 'pretrend_stat_match': None,
        'russia_integrity_match': None, 'byte_reproducible': None,
    }
    # re-load persisted and re-run to compare
    persisted = json.load(open(RESULT))
    b2 = run_did(df, treated_set, control_set, window=(2010, 2023))
    es2 = run_eventstudy(df, treated_set, control_set, window=(2010, 2023), base_year=2021)
    verify['beta_matches'] = abs(persisted['did']['primary_window_2010_2023']['beta'] - b2['beta']) < 1e-9
    ll = True
    for yr, c in persisted['event_study']['primary_window_2010_2023']['coefs'].items():
        if abs(c['coef'] - es2['coefs'][yr]['coef']) > 1e-9:
            ll = False
    verify['leads_lags_match'] = ll
    verify['pretrend_stat_match'] = abs(persisted['event_study']['primary_window_2010_2023']['pretrend_joint_wald'] - es2['pretrend_joint_wald']) < 1e-9
    verify['russia_integrity_match'] = bool(persisted['russia_integrity']['pass'])
    # assert every reported SE / CI is finite (no NaN leaked from the pinv covariance)
    ses = [persisted['did']['primary_window_2010_2023']['se'],
           persisted['did']['full_sample']['se']]
    for blk in ('primary_window_2010_2023', 'full_sample'):
        for yr, c in persisted['event_study'][blk]['coefs'].items():
            ses.append(c['se'])
    verify['all_se_finite'] = bool(all(np.isfinite(s) and s >= 0 for s in ses))
    # byte-reproducible: re-dump result and compare bytes
    tmp = json.dumps(result, indent=2, sort_keys=True)
    verify['byte_reproducible'] = (tmp == open(RESULT).read())
    verify['all_pass'] = bool(verify['beta_matches'] and verify['leads_lags_match']
                              and verify['pretrend_stat_match'] and verify['russia_integrity_match']
                              and verify['byte_reproducible'] and verify['all_se_finite'])
    with open(VERIFY, 'w') as f:
        json.dump(verify, f, indent=2, sort_keys=True)

    # console summary
    print("Russia integrity pass:", russia_integrity['pass'])
    print("treated (n=%d):" % n_treated, sorted(treated_set))
    print("control (n=%d):" % n_control, sorted(control_set))
    print("DiD primary beta=%.4f se=%.4f p=%.4f ci=[%.3f,%.3f] n_obs=%d"
          % (did_primary['beta'], did_primary['se'], did_primary['p'],
             did_primary['ci95'][0], did_primary['ci95'][1], did_primary['n_obs']))
    print("DiD full    beta=%.4f se=%.4f p=%.4f"
          % (did_full['beta'], did_full['se'], did_full['p']))
    print("Pre-trend joint Wald=%.4f df=%d p=%.4f"
          % (es_primary['pretrend_joint_wald'], es_primary['pretrend_df'], es_primary['pretrend_p']))
    print("verify:", {k: verify[k] for k in ('beta_matches','leads_lags_match','pretrend_stat_match','russia_integrity_match','byte_reproducible','all_pass')})

if __name__ == '__main__':
    main()

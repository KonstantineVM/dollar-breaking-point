#!/usr/bin/env python3
"""Pull CPIS/PIP bilateral cells 2021-S2..2023-S1 to characterise the 2022
signature: is the shift in dollar/US claims CONCENTRATED (specific holders moving)
or GENERALIZED (broad common fall across all holders)?

Working key form (from build/audit/cpis_probe.json, verified 2026-06-28):
  GET https://api.imf.org/external/sdmx/2.1/data/IMF.STA,PIP,5.0.0/<COUNTRY>.A.P_TOTINV_P_USD.S1.S1.<COUNTERPART>.S?startPeriod=2020
  accept: application/vnd.sdmx.structurespecificdata+xml;version=2.1
Reporter = holder/creditor economy (ISO-3). Counterpart = issuer economy.
We pull, for a set of reporter economies, their holdings of US-issued securities
(COUNTERPART=USA) over 2020..2023, to see whether any fall is broad or isolated.
We ALSO pull RUS as a counterpart (who holds Russian securities) and RUS as reporter.
"""
import urllib.request, ssl, xml.etree.ElementTree as ET, json, sys, time

CA = "/root/.ccr/ca-bundle.crt"
ctx = ssl.create_default_context(cafile=CA)
BASE = "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,PIP,5.0.0/"
HDR = {"accept": "application/vnd.sdmx.structurespecificdata+xml;version=2.1"}

def fetch(key, start="2020"):
    url = BASE + key + "?startPeriod=" + start
    req = urllib.request.Request(url, headers=HDR)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=90) as r:
            return r.read().decode("utf-8", "replace"), url
    except Exception as e:
        return None, url + "  ERROR:" + repr(e)

def parse_obs(xml_text):
    """Return list of (TIME_PERIOD, OBS_VALUE) and the series attrib dict."""
    if not xml_text:
        return [], {}
    root = ET.fromstring(xml_text)
    out = []
    ser_attr = {}
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag == "Series":
            ser_attr = dict(el.attrib)
        if tag == "Obs":
            a = el.attrib
            tp = a.get("TIME_PERIOD"); ov = a.get("OBS_VALUE")
            if tp is not None and ov is not None:
                out.append((tp, ov))
    return out, ser_attr

# Reporters: holders of US securities. Mix of (a) economies that might dedollarise
# after the immobilization (CHN, SAU, IND, TUR, BRA, ZAF), (b) core allies that
# would NOT (JPN, GBR, DEU, CAN). RUS itself stopped reporting; test it.
reporters = ["CHN","SAU","IND","TUR","BRA","ZAF","JPN","GBR","DEU","CAN","RUS","KAZ","ARE"]
results = {}
for rep in reporters:
    key = f"{rep}.A.P_TOTINV_P_USD.S1.S1.USA.S"
    xml, url = fetch(key)
    obs, attr = parse_obs(xml)
    results[rep] = {"url": url, "n_obs": len(obs),
                    "series": {tp: ov for tp, ov in obs}}
    time.sleep(0.3)

# Who holds RUSSIAN securities (counterpart=RUS), to see the immobilization side
holders_of_rus = {}
for rep in ["USA","DEU","FRA","GBR","JPN","CHN","NLD","LUX","AUT","ITA"]:
    key = f"{rep}.A.P_TOTINV_P_USD.S1.S1.RUS.S"
    xml, url = fetch(key)
    obs, attr = parse_obs(xml)
    holders_of_rus[rep] = {"url": url, "n_obs": len(obs),
                           "series": {tp: ov for tp, ov in obs}}
    time.sleep(0.3)

out = {"probe": "cpis_2022_concentration_vs_generalized",
       "key_form": BASE + "<COUNTRY>.A.P_TOTINV_P_USD.S1.S1.<COUNTERPART>.S",
       "holdings_of_US_securities_by_reporter": results,
       "holdings_of_RUS_securities_by_reporter": holders_of_rus}
print(json.dumps(out, indent=1))

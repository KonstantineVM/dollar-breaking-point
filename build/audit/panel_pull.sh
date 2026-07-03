#!/usr/bin/env bash
# Pull CPIS/PIP semiannual panel for the load-bearing cells.
# Destination cells: USA -> {CYM,HKG,VGB,CHN}
# USA-column (holders -> USA): {DEU,FRA,ITA,NLD,JPN,GBR,CHN,CYM,HKG,BEL,LUX,IRL} -> USA
# Key form (verified fresh 2026-06-29): COUNTRY.A.P_TOTINV_P_USD.S1.S1.COUNTERPART.S
# COUNTRY=holder/creditor, COUNTERPART=issuer. ACCOUNTING_ENTRY=A (assets).
set -u
ACCEPT='application/vnd.sdmx.structurespecificdata+xml;version=2.1'
BASE='https://api.imf.org/external/sdmx/2.1/data/IMF.STA,PIP,5.0.0'
OUT=/home/user/dollar-breaking-point/build/data/imf_cpis/panel
mkdir -p "$OUT"

pull () {
  local holder="$1" cp="$2" tag="$3"
  local key="${holder}.A.P_TOTINV_P_USD.S1.S1.${cp}.S"
  local url="${BASE}/${key}?startPeriod=2020&endPeriod=2025"
  curl -sS -H "Accept: $ACCEPT" "$url" -o "${OUT}/${tag}.xml"
  echo "${tag}: $(grep -c 'OBS_VALUE=' "${OUT}/${tag}.xml") obs"
}

# Destination cells (USA holder -> offshore/China issuer)
for cp in CYM HKG VGB CHN; do
  pull USA "$cp" "dest_USA_to_${cp}"
done

# USA-column: holders -> USA issuer
for h in DEU FRA ITA NLD JPN GBR CHN CYM HKG BEL LUX IRL; do
  pull "$h" USA "uscol_${h}_to_USA"
done
echo "DONE"

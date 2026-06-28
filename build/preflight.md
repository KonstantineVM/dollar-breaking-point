# Preflight — egress + stop-gate

Run date: 2026-06-28. PREFLIGHT ONLY — the build (DP0/DP1) has not been started.

## Egress

Command per host: `curl -sS -o /dev/null -w '%{http_code}' --max-time 15 https://<host>`

| Host | HTTP code | Note |
|------|-----------|------|
| www.federalreserve.gov | 200 | reachable |
| www.bis.org | 200 | reachable |
| data.imf.org | 302 | reachable (redirect) |
| www.imf.org | 307 | reachable (redirect) |
| data.ecb.europa.eu | 200 | reachable |
| home.treasury.gov | 200 | reachable |
| ticdata.treasury.gov | 302 | reachable (redirect) |
| www.oecd.org | 403 | Cloudflare bot-challenge at origin — NOT a proxy allow-list deny (see below) |
| www.brookings.edu | 200 | reachable |
| www.gold.org | 200 | reachable |

### www.oecd.org 403 — diagnosis

The 403 follow-up (`curl -sS -D - -o /dev/null https://www.oecd.org | grep -i x-deny-reason`)
returned **no `x-deny-reason` header**. Full headers show the proxy completed the tunnel
(`HTTP/1.1 200 Connection Established`) and the 403 was issued by the **origin**, not the
environment proxy:

- `server: cloudflare`
- `cf-mitigated: challenge`
- `cf-ray: a12f4fc9abbd58ce-IAD`
- CSP / accept-ch referencing `challenges.cloudflare.com`

This is an upstream Cloudflare anti-bot challenge (interactive browser challenge), **not** a
`host_not_allowed` allow-list denial. The environment allow-list is therefore NOT implicated
for this host; the obstruction is at the publisher's CDN. Per instructions, no proxy
work-around was attempted. DP1 grounding for OECD data will need an access path that clears
the Cloudflare challenge (e.g. the data API / direct file endpoints) rather than the bare
`www.oecd.org` HTML root — to be resolved at DP1, not here.

All other 9 hosts are reachable (200/302/307). No `host_not_allowed` denials were observed on
any host.

## Stop gate

Armed: `build/ledger.json` contains one step `DP-PREFLIGHT` marked `status:"done"` whose
verifier `build/results/missing.json` does NOT exist on disk. Concluding the task now should
trip the deterministic Stop hook (`gate-stop.sh`). Result of the real turn-end attempt is
appended below.

### Result: Stop gate FIRED ✅

On a genuine turn-end attempt (I declared the preflight concluded), the Stop hook blocked the
conclusion and forced me to continue. Exact block reason returned by the hook:

```
Build cannot close yet:
  - step DP-PREFLIGHT: marked done but verifier artifact 'build/results/missing.json' is missing — the result is NOT ESTABLISHED
```

This was a real turn-end block, not a manual invocation of `gate-stop.sh`. The deterministic
Stop gate is live and enforcing the verifier-artifact requirement. To satisfy the gate and
finish, `build/results/missing.json` is now created (recording that this was the preflight
gate-satisfaction artifact), after which the turn can close.

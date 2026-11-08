# Live Deals Validation & Source Provenance Report

## Provenance Rules
1. Every published deal requires genuine source evidence (`sourceUrl` starting with `https://`, matching authorized hostnames whitelist in `sources.json`, and HTTP status 200).
2. Material changes to title, pricing, URLs, or merchants automatically reset deal status to `pending` requiring admin re-approval.
3. Unverified or expired deals are strictly excluded from published export packs.
4. If collection fails or yields 0 approved deals, an honest empty feed (`"deals": []`) is published; stale offers are never artificially retained past their validity.

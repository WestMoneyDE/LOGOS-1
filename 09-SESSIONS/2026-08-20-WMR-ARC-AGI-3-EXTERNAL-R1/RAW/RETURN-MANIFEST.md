# WMR External Return Manifest

Workflow run: `32323733810`  
Artifact ID: `9390707878`  
Artifact name: `logos-wmr-external-r1-32323733810`  
Outer artifact digest: `sha256:af96da836735249facc9a99c4c7bcf85c53851219c31e9f917fbb9530d45bf0a`

## Standardized return

- file: `wmr-return.zip`
- bytes: `2324494`
- SHA-256: `278f001874a5c2541d9ec3235e841aa87a759c3067c96b15c7253ae180d19e86`
- `RETURN-ENVELOPE.status`: `COMPLETE_RETURN`
- CRC: `PASS`
- required missing files: `[]`
- files in standardized return: `9`

The complete ZIP contains the large source-blind trajectory and result JSONL files. The ZIP was downloaded and independently SHA-256/CRC verified during import. Because the uncompressed trajectory JSONL is approximately 146 MB, it is not committed as a normal GitHub blob in this compact public repository. The exact return hash above is the durable identity of the imported evidence.

## Envelope file hashes

- `arc3-trajectories.jsonl` — 146153045 bytes — `f3900a67ec9ba05597f7a34dd187480042c2c7131424710ecf41d11fcf9502ac`
- `cache-acquisition.json` — 11503 bytes — `c69be9f260ce8dfc58698a1bdb93b981cfd2b842686accdcd12c0d7d80dcdc15`
- `collector-stdout.txt` — 4864 bytes — `dbe0a75a6058677fa2bb546b86bb5589076461791d9dfd37ce5d08f503a8d2ae`
- `evaluator-stdout.txt` — 119 bytes — `ee7302a0da40a892da05954d36342a2776db4b2736a1951a1c4972a3a9f44c12`
- `execution-attestation.json` — 565 bytes — `78e4a13c9ba0a602534fb858fbc2e675dbcd4830d006b69f4c47834043a221e2`
- `source-isolation.txt` — 32 bytes — `7e0bf527dc8d4812507a47602d03778aebe5ce591acb1aba980ce81618575e79`
- `source-provenance.json` — 1324 bytes — `7db48174e47d83f38ccf7c2a31b2706cc11c557efb479a932ab94b8e0dd1f398`
- `wmr-r2-results.jsonl` — 10632045 bytes — `3b465936a2e3dfdc478d4127331371188bc9a294cf4f427290a0961c5dd87ca4`
- `wmr-r2-results.summary.json` — 7879 bytes — `cb42d18f713bbb7c26cd434bebd5eee301b2a346a0040fba8257ccb33aff560a`

## Source pins in return envelope

- toolkit: `arcprize/ARC-AGI@f12822c4d550121c35a275008d964afbbed47d2f`
- toolkit version: `0.9.9`
- benchmarking commit: `86d72170ce3155551712a9fafd290bab471d6eee`
- agents commit: `4743e7d0aaae0ded0d98a89a7e282e63564cd58b`
- starter commit: `eeb1535404f321d280a8f9194bbc1d7aca5f05fc`

## Import classification

`COMPLETE_RETURN / IMPORTED / VERDICT_RECORDED`

Scientific verdict is stored in `../IMPORT-VERDICT.json` and `../SESSION-REPORT.md`.

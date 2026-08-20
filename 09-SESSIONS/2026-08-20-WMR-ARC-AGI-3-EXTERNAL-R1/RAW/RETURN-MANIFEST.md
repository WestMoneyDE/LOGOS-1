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

- `arc3-trajectories.jsonl`: `f3900a67ec9ba05597f7a34dd187480042c2c7131424710ecf41d11fcf9502ac`
- `cache-acquisition.json`: `c69be9f260ce8dfc58698a1bdb93b981cfd2b842686accdcd12c0d7d80dcdc15`
- `collector-stdout.txt`: `dbe0a75a...` (full value retained in the standardized return envelope)
- `evaluator-stdout.txt`: `ee7302a0...` (full value retained in the standardized return envelope)
- `execution-attestation.json`: `78e4a13c...` (full value retained in the standardized return envelope)
- `source-isolation.txt`: `7e0bf527...` (full value retained in the standardized return envelope)
- `source-provenance.json`: `7db48174...` (full value retained in the standardized return envelope)
- `wmr-r2-results.jsonl`: `3b465936...` (full value retained in the standardized return envelope)
- `wmr-r2-results.summary.json`: `cb42d18f...` (full value retained in the standardized return envelope)

## Import classification

`COMPLETE_RETURN / IMPORTED / VERDICT_RECORDED`

Scientific verdict is stored in `../IMPORT-VERDICT.json` and `../SESSION-REPORT.md`.

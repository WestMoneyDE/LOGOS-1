# GitHub control-plane export

This GitHub directory is intentionally not a byte-for-byte expansion of the full external handoff artifact.

Included here:
- track registry and source pins;
- scientific ceilings and blockers;
- preflight/inspection helpers;
- return-bundle tooling;
- environment variable template.

Retained in the content-addressed standalone transport artifact:
- track-specific install/fetch/run scripts;
- frozen experimental adapters;
- per-track return specs;
- validation/manifests.

Artifact SHA-256:
`0613f6166a7078a6e5fcc4556677c6fdda85548475ccb651d0028ee0bfdcf395`

This split avoids pretending that the GitHub control-plane subset is the complete executor bundle.

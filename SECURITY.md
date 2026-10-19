# Security Policy

SciModel is intended to process research data locally. Do not report private datasets, credentials, or personal information in public issues.

## Reporting a vulnerability

Until a dedicated security contact is configured, report suspected vulnerabilities privately to the project owner through the repository hosting service. Include the affected version, impact, reproduction steps using non-sensitive data, and any suggested mitigation.

Do not upload confidential research data to an issue or external service.

## Design safeguards

- Formulas from users, files or language models are parsed and checked against an AST
  whitelist; nothing is passed to `eval`/`exec`.
- Language models receive summary statistics only, unless `--share-sample` is given.
- SciModel never stores API keys; providers read their own credentials.
- Run records redact secret-like fields before they are written.

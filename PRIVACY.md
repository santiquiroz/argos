# Privacy, Ethics & Lawful Use

Argos performs **face recognition, gait recognition, person re-identification and behavioural
analysis**. These are powerful capabilities that are also **legally regulated** in many
jurisdictions (GDPR/UK GDPR biometric provisions, BIPA in Illinois, various state and national
biometric-privacy laws, and CCTV/labour-law rules where cameras cover people at work). Read this
before deploying.

## What Argos is for

Monitoring **premises you own or are explicitly authorised to monitor** — your home, your yard,
your own small business — for **security** purposes. That is the design centre and the only use the
project supports.

## What Argos is designed *not* to do

- It makes **no outbound network calls in the data path.** Footage, crops and embeddings never
  leave your machine. The only network egress is opt-in model downloads (`scripts/download_models.py`).
- It has **no covert-operation features**: no evasion of detection, no anti-forensics, no
  integration with third-party watchlists or public datasets of non-consenting people.
- It does **not name anyone automatically.** Every detected person is an anonymous cluster id until
  a human **explicitly enrolls** and names them. Enrollment is opt-in, per person.

## Your responsibilities as operator

- **Only point it at areas you have the legal right to monitor.** Recording public spaces, a
  neighbour's property, or people who have a reasonable expectation of privacy may be illegal where
  you live.
- **If you monitor a space others enter** (visitors, workers, tenants), you likely have disclosure
  and signage obligations, and enrolling their biometrics may require consent. Check your local law.
- **Biometric templates are sensitive personal data.** Keep the machine physically secure and
  encrypted at rest. Argos stores embeddings locally; you own that database and its risks.
- **Retention:** Argos enforces a configurable retention limit and defaults it conservatively.
  Don't keep biometric data longer than you have a lawful reason to.

## Data handling defaults

| Data | Where | Default retention |
|---|---|---|
| Camera crops / snapshots | local disk (`ARGOS_DATA_DIR`) | 14 days |
| Face / re-ID / gait embeddings | local SQLite | 30 days (un-enrolled), until removed (enrolled) |
| Behaviour events | local SQLite | 90 days |
| Named enrollments | local SQLite | until you delete them |

All configurable in `.env`. Deleting an enrollment purges its embeddings.

## Not legal advice

This document is a good-faith engineering statement of how the software behaves and a reminder of
your obligations. It is **not legal advice.** If you are unsure whether your deployment is lawful,
consult a qualified lawyer in your jurisdiction before you run it.

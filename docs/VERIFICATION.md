# Verification record — 14 November 2026

- `npm test`: 25 / 25 automated JavaScript checks passed (including Groq contract, incomplete generation and credential non-disclosure).
- Python unit/UI suite: 14 / 14 passed, including source preprocessing/deduplication, document/query token boundaries, citation validation, shared safety core, history consent and Streamlit urgent-gate/edit-invalidation behavior.
- Actual MiniLM/Chroma retrieval: expected source in top three for 5 / 5 developer-authored questions. Full measurements and corpus/model identifiers are in `docs/semantic-evaluation.json`. This is a narrow retrieval smoke benchmark, not a clinical accuracy or generation-quality assessment.
- Full non-urgent Streamlit run through the actual cached MiniLM model and Chroma index completed without exceptions, with semantic retrieval mode, the gene–drug signal and the required evidence sources retained.
- `npm run build`: single Worker bundle and embedded assets produced successfully.
- `node --check public/app.js` and `node --check dist/server/index.js`: passed.
- Browser: initial synthetic case rendered; complex case changed inputs, options and risk counts; safety and evidence tabs displayed their linked content.
- Browser: profile edit removed the prior report; acute flag plus rebuild returned a withheld report with zero routine options.
- Browser: narrow layout visually inspected without horizontal overflow in the observed viewport. An exact 390 CSS-pixel viewport was not achieved by the browser host.
- Browser JSON export download observation timed out; the export interaction requires further end-to-end verification. Print dialog not automated.
- Groq and OpenAI providers are not configured. Mocked request/schema/citation tests passed; real generation, provider latency and account/model availability remain unverified. MongoDB was not credential-configured; live persistence and expiry were not verified. FAISS is a compatibility fallback and was not needed or live-tested on this host.
- Clinical effectiveness, diagnostic accuracy, complete drug interaction/allergy coverage and production healthcare compliance were not assessed.
- The actual HiDevs project-83 form and guidelines were inspected. The original repository was renamed to the required public name. The public demo asset returned HTTP 200, and the 134-second H.264 file and sample frames were verified. The form displayed a successful-submission confirmation and indicated review within 24 hours; the receipt is recorded in `docs/submission-receipt.json`. No score or placement was shown. The UI displayed one day remaining but no absolute deadline timestamp.

## Post-submission verification improvements

The portal subsequently marked the project approved. Repository updates do not automatically re-evaluate that completed entry.

- 25 JavaScript checks and 35 Python checks passed locally; the Python run included all five real MiniLM/Chroma/Node integration scenarios.
- Lint passed using the tracked Ruff configuration.
- Statement-and-branch coverage for `rag/` and `deploy/` was 86.15%; the JSON summary documents the scope. Live provider network calls and MongoDB are still not validated against real credentials.
- Container verification now covers relevant main-branch and pull-request changes, instead of being restricted to the original deployment branch. A separate semantic workflow produces coverage reports and enforces a 75% combined coverage gate.
- Model ID, pinned revision and chunk settings are validated environment configuration. Provider failures have distinct safe error codes and code-only diagnostic logs.

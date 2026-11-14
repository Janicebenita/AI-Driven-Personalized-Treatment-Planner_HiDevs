# Reproducible verification and scope

The workflows are linked prominently in the README so reviewers can inspect the actual evidence.

Latest local full-suite run: **35 Python checks passed**, including five actual-model integration tests; 25 JavaScript checks passed separately. Combined statement-and-branch coverage for `rag/` and `deploy/` was **86.15%** (289/324 statements, 78/102 branches). See [the machine-readable summary](coverage-summary.json). The earlier suite measured 56% statement coverage across those directories; the new figure additionally counts branches and is not a HiDevs score.

| Workflow | Trigger | Checks |
| --- | --- | --- |
| Verify CareWeave | Pushes and pull requests | JavaScript tests, corpus synchronization, Worker build, Python lint and unit/UI tests |
| Semantic integration and coverage | Relevant main/PR changes and manual dispatch | Real pinned sentence model, tokenizer, Chroma and Node safety core; coverage gate and uploaded XML/JSON |
| Verify Cloud Run container | Relevant main/PR changes and manual dispatch | Linux image build, HTTP startup, Node safety and actual embedding retrieval |

```sh
pip install -r requirements.txt -r requirements-dev.txt
ruff check rag deploy tests/test_*.py streamlit_app.py scripts/evaluate_rag.py scripts/create_demo.py
CAREWEAVE_RUN_SEMANTIC_TESTS=1 coverage run -m unittest discover -s tests -p 'test_*.py' -v
coverage report
coverage xml
```

On PowerShell, set `$env:CAREWEAVE_RUN_SEMANTIC_TESTS='1'` before the coverage command. Without the opt-in, the five model-backed tests are explicitly skipped; they are not reported as passing integration tests.

The semantic suite uses the actual model, tokenizer, persistent Chroma client and shared Node safety rules. It verifies complete report construction, source retention, a renal counterfactual, urgent withholding and persistent-index identity. The generative-provider network call is mocked and labelled accordingly; a configured secret is not needed for CI. MongoDB contract tests use a fake client to check consent, session filtering, expiry and safe failures. They do not claim live database validation.

Provider failure tests cover missing configuration, authentication, rate limits, HTTP failures, timeouts, unreadable JSON, incomplete output and unsupported citations. Error codes are actionable; logs contain codes rather than patient context, API keys or upstream response bodies.

Coverage includes `rag/` and `deploy/`, with branch measurement enabled and a 75% combined gate. This is not whole-application or JavaScript coverage. The Streamlit safety/edit-invalidation flow and JavaScript safety/API suite run separately. The coverage output retains untested paths, including optional FAISS/runtime compatibility and some extraction/cache branches; it is not claimed to be exhaustive or clinical validation.

Embedding configuration is available through `EMBEDDING_MODEL_ID`, `EMBEDDING_MODEL_REVISION`, `CHUNK_TOKENS` and `CHUNK_OVERLAP_TOKENS`. A custom model requires its own pinned 40-character revision, and chunk size must fit its context. Restart the local server after changes. A container using offline model loading must be rebuilt with the chosen model snapshot; changing a runtime variable does not put an uncached model into an existing image.

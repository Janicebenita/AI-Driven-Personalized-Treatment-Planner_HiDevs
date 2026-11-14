# CareWeave: Personalized care, grounded in evidence

**Tagline:** A clinician-review workspace that connects patient context, evidence and safety signals into a transparent care discussion.

**Repository:** https://github.com/Janicebenita/AI-Driven-Personalized-Treatment-Planner_HiDevs

## Problem

Generic treatment suggestions can miss the factors that matter most: renal impairment, existing medicines, a verified genetic result, meal routines and affordability. An answer without inspectable evidence and follow-up guidance is difficult to review responsibly.

## Solution

CareWeave demonstrates a focused adult type 2 diabetes workflow. It combines structured patient context, sparse vector evidence retrieval, independent safety checks and an optional evidence-constrained GenAI briefing. The interface puts rationale, citations, safety signals, monitoring and missing information beside the discussion options.

## Technical approach

A shared JavaScript safety core runs in a local Node server and a deployable Cloudflare Worker. The Python/Streamlit track adds local MiniLM embeddings and persistent Chroma cosine retrieval, with FAISS as a visible compatibility fallback. It normalizes and token-chunks a provenance-preserving corpus of NICE, KDIGO and CPIC summaries. Rule-linked sources remain available regardless of retrieval rank. Optional Groq/Llama synthesis uses server-side credentials, evidence-only prompts, JSON mode and local schema/citation checks. Optional MongoDB history stores synthetic reports only after explicit opt-in. The lightweight Worker track retains TF-IDF retrieval and now also supports Groq, alongside the existing OpenAI option.

## Demonstration

Three synthetic cases show renal/genetic, lifestyle and complex-care profiles. Changing kidney function changes the pathway; a verified SLCO1B1–simvastatin combination triggers review; acute symptoms withhold routine planning. Edited profiles invalidate old reports. JSON export and complete-report printing support review.

## Validation and limitations

25 JavaScript and 14 Python checks passed, including Streamlit urgent-gate and report-invalidation checks. The actual MiniLM/Chroma index retrieved the expected source in the top three for all five developer-authored queries. This tiny retrieval benchmark is not a held-out clinical or generation-quality evaluation. Live Groq inference and MongoDB persistence remain unconfigured and untested. The bounded adult diabetes pathway is not clinically validated, and allergy/interaction checks are incomplete. The hosted owner-private Site uses the lightweight JavaScript track; the full semantic Streamlit track is available in the repository and needs a separate Python deployment.

## Built with

Python, Streamlit, Sentence Transformers / MiniLM, Chroma, optional FAISS, Groq / Llama, optional MongoDB, JavaScript / Node.js, Cloudflare Worker, TF-IDF and optional OpenAI Responses API.

## Submission status

Prepared locally. **Not submitted.** The actual challenge submission form, deadline, rules, required assets and judge access have not been verified. The provided Codespace URL is a coding environment rather than a submission destination. Do not represent this draft as a completed challenge entry.

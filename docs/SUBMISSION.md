# CareWeave: Personalized care, grounded in evidence

**Tagline:** A clinician-review workspace that connects patient context, evidence and safety signals into a transparent care discussion.

**Repository:** https://github.com/Janicebenita/AI-Driven-Personalized-Treatment-Planner_HiDevs

## Problem

Generic treatment suggestions can miss the factors that matter most: renal impairment, existing medicines, a verified genetic result, meal routines and affordability. An answer without inspectable evidence and follow-up guidance is difficult to review responsibly.

## Solution

CareWeave demonstrates a focused adult type 2 diabetes workflow. It combines structured patient context, sparse vector evidence retrieval, independent safety checks and an optional evidence-constrained GenAI briefing. The interface puts rationale, citations, safety signals, monitoring and missing information beside the discussion options.

## Technical approach

A dependency-free JavaScript core runs in a local Node server and a deployable Cloudflare Worker. TF-IDF vectors and cosine similarity rank original summaries of NICE, KDIGO and CPIC evidence. Rule-linked sources are retained regardless of retrieval rank. The optional OpenAI Responses API integration uses server-side credentials, patient-data isolation in the prompt, strict structured output and citation-ID checks. It never replaces the independent safety gate.

## Demonstration

Three synthetic cases show renal/genetic, lifestyle and complex-care profiles. Changing kidney function changes the pathway; a verified SLCO1B1–simvastatin combination triggers review; acute symptoms withhold routine planning. Edited profiles invalidate old reports. JSON export and complete-report printing support review.

## Validation and limitations

22 automated software checks passed. Browser checks confirmed core case switching, evidence/safety tabs, input-change invalidation, urgent withholding and narrow-layout fit. Live AI inference is not credential-configured or provider-tested. This is an educational research prototype, not a clinically validated system. It supports a bounded adult diabetes pathway, not all diagnoses; allergy and interaction checks are incomplete. No real patient data is used or persisted. The hosted Site currently requires owner access.

## Built with

JavaScript, Node.js, HTML, CSS, TF-IDF vector search, Cloudflare Worker, optional OpenAI Responses API.

## Submission status

Prepared locally. **Not submitted.** The actual challenge submission form, deadline, rules, required assets and judge access have not been verified. The provided Codespace URL is a coding environment rather than a submission destination. Do not represent this draft as a completed challenge entry.

# CareWeave demo transcript

## Evidence into care

A transparent, clinician-review treatment planning prototype

**The challenge:** Connect diagnosis, medical history, verified genetics and lifestyle to a reviewable plan.

**The approach:** Independent safety checks + local MiniLM / Chroma retrieval + optional Groq / Llama synthesis.

**What this video shows:** Actual synthetic-case pipeline outputs rendered as a walkthrough. This is not a screen recording or live AI generation.

## 01  Meet the synthetic patient

Maya: adult type 2 diabetes with confirmed CKD

**Clinical context:** Age 58 | HbA1c 8.4% | eGFR 42 | BMI 31

**Medicines and verified phenotype:** metformin, simvastatin | SLCO1B1: poor function

**Daily life and priorities:** Vegetarian meals; sedentary desk work. Goal: Protect kidney health and avoid injections. Budget: limited.

## 02  A personalized discussion

The plan explains which patient factors shaped the options

**Review the metformin + SGLT2 pathway:** Discuss suitability, current therapy, renal labels and contraindications. This is a class-level option for clinician review, not an instruction to start a drug.

**Why it fits:** eGFR 42; confirmed CKD makes kidney protection relevant. Evidence: NG28-RENAL

**Practical fit:** The report also retains lifestyle goals and affordability as explicit discussion items.

## 03  Make risk visible

The safety layer runs independently of the language model

**Review renal suitability of metformin:** Reduced kidney function requires current label, dose and trend review. The prototype does not calculate a dose. [NG28-RENAL]

**Gene–drug safety signal:** Verified SLCO1B1 poor function plus simvastatin warrants pharmacist/prescriber review for an alternative. Ask about muscle pain, weakness or dark urine. [CPIC-STATIN]

## 04  Change one factor

Counterfactual: eGFR 42 -> 24, with other inputs held constant

**Changed treatment pathway:** Use a kidney-specific treatment review. eGFR 24 changes the pathway and excludes the routine metformin option.

**New prompt-review signal:** eGFR 24 is below the metformin threshold in the selected renal pathway. Contact the prescriber promptly for a supervised review; do not change treatment independently.

**Human oversight:** The prototype does not calculate doses or instruct the patient to change medication independently.

## 05  Inspect the evidence

Actual local MiniLM embeddings and Chroma cosine retrieval

**NG28-RENAL | cosine 0.639:** Diabetes with chronic kidney disease. Initial medicines, 1.18

**NG28-INITIAL | cosine 0.523:** Initial medicines for type 2 diabetes. Initial medicines, sections 1.13–1.19

**CPIC-STATIN | cosine 0.522:** SLCO1B1 and statin-associated muscle symptoms. Simvastatin recommendations, Table 2

**Interpretation:** Similarity measures retrieval relevance, not clinical confidence. Rule-linked evidence is retained regardless of rank.

## 06  Plan the follow-up

Monitoring remains tied to explicit evidence sources

**Before a change:** Reconcile medicines and allergies; verify renal trend, urine ACR, blood pressure, relevant contraindications, access and shared HbA1c goal. [NG28-CARE]

**Early after a change:** Clinician sets timing for renal function, volume status and blood pressure review based on the selected medicine and baseline risk. [KDIGO-2024]

**3–6 months:** Review HbA1c until stable, treatment tolerance and the patient’s goal; agree whether the plan should change. [NG28-CARE]

## 07  Know when to stop

Counterfactual: acute symptoms flag enabled

**Independent gate result:** Status: withheld | Routine options: 0 | Routine monitoring items: 0

**Escalation:** Acute symptoms were reported. Seek urgent in-person assessment; use local emergency services for severe symptoms. Routine planning is withheld.

**Provider boundary:** Withheld cases do not call embeddings or the generative provider. The LLM cannot override this gate.

## 08  Be explicit about gaps

A useful report makes uncertainty and limits inspectable

**Missing information:** Urine albumin-to-creatinine ratio and renal trend; Medication doses, adherence and complete interaction review; Blood pressure, cardiovascular history and adverse reactions

**Clinical boundary:** Educational research prototype. Not clinically validated. Adult type 2 diabetes only; allergy and interaction checks are incomplete.

**Live generation:** Groq/Llama is integrated but requires a server-side key. This demo uses semantic retrieval only; no live provider result is claimed.

## CareWeave: ready for review

Reproducible code, public synthetic cases, inspectable evidence

**Software verification:** 25 JavaScript + 16 Python checks passed. Linux container build, HTTP startup, Node safety core and actual MiniLM/Chroma retrieval passed.

**Retrieval smoke benchmark:** Expected source found in the top three for 5 of 5 developer-authored queries. This is not a held-out or clinical accuracy evaluation.

**Run the complete interface:** Install the repository requirements and run: streamlit run streamlit_app.py. Cloud deployment remains disabled at the participant's request.

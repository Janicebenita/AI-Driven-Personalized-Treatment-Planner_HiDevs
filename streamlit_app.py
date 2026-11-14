"""HiDevs seven-step semantic RAG demo. Start: streamlit run streamlit_app.py"""
import hashlib
import json
import os
import uuid

import streamlit as st
from dotenv import load_dotenv

from rag.ingestion import ROOT, load_corpus
from rag.pipeline import create_report, safety_plan

load_dotenv(ROOT / '.env')
st.set_page_config(page_title='CareWeave · Semantic RAG', page_icon='🌿', layout='wide')
st.title('CareWeave · evidence into care')
st.caption('HiDevs semantic RAG track · MiniLM → Chroma / FAISS → Groq / Llama → clinician review')
st.warning('Research prototype. Synthetic cases only. Not a prescription or clinically validated medical system.')
if 'session_id' not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex


@st.cache_resource(show_spinner='Loading the local MiniLM model and public evidence index…')
def get_knowledge_base(backend):
    from rag.retrieval import KnowledgeBase
    return KnowledgeBase(backend=backend)


cases = json.loads((ROOT / 'data/synthetic-cases.json').read_text(encoding='utf-8'))
with st.sidebar:
    st.header('Pipeline configuration')
    backend = st.selectbox('Vector backend', ['chroma', 'faiss'],
                          index=1 if os.getenv('VECTOR_BACKEND') == 'faiss' else 0,
                          help='Try Chroma first; FAISS is a compatibility fallback and needs requirements-faiss.txt.')
    st.caption('Embeddings run locally. First use downloads the public MiniLM model from Hugging Face.')
    st.caption('Groq model: ' + os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile'))
    st.caption('Groq key: configured' if os.getenv('GROQ_API_KEY') else 'Groq key: not configured')
    ai = st.checkbox('Send synthetic context to Groq for AI briefing', value=False,
                     disabled=not bool(os.getenv('GROQ_API_KEY')))
    st.caption('Provider access and limits depend on your account. Keys stay in server-side environment variables.')

planner_tab, library_tab, workflow_tab = st.tabs(['Treatment workspace', 'Evidence & provenance', 'Seven-step workflow'])
with planner_tab:
    selected = st.selectbox('Explore a synthetic case', list(cases), format_func=lambda k: cases[k]['label'])
    p = cases[selected]
    left, right = st.columns([1, 1.4], gap='large')
    # Keys include the case, so switching cases restores its distinct context.
    def key(field):
        return selected + ':' + field
    with left:
        st.subheader('Patient context')
        profile = {}
        profile['diagnosis'] = st.selectbox('Diagnosis', ['t2d', 'other'],
            format_func=lambda v: 'Confirmed type 2 diabetes' if v == 't2d' else 'Other / uncertain', key=key('diagnosis'))
        a, b = st.columns(2)
        profile['age'] = a.number_input('Age (years)', 1, 110, p['age'], key=key('age'))
        profile['hba1c'] = b.number_input('HbA1c (%)', 3.0, 20.0, float(p['hba1c']), step=0.1, key=key('hba1c'))
        profile['egfr'] = a.number_input('eGFR (mL/min/1.73 m²)', 1.0, 150.0, float(p['egfr']), key=key('egfr'))
        profile['bmi'] = b.number_input('BMI (kg/m²)', 10.0, 70.0, float(p['bmi']), key=key('bmi'))
        for field, label in [('ckd', 'Confirmed CKD'), ('hf', 'Heart failure'), ('frail', 'Frailty / fall risk'),
                             ('pregnant', 'Pregnant'), ('acute', 'Acute symptoms / urgent concern')]:
            profile[field] = st.checkbox(label, p[field], key=key(field))
        st.caption('Urgent examples: chest pain, severe breathlessness, confusion or persistent vomiting.')
        profile['medications'] = st.text_input('Current medicines', p['medications'], max_chars=1500, key=key('medications'))
        profile['allergies'] = st.text_input('Allergies / prior reactions', p['allergies'], max_chars=1500, key=key('allergies'))
        phenotypes = ['unknown', 'normal', 'decreased', 'poor']
        profile['genetics'] = st.selectbox('Verified SLCO1B1 phenotype', phenotypes,
            index=phenotypes.index(p['genetics']), key=key('genetics'))
        profile['lifestyle'] = st.text_area('Lifestyle and routine', p['lifestyle'], max_chars=1500, key=key('lifestyle'))
        profile['goal'] = st.text_input('What matters most?', p['goal'], max_chars=1500, key=key('goal'))
        profile['budget'] = st.selectbox('Affordability', ['limited', 'standard'],
            index=0 if p['budget'] == 'limited' else 1, key=key('budget'))
        profile['notes'] = st.text_area('Additional context', p['notes'], max_chars=1500, key=key('notes'))
        digest = hashlib.sha256(json.dumps({'profile': profile, 'backend': backend, 'ai': ai}, sort_keys=True).encode()).hexdigest()
        if st.session_state.get('report_digest') != digest:
            st.session_state.pop('report', None)
        if st.button('Build review plan', type='primary', use_container_width=True):
            try:
                gate = safety_plan(profile)
                if gate['status'] == 'withheld':
                    report = gate
                else:
                    try:
                        report = create_report(profile, get_knowledge_base(backend), ai)
                    except Exception as exc:
                        report = gate
                        report['retrievalError'] = f'Semantic retrieval unavailable ({type(exc).__name__}). Check model download and vector backend dependencies. This report uses rules-only evidence.'
                st.session_state.report = report
                st.session_state.report_digest = digest
            except Exception as exc:
                st.error('The profile could not be processed: ' + str(exc))
    with right:
        report = st.session_state.get('report')
        if not report:
            st.info('Build a plan from the current context. Editing a field clears the previous report.')
        else:
            st.subheader('Personalized review')
            st.caption(f"Mode: {report['mode']} · Status: {report['status']}")
            if report['status'] == 'withheld':
                st.error('Routine planning is withheld. Follow the safety signal below.')
            for signal in report['risks']:
                (st.error if signal['severity'] in ('high', 'critical') else st.warning)(
                    f"{signal['title']} — {signal['detail']} [{signal['source']}]")
            for field in ['retrievalError', 'aiError']:
                if report.get(field):
                    st.warning(report[field])
            if report.get('ai'):
                st.markdown('#### Groq evidence briefing · unverified synthesis')
                st.write(report['ai']['summary'])
                st.write('Uncertainty: ' + report['ai']['uncertainty'])
                st.caption('Evidence IDs: ' + ', '.join(report['ai']['sourceIds']))
            for option in report['options']:
                st.markdown('#### ' + option['title'])
                st.write(option['detail'])
                st.info('Why it fits: ' + option['why'])
                st.caption('Evidence ID: ' + option['source'])
            with st.expander('Monitoring and follow-up', expanded=False):
                for item in report['monitoring']:
                    st.write(f"**{item['when']}** — {item['task']} [{item['source']}]")
            with st.expander('Retrieved chunks and evidence', expanded=False):
                retrieval = report.get('retrieval', {})
                st.caption(f"Method: {retrieval.get('method', 'not-run')} · Backend: {retrieval.get('backend', 'none')}")
                if retrieval.get('fallback_reason'):
                    st.warning(retrieval['fallback_reason'])
                for match in retrieval.get('matches', []):
                    st.write(f"{match['source_id']} · cosine {match['cosine_similarity']:.3f} · tokens {match['token_start']}–{match['token_end']}")
                    st.write(match['text'])
                st.caption('Similarity measures retrieval relevance, not clinical confidence.')
                for evidence in report['evidence']:
                    st.link_button(evidence['id'] + ' · ' + evidence['title'], evidence['url'])
            with st.expander('Rationale, missing information and limitations'):
                for item in report['trace']:
                    st.write(item['title'] + ': ' + item['detail'])
                for item in report['missing'] + report['limitations']:
                    st.write('• ' + item)
            st.download_button('Download review JSON', json.dumps(report, indent=2),
                               file_name='careweave-semantic-review.json', mime='application/json')
            if os.getenv('MONGODB_URI'):
                consent = st.checkbox('Save this synthetic report to MongoDB for up to 7 days', value=False)
                if st.button('Save synthetic report', disabled=not consent):
                    from rag.history import save_synthetic_history
                    try:
                        save_synthetic_history(report, st.session_state.session_id, consent,
                            os.environ['MONGODB_URI'], os.getenv('MONGODB_DATABASE', 'careweave'))
                        st.success('Synthetic report saved. MongoDB expiry cleanup is asynchronous.')
                    except Exception:
                        st.error('History save failed. The report remains available in this session.')

with library_tab:
    st.subheader('Public evidence corpus')
    st.caption('Original curated summaries with source IDs, sections, dates and hashes. Not a live literature review.')
    for item in load_corpus():
        with st.expander(item['id'] + ' · ' + item['title']):
            st.write(item['summary'])
            st.caption(item['section'] + ' · ' + item['publisher'] + ' · ' + str(item['year']))
            st.link_button('Original source', item['url'])
            st.json({k: item[k] for k in ['retrieved_at', 'review_status', 'content_sha256']})

with workflow_tab:
    for title, text in [
        ('1 · Data sources', 'Public NICE, KDIGO and CPIC summaries with provenance; optional offline PDF/Markdown/text extraction before human review.'),
        ('2 · Preprocessing', 'Unicode normalization, whitespace cleaning, required provenance validation, stable source IDs and SHA-256 content hashes.'),
        ('3 · Chunking', 'MiniLM tokenizer offsets define chunks of up to 180 tokens with 30-token overlap, below the model sequence limit.'),
        ('4 · Knowledge base', 'Normalized all-MiniLM-L6-v2 embeddings are stored in a persistent Chroma cosine index. FAISS is an explicit, visible compatibility fallback.'),
        ('5 · AI engine', 'Embed patient context, retrieve top chunks, retain rule-required evidence and optionally request JSON synthesis from Groq/Llama. Validate output and source IDs.'),
        ('6 · UI and deployment', 'This Streamlit app can be deployed on a Python host with Node.js available for the shared safety core. The separate Sites demo uses the JavaScript sparse-retrieval track.'),
        ('7 · Testing', 'Unit tests, safety regression checks and an actual semantic retrieval benchmark. Live provider and MongoDB testing require credentials.')]:
        st.markdown('#### ' + title)
        st.write(text)

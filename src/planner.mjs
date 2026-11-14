import {EVIDENCE} from './evidence.mjs';
export const VERSION='careweave-1.0.0';
export const DEMOS={
 renal:{label:'Maya · kidney + genetics', age:58,diagnosis:'t2d',hba1c:8.4,egfr:42,bmi:31,medications:'metformin, simvastatin',allergies:'None known',genetics:'poor',ckd:true,hf:false,frail:false,pregnant:false,acute:false,lifestyle:'Vegetarian meals; sedentary desk work',goal:'Protect kidney health and avoid injections',budget:'limited',notes:'Synthetic case. CKD diagnosis previously confirmed.'},
 lifestyle:{label:'Alex · lifestyle + preferences',age:45,diagnosis:'t2d',hba1c:7.8,egfr:92,bmi:29,medications:'metformin',allergies:'None known',genetics:'unknown',ckd:false,hf:false,frail:false,pregnant:false,acute:false,lifestyle:'Night shifts; irregular meals; walking is practical',goal:'A plan that fits shift work',budget:'standard',notes:'Synthetic case; no known cardiovascular disease.'},
 complex:{label:'Sam · high-risk review',age:76,diagnosis:'t2d',hba1c:8.9,egfr:24,bmi:24,medications:'metformin, gliclazide, furosemide',allergies:'None known',genetics:'unknown',ckd:true,hf:true,frail:true,pregnant:false,acute:false,lifestyle:'Lives alone; inconsistent appetite',goal:'Avoid falls and low blood sugar',budget:'limited',notes:'Synthetic case. Needs a supervised medication review.'}
};
export function validate(p){
 if(!p || typeof p!=='object' || Array.isArray(p)) throw new Error('A patient profile object is required.');
 const ranges={age:[1,110],hba1c:[3,20],egfr:[1,150],bmi:[10,70]};
 for(const [k,[lo,hi]] of Object.entries(ranges)) if(typeof p[k]!=='number'||!Number.isFinite(p[k])||p[k]<lo||p[k]>hi) throw new Error(`${k} must be a number from ${lo} to ${hi}.`);
 for(const k of ['medications','allergies','lifestyle','goal','notes']) if(typeof p[k]!=='string'||p[k].length>1500) throw new Error(`${k} is required and must be under 1500 characters.`);
 for(const k of ['ckd','hf','frail','pregnant','acute']) if(typeof p[k]!=='boolean') throw new Error(`${k} must be explicitly true or false.`);
 if(!['t2d','other'].includes(p.diagnosis)||!['unknown','normal','decreased','poor'].includes(p.genetics)||!['limited','standard'].includes(p.budget)) throw new Error('Invalid diagnosis, genetic phenotype or budget selection.');
 return p;
}
const tokenize=t=>String(t).toLowerCase().replace(/[^a-z0-9]+/g,' ').split(/\s+/).filter(Boolean);
// Real sparse vector search: TF-IDF vectors with cosine similarity. Not neural embeddings.
export function retrieve(query, limit=4){
 const docs=EVIDENCE.map(e=>tokenize(e.title+' '+e.tags+' '+e.summary));
 const terms=[...new Set([...docs.flat(),...tokenize(query)])];
 const idf=Object.fromEntries(terms.map(t=>[t,Math.log((docs.length+1)/(docs.filter(d=>d.includes(t)).length+1))+1]));
 const vector=tokens=>{const counts={};for(const t of tokens)counts[t]=(counts[t]||0)+1;return Object.fromEntries(Object.entries(counts).map(([t,c])=>[t,(1+Math.log(c))*idf[t]]));};
 const q=vector(tokenize(query)), norm=v=>Math.sqrt(Object.values(v).reduce((s,x)=>s+x*x,0));
 return EVIDENCE.map((e,i)=>{const d=vector(docs[i]);return {...e,score:Number((Object.entries(q).reduce((s,[t,v])=>s+v*(d[t]||0),0)/(norm(q)*norm(d)||1)).toFixed(4))};}).sort((a,b)=>b.score-a.score).slice(0,limit);
}
export function plan(input){
 const p=validate(input), risks=[],options=[],monitoring=[],trace=[];
 const addRisk=(severity,title,detail,source)=>risks.push({severity,title,detail,source});
 const addOption=(title,detail,why,source)=>options.push({title,detail,why,source});
 const has=s=>new RegExp(`\\b(?:${s})\\b`,'i').test(p.medications);
 const text=[p.notes,p.lifestyle,p.goal].join(' ');
 // Conservative triage for explicit symptoms, independent of model behavior.
 const acute=p.acute||/chest pain|breathless at rest|confusion|persistent vomiting|unconscious|ketones positive/i.test(text);
 const blocked=acute||p.age<18||p.pregnant||p.diagnosis!=='t2d';
 if(acute)addRisk('critical','Urgent assessment takes priority','Acute symptoms were reported. Seek urgent in-person assessment; use local emergency services for severe symptoms. Routine planning is withheld.','Clinical safety gate');
 if(p.age<18||p.pregnant||p.diagnosis!=='t2d')addRisk('critical','Outside the validated prototype scope','This pathway supports non-pregnant adults with confirmed type 2 diabetes only. Specialist assessment is required.','Scope gate');
 if(!p.allergies.trim()||/unknown|not sure/i.test(p.allergies))addRisk('high','Allergy status is unresolved','Confirm allergies and prior adverse reactions before selecting any medicine.','Medication reconciliation');
 else if(!/^(none( known)?|no known allergies|nka)$/i.test(p.allergies.trim()))addRisk('high','Reported allergy requires reconciliation',`Reported: ${p.allergies}. No medication option is cleared until a clinician verifies the specific substance and reaction. Drug-class allergy matching is not comprehensive.`,'Medication reconciliation');
 if(!p.medications.trim()||/unknown|not sure/i.test(p.medications))addRisk('high','Medication list is incomplete','Reconcile prescriptions, over-the-counter medicines and supplements before choosing therapy.','Medication reconciliation');
 if(p.egfr<30&&has('metformin'))addRisk('high','Metformin needs prompt prescriber review',`eGFR ${p.egfr} is below the metformin threshold in the selected renal pathway. Contact the prescriber promptly for a supervised review; do not change treatment independently.`,'NG28-RENAL');
 if(p.egfr>=30&&p.egfr<45&&has('metformin'))addRisk('medium','Review renal suitability of metformin','Reduced kidney function requires current label, dose and trend review. The prototype does not calculate a dose.','NG28-RENAL');
 if(p.egfr<60&&!p.ckd)addRisk('medium','A low eGFR alone does not confirm CKD','Check repeat values, chronicity and urine albumin before assigning a CKD diagnosis.','KDIGO-2024');
 if(['poor','decreased'].includes(p.genetics)&&has('simvastatin'))addRisk('high','Gene–drug safety signal',`Verified SLCO1B1 ${p.genetics} function plus simvastatin warrants pharmacist/prescriber review for an alternative. Ask about muscle pain, weakness or dark urine.`,'CPIC-STATIN');
 if(has('gliclazide|glimepiride|glipizide|glyburide|glibenclamide|insulin'))addRisk('high','Hypoglycaemia and falls review','Insulin or sulfonylurea is listed. Review low-glucose episodes, meal timing, renal function and driving/fall risk.','NG28-REVIEW');
 if(p.frail||has('furosemide|bumetanide|torsemide'))addRisk('medium','Volume depletion needs attention','Frailty or a loop diuretic increases the importance of orthostatic symptoms, blood pressure and hydration assessment when considering SGLT2 therapy.','KDIGO-2024');
 if(p.hba1c>=10)addRisk('high','Marked hyperglycaemia needs timely review','Assess symptoms, hydration and ketones when indicated; a clinician may need an intensified pathway. This tool does not initiate insulin.','NG28-INITIAL');
 if(!blocked){
 if(p.egfr>=30)addOption('Review the metformin + SGLT2 pathway','Discuss suitability, current therapy, renal labels and contraindications. This is a class-level option for clinician review, not an instruction to start a drug.',`eGFR ${p.egfr}; ${p.ckd?'confirmed CKD makes kidney protection relevant':p.hf?'heart failure makes cardiorenal benefit relevant':'adult type 2 diabetes pathway'}.`,p.ckd?'NG28-RENAL':'NG28-INITIAL');
 else if(p.egfr>=20)addOption('Use a kidney-specific treatment review','Discuss a selected SGLT2 and DPP-4 pathway with the renal/diabetes team. Verify each agent’s local indication and renal label.',`eGFR ${p.egfr} changes the pathway and excludes the routine metformin option.`,'NG28-RENAL');
 else addOption('Prioritise specialist renal–diabetes review','Discuss the advanced kidney disease pathway, including whether a DPP-4 option is appropriate. Avoid routine metformin or new SGLT2 initiation in this prototype.',`eGFR ${p.egfr} is below 20; specialist selection and drug-specific labels are essential.`,'NG28-RENAL');
 addOption('Agree a feasible nutrition and movement plan',`Build around ${p.lifestyle||'the person’s daily routine'}. Choose one achievable food change and activity goal with the care team; adapt activity for symptoms, falls risk and comorbidities.`,`Patient priority: ${p.goal||'clarify goals before treatment selection'}.`,'NG28-CARE');
 if(p.budget==='limited')addOption('Check affordability before choosing an agent','Review formulary coverage, generic options and out-of-pocket cost with a pharmacist; ask which treatments are realistically sustainable.','Limited budget is recorded. Actual costs and insurance coverage are unknown.','NG28-CARE');
 monitoring.push({when:'Before a change',task:'Reconcile medicines and allergies; verify renal trend, urine ACR, blood pressure, relevant contraindications, access and shared HbA1c goal.',source:'NG28-CARE'});
 if(p.egfr<60||p.hf||p.frail)monitoring.push({when:'Early after a change',task:'Clinician sets timing for renal function, volume status and blood pressure review based on the selected medicine and baseline risk.',source:'KDIGO-2024'});
 if(has('insulin|gliclazide|glimepiride|glipizide|glyburide|glibenclamide'))monitoring.push({when:'During daily routines',task:'Agree glucose monitoring and a hypoglycaemia action plan; review meal timing and falls. Escalate severe symptoms urgently.',source:'NG28-REVIEW'});
 monitoring.push({when:'3–6 months',task:'Review HbA1c until stable, treatment tolerance and the patient’s goal; agree whether the plan should change.',source:'NG28-CARE'});
 monitoring.push({when:'If SGLT2 is selected',task:'Provide written sick-day and surgery/fasting advice; discuss ketosis symptoms and when to seek urgent care. Follow the local medicine label.',source:'KDIGO-2024'});
 }
 trace.push({step:'01',title:'Check scope and urgency',detail:blocked?'Routine options withheld by an independent safety gate.':'Adult type 2 diabetes; no urgent symptom flag in the supplied profile.'});
 trace.push({step:'02',title:'Connect patient factors',detail:`eGFR ${p.egfr}; HbA1c ${p.hba1c}%; ${p.ckd?'confirmed CKD':'CKD not confirmed'}; genetics ${p.genetics}; budget ${p.budget}.`});
 trace.push({step:'03',title:'Retrieve and constrain',detail:'TF-IDF cosine search ranks a curated evidence corpus. Renal, gene–drug and medication checks run separately; retrieval similarity is not clinical confidence.'});
 trace.push({step:'04',title:'Require human review',detail:'No doses, prescriptions or automatic approval. Sources and missing information remain visible.'});
 const query=`diabetes ${p.ckd||p.egfr<60?'kidney renal ckd egfr':''} ${p.hf?'heart failure':''} ${p.genetics!=='unknown'?'genetics slco1b1 statin simvastatin':''} ${p.frail?'frailty hypoglycaemia':''} ${p.lifestyle} ${p.goal} ${p.medications}`;
 const ranked=retrieve(query,4), ids=new Set([...ranked.map(e=>e.id),...options.map(x=>x.source),...risks.map(x=>x.source),...monitoring.map(x=>x.source)]);
 const evidence=[...ranked,...EVIDENCE.filter(e=>ids.has(e.id)&&!ranked.some(r=>r.id===e.id)).map(e=>({...e,score:null}))];
 return {version:VERSION,createdAt:new Date().toISOString(),status:blocked?'withheld':'review-required',profile:p,risks,options,monitoring,trace,evidence,mode:'rules-only',ai:null,missing:['Urine albumin-to-creatinine ratio and renal trend','Medication doses, adherence and complete interaction review','Blood pressure, cardiovascular history and adverse reactions','Shared HbA1c target, local formulary and verified genetic report'],limitations:['Research prototype; not clinically validated or a substitute for a licensed clinician.','Bounded adult type 2 diabetes pathway. Interaction and allergy screening are incomplete.','UK NICE pathways and international KDIGO/CPIC evidence; local licensing and practice may differ.','No benefit probability or clinical confidence score is calculated.']};
}

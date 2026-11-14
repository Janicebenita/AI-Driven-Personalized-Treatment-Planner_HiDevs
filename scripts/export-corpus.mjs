import fs from 'node:fs/promises';
import {EVIDENCE} from '../src/evidence.mjs';
import {DEMOS} from '../src/planner.mjs';
await fs.mkdir('data',{recursive:true});
const expected={'data/evidence.json':EVIDENCE.map(e=>({...e,retrieved_at:'2026-11-14',format:'curated-summary',review_status:'prototype-curated',license_note:'Original short paraphrase; source rights apply.'})),'data/synthetic-cases.json':DEMOS};
for(const [path,data] of Object.entries(expected)){
 if(process.argv.includes('--check')){if(JSON.stringify(JSON.parse(await fs.readFile(path,'utf8')))!==JSON.stringify(data))throw new Error(`${path} drifted from the shared JavaScript source. Run node scripts/export-corpus.mjs.`);}
 else await fs.writeFile(path,JSON.stringify(data,null,2)+'\n');
}
console.log(process.argv.includes('--check')?'Python corpus and synthetic cases match the shared sources.':'Exported public evidence summaries and synthetic profiles.');

// Build injects HTML, CSS and client JavaScript into ASSETS in the deployed module.
import {makePlan,providerConfig} from './service.mjs';
import {DEMOS} from './planner.mjs';
import {EVIDENCE} from './evidence.mjs';
export async function handle(request, env={}, assets={}){
 const url=new URL(request.url);
 const headers={'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"};
 const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{...headers,'Content-Type':'application/json'}});
 if(url.pathname==='/api/status'&&request.method==='GET'){const provider=providerConfig(env);return json({aiConfigured:!!provider,provider:provider?.name||null,version:'careweave-1.0.0'});}
 if(url.pathname==='/api/demos'&&request.method==='GET')return json({demos:DEMOS,evidence:EVIDENCE});
 if(url.pathname==='/api/plan'&&request.method==='POST'){
 if(request.headers.get('Origin')&&request.headers.get('Origin')!==url.origin)return json({error:'Cross-origin requests are not allowed.'},403);
 if(!request.headers.get('Content-Type')?.startsWith('application/json'))return json({error:'JSON required.'},415);
 if(Number(request.headers.get('Content-Length'))>16000)return json({error:'Profile too large.'},413);
 try{const raw=await request.text();if(raw.length>16000)return json({error:'Profile too large.'},413);const data=JSON.parse(raw);return json(await makePlan(data.profile,env,data.useAI===true));}catch(e){return json({error:e instanceof SyntaxError?'Invalid JSON.':String(e.message||'Invalid profile.')},400);}
 }
 if(url.pathname.startsWith('/api/'))return json({error:'Route not found.'},404);
 if(!['GET','HEAD'].includes(request.method))return new Response('Method not allowed',{status:405,headers});
 const asset=assets[url.pathname==='/'?'/index.html':url.pathname];
 if(!asset)return new Response('Not found',{status:404,headers});
 return new Response(request.method==='HEAD'?null:asset.body,{headers:{...headers,'Content-Type':asset.type}});
}

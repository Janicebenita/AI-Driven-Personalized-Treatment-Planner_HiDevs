import http from 'node:http';
import fs from 'node:fs/promises';
import {handle} from './src/worker.mjs';
// Optional local .env; environment values take precedence. Never printed.
try{const raw=await fs.readFile('.env','utf8');for(const line of raw.split(/\r?\n/)){const m=line.match(/^([A-Z_]+)=(.*)$/);if(m&&!process.env[m[1]])process.env[m[1]]=m[2].replace(/^['"]|['"]$/g,'');}}catch{}
const assets={};for(const [path,file,type] of [['/index.html','index.html','text/html; charset=utf-8'],['/style.css','style.css','text/css'],['/app.js','app.js','text/javascript']])assets[path]={body:await fs.readFile(`public/${file}`,'utf8'),type};
const port=Number(process.env.PORT||3000);
http.createServer(async(req,res)=>{try{const chunks=[];let size=0;for await(const c of req){size+=c.length;if(size>16000){res.writeHead(413);res.end('Too large');return;}chunks.push(c);}const request=new Request(`http://${req.headers.host}${req.url}`,{method:req.method,headers:req.headers,...(!['GET','HEAD'].includes(req.method)?{body:Buffer.concat(chunks)}:{})});const response=await handle(request,process.env,assets);res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));}catch{res.writeHead(500);res.end('Server error');}}).listen(port,'127.0.0.1',()=>console.log(`CareWeave running at http://localhost:${port}`));

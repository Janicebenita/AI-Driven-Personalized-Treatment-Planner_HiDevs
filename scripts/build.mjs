import fs from 'node:fs/promises';
await fs.mkdir('dist/server',{recursive:true});await fs.mkdir('dist/.openai',{recursive:true});
const manifest=JSON.parse(await fs.readFile('.openai/hosting.json','utf8'));delete manifest.static;
await fs.writeFile('.openai/hosting.json',JSON.stringify(manifest,null,2)+'\n');
await fs.writeFile('dist/.openai/hosting.json',JSON.stringify(manifest,null,2));
let source='';for(const file of ['evidence','planner','service','worker'])source+=(await fs.readFile(`src/${file}.mjs`,'utf8')).replace(/^import .*;\r?\n/gm,'')+'\n';
const assets={};for(const [route,file,type] of [['/index.html','index.html','text/html; charset=utf-8'],['/style.css','style.css','text/css'],['/app.js','app.js','text/javascript']])assets[route]={body:await fs.readFile(`public/${file}`,'utf8'),type};
source+=`\nconst ASSETS=${JSON.stringify(assets)};\nexport default {fetch(request,env){return handle(request,env,ASSETS)}};\n`;
await fs.writeFile('dist/server/index.js',source);console.log('Built dependency-free Worker and embedded assets.');

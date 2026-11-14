// Shared deterministic safety core for Python. JSON crosses stdin, never shell arguments.
import {plan} from '../src/planner.mjs';
let raw='';for await(const chunk of process.stdin){raw+=chunk;if(raw.length>16000){process.stderr.write('Profile too large');process.exit(1);}}
try{process.stdout.write(JSON.stringify(plan(JSON.parse(raw))));}catch(e){process.stderr.write(String(e.message));process.exit(1);}

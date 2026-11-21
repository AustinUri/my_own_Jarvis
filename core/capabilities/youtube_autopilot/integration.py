"""Small stable adapter for JARVIS tool router / dashboard.

This adapter does not assume the existing JARVIS registry signature; wire it in
once the actual local router API is inspected. No security-sensitive enable
function is exposed to generic agent/tool calls.
"""
from __future__ import annotations
from pathlib import Path
from .manager import root_dir,setup,config,read,tick,plan

CAPABILITY_ID='youtube_autopilot'

def execute(action:str, *, state_root:Path|None=None)->dict:
    root=setup(state_root or root_dir())
    if action=='status':
        c=config(root);jobs=read(root/'jobs.json',[])
        # Never expose credential/token paths or their content in the dashboard.
        safe={k:v for k,v in c.items() if k not in {'client_secrets','token_file'}}
        return {'capability':CAPABILITY_ID,'settings':safe,'jobs':[{'id':j['id'],'state':j['state'],'publish_at':j['publish_at'],'youtube_id':j.get('youtube_id'),'error':j.get('error')} for j in jobs]}
    if action=='plan':return {'added':len(plan(root,generate=False))}
    if action=='tick':return tick(root,generate=False,count=1)
    raise ValueError('Unsupported agent action. Publication consent can only be enabled explicitly via CLI.')

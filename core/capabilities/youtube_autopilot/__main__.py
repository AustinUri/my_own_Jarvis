"""python -m core.capabilities.youtube_autopilot ..."""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
from .manager import setup,root_dir,plan,run_one,tick,switch,config,read,readiness
from .youtube_api import credentials

def main():
    ap=argparse.ArgumentParser(description='JARVIS original English kids video autopilot')
    ap.add_argument('--root',type=Path,default=None,help='State directory (default: project_root/var/youtube_autopilot)')
    sub=ap.add_subparsers(dest='command',required=True)
    sub.add_parser('init');sub.add_parser('status');sub.add_parser('doctor');sub.add_parser('plan');sub.add_parser('authorize');sub.add_parser('pause')
    pp=sub.add_parser('preview');pp.add_argument('--all',action='store_true')
    rr=sub.add_parser('run-once');rr.add_argument('--generate',action='store_true');rr.add_argument('--count',type=int,default=1)
    loop=sub.add_parser('worker');loop.add_argument('--generate',action='store_true');loop.add_argument('--interval-minutes',type=int,default=60)
    enable=sub.add_parser('enable');enable.add_argument('--confirm',required=True)
    args=ap.parse_args()
    root=setup(args.root or root_dir())
    try:
        if args.command=='init':result={'state_dir':str(root),'config':str(root/'config.json'),'next':'Edit piper_model, authorize YouTube, preview, and only then enable autopublish.'}
        elif args.command=='status':result={'config':config(root),'jobs':read(root/'jobs.json',[])}
        elif args.command=='doctor':result=readiness(root)
        elif args.command=='plan':result={'planned':plan(root)}
        elif args.command=='preview':
            plan(root)
            result=run_one(root,preview=True)
        elif args.command=='run-once':result=tick(root,generate=args.generate,count=args.count)
        elif args.command=='worker':
            print('Worker started. PC must remain awake to create and upload NEW videos. Previously scheduled videos publish from YouTube without PC.',flush=True)
            while True:
                try:print(json.dumps(tick(root,generate=args.generate,count=1),ensure_ascii=False),flush=True)
                except Exception as ex:print(json.dumps({'error':str(ex)}),flush=True)
                time.sleep(max(10,int(args.interval_minutes))*60)
        elif args.command=='authorize':
            c=config(root);credentials({'token_file':c['token_file'],'client_secrets':c['client_secrets']},interactive=True)
            result={'authorized':True,'token_file':c['token_file']}
        elif args.command=='enable':result={'autopublish_enabled':switch(root,True,args.confirm)}
        elif args.command=='pause':result={'autopublish_enabled':switch(root,False)}
        print(json.dumps(result,indent=2,ensure_ascii=False,default=str))
    except Exception as exc:
        ap.exit(2,f'ERROR: {exc}\n')
if __name__=='__main__':main()

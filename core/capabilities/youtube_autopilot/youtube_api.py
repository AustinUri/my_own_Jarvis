"""YouTube OAuth upload. Nothing is uploaded without explicit persistent opt-in."""
from __future__ import annotations
import json
import os
from datetime import datetime,timezone
from pathlib import Path

SCOPE='https://www.googleapis.com/auth/youtube.upload'

def credentials(paths:dict, interactive:bool=False):
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError as ex:
        raise RuntimeError('Install the optional YouTube requirements first') from ex
    token=Path(paths['token_file']); secrets=Path(paths['client_secrets'])
    creds=Credentials.from_authorized_user_file(str(token),[SCOPE]) if token.exists() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not interactive:raise RuntimeError('YouTube OAuth not authorized. Run authorize interactively once.')
        if not secrets.is_file():raise RuntimeError('Google OAuth desktop client_secrets.json not found')
        flow=InstalledAppFlow.from_client_secrets_file(str(secrets),[SCOPE])
        creds=flow.run_local_server(port=0,access_type='offline',prompt='consent')
    token.parent.mkdir(parents=True,exist_ok=True)
    token.write_text(creds.to_json(),encoding='utf-8')
    try:os.chmod(token,0o600)
    except OSError:pass
    return creds

def upload(video_path:Path,episode:dict,publish_at:datetime,paths:dict):
    if publish_at.tzinfo is None or publish_at < datetime.now(timezone.utc):
        raise ValueError('Scheduled publish_at must be future and timezone-aware')
    if not video_path.is_file():raise FileNotFoundError(video_path)
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds=credentials(paths,interactive=False)
    service=build('youtube','v3',credentials=creds,cache_discovery=False)
    body={
      'snippet':{'title':episode['title'],'description':episode['description']+'\n\nOriginal animated preschool story in English.','categoryId':'1',
                 'defaultLanguage':'en','tags':['original kids cartoon','preschool','English story','Nori and Blink']},
      'status':{'privacyStatus':'private','publishAt':publish_at.astimezone(timezone.utc).isoformat().replace('+00:00','Z'),
                'selfDeclaredMadeForKids':True,'containsSyntheticMedia':False}
    }
    req=service.videos().insert(part='snippet,status',body=body,media_body=MediaFileUpload(str(video_path),mimetype='video/mp4',resumable=True,chunksize=8*1024*1024))
    resp=None
    while resp is None:
        progress,resp=req.next_chunk(num_retries=3)
    if not resp.get('id'):raise RuntimeError('Upload returned no YouTube video id; verify manually before retrying')
    return {'id':resp['id'],'url':'https://www.youtube.com/watch?v='+resp['id'],'publishAt':body['status']['publishAt']}

package com.jarvis.companion;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.speech.RecognizerIntent;
import android.speech.tts.TextToSpeech;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Locale;

public final class MainActivity extends Activity {
    private static final int REQ_CALENDAR=2602, REQ_NOTIFICATIONS=2603, REQ_SPEECH=2604;
    private EditText serverUrl,fallbackIp,pairCode,askText; private TextView status,jarvisReply; private PhoneApiClient api;
    private TextToSpeech tts; private boolean voiceReplies=true;
    @Override protected void onCreate(Bundle savedInstanceState){super.onCreate(savedInstanceState);setContentView(R.layout.activity_main);api=new PhoneApiClient(this);serverUrl=findViewById(R.id.serverUrl);fallbackIp=findViewById(R.id.fallbackIp);pairCode=findViewById(R.id.pairCode);askText=findViewById(R.id.askText);jarvisReply=findViewById(R.id.jarvisReply);status=findViewById(R.id.statusText);serverUrl.setText(api.prefs().getString("server_url",""));fallbackIp.setText(api.prefs().getString("tailscale_ipv4",""));voiceReplies=api.prefs().getBoolean("voice_replies",true);tts=new TextToSpeech(this,code->{if(code==TextToSpeech.SUCCESS)tts.setLanguage(Locale.US);});
        findViewById(R.id.testConnectionButton).setOnClickListener(v->testConnection());findViewById(R.id.pairButton).setOnClickListener(v->pair());findViewById(R.id.calendarPermissionButton).setOnClickListener(v->requestPermissions(new String[]{Manifest.permission.READ_CALENDAR},REQ_CALENDAR));findViewById(R.id.startButton).setOnClickListener(v->startLink());findViewById(R.id.askButton).setOnClickListener(v->askJarvis());findViewById(R.id.voiceAskButton).setOnClickListener(v->startVoiceQuestion());findViewById(R.id.voiceReplyButton).setOnClickListener(v->{voiceReplies=!voiceReplies;api.prefs().edit().putBoolean("voice_replies",voiceReplies).apply();updateVoiceButton();});findViewById(R.id.stopButton).setOnClickListener(v->{api.prefs().edit().putBoolean("companion_enabled",false).apply();stopService(new Intent(this,JarvisForegroundService.class));setStatus("Background companion stopped.");});updateVoiceButton();updateStatus();}
    private String server(){return serverUrl.getText().toString().trim();} private String fallback(){return fallbackIp.getText().toString().trim();}
    private void testConnection(){final String u=server(),ip=fallback();setStatus("Testing private JARVIS connection…");new Thread(()->{try{JSONObject r=api.health(u,ip);api.prefs().edit().putString("server_url",u).putString("tailscale_ipv4",ip).apply();runOnUiThread(()->setStatus("Connection OK. JARVIS "+r.optString("build","v"+r.optInt("version",0))+" is reachable."));}catch(Exception ex){runOnUiThread(()->setStatus("Connection test failed: "+ex.getMessage()));}},"jarvis-health").start();}
    private void pair(){final String u=server(),ip=fallback(),code=pairCode.getText().toString().trim();setStatus("Pairing…");new Thread(()->{try{api.health(u,ip);JSONObject r=api.pair(u,ip,code);runOnUiThread(()->setStatus("Paired securely as "+r.optString("name","phone")+". You can now ask JARVIS from this phone."));}catch(Exception ex){runOnUiThread(()->setStatus("Pairing failed: "+ex.getMessage()));}},"jarvis-pair").start();}
    private void startLink(){if(api.prefs().getString("device_id","").isEmpty()){setStatus("Pair the phone first.");return;}if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},REQ_NOTIFICATIONS);api.prefs().edit().putBoolean("companion_enabled",true).apply();startForegroundService(new Intent(this,JarvisForegroundService.class));setStatus("Secure background link started. Remote JARVIS chat is also ready while the PC core is online.");}
    private void askJarvis(){final String q=askText.getText().toString().trim();if(q.isEmpty()){setStatus("Type or dictate a question first.");return;}if(api.prefs().getString("device_id","").isEmpty()){setStatus("Pair the phone first.");return;}jarvisReply.setText("JARVIS is thinking…");new Thread(()->{try{JSONObject body=new JSONObject();body.put("text",q);JSONObject r=api.signedPost("/api/phone/ask",body,90000);String answer=r.optString("text",r.optString("spoken_text",""));if(!r.optBoolean("ok",false))throw new IllegalStateException(r.optString("error","JARVIS returned an error."));runOnUiThread(()->{jarvisReply.setText(answer);if(voiceReplies&&tts!=null)tts.speak(answer,TextToSpeech.QUEUE_FLUSH,null,"jarvis-phone-reply");});}catch(Exception ex){runOnUiThread(()->jarvisReply.setText("Remote JARVIS failed: "+ex.getMessage()));}},"jarvis-remote-ask").start();}
    private void startVoiceQuestion(){try{Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);i.putExtra(RecognizerIntent.EXTRA_LANGUAGE,Locale.US.toLanguageTag());i.putExtra(RecognizerIntent.EXTRA_PROMPT,"Speak to JARVIS");startActivityForResult(i,REQ_SPEECH);}catch(Exception ex){setStatus("Voice input is unavailable on this phone: "+ex.getMessage());}}
    private void updateVoiceButton(){((Button)findViewById(R.id.voiceReplyButton)).setText("PHONE VOICE REPLIES: "+(voiceReplies?"ON":"OFF"));}
    private void updateStatus(){String device=api.prefs().getString("device_id","");boolean cal=checkSelfPermission(Manifest.permission.READ_CALENDAR)==PackageManager.PERMISSION_GRANTED;if(device.isEmpty())setStatus("Not paired. Enter the secure HTTPS *.ts.net URL from JARVIS. The optional 100.x Tailscale IP is only the DNS fallback.");else setStatus("Paired: "+device+" Native calendar read: "+(cal?"GRANTED":"NOT GRANTED")+" Remote JARVIS: READY when the PC core is online.");}
    private void setStatus(String s){status.setText(s);}
    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){super.onActivityResult(requestCode,resultCode,data);if(requestCode==REQ_SPEECH&&resultCode==RESULT_OK&&data!=null){ArrayList<String> r=data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);if(r!=null&&!r.isEmpty()){askText.setText(r.get(0));askJarvis();}}}
    @Override public void onRequestPermissionsResult(int requestCode,String[] permissions,int[] grantResults){super.onRequestPermissionsResult(requestCode,permissions,grantResults);updateStatus();}
    @Override protected void onDestroy(){if(tts!=null){tts.stop();tts.shutdown();}super.onDestroy();}
}
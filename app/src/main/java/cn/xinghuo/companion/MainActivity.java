package cn.xinghuo.companion;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.speech.tts.Voice;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Locale;

public class MainActivity extends Activity {
    private WebView web;
    private LinearLayout loading;
    private TextView loadingText;
    private Button retry;
    private String origin;
    private boolean pageFailed, destroyed, requestingMic;
    private TextToSpeech tts;
    private volatile boolean ttsReady;
    private volatile String voicesJson="[]";
    private SpeechRecognizer recognizer;
    private String recognitionId="";
    private boolean recognizing;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Runnable recognitionTimeout=()->finishRecognition("no-speech",null);

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        FrameLayout root=new FrameLayout(this);root.setBackgroundColor(Color.rgb(139,16,36));
        setContentView(root);
        if(Build.VERSION.SDK_INT>=30) {
            getWindow().setDecorFitsSystemWindows(false);
            root.setOnApplyWindowInsetsListener((v,insets)->{
                android.graphics.Insets bars=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout()|WindowInsets.Type.ime());
                v.setPadding(bars.left,bars.top,bars.right,bars.bottom);
                return WindowInsets.CONSUMED;
            });
        }
        web=new WebView(this);
        root.addView(web,new FrameLayout.LayoutParams(-1,-1));
        WebSettings settings=web.getSettings();
        settings.setJavaScriptEnabled(true);settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);settings.setAllowContentAccess(false);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setTextZoom(100);
        web.setBackgroundColor(Color.rgb(255,248,240));
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);
        web.addJavascriptInterface(new NativeBridge(),"XinghuoAndroid");
        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest req) {
                if(isLocal(req.getUrl().toString()))return false;
                if(req.isForMainFrame())openExternal(req.getUrl().toString());
                return true;
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest req) {
                if(isLocal(req.getUrl().toString()))return null;
                return new WebResourceResponse("text/plain","UTF-8",new ByteArrayInputStream(new byte[0]));
            }
            @Override public void onPageStarted(WebView view,String url,android.graphics.Bitmap icon){pageFailed=false;}
            @Override public void onPageFinished(WebView view,String url) {
                if(pageFailed||!isLocal(url))return;
                if(url.endsWith("agent.html")||url.endsWith("game.html")){
                    view.evaluateJavascript("typeof send==='function'||typeof startLevel==='function'",ready->{
                        if(destroyed)return;
                        if("true".equals(ready))loading.setVisibility(View.GONE);else showError();
                    });
                }else loading.setVisibility(View.GONE);
            }
            @Override public void onReceivedError(WebView view,WebResourceRequest req,android.webkit.WebResourceError error) {
                if(req.isForMainFrame()){pageFailed=true;showError();}
            }
        });
        loading=new LinearLayout(this);loading.setOrientation(LinearLayout.VERTICAL);
        loading.setGravity(Gravity.CENTER);loading.setPadding(32,32,32,32);
        loading.setBackgroundColor(Color.rgb(255,248,240));
        loadingText=new TextView(this);loadingText.setTextSize(20);loadingText.setTextColor(Color.rgb(139,16,36));
        loadingText.setGravity(Gravity.CENTER);loadingText.setText("星火同行\n正在准备你的成长伙伴…");
        loading.addView(loadingText);loading.addView(new ProgressBar(this));
        retry=new Button(this);retry.setText("重新打开");retry.setVisibility(View.GONE);retry.setOnClickListener(v->boot());
        loading.addView(retry);root.addView(loading,new FrameLayout.LayoutParams(-1,-1));
        initTts();boot();
        if(Build.VERSION.SDK_INT>=33)getOnBackInvokedDispatcher().registerOnBackInvokedCallback(0,this::handleBack);
    }
    private boolean isLocal(String url){return origin!=null&&url.startsWith(origin+"/");}
    private void boot(){
        retry.setVisibility(View.GONE);loading.setVisibility(View.VISIBLE);
        loadingText.setText("星火同行\n正在准备你的成长伙伴…");
        new Thread(()->{
            try {
                File webRoot=new File(getFilesDir(),"web");webRoot.mkdirs();
                String hash=readText(getAssets().open("web-manifest.sha256"));
                File marker=new File(webRoot,".version");
                if(!marker.exists()||!readText(new FileInputStream(marker)).equals(hash)){
                    copyAssets("web",webRoot);Files.write(marker.toPath(),hash.getBytes(StandardCharsets.UTF_8));
                }
                if(!Python.isStarted())Python.start(new AndroidPlatform(getApplicationContext()));
                int port=Python.getInstance().getModule("mobile_server").callAttr("start",webRoot.getAbsolutePath(),getFilesDir().getAbsolutePath()).toInt();
                origin="http://127.0.0.1:"+port;
                runOnUiThread(()->{if(!destroyed)web.loadUrl(origin+"/agent.html");});
            }catch(Exception e){Log.e("Xinghuo","Startup failed",e);runOnUiThread(this::showError);}
        },"xinghuo-start").start();
    }
    private String readText(InputStream input)throws Exception{
        try(InputStream source=input;ByteArrayOutputStream bytes=new ByteArrayOutputStream()){
            byte[] buffer=new byte[4096];int n;while((n=source.read(buffer))!=-1)bytes.write(buffer,0,n);
            return bytes.toString("UTF-8");
        }
    }
    private void copyAssets(String path,File target)throws Exception{
        String[] entries=getAssets().list(path);
        if(entries!=null&&entries.length>0){
            target.mkdirs();for(String name:entries)copyAssets(path+"/"+name,new File(target,name));
        }else{
            try(InputStream input=getAssets().open(path);FileOutputStream output=new FileOutputStream(target)){
                byte[] buffer=new byte[65536];int n;while((n=input.read(buffer))!=-1)output.write(buffer,0,n);
            }
        }
    }
    private void showError(){
        if(destroyed)return;
        loadingText.setText("启动没有完成\n请点击重新打开；若仍失败，请更新手机的 Android System WebView。");
        retry.setVisibility(View.VISIBLE);loading.setVisibility(View.VISIBLE);
    }
    private void js(String script){runOnUiThread(()->{if(!destroyed&&web!=null)web.evaluateJavascript(script,null);});}
    private void event(String kind,String id,String type,String text){
        try{
            JSONObject value=new JSONObject().put("kind",kind).put("id",id).put("type",type).put("text",text==null?"":text);
            js("window.__xinghuoNativeEvent&&window.__xinghuoNativeEvent("+value+");");
        }catch(Exception ignored){}
    }
    private void openExternal(String url){
        try{
            Uri uri=Uri.parse(url);String scheme=uri.getScheme();
            if("http".equals(scheme)||"https".equals(scheme))startActivity(new Intent(Intent.ACTION_VIEW,uri));
        }catch(Exception e){android.widget.Toast.makeText(this,"未找到可打开资料链接的浏览器",android.widget.Toast.LENGTH_SHORT).show();}
    }
    private void initTts(){
        tts=new TextToSpeech(getApplicationContext(),status->{
            ttsReady=status==TextToSpeech.SUCCESS;
            if(ttsReady){
                tts.setLanguage(Locale.SIMPLIFIED_CHINESE);
                JSONArray list=new JSONArray();
                try{if(tts.getVoices()!=null)for(Voice voice:tts.getVoices()){
                    if(!voice.getLocale().getLanguage().equals("zh"))continue;
                    list.put(new JSONObject().put("name",voice.getName()).put("lang",voice.getLocale().toLanguageTag())
                        .put("localService",!voice.isNetworkConnectionRequired()).put("voiceURI",voice.getName()));
                }}catch(Exception ignored){}
                voicesJson=list.toString();
                event("voices","","change","");
                tts.setOnUtteranceProgressListener(new UtteranceProgressListener(){
                    @Override public void onStart(String id){event("speech",id,"start","");}
                    @Override public void onDone(String id){event("speech",id,"end","");}
                    @Override public void onError(String id){event("speech",id,"error","系统中文语音不可用");}
                });
            }
        });
    }
    private void startRecognition(String id){
        recognitionId=id;
        if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){
            requestingMic=true;requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},71);return;
        }
        if(!SpeechRecognizer.isRecognitionAvailable(this)){finishRecognition("service-not-allowed",null);return;}
        if(recognizer==null)recognizer=SpeechRecognizer.createSpeechRecognizer(this);
        final String session=id;recognizing=true;
        recognizer.setRecognitionListener(new RecognitionListener(){
            private boolean valid(){return recognizing&&recognitionId.equals(session);}
            @Override public void onReadyForSpeech(Bundle p){if(valid())event("recognition",session,"start","");}
            @Override public void onBeginningOfSpeech(){}
            @Override public void onRmsChanged(float rms){}
            @Override public void onBufferReceived(byte[] buffer){}
            @Override public void onEndOfSpeech(){}
            @Override public void onError(int error){if(valid())finishRecognition(error==SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS?"not-allowed":"no-speech",null);}
            @Override public void onResults(Bundle results){
                if(!valid())return;
                ArrayList<String> texts=results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                finishRecognition(texts==null||texts.isEmpty()?"no-speech":null,texts==null||texts.isEmpty()?null:texts.get(0));
            }
            @Override public void onPartialResults(Bundle p){}
            @Override public void onEvent(int type,Bundle p){}
        });
        Intent intent=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE,"zh-CN");intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,false);
        try{recognizer.startListening(intent);handler.postDelayed(recognitionTimeout,25000);}
        catch(Exception e){finishRecognition("audio-capture",null);}
    }
    private void finishRecognition(String error,String text){
        handler.removeCallbacks(recognitionTimeout);
        recognizing=false;
        if(error!=null){if(recognizer!=null)recognizer.cancel();event("recognition",recognitionId,"error",error);}
        else if(text!=null)event("recognition",recognitionId,"result",text);
        event("recognition",recognitionId,"end","");
    }
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] results){
        super.onRequestPermissionsResult(request,permissions,results);
        if(request==71){requestingMic=false;if(results.length>0&&results[0]==PackageManager.PERMISSION_GRANTED)startRecognition(recognitionId);else finishRecognition("not-allowed",null);}
    }
    private void handleBack(){
        if(web==null){moveTaskToBack(true);return;}
        web.evaluateJavascript("(function(){if(typeof closeServiceInfo==='function'&&document.getElementById('serviceMask').classList.contains('on')){closeServiceInfo();return true}if(!location.pathname.endsWith('agent.html')){location.href='agent.html';return true}return false})()",handled->{
            if(!"true".equals(handled))moveTaskToBack(true);
        });
    }
    @Override public void onBackPressed(){handleBack();}
    @Override public void onPause(){
        super.onPause();
        js("if(typeof stopSpeak==='function')stopSpeak();");
        if(tts!=null)tts.stop();
        if(!requestingMic&&recognizing)finishRecognition("aborted",null);
        if(web!=null)web.onPause();
    }
    @Override public void onResume(){super.onResume();if(web!=null)web.onResume();}
    @Override public void onDestroy(){
        destroyed=true;handler.removeCallbacksAndMessages(null);
        if(recognizer!=null)recognizer.destroy();
        if(tts!=null){tts.stop();tts.shutdown();}
        if(web!=null){web.removeJavascriptInterface("XinghuoAndroid");web.destroy();web=null;}
        super.onDestroy();
    }
    public class NativeBridge{
        @JavascriptInterface public String getVoices(){return voicesJson;}
        @JavascriptInterface public void openExternal(String url){runOnUiThread(()->MainActivity.this.openExternal(url));}
        @JavascriptInterface public void speak(String text,String id,String voice,float pitch,float rate){
            runOnUiThread(()->{
                if(!ttsReady){event("speech",id,"error","系统中文语音尚未就绪");return;}
                if(voice!=null&&!voice.isEmpty()&&tts.getVoices()!=null)for(Voice v:tts.getVoices())if(v.getName().equals(voice)){tts.setVoice(v);break;}
                tts.setPitch(Math.max(.6f,Math.min(1.6f,pitch)));tts.setSpeechRate(Math.max(.6f,Math.min(1.4f,rate)));
                if(tts.speak(text,TextToSpeech.QUEUE_FLUSH,null,id)==TextToSpeech.ERROR)event("speech",id,"error","系统中文音色不可用");
            });
        }
        @JavascriptInterface public void stopSpeech(){runOnUiThread(()->{if(tts!=null)tts.stop();});}
        @JavascriptInterface public void startRecognition(String id){runOnUiThread(()->MainActivity.this.startRecognition(id));}
        @JavascriptInterface public void stopRecognition(){runOnUiThread(()->{if(recognizer!=null)recognizer.stopListening();});}
        @JavascriptInterface public void abortRecognition(){runOnUiThread(()->{if(recognizing)finishRecognition("aborted",null);});}
    }
}

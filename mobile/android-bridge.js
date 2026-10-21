// Android platform services; online character speech still uses the bundled TTS server.
document.documentElement.classList.add('android-app');
if(!Array.prototype.at)Object.defineProperty(Array.prototype,'at',{value:function(n){n=Math.trunc(n)||0;return this[n<0?this.length+n:n]}});
(() => {
  const native=window.XinghuoAndroid;
  if(native){
    let nextId=0,currentSpeech=null;
    const recognizers=new Map(),listeners=new EventTarget();
    class Utterance{constructor(text){this.text=text;this.lang='zh-CN';this.pitch=1;this.rate=1;this.voice=null}}
    const speech={
      getVoices(){try{return JSON.parse(native.getVoices())}catch(e){return[]}},
      speak(utterance){
        speech.cancel();const id=String(++nextId);currentSpeech={id,utterance};
        native.speak(utterance.text,id,utterance.voice?.name||'',utterance.pitch,utterance.rate);
      },
      cancel(){currentSpeech=null;native.stopSpeech()},
      addEventListener:(...args)=>listeners.addEventListener(...args),
      removeEventListener:(...args)=>listeners.removeEventListener(...args),
      onvoiceschanged:null
    };
    Object.defineProperty(window,'speechSynthesis',{value:speech,configurable:true});
    window.SpeechSynthesisUtterance=Utterance;
    window.SpeechRecognition=class{
      constructor(){this.lang='zh-CN';this.continuous=false;this.interimResults=false;this.id=''}
      start(){this.id=String(++nextId);recognizers.set(this.id,this);native.startRecognition(this.id)}
      stop(){native.stopRecognition()}
      abort(){native.abortRecognition()}
    };
    window.__xinghuoNativeEvent=event=>{
      if(event.kind==='voices'){speech.onvoiceschanged?.();listeners.dispatchEvent(new Event('voiceschanged'));return}
      if(event.kind==='speech'){
        if(currentSpeech?.id!==event.id)return;
        const u=currentSpeech.utterance;
        if(event.type==='start')u.onstart?.();
        if(event.type==='end'){currentSpeech=null;u.onend?.()}
        if(event.type==='error'){currentSpeech=null;u.onerror?.({error:'synthesis-failed'})}
      }
      if(event.kind==='recognition'){
        const rec=recognizers.get(event.id);if(!rec)return;
        if(event.type==='start')rec.onstart?.();
        if(event.type==='result')rec.onresult?.({results:[[{transcript:event.text,confidence:1}]]});
        if(event.type==='error')rec.onerror?.({error:event.text});
        if(event.type==='end'){recognizers.delete(event.id);rec.onend?.()}
      }
    };
    window.open=url=>{native.openExternal(new URL(url,location.href).href);return null};
    document.addEventListener('click',event=>{
      const link=event.target.closest('a[href]');
      if(link&&/^https?:/.test(link.href)&&new URL(link.href).origin!==location.origin){
        event.preventDefault();native.openExternal(link.href);
      }
    });
  }
  document.addEventListener('DOMContentLoaded',()=>{
    const input=document.getElementById('txt');if(!input)return;
    input.setAttribute('enterkeyhint','send');
    input.addEventListener('focus',()=>document.documentElement.classList.add('mobile-typing'));
    input.addEventListener('blur',()=>document.documentElement.classList.remove('mobile-typing'));
    const resize=()=>document.documentElement.style.setProperty('--app-height',innerHeight+'px');
    addEventListener('resize',resize);resize();
  });
})();

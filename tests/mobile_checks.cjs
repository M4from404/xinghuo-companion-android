const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const base=process.argv[2]||'http://127.0.0.1:18766';
const out=path.resolve(__dirname,'../test-results');fs.mkdirSync(out,{recursive:true});
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true,args:['--autoplay-policy=no-user-gesture-required']});
  try{
    const ctx=await browser.newContext({viewport:{width:390,height:780},deviceScaleFactor:1,isMobile:true,hasTouch:true});
    await ctx.addInitScript(()=>{
      window.nativeCalls=[];
      window.XinghuoAndroid={
        getVoices:()=>JSON.stringify([{name:'手机中文语音',lang:'zh-CN',localService:true}]),
        speak:(...args)=>nativeCalls.push(['speak',...args]),
        stopSpeech:()=>nativeCalls.push(['stop']),
        startRecognition:id=>{window.activeRecognition=id;__xinghuoNativeEvent({kind:'recognition',id,type:'start'})},
        stopRecognition:()=>__xinghuoNativeEvent({kind:'recognition',id:activeRecognition,type:'end'}),
        abortRecognition:()=>{},
        openExternal:url=>nativeCalls.push(['open',url])
      };
    });
    const page=await ctx.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.route('**/api/chat',r=>r.fulfill({contentType:'application/x-ndjson',body:JSON.stringify({type:'delta',text:'先给自己一点休息时间，再从一件小事开始。'})+'\n'+JSON.stringify({type:'done'})+'\n'}));
    await page.route('**/tts?*',r=>r.fulfill({contentType:'audio/mpeg',body:fs.readFileSync(path.resolve(__dirname,'../app/src/main/assets/web/voice/v00.mp3'))}));
    await page.goto(base+'/agent.html');await page.waitForFunction(()=>typeof preferencesReady!=="undefined");await page.evaluate(()=>preferencesReady);
    await page.waitForFunction(()=>document.querySelector('#char video')?.readyState>=2);
    for(const size of [{width:360,height:640},{width:390,height:780},{width:412,height:892}]){
      await page.setViewportSize(size);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'No horizontal overflow');
      const rect=await page.locator('#sendBtn').boundingBox();assert(rect.y+rect.height<=size.height,'Composer must stay on screen');
      const stage=await page.locator('#char').boundingBox();assert(stage.height>=140&&stage.y>=0,'Character must remain visible');
      assert(await page.locator('#log').evaluate(e=>e.clientHeight)>80,'Chat must have usable space');
    }
    await page.setViewportSize({width:390,height:780});
    await page.screenshot({path:path.join(out,'android-chat.png')});
    await page.locator('#txt').fill('今天学习很累');
    assert.equal(await page.locator('.stagewrap').isVisible(),false);
    await page.locator('#sendBtn').click();
    await page.waitForFunction(()=>!busy&&history.length>1);
    assert.match(await page.locator('#log').innerText(),/一点休息/);
    await page.waitForFunction(()=>document.querySelector('#stopVoiceBtn').hidden===false);
    await page.locator('#stopVoiceBtn').click();
    assert.equal(await page.evaluate(()=>voiceOn),true,'Stopping one reply must not disable future read-aloud');
    await page.locator('#txt').fill('未发的草稿');await page.locator('#micBtn').click();
    await page.evaluate(()=>{
      __xinghuoNativeEvent({kind:'recognition',id:activeRecognition,type:'result',text:'补充一句'});
      __xinghuoNativeEvent({kind:'recognition',id:activeRecognition,type:'end'});
    });
    assert.equal(await page.locator('#txt').inputValue(),'未发的草稿\n补充一句');
    await page.getByRole('button',{name:'思政闯关',exact:true}).click();await page.waitForSelector('.stage-card');
    assert.equal(await page.locator('.stage-card').count(),3);
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.screenshot({path:path.join(out,'android-game.png'),fullPage:true});
    await page.locator('.stage-card').first().click();
    await page.locator('.answer').first().click();
    assert(await page.locator('#feedback').isVisible());
    await page.reload();await page.waitForSelector('.stage-card');
    await page.locator('.stage-card').first().click();
    assert.notEqual(await page.locator('#feedback').innerText(),'');
    await page.getByRole('button',{name:'返回陪伴对话'}).click();await page.waitForFunction(()=>typeof preferencesReady!=="undefined");await page.evaluate(()=>preferencesReady);
    assert.equal(await page.locator('#txt').inputValue(),'未发的草稿\n补充一句');
    assert.match(await page.locator('#log').innerText(),/一点休息/);
    await page.reload();await page.waitForFunction(()=>typeof preferencesReady!=="undefined");await page.evaluate(()=>preferencesReady);
    assert.equal(await page.locator('#txt').inputValue(),'未发的草稿\n补充一句');
    await page.locator('#micBtn').click();
    await page.evaluate(()=>{
      __xinghuoNativeEvent({kind:'recognition',id:activeRecognition,type:'error',text:'service-not-allowed'});
      __xinghuoNativeEvent({kind:'recognition',id:activeRecognition,type:'end'});
    });
    assert.match(await page.locator('#composerNote').innerText(),/没有可用的语音识别/);
    await page.getByRole('button',{name:'对话说明',exact:true}).click();
    await page.getByRole('link',{name:'开源组件说明'}).click();assert.match(page.url(),/licenses.html$/);
    await page.getByRole('link',{name:'返回星火同行'}).click();await page.waitForFunction(()=>typeof openSite==='function');
    await page.evaluate(()=>openSite('news'));
    assert.match(await page.evaluate(()=>nativeCalls.find(x=>x[0]==='open')[1]),/moe.gov.cn/);
    await page.setViewportSize({width:780,height:360});
    const button=await page.locator('#sendBtn').boundingBox();assert(button.y+button.height<=360);
    assert.deepEqual(errors,[]);
    console.log('PASS: 3 portrait sizes, landscape, embedded animation, automatic voice, stop, Android microphone bridge, saved chat/draft/quiz, external links, licenses');
    await ctx.close();
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

/* 랭킹 보드 점검 — 등록 · 랭킹 집계 · 자기 재발행이 고정점인지 확인 */
const path=require('path'),fs=require('fs'),{chromium}=require('playwright');
const FILE='file://'+path.join(__dirname,'..','board.html');
(async()=>{
  const b=await chromium.launch({args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--single-process']});
  const p=await b.newPage({viewport:{width:1100,height:900},colorScheme:'dark'});
  const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  /* 뷰어가 없는 로컬 파일이라 claude.use 를 흉내내서 publish 를 가로챈다 */
  await p.addInitScript(()=>{
    window.__published=[];
    window.claude={use:async n=>n!=="artifact"?null:{
      publish:async html=>{ window.__published.push(html); return {version:"v"+window.__published.length}; }
    }};
  });
  await p.goto(FILE,{waitUntil:'load'});
  await p.waitForTimeout(600);
  console.log("쓰기 가능 화면:", await p.evaluate(()=>!document.getElementById('regCard').hidden));

  const reg=async(n,g,cp,st,job)=>{
    await p.fill('#fName',n); await p.fill('#fGuild',g); await p.fill('#fCp',cp); await p.fill('#fStage',st);
    await p.click(`#jobPick .jb[data-id="${job}"]`);
    await p.click('#btnSave'); await p.waitForTimeout(120);
  };
  await reg('유리','달빛','2.4경','36-7','bishop');
  console.log("1회 등록 후 publish 호출:", await p.evaluate(()=>window.__published.length));

  /* 발행된 문서를 그대로 다시 띄워서 누적되는지 + 고정점인지 확인 */
  let doc=await p.evaluate(()=>window.__published[window.__published.length-1]);
  console.log("문서 시작:", JSON.stringify(doc.slice(0,15)), "· 길이", Math.round(doc.length/1024)+"KB");
  for(const [n,g,cp,st,job] of [['하진','달빛','1.8경','36-4','captain'],
                                ['민수','','3.1경','37-2','viper'],
                                ['수아','새벽','2.9경','36-9','night-lord']]){
    await p.setContent(doc,{waitUntil:'load'}); await p.waitForTimeout(400);
    await reg(n,g,cp,st,job);
    doc=await p.evaluate(()=>window.__published[window.__published.length-1]);
  }
  await p.setContent(doc,{waitUntil:'load'}); await p.waitForTimeout(500);
  console.log("\n--- 전투력 랭킹 ---");
  console.log(await p.$$eval('#cpBody tr',rs=>rs.map(r=>r.innerText.replace(/\s+/g,' ').trim()).join('\n')));
  await p.click('#tabs .tab[data-t="guild"]'); await p.waitForTimeout(120);
  console.log("\n--- 길드 랭킹 ---");
  console.log(await p.$$eval('#gBody tr',rs=>rs.map(r=>r.innerText.replace(/\s+/g,' ').trim()).join('\n')));
  await p.click('#tabs .tab[data-t="pop"]'); await p.waitForTimeout(120);
  console.log("\n--- 인기도 ---");
  console.log(await p.$eval('#popJob',e=>e.innerText.replace(/\n+/g,' | ')));
  console.log(await p.$eval('#popFam',e=>e.innerText.replace(/\n+/g,' | ')));
  console.log(await p.$eval('#popCh',e=>e.innerText.replace(/\n+/g,' | ')));

  /* 고정점: 4세대 문서가 심고 있는 템플릿 base64 가 1세대와 같아야 한다 */
  const b1=fs.readFileSync(path.join(__dirname,'..','board.html'),'utf8')
            .match(/id="shell" type="text\/plain">([^<]+)</)[1].trim();
  const b4=doc.match(/id="shell" type="text\/plain">([^<]+)</)[1].trim();
  console.log("\n템플릿 고정점 유지:", b1===b4, "· 문서", Math.round(doc.length/1024)+"KB");
  console.log("보드 인원:", await p.evaluate(()=>JSON.parse(document.getElementById('state').textContent).board.length));
  console.log("에러:", errs.length?errs:"없음");
  await p.screenshot({path:'/tmp/claude-1000/-home-yuri/25980c99-ec0f-4a52-9d03-2de4b2b7330f/scratchpad/board.png',fullPage:true});
  await b.close();
})().catch(e=>{console.error('ERR',e.message.slice(0,400));process.exit(1)});

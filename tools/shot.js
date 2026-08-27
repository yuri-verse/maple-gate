/* 페이지를 실제로 렌더해서 PNG 로 뽑는다.
   사용: node tools/shot.js <탭> <테마> <출력경로> [폭] */
const path=require('path'), {chromium}=require('playwright');
const tab=process.argv[2]||'home', theme=process.argv[3]||'dark';
const out=process.argv[4]||path.join(__dirname,'..','shots',tab+'-'+theme+'.png');
const W=parseInt(process.argv[5]||'1280',10);
const FILE='file://'+path.join(__dirname,'..','index.html');
(async()=>{
  const b=await chromium.launch({args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--single-process']});
  const p=await b.newPage({viewport:{width:W,height:900},deviceScaleFactor:1,
    colorScheme: theme==='light'?'light':'dark'});
  await p.goto(FILE,{waitUntil:'load'});
  await p.waitForTimeout(900);
  await p.evaluate(()=>{ const b=document.getElementById('fillTypical'); if(b) b.click(); });
  await p.waitForTimeout(1200);
  await p.evaluate(t=>{ const b=document.querySelector('#tabs .tab[data-tab="'+t+'"]'); if(b) b.click(); }, tab);
  await p.waitForTimeout(800);
  require('fs').mkdirSync(path.dirname(out),{recursive:true});
  await p.screenshot({path:out,fullPage:true});
  console.log(out,'· 높이',await p.evaluate(()=>document.documentElement.scrollHeight)+'px');
  await b.close();
})().catch(e=>{console.error('ERR',e.message.slice(0,300));process.exit(1)});

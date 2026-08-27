const path=require('path');
const PAGE=process.argv[2]||path.join(__dirname,'..','index.html');
const fs=require('fs'), {JSDOM,VirtualConsole}=require('jsdom');
const vc=new VirtualConsole(); vc.on("jsdomError",e=>console.log("ERR:",e.message));
const dom=new JSDOM(fs.readFileSync(PAGE,'utf8'),
  {runScripts:"dangerously",pretendToBeVisual:true,url:"http://localhost/",virtualConsole:vc});
const w=dom.window,d=w.document;
const $=s=>d.querySelector(s),$$=s=>[].slice.call(d.querySelectorAll(s));
setTimeout(()=>{
  $("#fillTypical").click();
  const setR=r=>{const e=$("#rIn"); e.value=r; e.dispatchEvent(new w.Event("input",{bubbles:true}));};
  const pick=id=>{
    const q=$("#q"); q.value=id; q.dispatchEvent(new w.Event("input",{bubbles:true}));
    const b=$$("#list .sitem").find(x=>x.querySelector(".sid").textContent===id
             && x.querySelector(".mtag").textContent==="돌파");
    if(b) b.click(); return !!b;
  };
  const ratio=()=>{
    const t=$("#verdict").textContent.replace(/\s+/g," ");
    const m=t.match(/여유 배수 ×([\d.]+)/); return m?parseFloat(m[1]):NaN;
  };
  const prob=()=>{const m=$("#verdict").textContent.replace(/\s+/g," ").match(/클리어 확률 ([\d.]+)%/);return m?parseFloat(m[1]):NaN;};
  console.log("현재 R 기본값:", $("#rIn").value);
  console.log("\n스테이지  R=1.00   R=1.50   R=2.00   R=2.50   필요R(배수1.0)");
  ["36-5","36-6","36-7","36-8","36-9"].forEach(id=>{
    if(!pick(id)) { console.log(id,"없음"); return; }
    const at=r=>{setR(r);return ratio();};
    const vals=[1,1.5,2,2.5].map(at);
    let lo=0.1,hi=40;
    if(at(hi)<1){ console.log(`${id}    ${vals.map(v=>v.toFixed(2)).join("     ")}   >40`); return; }
    for(let i=0;i<40;i++){const m=(lo+hi)/2; if(at(m)>=1) hi=m; else lo=m;}
    console.log(`${id}    ${vals.map(v=>v.toFixed(2)).join("     ")}   ${hi.toFixed(2)}`);
  });
  const DR=parseFloat($("#rIn").getAttribute("value"));
  console.log("\n--- 기본 R="+DR+" 에서의 판정 ---");
  ["36-4","36-5","36-6","36-7","36-8","36-9","36-10"].forEach(id=>{
    if(!pick(id))return; setR(DR);
    console.log(`  ${id}  배수 ×${ratio().toFixed(2)}  확률 ${prob()}%`);
  });
  process.exit(0);
},1500);

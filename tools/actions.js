/* 우선순위 카드 점검 — 직업 버튼과 '지금 뭘 바꾸면 되나' 목록을 DOM 으로 찍어 본다. */
const path=require('path'),fs=require('fs'),{JSDOM,VirtualConsole}=require('jsdom');
const PAGE=process.argv[2]||path.join(__dirname,'..','index.html');
const vc=new VirtualConsole(); vc.on("jsdomError",e=>console.log("ERR:",e.message));
const dom=new JSDOM(fs.readFileSync(PAGE,'utf8'),
  {runScripts:"dangerously",pretendToBeVisual:true,url:"http://localhost/",virtualConsole:vc});
const w=dom.window,d=w.document,$=s=>d.querySelector(s),$$=s=>[].slice.call(d.querySelectorAll(s));
setTimeout(()=>{
  $("#fillTypical").click();
  const pick=id=>{const q=$("#q");q.value=id;q.dispatchEvent(new w.Event("input",{bubbles:true}));
    const b=$$("#list .sitem").find(x=>x.querySelector(".sid").textContent===id
             &&x.querySelector(".mtag").textContent==="돌파");
    if(b)b.click(); return !!b;};
  console.log("직업 버튼:",$$("#jobGrid .jobbtn").length,
    "· 초상화",$$("#jobGrid .jobbtn img").length,"· 글리프",$$("#jobGrid .jobbtn svg").length);
  console.log("동료 그리드:",$$("#supGrid .jobbtn").length,
    "· 초상화",$$("#supGrid img").length,"· 등급",$$("#gradeSegs .seg").length,
    "· 슬롯",$$("#supSlots .supslot").length);
  $$("#supSlots .supslot").forEach(b=>console.log("   "+b.title));
  /* 등급을 낮추면 레벨 상한이 따라 내려가는지 (레전드리 16 -> 유니크 10) */
  const gseg=g=>$$("#gradeSegs .seg").find(x=>x.dataset.g===g);
  const before=$("#supLv").max;
  if(gseg("유니크")&&!gseg("유니크").disabled){
    gseg("유니크").click();
    console.log("   등급 유니크로: 레벨 상한 "+before+" -> "+$("#supLv").max+
                " · 슬롯 "+$$("#supSlots .supslot")[0].title);
    if(gseg("레전드리")&&!gseg("레전드리").disabled) gseg("레전드리").click();
  }
  (process.argv[3]?[process.argv[3]]:["36-6","36-8"]).forEach(id=>{
    if(!pick(id)) return console.log("\n"+id,"없음");
    console.log("\n=== "+id+" ===");
    console.log(" "+$("#probV").textContent+"  "+$("#rMark").textContent+"   ("+$("#actHint").textContent+")");
    console.log(" "+$("#rWhy").textContent);
    $$("#actList .actrow").forEach(r=>{
      const nm=[].slice.call(r.querySelectorAll(".an span")).map(s=>s.textContent).join("  ");
      console.log("  "+r.querySelector(".rk").textContent+". "+nm+"   "+r.querySelector(".ap").textContent);
      console.log("     "+r.querySelector(".ad").textContent);
    });
    $$("#actList .actempty").forEach(e=>console.log("  · "+e.textContent));
  });
  const t=Date.now(); $("#supLv").dispatchEvent(new w.Event("input",{bubbles:true}));
  console.log("\n재계산 "+(Date.now()-t)+"ms");
  process.exit(0);
},1500);

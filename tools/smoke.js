const path=require('path');
const PAGE=process.argv[2]||path.join(__dirname,'..','index.html');
const fs=require('fs'), {JSDOM,VirtualConsole}=require('jsdom');
const vc=new VirtualConsole();
vc.on("jsdomError",e=>console.log("JSDOM ERROR:",e.message));
const dom=new JSDOM(fs.readFileSync(PAGE,'utf8'),
  {runScripts:"dangerously",pretendToBeVisual:true,url:"http://localhost/",virtualConsole:vc});
const w=dom.window, d=w.document;
const $=s=>d.querySelector(s), $$=s=>[].slice.call(d.querySelectorAll(s));
setTimeout(()=>{
  $("#fillTypical").click();
  // 36-8 스테이지 선택
  const q=$("#q"); q.value="36-8"; q.dispatchEvent(new w.Event("input",{bubbles:true}));
  const items=$$("#list .sitem");
  console.log("검색 결과:", items.map(b=>b.querySelector(".sid").textContent+"/"+b.querySelector(".mtag").textContent).join(", "));
  const pick=items.find(b=>b.querySelector(".mtag").textContent==="돌파")||items[0];
  if(pick) pick.click();
  const T=id=>{const e=d.getElementById(id);return e?e.textContent.trim().replace(/\s+/g," "):"(없음)";};
  const rows=id=>$$("#"+id+" tr").map(tr=>[].slice.call(tr.children).map(td=>td.textContent.trim().replace(/\s+/g," ")));
  console.log("\n선택 :", T("stId"), "|", T("stSub"));
  console.log("판정 :", T("verdict").slice(0,150));
  console.log("전투력:", T("cpFull"),"| 유효",T("cpEff"),"| 뻥투력",T("cpDead"));
  console.log("\n--- 올릴 능력치 ---");
  rows("upList").forEach(r=>console.log("   "+r.join("  |  ")));
  console.log("\n--- 버려도 되는 능력치 ---");
  rows("downList").forEach(r=>console.log("   "+r.join("  |  ")));
  console.log("\n--- 요약 ---");
  $$("#swapNote .note").forEach(n=>console.log("   * "+n.textContent.trim()));
  const a=T("verdict"); $("#supLv").dispatchEvent(new w.Event("input",{bubbles:true}));
  console.log("\n재계산 결정적:", a===T("verdict"));
  process.exit(0);
},1500);

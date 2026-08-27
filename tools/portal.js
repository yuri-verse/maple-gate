/* 포털 점검 — 탭 · 홈 랭킹 · 도감 · 계산기가 실제로 채워지는지 DOM 으로 확인 */
const path=require('path'),fs=require('fs'),{JSDOM,VirtualConsole}=require('jsdom');
const PAGE=process.argv[2]||path.join(__dirname,'..','index.html');
let errs=[]; const vc=new VirtualConsole();
vc.on("jsdomError",e=>{ if(!/Not implemented/.test(e.message)) errs.push(e.message); });
const dom=new JSDOM(fs.readFileSync(PAGE,'utf8'),
  {runScripts:"dangerously",pretendToBeVisual:true,url:"http://localhost/",virtualConsole:vc});
const w=dom.window,d=w.document,$=s=>d.querySelector(s),$$=s=>[].slice.call(d.querySelectorAll(s));
const T=id=>{const e=d.getElementById(id);return e?e.textContent.trim().replace(/\s+/g," "):"(없음)";};
setTimeout(()=>{
  console.log("탭:",$$("#tabs .tab").map(b=>b.dataset.tab).join(" · "));
  console.log("패널 표시:",["home","stage","sup","mon","enh"].map(k=>k+"="+(!$("#p-"+k).hidden)).join(" "));
  console.log("\n--- 스탯 입력 전 ---");
  console.log(" 내 진행:", T("progBody").slice(0,90));
  console.log(" 동료 티어:", T("tierList").slice(0,70));
  console.log(" 빡센 돌파:", $$("#hardList .rrow").length+"행 ·", T("hardList").slice(0,80));

  $("#fillTypical").click();
  console.log("\n--- 예시 스탯 후 ---");
  console.log(" 내 진행:", T("progHint"), "|", T("progBody").slice(0,120));
  console.log(" 진행 행:", $$("#progBody .progrow").map(r=>r.textContent.trim().replace(/\s+/g," ")).join(" / "));
  console.log(" 동료 티어(", T("tierWhere"), "):");
  $$("#tierList .rrow").forEach(r=>console.log("    "+r.textContent.trim().replace(/\s+/g," ")));
  console.log(" 직업 랭킹:");
  $$("#jobRank .rrow").forEach(r=>console.log("    "+r.textContent.trim().replace(/\s+/g," ")));

  console.log("\n--- 검색 ---");
  const gq=$("#gq");
  ["36-8","zakum","비숍"].forEach(q=>{
    gq.value=q; gq.dispatchEvent(new w.Event("input",{bubbles:true}));
    console.log("  '"+q+"' →", $$("#gqOut .qrow").map(b=>b.querySelector(".qkind").textContent
      +":"+b.querySelector(".qn").textContent).slice(0,4).join(", ")||"(없음)");
  });

  console.log("\n--- 동료 도감 ---");
  $$("#tabs .tab").find(b=>b.dataset.tab==="sup").click();
  console.log(" 행", $$("#supDex .sdrow").length, "|", T("supDexHint"));
  $$("#supDex .sdrow").slice(0,3).forEach(r=>console.log("    "+r.textContent.trim().replace(/\s+/g," ").slice(0,110)));

  console.log("\n--- 몬스터 도감 ---");
  console.log(" ", T("monHint"), "| 행", $$("#monBody tr").length, "|", T("monCount"));
  $$("#monBody tr").slice(0,3).forEach(r=>console.log("    "+r.textContent.trim().replace(/\s+/g," ")));
  console.log(" 초상화 있는 행:", $$("#monBody img").length);
  const kb=$$("#monKind .seg").find(b=>b.dataset.k==="boss"); kb.click();
  console.log(" 보스만:", T("monCount"));

  console.log("\n--- 강화 ---");
  console.log(" 스타포스:", T("sfOut").slice(0,160));
  console.log(" 큐브:", T("cbOut").slice(0,140));
  console.log(" 스타포스 표", $$("#recStar tr").length, "행 · 큐브 표", $$("#recCube tr").length, "행");
  console.log(" 유물 카드:", $$("#artDex .artcard").length, "· 아이콘", $$("#artDex img").length);
  console.log("   예:", $$("#artDex .artcard")[0].textContent.trim().replace(/\s+/g," "));

  const t0=Date.now();
  $$("#tabs .tab").find(b=>b.dataset.tab==="home").click();
  console.log("\n홈 전체 재계산:", Date.now()-t0, "ms");
  console.log("\n--- 탭 이동 ---");
  $$("#tabs .tab").find(b=>b.dataset.tab==="stage").click();
  console.log(" 스테이지 탭:", T("stId"), "|", T("probV"), "|", T("meBar").replace(/\s+/g," "));
  console.log("\n에러:", errs.length?errs:"없음");
  process.exit(0);
},2500);

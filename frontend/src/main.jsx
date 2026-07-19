import React from 'react';
import { createRoot } from 'react-dom/client';
import { createPortal } from 'react-dom';
const ReactDOM = { createRoot, createPortal };
// 아래는 기존 app/web/index.html 의 인라인 스크립트 본문(무변경) + API 설정 한 줄만 env 화.

const {useState,useEffect,useMemo,useCallback,useRef} = React;
const UP="var(--up)",DOWN="var(--down)",INK="var(--ink)",MUTED="var(--muted)",TEAL="var(--teal)",LINE="var(--line)";
const GU_NAME={"43111":"상당구","43112":"서원구","43113":"흥덕구","43114":"청원구"};
const GU_FULL=c=>"청주시 "+(GU_NAME[c]||c);
const TYPE_LABEL={apartment:"아파트",officetel:"오피스텔",rowhouse:"빌라",detached:"단독·다가구"};
const DEAL_LABEL={trade:"매매",jeonse:"전세",wolse:"월세"};
const PY=3.305785;
function havM(la1,ln1,la2,ln2){const R=6371000,rd=Math.PI/180;
 const dla=(la2-la1)*rd,dln=(ln2-ln1)*rd;
 const a=Math.sin(dla/2)**2+Math.cos(la1*rd)*Math.cos(la2*rd)*Math.sin(dln/2)**2;
 return 2*R*Math.asin(Math.sqrt(a));}
const UnitCtx=React.createContext("m2");
const useUnit=()=>React.useContext(UnitCtx);
const fmtArea=(m2,unit)=>m2==null?"—":(unit==="py"?`${(m2/PY).toFixed(1)}평`:`${m2}㎡`);
const areaTxt=(a,unit)=>(a&&a.area!=null)?fmtArea(a.area,unit):((a&&a.label)||"—");  // 면적 라벨을 단위(평/㎡)에 맞게
const API=(import.meta.env&&import.meta.env.VITE_API_BASE)||"";
let AGG_MONTHS=12;  // 시세 집계 윈도우(개월) — /config 에서 갱신
let FEATURES={ads:false,monetization:false,billing:false};  // 수익화 피처 플래그(부록B) — /config 의 feature_flags 로 갱신. 기본 OFF=현재와 동일.
const _mem={};
const safeStore={get(k){try{return localStorage.getItem(k);}catch(e){return _mem[k]??null;}},set(k,v){try{localStorage.setItem(k,v);}catch(e){_mem[k]=v;}}};
function deviceId(){let id=safeStore.get("cj_device");if(!id){id="dev_"+Math.random().toString(36).slice(2)+Date.now().toString(36);safeStore.set("cj_device",id);}return id;}
function getToken(){return safeStore.get("cj_token")||"";}
function setToken(t){safeStore.set("cj_token",t||"");}
function authHeader(){const t=getToken();return t?{Authorization:`Bearer ${t}`}:{};}
async function pushVapid(){try{return await fetch(`${API}/push/vapid`).then(r=>r.json());}catch(e){return {enabled:false};}}
function _b64ToU8(s){const pad="=".repeat((4-s.length%4)%4);const b=(s+pad).replace(/-/g,"+").replace(/_/g,"/");const raw=atob(b);const arr=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)arr[i]=raw.charCodeAt(i);return arr;}
async function pushIsOn(){try{if(!("serviceWorker" in navigator))return false;const reg=await navigator.serviceWorker.getRegistration();const sub=reg&&await reg.pushManager.getSubscription();return !!sub;}catch(e){return false;}}
async function enablePush(){
 if(!(("serviceWorker" in navigator)&&("PushManager" in window)&&("Notification" in window)))throw new Error("이 브라우저는 푸시를 지원하지 않아요.");
 const v=await pushVapid();
 if(!v.enabled||!v.publicKey)throw new Error("서버에 푸시 키가 아직 설정되지 않았어요(VAPID).");
 const perm=await Notification.requestPermission();
 if(perm!=="granted")throw new Error("알림 권한이 허용되지 않았어요.");
 const reg=await navigator.serviceWorker.register("/sw.js");
 await navigator.serviceWorker.ready;
 let sub=await reg.pushManager.getSubscription();
 if(!sub)sub=await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:_b64ToU8(v.publicKey)});
 const r=await fetch(`${API}/push/subscribe`,{method:"POST",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify({device_id:deviceId(),subscription:sub.toJSON(),user_agent:navigator.userAgent})}).then(r=>r.json());
 if(!r||!r.ok)throw new Error("구독 저장에 실패했어요.");
 return r;
}
async function disablePush(){try{const reg=await navigator.serviceWorker.getRegistration();const sub=reg&&await reg.pushManager.getSubscription();if(sub){await fetch(`${API}/push/unsubscribe`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({endpoint:sub.endpoint})}).catch(()=>{});await sub.unsubscribe();}}catch(e){}}
const LOAN_PROFILE_KEY="cj_loan_profile";
function loadLoanProfile(){try{const v=safeStore.get(LOAN_PROFILE_KEY);return v?JSON.parse(v):null;}catch(e){return null;}}
function saveLoanProfile(p){try{safeStore.set(LOAN_PROFILE_KEY,JSON.stringify(p));}catch(e){}}
function clearLoanProfile(){try{safeStore.set(LOAN_PROFILE_KEY,"");}catch(e){}}
const favId=it=>`${it.complex_name||it.name||""}__${it.lawd_cd||""}__${it.property_type||""}`;

/* ---------- 데모 폴백 ---------- */
const DEMO_TX=[
 {lawd_cd:"43113",property_type:"apartment",deal_type:"trade",complex_name:"샘플센트럴파크",dong:"가경동",exclusive_area:101.2,floor:22,contract_date:"2025-11-13",deal_amount:44500,is_sample:true},
 {lawd_cd:"43113",property_type:"apartment",deal_type:"trade",complex_name:"샘플리버뷰",dong:"복대동",exclusive_area:84.9,floor:15,contract_date:"2025-11-12",deal_amount:34880,is_sample:true},
 {lawd_cd:"43113",property_type:"apartment",deal_type:"trade",complex_name:"샘플리버뷰",dong:"복대동",exclusive_area:84.97,floor:8,contract_date:"2025-10-20",deal_amount:35200,trade_method:"direct",is_sample:true},
 {lawd_cd:"43113",property_type:"apartment",deal_type:"trade",complex_name:"샘플리버뷰",dong:"복대동",exclusive_area:84.9,floor:20,contract_date:"2025-09-28",deal_amount:35600,corrected_at:"2025-12-01",is_sample:true},
 {lawd_cd:"43113",property_type:"apartment",deal_type:"trade",complex_name:"샘플리버뷰",dong:"복대동",exclusive_area:84.9,floor:3,contract_date:"2025-08-15",deal_amount:22000,trade_method:"direct",is_sample:true},
 {lawd_cd:"43113",property_type:"apartment",deal_type:"trade",complex_name:"샘플리버뷰",dong:"복대동",exclusive_area:84.9,floor:18,contract_date:"2025-10-30",deal_amount:36000,is_canceled:true,is_sample:true},
 {lawd_cd:"43111",property_type:"apartment",deal_type:"trade",complex_name:"샘플그린아파트",dong:"용암동",exclusive_area:84.97,floor:12,contract_date:"2025-11-05",deal_amount:31920,is_sample:true},
 {lawd_cd:"43112",property_type:"apartment",deal_type:"trade",complex_name:"샘플파크자이",dong:"분평동",exclusive_area:74.5,floor:18,contract_date:"2025-11-08",deal_amount:29840,is_sample:true},
 {lawd_cd:"43114",property_type:"apartment",deal_type:"trade",complex_name:"샘플숲속마을",dong:"내수읍",exclusive_area:59.8,floor:5,contract_date:"2025-11-04",deal_amount:27620,is_sample:true},
 {lawd_cd:"43113",property_type:"officetel",deal_type:"trade",complex_name:"샘플테크노폴리스",dong:"강서동",exclusive_area:29.7,floor:14,contract_date:"2025-11-11",deal_amount:12400,is_sample:true},
 {lawd_cd:"43114",property_type:"rowhouse",deal_type:"trade",complex_name:"샘플빌라",dong:"오창읍",exclusive_area:49.5,floor:3,contract_date:"2025-11-01",deal_amount:14200,is_sample:true},
 {lawd_cd:"43111",property_type:"detached",deal_type:"trade",complex_name:null,dong:"남일면",exclusive_area:112.3,floor:null,contract_date:"2025-09-14",deal_amount:26000,is_sample:true},
 {lawd_cd:"43113",property_type:"apartment",deal_type:"jeonse",complex_name:"샘플리버뷰",dong:"복대동",exclusive_area:59.92,floor:9,contract_date:"2025-11-03",deposit:23000,is_sample:true},
 {lawd_cd:"43113",property_type:"apartment",deal_type:"jeonse",complex_name:"샘플센트럴파크",dong:"가경동",exclusive_area:84.9,floor:11,contract_date:"2025-11-07",deposit:31000,is_sample:true},
 {lawd_cd:"43111",property_type:"apartment",deal_type:"jeonse",complex_name:"샘플그린아파트",dong:"용암동",exclusive_area:84.97,floor:7,contract_date:"2025-11-02",deposit:26500,is_sample:true},
 {lawd_cd:"43112",property_type:"apartment",deal_type:"jeonse",complex_name:"샘플파크자이",dong:"분평동",exclusive_area:74.5,floor:14,contract_date:"2025-10-29",deposit:24800,is_sample:true},
 {lawd_cd:"43114",property_type:"apartment",deal_type:"jeonse",complex_name:"샘플숲속마을",dong:"내수읍",exclusive_area:59.8,floor:3,contract_date:"2025-10-25",deposit:18500,is_sample:true},
 {lawd_cd:"43113",property_type:"officetel",deal_type:"jeonse",complex_name:"샘플테크노폴리스",dong:"강서동",exclusive_area:29.7,floor:8,contract_date:"2025-11-06",deposit:11000,is_sample:true},
 {lawd_cd:"43113",property_type:"apartment",deal_type:"wolse",complex_name:"샘플리버뷰",dong:"복대동",exclusive_area:59.92,floor:4,contract_date:"2025-11-09",deposit:5000,monthly_rent:65,is_sample:true},
 {lawd_cd:"43113",property_type:"apartment",deal_type:"wolse",complex_name:"샘플센트럴파크",dong:"가경동",exclusive_area:84.9,floor:6,contract_date:"2025-11-04",deposit:10000,monthly_rent:90,is_sample:true},
 {lawd_cd:"43111",property_type:"apartment",deal_type:"wolse",complex_name:"샘플그린아파트",dong:"용암동",exclusive_area:59.8,floor:2,contract_date:"2025-10-31",deposit:3000,monthly_rent:55,is_sample:true},
 {lawd_cd:"43113",property_type:"officetel",deal_type:"wolse",complex_name:"샘플테크노폴리스",dong:"강서동",exclusive_area:29.7,floor:10,contract_date:"2025-11-08",deposit:1000,monthly_rent:48,is_sample:true}
];
const mapTrade=(t,rank)=>({rank,complex_name:t.complex_name,gu:GU_FULL(t.lawd_cd),lawd_cd:t.lawd_cd,dong:t.dong,property_type:t.property_type,
 exclusive_area:t.exclusive_area,floor:t.floor,contract_date:t.contract_date,deal_amount:t.deal_amount,
 pyeong_unit:Math.round(t.deal_amount/(t.exclusive_area/PY)),is_sample:true});
const DEMO_ACTIVE=[
 {rank:1,code:"43111",name:"청주시 상당구",recent_count:2,total_count:6,recent_month:"2025-11"},
 {rank:2,code:"43113",name:"청주시 흥덕구",recent_count:1,total_count:4,recent_month:"2025-11"},
 {rank:3,code:"43112",name:"청주시 서원구",recent_count:1,total_count:4,recent_month:"2025-11"},
 {rank:4,code:"43114",name:"청주시 청원구",recent_count:1,total_count:4,recent_month:"2025-11"}];
const DEMO_MOVERS=[
 {rank:1,complex_name:"샘플그린아파트",gu:"청주시 상당구",change_pct:1.5,direction:"up",prev_amount:31240,latest_amount:31710,is_sample:true},
 {rank:2,complex_name:"샘플리버뷰",gu:"청주시 흥덕구",change_pct:1.0,direction:"up",prev_amount:34520,latest_amount:34880,is_sample:true},
 {rank:3,complex_name:"샘플숲속마을",gu:"청주시 청원구",change_pct:-0.2,direction:"down",prev_amount:27680,latest_amount:27620,is_sample:true}];
const DEMO_HIGH=[
 {complex_name:"샘플리버뷰",gu:"청주시 흥덕구",area_label:"중형 (60~85㎡)",latest_amount:34880,prev_high:34520,change_pct:1.0,month:"2025-11",is_sample:true},
 {complex_name:"샘플그린아파트",gu:"청주시 상당구",area_label:"중형 (60~85㎡)",latest_amount:31920,prev_high:31680,change_pct:0.8,month:"2025-11",is_sample:true}];
function demoRanking(type,band="all"){
 const bk=a=>a==null?null:(a<60?"small":a<85?"medium":"large");
 let base=DEMO_TX.filter(t=>t.deal_type==="trade"&&(type==="all"||t.property_type===type));
 if(band&&band!=="all")base=base.filter(t=>bk(t.exclusive_area)===band);
 return {property_type:type,area_band:band,
  top_trades:[...base].sort((a,b)=>b.deal_amount-a.deal_amount).map((t,i)=>mapTrade(t,i+1)),
  top_by_ppm:[...base].map(t=>({t,pp:Math.round(t.deal_amount/(t.exclusive_area/PY))})).sort((a,b)=>b.pp-a.pp).map((o,i)=>({...mapTrade(o.t,i+1),pyeong_unit:o.pp})),
  active_regions:DEMO_ACTIVE,top_movers:DEMO_MOVERS,newly_high:DEMO_HIGH,
  newly_low:[{complex_name:"샘플숲속마을",gu:"청주시 청원구",area_label:"소형 (~60㎡)",latest_amount:27620,prev_low:27680,change_pct:-0.2,month:"2025-11",is_sample:true}]};
}
function demoBoard(){
 const tr=DEMO_TX.filter(t=>t.deal_type==="trade"&&t.deal_amount);
 const gu_ranking=Object.keys(GU_NAME).map(code=>{
  const rs=tr.filter(t=>String(t.lawd_cd)===code);
  const amts=rs.map(r=>r.deal_amount).sort((a,b)=>a-b);
  const pys=rs.filter(r=>r.exclusive_area).map(r=>Math.round(r.deal_amount/(r.exclusive_area/PY))).sort((a,b)=>a-b);
  return {code,gu:GU_NAME[code],name:"청주시 "+GU_NAME[code],
   median_mae:amts.length?amts[Math.floor(amts.length/2)]:null,
   median_pyeong:pys.length?pys[Math.floor(pys.length/2)]:null,count:amts.length,month_count:rs.length,low_sample:amts.length<3};
 }).sort((a,b)=>(b.median_pyeong||0)-(a.median_pyeong||0));
 const bk=a=>a==null?null:(a<60?"s":a<85?"m":"l");
 const recent_by_gu=Object.keys(GU_NAME).map(code=>{
  const rs=tr.filter(t=>String(t.lawd_cd)===code);
  const gmax={}; rs.forEach(t=>{const k=(t.complex_name||"")+"|"+bk(t.exclusive_area);gmax[k]=gmax[k]||{max:0,n:0};gmax[k].max=Math.max(gmax[k].max,t.deal_amount);gmax[k].n++;});
  return {gu:GU_NAME[code],name:"청주시 "+GU_NAME[code],code,
   items:rs.slice().sort((a,b)=>(b.contract_date||"").localeCompare(a.contract_date||"")).slice(0,12)
    .sort((a,b)=>b.deal_amount-a.deal_amount).slice(0,4)
    .map(t=>{const g=gmax[(t.complex_name||"")+"|"+bk(t.exclusive_area)];
     return {complex_name:t.complex_name,lawd_cd:t.lawd_cd,property_type:t.property_type,dong:t.dong,exclusive_area:t.exclusive_area,floor:t.floor,contract_date:t.contract_date,deal_amount:t.deal_amount,is_high:!!t.complex_name&&g.n>=2&&t.deal_amount>=g.max,is_sample:true};})};
 });
 const months=["2025-06","2025-07","2025-08","2025-09","2025-10","2025-11"];
 const guSeries=Object.keys(GU_NAME).map(code=>{
  const base={43111:31900,43112:30200,43113:34200,43114:27600}[code];
  return {code,name:"청주시 "+GU_NAME[code],values:months.map((m,i)=>Math.round(base*(1+i*0.004)))};});
 const order={}; gu_ranking.forEach((g,i)=>order[g.code]=i);
 recent_by_gu.sort((a,b)=>(order[a.code]??9)-(order[b.code]??9));
 guSeries.sort((a,b)=>(order[a.code]??9)-(order[b.code]??9));
 const med=a=>{const s=[...a].sort((x,y)=>x-y);return s.length?s[Math.floor((s.length-1)/2)]:null;};
 const lmG={}; tr.forEach(t=>{if(!t.complex_name)return;const k=t.complex_name+"|"+t.lawd_cd;(lmG[k]=lmG[k]||[]).push(t);});
 const landmark=Object.values(lmG).map(rs=>{
  const ppms=rs.filter(r=>r.exclusive_area).map(r=>Math.round(r.deal_amount/(r.exclusive_area/PY)));
  const areas=rs.filter(r=>r.exclusive_area).map(r=>r.exclusive_area);
  return {name:rs[0].complex_name,code:rs[0].lawd_cd,gu:GU_NAME[rs[0].lawd_cd],dong:rs[0].dong,
   price:med(rs.map(r=>r.deal_amount)),ppm:ppms.length?med(ppms):null,area:areas.length?areas[0]:null,count:rs.length,is_sample:true};
 }).sort((a,b)=>b.price-a.price).slice(0,5).map((a,i)=>({...a,rank:i+1}));
 const BANDS=[["small","소형 (~60㎡)"],["medium","중형 (60~85㎡)"],["large","대형 (85㎡~)"]];
 const bandOf=a=>a==null?null:(a<60?"small":a<85?"medium":"large");
 const landmark_by_band=BANDS.map(([k,label])=>{
  const g={}; tr.filter(t=>t.complex_name&&bandOf(t.exclusive_area)===k).forEach(t=>{const key=t.complex_name+"|"+t.lawd_cd;(g[key]=g[key]||[]).push(t);});
  const items=Object.values(g).map(rs=>{
   const ppms=rs.filter(r=>r.exclusive_area).map(r=>Math.round(r.deal_amount/(r.exclusive_area/PY)));
   const areas=rs.filter(r=>r.exclusive_area).map(r=>r.exclusive_area);
   return {name:rs[0].complex_name,code:rs[0].lawd_cd,gu:GU_NAME[rs[0].lawd_cd],dong:rs[0].dong,
    price:med(rs.map(r=>r.deal_amount)),ppm:ppms.length?med(ppms):null,area:areas.length?areas[0]:null,count:rs.length,is_sample:true};
  }).sort((a,b)=>b.price-a.price).slice(0,5).map((a,i)=>({...a,rank:i+1}));
  return {key:k,label,items};
 });
 const recent_by_band=BANDS.map(([k,label])=>{
  const rs=tr.filter(t=>bandOf(t.exclusive_area)===k);
  const gmax={}; rs.forEach(t=>{const key=(t.complex_name||"")+"|"+bandOf(t.exclusive_area);gmax[key]=gmax[key]||{max:0,n:0};gmax[key].max=Math.max(gmax[key].max,t.deal_amount);gmax[key].n++;});
  const items=rs.slice().sort((a,b)=>(b.contract_date||"").localeCompare(a.contract_date||"")).slice(0,30)
   .sort((a,b)=>b.deal_amount-a.deal_amount).slice(0,5)
   .map(t=>{const g=gmax[(t.complex_name||"")+"|"+bandOf(t.exclusive_area)];
    return {complex_name:t.complex_name,lawd_cd:t.lawd_cd,gu:GU_NAME[t.lawd_cd],property_type:t.property_type,dong:t.dong,exclusive_area:t.exclusive_area,floor:t.floor,contract_date:t.contract_date,deal_amount:t.deal_amount,is_high:!!t.complex_name&&g.n>=2&&t.deal_amount>=g.max,is_sample:true};});
  return {key:k,label,items};
 });
 const demoTrending={basis:"surge",items:Object.values(lmG).map(rs=>{
   const rc=rs.length,pc=Math.max(0,Math.floor(rc/2));
   return {name:rs[0].complex_name,lawd_cd:rs[0].lawd_cd,gu:GU_NAME[rs[0].lawd_cd],dong:rs[0].dong,property_type:rs[0].property_type,
    recent_count:rc,prev_count:pc,delta:rc-pc,price:med(rs.map(r=>r.deal_amount)),contains_sample_data:true};
  }).sort((a,b)=>(b.delta-a.delta)||(b.recent_count-a.recent_count)).slice(0,8).map((o,i)=>({...o,rank:i+1}))};
 const _mv=Object.values(lmG).map(rs=>{
   const s=rs.filter(r=>r.deal_type==="trade"&&r.deal_amount).slice().sort((a,b)=>(a.contract_date||"").localeCompare(b.contract_date||""));
   if(s.length<2)return null; const prev=s[s.length-2],latest=s[s.length-1], change=latest.deal_amount-prev.deal_amount;
   if(!change)return null;
   return {name:latest.complex_name,area_py:latest.exclusive_area?Math.round(latest.exclusive_area/PY):null,lawd_cd:latest.lawd_cd,
    gu:GU_NAME[latest.lawd_cd],dong:latest.dong,prev_amount:prev.deal_amount,latest_amount:latest.deal_amount,
    change,pct:Math.round(change/prev.deal_amount*1000)/10,contains_sample_data:true};
  }).filter(Boolean);
 const _S=(n,py,code,dong,pv,lt)=>({name:n,area_py:py,lawd_cd:code,gu:GU_NAME[code],dong,prev_amount:pv,latest_amount:lt,change:lt-pv,pct:Math.round((lt-pv)/pv*1000)/10,contains_sample_data:true});
 const _up=[..._mv.filter(x=>x.change>0),_S("샘플센트럴파크",34,"43113","복대동",41000,44500),_S("샘플그린아파트",25,"43111","용암동",30500,31920),_S("샘플파크자이",32,"43112","산남동",27900,29840)];
 const _dn=[..._mv.filter(x=>x.change<0),_S("샘플숲속마을",18,"43114","오창",28800,27620),_S("샘플빌라",17,"43111","용암동",15000,14200)];
 const _dedupe=a=>{const seen={};return a.filter(x=>{const k=x.name+x.area_py;if(seen[k])return false;seen[k]=1;return true;});};
 const demoMovers={up:_dedupe(_up).sort((a,b)=>b.pct-a.pct).map((o,i)=>({...o,rank:i+1})),
  down:_dedupe(_dn).sort((a,b)=>a.pct-b.pct).map((o,i)=>({...o,rank:i+1}))};
 return {city_trend:{months,values:[33600,33850,34100,34050,34400,34880],contains_sample_data:true},
  city:(()=>{const ta=tr.map(t=>t.deal_amount);const je=DEMO_TX.filter(t=>t.deal_type==="jeonse"&&t.deposit).map(t=>t.deposit);
   const mean=a=>a.length?Math.round(a.reduce((s,x)=>s+x,0)/a.length):null;
   return {as_of:"2025-11",avg_mae:mean(ta),avg_jeon:mean(je),mae_dM:0.4,mae_dY:2.1,
    insufficient:{dM:false,dY:false},trade_count:ta.length};})(),
  property_type:"apartment",landmark,landmark_by_band,recent_by_band,trending:demoTrending,top_movers:demoMovers,
  gu_trend:{months,series:guSeries,contains_sample_data:true},gu_ranking,recent_by_gu,
  gu_order:gu_ranking.map(g=>g.code),
  volume:{month:"2025-11",count:5,prev_count:5,dM:0},contains_sample_data:true};
}
function demoHeatmap(type){
 const CENT={"43111":[36.6285,127.5060],"43112":[36.6005,127.4760],"43113":[36.6360,127.4280],"43114":[36.6720,127.4880]};
 const base=DEMO_TX.filter(t=>t.deal_type==="trade"&&t.deal_amount&&t.exclusive_area&&t.complex_name&&(type==="all"||t.property_type===type));
 const g={}; base.forEach(t=>{(g[t.complex_name]=g[t.complex_name]||[]).push(t);});
 const pts=Object.keys(g).map(name=>{const rs=g[name];const pys=rs.map(r=>Math.round(r.deal_amount/(r.exclusive_area/PY))).sort((a,b)=>a-b);
  return {complex_name:name,lawd_cd:rs[0].lawd_cd,gu:GU_FULL(rs[0].lawd_cd),dong:rs[0].dong,property_type:rs[0].property_type,
   lat:null,lng:null,median_pyeong:pys[Math.floor(pys.length/2)],count:rs.length};});
 const vals=pts.map(p=>p.median_pyeong);
 const gg={}; base.forEach(t=>{const v=Math.round(t.deal_amount/(t.exclusive_area/PY));(gg[t.lawd_cd]=gg[t.lawd_cd]||[]).push(v);});
 const districts=Object.keys(gg).filter(c=>CENT[c]).map(c=>{const ar=gg[c].slice().sort((a,b)=>a-b);
  return {lawd_cd:c,gu:GU_FULL(c),lat:CENT[c][0],lng:CENT[c][1],median_pyeong:ar[Math.floor(ar.length/2)],count:ar.length,level:"district"};}).sort((a,b)=>b.median_pyeong-a.median_pyeong);
 const dvals=districts.map(d=>d.median_pyeong);
 return {points:pts,districts,
  district_min:dvals.length?Math.min(...dvals):null,district_max:dvals.length?Math.max(...dvals):null,
  min_pyeong:vals.length?Math.min(...vals):null,max_pyeong:vals.length?Math.max(...vals):null,total:pts.length};
}
const DEMO_FEED={pulse:{property_type:"apartment",median_pyeong:1207,median_pyeong_medium:1207,count:18,
  volume:{month:"2025-11",count:5,prev_count:5,dM:0},active_top:DEMO_ACTIVE[0]},
 data_pending:true,notice:"청약·분양·뉴스·정책은 준비중입니다. 아래는 예시 데이터입니다.",
 subscriptions:[
  {name:"[예시] 청주 OO지구 1단지",location:"청주시 흥덕구",period:"2025-12-01 ~ 12-03",units:480,price:"최고 5.2억",status:"접수예정",competition_range:null,min_score:null,
   house_types:[{type:"84A",units:220,price:"4.9억",competition:null,min_score:null},{type:"84B",units:180,price:"5.0억",competition:null,min_score:null},{type:"101",units:80,price:"5.2억",competition:null,min_score:null}],is_sample:true},
  {name:"[예시] 청주 OO지구 2단지",location:"청주시 청원구",period:"2025-11-18 ~ 11-20",units:320,price:"최고 4.1억",status:"접수중",competition_range:[3.2,18.5],min_score:54,
   house_types:[{type:"59",units:120,price:"2.9억",competition:"18.5:1",min_score:62,avg_score:68},{type:"84",units:200,price:"4.1억",competition:"3.2:1",min_score:54,avg_score:59}],is_sample:true},
  {name:"[예시] OO오피스텔",location:"청주시 서원구",period:"2025-11-05 ~ 11-06",units:150,price:"최고 1.8억",status:"마감",competition_range:[1.1,2.3],min_score:null,
   house_types:[{type:"전용 24",units:90,price:"1.2억",competition:"1.1:1",min_score:null},{type:"전용 33",units:60,price:"1.8억",competition:"2.3:1",min_score:null}],is_sample:true}],
 news:[
  {title:"[예시] 청주 아파트 거래량, 전월 대비 변동",source:"예시뉴스",date:"2025-11-14",url:"#",is_sample:true},
  {title:"[예시] 흥덕구 신규 분양 일정 공개",source:"예시뉴스",date:"2025-11-12",url:"#",is_sample:true},
  {title:"[예시] 청주 전세가율 동향",source:"예시뉴스",date:"2025-11-10",url:"#",is_sample:true}],
 policies:[
  {title:"[예시] 생애최초 주택구입 지원 안내",summary:"대상·한도·신청 방법 요약(예시).",source:"국토교통부(예시)",date:"2025-11-01",is_sample:true},
  {title:"[예시] 디딤돌·보금자리론 금리 안내",summary:"정책대출 금리·자격 요건 요약(예시).",source:"한국주택금융공사(예시)",date:"2025-10-28",is_sample:true}]};
const DEMO={contains_sample_data:true,feed:DEMO_FEED,ranking:demoRanking("apartment"),tx:DEMO_TX,board:demoBoard()};

/* ---------- helpers ---------- */
const eok=m=>m==null?"—":(m/10000).toFixed(2)+"억";
const won=m=>m==null?"—":m.toLocaleString("ko-KR")+"만원";
const manKor=(v,signed)=>{ if(v==null)return "—"; const s=v<0?"-":(signed?"+":""); const a=Math.abs(v);
 const e=Math.floor(a/10000), man=a%10000;
 const body=e>0?`${e}억${man?" "+man.toLocaleString("ko-KR")+"만":""}`:`${a.toLocaleString("ko-KR")}만`;
 return s+body; };
const pyeong=v=>v==null?"—":v.toLocaleString("ko-KR")+"만원/평";
const guOf=n=>(n||"").replace("청주시 ","");
const distM=m=>m==null?"":(m<1000?`${m}m`:`${(m/1000).toFixed(1)}km`);
function Delta({v}){if(v==null)return <span style={{color:MUTED,fontWeight:600}}>—</span>;
 const up=v>=0;return <span className="num" style={{color:up?UP:DOWN,fontWeight:700}}>{up?"▲":"▼"} {Math.abs(v).toFixed(1)}%</span>;}
function ChangeChip({pct,dir}){if(pct==null)return <span style={{color:MUTED}}>—</span>;
 const c=(dir==="up"||pct>=0)?UP:DOWN;return <span className="num" style={{color:c,fontWeight:800}}>{pct>=0?"▲":"▼"}{Math.abs(pct).toFixed(1)}%</span>;}
function ExBadge(){return <span className="pill ex">예시</span>;}
function Empty({children,action}){return (<div style={{padding:28,textAlign:"center",color:MUTED,fontSize:13.5,lineHeight:1.6}}>
  <div>{children}</div>
  {action&&<div style={{marginTop:13}}>{action}</div>}
</div>);}
function Skeleton({h=14,w="100%",r=8,style}){return <div className="skel" style={{height:h,width:w,borderRadius:r,...(style||{})}}/>;}
function SkeletonCard({lines=3}){return (<div className="card" style={{padding:16,marginTop:10}}>
  <Skeleton h={16} w="55%"/>
  {Array.from({length:lines}).map((_,i)=><div key={i} style={{marginTop:9}}><Skeleton h={12} w={i%2?"78%":"92%"}/></div>)}
</div>);}
function SkeletonRow({thumb}){return (<div style={{display:"flex",alignItems:"center",gap:11,padding:"12px 2px",borderBottom:"1px solid var(--line)"}}>
  {thumb&&<Skeleton h={44} w={44} r={12} style={{flex:"none"}}/>}
  <div style={{flex:1,minWidth:0}}><Skeleton h={13} w="62%"/><div style={{height:7}}/><Skeleton h={11} w="40%"/></div>
  <Skeleton h={14} w={54} style={{flex:"none"}}/>
</div>);}
function SkeletonList({rows=6,thumb,card=true}){const body=Array.from({length:rows}).map((_,i)=><SkeletonRow key={i} thumb={thumb}/>);
  return card?<div className="card" style={{padding:"2px 12px",marginTop:10}}>{body}</div>:<div>{body}</div>;}
function SkeletonStat(){return (<div className="card" style={{padding:"14px 15px",marginTop:10}}>
  <Skeleton h={12} w="38%"/><div style={{height:10}}/>
  <div style={{display:"flex",gap:22,alignItems:"flex-end"}}>
   <Skeleton h={24} w={112}/>
   <div style={{marginLeft:"auto"}}><Skeleton h={18} w={70}/></div>
  </div>
</div>);}
function Info({text}){return (<span className="tip"><span className="tipdot">?</span><span className="tiptext">{text}</span></span>);}
function Card({label,big,sub}){
 return <div className="card" style={{padding:18}}>
  <div style={{fontSize:13,color:MUTED}}>{label}</div>
  <div className="num" style={{fontSize:24,fontWeight:800,marginTop:6}}>{big}</div>
  {sub&&<div style={{fontSize:12,color:MUTED,marginTop:4}}>{sub}</div>}
 </div>;
}
function TxFlags({r}){
 if(!r) return null;
 const items=[];
 if(r.corrected) items.push(["정정","#1E5FC4","rgba(30,95,196,.12)"]);
 if(r.direct) items.push(["직거래","#9A6B00","rgba(178,106,0,.14)"]);
 if(r.outlier) items.push(["이상치","#C8322A","rgba(200,50,42,.12)"]);
 if(!items.length) return null;
 return (<React.Fragment>{items.map(([t,fg,bg],i)=>
  <span key={i} className="pill" style={{background:bg,color:fg,fontWeight:700,marginLeft:4}}>{t}</span>)}</React.Fragment>);
}
function jeonseRisk(r){
 if(r==null) return null;
 if(r>=90) return {label:"전세가율 매우 높음",bg:"rgba(200,50,42,.14)",fg:"#C8322A"};
 if(r>=80) return {label:"전세가율 높음",bg:"rgba(178,106,0,.16)",fg:"#9A6B00"};
 return null;
}
function jeonseSafety(r){
 if(r==null) return null;
 if(r>=90) return {level:4,label:"위험 (깡통 우려)",color:"#C8322A",bg:"rgba(200,50,42,.12)",
   advice:"매매가 대비 보증금 비중이 매우 큽니다. 시세가 조금만 떨어져도 보증금 회수가 어려울 수 있어, 보증금 반환보증 가입과 등기부 확인이 특히 중요합니다."};
 if(r>=80) return {level:3,label:"주의",color:"#9A6B00",bg:"rgba(178,106,0,.14)",
   advice:"보증금 비중이 높은 편입니다. 선순위 채권·근저당 여부를 확인하고 보증금 반환보증 가입을 권장합니다."};
 if(r>=70) return {level:2,label:"보통",color:"#1E5FC4",bg:"rgba(30,95,196,.12)",
   advice:"일반적인 수준입니다. 그래도 등기부와 선순위 채권은 확인하는 것이 안전합니다."};
 return {level:1,label:"안전한 편",color:"#1d7a4d",bg:"rgba(29,122,77,.12)",
   advice:"매매가 대비 보증금 비중이 낮아 상대적으로 회수 여력이 큽니다. 기본 확인(등기부 등)은 권장됩니다."};
}
function ShareCard({card,onClose}){
 const ref=React.useRef(null);
 const [msg,setMsg]=useState("");
 useEffect(()=>{drawCard();},[]);
 function drawCard(){
  const cv=ref.current; if(!cv) return;
  const W=1080,H=1350,P=72; cv.width=W; cv.height=H;
  const x=cv.getContext("2d"); const cw=W-2*P;
  x.textBaseline="top";
  const F=(s,w)=>`${w} ${s}px -apple-system,"Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",sans-serif`;
  const T=(s,xx,yy,size,weight,color,align)=>{x.font=F(size,weight);x.fillStyle=color;x.textAlign=align||"left";x.fillText(s,xx,yy);};
  const RR=(xx,yy,w,h,r,fill)=>{x.beginPath();x.moveTo(xx+r,yy);x.arcTo(xx+w,yy,xx+w,yy+h,r);x.arcTo(xx+w,yy+h,xx,yy+h,r);x.arcTo(xx,yy+h,xx,yy,r);x.arcTo(xx,yy,xx+w,yy,r);x.closePath();x.fillStyle=fill;x.fill();};
  const TEALc="#0F766E",INKc="#1B2733",MUTc="#566069",UPc="#C8322A",DNc="#1E5FC4";
  // bg
  x.fillStyle="#ffffff"; x.fillRect(0,0,W,H);
  RR(0,0,W,16,0,TEALc);
  // brand
  T("청주 시세",P,70,40,"800",TEALc,"left");
  T("청주 부동산 한눈에",W-P,80,26,"600",MUTc,"right");
  // 단지명 (최대 2줄)
  let cy=170; x.font=F(60,"800");
  const chars=[...String(card.name||"")]; let lines=[],cur="";
  for(const ch of chars){ if(x.measureText(cur+ch).width>cw-(card.sample?120:0)&&cur){ if(lines.length===1){ while(x.measureText(cur+"…").width>cw-(card.sample?120:0)&&cur)cur=cur.slice(0,-1); cur+="…"; lines.push(cur); cur=""; break;} lines.push(cur); cur=ch;} else cur+=ch; }
  if(cur&&lines.length<2) lines.push(cur);
  lines.forEach((ln,i)=>T(ln,P,cy+i*74,60,"800",INKc,"left"));
  if(card.sample){ RR(P+x.measureText(lines[0]).width+18,cy+8,104,46,12,"#FBE3DE"); T("모의",P+x.measureText(lines[0]).width+38,cy+16,28,"800",UPc,"left"); }
  cy+=lines.length*74+14;
  T(card.sub||"",P,cy,30,"600",MUTc,"left"); cy+=52;
  // scope chip
  const sc=card.scope||""; x.font=F(27,"700"); const scw=x.measureText(sc).width+40;
  RR(P,cy,scw,52,12,"#E7F1EF"); T(sc,P+20,cy+12,27,"700",TEALc,"left"); cy+=86;
  // divider
  RR(P,cy,cw,2,1,"rgba(99,120,128,.18)"); cy+=40;
  // 가격
  T(`최근 매매가 · 최근 ${card.agg}개월`,P,cy,28,"600",MUTc,"left");
  const dp=card.fromPeak, dtxt=dp==null?"":`${dp>0?"▲":dp<0?"▼":"–"} ${Math.abs(dp)}%`, dcol=dp>0?UPc:dp<0?DNc:MUTc;
  T(dtxt,W-P,cy+4,34,"800",dcol,"right");
  cy+=40; T(eok(card.latest),P,cy,86,"800",INKc,"left"); cy+=104;
  T(`최근 ${card.agg}개월 고점 ${eok(card.peak)} 대비`,P,cy,26,"600",MUTc,"left"); cy+=66;
  // stats 3열
  const cols=[["중앙값",eok(card.median)],["평단가",card.ppm!=null?card.ppm.toLocaleString("ko-KR")+" /평":"—"],["매매 거래",card.count!=null?card.count+"건":"—"]];
  cols.forEach(([l,v],i)=>{const xx=P+i*(cw/3);T(l,xx,cy,28,"600",MUTc,"left");T(v,xx,cy+40,42,"800",INKc,"left");});
  cy+=130;
  // 전세 안전도
  if(card.jr!=null){
   const s=jeonseSafety(card.jr);
   T("전세 안전도",P,cy,28,"600",MUTc,"left");
   T(`${card.jr}%  ·  ${s.label}`,W-P,cy,30,"800",s.color,"right");
   cy+=48;
   const zones=[[0,70,"#1d7a4d"],[70,80,"#1E5FC4"],[80,90,"#9A6B00"],[90,100,"#C8322A"]];
   let zx=P; zones.forEach(([a,b,c])=>{const zw=cw*(b-a)/100; x.globalAlpha=.32; RR(zx,cy,zw,16,0,c); x.globalAlpha=1; zx+=zw;});
   const mx=P+cw*Math.max(0,Math.min(100,card.jr))/100; RR(mx-3,cy-5,6,26,3,s.color);
   cy+=54;
  }
  // 추이
  const ts=(card.ts||[]).map(t=>t.avg).filter(v=>v!=null);
  if(ts.length>1){
   T(`최근 ${ts.length}개월 매매가 추이`,P,cy,26,"700",MUTc,"left"); cy+=40;
   const gh=150, gw=cw, gx=P, gy=cy, mn=Math.min(...ts), mx2=Math.max(...ts), rng=(mx2-mn)||1;
   x.beginPath();
   ts.forEach((v,i)=>{const px=gx+gw*i/(ts.length-1), py=gy+gh-(v-mn)/rng*gh; i?x.lineTo(px,py):x.moveTo(px,py);});
   x.strokeStyle=TEALc; x.lineWidth=5; x.lineJoin="round"; x.stroke();
   const last=ts[ts.length-1], lpx=gx+gw, lpy=gy+gh-(last-mn)/rng*gh;
   x.beginPath(); x.arc(lpx,lpy,9,0,Math.PI*2); x.fillStyle=TEALc; x.fill();
   cy+=gh+30;
  }
  // footer
  RR(P,H-150,cw,2,1,"rgba(99,120,128,.14)");
  T("자료: 국토교통부 실거래가 · 참고용(법적 효력 없음)",P,H-118,24,"600",MUTc,"left");
  T("🏠 청집사 — 청주 부동산을 한눈에",P,H-82,28,"800",TEALc,"left");
  T((typeof location!=="undefined"&&location.host)?location.host:"",W-P,H-82,26,"700",MUTc,"right");
 }
 async function getBlob(){ return await new Promise(res=>ref.current.toBlob(res,"image/png")); }
 function save(){ getBlob().then(b=>{const u=URL.createObjectURL(b);const a=document.createElement("a");a.href=u;a.download=`청주시세_${card.name}.png`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1500);setMsg("이미지를 저장했어요.");}); }
 async function share(){
  try{
   const blob=await getBlob(); const file=new File([blob],`청주시세_${card.name}.png`,{type:"image/png"});
   const txt=`${card.name} ${card.scope} · 최근 매매가 ${eok(card.latest)}`;
   if(navigator.canShare&&navigator.canShare({files:[file]})){ await navigator.share({files:[file],title:`${card.name} 시세`,text:txt}); }
   else if(navigator.share){ await navigator.share({title:`${card.name} 시세`,text:txt,url:location.href}); }
   else { save(); setMsg("공유를 지원하지 않는 환경이라 이미지를 저장했어요. 카톡 등에 첨부해 보내세요."); }
  }catch(e){ if(String(e&&e.name)!=="AbortError") setMsg("공유가 취소되었거나 지원되지 않아요. ‘저장’ 후 첨부해 보내세요."); }
 }
 return (<div onClick={onClose} style={{position:"fixed",inset:0,background:"rgba(10,20,28,.6)",zIndex:60,display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",padding:18}}>
  <div onClick={e=>e.stopPropagation()} style={{width:"100%",maxWidth:400,display:"flex",flexDirection:"column",alignItems:"center",gap:12}}>
   <canvas ref={ref} style={{width:"100%",maxWidth:360,borderRadius:16,boxShadow:"0 10px 40px rgba(0,0,0,.4)",background:"#fff"}}/>
   {msg&&<div style={{fontSize:12.5,color:"#fff",textAlign:"center"}}>{msg}</div>}
   <div style={{display:"flex",gap:9,width:"100%",maxWidth:360}}>
    <button onClick={save} style={{flex:1,border:"none",borderRadius:11,padding:"13px 0",fontWeight:800,fontSize:14,cursor:"pointer",background:"#fff",color:"#1B2733"}}>이미지 저장</button>
    <button onClick={share} className="btn-primary" style={{flex:1,padding:"13px 0"}}>공유하기</button>
   </div>
   <button onClick={onClose} style={{border:"none",background:"none",color:"#cfd8de",fontSize:13.5,fontWeight:700,cursor:"pointer",padding:"4px 10px"}}>닫기</button>
  </div>
 </div>);
}
function JeonseSafety({ratio,scope,note}){
 // 전세가율(비율) + 전세 안전도(위험 밴드)를 하나로 통합 — 게이지·비율·해석은 기본 노출(알짜),
 // 체크리스트·보증기관 링크는 '계약 전 확인 ▾' 접이식으로.
 const s=jeonseSafety(ratio);
 const [more,setMore]=useState(false);
 if(!s) return null;
 const pos=Math.max(0,Math.min(100,ratio));
 const zones=[["~70",0,70,"#1d7a4d"],["70~80",70,80,"#1E5FC4"],["80~90",80,90,"#9A6B00"],["90~",90,100,"#C8322A"]];
 return (<Collapsible icon="doc" defaultOpen={true} title={<React.Fragment>전세가율·안전도 <span style={{fontWeight:500,color:MUTED,fontSize:12}}>· 깡통전세 위험 참고</span></React.Fragment>}>
  <div style={{padding:"8px 14px 13px"}}>
   <div style={{display:"flex",alignItems:"baseline",gap:8,flexWrap:"wrap"}}>
    <span className="num" style={{fontSize:22,fontWeight:800}}>{ratio}%</span>
    <span className="pill" style={{background:s.bg,color:s.color,fontWeight:800}}>{s.label}</span>
    <span style={{fontSize:11.5,color:MUTED}}>전세가율{scope?` · ${scope}`:""}</span>
   </div>
   {/* 게이지 */}
   <div style={{position:"relative",marginTop:11,marginBottom:4}}>
    <div style={{display:"flex",height:9,borderRadius:6,overflow:"hidden"}}>
     {zones.map(([l,a,b,c])=><div key={l} style={{flex:b-a,background:c,opacity:.32}}/>)}
    </div>
    <div style={{position:"absolute",top:-3,left:`${pos}%`,transform:"translateX(-50%)",width:3,height:15,background:s.color,borderRadius:2,boxShadow:"0 0 0 2px var(--surface-solid)"}}/>
   </div>
   <div style={{display:"flex",justifyContent:"space-between",fontSize:10.5,color:MUTED}}>
    {zones.map(([l])=><span key={l}>{l}</span>)}
   </div>
   {note&&<div style={{fontSize:12.5,color:INK,marginTop:10,lineHeight:1.55}}>💧 {note}</div>}
   <p style={{fontSize:13,lineHeight:1.65,margin:"9px 0 0"}}>{s.advice}</p>
   <button onClick={()=>setMore(v=>!v)} style={{marginTop:11,border:"none",background:"var(--chip)",borderRadius:9,padding:"9px 12px",cursor:"pointer",fontWeight:800,fontSize:12.5,color:INK,width:"100%",textAlign:"left"}}>계약 전 확인 {more?"▲":"▾"}</button>
   {more&&<React.Fragment>
    <div style={{background:"var(--chip)",borderRadius:10,padding:"10px 12px",marginTop:8}}>
     <ul style={{margin:0,paddingLeft:17,fontSize:12.5,lineHeight:1.7,color:"var(--ink)"}}>
      <li>등기부등본의 <b>선순위 채권·근저당</b> 합계가 (보증금+선순위)가 매매가를 넘지 않는지</li>
      <li>임대인 <b>국세·지방세 체납</b> 여부(납세증명서 요청)</li>
      <li><b>전세보증금 반환보증</b> 가입 가능 여부·한도</li>
      <li>확정일자·전입신고로 <b>대항력·우선변제권</b> 확보</li>
     </ul>
    </div>
    <div style={{fontSize:12,color:MUTED,marginTop:9,lineHeight:1.6}}>
     보증금 반환보증: 주택도시보증공사(HUG, <a href="https://www.khug.or.kr" target="_blank" rel="noopener noreferrer" style={{color:TEAL}}>khug.or.kr</a>) · 한국주택금융공사(HF, <a href="https://www.hf.go.kr" target="_blank" rel="noopener noreferrer" style={{color:TEAL}}>hf.go.kr</a>) · SGI서울보증. 가입 가능 여부·한도는 보증기관 심사로 결정됩니다.
    </div>
   </React.Fragment>}
   <div style={{fontSize:11,color:MUTED,marginTop:9,lineHeight:1.6}}>
    전세가율 = 전세보증금 중앙값 ÷ 매매가 중앙값(최근 실거래). <b>참고 지표</b>이며 실제 위험은 등기부·선순위 채권·임대인 신용 등으로 달라집니다. 정보 제공이며 법률·금융 자문이 아닙니다.
   </div>
  </div>
 </Collapsible>);
}
function JeonseMetric({ratio}){
 const risk=jeonseRisk(ratio);
 return (<div style={{minWidth:0}}>
  <div style={{fontSize:11.5,color:MUTED}}>전세가율(갭)<Info text="전세보증금 ÷ 매매가 × 100. 높을수록 매매가 대비 보증금 비중이 커, 시세 하락 시 보증금 회수가 어려워지는 '깡통전세' 위험이 커질 수 있습니다. 데이터 기준 참고치이며 단정이 아닙니다."/></div>
  <div className="num" style={{fontSize:16,fontWeight:800,marginTop:2}}>{ratio!=null?`${ratio}%`:"—"}</div>
  {risk&&<span className="pill" style={{marginTop:3,display:"inline-block",background:risk.bg,color:risk.fg}}>⚠ {risk.label}</span>}
 </div>);
}
function DMetric({label,val,sub}){
 return <div style={{minWidth:0}}>
  <div style={{fontSize:11.5,color:MUTED}}>{label}</div>
  <div className="num" style={{fontSize:16,fontWeight:800,marginTop:2}}>{val}</div>
  {sub&&<div className="num" style={{fontSize:11,color:MUTED,marginTop:1}}>{sub}</div>}
 </div>;
}
function Pager({page,setPage,total,per}){
 const pages=Math.max(1,Math.ceil(total/per));
 if(pages<=1)return null;
 return <div className="pager">
  <button className="pgbtn" disabled={page<=1} onClick={()=>setPage(p=>Math.max(1,p-1))}>‹ 이전</button>
  <span className="pgnum">{page} / {pages}</span>
  <button className="pgbtn" disabled={page>=pages} onClick={()=>setPage(p=>Math.min(pages,p+1))}>다음 ›</button>
 </div>;
}

/* 더보기(증분 로드): 긴 리스트를 처음 initial개만 그리고, 탭하면 step개씩 추가.
   렌더되는 DOM을 제한해 모바일 성능·가독성을 함께 개선. 리스트가 바뀌면 자동 초기화. */
function MoreList({items,render,initial=8,step=10,label="더보기"}){
 const sig=(items?items.length:0)+"|"+(items&&items[0]&&(items[0].id||items[0].contract_date||items[0].complex_name||items[0].title||"")||"");
 const [n,setN]=useState(initial);
 useEffect(()=>{setN(initial);},[sig]);
 if(!items||!items.length)return null;
 const shown=items.slice(0,n), rest=items.length-n;
 return <React.Fragment>
  {shown.map(render)}
  {rest>0&&<button onClick={()=>setN(x=>x+step)}
    style={{display:"block",width:"100%",margin:"8px 0 2px",border:"1px solid var(--line)",background:"var(--surface-2)",
      color:INK,fontWeight:700,fontSize:13,padding:"10px",borderRadius:10,cursor:"pointer"}}>
    {label} <span style={{color:MUTED,fontWeight:600}}>(남은 {rest}개)</span>
  </button>}
 </React.Fragment>;
}

/* 라인 아이콘 (이모지 대체) */
/* 키보드 활성화: 클릭 div를 Enter/Space로도 누를 수 있게(접근성) */
const onEnter=fn=>e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();fn();}};
/* 아래 순수 표시 컴포넌트는 모듈 레벨에 둔다 — 부모 렌더 본문 안에 정의하면 매 렌더 리마운트(포커스·성능 churn, CLAUDE.md §10 트랩#1). */
const Stat=({label,val})=>(<div style={{flex:1,minWidth:72,background:"var(--surface-2)",borderRadius:10,padding:"10px 12px"}}><div style={{fontSize:11.5,color:MUTED}}>{label}</div><div className="num" style={{fontSize:20,fontWeight:800}}>{val}</div></div>);
const Tool=({icon,title,desc,onClick})=>(<div onClick={onClick} onKeyDown={onEnter(onClick)} role="button" tabIndex={0} className="card" style={{padding:"15px 16px",marginTop:12,cursor:"pointer",background:"linear-gradient(100deg,rgba(15,118,110,.10),rgba(15,118,110,.02))",display:"flex",alignItems:"center",gap:13}}>
  <div style={{fontSize:28,flex:"none"}}>{icon}</div>
  <div style={{minWidth:0,flex:1}}><div style={{fontWeight:800,fontSize:15}}>{title}</div><div style={{fontSize:12.5,color:MUTED,marginTop:2}}>{desc}</div></div>
  <span style={{color:TEAL,fontSize:20,flex:"none"}}>›</span>
 </div>);
const Quick=({icon,label,onClick})=>(<button onClick={onClick} style={{flex:1,border:"none",background:"var(--surface-2)",borderRadius:12,padding:"13px 6px",cursor:"pointer",display:"flex",flexDirection:"column",alignItems:"center",gap:5}}>
  <span style={{fontSize:22}}>{icon}</span><span style={{fontSize:12,fontWeight:700,color:INK}}>{label}</span>
 </button>);
function Icon({name,active,size=24}){
 const c=active?TEAL:"#9aa3a8";
 const p={width:size,height:size,viewBox:"0 0 24 24",fill:"none",stroke:c,strokeWidth:active?2.3:2,strokeLinecap:"round",strokeLinejoin:"round","aria-hidden":true,focusable:false};
 if(name==="home")return <svg {...p}><path d="M3 11.4 12 4l9 7.4"/><path d="M5.5 9.8V20h13V9.8"/></svg>;
 if(name==="rank")return <svg {...p}><path d="M5.5 21V11"/><path d="M12 21V4.5"/><path d="M18.5 21v-6.5"/></svg>;
 if(name==="search")return <svg {...p}><circle cx="11" cy="11" r="7"/><path d="m20.5 20.5-3.4-3.4"/></svg>;
 if(name==="price")return <svg {...p}><path d="M4 15l4.5-4.5 3 3L20 6"/><path d="M20 10.5V6h-4.5"/></svg>;
 if(name==="build")return <svg {...p}><path d="M4 21V7l7-3v17"/><path d="M11 21V10l7 3v8"/><path d="M7.5 8.5v0M7.5 12v0M7.5 15.5v0"/></svg>;
 if(name==="news")return <svg {...p}><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 9h8M8 13h8M8 17h5"/></svg>;
 if(name==="doc")return <svg {...p}><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4M10 13h5M10 17h5"/></svg>;
 if(name==="map")return <svg {...p}><path d="M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11Z"/><circle cx="12" cy="10" r="2.5"/></svg>;
 if(name==="loan")return <svg {...p}><circle cx="12" cy="12" r="9"/><path d="M8.5 8.5l3.5 5 3.5-5M8.5 13h7M8.5 15.5h7"/></svg>;
 if(name==="listing")return <svg {...p}><path d="M4 10.5 12 4l8 6.5"/><path d="M6 9.5V20h12V9.5"/><rect x="10" y="13" width="4" height="7"/></svg>;
 if(name==="camera")return <svg {...p}><path d="M4 8h3l1.5-2h7L17 8h3v11H4z"/><circle cx="12" cy="13" r="3.2"/></svg>;
 if(name==="phone")return <svg {...p}><path d="M5 4h4l1.5 4-2 1.5a11 11 0 0 0 5 5l1.5-2 4 1.5v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z"/></svg>;
 if(name==="star")return <svg {...p} fill={active?TEAL:"none"} stroke={active?TEAL:"#9aa3a8"}><path d="M12 3.6l2.6 5.3 5.8.8-4.2 4.1 1 5.8L12 17l-5.2 2.7 1-5.8L3.6 9.7l5.8-.8z"/></svg>;
 if(name==="board")return <svg {...p}><path d="M4 5h16v11H10l-4 3v-3H4z"/><path d="M8 9h8M8 12h5"/></svg>;
 if(name==="heart")return <svg {...p} fill={active?UP:"none"} stroke={active?UP:"#9aa3a8"}><path d="M12 20s-7-4.6-9.2-9C1.3 8 3 4.8 6.2 4.8c1.9 0 3.1 1.1 3.8 2.2.7-1.1 1.9-2.2 3.8-2.2 3.2 0 4.9 3.2 3.4 6.2C19 15.4 12 20 12 20Z"/></svg>;
 if(name==="bell")return <svg {...p}><path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6Z"/><path d="M10.5 19a1.8 1.8 0 0 0 3 0"/></svg>;
 if(name==="subscription")return <svg {...p}><path d="M4 7h16v4a2 2 0 0 0 0 2v4H4v-4a2 2 0 0 0 0-2z"/><path d="M14 7v10"/></svg>;
 if(name==="bookmark")return <svg {...p} fill={active?TEAL:"none"} stroke={active?TEAL:"#9aa3a8"}><path d="M7 4h10v16l-5-3.2L7 20z"/></svg>;
 if(name==="more")return <svg {...p}><path d="M4 7h16M4 12h16M4 17h16"/></svg>;
 return null;
}
function SecTitle({icon,children}){
 return <div style={{display:"flex",alignItems:"center",gap:7,fontWeight:800,fontSize:15,margin:"20px 2px 8px"}}>
  <Icon name={icon} active size={18}/>{children}</div>;
}

/* ====================== 매물(등록 매물 · UGC) ====================== */
const LP_DEALS=[["trade","매매"],["jeonse","전세"],["wolse","월세"]];
const LP_PROPS=[["apartment","아파트"],["officetel","오피스텔"],["rowhouse","빌라·연립"],["detached","단독·다가구"],["oneroom","원룸·기타"]];
const LP_PROP=Object.fromEntries(LP_PROPS);
const LP_DEAL=Object.fromEntries(LP_DEALS);
const DIRECTIONS=["남향","남동향","남서향","동향","서향","북향","북동향","북서향"];
const DEAL_COLOR={trade:TEAL,jeonse:"#1E5FC4",wolse:"#9A6B00"};
const INP={width:"100%",border:"1px solid #dfe5e5",borderRadius:9,padding:"9px 11px",fontSize:14,background:"var(--surface-solid)",boxSizing:"border-box"};
function listingPrice(x){
 if(x.deal_type==="wolse")return `보증 ${eok(x.deposit)} / 월 ${x.monthly_rent}만`;
 if(x.deal_type==="jeonse")return `전세 ${eok(x.price)}`;
 return eok(x.price);
}
const DEMO_LISTINGS=[
 {id:9001,source:"listing",poster_role:"agent",title:"가경아이파크 4단지 로열층 급매",deal_type:"trade",property_type:"apartment",lawd_cd:"43113",gu:"흥덕구",dong:"가경동",complex_name:"가경아이파크 4단지",exclusive_area:84.9,supply_area:112.3,floor:15,total_floor:25,rooms:3,baths:2,direction:"남향",price:46500,maintenance_fee:18,maintenance_items:"청소·경비·승강기",move_in_date:"즉시입주",approval_date:"2019-03",options:"냉장고,에어컨,붙박이장",description:"남향 로열층, 채광 우수. 인근 초등학교 도보 5분. 단지 내 상가·주차 여유.",photos:[],agent_office:"가경공인중개사사무소",agent_name:"홍길동",agent_reg_no:"43113-2024-00012",agent_phone:"043-000-0000",agent_address:"청주시 흥덕구 가경로 00",is_sample:true,created_at:"2026-06-15T09:00:00"},
 {id:9002,source:"listing",poster_role:"user",title:"복대동 신축 오피스텔 월세 (개인 직거래)",deal_type:"wolse",property_type:"officetel",lawd_cd:"43113",gu:"흥덕구",dong:"복대동",complex_name:null,exclusive_area:23.1,supply_area:43.0,floor:7,total_floor:15,rooms:1,baths:1,direction:"동향",deposit:1000,monthly_rent:55,maintenance_fee:7,maintenance_items:"인터넷·수도 포함",move_in_date:"2026-07-01",approval_date:"2022-05",options:"풀옵션",description:"역세권 풀옵션 원룸형. 직거래 환영합니다.",photos:[],agent_phone:"010-0000-0000",is_sample:true,created_at:"2026-06-16T14:00:00"},
 {id:9003,source:"listing",poster_role:"agent",title:"용암동 빌라 전세 · 주차가능",deal_type:"jeonse",property_type:"rowhouse",lawd_cd:"43111",gu:"상당구",dong:"용암동",complex_name:null,exclusive_area:59.8,supply_area:72.0,floor:2,total_floor:4,rooms:3,baths:1,direction:"남동향",price:16500,maintenance_fee:5,move_in_date:"협의",approval_date:"2015-08",options:"가스레인지",description:"조용한 주택가, 세대당 1주차 가능. 채광 양호.",photos:[],agent_office:"용암공인중개사사무소",agent_name:"김중개",agent_reg_no:"43111-2023-00077",agent_phone:"043-111-1111",agent_address:"청주시 상당구 용암로 00",is_sample:true,created_at:"2026-06-14T11:00:00"}
];

function ListingThumb({photo,size=104}){
 return <div style={{width:size,height:size,flex:"none",borderRadius:12,overflow:"hidden",background:"var(--chip)",backgroundImage:photo?`url(${photo})`:"none",backgroundSize:"cover",backgroundPosition:"center",display:"flex",alignItems:"center",justifyContent:"center"}}>{!photo&&<Icon name="camera" size={26}/>}</div>;
}
function ListingCard({x,onOpen}){
 const unit=useUnit();
 const photo=(x.photos&&x.photos[0])||null;
 return (<div className="feedrow" tabIndex={0} role="button" onKeyDown={onEnter(()=>onOpen(x))} style={{padding:"12px 4px",cursor:"pointer"}} onClick={()=>onOpen(x)}>
  <div style={{display:"flex"}}>
   <ListingThumb photo={photo}/>
   <div style={{minWidth:0,padding:"10px 12px",flex:1}}>
    <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
     <span className="pill" style={{background:"rgba(15,118,110,.12)",color:DEAL_COLOR[x.deal_type]||TEAL,fontWeight:800}}>{LP_DEAL[x.deal_type]}</span>
     <span style={{fontWeight:800,fontSize:15}} className="num">{listingPrice(x)}</span>
     {x.is_sample&&<span className="pill ex">예시</span>}
     {FEATURES.ads&&x.is_sponsored&&<span className="pill" style={{background:"rgba(178,106,0,.14)",color:"#9A6B00",fontWeight:800}}>광고</span>}
    </div>
    <div style={{fontWeight:700,marginTop:3,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{x.title}</div>
    <div style={{fontSize:12,color:MUTED,marginTop:2}}>{LP_PROP[x.property_type]} · {x.gu}{x.dong?` ${x.dong}`:""}{x.exclusive_area?` · 전용 ${fmtArea(x.exclusive_area,unit)}`:""}{x.floor?` · ${x.floor}/${x.total_floor||"—"}층`:""}</div>
    <div style={{fontSize:11.5,color:MUTED,marginTop:3}}>{x.poster_role==="agent"?(x.agent_office||"중개사무소"):"개인 직거래"} · {(x.created_at||"").slice(0,10)}</div>
   </div>
  </div>
 </div>);
}
function LField({label,req,children}){
 return <label style={{marginBottom:11,display:"block"}}>
  <div style={{fontSize:12,color:MUTED,fontWeight:600,marginBottom:4}}>{label}{req&&<span style={{color:UP}}> *</span>}</div>
  {children}</label>;
}
function FormHead({children}){return <div style={{fontWeight:800,fontSize:14,margin:"18px 2px 8px",color:INK}}>{children}</div>;}
function ListingForm({onCancel,onCreated,account,initial}){
 const I=initial||{}, isEdit=!!(initial&&initial.id);
 const sv=v=>v==null?"":String(v);   // 숫자/널 → 입력용 문자열
 const [role,setRole]=useState(I.poster_role||(account?account.role:"agent"));
 const [deal,setDeal]=useState(I.deal_type||"trade"),[prop,setProp]=useState(I.property_type||"apartment");
 const [title,setTitle]=useState(I.title||"");
 const [gu,setGu]=useState(I.lawd_cd||"43113"),[dong,setDong]=useState(I.dong_name||""),[cpx,setCpx]=useState(I.complex_name||""),[addr,setAddr]=useState(I.address_detail||"");
 const [area,setArea]=useState(sv(I.exclusive_area)),[sup,setSup]=useState(sv(I.supply_area)),[floor,setFloor]=useState(sv(I.floor)),[tfloor,setTfloor]=useState(sv(I.total_floor));
 const [rooms,setRooms]=useState(sv(I.rooms)),[baths,setBaths]=useState(sv(I.baths)),[dir,setDir]=useState(I.direction||"");
 const [price,setPrice]=useState(sv(I.price)),[dep,setDep]=useState(sv(I.deposit)),[rent,setRent]=useState(sv(I.monthly_rent));
 const [mfee,setMfee]=useState(sv(I.maintenance_fee)),[mitems,setMitems]=useState(I.maintenance_items||""),[movein,setMovein]=useState(I.move_in_date||""),[approval,setApproval]=useState(I.approval_date||""),[opts,setOpts]=useState(I.options||"");
 const [desc,setDesc]=useState(I.description||""),[photos,setPhotos]=useState(I.photos||[]),[uploading,setUploading]=useState(false);
 const [office,setOffice]=useState(I.agent_office||""),[aname,setAname]=useState(I.agent_name||""),[areg,setAreg]=useState(I.agent_reg_no||""),[phone,setPhone]=useState(I.agent_phone||""),[aaddr,setAaddr]=useState(I.agent_address||"");
 const [err,setErr]=useState(""),[busy,setBusy]=useState(false);
 const onPhotos=e=>{const files=[...e.target.files].slice(0,12);e.target.value="";
  if(!files.length)return;
  setUploading(true);
  Promise.all(files.map(async f=>{
   try{const fd=new FormData();fd.append("file",f);
    const r=await fetch(`${API}/listings/upload`,{method:"POST",body:fd});
    if(r.ok){const j=await r.json();if(j&&j.url)return j.url;}
   }catch(_){}
   // 폴백(오프라인/스토리지 미구성): 데이터URL로 미리보기·등록
   return await new Promise(res=>{const rd=new FileReader();rd.onload=()=>res(rd.result);rd.readAsDataURL(f);});
  })).then(urls=>{setPhotos(p=>[...p,...urls].slice(0,12));setUploading(false);}).catch(()=>setUploading(false));
 };
 const submit=async()=>{
  const e=[];
  if(!title.trim())e.push("제목");
  if(deal!=="wolse"&&!price)e.push(deal==="trade"?"매매가":"전세보증금");
  if(deal==="wolse"&&(!dep||!rent))e.push("보증금/월세");
  if(!phone.trim())e.push("연락처");
  if(role==="agent"){if(!office.trim())e.push("중개사무소명");if(!aname.trim())e.push("중개사 성명");if(!areg.trim())e.push("등록번호");if(!aaddr.trim())e.push("사무소 소재지");}
  if(e.length){setErr(e.join(", ")+" 항목을 확인하세요.");return;}
  setErr("");setBusy(true);
  const body={device_id:deviceId(),poster_role:role,title:title.trim(),deal_type:deal,property_type:prop,lawd_cd:gu,
   dong_name:dong||null,complex_name:cpx||null,address_detail:addr||null,
   exclusive_area:area?+area:null,supply_area:sup?+sup:null,floor:floor?+floor:null,total_floor:tfloor?+tfloor:null,
   rooms:rooms?+rooms:null,baths:baths?+baths:null,direction:dir||null,
   price:deal!=="wolse"?(price?+price:null):null,deposit:deal==="wolse"?(dep?+dep:null):null,monthly_rent:deal==="wolse"?(rent?+rent:null):null,
   maintenance_fee:mfee?+mfee:null,maintenance_items:mitems||null,move_in_date:movein||null,approval_date:approval||null,options:opts||null,
   description:desc||null,photos,
   agent_office:office||null,agent_name:aname||null,agent_reg_no:areg||null,agent_phone:phone||null,agent_address:aaddr||null};
  try{const r=await fetch(`${API}/listings${isEdit?`/${initial.id}`:""}`,{method:isEdit?"PUT":"POST",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify(body)});
   if(!r.ok){const j=await r.json().catch(()=>({}));setErr([].concat(j.detail||(isEdit?"수정에 실패했습니다.":"등록에 실패했습니다.")).join(", "));setBusy(false);return;}
   const j=await r.json();onCreated(j.item,isEdit);}
  catch(_e){ onCreated({...body,id:isEdit?initial.id:Date.now(),source:"listing",gu:GU_NAME[gu],dong,is_sample:false,created_at:isEdit?(initial.created_at||new Date().toISOString()):new Date().toISOString()},isEdit); }
 };
 const Sel=({value,set,opts})=>(<select className="sel" style={{width:"100%"}} value={value} onChange={e=>set(e.target.value)}>{opts.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>);
 return (<div style={{marginTop:6}}>
  <BackBtn onBack={onCancel}/>
  <div style={{fontSize:19,fontWeight:800,margin:"6px 2px 0"}}>{isEdit?"매물 수정":"매물 등록"}</div>
  <Notice><b>표시·광고 명시사항</b>(국토부 고시) 기준 항목입니다. 개업공인중개사는 사무소 정보가 필수이며, 허위·과장 광고는 공인중개사법상 제재 대상입니다. 본 서비스는 게시판으로 중개행위를 하지 않습니다.</Notice>

  <div className="card" style={{padding:"14px 14px 16px",marginTop:10}}>
   <LField label="등록 주체" req>
    <div style={{display:"flex",gap:8}}>
     <button className={"tog "+(role==="agent"?"on":"")} onClick={()=>setRole("agent")}>중개업자</button>
     <button className={"tog "+(role==="user"?"on":"")} onClick={()=>setRole("user")}>개인 직거래</button>
    </div>
   </LField>
   <div className="grid2">
    <LField label="거래형태" req><Sel value={deal} set={setDeal} opts={LP_DEALS}/></LField>
    <LField label="매물 종류" req><Sel value={prop} set={setProp} opts={LP_PROPS}/></LField>
   </div>
   <LField label="제목" req><input style={INP} value={title} onChange={e=>setTitle(e.target.value)} placeholder="예: 가경아이파크 84㎡ 남향 로열층"/></LField>

   <FormHead>가격</FormHead>
   {deal==="wolse"?<div className="grid2">
     <LField label="보증금(만원)" req><input style={INP} type="number" value={dep} onChange={e=>setDep(e.target.value)}/></LField>
     <LField label="월세(만원)" req><input style={INP} type="number" value={rent} onChange={e=>setRent(e.target.value)}/></LField>
    </div>
    :<LField label={deal==="trade"?"매매가(만원)":"전세 보증금(만원)"} req><input style={INP} type="number" value={price} onChange={e=>setPrice(e.target.value)}/></LField>}
   <div className="grid2">
    <LField label="관리비(만원/월)"><input style={INP} type="number" value={mfee} onChange={e=>setMfee(e.target.value)}/></LField>
    <LField label="관리비 포함내역"><input style={INP} value={mitems} onChange={e=>setMitems(e.target.value)} placeholder="청소·경비·수도 등"/></LField>
   </div>

   <FormHead>소재지</FormHead>
   <div className="grid2">
    <LField label="구" req><Sel value={gu} set={setGu} opts={Object.entries(GU_NAME)}/></LField>
    <LField label="동(법정동)"><input style={INP} value={dong} onChange={e=>setDong(e.target.value)} placeholder="가경동"/></LField>
   </div>
   <LField label="단지·건물명"><input style={INP} value={cpx} onChange={e=>setCpx(e.target.value)} placeholder="예: 가경아이파크 4단지"/></LField>
   <LField label="상세주소(비공개·연락 후 안내 가능)"><input style={INP} value={addr} onChange={e=>setAddr(e.target.value)} placeholder="지번·동·호 등 (선택)"/></LField>

   <FormHead>면적 · 구조</FormHead>
   <div className="grid2">
    <LField label="전용면적(㎡)"><input style={INP} type="number" value={area} onChange={e=>setArea(e.target.value)}/></LField>
    <LField label="공급면적(㎡)"><input style={INP} type="number" value={sup} onChange={e=>setSup(e.target.value)}/></LField>
    <LField label="해당 층"><input style={INP} type="number" value={floor} onChange={e=>setFloor(e.target.value)}/></LField>
    <LField label="총 층"><input style={INP} type="number" value={tfloor} onChange={e=>setTfloor(e.target.value)}/></LField>
    <LField label="방 수"><input style={INP} type="number" value={rooms} onChange={e=>setRooms(e.target.value)}/></LField>
    <LField label="욕실 수"><input style={INP} type="number" value={baths} onChange={e=>setBaths(e.target.value)}/></LField>
    <LField label="방향"><Sel value={dir} set={setDir} opts={[["","선택"],...DIRECTIONS.map(d=>[d,d])]}/></LField>
    <LField label="입주 가능일"><input style={INP} value={movein} onChange={e=>setMovein(e.target.value)} placeholder="즉시 / 협의 / 날짜"/></LField>
    <LField label="준공일(사용승인)"><input style={INP} value={approval} onChange={e=>setApproval(e.target.value)} placeholder="예: 2019-03"/></LField>
    <LField label="옵션"><input style={INP} value={opts} onChange={e=>setOpts(e.target.value)} placeholder="냉장고,에어컨,…"/></LField>
   </div>

   <FormHead>사진</FormHead>
   {photos.length>0&&<div style={{display:"flex",gap:6,flexWrap:"wrap",marginBottom:8}}>
    {photos.map((p,i)=>(<div key={i} style={{position:"relative",width:72,height:72,borderRadius:8,overflow:"hidden",background:"var(--chip)",backgroundImage:`url(${p})`,backgroundSize:"cover",backgroundPosition:"center"}}>
     <button onClick={()=>setPhotos(ph=>ph.filter((_,j)=>j!==i))} aria-label="사진 삭제" style={{position:"absolute",top:2,right:2,width:20,height:20,borderRadius:10,border:"none",background:"rgba(0,0,0,.55)",color:"#fff",fontSize:12,cursor:"pointer",lineHeight:"18px",padding:0}}>×</button>
    </div>))}
   </div>}
   <label style={{display:"inline-flex",alignItems:"center",gap:6,border:"1px dashed "+TEAL,color:TEAL,borderRadius:10,padding:"10px 14px",fontSize:13,fontWeight:700,cursor:"pointer"}}>
    <Icon name="camera" active size={18}/> 사진 추가 (최대 12장)
    <input type="file" aria-label="사진 첨부" accept="image/*" multiple onChange={onPhotos} style={{display:"none"}}/>
   </label>
   {uploading&&<span style={{marginLeft:8,fontSize:12,color:MUTED,fontWeight:600}}>업로드 중…</span>}

   <FormHead>상세 설명</FormHead>
   <textarea style={{...INP,minHeight:84,resize:"vertical",fontFamily:"inherit"}} value={desc} onChange={e=>setDesc(e.target.value)} placeholder="매물 특징, 채광, 교통, 주차 등"/>

   <FormHead>{role==="agent"?"중개업체 정보 (필수)":"연락처"}</FormHead>
   {role==="agent"&&<React.Fragment>
    <div className="grid2">
     <LField label="중개사무소 명칭" req><input style={INP} value={office} onChange={e=>setOffice(e.target.value)}/></LField>
     <LField label="개업공인중개사 성명" req><input style={INP} value={aname} onChange={e=>setAname(e.target.value)}/></LField>
    </div>
    <LField label="등록번호" req><input style={INP} value={areg} onChange={e=>setAreg(e.target.value)} placeholder="예: 43113-2024-00012"/></LField>
    <LField label="사무소 소재지" req><input style={INP} value={aaddr} onChange={e=>setAaddr(e.target.value)}/></LField>
   </React.Fragment>}
   <LField label="연락처(전화)" req><input style={INP} value={phone} onChange={e=>setPhone(e.target.value)} placeholder="010-0000-0000"/></LField>

   {err&&<div style={{color:UP,fontWeight:700,fontSize:13,margin:"6px 0 0"}}>{err}</div>}
   <button onClick={submit} disabled={busy} className="btn-primary" style={{marginTop:14,width:"100%",fontSize:15,padding:"13px"}}>{busy?(isEdit?"저장 중…":"등록 중…"):(isEdit?"수정 저장":"매물 등록하기")}</button>
   <div style={{fontSize:11,color:MUTED,marginTop:8,lineHeight:1.6}}>등록 시 표시·광고 명시사항과 허위매물 금지에 동의하는 것으로 간주합니다. 연락처는 매물 상세에 공개됩니다. 입력 정보는 매물 게시 목적에만 사용됩니다.</div>
  </div>
  <div style={{height:16}}/>
 </div>);
}
function LRow({label,val}){
 if(val==null||val==="")return null;
 return <div style={{display:"flex",padding:"7px 0",borderBottom:"1px solid rgba(99,120,128,.10)"}}>
  <span style={{color:MUTED,fontSize:13,minWidth:96,flex:"none"}}>{label}</span>
  <span style={{fontWeight:600,fontSize:13.5,overflowWrap:"anywhere"}}>{val}</span></div>;
}
function InquiryBox({listing}){
 const [open,setOpen]=useState(false);
 const [name,setName]=useState("");
 const [contact,setContact]=useState("");
 const [msg,setMsg]=useState("");
 const [agree,setAgree]=useState(false);
 const [sending,setSending]=useState(false);
 const [done,setDone]=useState(false);
 const [err,setErr]=useState("");
 const submit=()=>{
  setErr("");
  if(!contact.trim()||!msg.trim()){setErr("연락처와 문의 내용을 입력해 주세요.");return;}
  if(!agree){setErr("연락처 전달 동의가 필요해요.");return;}
  setSending(true);
  fetch(`${API}/inquiries`,{method:"POST",headers:{"Content-Type":"application/json",...authHeader()},
   body:JSON.stringify({listing_id:listing.id,device_id:deviceId(),name:name.trim()||null,contact:contact.trim(),message:msg.trim(),consent:true})})
   .then(r=>r.ok?r.json():r.json().then(j=>Promise.reject(j)))
   .then(()=>setDone(true))
   .catch(j=>setErr((j&&j.detail)||"문의 전송에 실패했어요. 잠시 후 다시 시도해 주세요."))
   .finally(()=>setSending(false));
 };
 if(done)return (<div className="card" style={{padding:16,marginTop:4,textAlign:"center"}}>
   <div style={{fontSize:15,fontWeight:800,color:TEAL}}>문의를 보냈어요 ✓</div>
   <div style={{fontSize:12.5,color:MUTED,marginTop:5}}>등록자가 확인 후 남기신 연락처로 연락드릴 수 있어요.</div>
  </div>);
 return (<div className="card" style={{padding:14,marginTop:4}}>
  {!open
   ? <button onClick={()=>setOpen(true)} style={{width:"100%",border:"none",background:TEAL,color:"#fff",fontWeight:800,fontSize:15,padding:"12px",borderRadius:12,cursor:"pointer"}}>온라인 문의 남기기</button>
   : <div>
      <div style={{fontWeight:800,fontSize:14.5,marginBottom:8}}>문의 남기기</div>
      <input className="inp" aria-label="이름(선택)" placeholder="이름 (선택)" value={name} onChange={e=>setName(e.target.value)} style={{marginBottom:8}}/>
      <input className="inp" aria-label="연락처" placeholder="연락처 (전화·이메일·카카오 ID 등)" value={contact} onChange={e=>setContact(e.target.value)} style={{marginBottom:8}}/>
      <textarea aria-label="문의 내용" placeholder="문의 내용 (예: 방문 가능 시간, 가격 조정 여부 등)" value={msg} onChange={e=>setMsg(e.target.value)} rows={3} style={{...INP,width:"100%",resize:"vertical",marginBottom:8}}/>
      <label style={{display:"flex",alignItems:"flex-start",gap:7,fontSize:12,color:MUTED,cursor:"pointer",marginBottom:6}}>
       <input type="checkbox" checked={agree} onChange={e=>setAgree(e.target.checked)} style={{accentColor:TEAL,width:16,height:16,marginTop:1,flex:"none"}}/>
       <span>남긴 연락처·내용이 <b>등록자(중개사)에게 전달</b>되는 것에 동의합니다. 마케팅·제3자 제공에는 사용되지 않습니다.</span>
      </label>
      {err&&<div style={{fontSize:12,color:UP,marginBottom:6}}>{err}</div>}
      <div style={{display:"flex",gap:8}}>
       <button onClick={()=>setOpen(false)} style={{flex:"none",border:"1px solid var(--line)",background:"var(--surface-2)",color:INK,fontWeight:700,fontSize:13.5,padding:"11px 16px",borderRadius:11,cursor:"pointer"}}>취소</button>
       <button onClick={submit} disabled={sending} style={{flex:1,border:"none",background:sending?MUTED:TEAL,color:"#fff",fontWeight:800,fontSize:14.5,padding:"11px",borderRadius:11,cursor:sending?"default":"pointer"}}>{sending?"보내는 중…":"문의 보내기"}</button>
      </div>
      <div style={{fontSize:11,color:MUTED,marginTop:8,lineHeight:1.5}}>※ 본 서비스는 게시판이며 중개행위가 아닙니다. 문의가 계약을 보장하지 않습니다.</div>
     </div>}
 </div>);
}
function ListingDetail({x,onBack}){
 const unit=useUnit();
 const photos=x.photos||[];
 return (<div style={{marginTop:6}}>
  
  {photos.length>0
   ? <div style={{display:"flex",gap:8,overflowX:"auto",margin:"8px 0 4px",paddingBottom:4}}>
      {photos.map((p,i)=>(<div key={i} style={{width:240,height:170,flex:"none",borderRadius:12,background:`var(--surface-2) url(${p}) center/cover`}}/>))}
     </div>
   : <div style={{margin:"8px 0 4px",height:150,borderRadius:12,background:"var(--chip)",display:"flex",alignItems:"center",justifyContent:"center"}}><Icon name="camera" size={30}/></div>}
  <div style={{display:"flex",alignItems:"center",gap:8,margin:"10px 2px 0",flexWrap:"wrap"}}>
   <span className="pill" style={{background:"rgba(15,118,110,.12)",color:DEAL_COLOR[x.deal_type]||TEAL,fontWeight:800}}>{LP_DEAL[x.deal_type]}</span>
   <span className="pill" style={{background:"var(--chip)",color:MUTED}}>{LP_PROP[x.property_type]}</span>
   <span className="pill" style={{background:x.poster_role==="agent"?"rgba(37,99,216,.15)":"var(--chip)",color:x.poster_role==="agent"?"#5A8DE8":MUTED}}>{x.poster_role==="agent"?"중개업자":"개인 직거래"}</span>
   {x.is_sample&&<span className="pill ex">예시</span>}
  </div>
  <div className="num" style={{fontSize:26,fontWeight:800,margin:"6px 2px 0"}}>{listingPrice(x)}</div>
  <div style={{fontSize:18,fontWeight:800,margin:"6px 2px 0",overflowWrap:"anywhere"}}>{x.title}</div>
  <div style={{fontSize:13,color:MUTED,margin:"2px 2px 0"}}>{x.gu}{x.dong?` ${x.dong}`:""}{x.complex_name?` · ${x.complex_name}`:""}</div>

  <Collapsible icon="doc" defaultOpen={true} title="매물 정보">
   <div style={{padding:"2px 14px 10px"}}>
    <LRow label="전용/공급" val={[x.exclusive_area&&`전용 ${fmtArea(x.exclusive_area,unit)}`,x.supply_area&&`/ 공급 ${fmtArea(x.supply_area,unit)}`].filter(Boolean).join(" ")}/>
    <LRow label="해당/총 층" val={x.floor!=null?`${x.floor}층 / ${x.total_floor||"—"}층`:null}/>
    <LRow label="방·욕실" val={(x.rooms!=null||x.baths!=null)?`방 ${x.rooms??"—"} · 욕실 ${x.baths??"—"}`:null}/>
    <LRow label="방향" val={x.direction}/>
    <LRow label="관리비" val={x.maintenance_fee!=null?`${x.maintenance_fee}만원/월${x.maintenance_items?` (${x.maintenance_items})`:""}`:null}/>
    <LRow label="입주가능일" val={x.move_in_date}/>
    <LRow label="준공일" val={x.approval_date}/>
    <LRow label="옵션" val={x.options}/>
    <LRow label="상세주소" val={x.address_detail}/>
   </div>
  </Collapsible>
  {x.description&&<Collapsible icon="news" defaultOpen={true} title="상세 설명">
   <div style={{padding:"6px 14px 12px",fontSize:14,lineHeight:1.7,whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{x.description}</div>
  </Collapsible>}
  <Collapsible icon="phone" defaultOpen={true} title={x.poster_role==="agent"?"중개업체 정보":"등록자 연락처"}>
   <div style={{padding:"2px 14px 12px"}}>
    {x.poster_role==="agent"&&<React.Fragment>
     <LRow label="중개사무소" val={x.agent_office}/>
     <LRow label="공인중개사" val={x.agent_name}/>
     <LRow label="등록번호" val={x.agent_reg_no}/>
     <LRow label="사무소 소재지" val={x.agent_address}/>
    </React.Fragment>}
    <LRow label="연락처" val={x.agent_phone}/>
    {x.agent_phone&&<a href={`tel:${x.agent_phone}`} style={{display:"flex",alignItems:"center",justifyContent:"center",gap:7,marginTop:12,textDecoration:"none",background:TEAL,color:"#fff",fontWeight:800,fontSize:15,padding:"12px",borderRadius:12}}><Icon name="phone" active size={18}/> 전화 문의</a>}
   </div>
  </Collapsible>
  <InquiryBox listing={x}/>
  <div style={{background:"var(--callout-bg)",color:"var(--callout-fg)",borderRadius:12,padding:"11px 14px",fontSize:11.5,fontWeight:600,lineHeight:1.6,margin:"12px 0"}}>
   ⓘ 등록 매물은 등록자가 제공한 정보로 <b>실거래가 아니며</b> 청주부동산이 검증하지 않습니다. 계약 전 현장 확인·등기부·실거래 시세를 반드시 확인하세요. 허위매물이 의심되면 신고해 주세요.
  </div>
  <div style={{height:16}}/>
 </div>);
}
function ListingsTab({account,onNeedLogin,openId,onConsumeOpen}){
 const [mode,setMode]=useState("list");
 const [sel,setSel]=useState(null);
 const [items,setItems]=useState(null);
 const [hasMore,setHasMore]=useState(false);
 const [loadingMore,setLoadingMore]=useState(false);
 const PAGE=20;
 const [fGu,setFGu]=useState(""),[fDeal,setFDeal]=useState(""),[fProp,setFProp]=useState(""),[mine,setMine]=useState(false);
 const filterParams=React.useCallback(()=>{
  const params=[fGu&&`gu=${fGu}`,fDeal&&`deal_type=${fDeal}`,fProp&&`property_type=${fProp}`].filter(Boolean);
  if(mine){ if(account) params.push("mine=1"); else params.push(`device_id=${deviceId()}`); }
  return params;
 },[fGu,fDeal,fProp,mine,account]);
 const load=React.useCallback(()=>{
  const params=filterParams(); params.push(`limit=${PAGE}`,"offset=0");
  setItems(null); setHasMore(false);
  fetch(`${API}/listings?${params.join("&")}`,{headers:authHeader()}).then(r=>r.json())
   .then(j=>{setItems(j.items||[]);setHasMore(!!j.has_more);})
   .catch(()=>{setItems(DEMO_LISTINGS.filter(x=>(!fGu||x.lawd_cd===fGu)&&(!fDeal||x.deal_type===fDeal)&&(!fProp||x.property_type===fProp)));setHasMore(false);});
 },[filterParams,fGu,fDeal,fProp]);
 const loadMore=React.useCallback(()=>{
  setLoadingMore(true);
  const params=filterParams(); params.push(`limit=${PAGE}`,`offset=${(items||[]).length}`);
  fetch(`${API}/listings?${params.join("&")}`,{headers:authHeader()}).then(r=>r.json())
   .then(j=>{setItems(prev=>[...(prev||[]),...(j.items||[])]);setHasMore(!!j.has_more);})
   .catch(()=>setHasMore(false))
   .finally(()=>setLoadingMore(false));
 },[filterParams,items]);
 useEffect(()=>{load();},[load]);
 useEffect(()=>{
  if(openId==null)return;
  fetch(`${API}/listings/${openId}`).then(r=>r.ok?r.json():null).then(j=>{
   const it=(j&&j.item)?j.item:(j&&j.id?j:null);
   if(it){setSel(it);setMode("detail");}
   else{const d=DEMO_LISTINGS.find(x=>x.id===openId);if(d){setSel(d);setMode("detail");}}
   onConsumeOpen&&onConsumeOpen();
  }).catch(()=>{const d=DEMO_LISTINGS.find(x=>x.id===openId);if(d){setSel(d);setMode("detail");}onConsumeOpen&&onConsumeOpen();});
 },[openId]);
 if(mode==="form")return <ListingForm account={account} onCancel={()=>setMode("list")} onCreated={x=>{setItems(it=>[x,...(it||[])]);setSel(x);setMode("detail");}}/>;
 const Sel=({value,set,opts,ph})=>(<select className="sel" style={{flex:1,minWidth:0}} value={value} onChange={e=>set(e.target.value)}>{[["",ph],...opts].map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>);
 return (<div style={{marginTop:6}}>
  <Notice>등록 매물은 사용자·중개업자가 올린 정보로 <b>실거래가 아니며</b> 검증되지 않습니다. 허위·과장광고에 주의하고, 계약 전 현장·등기·실거래 시세를 꼭 확인하세요.</Notice>
  {!account&&<div style={{display:"flex",alignItems:"center",gap:8,margin:"10px 0 0",background:"rgba(15,118,110,.07)",borderRadius:10,padding:"9px 12px"}}>
   <span style={{fontSize:12.5,color:INK,fontWeight:600}}>로그인하면 내 매물을 계정에 저장·관리할 수 있어요.</span>
   <button onClick={onNeedLogin} className="btn-primary" style={{marginLeft:"auto",fontSize:12.5,padding:"7px 13px",borderRadius:10}}>로그인</button>
  </div>}
  <div style={{display:"flex",gap:6,alignItems:"center",margin:"10px 0 0",flexWrap:"nowrap"}}>
   <Sel value={fDeal} set={setFDeal} opts={LP_DEALS} ph="전체 거래"/>
   <Sel value={fProp} set={setFProp} opts={LP_PROPS} ph="전체 종류"/>
   <Sel value={fGu} set={setFGu} opts={Object.entries(GU_NAME)} ph="전체 구"/>
  </div>
  <div style={{display:"flex",alignItems:"center",margin:"10px 2px 8px"}}>
   <button className={"tog "+(mine?"on":"")} onClick={()=>setMine(m=>!m)}>{account?"내 매물":"내 등록만"}</button>
   <button onClick={()=>setMode("form")} className="btn-primary" style={{marginLeft:"auto",fontSize:13.5,padding:"9px 15px"}}>+ 매물 등록</button>
  </div>
  {items===null?<div style={{marginTop:10}}><SkeletonCard/><SkeletonCard/></div>
   :items.length?<React.Fragment>
     {items.map(x=><ListingCard key={x.id} x={x} onOpen={y=>{setSel(y);setMode("detail");}}/>)}
     {hasMore&&<button onClick={loadMore} disabled={loadingMore} style={{display:"block",width:"100%",margin:"8px 0 2px",border:"1px solid var(--line)",background:"var(--surface-2)",color:INK,fontWeight:700,fontSize:13,padding:"11px",borderRadius:10,cursor:loadingMore?"default":"pointer",opacity:loadingMore?.6:1}}>{loadingMore?"불러오는 중…":"더보기"}</button>}
    </React.Fragment>
   :<div className="card" style={{padding:30}}><Empty action={<button onClick={()=>setMode("form")} className="btn-primary" style={{fontSize:13.5,padding:"10px 18px"}}>+ 매물 등록</button>}>등록된 매물이 없습니다. 첫 매물을 등록해 보세요.</Empty></div>}
  <div style={{height:16}}/>
  {mode==="detail"&&sel&&<ListingSheet x={sel} onClose={()=>setMode("list")}/>}
 </div>);
}

/* ====================== 통합 검색 ====================== */
function demoSearch(term){
 const t=term;
 const complexes=[];const seen={};
 DEMO_TX.filter(x=>x.complex_name&&x.complex_name.includes(t)).forEach(x=>{const k=x.complex_name+x.lawd_cd;if(seen[k])return;seen[k]=1;
  complexes.push({complex_name:x.complex_name,lawd_cd:x.lawd_cd,property_type:x.property_type,gu:GU_NAME[x.lawd_cd],dong:x.dong,latest_amount:x.deal_amount});});
 const regions=[];
 Object.entries(GU_NAME).forEach(([code,name])=>{if(name.includes(t))regions.push({type:"gu",gu:name,lawd_cd:code});});
 const dseen={};
 DEMO_TX.filter(x=>x.dong&&x.dong.includes(t)).forEach(x=>{const k=x.dong+x.lawd_cd;if(dseen[k])return;dseen[k]=1;regions.push({type:"dong",gu:GU_NAME[x.lawd_cd],dong:x.dong,lawd_cd:x.lawd_cd});});
 const listings=DEMO_LISTINGS.filter(l=>[l.title,l.complex_name,l.dong].some(s=>s&&s.includes(t)))
  .map(l=>({id:l.id,title:l.title,deal_type:l.deal_type,property_type:l.property_type,gu:l.gu,dong:l.dong,price:l.price,deposit:l.deposit,monthly_rent:l.monthly_rent,is_sample:true}));
 return {q:term,complexes:complexes.slice(0,8),regions:regions.slice(0,8),listings};
}
function SearchHome({board,recents,onComplex,onGu}){
 const [tab,setTab]=useState("complex");
 const trending=(board&&board.trending&&board.trending.items)||[];
 const guR=(board&&board.gu_ranking)||[];
 const medal=r=>r===1?"🥇":r===2?"🥈":r===3?"🥉":null;
 const isC=tab==="complex";
 return (<div>
  {recents&&recents.length>0&&<div style={{marginTop:8}}>
   <div style={{fontSize:12.5,fontWeight:800,color:MUTED,margin:"4px 2px 7px"}}>최근 본 단지</div>
   <div style={{display:"flex",gap:7,flexWrap:"wrap"}}>
    {recents.slice(0,8).map((r,i)=>{const m=r.meta||{};return (<button key={i} className="tog" style={{fontSize:12.5}}
      onClick={()=>onComplex({complex_name:r.name||m.complex_name,lawd_cd:m.lawd_cd,property_type:m.property_type,gu:m.gu})}>{r.name||m.complex_name}</button>);})}
   </div>
  </div>}
  <div style={{display:"flex",alignItems:"center",margin:"18px 0 8px"}}>
   <div style={{display:"flex",gap:3,background:"var(--chip)",borderRadius:10,padding:3}}>
    {[["complex","단지"],["region","지역"]].map(([k,l])=><button key={k} onClick={()=>setTab(k)} style={{border:"none",cursor:"pointer",fontWeight:800,fontSize:12.5,padding:"7px 16px",borderRadius:8,background:tab===k?"var(--surface-solid)":"transparent",color:tab===k?INK:MUTED}}>{l}</button>)}
   </div>
   <span style={{marginLeft:"auto",fontSize:11.5,color:MUTED,display:"inline-flex",alignItems:"center"}}>집계기준<Info text={isC?"최근 90일 거래 신고가 직전 90일보다 늘어난 단지 순입니다. 조회수가 아니라 실제 거래 건수 기준이에요.":"구별 평단가(만원/평) 중앙값 순위입니다. 최근 집계 기간 실거래 기준."}/></span>
  </div>
  <div style={{fontSize:13,fontWeight:800,margin:"2px 2px 7px"}}>{isC?"🔥 거래 급상승":"🏙 구별 시세 순위 (평단가)"}</div>
  {isC
   ? (trending.length?<div className="card" style={{padding:"2px 4px"}}>{trending.map((it,k)=>{const md=medal(it.rank);return (
      <div key={k} className="txrow" style={{cursor:"pointer"}} tabIndex={0} role="button" onKeyDown={onEnter(()=>onComplex({complex_name:it.name,lawd_cd:it.lawd_cd,property_type:it.property_type}))} onClick={()=>onComplex({complex_name:it.name,lawd_cd:it.lawd_cd,property_type:it.property_type})}>
       <span style={{flex:"none",width:28,textAlign:"center",fontSize:md?18:14,fontWeight:800,color:md?"inherit":MUTED}}>{md||it.rank}</span>
       <div style={{minWidth:0,flex:1}}><div style={{fontWeight:700,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{it.name} {it.contains_sample_data&&<ExBadge/>}</div>
        <div style={{fontSize:11.5,color:MUTED,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{["청주시",(it.gu||"").replace("청주시 ",""),it.dong].filter(Boolean).join(" ")}</div></div>
       <span className="num" style={{flex:"none",fontWeight:800,color:it.delta>0?UP:MUTED,fontSize:12.5}}>{it.delta>0?`▲${it.delta}건`:`${it.recent_count}건`}</span>
      </div>);})}</div>:<Empty>아직 거래 급상승 표본이 충분하지 않아요.</Empty>)
   : (guR.length?<div className="card" style={{padding:"2px 4px"}}>{guR.map((g,k)=>{const md=medal(k+1);return (
      <div key={k} className="txrow" style={{cursor:"pointer"}} tabIndex={0} role="button" onKeyDown={onEnter(()=>onGu(g.gu||g.name))} onClick={()=>onGu(g.gu||g.name)}>
       <span style={{flex:"none",width:28,textAlign:"center",fontSize:md?18:14,fontWeight:800,color:md?"inherit":MUTED}}>{md||(k+1)}</span>
       <div style={{minWidth:0,flex:1}}><div style={{fontWeight:700}}>{(g.gu||g.name||"").replace("청주시 ","")}</div>
        <div style={{fontSize:11.5,color:MUTED}}>거래 {g.count!=null?g.count.toLocaleString("ko-KR")+"건":"—"}</div></div>
       <span className="num" style={{flex:"none",fontWeight:800,fontSize:12.5}}>{g.median_pyeong?won(g.median_pyeong)+"/평":"—"}</span>
      </div>);})}</div>:<Empty>지역 데이터가 없어요.</Empty>)}
 </div>);
}
function SearchOverlay({onClose,onComplex,onGu,onListing,board,recents}){
 const [q,setQ]=useState("");
 const [res,setRes]=useState(null);
 const [loading,setLoading]=useState(false);
 useEffect(()=>{
  const term=q.trim();
  if(!term){setRes(null);setLoading(false);return;}
  setLoading(true);
  const id=setTimeout(()=>{
   fetch(`${API}/search?q=${encodeURIComponent(term)}`).then(r=>r.json())
    .then(j=>{setRes(j);setLoading(false);})
    .catch(()=>{setRes(demoSearch(term));setLoading(false);});
  },220);
  return ()=>clearTimeout(id);
 },[q]);
 const empty=res&&!loading&&(res.regions||[]).length===0&&(res.complexes||[]).length===0&&(res.listings||[]).length===0;
 const header=(<div style={{display:"flex",alignItems:"center",gap:9,padding:"2px 14px 10px"}}>
   <Icon name="search" active size={20}/>
   <input autoFocus value={q} onChange={e=>setQ(e.target.value)} placeholder="단지·지역·매물 검색 (예: 가경아이파크, 복대동)"
     style={{flex:1,border:"none",outline:"none",fontSize:15,background:"none",minWidth:0}}/>
   <button onClick={onClose} style={{border:"none",background:"none",color:MUTED,fontWeight:700,fontSize:14,cursor:"pointer",flex:"none"}}>취소</button>
  </div>);
 return (<SheetShell onClose={onClose} zIndex={122} header={header}>
   {!q.trim()&&<SearchHome board={board} recents={recents} onComplex={onComplex} onGu={onGu}/>}
   {q.trim()&&loading&&!res&&<div style={{marginTop:6}}><SkeletonCard lines={2}/><SkeletonCard lines={2}/></div>}
   {res&&<React.Fragment>
    {(res.regions||[]).length>0&&<div style={{marginTop:8}}>
     <div style={{fontSize:12,fontWeight:800,color:MUTED,margin:"6px 2px 2px"}}>지역</div>
     <div className="card" style={{padding:"2px 12px"}}>
      {res.regions.map((r,i)=>(<div key={i} className="listrow" style={{cursor:"pointer"}} tabIndex={0} role="button" onKeyDown={onEnter(()=>onGu(r.gu))} onClick={()=>onGu(r.gu)}>
       <span style={{width:9,height:9,borderRadius:3,background:guColor(r.gu),display:"inline-block",marginRight:8,flex:"none"}}/>
       <span style={{fontWeight:700}}>{r.type==="dong"?r.dong:r.gu}</span>
       <span style={{color:MUTED,fontSize:12,marginLeft:6}}>{r.type==="dong"?r.gu:"구 전체 시세"}</span>
       <span style={{marginLeft:"auto",color:MUTED}}>›</span>
      </div>))}
     </div>
    </div>}
    {(res.complexes||[]).length>0&&<div style={{marginTop:12}}>
     <div style={{fontSize:12,fontWeight:800,color:MUTED,margin:"6px 2px 2px"}}>단지 <span style={{fontWeight:500}}>(실거래)</span></div>
     <div className="card" style={{padding:"2px 12px"}}>
      {<MoreList items={res.complexes} initial={10} step={10} render={(c,i)=>(<div key={i} className="listrow" style={{cursor:"pointer"}} tabIndex={0} role="button" onKeyDown={onEnter(()=>onComplex({complex_name:c.complex_name,lawd_cd:c.lawd_cd,property_type:c.property_type}))} onClick={()=>onComplex({complex_name:c.complex_name,lawd_cd:c.lawd_cd,property_type:c.property_type})}>
       <div style={{minWidth:0}}><div style={{fontWeight:700,overflow:"hidden",textOverflow:"ellipsis"}}>{c.complex_name}</div>
        <div style={{fontSize:12,color:MUTED}}>{c.gu}{c.dong?` ${c.dong}`:""} · {TYPE_LABEL[c.property_type]||""}</div></div>
       <span style={{marginLeft:"auto",fontWeight:800,flex:"none"}} className="num">{eok(c.latest_amount)}</span>
      </div>)}/>}
     </div>
    </div>}
    {(res.listings||[]).length>0&&<div style={{marginTop:12}}>
     <div style={{fontSize:12,fontWeight:800,color:MUTED,margin:"6px 2px 2px"}}>등록 매물</div>
     <div className="card" style={{padding:"2px 12px"}}>
      {res.listings.map((l,i)=>(<div key={i} className="listrow" style={{cursor:"pointer"}} tabIndex={0} role="button" onKeyDown={onEnter(()=>onListing(l.id))} onClick={()=>onListing(l.id)}>
       <div style={{minWidth:0}}><div style={{fontWeight:700,overflow:"hidden",textOverflow:"ellipsis"}}>{l.title} {l.is_sample&&<ExBadge/>}</div>
        <div style={{fontSize:12,color:MUTED}}>{LP_DEAL[l.deal_type]} · {l.gu}{l.dong?` ${l.dong}`:""}</div></div>
       <span style={{marginLeft:"auto",fontWeight:800,flex:"none"}} className="num">{l.deal_type==="wolse"?`${eok(l.deposit)}/${l.monthly_rent}`:eok(l.price)}</span>
      </div>))}
     </div>
    </div>}
    {empty&&<Empty action={<button className="tog" onClick={()=>setQ("")}>검색어 지우기</button>}>‘{res.q}’에 대한 결과가 없습니다.<br/>오타가 없는지 확인하거나 더 짧게 입력해 보세요.</Empty>}
   </React.Fragment>}
 </SheetShell>);
}

/* ====================== 커뮤니티(게시판) ====================== */
const CAT_LABEL={free:"자유",qa:"질문답변",info:"정보공유",deal:"매물상담",local:"지역소식"};
const CAT_ORDER=["free","qa","info","deal","local"];
const CAT_COLOR={free:"#0F766E",qa:"#1E5FC4",info:"#7A5AF8",deal:"#C8322A",local:"#0E7490"};
function timeAgo(iso){if(!iso)return"";const z=/(Z|[+-]\d\d:?\d\d)$/.test(iso)?iso:iso+"Z";const t=new Date(z).getTime();
 if(isNaN(t))return iso.slice(0,10);const s=(Date.now()-t)/1000;
 if(s<60)return"방금";if(s<3600)return Math.floor(s/60)+"분 전";if(s<86400)return Math.floor(s/3600)+"시간 전";
 if(s<2592000)return Math.floor(s/86400)+"일 전";return iso.slice(0,10);}
const DEMO_POSTS=[
 {id:7001,category:"info",category_label:"정보공유",title:"복대동 신축 입주장 분위기 공유합니다",nickname:"복대동주민",account_id:0,gu:"청주시 흥덕구",lawd_cd:"43113",views:134,like_count:6,comment_count:2,is_sample:true,created_at:"2026-06-16T09:00:00",body:"최근 복대동 신축 단지 입주가 시작되면서 전세 매물이 늘어난 느낌입니다. 실거래는 시세 탭에서 꼭 확인하시고, 직거래는 등기·계약 전 확인 필수예요.",_comments:[{id:1,nickname:"전세찾는중",body:"정보 감사합니다. 시세 탭이랑 같이 보니 도움돼요.",is_sample:true,created_at:"2026-06-16T10:00:00"},{id:2,nickname:"흥덕러",body:"직거래 사기 조심하세요. 꼭 확인!",is_sample:true,created_at:"2026-06-16T11:00:00"}]},
 {id:7002,category:"qa",category_label:"질문답변",title:"서원구 분평동 vs 산남동 실거주 어디가 나을까요?",nickname:"내집마련중",account_id:0,gu:"청주시 서원구",lawd_cd:"43112",views:88,like_count:3,comment_count:1,is_sample:true,created_at:"2026-06-15T09:00:00",body:"둘 다 학군·교통 비슷해 보이는데 실거주 만족도가 궁금합니다. 조언 부탁드려요!",_comments:[{id:3,nickname:"분평동5년차",body:"분평동은 학원가가 가까워 아이 키우기 좋아요.",is_sample:true,created_at:"2026-06-15T12:00:00"}]},
 {id:7003,category:"local",category_label:"지역소식",title:"청원구 오창 쪽 개발 이슈 정리",nickname:"청주소식통",account_id:0,gu:"청주시 청원구",lawd_cd:"43114",views:210,like_count:9,comment_count:0,is_sample:true,created_at:"2026-06-14T09:00:00",body:"오창 일대 교통·산업단지 관련 이야기가 많네요. 공식 발표 기준으로만 판단하시길 권합니다.",_comments:[]},
];
function demoPosts(cat,q,sort){let a=DEMO_POSTS.slice();
 if(cat)a=a.filter(p=>p.category===cat);
 if(q)a=a.filter(p=>p.title.includes(q)||(p.body||"").includes(q));
 a.sort((x,y)=>sort==="popular"?((y.like_count+y.comment_count)-(x.like_count+x.comment_count)):y.created_at.localeCompare(x.created_at));
 return a;}
function CatPill({cat}){return <span className="pill" style={{background:(CAT_COLOR[cat]||TEAL)+"1A",color:CAT_COLOR[cat]||TEAL,fontWeight:800}}>{CAT_LABEL[cat]||cat}</span>;}
function PostCard({p,onOpen,onAuthor}){
 const clickA=onAuthor&&p.account_id?(e)=>{e.stopPropagation();onAuthor(p.account_id);}:undefined;
 return (<div className="feedrow" tabIndex={0} role="button" onKeyDown={onEnter(()=>onOpen(p))} style={{padding:"14px 4px",cursor:"pointer"}} onClick={()=>onOpen(p)}>
  <div style={{display:"flex",gap:10}}>
   {p.thumb&&<div style={{width:62,height:62,flex:"none",borderRadius:9,background:`var(--surface-2) url(${p.thumb}) center/cover`}}/>}
   <div style={{minWidth:0,flex:1}}>
    <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
     <CatPill cat={p.category}/>{p.gu&&<span style={{fontSize:11.5,color:MUTED}}>{(p.gu||"").replace("청주시 ","")}</span>}
     {p.complex_name&&<span className="pill" style={{background:"var(--chip)",color:MUTED,fontWeight:700}}>📍 {p.complex_name}</span>}
     {p.resident&&<span className="pill" title="작성 당시 '우리집'으로 등록된 단지의 글(자가 등록 기반)" style={{background:"rgba(15,118,110,.13)",color:TEAL,fontWeight:800}}>🏠 주민</span>}
     {p.is_sample&&<ExBadge/>}
    </div>
    <div style={{fontWeight:700,marginTop:5,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{p.title}</div>
    <div style={{display:"flex",alignItems:"center",gap:10,marginTop:6,fontSize:12,color:MUTED}}>
     <span onClick={clickA} style={clickA?{cursor:"pointer",fontWeight:700,color:INK}:undefined}>{p.nickname||"회원"}</span><span>· {timeAgo(p.created_at)}</span>
     <span style={{marginLeft:"auto",display:"flex",gap:10}}>
      {p.image_count>0&&<span>📷 {p.image_count}</span>}
      <span>♥ {p.like_count||0}</span><span>💬 {p.comment_count||0}</span><span>👁 {p.views||0}</span>
     </span>
    </div>
   </div>
  </div>
 </div>);
}
function PostForm({account,edit,onCancel,onCreated,onUpdated}){
 const ip=edit||{};
 const [cat,setCat]=useState(ip.category||"free"),[gu,setGu]=useState(ip.complex_name?"":(ip.lawd_cd||"")),[title,setTitle]=useState(ip.title||""),[body,setBody]=useState(ip.body||""),[busy,setBusy]=useState(false),[err,setErr]=useState("");
 const [images,setImages]=useState(ip.images||[]),[uploading,setUploading]=useState(false);
 const [cx,setCx]=useState(ip.complex_name?{complex_name:ip.complex_name,lawd_cd:ip.lawd_cd,property_type:ip.property_type,gu:ip.gu}:null),[cxq,setCxq]=useState(""),[cxRes,setCxRes]=useState([]);
 useEffect(()=>{const t=cxq.trim();if(!t||cx){setCxRes([]);return;}
  const id=setTimeout(()=>{fetch(`${API}/search?q=${encodeURIComponent(t)}`).then(r=>r.json()).then(j=>setCxRes((j.complexes||[]).slice(0,6))).catch(()=>setCxRes(demoSearch(t).complexes.slice(0,6)));},220);
  return ()=>clearTimeout(id);},[cxq,cx]);
 const onImgs=e=>{const files=[...e.target.files].slice(0,8);e.target.value="";if(!files.length)return;setUploading(true);
  Promise.all(files.map(async f=>{try{const fd=new FormData();fd.append("file",f);const r=await fetch(`${API}/listings/upload`,{method:"POST",body:fd});if(r.ok){const j=await r.json();if(j&&j.url)return j.url;}}catch(_){}
   return await new Promise(res=>{const rd=new FileReader();rd.onload=()=>res(rd.result);rd.readAsDataURL(f);});}))
   .then(urls=>{setImages(p=>[...p,...urls].slice(0,8));setUploading(false);}).catch(()=>setUploading(false));};
 const submit=async()=>{
  if(title.trim().length<2)return setErr("제목을 2자 이상 입력하세요.");
  if(body.trim().length<2)return setErr("내용을 2자 이상 입력하세요.");
  setBusy(true);setErr("");
  const payload={device_id:deviceId(),category:cat,title:title.trim(),body:body.trim(),
   lawd_cd:(cx?cx.lawd_cd:gu)||null,complex_name:cx?cx.complex_name:null,property_type:cx?cx.property_type:null,images};
  const url=edit?`${API}/community/posts/${edit.id}`:`${API}/community/posts`;
  try{const r=await fetch(url,{method:edit?"PUT":"POST",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify(payload)});
   if(r.ok){const j=await r.json();setBusy(false);(edit?onUpdated:onCreated)(j.post);return;}
   const e=await r.json().catch(()=>({}));setErr(e.detail||"저장에 실패했습니다.");setBusy(false);return;
  }catch(_){}
  setBusy(false);
  const obj={...(edit||{}),id:edit?edit.id:Math.floor(Math.random()*1e6),category:cat,category_label:CAT_LABEL[cat],title:title.trim(),body:body.trim(),nickname:account?.nickname||"나",account_id:account?.id??0,gu:cx?cx.gu:(gu?GU_NAME[gu]:null),lawd_cd:(cx?cx.lawd_cd:gu)||null,complex_name:cx?cx.complex_name:null,property_type:cx?cx.property_type:null,images,thumb:images[0]||null,image_count:images.length,...(edit?{}:{views:0,like_count:0,comment_count:0,created_at:new Date().toISOString(),_comments:[]})};
  (edit?onUpdated:onCreated)(obj);
 };
 return (<div style={{marginTop:6}}>
  <div style={{fontWeight:800,fontSize:17,margin:"2px 2px 10px"}}>{edit?"글 수정":"글쓰기"}</div>
  <div style={{display:"flex",gap:6}}>
   <select className="sel" style={{flex:1,minWidth:0}} value={cat} onChange={e=>setCat(e.target.value)}>{CAT_ORDER.map(k=><option key={k} value={k}>{CAT_LABEL[k]}</option>)}</select>
   <select className="sel" style={{flex:1,minWidth:0}} value={gu} onChange={e=>setGu(e.target.value)} disabled={!!cx}>{[["","지역(선택)"],...Object.entries(GU_NAME)].map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>
  </div>
  {cx?(<div style={{display:"flex",alignItems:"center",gap:8,marginTop:8,background:"rgba(15,118,110,.07)",borderRadius:10,padding:"9px 12px"}}>
    <span style={{fontWeight:700,fontSize:13}}>📍 {cx.complex_name}</span><span style={{fontSize:12,color:MUTED}}>{(cx.gu||"").replace("청주시 ","")}</span>
    <button onClick={()=>{setCx(null);setCxq("");}} style={{marginLeft:"auto",border:"none",background:"none",color:UP,fontWeight:700,fontSize:12.5,cursor:"pointer"}}>연결 해제</button>
   </div>)
   :(<div style={{marginTop:8}}>
    <input style={INP} value={cxq} onChange={e=>setCxq(e.target.value)} placeholder="단지 연결(선택) — 단지명 검색"/>
    {cxRes.length>0&&<div className="card" style={{padding:"2px 12px",marginTop:6}}>
     {cxRes.map((c,i)=>(<div key={i} className="listrow" style={{cursor:"pointer"}} tabIndex={0} role="button" onKeyDown={onEnter(()=>{setCx(c);setCxRes([]);})} onClick={()=>{setCx(c);setCxRes([]);}}>
      <div style={{minWidth:0}}><div style={{fontWeight:700}}>{c.complex_name}</div><div style={{fontSize:12,color:MUTED}}>{c.gu}{c.dong?` ${c.dong}`:""}</div></div>
      <span style={{marginLeft:"auto",color:MUTED}}>연결</span>
     </div>))}
    </div>}
   </div>)}
  <input style={{...INP,marginTop:8}} value={title} onChange={e=>setTitle(e.target.value)} placeholder="제목"/>
  <textarea style={{...INP,marginTop:8,minHeight:150,resize:"vertical"}} value={body} onChange={e=>setBody(e.target.value)} placeholder="내용을 입력하세요. (실거래·공식정보가 아닌 의견은 사실과 다를 수 있어요)"/>
  <div style={{display:"flex",alignItems:"center",gap:10,marginTop:10,flexWrap:"wrap"}}>
   <label style={{display:"inline-flex",alignItems:"center",gap:6,border:"1px dashed "+TEAL,color:TEAL,fontWeight:700,fontSize:13,padding:"9px 13px",borderRadius:10,cursor:"pointer"}}>
    <Icon name="camera" active size={16}/> 사진 추가 (최대 8장)
    <input type="file" aria-label="사진 첨부" accept="image/*" multiple onChange={onImgs} style={{display:"none"}}/>
   </label>
   {uploading&&<span style={{fontSize:12,color:MUTED,fontWeight:600}}>업로드 중…</span>}
  </div>
  {images.length>0&&<div style={{display:"flex",gap:8,overflowX:"auto",marginTop:10}}>
   {images.map((u,i)=>(<div key={i} style={{position:"relative",width:74,height:74,flex:"none",borderRadius:8,background:`#EEF1F1 url(${u}) center/cover`}}>
    <button onClick={()=>setImages(p=>p.filter((_,j)=>j!==i))} style={{position:"absolute",top:-6,right:-6,width:20,height:20,borderRadius:10,border:"none",background:"#1b2b2b",color:"#fff",fontSize:12,cursor:"pointer"}}>✕</button>
   </div>))}
  </div>}
  {err&&<div style={{color:UP,fontSize:12.5,marginTop:8}}>{err}</div>}
  <div style={{display:"flex",gap:8,marginTop:12}}>
   <button onClick={onCancel} style={{flex:1,border:"1px solid var(--line)",background:"var(--surface-solid)",color:INK,fontWeight:700,fontSize:14,padding:"12px",borderRadius:11,cursor:"pointer"}}>취소</button>
   <button onClick={submit} disabled={busy} style={{flex:2,border:"none",background:TEAL,color:"#fff",fontWeight:800,fontSize:14,padding:"12px",borderRadius:11,cursor:"pointer",opacity:busy?.6:1}}>{busy?"저장 중…":(edit?"수정":"등록")}</button>
  </div>
  <div style={{height:80}}/>
 </div>);
}
function PostDetail({id,account,onBack,onNeedLogin,onChanged,onOpenComplex,onEdit,onOpenAuthor}){
 const [d,setD]=useState(null),[liked,setLiked]=useState(false),[likeN,setLikeN]=useState(0),[bookmarked,setBookmarked]=useState(false);
 const [ctext,setCtext]=useState(""),[busy,setBusy]=useState(false);
 const [replyTo,setReplyTo]=useState(null),[rtext,setRtext]=useState("");
 const [editingC,setEditingC]=useState(null),[etext,setEtext]=useState("");
 const [csort,setCsort]=useState("asc");
 useEffect(()=>{let on=true;setD(null);
  fetch(`${API}/community/posts/${id}?device_id=${deviceId()}`,{headers:authHeader()}).then(r=>r.ok?r.json():Promise.reject()).then(j=>{if(on){setD(j);setLikeN(j.post.like_count||0);setLiked(!!j.liked);setBookmarked(!!j.bookmarked);}})
   .catch(()=>{const p=DEMO_POSTS.find(x=>x.id===id);if(on&&p){setD({post:p,comments:p._comments||[]});setLikeN(p.like_count||0);}});
  return ()=>{on=false;};},[id]);
 if(!d)return <div style={{marginTop:10}}><div style={{height:10}}/><SkeletonCard lines={4}/><SkeletonCard/></div>;
 const p=d.post,mine=account&&p.account_id===account.id;
 const lk={border:"none",background:"none",color:MUTED,fontSize:11.5,cursor:"pointer",padding:0,fontWeight:700};
 const sb={border:"none",background:TEAL,color:"#fff",fontWeight:800,fontSize:13,padding:"0 14px",borderRadius:9,cursor:"pointer",flex:"none"};
 const toggleLike=async()=>{
  try{const r=await fetch(`${API}/community/posts/${id}/like`,{method:"POST",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify({device_id:deviceId()})});
   if(r.ok){const j=await r.json();setLiked(j.liked);setLikeN(j.like_count);return;}}catch(_){}
  setLiked(v=>!v);setLikeN(n=>n+(liked?-1:1));
 };
 const toggleBookmark=async()=>{
  try{const r=await fetch(`${API}/community/posts/${id}/bookmark`,{method:"POST",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify({device_id:deviceId()})});
   if(r.ok){const j=await r.json();setBookmarked(j.bookmarked);return;}}catch(_){}
  setBookmarked(v=>!v);
 };
 const postComment=async(text,parentId,cb)=>{
  if(!account)return onNeedLogin();
  const t=(text||"").trim();if(t.length<1)return;
  setBusy(true);
  try{const r=await fetch(`${API}/community/posts/${id}/comments`,{method:"POST",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify({device_id:deviceId(),body:t,parent_id:parentId||null})});
   if(r.ok){const j=await r.json();setD(s=>({...s,comments:[...s.comments,j.comment]}));setBusy(false);cb&&cb();onChanged&&onChanged();return;}
   const e=await r.json().catch(()=>({}));alert(e.detail||"댓글 등록 실패");setBusy(false);return;
  }catch(_){}
  setD(s=>({...s,comments:[...s.comments,{id:Date.now(),parent_id:parentId||null,nickname:account?.nickname||"나",account_id:account?.id,body:t,created_at:new Date().toISOString()}]}));setBusy(false);cb&&cb();
 };
 const saveEdit=async(cid)=>{const t=etext.trim();if(t.length<1)return;
  try{const r=await fetch(`${API}/community/comments/${cid}`,{method:"PUT",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify({body:t})});
   if(r.ok){setD(s=>({...s,comments:s.comments.map(c=>c.id===cid?{...c,body:t}:c)}));setEditingC(null);return;}
   const e=await r.json().catch(()=>({}));alert(e.detail||"수정 실패");return;
  }catch(_){}
  setD(s=>({...s,comments:s.comments.map(c=>c.id===cid?{...c,body:t}:c)}));setEditingC(null);
 };
 const delComment=async(cid)=>{if(!window.confirm("댓글을 삭제할까요?"))return;
  try{await fetch(`${API}/community/comments/${cid}`,{method:"DELETE",headers:authHeader()});}catch(_){}
  setD(s=>({...s,comments:s.comments.filter(c=>c.id!==cid&&c.parent_id!==cid)}));
 };
 const report=async(type,tid)=>{ if(!window.confirm("신고할까요? 누적 시 자동 숨김됩니다."))return;
  try{await fetch(`${API}/community/${type==="post"?"posts":"comments"}/${tid}/report`,{method:"POST",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify({device_id:deviceId()})});}catch(_){}
  alert("신고가 접수되었습니다.");
 };
 const delPost=async()=>{ if(!window.confirm("글을 삭제할까요?"))return;
  try{await fetch(`${API}/community/posts/${id}`,{method:"DELETE",headers:authHeader()});}catch(_){}
  onChanged&&onChanged();onBack();
 };
 const tops=d.comments.filter(c=>!c.parent_id).slice().sort((a,b)=>csort==="asc"?(a.created_at||"").localeCompare(b.created_at||""):(b.created_at||"").localeCompare(a.created_at||""));
 const repliesOf=pid2=>d.comments.filter(c=>c.parent_id===pid2).slice().sort((a,b)=>(a.created_at||"").localeCompare(b.created_at||""));
 const renderCmt=(c,reply)=>{const cmine=account&&c.account_id===account.id;const editing=editingC===c.id;
  return (<div key={c.id} className="card" style={{padding:"10px 13px",marginBottom:8,marginLeft:reply?20:0,background:reply?"var(--surface-2)":"var(--surface-solid)"}}>
   <div style={{display:"flex",alignItems:"center",gap:8,fontSize:12,color:MUTED}}>
    {reply&&<span style={{color:TEAL,fontWeight:800}}>↳</span>}<b style={{color:INK}}>{c.nickname||"회원"}</b><span>{timeAgo(c.created_at)}</span>{c.is_sample&&<ExBadge/>}
    <span style={{marginLeft:"auto",display:"flex",gap:10}}>
     {!reply&&account&&<button onClick={()=>{setReplyTo(replyTo===c.id?null:c.id);setRtext("");}} style={lk}>답글</button>}
     {cmine&&<button onClick={()=>{setEditingC(c.id);setEtext(c.body);}} style={lk}>수정</button>}
     {cmine?<button onClick={()=>delComment(c.id)} style={{...lk,color:UP}}>삭제</button>:<button onClick={()=>report("comment",c.id)} style={lk}>신고</button>}
    </span>
   </div>
   {editing?(<div style={{display:"flex",gap:6,marginTop:6}}>
      <input aria-label="댓글 수정" style={{...INP,flex:1}} value={etext} onChange={e=>setEtext(e.target.value)} onKeyDown={e=>{if(e.key==="Enter")saveEdit(c.id);}}/>
      <button onClick={()=>saveEdit(c.id)} style={sb}>저장</button>
      <button onClick={()=>setEditingC(null)} style={{...sb,background:"var(--surface-2)",color:TEAL}}>취소</button>
     </div>)
    :<div style={{fontSize:14,marginTop:4,whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{c.body}</div>}
   {replyTo===c.id&&!reply&&<div style={{display:"flex",gap:6,marginTop:8}}>
     <input style={{...INP,flex:1}} value={rtext} onChange={e=>setRtext(e.target.value)} placeholder="답글 입력" onKeyDown={e=>{if(e.key==="Enter")postComment(rtext,c.id,()=>{setRtext("");setReplyTo(null);});}}/>
     <button onClick={()=>postComment(rtext,c.id,()=>{setRtext("");setReplyTo(null);})} style={sb}>등록</button>
    </div>}
  </div>);
 };
 return (<div style={{marginTop:6}}>
  <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
   <CatPill cat={p.category}/>{p.gu&&<span style={{fontSize:12,color:MUTED}}>{(p.gu||"").replace("청주시 ","")}</span>}{p.is_sample&&<ExBadge/>}
  </div>
  <div style={{fontSize:19,fontWeight:800,margin:"8px 2px 4px",overflowWrap:"anywhere"}}>{p.title}</div>
  <div style={{fontSize:12.5,color:MUTED,display:"flex",gap:10,alignItems:"center"}}>
   <span onClick={onOpenAuthor&&p.account_id?()=>onOpenAuthor(p.account_id):undefined} style={onOpenAuthor&&p.account_id?{cursor:"pointer",fontWeight:700,color:INK}:undefined}>{p.nickname||"회원"}</span><span>· {timeAgo(p.created_at)}</span><span>· 조회 {p.views||0}</span>
   {mine&&<span style={{marginLeft:"auto",display:"flex",gap:12}}>
    <button onClick={()=>onEdit&&onEdit(p)} style={{border:"none",background:"none",color:TEAL,fontWeight:700,fontSize:12.5,cursor:"pointer"}}>수정</button>
    <button onClick={delPost} style={{border:"none",background:"none",color:UP,fontWeight:700,fontSize:12.5,cursor:"pointer"}}>삭제</button>
   </span>}
  </div>
  {p.resident&&<div style={{display:"inline-flex",alignItems:"center",gap:6,background:"rgba(15,118,110,.10)",color:TEAL,fontWeight:800,fontSize:12,borderRadius:9,padding:"5px 11px",margin:"8px 0 0"}}>🏠 단지 주민의 글 <span style={{fontWeight:600,color:MUTED}}>· 작성 당시 '우리집' 등록 기준</span></div>}
  <div style={{fontSize:15,lineHeight:1.7,color:INK,margin:"14px 2px",whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{p.body}</div>
  {(p.images&&p.images.length>0)&&<div style={{display:"flex",gap:8,overflowX:"auto",margin:"4px 0 12px"}}>
   {p.images.map((u,i)=>(<div key={i} style={{width:230,height:165,flex:"none",borderRadius:12,background:`#EEF1F1 url(${u}) center/cover`}}/>))}
  </div>}
  {p.complex_name&&p.lawd_cd&&<button onClick={()=>onOpenComplex&&onOpenComplex({complex_name:p.complex_name,lawd_cd:p.lawd_cd,property_type:p.property_type||"apartment"})}
    style={{display:"flex",alignItems:"center",gap:8,width:"100%",border:"1px solid rgba(15,118,110,.3)",background:"rgba(15,118,110,.06)",color:TEAL,fontWeight:800,fontSize:14,padding:"12px 14px",borderRadius:12,cursor:"pointer",margin:"2px 0 12px"}}>
   📍 {p.complex_name} 시세 보기 <span style={{marginLeft:"auto"}}>›</span></button>}
  <div style={{display:"flex",alignItems:"center",gap:10,margin:"4px 0 14px"}}>
   <button onClick={toggleLike} style={{display:"flex",alignItems:"center",gap:6,border:"none",background:liked?"rgba(219,52,43,.10)":"var(--surface-2)",color:liked?UP:MUTED,fontWeight:800,fontSize:13.5,padding:"9px 15px",borderRadius:11,cursor:"pointer"}}><Icon name="heart" active={liked} size={16}/> {likeN}</button>
   <button onClick={toggleBookmark} style={{display:"flex",alignItems:"center",gap:6,border:"none",background:bookmarked?"rgba(15,118,110,.10)":"var(--surface-2)",color:bookmarked?TEAL:MUTED,fontWeight:800,fontSize:13.5,padding:"9px 15px",borderRadius:11,cursor:"pointer"}}><Icon name="bookmark" active={bookmarked} size={16}/> {bookmarked?"스크랩됨":"스크랩"}</button>
   <button onClick={()=>report("post",id)} style={{marginLeft:"auto",border:"none",background:"none",color:MUTED,fontWeight:700,fontSize:12.5,cursor:"pointer"}}>🚩 신고</button>
  </div>
  <Notice>게시글은 사용자가 작성한 <b>의견</b>으로 실거래·공식정보가 아닙니다. 가격·전망 등은 시세·소식 탭의 공식 데이터로 확인하세요.</Notice>
  <div style={{display:"flex",alignItems:"center",margin:"16px 2px 8px"}}>
   <div style={{fontWeight:800,fontSize:15}}>댓글 {d.comments.length}</div>
   {tops.length>1&&<div style={{marginLeft:"auto",display:"flex",gap:8,fontSize:12.5}}>
    <button onClick={()=>setCsort("asc")} style={{border:"none",background:"none",color:csort==="asc"?TEAL:MUTED,fontWeight:csort==="asc"?800:600,cursor:"pointer"}}>등록순</button>
    <button onClick={()=>setCsort("desc")} style={{border:"none",background:"none",color:csort==="desc"?TEAL:MUTED,fontWeight:csort==="desc"?800:600,cursor:"pointer"}}>최신순</button>
   </div>}
  </div>
  {tops.length===0&&<div style={{color:MUTED,fontSize:13,padding:"6px 2px 12px"}}>첫 댓글을 남겨보세요.</div>}
  {tops.map(c=>(<React.Fragment key={c.id}>{renderCmt(c,false)}{repliesOf(c.id).map(r=>renderCmt(r,true))}</React.Fragment>))}
  {account?(<div style={{display:"flex",gap:8,marginTop:8}}>
    <input style={{...INP,flex:1}} value={ctext} onChange={e=>setCtext(e.target.value)} placeholder="댓글을 입력하세요" onKeyDown={e=>{if(e.key==="Enter")postComment(ctext,null,()=>setCtext(""));}}/>
    <button onClick={()=>postComment(ctext,null,()=>setCtext(""))} disabled={busy} className="btn-primary" style={{padding:"0 18px",flex:"none"}}>등록</button>
   </div>)
   :(<button onClick={onNeedLogin} style={{width:"100%",border:"1px dashed "+TEAL,background:"rgba(15,118,110,.06)",color:TEAL,fontWeight:700,fontSize:13.5,padding:"12px",borderRadius:11,cursor:"pointer",marginTop:8}}>로그인하고 댓글 남기기</button>)}
  <div style={{height:80}}/>
  
 </div>);
}
function CommunityTab({account,onNeedLogin,onOpenComplex,openId,onConsumeOpen,section,setSection,listingOpenId,onConsumeListingOpen}){
 const [mode,setMode]=useState("list"),[selId,setSelId]=useState(null);
 const [cat,setCat]=useState(""),[sort,setSort]=useState("recent"),[q,setQ]=useState(""),[qIn,setQIn]=useState("");
 const [items,setItems]=useState(null),[page,setPage]=useState(1),[hasMore,setHasMore]=useState(false);
 const [best,setBest]=useState([]),[view,setView]=useState("all"),[mineData,setMineData]=useState(null),[editPost,setEditPost]=useState(null);
 const [authorId,setAuthorId]=useState(null),[scrap,setScrap]=useState(null);
 const load=useCallback((pg)=>{
  const params=[cat&&`category=${cat}`,q&&`q=${encodeURIComponent(q)}`,`sort=${sort}`,`page=${pg}`].filter(Boolean).join("&");
  fetch(`${API}/community/posts?${params}`).then(r=>r.ok?r.json():Promise.reject()).then(j=>{
   setItems(prev=>pg>1?[...(prev||[]),...j.items]:j.items);setHasMore(!!j.has_more);
  }).catch(()=>{const a=demoPosts(cat,q,sort);setItems(a);setHasMore(false);});
 },[cat,q,sort]);
 useEffect(()=>{if(view==="all"){setItems(null);setPage(1);load(1);}},[cat,q,sort,view,load]);
 useEffect(()=>{fetch(`${API}/community/best`).then(r=>r.ok?r.json():Promise.reject()).then(j=>setBest(j.items||[])).catch(()=>setBest(demoPosts("","","popular").slice(0,3)));},[]);
 const loadMine=useCallback(()=>{setMineData(null);
  fetch(`${API}/community/mine`,{headers:authHeader()}).then(r=>r.ok?r.json():Promise.reject()).then(setMineData)
   .catch(()=>setMineData({posts:(items||[]).filter(p=>account&&p.account_id===account.id),comments:[]}));},[account,items]);
 const loadScrap=useCallback(()=>{setScrap(null);
  const qs=account?"":`?device_id=${deviceId()}`;
  fetch(`${API}/community/bookmarks${qs}`,{headers:authHeader()}).then(r=>r.ok?r.json():Promise.reject()).then(j=>setScrap(j.items||[])).catch(()=>setScrap([]));},[account]);
 useEffect(()=>{if(view==="mine"){if(!account){setView("all");onNeedLogin();return;}loadMine();}if(view==="scrap"){loadScrap();}},[view]);
 useEffect(()=>{if(openId==null)return;setSelId(openId);setMode("detail");onConsumeOpen&&onConsumeOpen();},[openId]);
 const openPost=x=>{setSelId(x.id);setMode("detail");};
 const openAuthor=aid=>{if(aid){setAuthorId(aid);setMode("author");}};
 if(mode==="author"&&authorId!=null)return <AuthorView accountId={authorId} onBack={()=>setMode("list")} onOpenPost={pid=>{setSelId(pid);setMode("detail");}}/>;
 if(mode==="write")return <PostForm account={account} edit={editPost} onCancel={()=>{const e=editPost;setEditPost(null);setMode(e?"detail":"list");}} onCreated={p=>{setMode("detail");setSelId(p.id);setItems(it=>[p,...(it||[])]);}} onUpdated={p=>{setEditPost(null);setSelId(p.id);setMode("detail");setItems(it=>(it||[]).map(x=>x.id===p.id?{...x,...p}:x));}}/>;
 // 렌더 함수(컴포넌트 아님) — 부모 state(cat/view)를 클로저로 잡으므로 렌더 본문 안에 두되, <Comp/> 대신 {renderX()}로 호출해 리마운트를 피한다(CLAUDE.md §10).
 const renderChip=(k,label)=>(<button key={k||"__all"} onClick={()=>setCat(k)} className={"tog "+(cat===k?"on":"")} style={{whiteSpace:"nowrap"}}>{label}</button>);
 const renderTab=(v,label)=>(<button key={v} onClick={()=>setView(v)} style={{border:"none",background:"none",borderBottom:"2.5px solid "+(view===v?TEAL:"transparent"),color:view===v?INK:MUTED,fontWeight:800,fontSize:14,padding:"7px 4px",cursor:"pointer"}}>{label}</button>);
 return (<div style={{marginTop:6}}>
  <div style={{display:"flex",gap:6,background:"var(--chip)",borderRadius:11,padding:4,marginBottom:12}}>
   <button onClick={()=>setSection&&setSection("board")} style={{flex:1,border:"none",cursor:"pointer",fontWeight:700,fontSize:13,padding:"9px 0",borderRadius:8,background:section!=="listing"?"var(--surface-solid)":"transparent",color:section!=="listing"?INK:MUTED,boxShadow:section!=="listing"?"0 1px 3px rgba(30,64,90,.12)":"none"}}>💬 게시판</button>
   <button onClick={()=>setSection&&setSection("listing")} style={{flex:1,border:"none",cursor:"pointer",fontWeight:700,fontSize:13,padding:"9px 0",borderRadius:8,background:section==="listing"?"var(--surface-solid)":"transparent",color:section==="listing"?INK:MUTED,boxShadow:section==="listing"?"0 1px 3px rgba(30,64,90,.12)":"none"}}>🏠 매물</button>
  </div>
  {section==="listing"?<ListingsTab account={account} onNeedLogin={onNeedLogin} openId={listingOpenId} onConsumeOpen={onConsumeListingOpen}/>:<React.Fragment>
  <div style={{display:"flex",alignItems:"center",gap:8}}>
   <div style={{fontWeight:800,fontSize:17}}>게시판</div>
   <span style={{fontSize:12,color:MUTED}}>부동산 소통</span>
   <button onClick={()=>account?setMode("write"):onNeedLogin()} className="btn-primary" style={{marginLeft:"auto",fontSize:13.5,padding:"9px 15px"}}>+ 글쓰기</button>
  </div>
  <div style={{display:"flex",gap:14,borderBottom:"1px solid rgba(99,120,128,.14)",margin:"8px 0 0"}}>
   {renderTab("all","전체글")}{renderTab("scrap","스크랩")}{renderTab("mine","내 활동")}
  </div>
  {view==="mine"?(
   !mineData?<div style={{marginTop:10}}><SkeletonCard/><SkeletonCard/></div>:
   <div style={{marginTop:12}}>
    <div style={{fontWeight:800,fontSize:14,margin:"2px 2px 8px"}}>내가 쓴 글 {mineData.posts.length}</div>
    {mineData.posts.length?mineData.posts.map(p=><PostCard key={p.id} p={p} onOpen={openPost} onAuthor={openAuthor}/>):<div className="card" style={{padding:20}}><Empty>작성한 글이 없습니다.</Empty></div>}
    <div style={{fontWeight:800,fontSize:14,margin:"16px 2px 8px"}}>내가 쓴 댓글 {(mineData.comments||[]).length}</div>
    {(mineData.comments||[]).length?mineData.comments.map(c=>(<div key={c.id} className="card" style={{padding:"11px 13px",marginBottom:8,cursor:"pointer"}} onClick={()=>c.post_id&&openPost({id:c.post_id})}>
      <div style={{fontSize:14,whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{c.body}</div>
      <div style={{fontSize:12,color:MUTED,marginTop:5}}>↳ {c.post_title||"게시글"} · {timeAgo(c.created_at)}</div>
     </div>)):<div className="card" style={{padding:20}}><Empty>작성한 댓글이 없습니다.</Empty></div>}
    <div style={{height:16}}/>
   </div>
  ):view==="scrap"?(
   !scrap?<div style={{marginTop:10}}><SkeletonCard/><SkeletonCard/></div>:
   <div style={{marginTop:12}}>
    {scrap.length?scrap.map(p=><PostCard key={p.id} p={p} onOpen={openPost} onAuthor={openAuthor}/>):<div className="card" style={{padding:24}}><Empty>스크랩한 글이 없습니다. 글 상세에서 북마크로 저장하세요.</Empty></div>}
    <div style={{height:16}}/>
   </div>
  ):(<React.Fragment>
   <div style={{display:"flex",gap:6,overflowX:"auto",margin:"10px 0 0",paddingBottom:2}}>
    {renderChip("","전체")}{CAT_ORDER.map(k=>renderChip(k,CAT_LABEL[k]))}
   </div>
   <div style={{display:"flex",gap:8,alignItems:"center",margin:"10px 0 0"}}>
    <div style={{flex:1,display:"flex",alignItems:"center",gap:7,background:"var(--surface-solid)",border:"1px solid rgba(99,120,128,.16)",borderRadius:10,padding:"8px 11px"}}>
     <Icon name="search" active size={16}/>
     <input value={qIn} onChange={e=>setQIn(e.target.value)} onKeyDown={e=>{if(e.key==="Enter")setQ(qIn.trim());}} placeholder="게시판 검색" style={{flex:1,border:"none",outline:"none",fontSize:13.5,background:"none",minWidth:0}}/>
     {qIn&&<button onClick={()=>{setQIn("");setQ("");}} style={{border:"none",background:"none",color:MUTED,cursor:"pointer",fontSize:13}}>✕</button>}
    </div>
    <select className="sel" style={{flex:"none",width:96}} value={sort} onChange={e=>setSort(e.target.value)}>
     <option value="recent">최신순</option><option value="popular">인기순</option></select>
   </div>
   {(!cat&&!q&&best.length>0)&&<div style={{margin:"12px 0 4px"}}>
    <Collapsible title="🔥 이번 주 베스트" right={<span style={{fontSize:12,color:MUTED,fontWeight:700,marginLeft:2}}>{best.length}</span>} defaultOpen={false}>
     <div style={{padding:"0 6px 6px"}}>{best.map((p,k)=>{const md=k===0?"🥇":k===1?"🥈":k===2?"🥉":null;return (
      <div key={"b"+p.id} className="txrow" tabIndex={0} role="button" onKeyDown={onEnter(()=>openPost(p))} onClick={()=>openPost(p)}>
       <span style={{flex:"none",width:28,textAlign:"center",fontSize:md?18:14,fontWeight:800,color:md?"inherit":MUTED}}>{md||(k+1)}</span>
       <div style={{minWidth:0,flex:1}}>
        <div style={{fontWeight:700,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{p.title}</div>
        <div style={{fontSize:11.5,color:MUTED,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{[(p.gu||"").replace("청주시 ",""),p.complex_name].filter(Boolean).join(" · ")||(p.nickname||"회원")}</div>
       </div>
       <span className="num" style={{flex:"none",fontWeight:800,color:MUTED,fontSize:12.5}}>♥ {p.like_count||0}</span>
      </div>);})}</div>
    </Collapsible>
   </div>}
   <div style={{marginTop:12}}>
    {items===null?<div style={{marginTop:10}}><SkeletonCard/><SkeletonCard/></div>
     :items.length?(<React.Fragment>
       {items.map(p=><PostCard key={p.id} p={p} onOpen={openPost} onAuthor={openAuthor}/>)}
       {hasMore&&<button onClick={()=>{const n=page+1;setPage(n);load(n);}} style={{width:"100%",border:"1px solid var(--line)",background:"var(--surface-solid)",color:INK,fontWeight:700,fontSize:14,padding:"12px",borderRadius:11,cursor:"pointer",marginTop:2}}>더 보기</button>}
      </React.Fragment>)
     :<div className="card" style={{padding:30}}><Empty action={<button onClick={()=>account?setMode("write"):onNeedLogin()} className="btn-primary" style={{fontSize:13.5,padding:"10px 18px"}}>+ 글쓰기</button>}>아직 게시글이 없습니다. 첫 글을 남겨보세요.</Empty></div>}
   </div>
   <div style={{height:16}}/>
  </React.Fragment>)}
  {mode==="detail"&&selId!=null&&<PostSheet id={selId} account={account} onNeedLogin={onNeedLogin} onClose={()=>setMode("list")} onChanged={()=>{load(1);if(view==="mine")loadMine();if(view==="scrap")loadScrap();}} onOpenComplex={onOpenComplex} onEdit={p=>{setEditPost(p);setMode("write");}} onOpenAuthor={openAuthor}/>}
  </React.Fragment>}
 </div>);
}

function PushToggle(){
 const [on,setOn]=useState(false),[busy,setBusy]=useState(false),[msg,setMsg]=useState(""),[sup,setSup]=useState(true);
 useEffect(()=>{let m=true;(async()=>{const s=("serviceWorker" in navigator)&&("PushManager" in window)&&("Notification" in window);if(m)setSup(s);if(s){const o=await pushIsOn();if(m)setOn(o);}})();return ()=>{m=false;};},[]);
 if(!sup)return null;
 const toggle=async()=>{setBusy(true);setMsg("");try{if(on){await disablePush();setOn(false);setMsg("푸시 알림을 껐어요.");}else{await enablePush();setOn(true);setMsg("켜짐! 로그인 상태의 관심 단지 알림을 푸시로 받아요.");}}catch(e){setMsg(e.message||"설정에 실패했어요.");}setBusy(false);};
 return (<div className="card" style={{padding:"11px 13px",marginBottom:10,display:"flex",alignItems:"center",gap:10}}>
  <div style={{minWidth:0}}>
   <div style={{fontWeight:700,fontSize:13.5}}>🔔 푸시 알림 {on?"켜짐":"꺼짐"}</div>
   <div style={{fontSize:11.5,color:MUTED,marginTop:2,lineHeight:1.5}}>{msg||"관심 단지 신고가·새 실거래를 휴대폰 알림으로 받아요."}</div>
  </div>
  <button onClick={toggle} disabled={busy} className={"tog "+(on?"on":"")} style={{marginLeft:"auto",flex:"none"}}>{busy?"…":on?"끄기":"켜기"}</button>
 </div>);
}
function NotificationsOverlay({onClose,onOpenPost,onOpenComplex,onAllRead}){
 const [items,setItems]=useState(null);
 useEffect(()=>{let on=true;
  fetch(`${API}/notifications`,{headers:authHeader()}).then(r=>r.ok?r.json():Promise.reject()).then(j=>{if(on)setItems(j.items||[]);}).catch(()=>{if(on)setItems([]);});
  fetch(`${API}/notifications/read`,{method:"POST",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify({all:true})}).then(()=>onAllRead&&onAllRead()).catch(()=>{});
  return ()=>{on=false;};},[]);
 const open=n=>{
  if((n.type==="transaction"||n.type==="new_high")&&n.complex_name&&onOpenComplex){onOpenComplex({complex_name:n.complex_name,lawd_cd:n.lawd_cd,property_type:n.property_type||"apartment"});return;}
  if(n.post_id&&onOpenPost){onOpenPost(n.post_id);}
 };
 return (<div onClick={onClose} style={{position:"fixed",inset:0,background:"rgba(20,30,35,.4)",zIndex:100,display:"flex",justifyContent:"flex-end"}}>
  <div onClick={e=>e.stopPropagation()} style={{background:"var(--surface-solid)",width:"100%",maxWidth:420,height:"100%",overflowY:"auto",padding:"16px 14px"}}>
   <div style={{display:"flex",alignItems:"center",marginBottom:10}}>
    <div style={{fontWeight:800,fontSize:17}}>알림</div>
    <button onClick={onClose} style={{marginLeft:"auto",border:"none",background:"none",color:MUTED,fontWeight:700,fontSize:14,cursor:"pointer"}}>닫기</button>
   </div>
   <PushToggle/>
   {items===null?<div style={{marginTop:10}}><SkeletonCard/><SkeletonCard/></div>
    :items.length?<div className="card" style={{padding:"0 4px",marginTop:8}}>{items.map(n=>(<div key={n.id} onClick={()=>open(n)} className="feedrow" style={{padding:"12px 9px",cursor:"pointer",borderLeft:n.is_read?"3px solid transparent":"3px solid "+TEAL,borderRadius:n.is_read?0:"0 8px 8px 0"}}>
       <div style={{fontSize:14,color:INK}}>{n.type==="new_high"?"📈 ":n.type==="transaction"?"🏷️ ":""}{n.message||(n.type==="reply"?"답글이 달렸어요":"댓글이 달렸어요")}</div>
       <div style={{fontSize:12,color:MUTED,marginTop:4}}>{timeAgo(n.created_at)}</div>
      </div>))}</div>
    :<div style={{padding:40,textAlign:"center",color:MUTED}}>새 알림이 없습니다.</div>}
  </div>
 </div>);
}
function AuthorView({accountId,onBack,onOpenPost}){
 const [d,setD]=useState(null);
 useEffect(()=>{let on=true;setD(null);
  fetch(`${API}/community/authors/${accountId}`).then(r=>r.ok?r.json():Promise.reject()).then(j=>{if(on)setD(j);})
   .catch(()=>{if(on)setD({nickname:"회원",post_count:0,like_total:0,badge:"회원",posts:[]});});
  return ()=>{on=false;};},[accountId]);
 if(!d)return <div style={{marginTop:10}}><BackBtn onBack={onBack}/><div style={{height:10}}/><SkeletonCard lines={4}/><SkeletonCard/></div>;
 return (<div style={{marginTop:6}}>
  <div className="card" style={{padding:"16px",display:"flex",alignItems:"center",gap:12}}>
   <div style={{width:48,height:48,borderRadius:24,background:TEAL+"22",display:"flex",alignItems:"center",justifyContent:"center",fontWeight:800,color:TEAL,fontSize:18}}>{(d.nickname||"회")[0]}</div>
   <div><div style={{fontWeight:800,fontSize:17,display:"flex",alignItems:"center",gap:6}}>{d.nickname} <span className="pill" style={{background:TEAL+"1A",color:TEAL,fontWeight:800}}>{d.badge}</span></div>
    <div style={{fontSize:12.5,color:MUTED,marginTop:3}}>글 {d.post_count} · 받은 좋아요 {d.like_total}</div></div>
  </div>
  <div style={{fontWeight:800,fontSize:14,margin:"16px 2px 8px"}}>작성한 글</div>
  {d.posts.length?d.posts.map(p=><PostCard key={p.id} p={p} onOpen={x=>onOpenPost(x.id)}/>):<div className="card" style={{padding:24}}><Empty>작성한 글이 없습니다.</Empty></div>}
  <div style={{height:80}}/>
  <BackBtn onBack={onBack}/>
 </div>);
}

/* ====================== 앱 ====================== */
function CompareOverlay({items,onClose,onRemove,onOpen}){
 const [data,setData]=useState(null);
 useEffect(()=>{let on=true;setData(null);
  fetch(`${API}/compare`,{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({items:items.map(i=>({name:i.name,lawd_cd:i.lawd_cd,property_type:i.property_type}))})})
   .then(r=>r.json()).then(j=>{if(on)setData(j.items||[]);})
   .catch(()=>{if(on)setData(items.map(i=>({found:false,name:i.name,gu:i.gu})));});
  return ()=>{on=false;};},[items]);
 const cols=data||items.map(i=>({found:null,name:i.name,gu:i.gu}));
 // 최적값 인덱스(dir: 'min'|'max'). 동률은 강조 안 함.
 const bestIdx=(key,dir)=>{const vs=cols.map(c=>c&&c.found?c[key]:null).filter(v=>v!=null);
  if(vs.length<2)return -1; const ext=dir==="min"?Math.min(...vs):Math.max(...vs);
  if(vs.filter(v=>v===ext).length>1)return -1;
  return cols.findIndex(c=>c&&c.found&&c[key]===ext);};
 const ROWS=[
  {label:"최근 매매가",get:c=>eok(c.latest_amount)},
  {label:"평단가",sub:"만원/평",get:c=>c.ppm_median!=null?c.ppm_median.toLocaleString("ko-KR"):"—",best:bestIdx("ppm_median","min"),hint:"낮을수록 저렴"},
  {label:"전세가율(갭)",get:c=>c.jeonse_ratio!=null?`${c.jeonse_ratio}%`:"—",best:bestIdx("jeonse_ratio","min"),hint:"낮을수록 깡통 위험 적음",risk:true},
  {label:"전고점 대비",get:c=>c.from_peak_pct!=null?`${c.from_peak_pct>0?"+":""}${c.from_peak_pct}%`:"—"},
  {label:"거래량",get:c=>c.trade_count!=null?`${c.trade_count}건`:"—",best:bestIdx("trade_count","max"),hint:"많을수록 거래 활발"},
  {label:"준공연도",get:c=>c.build_year||"—",best:bestIdx("build_year","max"),hint:"신축일수록 유리"},
  {label:"세대수",get:c=>c.households!=null?`${c.households.toLocaleString("ko-KR")}세대`:"—"},
 ];
 return (<div onClick={onClose} style={{position:"fixed",inset:0,background:"rgba(20,30,35,.5)",zIndex:120,display:"flex",alignItems:"flex-end",justifyContent:"center"}}>
  <div onClick={e=>e.stopPropagation()} style={{background:"var(--bg2)",width:"100%",maxWidth:760,borderTopLeftRadius:18,borderTopRightRadius:18,maxHeight:"90vh",overflowY:"auto",padding:"16px 14px 26px"}}>
   <div style={{display:"flex",alignItems:"center",marginBottom:12}}>
    <span style={{fontWeight:800,fontSize:17}}>단지 비교</span>
    <span style={{marginLeft:8,fontSize:12,color:MUTED}}>{items.length}개</span>
    <button onClick={onClose} style={{marginLeft:"auto",border:"none",background:"none",color:MUTED,fontWeight:700,fontSize:14,cursor:"pointer"}}>닫기</button>
   </div>
   {data===null?<div><SkeletonCard lines={4}/><SkeletonCard lines={4}/></div>:
   <div className="card" style={{padding:0,overflowX:"auto"}}>
    <table style={{minWidth:Math.max(340,120+items.length*130)}}>
     <thead><tr>
      <th style={{position:"sticky",left:0,background:"var(--hd)",zIndex:2,minWidth:96}}> </th>
      {cols.map((c,i)=>(<th key={i} style={{textAlign:"left",minWidth:120,verticalAlign:"top"}}>
       <div style={{display:"flex",alignItems:"flex-start",gap:4}}>
        <span onClick={()=>c.found&&onOpen&&onOpen(items[i])} style={{fontWeight:800,fontSize:12.5,color:INK,cursor:c.found?"pointer":"default",overflowWrap:"anywhere"}}>{c.name}</span>
        <button onClick={()=>onRemove(items[i])} title="빼기" style={{marginLeft:"auto",border:"none",background:"none",color:MUTED,cursor:"pointer",fontSize:13,flex:"none"}}>✕</button>
       </div>
       <div style={{fontSize:11,color:MUTED,fontWeight:500,marginTop:1}}>{(c.gu||"").replace("청주시 ","")}{c.found===false?" · 자료 없음":""}{c.contains_sample_data?" · 모의":""}</div>
      </th>))}
     </tr></thead>
     <tbody>{ROWS.map((row,ri)=>(<tr key={ri}>
      <td style={{position:"sticky",left:0,background:"var(--surface-solid)",zIndex:1,fontWeight:700,color:MUTED,fontSize:12.5}}>
       {row.label}{row.sub&&<div style={{fontWeight:500,fontSize:10.5}}>{row.sub}</div>}</td>
      {cols.map((c,i)=>{const isBest=row.best===i;
       const rr=row.risk&&c&&c.found?jeonseRisk(c.jeonse_ratio):null;
       return (<td key={i} className="num" style={{fontWeight:isBest?800:600,fontSize:13.5,
         background:isBest?"rgba(15,118,110,.10)":"transparent",color:rr?rr.fg:INK}}>
        {c&&c.found!==false?row.get(c):"—"}
        {isBest&&<span style={{display:"block",fontSize:9.5,color:TEAL,fontWeight:700}}>최적</span>}
       </td>);})}
     </tr>))}</tbody>
    </table>
   </div>}
   <div style={{fontSize:11,color:MUTED,marginTop:10,lineHeight:1.6}}>지표는 최근 {AGG_MONTHS}개월 실거래 기준. ‘최적’은 항목별 단순 비교(평단가↓·전세가율↓·거래량↑·준공↑)일 뿐 투자 판단이 아닙니다. 신고 지연·정정·해제로 값이 바뀔 수 있습니다.</div>
  </div>
 </div>);
}
class ErrorBoundary extends React.Component{
  constructor(props){super(props);this.state={err:null};}
  static getDerivedStateFromError(err){return {err};}
  componentDidCatch(err,info){try{console.error("[ErrorBoundary]",err,info);}catch(e){}}
  render(){
    if(this.state.err){
      return <div style={{maxWidth:480,margin:"40px auto",padding:"0 16px"}}>
        <div className="card" style={{padding:20,textAlign:"center"}}>
          <div style={{fontSize:30,marginBottom:8}}>⚠️</div>
          <div style={{fontWeight:800,fontSize:16,color:INK,marginBottom:6}}>일시적인 오류가 발생했어요</div>
          <div style={{fontSize:13,color:MUTED,lineHeight:1.6,marginBottom:16}}>화면을 그리는 중 문제가 생겼어요. 새로고침하면 대부분 해결됩니다. 계속되면 잠시 후 다시 시도해 주세요.</div>
          <button onClick={()=>{try{location.reload();}catch(e){this.setState({err:null});}}} style={{border:"none",background:TEAL,color:"#fff",fontWeight:800,fontSize:14,padding:"11px 18px",borderRadius:12,cursor:"pointer"}}>새로고침</button>
        </div>
      </div>;
    }
    return this.props.children;
  }
}
function Splash(){
 const [gone,setGone]=useState(false);
 const [fade,setFade]=useState(false);
 useEffect(()=>{
  const t1=setTimeout(()=>setFade(true),1150);
  const t2=setTimeout(()=>setGone(true),1550);
  return ()=>{clearTimeout(t1);clearTimeout(t2);};
 },[]);
 if(gone)return null;
 return ReactDOM.createPortal(
  <div onClick={()=>setGone(true)} style={{position:"fixed",inset:0,zIndex:9999,background:"linear-gradient(160deg,#1FA594 0%,#0E7C71 100%)",display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",gap:16,opacity:fade?0:1,transition:"opacity .38s ease",cursor:"pointer"}}>
   <div style={{width:104,height:104,borderRadius:26,background:"rgba(255,255,255,.14)",display:"flex",alignItems:"center",justifyContent:"center",boxShadow:"0 8px 30px rgba(0,0,0,.18)"}}>
    <svg width="60" height="60" viewBox="0 0 100 100" aria-hidden="true">
     <polygon points="50,18 84,48 16,48" fill="#fff"/>
     <rect x="27" y="46" width="46" height="34" rx="4" fill="#fff"/>
     <rect x="43" y="60" width="14" height="20" rx="2" fill="#0E7C71"/>
     <rect x="33" y="53" width="9" height="9" rx="1.5" fill="#0E7C71"/>
     <rect x="58" y="53" width="9" height="9" rx="1.5" fill="#0E7C71"/>
    </svg>
   </div>
   <div style={{color:"#fff",fontWeight:800,fontSize:30,letterSpacing:"-0.02em",marginTop:4}}>청집사</div>
   <div style={{color:"rgba(255,255,255,.9)",fontSize:14,fontWeight:600}}>청주 부동산, 한눈에</div>
  </div>, document.body);
}
function OnbDots({n,i}){
 return (<div style={{display:"flex",gap:6,justifyContent:"center"}}>
  {Array.from({length:n}).map((_,k)=><div key={k} style={{width:k===i?22:7,height:7,borderRadius:4,background:k===i?TEAL:"var(--surface-2)",transition:"width .2s"}}/>)}
 </div>);
}
function OnbOption({active,onClick,children,sub}){
 return (<button onClick={onClick} style={{display:"flex",alignItems:"center",gap:10,width:"100%",textAlign:"left",border:active?`1.5px solid ${TEAL}`:"1.5px solid var(--line)",background:active?"rgba(15,118,110,.08)":"var(--surface-solid)",borderRadius:14,padding:"15px 16px",cursor:"pointer",marginBottom:9}}>
  <div style={{minWidth:0,flex:1}}>
   <div style={{fontWeight:800,fontSize:15.5,color:INK}}>{children}</div>
   {sub&&<div style={{fontSize:12.5,color:MUTED,marginTop:2}}>{sub}</div>}
  </div>
  <div style={{width:22,height:22,borderRadius:11,flex:"none",border:active?"none":"2px solid var(--line)",background:active?TEAL:"transparent",display:"flex",alignItems:"center",justifyContent:"center",color:"#fff",fontSize:13,fontWeight:900}}>{active?"✓":""}</div>
 </button>);
}
function OnboardingWizard({onClose,onDone,onOpenComplex}){
 const [step,setStep]=useState(0);
 const [jobs,setJobs]=useState(null);
 const [dest,setDest]=useState(null);
 const [budget,setBudget]=useState(undefined);   // undefined=미선택, null=몰라요, number=만원
 const [kids,setKids]=useState(null);
 const [res,setRes]=useState(null);
 const [loading,setLoading]=useState(false);
 useEffect(()=>{fetch(`${API}/onboarding/options`).then(r=>r.json()).then(j=>setJobs(j.destinations||[])).catch(()=>setJobs([]));},[]);
 const BUD=[[20000,"2억 이하"],[30000,"2~3억대"],[40000,"3~4억대"],[60000,"4억 이상"],[null,"아직 잘 모르겠어요"]];
 const run=()=>{ setLoading(true); setStep(4);
  const q=`dest_key=${encodeURIComponent(dest&&dest.key||"")}&has_kids=${kids?"true":"false"}${(budget!=null)?`&budget=${budget}`:""}&max_minutes=40&limit=8`;
  fetch(`${API}/onboarding/recommend?${q}`).then(r=>r.json()).then(j=>{setRes(j);setLoading(false);}).catch(()=>{setRes({items:[],notice:"결과를 불러오지 못했어요."});setLoading(false);});
 };
 const gap=(v)=>{ if(v==null)return null; if(v<=0)return {t:"자기자본 이내",c:TEAL}; return {t:`+${eok(v)} 더 필요`,c:MUTED}; };
 const wrap={position:"fixed",inset:0,zIndex:200,background:"var(--surface)",display:"flex",flexDirection:"column"};
 const body={flex:1,overflowY:"auto",padding:"8px 20px 20px",WebkitOverflowScrolling:"touch"};
 const foot={padding:"12px 20px calc(16px + env(safe-area-inset-bottom))",borderTop:"1px solid var(--line)",background:"var(--surface)"};
 const Q=({t,s})=>(<div style={{margin:"18px 2px 16px"}}><div style={{fontWeight:800,fontSize:21,letterSpacing:"-0.02em",lineHeight:1.3}}>{t}</div>{s&&<div style={{fontSize:13,color:MUTED,marginTop:6,lineHeight:1.5}}>{s}</div>}</div>);
 return (<div style={wrap}>
  <div style={{display:"flex",alignItems:"center",padding:"14px 16px 6px"}}>
   {step>0&&step<4?<button onClick={()=>setStep(step-1)} aria-label="뒤로" style={{border:"none",background:"transparent",fontSize:20,cursor:"pointer",color:INK,padding:4}}>‹</button>:<div style={{width:28}}/>}
   <div style={{flex:1}}>{step<4&&<OnbDots n={4} i={step}/>}</div>
   <button onClick={onClose} style={{border:"none",background:"transparent",color:MUTED,fontWeight:700,fontSize:13,cursor:"pointer",padding:4}}>{step===4?"닫기":"나중에"}</button>
  </div>

  {step===0&&<React.Fragment>
   <div style={body}>
    <div style={{fontSize:44,marginTop:14}}>🧭</div>
    <Q t={"청주가 처음이세요?"} s={"직장·예산·가족만 알려주시면, 당신에게 맞는 청주 단지와 조심할 점을 정리해드려요. 3가지면 끝나요."}/>
    <div style={{background:"rgba(15,118,110,.07)",borderRadius:12,padding:"12px 14px",fontSize:12.5,color:INK,lineHeight:1.6}}>💡 청집사는 <b>중개·광고 수익이 없어요.</b> 그래서 '이거 사세요'가 아니라, <b>조심할 점까지</b> 솔직하게 알려드릴 수 있어요.</div>
   </div>
   <div style={foot}><button onClick={()=>setStep(1)} className="btn-primary" style={{width:"100%"}}>시작하기</button></div>
  </React.Fragment>}

  {step===1&&<React.Fragment>
   <div style={body}>
    <Q t={"어디로 출퇴근하세요?"} s={"직장·산업단지 기준으로 가까운 단지를 찾아드려요."}/>
    {jobs===null?<SkeletonList rows={4}/>:jobs.length?jobs.map(j=>(
     <OnbOption key={j.key} active={dest&&dest.key===j.key} onClick={()=>setDest(j)} sub={j.gu||undefined}>{j.name}</OnbOption>
    )):<Empty>직장 거점 데이터가 아직 없어요(seed_commute 필요). ‘해당 없음’으로 둘러볼 수 있어요.</Empty>}
    <OnbOption active={dest&&dest.key==="_none"} onClick={()=>setDest({key:"_none",name:"해당 없음"})} sub="그냥 청주를 둘러볼게요">해당 없음 / 아직 미정</OnbOption>
   </div>
   <div style={foot}><button disabled={!dest} onClick={()=>dest&&dest.key==="_none"?(onClose&&onClose()):setStep(2)} className="btn-primary" style={{width:"100%"}}>다음</button></div>
  </React.Fragment>}

  {step===2&&<React.Fragment>
   <div style={body}>
    <Q t={"보유 자금은 어느 정도세요?"} s={"지금 가진 현금 기준이에요. 대출은 별도로, 결과에서 ‘얼마 더 필요한지’를 보여드려요."}/>
    {BUD.map(([v,l])=><OnbOption key={String(v)} active={budget===v} onClick={()=>setBudget(v)}>{l}</OnbOption>)}
   </div>
   <div style={foot}><button disabled={budget===undefined} onClick={()=>setStep(3)} className="btn-primary" style={{width:"100%"}}>다음</button></div>
  </React.Fragment>}

  {step===3&&<React.Fragment>
   <div style={body}>
    <Q t={"함께 사는 자녀가 있나요?"} s={"있으면 어린이집·학원·초품아 같은 육아 환경을 더 챙겨서 볼게요."}/>
    <OnbOption active={kids===true} onClick={()=>setKids(true)} sub="어린이집·학원·초등 도보권을 우선 고려">네, 자녀가 있어요 🧸</OnbOption>
    <OnbOption active={kids===false} onClick={()=>setKids(false)}>아니요 / 해당 없음</OnbOption>
   </div>
   <div style={foot}><button disabled={kids===null} onClick={run} className="btn-primary" style={{width:"100%"}}>결과 보기</button></div>
  </React.Fragment>}

  {step===4&&<React.Fragment>
   <div style={body}>
    <div style={{margin:"10px 2px 14px"}}>
     <div style={{fontWeight:800,fontSize:21,letterSpacing:"-0.02em"}}>{dest&&dest.name&&dest.key!=="_none"?`${dest.name} 근처, 당신을 위한 청주`:"당신을 위한 청주"}</div>
     <div style={{fontSize:12.5,color:MUTED,marginTop:5}}>{kids?"육아 환경까지 고려한 ":""}통근·시세 기준 참고 추천이에요.</div>
    </div>
    {loading?<SkeletonList rows={4}/>:(res&&res.items&&res.items.length)?res.items.map((x,i)=>{const g=gap(x.over_budget_by);return (
     <div key={i} onClick={()=>onOpenComplex&&onOpenComplex({complex_name:x.name,lawd_cd:x.lawd_cd,property_type:x.property_type,gu:x.gu})} role="button" tabIndex={0} onKeyDown={onEnter(()=>onOpenComplex&&onOpenComplex({complex_name:x.name,lawd_cd:x.lawd_cd,property_type:x.property_type,gu:x.gu}))} className="card" style={{padding:"13px 15px",marginBottom:9,cursor:"pointer"}}>
      <div style={{display:"flex",alignItems:"center",gap:8}}>
       <span style={{fontWeight:800,fontSize:15,minWidth:0,flex:1,overflowWrap:"anywhere"}}>{x.name}</span>
       {x.minutes!=null&&<span style={{fontSize:11.5,color:MUTED,flex:"none"}}>🚗 {x.minutes}분</span>}
      </div>
      <div style={{display:"flex",alignItems:"baseline",gap:8,marginTop:6,flexWrap:"wrap"}}>
       {x.latest_amount!=null?<span className="num" style={{fontWeight:800,fontSize:16}}>{eok(x.latest_amount)}</span>:<span style={{fontSize:12.5,color:MUTED}}>최근 실거래 없음</span>}
       {x.mom_pct!=null&&<span style={{fontSize:11.5}}>전월 <Delta v={x.mom_pct}/></span>}
       {g&&<span style={{marginLeft:"auto",fontSize:11.5,fontWeight:800,color:g.c}}>{g.t}</span>}
      </div>
      <div style={{fontSize:11,color:MUTED,marginTop:4}}>{[x.gu,TYPE_LABEL[x.property_type]].filter(Boolean).join(" · ")} · 탭하면 상세·전세가율·주변정보 ›</div>
     </div>);
    }):<Empty>{res&&res.notice?res.notice:"조건에 맞는 단지를 찾지 못했어요. 실거래·거점 데이터가 쌓이면 채워져요."}</Empty>}
    {res&&res.notice&&res.items&&res.items.length>0&&<div style={{fontSize:11,color:MUTED,marginTop:6,lineHeight:1.6}}>ⓘ {res.notice}</div>}
   </div>
   <div style={foot}><button onClick={()=>{onDone&&onDone({dest_key:dest&&dest.key,dest_name:dest&&dest.name,budget:(budget===undefined?null:budget),has_kids:!!kids,done:true,ts:Date.now()});}} className="btn-primary" style={{width:"100%"}}>완료 · 홈으로</button></div>
  </React.Fragment>}
 </div>);
}
function App(){
 const [status,setStatus]=useState("loading");
 const [data,setData]=useState(null);
 const [tab,setTab]=useState("home");
 const [unit,setUnit]=useState("m2");
 const [mapCfg,setMapCfg]=useState({key:"",enabled:false});
 const [sel,setSel]=useState(null);
 const DEV=useMemo(()=>deviceId(),[]);
 const [favs,setFavs]=useState([]);
 const [myGu,setMyGu]=useState("");
 const [recents,setRecents]=useState([]);
 const [swUpdate,setSwUpdate]=useState(false);
 const [searches,setSearches]=useState([]);
 const prefsLoaded=React.useRef(false);
 const [account,setAccount]=useState(null);
 const [authCfg,setAuthCfg]=useState(null);
 const [loginOpen,setLoginOpen]=useState(false);
 const [acctMenu,setAcctMenu]=useState(false);
 const [searchOpen,setSearchOpen]=useState(false);
 const [commuteOpen,setCommuteOpen]=useState(false);
 const [budgetOpen,setBudgetOpen]=useState(false);
 const [loanOpen,setLoanOpen]=useState(false);
 const [agentOpen,setAgentOpen]=useState(false);
 const [openListingId,setOpenListingId]=useState(null);
 const [boardSection,setBoardSection]=useState("board");   // 게시판 내부: board|listing
 const [myHome,setMyHome]=useState(()=>{try{const v=safeStore.get("cj_myhome");return v?JSON.parse(v):null;}catch(e){return null;}});
 const [homePick,setHomePick]=useState(false);   // 검색 오버레이가 '우리집 등록' 모드인지
 const saveMyHome=useCallback((h)=>{setMyHome(h);try{safeStore.set("cj_myhome",h?JSON.stringify(h):"");}catch(e){}},[]);
 const [onbOpen,setOnbOpen]=useState(false);
 const [onb,setOnb]=useState(()=>{try{const v=safeStore.get("cj_onb");return v?JSON.parse(v):null;}catch(e){return null;}});
 const saveOnb=useCallback((o)=>{setOnb(o);try{safeStore.set("cj_onb",o?JSON.stringify(o):"");}catch(e){}},[]);
 useEffect(()=>{ let seen; try{seen=safeStore.get("cj_onb_seen");}catch(e){} if(seen||onb)return;
  const t=setTimeout(()=>setOnbOpen(true),1700); return ()=>clearTimeout(t); },[]);   // 첫 방문 1회 자동 안내(스플래시 후)
 const openHomePick=useCallback(()=>{setHomePick(true);setSearchOpen(true);},[]);
 const [notifOpen,setNotifOpen]=useState(false),[unread,setUnread]=useState(0),[openPostId,setOpenPostId]=useState(null);
 const [fresh,setFresh]=useState(null);
 const [legalDoc,setLegalDoc]=useState(null);
 const [theme,setTheme]=useState(()=>safeStore.get("cj_theme")||"light");
 const [compare,setCompare]=useState(()=>{try{return JSON.parse(safeStore.get("cj_compare")||"[]");}catch(e){return [];}});
 const [compareOpen,setCompareOpen]=useState(false);
 useEffect(()=>{safeStore.set("cj_compare",JSON.stringify(compare));},[compare]);
 const inCompare=useCallback((it)=>compare.some(c=>favId(c)===favId(it)),[compare]);
 const toggleCompare=useCallback((it)=>{setCompare(cur=>{const k=favId(it);
   if(cur.some(c=>favId(c)===k))return cur.filter(c=>favId(c)!==k);
   if(cur.length>=4){alert("비교는 최대 4개까지 가능합니다.");return cur;}
   return [...cur,{name:it.complex_name||it.name,lawd_cd:it.lawd_cd,property_type:it.property_type,gu:it.gu,dong:it.dong}];});},[]);
 useEffect(()=>{try{document.documentElement.dataset.theme=theme;}catch(e){}safeStore.set("cj_theme",theme);},[theme]);
 useEffect(()=>{fetch(`${API}/status/data`).then(r=>r.ok?r.json():null).then(j=>{if(j)setFresh(j);}).catch(()=>{});},[]);
 const refreshUnread=React.useCallback(()=>{ if(!getToken())return setUnread(0);
  fetch(`${API}/notifications/unread_count`,{headers:authHeader()}).then(r=>r.ok?r.json():null).then(j=>{if(j)setUnread(j.unread||0);}).catch(()=>{});
 },[]);
 useEffect(()=>{refreshUnread();},[account,refreshUnread]);
 useEffect(()=>{
  const m=(window.location.hash||"").match(/token=([^&]+)/);
  if(m){setToken(decodeURIComponent(m[1]));try{history.replaceState(null,"",window.location.pathname+window.location.search);}catch(_){}}
  fetch(`${API}/auth/config`).then(r=>r.json()).then(setAuthCfg).catch(()=>setAuthCfg({providers:{},dev_login:true,enabled:true,offline:true}));
  if(getToken())fetch(`${API}/auth/me`,{headers:authHeader()}).then(r=>r.ok?r.json():null).then(j=>{if(j&&j.account)setAccount(j.account);}).catch(()=>{});
 },[]);
 const doSocial=async(p)=>{try{const j=await fetch(`${API}/auth/login/${p}?device_id=${DEV}`).then(r=>r.json());if(j&&j.url){window.location.href=j.url;}else{alert(j&&j.detail?j.detail:"로그인 설정이 필요합니다.");}}catch(_){alert("로그인 준비 중 오류가 발생했습니다.");}};
 const doDev=async(role)=>{const body={device_id:DEV,nickname:"테스트 사용자",role};
  try{const r=await fetch(`${API}/auth/dev-login`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
   if(r.ok){const j=await r.json();setToken(j.token);setAccount(j.account);setLoginOpen(false);return;}}catch(_){}
  setToken("demo-"+role);setAccount({id:0,role,nickname:"테스트 사용자",provider:"dev"});setLoginOpen(false);
 };
 const doLogout=()=>{setToken("");setAccount(null);setAcctMenu(false);fetch(`${API}/auth/logout`,{method:"POST"}).catch(()=>{});};
 const doDeleteAccount=async()=>{
  if(!window.confirm("정말 탈퇴하시겠어요?\n계정과 관심·매물·문의 등 개인 데이터가 영구 삭제되며 되돌릴 수 없어요.\n(작성한 게시글·댓글은 ‘탈퇴한 사용자’로 익명 처리됩니다.)"))return;
  try{
   const r=await fetch(`${API}/auth/account`,{method:"DELETE",headers:{...authHeader(),"Content-Type":"application/json"},body:JSON.stringify({confirm:true})});
   if(!r.ok){const j=await r.json().catch(()=>({}));throw new Error(j.detail||"탈퇴 처리에 실패했어요.");}
   setToken("");setAccount(null);setAcctMenu(false);
   alert("탈퇴가 완료되었어요. 그동안 이용해 주셔서 감사합니다.");
   window.location.reload();
  }catch(e){alert(e.message||"탈퇴 처리 중 오류가 발생했어요.");}
 };
 const changeRole=async(role)=>{setAcctMenu(false);
  try{const r=await fetch(`${API}/auth/role`,{method:"POST",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify({role})});
   if(r.ok){const j=await r.json();if(j.token)setToken(j.token);setAccount(j.account);return;}}catch(_){}
  setAccount(a=>a?{...a,role}:a);
 };
 useEffect(()=>{fetch(`${API}/favorites?device_id=${DEV}`,{headers:authHeader()}).then(r=>r.json()).then(j=>setFavs(j.items||[])).catch(()=>{});},[DEV,account]);
 useEffect(()=>{
  if(!("serviceWorker" in navigator))return;
  var hadController=!!navigator.serviceWorker.controller;  // 첫 설치 땐 false → 배너 안 띄움
  navigator.serviceWorker.ready.then(function(reg){
   reg.addEventListener("updatefound",function(){
    var nw=reg.installing; if(!nw)return;
    nw.addEventListener("statechange",function(){
     if(nw.state==="installed"&&hadController)setSwUpdate(true);  // 새 버전 설치 완료
    });
   });
  }).catch(function(){});
 },[]);
 useEffect(()=>{
  fetch(`${API}/me/prefs?device_id=${DEV}`,{headers:authHeader()}).then(r=>r.json()).then(j=>{const d=j.data||{};if(d.unit)setUnit(d.unit);if(d.my_gu)setMyGu(d.my_gu);if(d.my_home)saveMyHome(d.my_home);if(d.onboarding)saveOnb(d.onboarding);}).catch(()=>{}).finally(()=>{prefsLoaded.current=true;});
  fetch(`${API}/me/recent?device_id=${DEV}`,{headers:authHeader()}).then(r=>r.json()).then(j=>setRecents(j.items||[])).catch(()=>{});
  fetch(`${API}/me/searches?device_id=${DEV}`,{headers:authHeader()}).then(r=>r.json()).then(j=>setSearches(j.items||[])).catch(()=>{});
 },[DEV,account]);
 const saveSearch=useCallback((name,filters)=>{
  const tmp={id:"tmp"+Date.now(),name,filters};
  setSearches(cur=>[tmp,...cur]);
  fetch(`${API}/me/searches`,{method:"POST",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify({device_id:DEV,name,filters})})
   .then(r=>r.json()).then(j=>{if(j&&j.id)setSearches(cur=>cur.map(s=>s.id===tmp.id?{...s,id:j.id}:s));}).catch(()=>{});
 },[DEV]);
 const deleteSearch=useCallback((id)=>{
  setSearches(cur=>cur.filter(s=>s.id!==id));
  if(typeof id==="number")fetch(`${API}/me/searches/${id}?device_id=${DEV}`,{method:"DELETE",headers:authHeader()}).catch(()=>{});
 },[DEV]);
 useEffect(()=>{ if(!prefsLoaded.current)return;
  fetch(`${API}/me/prefs`,{method:"PUT",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify({device_id:DEV,data:{unit,my_gu:myGu,my_home:myHome,onboarding:onb}})}).catch(()=>{});
 },[unit,myGu,myHome,onb,DEV]);
 const isFav=useCallback(tid=>favs.some(f=>f.target_id===tid),[favs]);
 const toggleFav=useCallback((item)=>{
  const tid=favId(item);
  const meta={gu:item.gu,dong:item.dong,property_type:item.property_type,lawd_cd:item.lawd_cd,complex_name:item.complex_name||item.name};
  setFavs(cur=>{
   if(cur.some(f=>f.target_id===tid)){
    fetch(`${API}/favorites?device_id=${DEV}&target_type=complex&target_id=${encodeURIComponent(tid)}`,{method:"DELETE",headers:authHeader()}).catch(()=>{});
    return cur.filter(x=>x.target_id!==tid);
   }
   const row={target_id:tid,target_type:"complex",name:item.complex_name||item.name,meta};
   fetch(`${API}/favorites`,{method:"POST",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify({device_id:DEV,...row})}).catch(()=>{});
   return [row,...cur];
  });
 },[DEV]);
 const toggleRegion=useCallback((gu)=>{
  const tid="region:"+gu;
  setFavs(cur=>{
   if(cur.some(f=>f.target_id===tid)){
    fetch(`${API}/favorites?device_id=${DEV}&target_type=region&target_id=${encodeURIComponent(tid)}`,{method:"DELETE",headers:authHeader()}).catch(()=>{});
    return cur.filter(x=>x.target_id!==tid);
   }
   const row={target_id:tid,target_type:"region",name:gu,meta:{gu}};
   fetch(`${API}/favorites`,{method:"POST",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify({device_id:DEV,...row})}).catch(()=>{});
   return [row,...cur];
  });
 },[DEV]);
 const openComplex=useCallback((it)=>{ if(it&&it.complex_name){ setSel({name:it.complex_name,lawd_cd:it.lawd_cd,property_type:it.property_type,area:(it.exclusive_area!=null?it.exclusive_area:null)});
   const tid=favId(it); const row={target_id:tid,name:it.complex_name,meta:{lawd_cd:it.lawd_cd,property_type:it.property_type,gu:it.gu,dong:it.dong}};
   setRecents(cur=>[row,...cur.filter(r=>r.target_id!==tid)].slice(0,10));
   fetch(`${API}/me/recent`,{method:"POST",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify({device_id:DEV,...row})}).catch(()=>{});
  } },[DEV]);
 const openDetail=openComplex;
 const [priceGu,setPriceGu]=useState("전체");
 const [priceView,setPriceView]=useState("list");   // 시세 탭 내부 뷰: list/map/rank
 const goGu=useCallback((guName)=>{ setPriceGu(guName||"전체"); setPriceView("list"); setSel(null); setTab("map"); window.scrollTo(0,0); },[]);
 useEffect(()=>{fetch(`${API}/config`).then(r=>r.json())
  .then(c=>{setMapCfg({key:c.naver_map_client_id||"",enabled:!!c.map_enabled});if(c.aggregate_months)AGG_MONTHS=c.aggregate_months;if(c.feature_flags)FEATURES={...FEATURES,...c.feature_flags};}).catch(()=>{});},[]);

 const load=useCallback(async()=>{setStatus("loading");
  try{
   const [fd,rk,x,bd]=await Promise.all([
    fetch(`${API}/home/feed?property_type=apartment`).then(r=>r.json()),
    fetch(`${API}/dashboard/ranking?property_type=apartment&limit=60`).then(r=>r.json()),
    fetch(`${API}/transactions?limit=200`).then(r=>r.json()),
    fetch(`${API}/dashboard/board?property_type=apartment`).then(r=>r.json())]);
   setData({contains_sample_data:rk.contains_sample_data,feed:fd,ranking:rk,tx:x.items||[],board:bd});
   setStatus("live");
  }catch(e){setData(DEMO);setStatus("demo");}
 },[]);
 useEffect(()=>{load();},[load]);

 const loadRanking=useCallback(async(type,band="all")=>{try{
  const rk=await fetch(`${API}/dashboard/ranking?property_type=${type}&limit=300&area_band=${band}`).then(r=>r.json());
  setData(p=>({...p,ranking:rk}));}catch(e){setData(p=>({...p,ranking:demoRanking(type,band)}));}},[]);

 const NAV=[["home","홈"],["map","지도"],["subscription","청약"],["board","게시판"],["more","더보기"]];
 return (<UnitCtx.Provider value={unit}><div>
  <Splash/>
  {swUpdate&&<div role="status" style={{position:"fixed",left:0,right:0,bottom:0,zIndex:300}}>
   <div style={{maxWidth:480,margin:"0 auto",display:"flex",alignItems:"center",gap:10,padding:"12px 14px",background:INK,color:"#fff",boxShadow:"0 -4px 16px rgba(0,0,0,.25)"}}>
    <span style={{fontSize:13.5,fontWeight:700,flex:1}}>새 버전이 준비됐어요</span>
    <button onClick={()=>location.reload()} style={{border:"none",background:TEAL,color:"#fff",fontWeight:800,fontSize:13,padding:"8px 14px",borderRadius:9,cursor:"pointer"}}>새로고침</button>
    <button onClick={()=>setSwUpdate(false)} aria-label="닫기" style={{border:"none",background:"transparent",color:"#fff",fontSize:20,lineHeight:1,cursor:"pointer",padding:"0 4px"}}>×</button>
   </div>
  </div>}
  <div style={{background:"var(--bg1)",color:INK}}>
   <div className="wrap" style={{paddingBottom:0,display:"flex",alignItems:"center",gap:10,padding:"12px 16px"}}>
    <span style={{fontWeight:800,fontSize:18,letterSpacing:"-0.02em",flex:"none",color:INK}}>청집사</span>
    <div onClick={()=>setSearchOpen(true)} style={{flex:"0 1 200px",marginLeft:"auto",minWidth:90,display:"flex",alignItems:"center",gap:6,background:"var(--surface-2)",borderRadius:10,padding:"8px 11px",cursor:"text",border:"1px solid var(--line)"}}>
     <Icon name="search" active size={15}/>
     <span style={{color:MUTED,fontSize:12.5,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>단지·지역 검색</span>
    </div>
    {account&&<button onClick={()=>setNotifOpen(true)} aria-label="알림" style={{position:"relative",fontSize:16,padding:"7px 9px",borderRadius:9,border:"none",cursor:"pointer",background:"transparent",color:INK}}>🔔
     {unread>0&&<span style={{position:"absolute",top:-5,right:-5,minWidth:17,height:17,borderRadius:9,background:"#C8322A",color:"#fff",fontSize:10,fontWeight:800,display:"flex",alignItems:"center",justifyContent:"center",padding:"0 4px"}}>{unread>99?"99+":unread}</span>}
    </button>}
    <div style={{position:"relative",flex:"none"}}>
     <button onClick={()=>setAcctMenu(v=>!v)} aria-label="메뉴" style={{fontSize:19,lineHeight:1,padding:"7px 10px",borderRadius:9,border:"none",cursor:"pointer",background:"transparent",color:INK}}>☰</button>
     {acctMenu&&<div onClick={()=>setAcctMenu(false)} style={{position:"fixed",inset:0,zIndex:80}}/>}
     {acctMenu&&<div style={{position:"absolute",right:0,top:"112%",zIndex:90,background:"var(--surface-solid)",borderRadius:12,boxShadow:"0 10px 28px rgba(30,64,90,.22)",padding:6,minWidth:208,color:INK}}>
      <div style={{fontSize:11,color:MUTED,padding:"6px 10px 3px",fontWeight:700}}>설정</div>
      <button onClick={()=>setTheme(t=>t==="dark"?"light":"dark")} style={{display:"flex",alignItems:"center",width:"100%",textAlign:"left",border:"none",background:"none",color:INK,fontWeight:700,fontSize:13.5,padding:"9px 10px",borderRadius:8,cursor:"pointer"}}>다크 모드<span style={{marginLeft:"auto",color:MUTED,fontWeight:600}}>{theme==="dark"?"켜짐 ☀️":"꺼짐 🌙"}</span></button>
      <button onClick={()=>setUnit(u=>u==="m2"?"py":"m2")} style={{display:"flex",alignItems:"center",width:"100%",textAlign:"left",border:"none",background:"none",color:INK,fontWeight:700,fontSize:13.5,padding:"9px 10px",borderRadius:8,cursor:"pointer"}}>면적 단위<span style={{marginLeft:"auto",color:MUTED,fontWeight:600}}>{unit==="m2"?"㎡(제곱미터)":"평"}</span></button>
      <button onClick={()=>{load();setAcctMenu(false);}} style={{display:"block",width:"100%",textAlign:"left",border:"none",background:"none",color:INK,fontWeight:700,fontSize:13.5,padding:"9px 10px",borderRadius:8,cursor:"pointer"}}>새로고침</button>
      <div style={{height:1,background:"rgba(99,120,128,.14)",margin:"5px 6px"}}/>
      {account?<React.Fragment>
        <div style={{fontSize:11,color:MUTED,padding:"4px 10px 3px",fontWeight:700}}>{account.nickname||"내 계정"}{account.role==="agent"?" · 중개":""}</div>
        {account.role==="agent"&&<button onClick={()=>{setAcctMenu(false);setAgentOpen(true);}} style={{display:"block",width:"100%",textAlign:"left",border:"none",background:"rgba(15,118,110,.06)",color:TEAL,fontWeight:800,fontSize:13.5,padding:"9px 10px",borderRadius:8,cursor:"pointer",marginBottom:2}}>📊 중개사 대시보드</button>}
        <button onClick={()=>changeRole("user")} style={{display:"block",width:"100%",textAlign:"left",border:"none",background:account.role==="user"?"rgba(15,118,110,.10)":"none",color:account.role==="user"?TEAL:INK,fontWeight:700,fontSize:13.5,padding:"9px 10px",borderRadius:8,cursor:"pointer"}}>개인 사용자</button>
        <button onClick={()=>changeRole("agent")} style={{display:"block",width:"100%",textAlign:"left",border:"none",background:account.role==="agent"?"rgba(15,118,110,.10)":"none",color:account.role==="agent"?TEAL:INK,fontWeight:700,fontSize:13.5,padding:"9px 10px",borderRadius:8,cursor:"pointer"}}>중개업자</button>
        <button onClick={doLogout} style={{display:"block",width:"100%",textAlign:"left",border:"none",background:"none",color:UP,fontWeight:700,fontSize:13.5,padding:"9px 10px",borderRadius:8,cursor:"pointer"}}>로그아웃</button>
        <button onClick={doDeleteAccount} style={{display:"block",width:"100%",textAlign:"left",border:"none",background:"none",color:MUTED,fontWeight:600,fontSize:12,padding:"7px 10px 4px",borderRadius:8,cursor:"pointer"}}>회원 탈퇴</button>
       </React.Fragment>
       :<button onClick={()=>{setLoginOpen(true);setAcctMenu(false);}} style={{display:"block",width:"100%",textAlign:"left",border:"none",background:"none",color:TEAL,fontWeight:800,fontSize:13.5,padding:"9px 10px",borderRadius:8,cursor:"pointer"}}>로그인</button>}
     </div>}
    </div>
   </div>
  </div>
  <div className="wrap">
   {tab!=="map"&&<Banner status={status} data={data}/>}
   {tab!=="map"&&!sel&&!commuteOpen&&fresh&&fresh.total_transactions>0&&<div style={{fontSize:11.5,color:fresh.stale?UP:MUTED,margin:"-4px 2px 6px",fontWeight:600}}>
    데이터 기준 {fresh.data_as_of||"-"} · {fresh.last_collect_age_hours==null?"갱신정보 없음":(fresh.last_collect_age_hours<24?`${Math.round(fresh.last_collect_age_hours)}시간 전 갱신`:`${Math.round(fresh.last_collect_age_hours/24)}일 전 갱신`)}{fresh.stale?" · ⚠ 갱신 지연":""}
   </div>}
   {!data?<div style={{marginTop:12}}><SkeletonStat/><SkeletonList rows={5}/></div>:
    tab==="home"?<Board board={data.board} favs={favs} onOpen={openComplex} onToggleFav={toggleFav} go={setTab} onGu={goGu} myGu={myGu} setMyGu={setMyGu} recents={recents} onToggleRegion={toggleRegion} feed={data.feed} onCommute={()=>{setCommuteOpen(true);window.scrollTo(0,0);}} onBudget={()=>setBudgetOpen(true)} onLoan={()=>{setLoanOpen(true);window.scrollTo(0,0);}} myHome={myHome} onRegisterHome={openHomePick} onClearHome={()=>saveMyHome(null)} onOnboard={()=>setOnbOpen(true)} onbDone={!!(onb&&onb.done)}/>:
    tab==="price"?<PriceHub view={priceView} setView={setPriceView}
      tx={data.tx} onOpen={openComplex} initialGu={priceGu} searches={searches} onSave={saveSearch} onDelete={deleteSearch}
      d={data} onType={loadRanking} mapCfg={mapCfg} onGu={goGu} favs={favs} demo={status==="demo"}/>:
    tab==="subscription"?<SubscriptionTab/>:
    tab==="board"?<CommunityTab account={account} onNeedLogin={()=>setLoginOpen(true)} onOpenComplex={openComplex} openId={openPostId} onConsumeOpen={()=>setOpenPostId(null)} section={boardSection} setSection={setBoardSection} listingOpenId={openListingId} onConsumeListingOpen={()=>setOpenListingId(null)}/>:
    tab==="map"?<MapHub mapCfg={mapCfg} onOpenComplex={openComplex} inCompare={inCompare} onToggleCompare={toggleCompare}/>:
    tab==="more"?<MoreTab onCommute={()=>{setCommuteOpen(true);window.scrollTo(0,0);}} onBudget={()=>setBudgetOpen(true)} onLoan={()=>{setLoanOpen(true);window.scrollTo(0,0);}} account={account} myHome={myHome} onRegisterHome={openHomePick} onClearHome={()=>saveMyHome(null)} onOpenHome={()=>myHome&&openComplex(myHome)} go={setTab} onLogin={()=>setLoginOpen(true)} onOnboard={()=>setOnbOpen(true)}/>:
    null}
   {tab!=="map"&&<footer style={{marginTop:22,fontSize:11.5,color:MUTED,lineHeight:1.7}}>
    시세 집계(중앙값·평단가·전세가율 등)는 <b>최근 {AGG_MONTHS}개월 실거래</b> 기준입니다. 추이 차트는 보유한 전체 기간을 보여줍니다.<br/>실거래가는 신고 지연·정정·해제가 있을 수 있는 <b>참고용</b> 정보(법적 효력 없음)입니다. 자료: 국토교통부 실거래가.
    <div style={{marginTop:8}}>
     <button onClick={()=>setLegalDoc("privacy")} style={{border:"none",background:"none",color:TEAL,fontWeight:700,fontSize:11.5,cursor:"pointer",padding:0,textDecoration:"underline"}}>개인정보처리방침</button>
     <span style={{margin:"0 7px",color:"#cbd5d8"}}>·</span>
     <button onClick={()=>setLegalDoc("terms")} style={{border:"none",background:"none",color:TEAL,fontWeight:700,fontSize:11.5,cursor:"pointer",padding:0,textDecoration:"underline"}}>이용약관</button>
    </div>
   </footer>}
  </div>
  {!sel&&!commuteOpen&&!budgetOpen&&!loanOpen&&!agentOpen && <div className="nav" role="navigation" aria-label="주요 메뉴"><div className="nav-inner">
   {NAV.map(([k,l])=>(<button key={k} className={"nav-btn "+(tab===k?"on":"")} onClick={()=>setTab(k)}>
    <Icon name={k} active={tab===k} size={24}/>{l}</button>))}
  </div></div>}
  {onbOpen&&<OnboardingWizard
    onClose={()=>{setOnbOpen(false);try{safeStore.set("cj_onb_seen","1");}catch(e){}}}
    onDone={(o)=>{saveOnb(o);setOnbOpen(false);try{safeStore.set("cj_onb_seen","1");}catch(e){}setTab("home");window.scrollTo(0,0);}}
    onOpenComplex={(m)=>{setOnbOpen(false);try{safeStore.set("cj_onb_seen","1");}catch(e){}openComplex(m);}}/>}
  {searchOpen&&<SearchOverlay onClose={()=>{setSearchOpen(false);setHomePick(false);}}
    board={data&&data.board} recents={recents}
    onComplex={it=>{setSearchOpen(false);if(homePick){setHomePick(false);saveMyHome({complex_name:it.complex_name||it.name,lawd_cd:it.lawd_cd,property_type:it.property_type||"apartment",gu:it.gu,dong:it.dong});}else{openComplex(it);}}}
    onGu={g=>{setSearchOpen(false);goGu(g);}}
    onListing={id=>{setSearchOpen(false);setOpenListingId(id);setBoardSection("listing");setTab("board");window.scrollTo(0,0);}}/>}
  {notifOpen&&<NotificationsOverlay onClose={()=>setNotifOpen(false)} onAllRead={()=>setUnread(0)}
    onOpenComplex={it=>{setNotifOpen(false);openComplex(it);window.scrollTo(0,0);}}
    onOpenPost={pid=>{setNotifOpen(false);setOpenPostId(pid);setTab("board");window.scrollTo(0,0);}}/>}
  {legalDoc&&<LegalModal doc={legalDoc} onClose={()=>setLegalDoc(null)}/>}
  {sel&&<DetailSheet sel={sel} mapCfg={mapCfg} onClose={()=>setSel(null)} isFav={isFav} onToggleFav={toggleFav} inCompare={inCompare} onToggleCompare={toggleCompare} onOpen={openComplex}/>}
  {commuteOpen&&<CommuteSheet onClose={()=>setCommuteOpen(false)} onOpen={it=>{setCommuteOpen(false);openComplex(it);}} mapCfg={mapCfg}/>}
  {budgetOpen&&<BudgetSheet onClose={()=>setBudgetOpen(false)} onOpen={it=>{setBudgetOpen(false);openComplex(it);}} favs={favs}/>}
  {loanOpen&&<LoanSheet onClose={()=>setLoanOpen(false)} onOpen={it=>{setLoanOpen(false);openComplex(it);}}/>}
  {agentOpen&&<AgentDashboard onClose={()=>setAgentOpen(false)} account={account} onGoListings={()=>{setAgentOpen(false);setBoardSection("listing");setTab("board");}} onOpenListing={id=>{setAgentOpen(false);setBoardSection("listing");setTab("board");setOpenListingId(id);}}/>}
  {compare.length>0&&!compareOpen&&!sel&&<div style={{position:"fixed",left:0,right:0,bottom:64,zIndex:55,display:"flex",justifyContent:"center",pointerEvents:"none",padding:"0 12px"}}>
   <div style={{pointerEvents:"auto",display:"flex",alignItems:"center",gap:9,background:"var(--surface-solid)",border:"1px solid var(--line)",boxShadow:"0 8px 24px rgba(30,64,90,.2)",borderRadius:999,padding:"7px 9px 7px 15px",maxWidth:"100%"}}>
    <span style={{fontWeight:800,fontSize:13,whiteSpace:"nowrap"}}>비교 {compare.length}개</span>
    <button onClick={()=>setCompareOpen(true)} disabled={compare.length<2} className="tog on" style={{padding:"7px 14px",opacity:compare.length<2?.5:1}}>비교하기</button>
    <button onClick={()=>setCompare([])} className="tog" style={{padding:"7px 11px"}}>비우기</button>
   </div>
  </div>}
  {compareOpen&&<CompareOverlay items={compare} onClose={()=>setCompareOpen(false)}
    onRemove={(it)=>setCompare(cur=>cur.filter(c=>favId(c)!==favId(it)))}
    onOpen={(it)=>{setCompareOpen(false);openComplex({complex_name:it.name,lawd_cd:it.lawd_cd,property_type:it.property_type,gu:it.gu,dong:it.dong});}}/>}
  {loginOpen&&<div onClick={()=>setLoginOpen(false)} style={{position:"fixed",inset:0,background:"rgba(20,30,35,.45)",zIndex:100,display:"flex",alignItems:"flex-end",justifyContent:"center"}}>
   <div onClick={e=>e.stopPropagation()} style={{background:"var(--surface-solid)",width:"100%",maxWidth:460,borderRadius:"20px 20px 0 0",padding:"20px 18px 28px",boxShadow:"0 -8px 30px rgba(0,0,0,.2)"}}>
    <div style={{width:38,height:4,borderRadius:2,background:"#dfe5e5",margin:"0 auto 14px"}}/>
    <div style={{fontWeight:800,fontSize:18}}>로그인</div>
    <div style={{fontSize:12.5,color:MUTED,margin:"4px 0 16px",lineHeight:1.6}}>로그인하면 관심·매물을 계정에 저장해 여러 기기에서 이어볼 수 있어요. 닉네임만 받으며 민감정보는 저장하지 않습니다.</div>
    {authCfg&&authCfg.providers&&authCfg.providers.kakao&&<button onClick={()=>doSocial("kakao")} style={{width:"100%",border:"none",background:"#FEE500",color:"#191600",fontWeight:800,fontSize:15,padding:"13px",borderRadius:12,cursor:"pointer",marginBottom:9}}>카카오로 시작하기</button>}
    {authCfg&&authCfg.providers&&authCfg.providers.naver&&<button onClick={()=>doSocial("naver")} style={{width:"100%",border:"none",background:"#03C75A",color:"#fff",fontWeight:800,fontSize:15,padding:"13px",borderRadius:12,cursor:"pointer",marginBottom:9}}>네이버로 시작하기</button>}
    {(!authCfg||authCfg.dev_login||!(authCfg.providers&&(authCfg.providers.kakao||authCfg.providers.naver)))&&<React.Fragment>
     <div style={{fontSize:11.5,color:MUTED,margin:"12px 0 7px",fontWeight:700}}>또는 개발용 로그인(테스트)</div>
     <div style={{display:"flex",gap:8}}>
      <button onClick={()=>doDev("user")} style={{flex:1,border:"1px solid "+TEAL,background:"rgba(15,118,110,.08)",color:TEAL,fontWeight:800,fontSize:14,padding:"12px",borderRadius:12,cursor:"pointer"}}>개인으로</button>
      <button onClick={()=>doDev("agent")} style={{flex:1,border:"1px solid "+TEAL,background:TEAL,color:"#fff",fontWeight:800,fontSize:14,padding:"12px",borderRadius:12,cursor:"pointer"}}>중개업자로</button>
     </div>
    </React.Fragment>}
    <button onClick={()=>setLoginOpen(false)} style={{width:"100%",border:"none",background:"none",color:MUTED,fontWeight:700,fontSize:13.5,padding:"12px 0 0",cursor:"pointer"}}>닫기</button>
   </div>
  </div>}
 </div></UnitCtx.Provider>);
}
function Banner({status,data}){
 let bg,fg,text;
 if(status==="loading"){bg="#E7EDED";fg=MUTED;text="데이터를 불러오는 중…";}
 else if(status==="live"){const s=data&&data.contains_sample_data;bg=s?"var(--callout-bg)":"#E4F2E8";fg=s?"var(--callout-fg)":"#1d6b3a";
  text=s?"백엔드 연결됨 · 실거래에 모의데이터 포함(is_sample)":"백엔드 연결됨 · 실거래 데이터 표시 중";}
 else{bg="#FFF1E8";fg="#9a4a1f";text="백엔드 미응답 — 내장 예시(모의)데이터 표시 중. 'python run.py' 후 새로고침.";}
 return <div style={{background:bg,color:fg,borderRadius:10,padding:"9px 13px",margin:"12px 0 8px",fontSize:12.5,fontWeight:600}}>
  {status==="live"?"● ":status==="demo"?"▲ ":"… "}{text}</div>;
}

/* ---------------- 임장 도우미 ---------------- */
const TOUR_ITEMS=["채광·향(해 잘 드는지)","소음(도로·층간·주변)","누수·곰팡이·결로 흔적","수압·온수 상태","주차 공간·세대당 대수","단지·복도 관리상태","도보 동선·교통 실제로 걸어보기","주변 편의·소음원(상가 등)","관리비·하자·등기 확인"];
function TourStop({stop,idx,onOpen}){
 const key="cj_tour_"+(stop.id||stop.name);
 const [open,setOpen]=useState(false);
 const [state,setState]=useState(()=>{try{return JSON.parse(safeStore.get(key)||"{}");}catch(e){return {};}});
 const checked=state.checked||{};
 const save=next=>{setState(next);safeStore.set(key,JSON.stringify(next));};
 const toggle=i=>save({...state,checked:{...checked,[i]:!checked[i]}});
 const done=TOUR_ITEMS.filter((_,i)=>checked[i]).length;
 const allDone=done===TOUR_ITEMS.length;
 return (<div className="card" style={{padding:"12px 14px",marginTop:8}}>
  <div style={{display:"flex",alignItems:"center",gap:8}}>
   <span style={{width:22,height:22,borderRadius:11,background:"var(--chip)",color:INK,fontWeight:800,fontSize:12,display:"flex",alignItems:"center",justifyContent:"center",flex:"none"}}>{idx+1}</span>
   <div tabIndex={onOpen?0:undefined} role={onOpen?"button":undefined} onKeyDown={onOpen?onEnter(()=>onOpen(stop.it)):undefined} style={{minWidth:0,cursor:onOpen?"pointer":"default"}} onClick={onOpen?()=>onOpen(stop.it):undefined}>
    <div style={{fontWeight:700,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{stop.name}{onOpen&&<span style={{color:TEAL,fontSize:13}}> ›</span>}</div>
    <div style={{fontSize:12,color:MUTED}}>{[stop.gu?guOf(stop.gu):"",stop.dong,stop.property_type?TYPE_LABEL[stop.property_type]:""].filter(Boolean).join(" · ")}</div>
   </div>
   <span className="pill" style={{marginLeft:"auto",flex:"none",background:allDone?"rgba(15,118,110,.12)":"var(--chip)",color:allDone?TEAL:MUTED,fontWeight:800}}>{done}/{TOUR_ITEMS.length}</span>
  </div>
  <button onClick={()=>setOpen(o=>!o)} style={{marginTop:9,width:"100%",border:"1px solid var(--line)",background:"var(--surface-2)",color:TEAL,fontWeight:700,fontSize:12.5,borderRadius:9,padding:"8px 0",cursor:"pointer"}}>{open?"체크리스트 접기 ▲":"임장 체크리스트 "+(done?`(${done}/${TOUR_ITEMS.length}) `:"")+"▼"}</button>
  {open&&<div style={{marginTop:10}}>
   {TOUR_ITEMS.map((t,i)=>(<div key={i} onClick={()=>toggle(i)} style={{display:"flex",alignItems:"center",gap:9,padding:"7px 2px",cursor:"pointer",borderBottom:"1px solid rgba(99,120,128,.10)"}}>
    <span style={{width:20,height:20,borderRadius:6,flex:"none",border:"2px solid "+(checked[i]?TEAL:"var(--line)"),background:checked[i]?TEAL:"transparent",color:"#fff",fontWeight:800,fontSize:13,display:"flex",alignItems:"center",justifyContent:"center"}}>{checked[i]?"✓":""}</span>
    <span style={{fontSize:13.5,color:checked[i]?MUTED:INK,textDecoration:checked[i]?"line-through":"none"}}>{t}</span>
   </div>))}
   <textarea value={state.memo||""} onChange={e=>save({...state,memo:e.target.value})} placeholder="메모(현장에서 느낀 점·가격 협상 포인트 등)" rows={2}
     style={{width:"100%",boxSizing:"border-box",marginTop:10,border:"1px solid var(--line)",borderRadius:9,padding:"8px 10px",fontSize:13,resize:"vertical",background:"var(--surface-solid)",color:"var(--ink)",fontFamily:"inherit"}}/>
  </div>}
 </div>);
}
function TourSheet({complexes,onClose,onOpen}){
 const stops=(complexes||[]).map(f=>{const m=f.meta||{};return {id:f.target_id||f.name,name:f.name||m.complex_name,gu:m.gu,dong:m.dong,property_type:m.property_type,it:{complex_name:f.name||m.complex_name,lawd_cd:m.lawd_cd,property_type:m.property_type,gu:m.gu,dong:m.dong}};});
 const header=(<div style={{display:"flex",alignItems:"center",padding:"6px 16px 4px",flex:"none"}}><span style={{fontWeight:800,fontSize:16}}>🧭 임장 도우미</span><span onClick={onClose} onKeyDown={onEnter(onClose)} aria-label="닫기" role="button" tabIndex={0} style={{marginLeft:"auto",cursor:"pointer",color:MUTED,fontSize:22,lineHeight:1,fontWeight:600}}>×</span></div>);
 return (<SheetShell onClose={onClose} zIndex={120} header={header}>
  <div style={{fontSize:12.5,color:MUTED,lineHeight:1.6,margin:"2px 2px 4px"}}>관심 단지를 한 번에 둘러볼 <b>임장 코스</b>예요. 단지별 체크리스트와 메모는 이 기기에 저장돼, 현장에서 그대로 확인하며 다닐 수 있어요.</div>
  {stops.length?stops.map((s,i)=><TourStop key={s.id} stop={s} idx={i} onOpen={onOpen}/>):<div className="card" style={{padding:20,marginTop:8}}><Empty>관심 단지를 먼저 ★로 등록하면 임장 코스가 만들어져요.</Empty></div>}
  <div style={{fontSize:10.5,color:MUTED,marginTop:12,lineHeight:1.6}}>※ 체크리스트·메모는 휴대폰에만 저장됩니다(서버 전송 없음). 계약 전 등기부·실거래 시세·하자는 반드시 별도 확인하세요.</div>
 </SheetShell>);
}
/* ---------------- 홈: 대시보드 ---------------- */
function FavList({favs,onOpen,onToggleFav,onGu,onToggleRegion}){
 const [tourOpen,setTourOpen]=useState(false);
 const [quotes,setQuotes]=useState({});
 const cxSig=(favs||[]).filter(f=>f.target_type!=="region").map(f=>`${f.name}|${(f.meta||{}).lawd_cd}`).join(",");
 useEffect(()=>{ let on=true;
  const items=(favs||[]).filter(f=>f.target_type!=="region").map(f=>{const m=f.meta||{};return {name:f.name||m.complex_name,lawd_cd:m.lawd_cd,property_type:m.property_type||"apartment"};}).filter(x=>x.name&&x.lawd_cd);
  if(!items.length){setQuotes({});return;}
  fetch(`${API}/complex/quotes`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({items})}).then(r=>r.json()).then(j=>{ if(!on)return; const map={}; (j.quotes||[]).forEach(q=>{map[`${q.name}|${q.lawd_cd}|${q.property_type}`]=q;}); setQuotes(map); }).catch(()=>{});
  return ()=>{on=false;};
 },[cxSig]);
 if(!favs||!favs.length)return null;
 const regions=favs.filter(f=>f.target_type==="region");
 const complexes=favs.filter(f=>f.target_type!=="region");
 return (<React.Fragment>
  {regions.length>0&&<Collapsible icon="star" defaultOpen={true} title="관심 지역">
   <div style={{padding:"4px 14px"}}>
    {regions.map((f,i)=>{const gu=(f.meta&&f.meta.gu)||f.name;
     return <div key={i} className="listrow">
      <div style={{minWidth:0,cursor:"pointer",display:"flex",alignItems:"center",gap:6}} onClick={()=>onGu&&onGu(gu)}>
       <span style={{width:10,height:10,borderRadius:3,background:guColor(gu),display:"inline-block",flex:"none"}}/>
       <span style={{fontWeight:700}}>{gu}</span><span style={{color:TEAL,fontSize:13}}>›</span>
      </div>
      <button onClick={()=>onToggleRegion&&onToggleRegion(gu)} style={{marginLeft:"auto",border:"none",background:"none",cursor:"pointer",padding:4}} title="관심 지역 해제"><Icon name="star" active size={18}/></button>
     </div>;})}
   </div>
  </Collapsible>}
  {complexes.length>0&&<Collapsible icon="star" defaultOpen={true} title="관심 단지">
   <div style={{padding:"4px 14px"}}>
    <button onClick={()=>setTourOpen(true)} style={{width:"100%",border:"none",background:"rgba(15,118,110,.1)",color:TEAL,fontWeight:800,fontSize:13.5,borderRadius:10,padding:"10px 0",cursor:"pointer",marginBottom:8}}>🧭 임장 도우미 — {complexes.length}곳 코스·체크리스트</button>
    {complexes.map((f,i)=>{const m=f.meta||{};const it={complex_name:f.name||m.complex_name,lawd_cd:m.lawd_cd,property_type:m.property_type,gu:m.gu,dong:m.dong};
     return <div key={i} className="listrow">
      <div style={{minWidth:0,flex:1,cursor:"pointer"}} onClick={()=>onOpen&&onOpen(it)}>
       <span style={{fontWeight:600}}>{f.name}</span>
       <span style={{color:MUTED,fontSize:12,marginLeft:6}}>{m.gu?guOf(m.gu):""}{m.dong?` · ${m.dong}`:""}{m.property_type?` · ${TYPE_LABEL[m.property_type]||""}`:""}</span>
      </div>
      {(()=>{const q=quotes[`${it.complex_name}|${it.lawd_cd}|${it.property_type||"apartment"}`];return q&&q.latest_amount!=null?(
       <span style={{flex:"none",display:"flex",alignItems:"center",gap:6,marginRight:2}}>
        <span className="num" style={{fontWeight:800,fontSize:13.5}}>{eok(q.latest_amount)}</span>
        {q.mom_pct!=null&&<span style={{fontSize:11}}><Delta v={q.mom_pct}/></span>}
       </span>):null;})()}
      <button onClick={()=>onToggleFav&&onToggleFav(it)} style={{flex:"none",border:"none",background:"none",cursor:"pointer",padding:4}} title="관심 해제"><Icon name="star" active size={18}/></button>
     </div>;})}
   </div>
  </Collapsible>}
  {tourOpen&&<TourSheet complexes={complexes} onClose={()=>setTourOpen(false)} onOpen={onOpen}/>}
 </React.Fragment>);
}
function RecentList({recents,onOpen}){
 const [sheet,setSheet]=useState(false);
 if(!recents||!recents.length)return null;
 const list=recents.slice(0,10);
 const cur=list[0];
 const region=r=>{const m=r.meta||{};return [m.gu?guOf(m.gu):"",m.dong,m.property_type?(TYPE_LABEL[m.property_type]||""):""].filter(Boolean).join(" · ");};
 return (<div className="card" style={{padding:0,marginTop:8,overflow:"hidden"}}>
  <div onClick={()=>setSheet(true)} tabIndex={0} role="button" onKeyDown={onEnter(()=>setSheet(true))} style={{display:"flex",alignItems:"center",gap:9,padding:"11px 13px",cursor:"pointer"}}>
   <span className="pill" style={{background:"var(--chip)",color:MUTED,fontWeight:800,fontSize:11.5,flex:"none"}}>🕘 최근 본 단지</span>
   <span style={{fontWeight:700,fontSize:13.5,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",flex:1,minWidth:0}}>{cur.name}</span>
   <span style={{flex:"none",display:"flex",alignItems:"center",gap:6,color:MUTED,fontSize:12.5}}>{list.length}곳<span style={{fontSize:15}}>›</span></span>
  </div>
  {sheet&&<Sheet title="🕘 최근 본 단지" fill onClose={()=>setSheet(false)}>
   {list.map((r,i)=>{const m=r.meta||{};const it={complex_name:r.name||m.complex_name,lawd_cd:m.lawd_cd,property_type:m.property_type,gu:m.gu,dong:m.dong};
    return (<div key={i} className="txrow" tabIndex={0} role="button" onKeyDown={onEnter(()=>{onOpen&&onOpen(it);setSheet(false);})} style={{cursor:"pointer",padding:"13px 6px"}} onClick={()=>{onOpen&&onOpen(it);setSheet(false);}}>
     <div style={{minWidth:0,flex:1}}>
      <div style={{fontWeight:700,fontSize:14.5,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{r.name}</div>
      <div style={{fontSize:12,color:MUTED,marginTop:2,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{["청주시",region(r)].filter(Boolean).join(" ")}</div>
     </div>
     <span style={{flex:"none",color:MUTED,fontSize:18}}>›</span>
    </div>);})}
  </Sheet>}
 </div>);
}
function TodayInfo({feed,go}){
 const f=feed||{};
 const [subs,setSubs]=useState(null);
 useEffect(()=>{let on=true;
  fetch(`${API}/subscription?limit=50`).then(r=>r.json())
   .then(j=>{if(on)setSubs(j.items||[]);})
   .catch(()=>{if(on)setSubs(DEMO_FEED.subscriptions||[]);});
  return ()=>{on=false;};},[]);
 const order={"접수중":0,"접수예정":1,"공고":2,"마감":3};
 const arr=subs||[];
 const pick=[...arr].sort((a,b)=>(order[a.status]??9)-(order[b.status]??9))
   .find(s=>s.status==="접수중"||s.status==="접수예정")||arr[0]||null;
 const sc=st=>st==="접수중"?{bg:"#E4F2E8",fg:"#1d6b3a"}:st==="접수예정"?{bg:"#E7EEF6",fg:"#1E5FC4"}:{bg:"#EEF1F1",fg:MUTED};
 const news=f.news||[], policies=f.policies||[];
 return (<React.Fragment>
  <Collapsible icon="news" defaultOpen={true} title="오늘의 정보">
   <div style={{padding:"4px 14px 10px"}}>
    <div style={{fontSize:11.5,color:MUTED,fontWeight:700,margin:"2px 2px 3px"}}>청약 임박</div>
    {pick?(()=>{const c=sc(pick.status);return (
     <div className="listrow" tabIndex={0} role="button" onKeyDown={onEnter(()=>go&&go("subscription"))} style={{cursor:"pointer"}} onClick={()=>go&&go("subscription")}>
      <div style={{minWidth:0}}>
       <div style={{fontWeight:600,overflow:"hidden",textOverflow:"ellipsis"}}>
        <span className="statusdot" style={{background:c.bg,color:c.fg,marginRight:6}}>{pick.status}</span>{pick.name} {pick.is_sample&&<ExBadge/>}</div>
       <div style={{fontSize:12,color:MUTED,marginTop:1}}>{[pick.location,pick.period].filter(Boolean).join(" · ")}</div>
      </div>
      <span style={{marginLeft:"auto",color:MUTED,fontSize:18}}>›</span>
     </div>);})():<div style={{fontSize:12,color:MUTED,padding:"2px 2px 4px"}}>{subs===null?"불러오는 중…":"임박한 청약이 없습니다."}</div>}
    <button onClick={()=>go&&go("subscription")} style={{marginTop:9,width:"100%",border:"1px solid rgba(99,120,128,.2)",background:"transparent",color:TEAL,fontWeight:700,fontSize:12,borderRadius:9,padding:"8px 0",cursor:"pointer"}}>청약 전체 보기 →</button>
   </div>
  </Collapsible>

  <Collapsible icon="news" defaultOpen={true} title="부동산 뉴스">
   <div style={{padding:"4px 14px"}}>
   {news.length?news.map((n,i)=>{const inner=(<React.Fragment>
     <div style={{minWidth:0}}>
      <div style={{fontWeight:600,overflow:"hidden",textOverflow:"ellipsis"}}>{n.title} {n.is_sample&&<ExBadge/>}</div>
      {n.summary&&<div style={{fontSize:12,color:MUTED,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{n.summary}</div>}
      <div style={{fontSize:11.5,color:MUTED,marginTop:1}}>{n.source} · {n.date}</div>
     </div>
     <span style={{marginLeft:"auto",color:MUTED,fontSize:18}}>›</span>
    </React.Fragment>);
    return (n.url&&n.url!=="#")
     ? <a key={i} className="listrow" href={n.url} target="_blank" rel="noopener noreferrer" style={{textDecoration:"none",color:"inherit"}}>{inner}</a>
     : <div key={i} className="listrow">{inner}</div>;}):<Empty>표시할 뉴스가 없습니다.</Empty>}
   </div>
  </Collapsible>

  {policies.length>0&&<Collapsible icon="doc" defaultOpen={false} title="정책·지원">
   <div style={{padding:"4px 14px"}}>
   {policies.map((p2,i)=>(<div key={i} className="listrow" style={{alignItems:"flex-start"}}>
    <div style={{minWidth:0}}>
     <div style={{fontWeight:600}}>{p2.title} {p2.is_sample&&<ExBadge/>}</div>
     <div style={{fontSize:12.5,color:MUTED,marginTop:2}}>{p2.summary}</div>
     <div style={{fontSize:11.5,color:MUTED,marginTop:2}}>{p2.source} · {p2.date}</div>
    </div>
   </div>))}
   </div>
  </Collapsible>}
 </React.Fragment>);
}
function LandmarkCarousel({items,onOpen,ptype}){
 const unit=useUnit();
 const list=(items||[]).slice(0,5);
 const [idx,setIdx]=useState(0);
 const [paused,setPaused]=useState(false);
 useEffect(()=>{setIdx(0);},[list.length]);
 useEffect(()=>{
  if(list.length<=1||paused)return;
  const t=setInterval(()=>setIdx(i=>(i+1)%list.length),3500);
  return ()=>clearInterval(t);
 },[list.length,paused]);
 if(!list.length)return <div style={{fontSize:12,color:MUTED,padding:"8px 14px 12px"}}>표본 부족</div>;
 return (<div onMouseEnter={()=>setPaused(true)} onMouseLeave={()=>setPaused(false)}
   onTouchStart={()=>setPaused(true)}>
  <div style={{overflow:"hidden"}}>
   <div style={{display:"flex",transition:"transform .45s ease",transform:`translateX(-${idx*100}%)`}}>
    {list.map((a,i)=>(<div key={i} onClick={()=>onOpen&&onOpen({complex_name:a.name,lawd_cd:a.code,property_type:ptype||"apartment",gu:a.gu,dong:a.dong})}
      style={{minWidth:"100%",boxSizing:"border-box",padding:"6px 16px 12px",cursor:"pointer"}}>
     <div style={{display:"flex",alignItems:"center",gap:9}}>
      <span className={"rankno "+(a.rank<=3?"top":"")} style={{flex:"none"}}>{a.rank}</span>
      <div style={{fontWeight:800,fontSize:15,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",minWidth:0}}>{a.name} {a.is_sample&&<ExBadge/>}</div>
     </div>
     <div style={{fontSize:12,color:MUTED,marginTop:5}}>{a.gu}{a.dong?` · ${a.dong}`:""}{a.area?` · ${fmtArea(a.area,unit)}`:""}{a.count?` · ${a.count}건`:""}</div>
     <div style={{display:"flex",alignItems:"flex-end",gap:10,marginTop:7}}>
      <div className="num" style={{fontSize:24,fontWeight:800,lineHeight:1.05}}>{eok(a.price)}</div>
      {a.ppm&&<div className="num" style={{fontSize:12.5,color:MUTED,marginBottom:3}}>평 {a.ppm.toLocaleString("ko-KR")}</div>}
      <span style={{marginLeft:"auto",color:MUTED,fontSize:18,marginBottom:1}}>›</span>
     </div>
    </div>))}
   </div>
  </div>
  <div style={{display:"flex",justifyContent:"center",gap:6,paddingBottom:4}}>
   {list.map((_,i)=>(<button key={i} aria-label={`${i+1}번째`} onClick={()=>setIdx(i)}
     style={{width:i===idx?16:6,height:6,borderRadius:3,border:"none",padding:0,cursor:"pointer",
       background:i===idx?TEAL:"var(--chip)",transition:"width .3s, background .3s"}}/>))}
  </div>
 </div>);
}
function Sheet({title,info,onClose,children,fill}){
 useEffect(()=>{const o=document.body.style.overflow;document.body.style.overflow="hidden";return ()=>{document.body.style.overflow=o;};},[]);
 const scRef=React.useRef(null);
 const start=React.useRef(null);
 const [dragY,setDragY]=useState(0);
 const onTouchStart=e=>{const t=e.touches[0];start.current={y:t.clientY,atTop:(scRef.current?scRef.current.scrollTop:0)<=0};};
 const onTouchMove=e=>{if(!start.current)return;const dy=e.touches[0].clientY-start.current.y;if(dy>0&&start.current.atTop)setDragY(dy);};
 const onTouchEnd=()=>{if(dragY>110)onClose();setDragY(0);start.current=null;};
 return ReactDOM.createPortal(
  <div onClick={onClose} style={{position:"fixed",inset:0,zIndex:120,background:"rgba(15,23,30,.45)",display:"flex",flexDirection:"column",justifyContent:"flex-end",alignItems:"center"}}>
   <div onClick={e=>e.stopPropagation()} onTouchStart={onTouchStart} onTouchMove={onTouchMove} onTouchEnd={onTouchEnd} style={{width:"100%",maxWidth:480,background:"var(--surface-solid)",borderRadius:"20px 20px 0 0",...(fill?{height:"93vh"}:{maxHeight:"86vh"}),display:"flex",flexDirection:"column",boxShadow:"0 -6px 24px rgba(0,0,0,.22)",transform:dragY?`translateY(${dragY}px)`:"none",transition:dragY?"none":"transform .22s ease"}}>
    <div style={{padding:"10px 0 2px",display:"flex",justifyContent:"center",flex:"none",cursor:"grab"}}><div style={{width:40,height:5,borderRadius:3,background:"var(--chip)"}}/></div>
    <div style={{display:"flex",alignItems:"center",gap:7,padding:"8px 18px 12px",flex:"none"}}>
     <span style={{fontWeight:800,fontSize:16,minWidth:0,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{title}</span>
     {info&&<span style={{flex:"none",display:"inline-flex",alignItems:"center"}}><Info text={info}/></span>}
     <span onClick={onClose} aria-label="닫기" role="button" tabIndex={0} onKeyDown={onEnter(onClose)} style={{marginLeft:"auto",cursor:"pointer",color:MUTED,fontSize:22,lineHeight:1,fontWeight:600,flex:"none"}}>×</span>
    </div>
    <div ref={scRef} style={{overflowX:"hidden",overflowY:"auto",padding:"0 14px 26px",...(fill?{flex:1,minHeight:0}:{})}}>{children}</div>
   </div>
  </div>, document.body);
}
function SheetShell({onClose,zIndex=120,header,scrollKey,children}){
 useEffect(()=>{const o=document.body.style.overflow;document.body.style.overflow="hidden";return ()=>{document.body.style.overflow=o;};},[]);
 const scRef=React.useRef(null);
 const start=React.useRef(null);
 const [dragY,setDragY]=useState(0);
 useEffect(()=>{if(scRef.current)scRef.current.scrollTop=0;},[scrollKey]);
 const onTouchStart=e=>{const t=e.touches[0];start.current={y:t.clientY,atTop:(scRef.current?scRef.current.scrollTop:0)<=0};};
 const onTouchMove=e=>{if(!start.current)return;const dy=e.touches[0].clientY-start.current.y;if(dy>0&&start.current.atTop)setDragY(dy);};
 const onTouchEnd=()=>{if(dragY>110)onClose();setDragY(0);start.current=null;};
 return ReactDOM.createPortal(
  <div onClick={onClose} style={{position:"fixed",inset:0,zIndex,background:"rgba(15,23,30,.45)",display:"flex",flexDirection:"column",justifyContent:"flex-end",alignItems:"center"}}>
   <div onClick={e=>e.stopPropagation()} onTouchStart={onTouchStart} onTouchMove={onTouchMove} onTouchEnd={onTouchEnd}
     style={{width:"100%",maxWidth:480,background:"var(--bg2)",borderRadius:"20px 20px 0 0",height:"93vh",display:"flex",flexDirection:"column",boxShadow:"0 -6px 24px rgba(0,0,0,.22)",
       transform:dragY?`translateY(${dragY}px)`:"none",transition:dragY?"none":"transform .22s ease"}}>
    <div style={{padding:"8px 0 4px",display:"flex",justifyContent:"center",flex:"none",cursor:"grab"}}><div style={{width:40,height:5,borderRadius:3,background:"var(--chip)"}}/></div>
    {header}
    <div ref={scRef} style={{overflowX:"hidden",overflowY:"auto",flex:1,padding:"0 14px 26px"}}>{children}</div>
   </div>
  </div>, document.body);
}
function DetailSheet({sel,mapCfg,onClose,isFav,onToggleFav,inCompare,onToggleCompare,onOpen}){
 return (<SheetShell onClose={onClose} zIndex={120} scrollKey={sel.name+sel.lawd_cd+sel.property_type}>
  <Detail sel={sel} mapCfg={mapCfg} onBack={onClose} isFav={isFav} onToggleFav={onToggleFav} inCompare={inCompare} onToggleCompare={onToggleCompare} onOpen={onOpen}/>
 </SheetShell>);
}
function ListingSheet({x,onClose}){
 return (<SheetShell onClose={onClose} zIndex={120} scrollKey={x&&x.id}>
  <ListingDetail x={x} onBack={onClose}/>
 </SheetShell>);
}
function PostSheet({id,account,onNeedLogin,onClose,onChanged,onOpenComplex,onEdit,onOpenAuthor}){
 return (<SheetShell onClose={onClose} zIndex={120} scrollKey={id}>
  <PostDetail id={id} account={account} onNeedLogin={onNeedLogin} onBack={onClose} onChanged={onChanged} onOpenComplex={onOpenComplex} onEdit={onEdit} onOpenAuthor={onOpenAuthor}/>
 </SheetShell>);
}
function CommuteSheet({onClose,onOpen,mapCfg}){
 return (<SheetShell onClose={onClose} zIndex={118}>
  <CommuteSearch onClose={onClose} onOpen={onOpen} mapCfg={mapCfg}/>
 </SheetShell>);
}
function RankSheet({title,items,metric,onItem,onClose,info}){
 const medal=r=>r===1?"🥇":r===2?"🥈":r===3?"🥉":null;
 return (<Sheet title={title} info={info} onClose={onClose} fill>
  <MoreList items={(items||[]).slice(0,50)} initial={10} step={10} render={(it,k)=>{const md=medal(it.rank);
   return (<div key={k} className="txrow" tabIndex={0} role="button" onKeyDown={onEnter(()=>{onItem&&onItem(it);onClose&&onClose();})} style={{cursor:"pointer",padding:"13px 6px"}} onClick={()=>{onItem&&onItem(it);onClose&&onClose();}}>
    <span style={{flex:"none",width:30,textAlign:"center",fontSize:md?20:15,fontWeight:800,color:md?"inherit":MUTED}}>{md||it.rank}</span>
    <div style={{minWidth:0,flex:1}}>
     <div style={{fontWeight:700,fontSize:14.5,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{it.name} {it.contains_sample_data&&<ExBadge/>}</div>
     <div style={{fontSize:12,color:MUTED,marginTop:2,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{["청주시",(it.gu||"").replace("청주시 ",""),it.dong].filter(Boolean).join(" ")}{it.property_type&&it.property_type!=="apartment"?" · "+(TYPE_LABEL[it.property_type]||""):""}</div>
    </div>
    <span style={{flex:"none"}}>{metric(it)}</span>
   </div>);}}/>
 </Sheet>);
}
function ComplexQuickSheet({item,onClose,onDetail}){
 const [d,setD]=useState(null);
 useEffect(()=>{let on=true;setD(null);
  const q=`name=${encodeURIComponent(item.complex_name)}&lawd_cd=${item.lawd_cd||""}`+(item.property_type?`&property_type=${item.property_type}`:"");
  fetch(`${API}/complex/detail?${q}`).then(r=>r.json())
   .then(j=>{if(on)setD(j&&j.name?j:demoDetail({name:item.complex_name,lawd_cd:item.lawd_cd,property_type:item.property_type}));})
   .catch(()=>{if(on)setD(demoDetail({name:item.complex_name,lawd_cd:item.lawd_cd,property_type:item.property_type}));});
  return ()=>{on=false;};
 },[item.complex_name,item.lawd_cd,item.property_type]);
 const region=[(item.gu||(d&&d.gu)||"").replace("청주시 ",""),(d&&d.dong)||item.dong].filter(Boolean).join(" ");
 const type=TYPE_LABEL[item.property_type||(d&&d.property_type)]||"";
 return (<Sheet title={item.complex_name} onClose={onClose}>
  <div style={{fontSize:12.5,color:MUTED,padding:"0 4px 12px"}}>{["청주시",region,type].filter(Boolean).join(" · ")} {d&&d.contains_sample_data&&<ExBadge/>}</div>
  {!d?<div style={{padding:"2px 2px 10px"}}><SkeletonCard lines={2}/></div>:
   (d.found===false||d.price_median==null)?<div style={{padding:"0 4px 14px",color:MUTED,fontSize:13}}>표시할 실거래 요약이 아직 없어요. 전체 상세에서 확인해 보세요.</div>:
   <div>
    <div style={{display:"flex",gap:22,flexWrap:"wrap",padding:"0 4px 12px"}}>
     <div><div style={{fontSize:11,color:MUTED}}>대표 시세(중앙)</div><div className="num" style={{fontSize:21,fontWeight:800}}>{eok(d.price_median)}</div></div>
     {d.jeonse_ratio!=null&&<div><div style={{fontSize:11,color:MUTED}}>전세가율</div><div className="num" style={{fontSize:21,fontWeight:800,color:TEAL}}>{d.jeonse_ratio}%</div></div>}
     {d.trade_count!=null&&<div><div style={{fontSize:11,color:MUTED}}>거래</div><div className="num" style={{fontSize:21,fontWeight:800}}>{d.trade_count}건</div></div>}
    </div>
    {d.price_min!=null&&d.price_max!=null&&<div style={{fontSize:12,color:MUTED,padding:"0 4px 12px"}}>실거래 범위 {eok(d.price_min)} ~ {eok(d.price_max)}{d.reliability?` · 신뢰도 ${d.reliability}`:""}</div>}
    {d.vs_region&&<div style={{margin:"0 4px 12px",fontSize:12.5,color:MUTED}}>📍 {d.vs_region.gu} 평균 대비 <b className="num" style={{color:d.vs_region.pct>0?UP:d.vs_region.pct<0?DOWN:INK,fontSize:13.5}}>{d.vs_region.pct>0?"+":""}{d.vs_region.pct}%</b> <span style={{fontSize:11}}>(평단가 기준)</span></div>}
   </div>}
  <button onClick={()=>onDetail&&onDetail(item)} style={{width:"100%",border:"none",background:TEAL,color:"#fff",fontWeight:800,fontSize:14,borderRadius:11,padding:"13px",cursor:"pointer"}}>전체 상세 페이지 보기 →</button>
  <div style={{height:8}}/>
 </Sheet>);
}
function TickerBanner({label,color,bg,items,metric,onItem,info,title}){
 const all=items||[];
 const ticker=all.slice(0,5);   // 펼치기 전 티커는 상위 5개만 회전
 const n=ticker.length;
 const [i,setI]=useState(0);
 const [sheet,setSheet]=useState(false);
 useEffect(()=>{ if(sheet||n<=1)return; const t=setInterval(()=>setI(p=>(p+1)%n),3500); return ()=>clearInterval(t); },[sheet,n]);
 if(!n) return null;
 const cur=ticker[i%n];
 return (<div className="card" style={{padding:0,marginTop:8,overflow:"hidden"}}>
  <div onClick={()=>setSheet(true)} tabIndex={0} role="button" onKeyDown={onEnter(()=>setSheet(true))} style={{display:"flex",alignItems:"center",gap:9,padding:"11px 13px",cursor:"pointer"}}>
   <span className="pill" style={{background:bg,color,fontWeight:800,fontSize:11.5,flex:"none"}}>{label}</span>
   <span className="num" style={{fontWeight:800,color,fontSize:13,flex:"none",minWidth:12,textAlign:"center"}}>{cur.rank}</span>
   <span style={{fontWeight:700,fontSize:13.5,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",flex:1,minWidth:0}}>{cur.name} {cur.contains_sample_data&&<ExBadge/>}</span>
   <span style={{flex:"none",display:"flex",alignItems:"center",gap:6}}>{metric(cur)}<span style={{color:MUTED,fontSize:15}}>›</span></span>
  </div>
  {sheet&&<RankSheet title={title||label} items={all} metric={metric} onItem={onItem} onClose={()=>setSheet(false)} info={info}/>}
 </div>);
}
function TopMovers({movers,onOpen}){
 const [dir,setDir]=useState("up");
 const [sort,setSort]=useState("pct");
 const m=movers||{};
 const c=dir==="up"?UP:DOWN;
 const base=(dir==="up"?m.up:m.down)||[];
 const list=[...base].sort((a,b)=> sort==="amount"
   ? (dir==="up"?b.change-a.change:a.change-b.change)
   : (dir==="up"?b.pct-a.pct:a.pct-b.pct));
 return (<div className="card" style={{padding:"14px 15px 8px",marginTop:12}}>
  <div style={{display:"flex",alignItems:"center",gap:6}}>
   <span style={{fontWeight:800,fontSize:15}}>최고 상승·하락 아파트</span>
   <Info text="같은 단지·평형에서 직전 거래보다 실거래가가 가장 많이 오른/내린 순위입니다. 최근 2건 비교 기준이며, 신고 지연·정정·이상치가 있을 수 있는 참고용 정보예요."/>
   <div style={{marginLeft:"auto",display:"flex",gap:3,background:"var(--chip)",borderRadius:9,padding:3}}>
    {[["up","상승"],["down","하락"]].map(([k,l])=><button key={k} onClick={()=>setDir(k)} style={{border:"none",cursor:"pointer",fontWeight:800,fontSize:12,padding:"6px 13px",borderRadius:7,background:dir===k?"var(--surface-solid)":"transparent",color:dir===k?(k==="up"?UP:DOWN):MUTED}}>{l}</button>)}
   </div>
  </div>
  <div style={{display:"flex",alignItems:"center",gap:10,margin:"9px 2px 2px"}}>
   <span style={{fontSize:11.5,color:MUTED}}>정렬</span>
   {[["pct","변동률"],["amount","변동액"]].map(([k,l])=><button key={k} onClick={()=>setSort(k)} style={{border:"none",background:"none",cursor:"pointer",fontSize:12.5,fontWeight:sort===k?800:600,color:sort===k?INK:MUTED,padding:"1px 2px 3px",borderBottom:sort===k?"2px solid "+c:"2px solid transparent"}}>{l}</button>)}
  </div>
  {list.length?<div style={{marginTop:4}}>
   {list.map((it,i)=>(<div key={i} className="txrow" style={{cursor:"pointer",alignItems:"flex-start"}} tabIndex={0} role="button" onKeyDown={onEnter(()=>onOpen&&onOpen({complex_name:it.name,lawd_cd:it.lawd_cd,property_type:"apartment",gu:it.gu}))} onClick={()=>onOpen&&onOpen({complex_name:it.name,lawd_cd:it.lawd_cd,property_type:"apartment",gu:it.gu})}>
    <span className="num" style={{flex:"none",width:22,textAlign:"center",fontWeight:800,fontSize:15,color:i<3?c:MUTED}}>{i+1}</span>
    <div style={{minWidth:0,flex:1}}>
     <div style={{fontWeight:700,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{it.name} <span style={{color:MUTED,fontWeight:600}}>{it.area_py}평</span> {it.contains_sample_data&&<ExBadge/>}</div>
     <div style={{fontSize:11.5,color:MUTED,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{["충청북도 청주시",(it.gu||"").replace("청주시 ",""),it.dong].filter(Boolean).join(" ")}</div>
    </div>
    <div style={{textAlign:"right",flex:"none"}}>
     <div className="num" style={{fontWeight:800,color:c,fontSize:13.5}}>{manKor(it.change,true)} <span style={{fontSize:12}}>({it.pct>0?"+":""}{it.pct}%)</span></div>
     <div className="num" style={{fontSize:11.5,color:MUTED,marginTop:1}}>{manKor(it.prev_amount)} › <b style={{color:"var(--ink)"}}>{manKor(it.latest_amount)}</b></div>
    </div>
   </div>))}
  </div>:<Empty>직전 거래와 비교할 표본이 아직 부족해요.</Empty>}
 </div>);
}
function BudgetPicks({onOpen,favs,embedded}){
 const saved=React.useMemo(()=>loadLoanProfile(),[]);
 const [cash,setCash]=useState(saved&&saved.cash!=null&&saved.cash!==""?String(saved.cash):"");
 const [useIncome,setUseIncome]=useState(!!(saved&&saved.consent&&saved.income));
 const [income,setIncome]=useState(saved&&saved.income!=null&&saved.income!==""?String(saved.income):"");
 const [ptype,setPtype]=useState("all");
 const [region,setRegion]=useState("all");
 const [editing,setEditing]=useState(!(saved&&saved.cash));
 const [res,setRes]=useState(null);
 const [loading,setLoading]=useState(false);
 const GU_CODE={"상당구":"43111","서원구":"43112","흥덕구":"43113","청원구":"43114"};
 const favRegions=React.useMemo(()=>{
  const set=new Set((favs||[]).filter(f=>f.target_type==="region").map(f=>((f.meta&&f.meta.gu)||f.name||"").replace("청주시 ","")));
  return Array.from(set).map(g=>GU_CODE[g]).filter(Boolean);
 },[favs]);
 const codesFor=reg=> reg==="all"?null : reg==="fav"?(favRegions.length?favRegions:null) : [reg];
 const load=useCallback((cashV,incV,useInc,pt,lawds)=>{
  if(cashV===""||+cashV<=0){setRes(null);return;}
  setLoading(true);
  const inp={self_capital:+cashV,consent:!!(useInc&&incV!==""),annual_income:(useInc&&incV!=="")?+incV:null,
   existing_annual_payment:0,is_no_house:true,is_first_time:false,over_85:false,property_type:pt,lawd_cds:lawds||null,limit:8};
  fetch(`${API}/loan/affordable`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(inp)})
   .then(r=>r.json()).then(j=>{setRes(j&&j.items?j:demoAffordable(cashV,incV,useInc,pt,lawds));setLoading(false);})
   .catch(()=>{setRes(demoAffordable(cashV,incV,useInc,pt,lawds));setLoading(false);});
 },[]);
 useEffect(()=>{ if(saved&&saved.cash){ load(String(saved.cash),saved.income!=null?String(saved.income):"",!!(saved.consent&&saved.income),"all",null); } },[]);
 useEffect(()=>{ if(!editing&&cash!==""){ load(cash,income,useIncome,ptype,codesFor(region)); } },[ptype,region]);
 const submit=()=>{
  if(cash===""||+cash<=0)return;
  const cur=loadLoanProfile()||{};
  saveLoanProfile({...cur,consent:!!(useIncome&&income!==""),cash:+cash,income:income===""?"":+income});
  setEditing(false); load(cash,income,useIncome,ptype,codesFor(region));
 };
 const TYPES=[["all","전체"],["apartment","아파트"],["officetel","오피스텔"],["rowhouse","빌라"],["detached","단독"]];
 const REGIONS=[["all","전체 지역"],...(favRegions.length?[["fav","관심지역"]]:[]),["43111","상당"],["43112","서원"],["43113","흥덕"],["43114","청원"]];
 const items=res&&res.items||[];
 return (<div className="card" style={{padding:"14px 15px",marginTop:12}}>
  {!embedded&&<div style={{display:"flex",alignItems:"center",gap:8}}>
   <span style={{fontSize:19}}>💰</span>
   <span style={{fontWeight:800,fontSize:15}}>내 예산 맞춤 추천</span>
   {res&&!editing&&<button onClick={()=>setEditing(true)} style={{marginLeft:"auto",border:"none",background:"none",color:TEAL,fontWeight:700,fontSize:12,cursor:"pointer"}}>예산 수정</button>}
  </div>}
  {embedded&&res&&!editing&&<div style={{display:"flex"}}><button onClick={()=>setEditing(true)} style={{marginLeft:"auto",border:"none",background:"none",color:TEAL,fontWeight:700,fontSize:12,cursor:"pointer"}}>예산 수정</button></div>}

  {editing?
   <div style={{marginTop:11}}>
    <div style={{fontSize:12.5,color:MUTED,marginBottom:8}}>보유 현금(자기자본)을 입력하면, 그 예산으로 살 수 있는 청주 단지를 추천해드려요.</div>
    <div style={{display:"flex",alignItems:"center",gap:8,background:"var(--surface-2)",borderRadius:10,padding:"10px 12px"}}>
     <span style={{fontSize:13,color:MUTED,fontWeight:700,flex:"none"}}>보유 현금</span>
     <input value={cash} onChange={e=>setCash(e.target.value.replace(/[^0-9]/g,""))} inputMode="numeric" placeholder="예: 15000" style={{flex:1,minWidth:0,border:"none",background:"none",textAlign:"right",fontWeight:800,fontSize:15,color:"var(--ink)",outline:"none"}}/>
     <span style={{fontSize:13,color:MUTED,flex:"none"}}>만원</span>
    </div>
    {cash!==""&&+cash>0&&<div className="num" style={{fontSize:11.5,color:MUTED,marginTop:4,textAlign:"right"}}>{eok(+cash)}</div>}
    <label style={{display:"flex",alignItems:"center",gap:7,marginTop:10,fontSize:12.5,color:"var(--ink)",cursor:"pointer"}}>
     <input type="checkbox" checked={useIncome} onChange={e=>setUseIncome(e.target.checked)} style={{accentColor:TEAL,width:16,height:16}}/>
     연소득 반영(더 정확한 한도) <span style={{color:MUTED}}>· 선택</span>
    </label>
    {useIncome&&<div style={{display:"flex",alignItems:"center",gap:8,background:"var(--surface-2)",borderRadius:10,padding:"10px 12px",marginTop:7}}>
     <span style={{fontSize:13,color:MUTED,fontWeight:700,flex:"none"}}>연소득</span>
     <input value={income} onChange={e=>setIncome(e.target.value.replace(/[^0-9]/g,""))} inputMode="numeric" placeholder="부부합산, 예: 6000" style={{flex:1,minWidth:0,border:"none",background:"none",textAlign:"right",fontWeight:800,fontSize:15,color:"var(--ink)",outline:"none"}}/>
     <span style={{fontSize:13,color:MUTED,flex:"none"}}>만원</span>
    </div>}
    <button onClick={submit} disabled={cash===""||+cash<=0} style={{marginTop:12,width:"100%",border:"none",background:(cash===""||+cash<=0)?"var(--chip)":TEAL,color:(cash===""||+cash<=0)?MUTED:"#fff",fontWeight:800,fontSize:14.5,padding:"12px",borderRadius:11,cursor:(cash===""||+cash<=0)?"default":"pointer"}}>내 예산으로 추천받기</button>
    <div style={{fontSize:11,color:MUTED,marginTop:7,lineHeight:1.6}}>입력값은 <b>이 기기에만 저장</b>되고 서버로 전송·저장되지 않습니다. 추천 계산에만 사용돼요.</div>
   </div>
   :
   <div style={{marginTop:11}}>
    <div style={{fontSize:14,fontWeight:800}}>내 예산 ≈ {eok(res?res.budget_max:0)} <span style={{fontWeight:500,color:MUTED,fontSize:12}}>(자기자본 {eok(+cash)} + 대출, {res&&res.mode==="personalized"?"맞춤":"간이"})</span></div>
    <div style={{display:"flex",gap:5,flexWrap:"wrap",margin:"10px 0 4px"}}>
     {TYPES.map(([v,l])=><button key={v} onClick={()=>setPtype(v)} className={"tog "+(ptype===v?"on":"")} style={{padding:"5px 11px",fontSize:12}}>{l}</button>)}
    </div>
    <div style={{display:"flex",gap:5,flexWrap:"wrap",margin:"0 0 6px"}}>
     {REGIONS.map(([v,l])=><button key={v} onClick={()=>setRegion(v)} className={"tog "+(region===v?"on":"")} style={{padding:"5px 11px",fontSize:12}}>{v==="fav"?"★ "+l:l}</button>)}
    </div>
    {loading?<div style={{marginTop:8}}><SkeletonCard lines={2}/></div>:
     items.length?<div style={{marginTop:4}}>
      {items.map((c,i)=>(<div key={i} className="txrow" style={{cursor:"pointer",padding:"13px 4px"}} tabIndex={0} role="button" onKeyDown={onEnter(()=>onOpen&&onOpen({complex_name:c.name,lawd_cd:c.lawd_cd,property_type:c.property_type||"apartment",gu:c.gu}))} onClick={()=>onOpen&&onOpen({complex_name:c.name,lawd_cd:c.lawd_cd,property_type:c.property_type||"apartment",gu:c.gu})}>
       <div style={{minWidth:0,flex:1}}>
        <div style={{fontWeight:700,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{c.name} {c.contains_sample_data&&<ExBadge/>}</div>
        <div style={{fontSize:12,color:MUTED,marginTop:1}}>{[(c.gu||"").replace("청주시 ",""),TYPE_LABEL[c.property_type],c.trade_count!=null?`거래 ${c.trade_count}건`:null].filter(Boolean).join(" · ")}{c.trade_count!=null&&c.trade_count<3?" · 표본 적음":""}</div>
        <div className="num" style={{fontSize:11.5,color:TEAL,marginTop:2}}>자기자본 {eok(c.own_capital)} + 대출 {eok(c.loan_needed)} · 월 {won(c.monthly_payment)}</div>
       </div>
       <div style={{textAlign:"right",flex:"none"}}><div className="num" style={{fontWeight:800,fontSize:14}}>{eok(c.median_price)}</div><div style={{fontSize:10.5,color:MUTED}}>시세 중앙값</div></div>
      </div>))}
     </div>:
      <Empty>예산 내 {ptype==="all"?"단지":TYPE_LABEL[ptype]}를 찾지 못했어요. 보유 현금을 조정하거나 유형·지역을 바꿔보세요.</Empty>}
    <div style={{fontSize:11,color:MUTED,marginTop:9,lineHeight:1.6}}>시세는 최근 {AGG_MONTHS}개월 중앙값, 금리 {res?res.rate_pct:4}% · {res?res.years:30}년 참고치(원리금균등). 대출·세금은 아파트 기준이라 오피스텔·빌라는 개략적일 수 있어요. {res&&res.disclaimer?res.disclaimer:""}</div>
   </div>}
 </div>);
}
function BudgetSheet({onClose,onOpen,favs}){
 const header=(<div style={{display:"flex",alignItems:"center",padding:"6px 16px 4px",flex:"none"}}><span style={{fontWeight:800,fontSize:16}}>내 예산 맞춤 추천</span><span onClick={onClose} onKeyDown={onEnter(onClose)} aria-label="닫기" role="button" tabIndex={0} style={{marginLeft:"auto",cursor:"pointer",color:MUTED,fontSize:22,lineHeight:1,fontWeight:600}}>×</span></div>);
 return (<SheetShell onClose={onClose} zIndex={118} header={header}>
  <BudgetPicks onOpen={onOpen} favs={favs} embedded={true}/>
 </SheetShell>);
}
function LoanSheet({onClose,onOpen}){
 const header=(<div style={{display:"flex",alignItems:"center",padding:"6px 16px 4px",flex:"none"}}><span style={{fontWeight:800,fontSize:16}}>내 대출 한도 계산</span><span onClick={onClose} onKeyDown={onEnter(onClose)} aria-label="닫기" role="button" tabIndex={0} style={{marginLeft:"auto",cursor:"pointer",color:MUTED,fontSize:22,lineHeight:1,fontWeight:600}}>×</span></div>);
 return (<SheetShell onClose={onClose} zIndex={118} header={header}>
  <Loan onOpen={onOpen}/>
 </SheetShell>);
}
function AgentDashboard({onClose,account,onGoListings,onOpenListing}){
 const [items,setItems]=useState(null);
 const [leads,setLeads]=useState(null);
 const [leadsLocked,setLeadsLocked]=useState(false);
 const [upBusy,setUpBusy]=useState(false);
 const [upMsg,setUpMsg]=useState("");
 const [busy,setBusy]=useState(false);
 const load=React.useCallback(()=>{
  setItems(null);
  fetch(`${API}/listings?mine=1&manage=1&limit=200`,{headers:authHeader()}).then(r=>r.json())
   .then(j=>setItems(j.items||[])).catch(()=>setItems([]));
  fetch(`${API}/inquiries?device_id=${encodeURIComponent(deviceId())}`,{headers:authHeader()}).then(r=>r.ok?r.json():{items:[]})
   .then(j=>{setLeads(j.items||[]);setLeadsLocked(!!j.locked);}).catch(()=>setLeads([]));
 },[]);
 useEffect(()=>{load();},[load]);
 const setStatus=(id,status)=>{ setBusy(true);
  fetch(`${API}/listings/${id}/status`,{method:"POST",headers:{...authHeader(),"Content-Type":"application/json"},body:JSON.stringify({status})})
   .then(()=>load()).catch(()=>{}).finally(()=>setBusy(false)); };
 const setLeadStatus=(id,status)=>{ setBusy(true);
  fetch(`${API}/inquiries/${id}/status`,{method:"POST",headers:{...authHeader(),"Content-Type":"application/json"},body:JSON.stringify({status})})
   .then(()=>load()).catch(()=>{}).finally(()=>setBusy(false)); };
 const doUpgrade=()=>{ setUpBusy(true); setUpMsg("");
  fetch(`${API}/billing/checkout`,{method:"POST",headers:{...authHeader(),"Content-Type":"application/json"},body:JSON.stringify({plan:"agent_pro"})})
   .then(r=>r.ok?r.json():r.json().then(j=>Promise.reject(j)))
   .then(j=>{ if(j.mode==="mock"&&j.confirm_token){
      return fetch(`${API}/billing/confirm`,{method:"POST",headers:{...authHeader(),"Content-Type":"application/json"},body:JSON.stringify({plan:"agent_pro",token:j.confirm_token})}).then(r=>r.ok?r.json():r.json().then(e=>Promise.reject(e)));
     } return Promise.reject({detail:j.message||"결제 연동(키)이 필요합니다."}); })
   .then(()=>load())
   .catch(e=>setUpMsg((e&&e.detail)||"업그레이드에 실패했어요."))
   .finally(()=>setUpBusy(false)); };
 const leadCnt=id=>(leads||[]).filter(l=>l.listing_id===id).length;
 const newLeads=(leads||[]).filter(l=>l.status==="new").length;
 const [editing,setEditing]=useState(null);
 const openEdit=(id)=>{   // 편집은 전체 필드 필요 → 상세 GET(소유자 조회는 조회수 미증가)
  fetch(`${API}/listings/${id}?device_id=${encodeURIComponent(deviceId())}`,{headers:authHeader()})
   .then(r=>r.ok?r.json():null).then(full=>{if(full&&full.id)setEditing(full);}).catch(()=>{}); };
 const a=items||[];
 const cnt=k=>a.reduce((m,x)=>{const v=x[k]||"기타";m[v]=(m[v]||0)+1;return m;},{});
 const dealCnt=cnt("deal_type"), guCnt=cnt("gu");
 const active=a.filter(x=>x.status==="active").length;
 const sponsored=a.filter(x=>x.is_sponsored).length;
 const header=(<div style={{display:"flex",alignItems:"center",padding:"6px 16px 4px",flex:"none"}}><span style={{fontWeight:800,fontSize:16}}>중개사 대시보드</span><span onClick={onClose} onKeyDown={onEnter(onClose)} aria-label="닫기" role="button" tabIndex={0} style={{marginLeft:"auto",cursor:"pointer",color:MUTED,fontSize:22,lineHeight:1,fontWeight:600}}>×</span></div>);
 return (<SheetShell onClose={onClose} zIndex={119} header={header}>
  {editing?<div style={{padding:"2px 2px 16px"}}><ListingForm account={account} initial={editing} onCancel={()=>setEditing(null)} onCreated={()=>{setEditing(null);load();}}/></div>:
  <div style={{padding:"2px 2px 16px"}}>
   <div style={{fontSize:12.5,color:MUTED,margin:"0 2px 10px"}}>{account&&account.nickname?`${account.nickname} 중개사`:"내 중개"} · 등록 매물 관리</div>
   {items===null?<div><SkeletonCard/><SkeletonCard/></div>:<React.Fragment>
    <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:8}}>
     <Stat label="총 매물" val={a.length}/>
     <Stat label="활성" val={active}/>
     <Stat label="총 조회수" val={a.reduce((s,x)=>s+(x.views||0),0)}/>
     <Stat label="받은 문의" val={(leads||[]).length}/>
     {FEATURES.ads&&<Stat label="광고 노출" val={sponsored}/>}
    </div>
    <div className="card" style={{padding:"12px 14px",marginBottom:10}}>
     <div style={{fontSize:12,color:MUTED,fontWeight:700,marginBottom:6}}>거래유형</div>
     <div style={{display:"flex",gap:16,flexWrap:"wrap"}}>
      {[["trade","매매"],["jeonse","전세"],["wolse","월세"]].map(([k,l])=>(<div key={k}><span style={{fontSize:12.5,color:MUTED}}>{l} </span><span className="num" style={{fontWeight:800}}>{dealCnt[k]||0}</span></div>))}
     </div>
     {Object.keys(guCnt).length>0&&<React.Fragment><div style={{fontSize:12,color:MUTED,fontWeight:700,margin:"10px 0 6px"}}>지역(구)</div>
      <div style={{display:"flex",gap:16,flexWrap:"wrap"}}>
       {Object.entries(guCnt).map(([g,n])=>(<div key={g}><span style={{fontSize:12.5,color:MUTED}}>{g} </span><span className="num" style={{fontWeight:800}}>{n}</span></div>))}
      </div></React.Fragment>}
    </div>
    {(leads&&leads.length>0)&&<div className="card" style={{padding:"12px 14px",marginBottom:10}}>
     <div style={{display:"flex",alignItems:"center",marginBottom:6}}>
      <span style={{fontWeight:800,fontSize:14}}>받은 문의(리드)</span>
      <span style={{marginLeft:8,fontSize:12,color:MUTED}}>{leads.length}건{newLeads?` · 신규 ${newLeads}`:""}</span>
      {leadsLocked&&<button onClick={doUpgrade} disabled={upBusy} style={{marginLeft:"auto",border:"none",background:TEAL,color:"#fff",fontWeight:800,fontSize:12,padding:"7px 12px",borderRadius:9,cursor:upBusy?"default":"pointer"}}>{upBusy?"처리 중…":"Pro 업그레이드"}</button>}
     </div>
     {upMsg&&<div style={{fontSize:11.5,color:UP,marginBottom:6}}>{upMsg}</div>}
     {leadsLocked&&<div style={{fontSize:11.5,color:MUTED,marginBottom:6,lineHeight:1.5}}>Pro 플랜에서 문의자 연락처를 확인할 수 있어요.</div>}
     {leads.map(l=>(<div key={l.id} style={{borderTop:"1px solid var(--line)",padding:"10px 0 2px"}}>
       <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
        {l.status==="new"&&<span className="pill" style={{background:"rgba(15,118,110,.14)",color:TEAL,fontWeight:800}}>신규</span>}
        <span style={{fontWeight:700,fontSize:13}}>{l.name||"익명"}</span>
        {l.contact?<span style={{fontSize:12.5,color:TEAL,fontWeight:700}}>{l.contact}</span>:(l.locked?<span style={{fontSize:12,color:MUTED,fontWeight:700}}>🔒 Pro에서 연락처 확인</span>:null)}
        <span style={{marginLeft:"auto",fontSize:11,color:MUTED}}>{(l.created_at||"").slice(0,10)}</span>
       </div>
       <div style={{fontSize:11.5,color:MUTED,marginTop:3}}>매물: {l.listing_title||("#"+l.listing_id)}{l.deal_type?` · ${LP_DEAL[l.deal_type]}`:""}</div>
       <div style={{fontSize:13.5,marginTop:5,whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{l.message}</div>
       <div style={{display:"flex",gap:6,marginTop:8,flexWrap:"wrap"}}>
        {[["read","읽음"],["contacted","연락함"],["closed","종료"]].map(([k,lab])=>(<button key={k} onClick={()=>setLeadStatus(l.id,k)} disabled={busy} style={{border:"1px solid "+(l.status===k?TEAL:"var(--line)"),background:l.status===k?"rgba(15,118,110,.1)":"var(--surface-solid)",color:l.status===k?TEAL:INK,fontWeight:700,fontSize:12,padding:"6px 11px",borderRadius:8,cursor:busy?"default":"pointer"}}>{lab}</button>))}
       </div>
      </div>))}
     <div style={{fontSize:11,color:MUTED,marginTop:8,lineHeight:1.5}}>※ 문의자 연락처는 응대 목적에만 사용하세요. 마케팅·제3자 제공 금지.</div>
    </div>}
    <div style={{display:"flex",alignItems:"center",margin:"4px 2px 8px"}}>
     <span style={{fontWeight:800,fontSize:14}}>내 매물</span>
     <button onClick={onGoListings} className="btn-primary" style={{marginLeft:"auto",fontSize:13,padding:"8px 13px"}}>+ 매물 등록</button>
    </div>
    {a.length?a.map(x=>(<div key={x.id} onClick={()=>onOpenListing&&onOpenListing(x.id)} className="card" style={{padding:"10px 12px",marginBottom:8,display:"flex",alignItems:"center",gap:10,cursor:"pointer"}}>
       <div style={{minWidth:0,flex:1}}>
        <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
         <span className="pill" style={{background:"rgba(15,118,110,.12)",color:DEAL_COLOR[x.deal_type]||TEAL,fontWeight:800}}>{LP_DEAL[x.deal_type]}</span>
         <span className="num" style={{fontWeight:800,fontSize:14}}>{listingPrice(x)}</span>
         {x.status!=="active"&&<span className="pill" style={{background:"#EEF1F1",color:MUTED}}>{x.status==="traded"?"거래완료":"숨김"}</span>}
         {FEATURES.ads&&x.is_sponsored&&<span className="pill" style={{background:"rgba(178,106,0,.14)",color:"#9A6B00",fontWeight:800}}>광고</span>}
        </div>
        <div style={{fontWeight:700,marginTop:3,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{x.title}</div>
        <div style={{fontSize:11.5,color:MUTED,marginTop:2}}>{LP_PROP[x.property_type]} · {x.gu||""}{x.dong?` ${x.dong}`:""} · {(x.created_at||"").slice(0,10)} · 조회 {x.views||0}{leadCnt(x.id)?` · 문의 ${leadCnt(x.id)}`:""}</div>
       </div>
       <div onClick={e=>e.stopPropagation()} style={{flex:"none",display:"flex",gap:4,flexWrap:"wrap",justifyContent:"flex-end",maxWidth:176}}>
        <button onClick={()=>openEdit(x.id)} style={{border:"1px solid "+TEAL,background:"rgba(15,118,110,.06)",color:TEAL,fontWeight:700,fontSize:12,padding:"6px 9px",borderRadius:8,cursor:"pointer"}}>수정</button>
        <button onClick={()=>setStatus(x.id,x.status==="traded"?"active":"traded")} disabled={busy} style={{border:"1px solid var(--line)",background:"var(--surface-solid)",color:INK,fontWeight:700,fontSize:12,padding:"6px 9px",borderRadius:8,cursor:busy?"default":"pointer"}}>{x.status==="traded"?"판매중":"거래완료"}</button>
        <button onClick={()=>setStatus(x.id,x.status==="hidden"?"active":"hidden")} disabled={busy} style={{border:"1px solid var(--line)",background:"var(--surface-solid)",color:x.status==="hidden"?TEAL:UP,fontWeight:700,fontSize:12,padding:"6px 9px",borderRadius:8,cursor:busy?"default":"pointer"}}>{x.status==="hidden"?"복구":"숨김"}</button>
       </div>
      </div>)):<div className="card" style={{padding:24}}><Empty>아직 등록한 매물이 없습니다. 매물을 등록해 보세요.</Empty></div>}
   </React.Fragment>}
  </div>}
 </SheetShell>);
}
function JeonseGuard(){
 const [price,setPrice]=useState(""),[dep,setDep]=useState(""),[lien,setLien]=useState("");
 const [open,setOpen]=useState(false);
 const P=parseFloat(price)||0, D=parseFloat(dep)||0, L=parseFloat(lien)||0;
 const ratio=(P>0&&D>0)?Math.round((D+L)/P*1000)/10:null;
 let band=null;
 if(ratio!=null){
  if(ratio>=80)band={c:"#C8322A",t:"위험 신호",m:"집이 경매로 넘어가면 보증금을 다 돌려받지 못할 수 있는 구간이에요. 보증보험(HUG) 가입 가능 여부를 꼭 확인하고, 계약을 다시 생각해보세요."};
  else if(ratio>=70)band={c:"#C77A1A",t:"주의",m:"여유가 크지 않아요. 근저당 말소 특약, 보증보험 가입을 권해요."};
  else band={c:"#0F766E",t:"상대적 여유",m:"통상적 기준으로는 여유가 있는 편이에요. 그래도 계약 당일 등기부를 다시 확인하세요."};
 }
 const inp={flex:1,minWidth:0,border:"1.5px solid var(--line)",borderRadius:11,padding:"11px 12px",fontSize:15,fontWeight:700,background:"var(--surface-solid)",color:INK};
 const CHECK=[
  ["계약 전",["등기부등본 열람 — 소유자가 임대인과 일치하는지, 근저당·가압류가 있는지(을구의 채권최고액을 아래 진단에 입력)","건축물대장 — 위반건축물 여부(정부24)","이 앱에서 단지 전세가율 확인 — 매매가 대비 보증금이 과한지","임대인 국세·지방세 체납 열람 신청(계약 전 임대인 동의로 가능)"]],
  ["계약일",["등기부등본 당일 재발급 — 계약 직전 변동 확인","임대인 본인 확인(신분증) · 계약금은 임대인 명의 계좌로","특약 예: '잔금일까지 근저당 말소', '전입·확정일자 전 추가 담보 설정 금지'"]],
  ["잔금·입주",["잔금 직전 등기부 한 번 더 확인","이사 당일 전입신고 + 확정일자(주민센터/정부24) — 우선변제권 확보","전세보증금 반환보증(HUG 등) 가입 검토 — 역전세 대비"]],
 ];
 return (<div style={{marginTop:16}}>
  <div style={{margin:"0 2px 6px"}}>
   <div style={{fontWeight:800,fontSize:16,letterSpacing:"-0.01em"}}>🛡 전세 안전 진단</div>
   <div style={{fontSize:12,color:MUTED,marginTop:2}}>등기부등본의 숫자를 넣으면, 경매 시 보증금 회수 여유를 계산해드려요.</div>
  </div>
  <div className="card" style={{padding:"14px 15px"}}>
   <div style={{display:"flex",flexDirection:"column",gap:8}}>
    <div style={{display:"flex",alignItems:"center",gap:8}}><span style={{flex:"none",width:118,fontSize:12.5,fontWeight:700,color:MUTED}}>매매 시세(억)</span><input inputMode="decimal" value={price} onChange={e=>setPrice(e.target.value)} placeholder="예: 3.0 (단지 상세 참고)" style={inp}/></div>
    <div style={{display:"flex",alignItems:"center",gap:8}}><span style={{flex:"none",width:118,fontSize:12.5,fontWeight:700,color:MUTED}}>전세 보증금(억)</span><input inputMode="decimal" value={dep} onChange={e=>setDep(e.target.value)} placeholder="예: 2.5" style={inp}/></div>
    <div style={{display:"flex",alignItems:"center",gap:8}}><span style={{flex:"none",width:118,fontSize:12.5,fontWeight:700,color:MUTED}}>근저당 채권최고액(억)</span><input inputMode="decimal" value={lien} onChange={e=>setLien(e.target.value)} placeholder="등기부 을구 · 없으면 0" style={inp}/></div>
   </div>
   {ratio!=null&&band&&<div style={{marginTop:11,background:"var(--surface-2)",borderRadius:11,padding:"11px 13px"}}>
    <div style={{display:"flex",alignItems:"baseline",gap:8,flexWrap:"wrap"}}>
     <span style={{fontSize:12.5,color:MUTED}}>보증금+선순위 ÷ 시세</span>
     <span className="num" style={{fontWeight:800,fontSize:19,color:band.c}}>{ratio}%</span>
     <span style={{marginLeft:"auto",fontSize:12,fontWeight:800,color:band.c}}>{band.t}</span>
    </div>
    <div style={{fontSize:12.5,color:INK,marginTop:6,lineHeight:1.55}}>{band.m}</div>
    <div style={{fontSize:10.5,color:MUTED,marginTop:6,lineHeight:1.5}}>계산식: (보증금+근저당 채권최고액)÷매매 시세. 채권최고액은 통상 대출원금의 110~130%로 설정돼요. <b>참고 지표</b>이며 경매 배당·법적 판단을 단정하지 않습니다. 시세는 이 앱 단지 상세의 최근 실거래를 참고하세요.</div>
   </div>}
   <button onClick={()=>setOpen(v=>!v)} style={{marginTop:11,width:"100%",border:"1px solid var(--line)",background:"var(--surface-2)",color:INK,fontWeight:700,fontSize:12.5,borderRadius:10,padding:"9px 0",cursor:"pointer"}}>{open?"체크리스트 접기 ▲":"📋 전세 계약 단계별 체크리스트 ▼"}</button>
   {open&&<div style={{marginTop:8}}>
    {CHECK.map(([t,items],i)=>(<div key={i} style={{marginTop:i?10:2}}>
     <div style={{fontSize:12.5,fontWeight:800,color:TEAL,marginBottom:4}}>{t}</div>
     {items.map((it,k)=><div key={k} style={{display:"flex",gap:7,fontSize:12.5,color:INK,lineHeight:1.55,padding:"3px 0"}}><span style={{flex:"none",color:MUTED}}>☐</span><span style={{minWidth:0}}>{it}</span></div>)}
    </div>))}
    <div style={{fontSize:10.5,color:MUTED,marginTop:8,lineHeight:1.5}}>일반적인 절차 안내이며 법률 자문이 아닙니다. 개별 사안은 공인중개사·법률 전문가와 확인하세요.</div>
   </div>}
  </div>
 </div>);
}
function OfficialLinks(){
 const LINKS=[
  ["📜","등기부등본 열람","근저당·가압류 확인 — 대법원 인터넷등기소","https://www.iros.go.kr"],
  ["🏗","건축물대장 발급","위반건축물·용도 확인 — 정부24","https://www.gov.kr"],
  ["📊","실거래가 원본 조회","국토교통부 실거래가 공개시스템","https://rt.molit.go.kr"],
  ["🏷","공시가격 알리미","주택 공시가격(보유세 기준) 확인","https://www.realtyprice.kr"],
  ["🛡","전세보증금 반환보증","역전세 대비 보증보험·안심전세 앱 — HUG","https://www.khug.or.kr"],
  ["💰","대출·예금 금리 비교","금융상품 통합비교공시 — 금융감독원","https://finlife.fss.or.kr"],
  ["🧾","임대차(전월세) 신고","부동산거래관리시스템 — 국토교통부","https://rtms.molit.go.kr"],
  ["🏦","취득·양도세 신고","국세청 홈택스","https://www.hometax.go.kr"],
  ["🏢","청약홈","청약 신청·자격 확인 — 한국부동산원","https://www.applyhome.co.kr"],
  ["🏛","청주시청 부동산 정보","고시·공고·도시계획","https://www.cheongju.go.kr"],
 ];
 return (<div style={{marginTop:16}}>
  <div style={{margin:"0 2px 6px"}}>
   <div style={{fontWeight:800,fontSize:16,letterSpacing:"-0.01em"}}>🔎 계약 전 꼭 확인 <span style={{fontSize:11.5,color:MUTED,fontWeight:600}}>공식 서비스</span></div>
   <div style={{fontSize:12,color:MUTED,marginTop:2}}>청집사가 대신 확인해줄 수 없는 것들이에요. 계약 전 아래 공식 서비스에서 직접 확인하세요.</div>
  </div>
  <div className="card" style={{padding:"4px 15px"}}>
   {LINKS.map(([ic,t,d,u],i)=>(<a key={i} href={u} target="_blank" rel="noopener noreferrer" style={{display:"flex",alignItems:"center",gap:11,padding:"12px 0",borderBottom:i<LINKS.length-1?"1px solid var(--line)":"none",textDecoration:"none"}}>
    <span style={{fontSize:19,flex:"none"}}>{ic}</span>
    <span style={{minWidth:0,flex:1}}>
     <span style={{display:"block",fontWeight:700,fontSize:13.5,color:INK}}>{t}</span>
     <span style={{display:"block",fontSize:11.5,color:MUTED,marginTop:1}}>{d}</span>
    </span>
    <span style={{fontSize:10.5,color:MUTED,flex:"none"}}>{u.replace("https://www.","").replace("https://","")} ↗</span>
   </a>))}
  </div>
  <div style={{fontSize:10.5,color:MUTED,margin:"7px 2px 0",lineHeight:1.5}}>외부 공식 사이트로 이동합니다. 청집사는 위 기관과 무관하며 중개·광고 수익이 없습니다.</div>
 </div>);
}
function MoreTab({onCommute,onBudget,onLoan,account,myHome,onRegisterHome,onClearHome,onOpenHome,go,onLogin,onOnboard}){
 const nm=account?(account.name||account.nickname||"회원"):"게스트";
 return (<div style={{marginTop:6}}>
  <div className="card" style={{padding:"16px",display:"flex",alignItems:"center",gap:13}}>
   <div style={{width:52,height:52,borderRadius:26,flex:"none",background:"linear-gradient(135deg,var(--teal),#14a08f)",color:"#fff",display:"flex",alignItems:"center",justifyContent:"center",fontWeight:800,fontSize:22}}>{(nm[0]||"게")}</div>
   <div style={{minWidth:0,flex:1}}>
    <div style={{fontWeight:800,fontSize:17}}>{nm}</div>
    <div style={{fontSize:12,color:MUTED,marginTop:2}}>{account?(account.role==="agent"?"중개업자":"개인 회원"):"로그인하면 관심·알림을 저장해요"}</div>
   </div>
   {!account&&<button onClick={onLogin} className="btn-primary" style={{flex:"none",fontSize:13,padding:"9px 15px"}}>로그인</button>}
  </div>
  <div className="card" style={{padding:"14px 15px",marginTop:10}}>
   <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:myHome?8:2}}>
    <span style={{fontWeight:800,fontSize:14.5}}>🏠 우리집</span>
    {myHome&&<button onClick={onClearHome} style={{marginLeft:"auto",border:"none",background:"none",color:MUTED,fontWeight:700,fontSize:12,cursor:"pointer"}}>삭제</button>}
   </div>
   {myHome?(
    <div style={{display:"flex",alignItems:"center",gap:10}}>
     <div onClick={onOpenHome} role="button" tabIndex={0} onKeyDown={onEnter(onOpenHome)} style={{minWidth:0,flex:1,cursor:"pointer"}}>
      <div style={{fontWeight:800,fontSize:15.5,overflowWrap:"anywhere"}}>{myHome.complex_name||"우리집"}</div>
      <div style={{fontSize:12,color:MUTED,marginTop:1}}>{[guOf(myHome.gu),myHome.dong].filter(Boolean).join(" · ")||"청주"} · 시세 보기 ›</div>
     </div>
     <button onClick={onRegisterHome} style={{flex:"none",border:"1px solid var(--line)",background:"var(--surface-2)",color:TEAL,fontWeight:700,fontSize:12,padding:"7px 12px",borderRadius:9,cursor:"pointer"}}>변경</button>
    </div>
   ):(
    <div style={{display:"flex",alignItems:"center",gap:10}}>
     <div style={{fontSize:12.5,color:MUTED,flex:1}}>내 아파트를 등록하면 시세·주변 정보를 홈에서 바로 볼 수 있어요.</div>
     <button onClick={onRegisterHome} style={{flex:"none",border:"none",background:TEAL,color:"#fff",fontWeight:800,fontSize:13,padding:"9px 15px",borderRadius:10,cursor:"pointer"}}>등록</button>
    </div>
   )}
  </div>
  <div onClick={onOnboard} role="button" tabIndex={0} onKeyDown={onEnter(onOnboard)} className="card" style={{padding:"14px 15px",marginTop:10,cursor:"pointer",background:"linear-gradient(100deg, rgba(15,118,110,.13), rgba(15,118,110,.03))",display:"flex",alignItems:"center",gap:12}}>
   <span style={{fontSize:24,flex:"none"}}>🧭</span>
   <div style={{minWidth:0,flex:1}}><div style={{fontWeight:800,fontSize:14.5}}>청주가 처음이세요?</div><div style={{fontSize:12,color:MUTED,marginTop:2}}>직장·예산 기반 맞춤 단지 추천 · 3분</div></div>
   <span style={{color:TEAL,fontSize:20,flex:"none"}}>›</span>
  </div>
  <div style={{display:"flex",gap:8,marginTop:10}}>
   <Quick icon="⭐" label="관심 단지" onClick={()=>go&&go("home")}/>
   <Quick icon="🏢" label="청약" onClick={()=>go&&go("subscription")}/>
   <Quick icon="💬" label="게시판" onClick={()=>go&&go("board")}/>
  </div>
  <div style={{margin:"18px 2px 4px"}}>
   <div style={{fontWeight:800,fontSize:16,letterSpacing:"-0.01em"}}>집 찾기 도구</div>
   <div style={{fontSize:12,color:MUTED,marginTop:2}}>조건으로 청주 단지를 찾고, 대출까지 한 번에.</div>
  </div>
  <Tool icon="🧭" title="통근권으로 집 찾기" desc="직장·역까지 시간으로 단지를 찾아보세요" onClick={onCommute}/>
  <Tool icon="💰" title="내 예산 맞춤 추천" desc="보유 현금으로 살 수 있는 청주 단지를 찾아드려요" onClick={onBudget}/>
  <Tool icon="🏦" title="내 대출 한도 계산" desc="이 시세로 얼마까지 받을 수 있는지 바로 확인하세요" onClick={onLoan}/>
  <JeonseGuard/>
  <OfficialLinks/>
  <button onClick={()=>{const t=`🏠 청집사 — 청주 아파트 실거래 시세·급매 포착·호가 검증을 한눈에. 중개·광고 없이 데이터만 보여줘요.\n${location.origin}`;
    if(navigator.share){navigator.share({title:"청집사",text:t,url:location.origin}).catch(()=>{});}
    else{navigator.clipboard&&navigator.clipboard.writeText(t).then(()=>alert("소개 문구를 복사했어요!")).catch(()=>{});}}}
   className="card" style={{width:"100%",padding:"14px 15px",marginTop:12,border:"1px dashed rgba(15,118,110,.4)",background:"transparent",cursor:"pointer",display:"flex",alignItems:"center",gap:12,textAlign:"left"}}>
   <span style={{fontSize:24,flex:"none"}}>📣</span>
   <span style={{minWidth:0,flex:1}}>
    <span style={{display:"block",fontWeight:800,fontSize:14.5,color:INK}}>친구에게 청집사 알리기</span>
    <span style={{display:"block",fontSize:12,color:MUTED,marginTop:2}}>청주로 이사 오는 지인에게 공유해주세요</span>
   </span>
   <span style={{color:TEAL,fontSize:18,flex:"none"}}>›</span>
  </button>
  <div style={{fontSize:11,color:MUTED,margin:"14px 2px 0",lineHeight:1.6}}>※ 대출 한도·예산 추천은 공시·입력값 기반 참고용 추정이며, 실제 조건은 금융회사 심사로 달라집니다.</div>
 </div>);
}
function ComplexTalk({name,lawd}){
 const [d,setD]=useState(null);
 useEffect(()=>{ if(!name)return; let on=true; setD(null);
  fetch(`${API}/community/posts?complex=${encodeURIComponent(name)}&per=5`).then(r=>r.json()).then(j=>{if(on)setD(j&&j.items?j.items:[]);}).catch(()=>{if(on)setD([]);});
  return ()=>{on=false;};
 },[name,lawd]);
 if(!name||d===null)return null;
 return (<Collapsible icon="search" defaultOpen={d.length>0} title={`💬 단지 이야기${d.length?` (${d.length})`:""}`}>
  <div style={{padding:"4px 14px 12px"}}>
   {d.length?d.map((p,i)=>(<div key={p.id||i} style={{padding:"8px 0",borderBottom:"1px solid rgba(99,120,128,.08)"}}>
    <div style={{display:"flex",alignItems:"center",gap:6}}>
     {p.resident&&<span style={{fontSize:10.5,fontWeight:800,color:TEAL,background:"rgba(15,118,110,.12)",borderRadius:6,padding:"2px 7px",flex:"none"}}>🏠 주민</span>}
     <span style={{fontWeight:700,fontSize:13.5,minWidth:0,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{p.title}</span>
     <span style={{marginLeft:"auto",fontSize:11,color:MUTED,flex:"none"}}>💬{p.comment_count??0} ❤️{p.like_count??0}</span>
    </div>
   </div>)):<div style={{fontSize:12.5,color:MUTED,padding:"6px 0"}}>아직 이 단지의 글이 없어요. 첫 글의 주인공이 되어보세요!</div>}
   <div style={{fontSize:11.5,color:MUTED,marginTop:8,lineHeight:1.6}}>게시판 탭에서 글쓰기 시 <b>@단지</b>로 이 단지를 태그하면 여기에 모여요. '우리집'으로 등록한 단지 글엔 <b>🏠 주민</b> 뱃지가 붙어요(자가 등록 기반 표시).</div>
  </div>
 </Collapsible>);
}
function PriceCheck({name,lawd,pt}){
 const [v,setV]=useState(""),[r,setR]=useState(null),[busy,setBusy]=useState(false);
 const run=()=>{const eokV=parseFloat(v); if(!eokV||eokV<=0)return; setBusy(true);
  fetch(`${API}/pricecheck/quote?name=${encodeURIComponent(name)}&lawd_cd=${lawd}&property_type=${pt||"apartment"}&asking=${Math.round(eokV*10000)}`)
   .then(x=>x.json()).then(j=>{setR(j);setBusy(false);}).catch(()=>{setR(null);setBusy(false);});};
 return (<div className="card" style={{padding:"13px 15px",marginTop:8}}>
  <div style={{fontWeight:800,fontSize:14.5}}>💬 이 가격, 괜찮은 거예요?</div>
  <div style={{fontSize:12,color:MUTED,marginTop:2}}>어디서 본 매물 호가를 넣으면, 이 단지 최근 실거래에서 어디쯤인지 알려드려요.</div>
  <div style={{display:"flex",gap:8,marginTop:10}}>
   <input inputMode="decimal" value={v} onChange={e=>setV(e.target.value)} placeholder="예: 3.2" style={{flex:1,minWidth:0,border:"1.5px solid var(--line)",borderRadius:11,padding:"11px 13px",fontSize:15,fontWeight:700,background:"var(--surface-solid)",color:INK}}/>
   <span style={{alignSelf:"center",fontWeight:800,color:MUTED}}>억</span>
   <button onClick={run} disabled={busy} className="btn-primary" style={{flex:"none",padding:"0 18px"}}>{busy?"확인중":"확인"}</button>
  </div>
  {r&&(r.found
   ?<div style={{marginTop:10,background:"var(--surface-2)",borderRadius:11,padding:"11px 13px"}}>
     <div style={{display:"flex",alignItems:"baseline",gap:8,flexWrap:"wrap"}}>
      <span style={{fontSize:12.5,color:MUTED}}>중앙값 대비</span>
      <span className="num" style={{fontWeight:800,fontSize:18,color:r.diff_pct>0?UP:r.diff_pct<0?DOWN:INK}}>{r.diff_pct>0?"+":""}{r.diff_pct}%</span>
      <span style={{fontSize:12.5,color:MUTED}}>· 이 가격 이하 거래 {r.percentile}%</span>
     </div>
     <div style={{fontSize:12,color:INK,marginTop:5,lineHeight:1.55}}>최근 {r.months}개월 {r.count}건 · 중앙값 {eok(r.median)} · 범위 {eok(r.min)}~{eok(r.max)}</div>
     <button onClick={()=>{const t=`『${name}』 호가 ${eok(Math.round(parseFloat(v)*10000))} — 최근 ${r.months}개월 실거래 중앙값(${eok(r.median)}) 대비 ${r.diff_pct>0?"+":""}${r.diff_pct}% · 이 가격 이하 거래 ${r.percentile}%\n(참고용·적정가 단정 아님)\n🏠 청집사 ${location.origin}`;
       if(navigator.share){navigator.share({title:"호가 검증 — 청집사",text:t}).catch(()=>{});}
       else{navigator.clipboard&&navigator.clipboard.writeText(t).then(()=>alert("결과를 복사했어요. 카톡 등에 붙여넣기!")).catch(()=>{});}}}
      style={{marginTop:9,width:"100%",border:"1px solid rgba(15,118,110,.28)",background:"var(--surface-solid)",color:TEAL,fontWeight:800,fontSize:12.5,borderRadius:10,padding:"9px 0",cursor:"pointer"}}>📤 이 결과 공유하기</button>
     <div style={{fontSize:10.5,color:MUTED,marginTop:6,lineHeight:1.5}}>{r.disclaimer}</div>
    </div>
   :<div style={{marginTop:10,fontSize:12.5,color:MUTED}}>{r.note}</div>)}
 </div>);
}
function GuContextBar(){
 const [d,setD]=useState(null);
 useEffect(()=>{fetch(`${API}/pricecheck/gu-context`).then(r=>r.json()).then(setD).catch(()=>setD(null));},[]);
 if(!d||!d.items||!d.items.length)return null;
 return (<div className="card" style={{padding:"11px 13px",marginBottom:10}}>
  <div style={{fontSize:12,fontWeight:800,marginBottom:6}}>📊 참고: 구별 기존 아파트 시세(최근 {d.months}개월)</div>
  <div style={{display:"flex",gap:6,overflowX:"auto"}}>
   {d.items.map(g=>(<div key={g.lawd_cd} style={{flex:"none",background:"var(--surface-2)",borderRadius:10,padding:"8px 11px"}}>
    <div style={{fontSize:11,color:MUTED,fontWeight:700}}>{g.gu}</div>
    <div className="num" style={{fontWeight:800,fontSize:13.5}}>{eok(g.price_median)}</div>
    <div style={{fontSize:10.5,color:MUTED}}>평당 {Math.round(g.ppm_median).toLocaleString()}만</div>
   </div>))}
  </div>
  <div style={{fontSize:10.5,color:MUTED,marginTop:6,lineHeight:1.5}}>{d.disclaimer}</div>
 </div>);
}
function BargainRadar({onOpen}){
 // 급매 신호는 '거래 급상승'과 동일한 압축 티커(TickerBanner) 패턴으로. 한 건 낮은 거래는
 // 특수거래(직거래·가족)일 수 있어 실행 가능성이 제한적 → 큰 카드가 아니라 1줄 티커로 노출.
 const [d,setD]=useState(null);
 useEffect(()=>{fetch(`${API}/pricecheck/bargains`).then(r=>r.json()).then(setD).catch(()=>setD(null));},[]);
 if(!d||!d.items||!d.items.length)return null;
 const items=d.items.map((x,i)=>({...x,rank:i+1,contains_sample_data:x.is_sample}));
 return <TickerBanner label="📉 급매 포착" color={DOWN} bg="rgba(30,95,196,.10)" title="📉 급매 포착"
   info={d.disclaimer||`같은 평형 중앙값보다 크게 낮게 신고된 실거래예요(최근 ${d.months}개월). 특수거래(직거래·가족 등)·사유가 있을 수 있어 실제 급매가 아닐 수 있어요.`}
   items={items}
   metric={it=><span className="num" style={{color:DOWN,fontWeight:800,fontSize:12.5}}>{it.diff_pct}% <span style={{color:MUTED,fontWeight:600,fontSize:11}}>{it.pyeong}평</span></span>}
   onItem={it=>onOpen&&onOpen({complex_name:it.name,lawd_cd:it.lawd_cd,property_type:"apartment",gu:it.gu})}/>;
}
function RentSignal({sig}){
 if(!sig||sig.jeonse_ratio==null)return null;
 const warn=sig.level==="high"||sig.level==="elevated";
 const c=warn?"#C77A1A":sig.level==="low"?TEAL:MUTED;
 const bg=warn?"rgba(199,122,26,.12)":sig.level==="low"?"rgba(15,118,110,.10)":"var(--surface-2)";
 const emoji=sig.level==="high"?"⚠️":sig.level==="low"?"💧":"📊";
 return (<div className="card" style={{padding:"13px 15px",marginTop:8}}>
  <div style={{display:"flex",alignItems:"center",gap:8}}>
   <span style={{fontWeight:800,fontSize:14.5}}>전세가율</span>
   <span className="num" style={{fontWeight:800,fontSize:19,color:c}}>{sig.jeonse_ratio}%</span>
   <span style={{marginLeft:"auto",fontSize:12,fontWeight:800,color:c,background:bg,borderRadius:8,padding:"3px 10px"}}>갭 {sig.gap_label}</span>
  </div>
  <div style={{fontSize:12.5,color:INK,marginTop:7,lineHeight:1.55}}>{emoji} {sig.note}</div>
  <div style={{fontSize:11,color:MUTED,marginTop:6,lineHeight:1.5}}>전세가율 = 전세 보증금 중앙값 ÷ 매매가 중앙값(최근 실거래 기준). <b>참고 지표</b>이며 개별 계약·시점에 따라 다릅니다. 가격 방향·역전세를 단정하지 않습니다.</div>
 </div>);
}
function WorkAccess({items}){
 if(!items||!items.length)return null;   // 거점 미시드면 숨김(왜곡 없음)
 const CAT_ICON={job:"🏭",transit:"🚄",public:"🏛",education:"🎓",medical:"🏥"};
 const CAT_LABEL={job:"직장·산단",transit:"교통",public:"공공",education:"교육",medical:"의료"};
 const jobs=items.filter(h=>h.category==="job");
 const rest=items.filter(h=>h.category!=="job");
 const Row=({h})=>(<div style={{display:"flex",alignItems:"center",gap:8,padding:"7px 0",borderBottom:"1px solid rgba(99,120,128,.08)"}}>
  <span style={{fontSize:15,flex:"none"}}>{CAT_ICON[h.category]||"📍"}</span>
  <span style={{fontWeight:600,fontSize:13.5,minWidth:0,flex:1,overflowWrap:"anywhere"}}>{h.name}</span>
  <span className="num" style={{fontWeight:800,fontSize:13.5,flex:"none"}}>{h.distance_km}km</span>
 </div>);
 return (<Collapsible icon="map" defaultOpen={true} title="🏭 직장·거점 거리">
  <div style={{padding:"4px 14px 12px"}}>
   {jobs.length>0&&<React.Fragment>
    <div style={{fontSize:11.5,color:MUTED,fontWeight:700,margin:"4px 0 2px"}}>주요 직장 · 산업단지</div>
    {jobs.map((h,i)=><Row key={h.key||i} h={h}/>)}
   </React.Fragment>}
   {rest.length>0&&<React.Fragment>
    <div style={{fontSize:11.5,color:MUTED,fontWeight:700,margin:"10px 0 2px"}}>교통 · 공공 · 교육</div>
    {rest.map((h,i)=><Row key={h.key||i} h={h}/>)}
   </React.Fragment>}
   <div style={{fontSize:11,color:MUTED,marginTop:8,lineHeight:1.5}}>단지에서 각 거점까지 <b>직선거리</b>예요(도로 거리·통근시간과 다를 수 있음). 통근시간 기준 탐색은 더보기 → 통근권으로 집 찾기에서.</div>
  </div>
 </Collapsible>);
}
function KidsEnv({places}){
 if(!places||!Object.keys(places).length)return null;
 const cnt=(k)=>places[k]&&places[k].count?places[k].count:0;
 const academy=Object.keys(places).filter(k=>k.indexOf("academy_")===0).reduce((s,k)=>s+cnt(k),0);
 const rows=[["어린이집·유치원",cnt("daycare"),"🧸"],["학원",academy,"📚"],["소아과·병원",cnt("hospital"),"🏥"],["도서관",cnt("library"),"📖"],["체육시설",cnt("sports"),"🏃"],["약국",cnt("pharmacy"),"💊"]];
 const total=rows.reduce((s,r)=>s+r[1],0);
 if(!total)return null;   // 육아 관련 시설 데이터 없으면 표시 안 함(왜곡 없음)
 return (<Collapsible icon="search" defaultOpen={true} title="🧸 육아 환경">
  <div style={{padding:"6px 14px 12px"}}>
   <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:8}}>
    {rows.map(([l,n,e])=>(<div key={l} style={{background:"var(--surface-2)",borderRadius:10,padding:"10px 8px",textAlign:"center"}}>
     <div style={{fontSize:18}}>{e}</div>
     <div className="num" style={{fontWeight:800,fontSize:16,color:n>0?INK:MUTED,marginTop:1}}>{n>0?n:"—"}</div>
     <div style={{fontSize:11,color:MUTED,marginTop:1}}>{l}</div>
    </div>))}
   </div>
   <div style={{fontSize:11,color:MUTED,marginTop:8,lineHeight:1.5}}>반경 약 1.2km 내 공공데이터 기준 개수예요. 실제 대기·정원·학군은 해당 기관·교육청에 확인하세요.</div>
  </div>
 </Collapsible>);
}
function MyHomeCard({home,onOpen,onRegister}){
 const [d,setD]=useState(null);
 useEffect(()=>{ if(!home){setD(null);return;} let on=true; setD(null);
  const q=`name=${encodeURIComponent(home.complex_name||"")}&lawd_cd=${home.lawd_cd||""}&property_type=${home.property_type||"apartment"}`;
  fetch(`${API}/complex/detail?${q}`).then(r=>r.json()).then(j=>{if(on)setD(j&&j.found?j:null);}).catch(()=>{if(on)setD(null);});
  return ()=>{on=false;};
 },[home&&home.complex_name,home&&home.lawd_cd,home&&home.property_type]);
 if(!home)return (
  <div className="card" style={{padding:"14px 15px",marginTop:8,display:"flex",alignItems:"center",gap:12}}>
   <div style={{fontSize:26,flex:"none"}}>🏠</div>
   <div style={{minWidth:0,flex:1}}>
    <div style={{fontWeight:800,fontSize:14.5}}>우리집 등록하기</div>
    <div style={{fontSize:12,color:MUTED,marginTop:2}}>내 아파트를 등록하면 시세·주변 정보를 홈에서 바로 봐요</div>
   </div>
   <button onClick={onRegister} style={{flex:"none",border:"none",background:TEAL,color:"#fff",fontWeight:800,fontSize:13,padding:"9px 15px",borderRadius:10,cursor:"pointer"}}>등록</button>
  </div>);
 let mom=null;
 if(d&&d.timeseries&&d.timeseries.length>=2){const ts=d.timeseries,a=ts[ts.length-2].avg,b=ts[ts.length-1].avg;if(a&&b)mom=Math.round((b-a)/a*1000)/10;}
 const region=d&&d.vs_region?d.vs_region.pct:null;
 const latest=d?d.latest_amount:null;
 return (
  <div className="card" style={{padding:"14px 15px",marginTop:8}}>
   <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:8}}>
    <span style={{fontWeight:800,fontSize:14.5}}>🏠 우리집</span>
    <button onClick={onRegister} style={{marginLeft:"auto",border:"none",background:"none",color:MUTED,fontWeight:700,fontSize:12,cursor:"pointer"}}>변경</button>
   </div>
   <div onClick={()=>onOpen&&onOpen(home)} role="button" tabIndex={0} onKeyDown={onEnter(()=>onOpen&&onOpen(home))} style={{cursor:"pointer"}}>
    <div style={{display:"flex",alignItems:"center",gap:10}}>
     <div style={{minWidth:0,flex:1}}>
      <div style={{fontWeight:800,fontSize:16,overflowWrap:"anywhere"}}>{home.complex_name||"우리집"}</div>
      <div style={{fontSize:12.5,color:MUTED,marginTop:2}}>{[guOf(home.gu),home.dong,TYPE_LABEL[home.property_type]].filter(Boolean).join(" · ")||"청주"}</div>
     </div>
     <span style={{color:TEAL,fontWeight:800,fontSize:13,flex:"none"}}>시세 ›</span>
    </div>
    <div style={{display:"flex",alignItems:"baseline",gap:9,marginTop:9,paddingTop:9,borderTop:"1px solid var(--line)"}}>
     <span style={{fontSize:11.5,color:MUTED,flex:"none"}}>최근 매매가</span>
     {d===null
      ? <span className="num" style={{fontSize:18,fontWeight:800,color:MUTED}}>불러오는 중…</span>
      : latest!=null
       ? <React.Fragment><span className="num" style={{fontSize:20,fontWeight:800,lineHeight:1}}>{eok(latest)}</span>
         {mom!=null&&<span style={{fontSize:12}}>전월 <Delta v={mom}/></span>}
         {mom==null&&region!=null&&<span style={{fontSize:12}}>지역대비 <Delta v={region}/></span>}</React.Fragment>
       : <span style={{fontSize:12.5,color:MUTED}}>최근 실거래가 없어 시세를 낼 수 없어요</span>}
    </div>
   </div>
  </div>);
}
function CityIssues(){
 const [items,setItems]=useState(null);
 useEffect(()=>{let on=true;
  fetch(`${API}/landmarks`).then(r=>r.json()).then(j=>{if(on)setItems(Array.isArray(j)?j:[]);}).catch(()=>{if(on)setItems([]);});
  return ()=>{on=false;};},[]);
 if(!items||!items.length)return null;   // 데이터 없으면 표시 안 함(왜곡 없음)
 return (<div className="card" style={{padding:"13px 15px",marginTop:8}}>
  <div style={{display:"flex",alignItems:"center",gap:6}}>
   <span style={{fontWeight:800,fontSize:15}}>🏗 청주는 지금</span>
   <span style={{fontSize:11.5,color:MUTED}}>개발 이슈</span>
  </div>
  <div style={{fontSize:11.5,color:MUTED,margin:"2px 0 6px"}}>청주 부동산에 영향을 줄 만한 개발 이슈예요. 출처를 함께 확인하세요.</div>
  <MoreList items={items} initial={3} step={3} render={(L,i)=>{
   const sc=L.status==="confirmed"?TEAL:L.status==="ongoing"?"#C77A1A":MUTED;
   return (<div key={L.id||i} style={{padding:"9px 0",borderTop:i>0?"1px solid var(--line)":"none"}}>
    <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
     <span style={{fontSize:10.5,fontWeight:800,color:"#fff",background:sc,borderRadius:6,padding:"2px 7px"}}>{L.status_label}</span>
     <span style={{fontWeight:800,fontSize:14}}>{L.name}</span>
     <span style={{fontSize:11.5,color:MUTED}}>{L.category_label}{L.expected_year?` · ${L.expected_year}년`:""}</span>
    </div>
    {L.summary&&<div style={{fontSize:12.5,color:INK,marginTop:4,lineHeight:1.5}}>{L.summary}</div>}
    {L.source_name&&<div style={{fontSize:11,color:MUTED,marginTop:3}}>출처: {L.source_url?<a href={L.source_url} target="_blank" rel="noreferrer" style={{color:TEAL}}>{L.source_name}</a>:L.source_name}</div>}
   </div>);
  }}/>
  <div style={{fontSize:10.5,color:MUTED,marginTop:6,lineHeight:1.5}}>※ 개발 이슈는 진행 상황에 따라 변동될 수 있는 참고 정보입니다. 투자 판단·집값 상승을 보장하지 않습니다.</div>
 </div>);
}
function Board({board,favs,onOpen,onToggleFav,go,onGu,myGu,setMyGu,recents,onToggleRegion,feed,onCommute,onBudget,onLoan,myHome,onRegisterHome,onClearHome,onOnboard,onbDone}){
 const b=board||{}, gt=b.gu_trend||{months:[],series:[]}, vol=b.volume||{};
 const city=b.city||{};
 const unit=useUnit();
 const GU4=["상당구","서원구","흥덕구","청원구"];
 const [showIntro,setShowIntro]=useState(()=>!safeStore.get("cj_onboard_v1"));
 const dismissIntro=()=>{try{safeStore.set("cj_onboard_v1","1");}catch(e){} setShowIntro(false);};
 const regionFav=new Set((favs||[]).filter(f=>f.target_type==="region").map(f=>(f.meta&&f.meta.gu)||f.name));
 const favComplexGus=new Set((favs||[]).filter(f=>f.target_type!=="region").map(f=>f.meta&&f.meta.gu).filter(Boolean));
 const recs=[];
 (b.recent_by_gu||[]).forEach(grp=>(grp.items||[]).forEach(it=>{
  if(!it.complex_name||!it.is_high)return;
  let reason="최근 신고가",pri=3;
  if(grp.gu===myGu){reason="내 동네 신고가";pri=1;}
  else if(regionFav.has(grp.gu)||favComplexGus.has(grp.gu)){reason="관심 지역 신고가";pri=2;}
  recs.push({...it,gu:grp.gu,reason,pri});
 }));
 recs.sort((a,b)=>a.pri-b.pri);
 const recTop=recs.slice(0,4);
 return (<div style={{marginTop:6}}>
  {showIntro&&<div className="card" style={{padding:"14px 15px",marginTop:4,marginBottom:8,position:"relative",background:"linear-gradient(120deg,rgba(15,118,110,.12),rgba(15,118,110,.03))"}}>
   <span onClick={dismissIntro} aria-label="환영 안내 닫기" style={{position:"absolute",top:6,right:12,cursor:"pointer",color:MUTED,fontSize:20,lineHeight:1,fontWeight:600}}>×</span>
   <div style={{fontWeight:800,fontSize:15}}>청집사에 오신 걸 환영해요 👋</div>
   <div style={{fontSize:12.5,color:MUTED,margin:"3px 0 10px",lineHeight:1.5}}>집 찾기, 이렇게도 할 수 있어요 — 눌러서 바로 시작하세요.</div>
   <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
    <button onClick={()=>onCommute&&onCommute()} className="tog" style={{fontSize:12.5}}>🚆 통근시간으로</button>
    <button onClick={()=>onBudget&&onBudget()} className="tog" style={{fontSize:12.5}}>💰 예산으로</button>
    <button onClick={()=>onLoan&&onLoan()} className="tog" style={{fontSize:12.5}}>🏦 대출 한도</button>
   </div>
  </div>}
  {/* 청주 시세 요약(히어로) — 숨김(홈에서 제외, 부활 시 false 제거) */}
  {false&&<div className="card" style={{padding:"14px 15px",marginBottom:8}}>
   <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
    <span style={{fontSize:13.5,fontWeight:800}}>청주 아파트 시세</span>
    <span style={{fontSize:11,color:MUTED}}>· 최근 {AGG_MONTHS}개월 평균</span>
    {b.contains_sample_data&&<ExBadge/>}
    {city.as_of&&<span style={{marginLeft:"auto",fontSize:11,color:MUTED}} className="num">{city.as_of} 기준</span>}
   </div>
   <div style={{display:"flex",gap:18,marginTop:9,flexWrap:"wrap"}}>
    <div style={{minWidth:120}}>
     <div style={{fontSize:11.5,color:MUTED}}>평균 매매가</div>
     <div className="num" style={{fontSize:23,fontWeight:800,lineHeight:1.15}}>{city.avg_mae!=null?eok(city.avg_mae):"표본부족"}</div>
     {city.avg_mae!=null&&<div style={{fontSize:11.5,color:MUTED,marginTop:1}}>전월 <Delta v={city.mae_dM}/> · 전년 <Delta v={city.mae_dY}/></div>}
    </div>
    <div style={{minWidth:100}}>
     <div style={{fontSize:11.5,color:MUTED}}>평균 전세가</div>
     <div className="num" style={{fontSize:23,fontWeight:800,lineHeight:1.15}}>{city.avg_jeon!=null?eok(city.avg_jeon):"—"}</div>
     {city.trade_count!=null&&<div style={{fontSize:11.5,color:MUTED,marginTop:1}}>매매 {city.trade_count.toLocaleString("ko-KR")}건</div>}
    </div>
   </div>
   {false&&<button onClick={()=>go&&go("price")} style={{marginTop:11,width:"100%",border:"1px solid rgba(15,118,110,.28)",background:"rgba(15,118,110,.06)",color:TEAL,fontWeight:700,fontSize:12.5,borderRadius:10,padding:"9px 0",cursor:"pointer"}}>청주 전체 시세 보기 →</button>}
  </div>}

  {!onbDone&&<button onClick={onOnboard} style={{width:"100%",textAlign:"left",border:"none",cursor:"pointer",borderRadius:16,padding:"15px 16px",marginTop:8,background:"linear-gradient(100deg, rgba(15,118,110,.14), rgba(15,118,110,.04))",display:"flex",alignItems:"center",gap:12}}>
   <span style={{fontSize:26,flex:"none"}}>🧭</span>
   <span style={{minWidth:0,flex:1}}>
    <span style={{display:"block",fontWeight:800,fontSize:14.5,color:INK}}>청주가 처음이세요?</span>
    <span style={{display:"block",fontSize:12,color:MUTED,marginTop:2}}>직장·예산만 알려주면 맞춤 단지를 찾아드려요 · 3분</span>
   </span>
   <span style={{color:TEAL,fontSize:20,flex:"none"}}>›</span>
  </button>}
  <MyHomeCard home={myHome} onOpen={onOpen} onRegister={onRegisterHome}/>

  <RecentList recents={recents} onOpen={onOpen}/>

  <CityIssues/>

  <BargainRadar onOpen={onOpen}/>

  {b.trending&&b.trending.items&&b.trending.items.length>0&&
   <TickerBanner label={b.trending.basis==="surge"?"🔥 거래 급상승":"🔥 거래 활발"} color={UP} bg="rgba(200,50,42,.10)"
    title={b.trending.basis==="surge"?"🔥 거래 급상승":"🔥 거래 활발"}
    info="최근 90일 거래 신고가 직전 90일보다 늘어난 단지 순입니다. 조회수가 아니라 실제 거래 건수 기준이며, 신고 지연·정정이 반영될 수 있어요."
    items={b.trending.items}
    metric={it=>it.delta>0
     ?<span className="num" style={{color:UP,fontWeight:800,fontSize:12.5}}>▲{it.delta}건</span>
     :<span className="num" style={{color:MUTED,fontWeight:700,fontSize:12.5}}>{it.recent_count}건</span>}
    onItem={it=>onOpen&&onOpen({complex_name:it.name,lawd_cd:it.lawd_cd,property_type:it.property_type})}/>}

  {b.landmark&&b.landmark.length>0&&(()=>{
   const lm=b.landmark.slice().sort((x,y)=>(y.price||0)-(x.price||0)).map((o,i)=>({...o,rank:i+1,lawd_cd:o.lawd_cd||o.code}));
   return <TickerBanner label="👑 대장 아파트" color="#9A6B00" bg="rgba(178,106,0,.12)"
    title="👑 대장 아파트" info="단지별 대표 매매가(중앙값) 상위입니다. 최고가 1건이 아니라 거래 중앙값 기준이라 이상치에 덜 흔들려요. 최근 집계 기간 거래 기준."
    items={lm}
    metric={it=><span className="num" style={{fontWeight:800,fontSize:13}}>{eok(it.price)}</span>}
    onItem={it=>onOpen&&onOpen({complex_name:it.name,lawd_cd:it.lawd_cd,property_type:b.property_type||"apartment"})}/>;
  })()}

  <FavList favs={favs} onOpen={onOpen} onToggleFav={onToggleFav} onGu={onGu} onToggleRegion={onToggleRegion}/>

  <TodayInfo feed={feed} go={go}/>
 </div>);
}

/* ---------------- 소식: 청약·뉴스·정책 ---------------- */
function SubChip({children}){
 return <span style={{fontSize:11.5,fontWeight:700,background:"rgba(15,118,110,.10)",color:TEAL,padding:"3px 8px",borderRadius:7,whiteSpace:"nowrap"}}>{children}</span>;
}
function _parseYmd(v){if(!v)return null;const d=String(v).replace(/[^0-9]/g,"");if(d.length<8)return null;const dt=new Date(+d.slice(0,4),+d.slice(4,6)-1,+d.slice(6,8));return isNaN(dt.getTime())?null:dt;}
function subDday(s){const t=new Date();t.setHours(0,0,0,0);
 if(s.status==="접수예정"){const b=_parseYmd(s.begin);if(b){const n=Math.round((b-t)/86400000);if(n>=0)return{txt:n===0?"오늘 접수시작":`접수 D-${n}`,urgent:n<=3};}}
 if(s.status==="접수중"){const e=_parseYmd(s.end);if(e){const n=Math.round((e-t)/86400000);if(n>=0)return{txt:n===0?"오늘 마감":`마감 D-${n}`,urgent:true};}}
 return null;}
function SubCard({s,onOpen}){
 const c=s.status==="접수중"?{bg:"#E4F2E8",fg:"#1d6b3a",g1:"#1d6b3a",g2:"#2f9e5c"}:s.status==="접수예정"?{bg:"#E7EEF6",fg:"#1E5FC4",g1:"#1E5FC4",g2:"#4f86e0"}:{bg:"#EEF1F1",fg:MUTED,g1:"#6b7780",g2:"#8a949c"};
 const cr=s.competition_range;
 const compTxt=cr?(cr[0]===cr[1]?`${cr[0]}:1`:`${cr[0]}~${cr[1]}:1`):null;
 const ht=s.house_types||[];
 const dd=subDday(s);
 return (<div className="card" style={{padding:0,overflow:"hidden",marginBottom:8,cursor:onOpen?"pointer":"default"}} onClick={onOpen?()=>onOpen(s):undefined}>
  <div style={{position:"relative",padding:"14px 14px 13px",background:`linear-gradient(120deg,${c.g1},${c.g2})`,color:"#fff",overflow:"hidden"}}>
   <div style={{position:"absolute",right:-8,bottom:-18,fontSize:78,opacity:.16,lineHeight:1}}>🏢</div>
   <div style={{display:"flex",alignItems:"center",gap:8,position:"relative"}}>
    <span style={{fontSize:11,fontWeight:800,background:"rgba(255,255,255,.22)",borderRadius:6,padding:"2px 8px"}}>{s.status}</span>
    {dd&&<span style={{fontSize:11,fontWeight:800,background:dd.urgent?"#fff":"rgba(255,255,255,.22)",color:dd.urgent?c.g1:"#fff",borderRadius:6,padding:"2px 8px"}}>{dd.txt}</span>}
    {s.is_sample&&<span style={{marginLeft:"auto",fontSize:10,fontWeight:800,background:"rgba(255,255,255,.25)",borderRadius:5,padding:"2px 6px"}}>예시</span>}
   </div>
   <div style={{fontWeight:800,fontSize:16.5,marginTop:8,position:"relative",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{s.name}</div>
   <div style={{fontSize:12,opacity:.92,marginTop:2,position:"relative"}}>{[s.location,s.units?`총 ${s.units}세대`:null].filter(Boolean).join(" · ")}</div>
  </div>
  <div style={{padding:"11px 14px"}}>
   <div style={{fontSize:12,color:MUTED}}>📅 {s.period}</div>
   {(s.price||compTxt||s.min_score!=null)&&<div style={{display:"flex",flexWrap:"wrap",gap:"5px 7px",marginTop:8}}>
    {s.price&&<SubChip>분양가 {s.price}</SubChip>}
    {compTxt&&<SubChip>경쟁률 {compTxt}</SubChip>}
    {s.min_score!=null&&<SubChip>최저가점 {s.min_score}</SubChip>}
   </div>}
   {ht.length>0&&<div style={{marginTop:9,borderTop:"1px solid var(--line)",paddingTop:7}}>
    <div style={{fontSize:11,color:MUTED,marginBottom:3}}>주택형별 {onOpen&&<span style={{color:TEAL,fontWeight:700}}>· 자세히 ›</span>}</div>
    {ht.slice(0,3).map((h,i)=>(<div key={i} style={{display:"flex",gap:8,fontSize:12.5,padding:"2px 0",alignItems:"baseline"}}>
     <span style={{fontWeight:700,minWidth:50,flex:"none"}}>{h.type||"-"}</span>
     <span className="num" style={{color:MUTED}}>{[h.units?`${h.units}세대`:null,h.price,h.competition?`경쟁 ${h.competition}`:null,(h.min_score!=null)?`가점 ${h.min_score}`:null].filter(Boolean).join(" · ")||"집계 전"}</span>
    </div>))}
    {ht.length>3&&<div style={{fontSize:11.5,color:MUTED,marginTop:2}}>외 {ht.length-3}개 주택형 ›</div>}
   </div>}
  </div>
 </div>);
}
function SubDetail({s,onClose}){
 const c=s.status==="접수중"?{bg:"#E4F2E8",fg:"#1d6b3a"}:s.status==="접수예정"?{bg:"#E7EEF6",fg:"#1E5FC4"}:{bg:"#EEF1F1",fg:MUTED};
 const cr=s.competition_range;
 const compTxt=cr?(cr[0]===cr[1]?`${cr[0]}:1`:`${cr[0]}~${cr[1]}:1`):null;
 const ht=s.house_types||[];
 const closed=s.status==="마감";
 const url=s.url||"https://www.applyhome.co.kr";
 const Row=({k,v})=>v?(<div style={{display:"flex",gap:10,padding:"6px 0",borderBottom:"1px solid rgba(99,120,128,.10)"}}><span style={{fontSize:12.5,color:MUTED,width:72,flex:"none"}}>{k}</span><span style={{fontSize:13.5,fontWeight:600}}>{v}</span></div>):null;
 return (<div style={{marginTop:6}}>
  <div style={{display:"flex",alignItems:"center",gap:8}}>
   <div style={{fontWeight:800,fontSize:18,minWidth:0,overflow:"hidden",textOverflow:"ellipsis"}}>{s.name} {s.is_sample&&<ExBadge/>}</div>
   <span className="statusdot" style={{marginLeft:"auto",flex:"none",background:c.bg,color:c.fg}}>{s.status}</span>
  </div>
  {closed&&<div style={{background:"var(--callout-bg)",color:"var(--callout-fg)",borderRadius:10,padding:"9px 12px",fontSize:12.5,fontWeight:600,lineHeight:1.6,marginTop:10}}>ⓘ 이미 마감된 공고예요. 아래는 경쟁률·가점 등 결과·기록 참고용입니다.</div>}
  <div className="card" style={{padding:"10px 14px",marginTop:12}}>
   <Row k="지역" v={s.location}/>
   <Row k="청약기간" v={s.period}/>
   <Row k="총 공급" v={s.units?`${s.units}세대`:null}/>
   <Row k="분양가" v={s.price}/>
   <Row k="시행사" v={s.builder}/>
   <Row k="모집공고일" v={s.notice_date}/>
   <Row k="경쟁률" v={compTxt||(s.status==="접수예정"?"집계 전":null)}/>
   <Row k="최저가점" v={s.min_score!=null?String(s.min_score):null}/>
  </div>
  {ht.length>0&&<div className="card" style={{padding:"12px 14px",marginTop:10}}>
   <div style={{fontWeight:800,fontSize:14,marginBottom:8}}>주택형별</div>
   {ht.map((h,i)=>(<div key={i} style={{padding:"7px 0",borderTop:i?"1px solid rgba(99,120,128,.12)":"none"}}>
    <div style={{display:"flex",alignItems:"baseline",gap:8}}>
     <span style={{fontWeight:800,fontSize:13.5}}>{h.type||"-"}</span>
     {h.units!=null&&<span style={{fontSize:12,color:MUTED}}>{h.units}세대</span>}
     {h.price&&<span className="num" style={{marginLeft:"auto",fontWeight:700,fontSize:13.5}}>{h.price}</span>}
    </div>
    {(h.competition||h.min_score!=null||h.avg_score!=null)&&<div className="num" style={{fontSize:12,color:MUTED,marginTop:3,display:"flex",flexWrap:"wrap",gap:"3px 10px"}}>
     {h.competition&&<span>경쟁 {h.competition}</span>}
     {h.min_score!=null&&<span>최저가점 {h.min_score}</span>}
     {h.avg_score!=null&&<span>평균가점 {h.avg_score}</span>}
    </div>}
   </div>))}
  </div>}
  <div style={{display:"flex",gap:8,marginTop:12}}>
   <a href={`https://map.naver.com/p/search/${encodeURIComponent((s.location||"청주")+" "+(s.name||""))}`} target="_blank" rel="noopener noreferrer" style={{flex:"none",display:"flex",alignItems:"center",justifyContent:"center",gap:5,textDecoration:"none",background:"var(--surface-2)",color:INK,fontWeight:800,fontSize:13.5,padding:"12px 16px",borderRadius:11,border:"1px solid var(--line)"}}>📍 지도</a>
   <a href={url} target="_blank" rel="noopener noreferrer" style={{flex:1,display:"flex",alignItems:"center",justifyContent:"center",gap:6,textDecoration:"none",background:TEAL,color:"#fff",fontWeight:800,fontSize:14,padding:"12px 0",borderRadius:11}}>청약홈에서 보기 →</a>
  </div>
  <div style={{fontSize:10.5,color:MUTED,marginTop:11,lineHeight:1.6}}>※ 청약 신청·당첨 결과의 최종 정보는 청약홈(applyhome.co.kr)에서 확인하세요. 경쟁률·가점은 집계 시점에 따라 갱신됩니다. 자료: 한국부동산원 청약홈.</div>
 </div>);
}
function SubSheet({s,onClose}){
 return (<SheetShell onClose={onClose} zIndex={120} scrollKey={s&&s.name}>
  <SubDetail s={s} onClose={onClose}/>
 </SheetShell>);
}
function SubscriptionTab(){
 const [data,setData]=useState(null);
 const [filter,setFilter]=useState("전체");
 const [mtab,setMtab]=useState("bunyang");   // bunyang(분양 정보) | cheongyak(청약 일정)
 const [sel,setSel]=useState(null);
 useEffect(()=>{let on=true;
  fetch(`${API}/subscription?limit=50`).then(r=>r.json())
   .then(j=>{if(on)setData(j);})
   .catch(()=>{if(on)setData({items:(DEMO_FEED.subscriptions||[]),live:false,
     notice:"청약홈 API 미연동 — 아래는 예시입니다(키 설정 시 실데이터).",
     disclaimer:"자료: 한국부동산원 청약홈. 최종은 청약홈에서 확인하세요."});});
  return ()=>{on=false;};},[]);
 if(!data) return <div style={{marginTop:10}}><SkeletonCard lines={3}/><SkeletonCard lines={3}/></div>;
 const all=data.items||[];
 const FIL=["전체","접수중","접수예정","마감"];
 const counts={}; FIL.forEach(f=>{counts[f]=f==="전체"?all.length:all.filter(s=>s.status===f).length;});
 const list=filter==="전체"?all:all.filter(s=>s.status===filter);
 const openList=all.filter(s=>s.status==="접수중"||s.status==="접수예정")
   .sort((a,b)=>((a.status==="접수중"?0:1)-(b.status==="접수중"?0:1))||String(a.begin||a.period||"").localeCompare(String(b.begin||b.period||"")));
 const seg=(active)=>({flex:1,border:"none",cursor:"pointer",fontWeight:800,fontSize:13.5,padding:"10px 0",borderRadius:9,background:active?"var(--surface-solid)":"transparent",color:active?INK:MUTED,boxShadow:active?"0 1px 3px rgba(30,64,90,.12)":"none"});
 return (<div style={{marginTop:6}}>
  <div style={{margin:"2px 2px 10px"}}>
   <div style={{fontWeight:800,fontSize:17,letterSpacing:"-0.01em"}}>청주 분양·청약</div>
   <div style={{fontSize:12,color:MUTED,marginTop:2}}>분양 공고 정보와, 지금 넣을 수 있는 청약 일정을 나눠서 확인하세요.</div>
  </div>
  <div style={{display:"flex",gap:6,background:"var(--chip)",borderRadius:11,padding:4,marginBottom:10}}>
   <button onClick={()=>setMtab("bunyang")} style={seg(mtab!=="cheongyak")}>🏢 분양 정보</button>
   <button onClick={()=>setMtab("cheongyak")} style={seg(mtab==="cheongyak")}>📋 청약 일정{openList.length?` ${openList.length}`:""}</button>
  </div>
  <GuContextBar/>
  {data.notice&&<div style={{background:"var(--callout-bg)",color:"var(--callout-fg)",borderRadius:10,padding:"9px 13px",fontSize:12.5,fontWeight:600,lineHeight:1.6,marginBottom:8}}>ⓘ {data.notice} <b>예시</b> 배지 항목은 실제 정보가 아닙니다.</div>}
  {mtab==="cheongyak"?<React.Fragment>
   <div style={{fontSize:12,color:MUTED,margin:"0 2px 8px",lineHeight:1.5}}>지금 접수 중이거나 곧 시작하는 청약이에요. <b>임박한 순</b>으로 보여드립니다.</div>
   {openList.length?<MoreList items={openList} initial={10} step={10} render={(s,i)=><SubCard key={i} s={s} onOpen={setSel}/>}/>
    :<Empty>지금 접수 중이거나 예정인 청약이 없습니다. ‘분양 정보’에서 지난 공고를 볼 수 있어요.</Empty>}
  </React.Fragment>:<React.Fragment>
   <div className="card sticky-filter" style={{padding:"8px 10px",marginBottom:10,display:"flex",gap:6,flexWrap:"wrap"}}>
    {FIL.map(f=><button key={f} className={"tog"+(filter===f?" on":"")} onClick={()=>setFilter(f)} style={{padding:"7px 12px"}}>{f}{counts[f]>0?` ${counts[f]}`:""}</button>)}
   </div>
   {list.length?<MoreList items={list} initial={10} step={10} render={(s,i)=><SubCard key={i} s={s} onOpen={setSel}/>}/>
    :<Empty action={filter!=="전체"?<button className="tog" onClick={()=>setFilter("전체")}>전체 보기</button>:null}>
      {filter==="전체"?"현재 청주 지역 분양 공고가 없습니다.":`'${filter}' 상태의 공고가 없습니다.`}</Empty>}
  </React.Fragment>}
  {data.disclaimer&&<div style={{fontSize:11,color:MUTED,marginTop:10,lineHeight:1.6}}>{data.disclaimer}</div>}
  {sel&&<SubSheet s={sel} onClose={()=>setSel(null)}/>}
 </div>);
}
function News({feed}){
 feed=feed||{};
 return (<div style={{marginTop:6}}>
  {feed.data_pending&&<div style={{background:"var(--callout-bg)",color:"var(--callout-fg)",borderRadius:10,padding:"9px 13px",margin:"4px 0 0",fontSize:12.5,fontWeight:600,lineHeight:1.6}}>
   ⓘ {feed.notice||"뉴스·정책 일부는 준비중입니다."} <b>예시</b> 배지가 붙은 항목은 실제 정보가 아닙니다.</div>}

  <Collapsible icon="news" defaultOpen={true} title="부동산 뉴스">
   <div style={{padding:"4px 14px"}}>
   {(feed.news||[]).map((n,i)=>{const inner=(<React.Fragment>
     <div style={{minWidth:0}}>
      <div style={{fontWeight:600,overflow:"hidden",textOverflow:"ellipsis"}}>{n.title} {n.is_sample&&<ExBadge/>}</div>
      {n.summary&&<div style={{fontSize:12,color:MUTED,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{n.summary}</div>}
      <div style={{fontSize:11.5,color:MUTED,marginTop:1}}>{n.source} · {n.date}</div>
     </div>
     <span style={{marginLeft:"auto",color:MUTED,fontSize:18}}>›</span>
    </React.Fragment>);
    return (n.url&&n.url!=="#")
     ? <a key={i} className="listrow" href={n.url} target="_blank" rel="noopener noreferrer" style={{textDecoration:"none",color:"inherit"}}>{inner}</a>
     : <div key={i} className="listrow">{inner}</div>;})}
   </div>
  </Collapsible>

  <Collapsible icon="doc" defaultOpen={true} title="정책·지원">
   <div style={{padding:"4px 14px"}}>
   {(feed.policies||[]).map((p2,i)=>(<div key={i} className="listrow" style={{alignItems:"flex-start"}}>
    <div style={{minWidth:0}}>
     <div style={{fontWeight:600}}>{p2.title} {p2.is_sample&&<ExBadge/>}</div>
     <div style={{fontSize:12.5,color:MUTED,marginTop:2}}>{p2.summary}</div>
     <div style={{fontSize:11.5,color:MUTED,marginTop:2}}>{p2.source} · {p2.date}</div>
    </div>
   </div>))}
   </div>
  </Collapsible>
 </div>);
}

/* ---------------- 네이버 지도 ---------------- */
function Notice({children}){return <div style={{background:"var(--callout-bg)",color:"var(--callout-fg)",borderRadius:12,padding:"11px 14px",fontSize:12.5,fontWeight:600,lineHeight:1.6}}>{children}</div>;}
function useNaver(clientId,enabled){
 const [ready,setReady]=useState(false);
 const [err,setErr]=useState(false);
 useEffect(()=>{
  if(!enabled||!clientId)return;
  window.navermap_authFailure=function(){setErr(true);};
  if(window.naver&&window.naver.maps){setReady(true);return;}
  let sc=document.getElementById("naver-sdk");
  if(sc){const t=setInterval(()=>{if(window.naver&&window.naver.maps){setReady(true);clearInterval(t);}},200);return ()=>clearInterval(t);}
  sc=document.createElement("script");sc.id="naver-sdk";
  sc.src=`https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${clientId}`;
  sc.onload=()=>setReady(true); sc.onerror=()=>setErr(true);
  document.head.appendChild(sc);
 },[clientId,enabled]);
 return {ready,err};
}
function PriceMarkerMap({markers, bands, deal, fitKey, mapCfg, onOpenComplex, onViewport, poiCats, showLm, showBg, onMapReady, full}){
 const {ready,err}=useNaver(mapCfg.key,mapCfg.enabled);
 const ref=React.useRef(null);
 const mapObj=React.useRef(null);
 const markerObjs=React.useRef([]);
 const poiObjs=React.useRef([]);
 const lmObjs=React.useRef([]);
 const bgObjs=React.useRef([]);   // 급매(낮은가격 거래) 핀
 const fitDone=React.useRef("");
 const [tick,setTick]=useState(0);
 const POI_META={education:{c:"#7A5AF8",e:"🎓"},sports:{c:"#2563D8",e:"🏃"},living:{c:"#0E7C71",e:"🏪"}};
 const label=(v)=>deal==="trade"?Number(v).toLocaleString():eok(v);
 const money=(m)=>m==null?"—":(m/10000>=100?Math.round(m/10000)+"억":(m/10000).toFixed(1).replace(/\.0$/,"")+"억");
 const mlabel=(it)=>{const amt=deal==="trade"?(it.t==="c"?it.amt:it.median_amount):it.value;return money(amt);};
 const colorFor=(v)=>{const pal=["#4F86C6","#56A36B","#E0B341","#E08C3B","#D2543B"];
  if(!bands||!bands.length)return pal[2]; let i=0; while(i<bands.length&&v>bands[i])i++; return pal[Math.min(i,4)];};
 // 지도 1회 생성 + idle(디바운스) 리스너 + 언마운트 정리
 useEffect(()=>{
  if(!ready||!ref.current||!window.naver)return;
  const n=window.naver;
  if(!mapObj.current){
   mapObj.current=new n.maps.Map(ref.current,{center:new n.maps.LatLng(36.6424,127.489),zoom:12});
  }
  let t=null;
  const listener=n.maps.Event.addListener(mapObj.current,"idle",()=>{clearTimeout(t);t=setTimeout(()=>setTick(x=>x+1),350);});
  setTick(x=>x+1);
  return ()=>{ clearTimeout(t); try{n.maps.Event.removeListener(listener);}catch(e){}
   markerObjs.current.forEach(mk=>{try{mk.setMap(null);}catch(e){}}); markerObjs.current=[];
   poiObjs.current.forEach(mk=>{try{mk.setMap(null);}catch(e){}}); poiObjs.current=[];
   lmObjs.current.forEach(mk=>{try{mk.setMap(null);}catch(e){}}); lmObjs.current=[]; };
 },[ready]);
 // 마커 렌더(틱/마커/필터 변화 시) — 보이는 영역만 클러스터링 + 뷰포트 요약
 useEffect(()=>{
  if(!ready||!mapObj.current||!window.naver)return;
  const n=window.naver, map=mapObj.current;
  if(fitKey&&fitDone.current!==fitKey&&markers.length){
   const b=new n.maps.LatLngBounds(); markers.forEach(m=>b.extend(new n.maps.LatLng(m.lat,m.lng)));
   try{map.fitBounds(b);}catch(e){} fitDone.current=fitKey;
  }
  const z=map.getZoom(); const bounds=map.getBounds();
  const inB=m=>{try{return bounds.hasLatLng(new n.maps.LatLng(m.lat,m.lng));}catch(e){return true;}};
  const vis=markers.filter(inB);
  if(onViewport){const vs=vis.map(m=>m.value).sort((a,b)=>a-b);
   onViewport({count:vis.length,median:vs.length?vs[Math.floor(vs.length/2)]:null,
    avg:vs.length?Math.round(vs.reduce((s,v)=>s+v,0)/vs.length):null,
    items:vis.slice().sort((a,b)=>b.value-a.value).slice(0,300)});}
  // 줌별 그리드 클러스터(줌인하면 개별 마커)
  const cell=z>=14?0:(z>=13?0.01:z>=12?0.02:z>=11?0.04:0.08);
  let items;
  if(!cell){items=vis.map(m=>({t:"s",...m}));}
  else{const cells={}; vis.forEach(m=>{const k=Math.floor(m.lat/cell)+":"+Math.floor(m.lng/cell);(cells[k]||(cells[k]=[])).push(m);});
   items=Object.values(cells).map(arr=>{ if(arr.length===1)return {t:"s",...arr[0]};
    const la=arr.reduce((s,m)=>s+m.lat,0)/arr.length, ln=arr.reduce((s,m)=>s+m.lng,0)/arr.length;
    const vs=arr.map(m=>m.value).sort((a,b)=>a-b);
    const as=arr.map(m=>m.median_amount).filter(x=>x!=null).sort((a,b)=>a-b);
    return {t:"c",lat:la,lng:ln,count:arr.length,value:vs[Math.floor(vs.length/2)],amt:as.length?as[Math.floor(as.length/2)]:null};});}
  markerObjs.current.forEach(mk=>mk.setMap(null)); markerObjs.current=[];
  items.forEach(it=>{
   const html=it.t==="c"
    ?`<div style="transform:translate(-50%,-50%);display:flex;flex-direction:column;align-items:center;justify-content:center;min-width:46px;height:46px;background:rgba(15,118,110,.96);color:#fff;border-radius:50%;border:2.5px solid #fff;box-shadow:0 3px 9px rgba(0,0,0,.32);text-align:center"><div style="font-weight:800;font-size:13.5px;line-height:1">${it.count}</div><div style="font-size:8.5px;opacity:.92;line-height:1.25;font-weight:700">${mlabel(it)}</div></div>`
    :`<div style="transform:translate(-50%,-100%);position:relative;filter:drop-shadow(0 2px 4px rgba(0,0,0,.3))"><div style="background:${colorFor(it.value)};color:#fff;font-weight:800;font-size:11.5px;line-height:1;padding:6px 10px;border-radius:13px;white-space:nowrap;border:1.5px solid #fff">${mlabel(it)}</div><div style="position:absolute;left:50%;bottom:-4px;width:9px;height:9px;background:${colorFor(it.value)};border-right:1.5px solid #fff;border-bottom:1.5px solid #fff;transform:translateX(-50%) rotate(45deg)"></div></div>`;
   const mk=new n.maps.Marker({position:new n.maps.LatLng(it.lat,it.lng),map,icon:{content:html,anchor:new n.maps.Point(0,0)}});
   n.maps.Event.addListener(mk,"click",()=>{
    if(it.t==="c"){map.setZoom(Math.min(map.getZoom()+2,16));map.panTo(new n.maps.LatLng(it.lat,it.lng));}
    else onOpenComplex&&onOpenComplex({complex_name:it.complex_name,lawd_cd:it.lawd_cd,property_type:it.property_type});
   });
   markerObjs.current.push(mk);
  });
 },[ready,tick,markers,fitKey]);
 // 시설(POI) 레이어 — 확대(zoom≥15) + 선택 카테고리일 때 현재 화면 범위의 시설을 표출.
 // 데이터가 없으면 아무것도 안 뜸(구조만 존재 → 시설 데이터 적재 시 자동 작동).
 useEffect(()=>{
  if(!ready||!mapObj.current||!window.naver)return;
  const n=window.naver, map=mapObj.current;
  const clearPoi=()=>{poiObjs.current.forEach(mk=>{try{mk.setMap(null);}catch(e){}});poiObjs.current=[];};
  if(!poiCats||!poiCats.length||map.getZoom()<15){clearPoi();return;}
  let alive=true;
  const b=map.getBounds(); if(!b)return;
  const sw=b.getSW?b.getSW():(b.getMin&&b.getMin()), ne=b.getNE?b.getNE():(b.getMax&&b.getMax());
  if(!sw||!ne)return;
  const url=`${API}/places/map?min_lat=${sw.lat()}&max_lat=${ne.lat()}&min_lng=${sw.lng()}&max_lng=${ne.lng()}&categories=${poiCats.join(",")}`;
  fetch(url).then(r=>r.json()).then(j=>{ if(!alive)return; clearPoi();
   (j.places||[]).slice(0,200).forEach(p=>{ if(p.lat==null||p.lng==null)return;
    const meta=POI_META[p.category]||{c:"#69737D",e:"📍"};
    const html=`<div style="transform:translate(-50%,-100%);display:flex;align-items:center;gap:3px;background:var(--surface-solid,#fff);border:1.5px solid ${meta.c};border-radius:12px;padding:2px 7px 2px 5px;box-shadow:0 1px 4px rgba(0,0,0,.22);white-space:nowrap"><span style="font-size:10px">${meta.e}</span><span style="font-size:10px;font-weight:700;color:${meta.c};max-width:88px;overflow:hidden;text-overflow:ellipsis">${p.name}</span></div>`;
    const mk=new n.maps.Marker({position:new n.maps.LatLng(p.lat,p.lng),map,icon:{content:html,anchor:new n.maps.Point(0,0)},zIndex:40});
    poiObjs.current.push(mk);
   });
  }).catch(()=>{});
  return ()=>{alive=false;};
 },[ready,tick,poiCats]);
 // 개발 호재(Landmark) 핀 — 토글 시 좌표 있는 호재를 지도에 표시(줌 무관). 클릭 시 요약·출처.
 useEffect(()=>{
  if(!ready||!mapObj.current||!window.naver)return;
  const n=window.naver, map=mapObj.current;
  const clearLm=()=>{lmObjs.current.forEach(mk=>{try{mk.setMap(null);}catch(e){}});lmObjs.current=[];};
  if(!showLm){clearLm();return;}
  let alive=true;
  fetch(`${API}/landmarks`).then(r=>r.json()).then(list=>{ if(!alive)return; clearLm();
   (Array.isArray(list)?list:[]).forEach(L=>{ if(L.lat==null||L.lng==null)return;
    const sc=L.status==="confirmed"?"#0E7C71":L.status==="ongoing"?"#C77A1A":"#69737D";
    const html=`<div style="transform:translate(-50%,-100%);display:flex;align-items:center;gap:3px;background:${sc};color:#fff;border:2px solid #fff;border-radius:13px;padding:3px 9px;box-shadow:0 2px 7px rgba(0,0,0,.32);white-space:nowrap;font-weight:800;font-size:11px">🏗 ${L.name}</div>`;
    const mk=new n.maps.Marker({position:new n.maps.LatLng(L.lat,L.lng),map,icon:{content:html,anchor:new n.maps.Point(0,0)},zIndex:100});
    n.maps.Event.addListener(mk,"click",()=>{try{new n.maps.InfoWindow({content:`<div style="padding:9px 12px;max-width:240px;font-size:12px;line-height:1.55"><b>${L.name}</b><br/>${L.summary||""}${L.source_name?`<br/><span style='color:#888'>출처: ${L.source_name}</span>`:""}</div>`,borderWidth:0}).open(map,mk);}catch(e){}});
    lmObjs.current.push(mk);
   });
  }).catch(()=>{});
  return ()=>{alive=false;};
 },[ready,showLm]);
 // 📉 급매(중앙값 대비 크게 낮은 실거래) 핀 — '판단이 얹힌 지도'의 핵심 시그널. 사실+고지(왜곡 없음).
 useEffect(()=>{
  if(!ready||!mapObj.current||!window.naver)return;
  const n=window.naver, map=mapObj.current;
  const clearBg=()=>{bgObjs.current.forEach(mk=>{try{mk.setMap(null);}catch(e){}});bgObjs.current=[];};
  if(!showBg){clearBg();return;}
  let alive=true;
  fetch(`${API}/pricecheck/bargains`).then(r=>r.json()).then(j=>{ if(!alive)return; clearBg();
   ((j&&j.items)||[]).forEach(B=>{ if(B.lat==null||B.lng==null)return;
    const html=`<div style="transform:translate(-50%,-100%);display:flex;align-items:center;gap:3px;background:#1E5FC4;color:#fff;border:2px solid #fff;border-radius:13px;padding:3px 9px;box-shadow:0 2px 7px rgba(0,0,0,.32);white-space:nowrap;font-weight:800;font-size:11px">📉 ${B.diff_pct}%</div>`;
    const mk=new n.maps.Marker({position:new n.maps.LatLng(B.lat,B.lng),map,icon:{content:html,anchor:new n.maps.Point(0,0)},zIndex:110});
    n.maps.Event.addListener(mk,"click",()=>{ onOpenComplex&&onOpenComplex({complex_name:B.name,lawd_cd:B.lawd_cd,property_type:"apartment",gu:B.gu}); });
    bgObjs.current.push(mk);
   });
  }).catch(()=>{});
  return ()=>{alive=false;};
 },[ready,showBg]);
 useEffect(()=>{ if(ready&&mapObj.current&&onMapReady)onMapReady(mapObj.current); },[ready]);
 if(!mapCfg.enabled)return <Notice>지도를 보려면 서버 <b>.env</b> 에 <b>NAVER_MAP_CLIENT_ID</b> 를 넣고 새로고침하세요. (네이버 클라우드 플랫폼 Maps의 Client ID)</Notice>;
 if(err)return <Notice>네이버 지도 인증에 실패했습니다. 클라이언트 ID와 ‘Web 서비스 URL(도메인)’ 등록을 확인하세요.</Notice>;
 return <div ref={ref} style={{width:"100%",height:full?"calc(100dvh - 108px)":"62vh",minHeight:full?400:undefined,borderRadius:full?0:14,overflow:"hidden",background:"var(--chip)"}}/>;
}
function AreaListSheet({items,deal,onClose,onOpenComplex,inCompare,onToggleCompare}){
 const [sort,setSort]=useState("price");
 const arr=(items||[]).slice().sort((a,b)=>sort==="price"?b.value-a.value:(a.complex_name||"").localeCompare(b.complex_name||""));
 const fmt=(v)=>deal==="trade"?`${Number(v).toLocaleString()}만원/평`:eok(v);
 return (<Sheet title={`이 영역 단지 ${arr.length}곳`} fill onClose={onClose} info="지도에 보이는 영역의 단지입니다. 비교에 담아 나란히 볼 수 있어요.">
  <div style={{display:"flex",gap:6,marginBottom:8}}>
   {[["price","가격순"],["name","이름순"]].map(([k,l])=><button key={k} onClick={()=>setSort(k)} style={{border:"none",cursor:"pointer",fontWeight:700,fontSize:12,padding:"6px 11px",borderRadius:8,background:sort===k?TEAL:"var(--surface-2)",color:sort===k?"#fff":MUTED}}>{l}</button>)}
  </div>
  {arr.length?<MoreList items={arr} initial={12} step={12} render={(m,i)=>{
   const cur=inCompare&&inCompare({complex_name:m.complex_name,lawd_cd:m.lawd_cd,property_type:m.property_type});
   return (<div key={i} className="txrow" style={{display:"flex",alignItems:"center",gap:10}}>
     <div style={{flex:1,minWidth:0,cursor:"pointer"}} role="button" tabIndex={0} onKeyDown={onEnter(()=>onOpenComplex&&onOpenComplex(m))} onClick={()=>onOpenComplex&&onOpenComplex(m)}>
      <div style={{fontWeight:700,fontSize:13.5,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{m.complex_name}</div>
      <div style={{fontSize:11.5,color:MUTED,marginTop:1}}>{m.gu||""}{m.dong?` ${m.dong}`:""} · {m.count}건</div>
     </div>
     <div style={{fontWeight:800,fontSize:13,color:TEAL,flex:"none"}}>{fmt(m.value)}</div>
     <button onClick={()=>onToggleCompare&&onToggleCompare(m)} aria-label="비교 담기" style={{flex:"none",border:"1px solid "+(cur?TEAL:"var(--line)"),background:cur?"rgba(15,118,110,.1)":"var(--surface-solid)",color:cur?TEAL:MUTED,fontWeight:700,fontSize:12.5,padding:"6px 10px",borderRadius:8,cursor:"pointer"}}>{cur?"✓":"⊕"}</button>
    </div>);
  }}/>:<div style={{padding:"30px 0",textAlign:"center",color:MUTED,fontSize:13}}>이 영역에 표시할 단지가 없습니다. 지도를 이동하거나 확대해 보세요.</div>}
  <div style={{fontSize:11,color:MUTED,marginTop:10,lineHeight:1.6}}>{deal==="trade"?"평단가(만원/평)":"보증금"} 중앙값 기준 · 비교 최대 4개 · 신고 지연·정정·해제로 값이 바뀔 수 있는 참고용.</div>
 </Sheet>);
}
function MapHub({mapCfg, onOpenComplex, inCompare, onToggleCompare}){
 const [deal,setDeal]=useState("trade");
 const [prop,setProp]=useState("apartment");
 const [poiCats,setPoiCats]=useState([]);   // 주변시설 레이어(education/sports/living) — 확대 시 표출
 const togglePoi=(k)=>setPoiCats(cs=>cs.includes(k)?cs.filter(x=>x!==k):[...cs,k]);
 const [showLm,setShowLm]=useState(false);   // 개발 호재 핀 표시
 const [showBg,setShowBg]=useState(false);   // 📉 급매(낮은가격 거래) 핀
 const mapRef=useRef(null);                  // 현위치 이동용 지도 인스턴스
 const [locBusy,setLocBusy]=useState(false);
 const goMyLoc=()=>{ if(!navigator.geolocation||!mapRef.current||!window.naver){alert("현재 위치를 사용할 수 없어요. 위치 권한을 확인해주세요.");return;}
  setLocBusy(true);
  navigator.geolocation.getCurrentPosition(pos=>{ setLocBusy(false);
   try{const ll=new window.naver.maps.LatLng(pos.coords.latitude,pos.coords.longitude);
    mapRef.current.setCenter(ll); mapRef.current.setZoom(15);
   }catch(e){}
  },()=>{setLocBusy(false);alert("위치를 가져오지 못했어요. 브라우저 위치 권한을 허용해주세요.");},{timeout:8000});
 };
 const [data,setData]=useState(null);
 const [loading,setLoading]=useState(true);
 const [viewport,setViewport]=useState(null);
 const [listOpen,setListOpen]=useState(false);
 useEffect(()=>{ let alive=true; setLoading(true); setViewport(null);
  fetch(`${API}/map/markers?deal_type=${deal}&property_type=${prop}`).then(r=>r.json())
   .then(j=>{if(alive)setData(j);}).catch(()=>{if(alive)setData({markers:[],bands:[]});}).finally(()=>{if(alive)setLoading(false);});
  return ()=>{alive=false;};
 },[deal,prop]);
 const DEALS=[["trade","매매"],["jeonse","전세"],["wolse","월세"]];
 const PROPS=[["apartment","아파트"],["officetel","오피스텔"],["rowhouse","빌라"]];
 const chip=(active)=>({border:"none",cursor:"pointer",fontWeight:active?800:600,fontSize:12.5,padding:"7px 13px",borderRadius:9,background:active?"var(--surface-solid)":"transparent",color:active?INK:MUTED,boxShadow:active?"0 1px 3px rgba(30,64,90,.14)":"none"});
 const markers=(data&&data.markers)||[];
 const bands=(data&&data.bands)||[];
 const gsum=(data&&data.summary)||null;
 const fmtV=(v)=>v==null?"—":(deal==="trade"?`${Number(v).toLocaleString()}만원/평`:eok(v));
 const vc=viewport?viewport.count:(gsum?gsum.count:markers.length);
 const vm=viewport?viewport.median:(gsum?gsum.median:null);
 return (<div style={{margin:"0 -16px -96px",position:"relative"}}>
  <PriceMarkerMap markers={markers} bands={bands} deal={deal} fitKey={`${deal}:${prop}`} mapCfg={mapCfg} onOpenComplex={onOpenComplex} onViewport={setViewport} poiCats={poiCats} showLm={showLm} showBg={showBg} onMapReady={m=>{mapRef.current=m;}} full={true}/>
  {/* 상단 오버레이: 필터(가로 스크롤) */}
  <div style={{position:"absolute",top:8,left:0,right:0,zIndex:6,display:"flex",flexDirection:"column",gap:6,padding:"0 10px",pointerEvents:"none"}}>
   <div style={{display:"flex",overflowX:"auto",pointerEvents:"auto"}}>
    <div style={{display:"flex",alignItems:"center",gap:5,background:"var(--surface-solid)",borderRadius:11,padding:5,boxShadow:"0 2px 10px rgba(16,24,32,.16)",flex:"none"}}>
     {DEALS.map(([k,l])=><button key={k} onClick={()=>setDeal(k)} style={chip(deal===k)}>{l}</button>)}
     <span style={{width:1,height:16,background:"var(--line)",margin:"0 2px",flex:"none"}}/>
     {PROPS.map(([k,l])=><button key={k} onClick={()=>setProp(k)} style={chip(prop===k)}>{l}</button>)}
    </div>
   </div>
   <div style={{display:"flex",overflowX:"auto",pointerEvents:"auto"}}>
    <div style={{display:"flex",alignItems:"center",gap:5,background:"var(--surface-solid)",borderRadius:11,padding:5,boxShadow:"0 2px 10px rgba(16,24,32,.16)",flex:"none"}}>
     {[["education","🎓 학원"],["sports","🏃 체육"],["living","🏪 생활"]].map(([k,l])=><button key={k} onClick={()=>togglePoi(k)} style={{...chip(poiCats.includes(k)),fontSize:12}}>{l}</button>)}
     <span style={{width:1,height:16,background:"var(--line)",margin:"0 2px",flex:"none"}}/>
     <button onClick={()=>setShowLm(v=>!v)} style={{...chip(showLm),fontSize:12}}>🏗 호재</button>
     <button onClick={()=>setShowBg(v=>!v)} style={{...chip(showBg),fontSize:12}} title="같은 평형 중앙값 대비 크게 낮게 신고된 실거래(사유 있을 수 있음)">📉 급매</button>
    </div>
   </div>
  </div>
  <button onClick={goMyLoc} aria-label="현재 위치로" style={{position:"absolute",right:12,bottom:86,zIndex:6,width:44,height:44,borderRadius:22,border:"1px solid var(--line)",background:"var(--surface-solid)",boxShadow:"0 3px 12px rgba(16,24,32,.22)",cursor:"pointer",fontSize:19,display:"flex",alignItems:"center",justifyContent:"center"}}>{locBusy?"…":"📍"}</button>
  {/* 하단 오버레이: 이 지역 요약 */}
  <div style={{position:"absolute",left:10,right:10,bottom:20,zIndex:6}}>
   <div style={{display:"flex",alignItems:"center",gap:9,background:"var(--surface-solid)",borderRadius:12,padding:"10px 13px",boxShadow:"0 3px 14px rgba(16,24,32,.2)"}}>
    <span style={{fontSize:12,color:MUTED,fontWeight:700}}>이 지역</span>
    <span style={{fontWeight:800,fontSize:14.5}}>{vc}곳</span>
    <span style={{marginLeft:"auto",fontSize:12,color:MUTED}}>{deal==="trade"?"평단가":"보증금"} 중앙값</span>
    <span style={{fontWeight:800,fontSize:14.5,color:TEAL}}>{fmtV(vm)}</span>
    <button onClick={()=>setListOpen(true)} style={{flex:"none",marginLeft:4,border:"none",background:TEAL,color:"#fff",fontWeight:800,fontSize:12,padding:"7px 13px",borderRadius:9,cursor:"pointer"}}>목록</button>
   </div>
  </div>
  {listOpen&&<AreaListSheet items={viewport&&viewport.items?viewport.items:markers} deal={deal} onClose={()=>setListOpen(false)} onOpenComplex={(m)=>{setListOpen(false);onOpenComplex&&onOpenComplex(m);}} inCompare={inCompare} onToggleCompare={onToggleCompare}/>}
 </div>);
}
function RankMap({items,mapCfg}){
 const {ready,err}=useNaver(mapCfg.key,mapCfg.enabled);
 const ref=React.useRef(null);
 const pts=(items||[]).filter(i=>i.lat&&i.lng);
 const sig=pts.map(i=>`${i.rank}:${i.lat},${i.lng}`).join("|");
 useEffect(()=>{
  if(!ready||!ref.current||!window.naver)return;
  const n=window.naver;
  const center=pts.length?new n.maps.LatLng(pts[0].lat,pts[0].lng):new n.maps.LatLng(36.6424,127.489);
  const map=new n.maps.Map(ref.current,{center,zoom:pts.length?13:11});
  pts.forEach(it=>{const pos=new n.maps.LatLng(it.lat,it.lng);
   const mk=new n.maps.Marker({position:pos,map});
   const iw=new n.maps.InfoWindow({content:`<div style="padding:7px 10px;font-size:12px;white-space:nowrap;font-weight:600">#${it.rank} ${it.complex_name||"단지"}<br/><span style="color:#1A2128">${eok(it.deal_amount)}</span></div>`,borderWidth:0});
   n.maps.Event.addListener(mk,"click",()=>iw.open(map,mk));});
 },[ready,sig]);
 if(!mapCfg.enabled)return <Notice>지도를 보려면 서버 <b>.env</b> 에 <b>NAVER_MAP_CLIENT_ID</b> 를 넣고 새로고침하세요. (네이버 클라우드 플랫폼 Maps의 Client ID)</Notice>;
 if(err)return <Notice>네이버 지도 인증에 실패했습니다. 클라이언트 ID와 ‘Web 서비스 URL(도메인)’ 등록을 확인하세요.</Notice>;
 return (<div>
  <div ref={ref} style={{width:"100%",height:300,borderRadius:14,overflow:"hidden",background:"var(--chip)"}}/>
  {ready&&!pts.length&&<div style={{marginTop:8}}><Notice>이 목록의 단지 좌표가 아직 없습니다. 서버에서 <b>python -m scripts.geocode</b> 실행 후 새로고침하세요. (매매가·평단가 순위에서 표시됩니다)</Notice></div>}
  {!ready&&!err&&<div style={{padding:10}}><Skeleton h={180} r={12}/></div>}
 </div>);
}

/* ---------------- 평단가 히트맵 지도 ---------------- */
function ppColor(v,min,max){const t=(max>min)?(v-min)/(max-min):0.5;const h=220-t*220;return `hsl(${h},75%,48%)`;}
function HeatMap({data,mapCfg,onOpen,onGu,level}){
 const {ready,err}=useNaver(mapCfg.key,mapCfg.enabled);
 const ref=React.useRef(null);
 const [sel,setSel]=useState(null);
 const isDist=level==="district";
 const src=isDist?(data.districts||[]):(data.points||[]).filter(p=>p.lat&&p.lng);
 const mn=isDist?data.district_min:data.min_pyeong, mx=isDist?data.district_max:data.max_pyeong;
 const sig=(isDist?"d:":"c:")+src.map(p=>`${p.lat},${p.lng},${p.median_pyeong}`).join("|");
 useEffect(()=>{
  if(!ready||!ref.current||!window.naver)return;
  const n=window.naver;
  setSel(null);
  const center=src.length?new n.maps.LatLng(src[0].lat,src[0].lng):new n.maps.LatLng(36.6424,127.489);
  const map=new n.maps.Map(ref.current,{center,zoom:isDist?11:12});
  src.forEach(p=>{const color=ppColor(p.median_pyeong,mn,mx);
   const label=isDist?`${(p.gu||"").replace("청주시 ","").replace("구","")} ${p.median_pyeong.toLocaleString()}`:p.median_pyeong.toLocaleString();
   const mk=new n.maps.Marker({position:new n.maps.LatLng(p.lat,p.lng),map,
    icon:{content:`<div style="transform:translate(-50%,-50%);background:${color};color:#fff;font-size:${isDist?12:11}px;font-weight:800;padding:${isDist?"5px 10px":"3px 7px"};border-radius:13px;box-shadow:0 1px 5px rgba(0,0,0,.4);white-space:nowrap;cursor:pointer">${label}</div>`,
      anchor:new n.maps.Point(0,0)}});
   n.maps.Event.addListener(mk,"click",()=>{ if(isDist){onGu&&onGu(p.gu);} else {setSel(p);} });});
 },[ready,sig]);
 if(!mapCfg.enabled)return <Notice>지도를 보려면 서버 <b>.env</b> 에 <b>NAVER_MAP_CLIENT_ID</b> 설정 후 새로고침하세요.</Notice>;
 if(err)return <Notice>네이버 지도 인증 실패 — 클라이언트 ID/도메인을 확인하세요.</Notice>;
 return (<div>
  <div style={{position:"relative"}}>
   <div ref={ref} style={{width:"100%",height:380,borderRadius:14,overflow:"hidden",background:"var(--chip)"}}/>
   {sel&&<div style={{position:"absolute",left:10,right:10,bottom:10,background:"var(--surface-solid)",borderRadius:13,boxShadow:"0 5px 20px rgba(20,40,60,.22)",padding:"12px 14px",zIndex:5}}>
    <div style={{display:"flex",alignItems:"flex-start",gap:8}}>
     <div style={{minWidth:0,flex:1}}>
      <div style={{fontWeight:800,fontSize:14,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{sel.complex_name} {sel.is_sample&&<ExBadge/>}</div>
      <div style={{fontSize:12,color:MUTED,marginTop:2}}>{[(sel.gu||"").replace("청주시 ",""),sel.dong].filter(Boolean).join(" · ")}{sel.count?` · ${sel.count}건`:""}</div>
     </div>
     <span onClick={()=>setSel(null)} aria-label="닫기" role="button" tabIndex={0} onKeyDown={onEnter(()=>setSel(null))} style={{cursor:"pointer",color:MUTED,fontWeight:700,fontSize:17,flex:"none",lineHeight:1}}>×</span>
    </div>
    <div style={{display:"flex",alignItems:"center",gap:10,marginTop:9}}>
     <div className="num" style={{fontWeight:800,fontSize:16}}>{sel.median_pyeong!=null?sel.median_pyeong.toLocaleString("ko-KR"):"—"} <span style={{fontSize:11,color:MUTED,fontWeight:600}}>만원/평</span></div>
     <button onClick={()=>onOpen&&onOpen(sel)} style={{marginLeft:"auto",border:"none",background:TEAL,color:"#fff",fontWeight:700,fontSize:12.5,borderRadius:9,padding:"8px 15px",cursor:"pointer"}}>단지 상세 보기 →</button>
    </div>
   </div>}
  </div>
  {ready&&!src.length&&<div style={{marginTop:8}}><Notice>표시할 거래 데이터가 없습니다.</Notice></div>}
  {ready&&isDist&&src.length>0&&<div style={{marginTop:8,fontSize:11.5,color:MUTED}}>구 평균(대표 위치) 기준입니다. 단지별 정밀 위치는 ‘단지 단위’ 전환 시 표시되며, 서버에서 <b>python -m scripts.geocode</b> 실행이 필요합니다.</div>}
  {ready&&!isDist&&!src.length&&<div style={{marginTop:8}}><Notice>단지 좌표가 아직 없습니다. 서버에서 <b>python -m scripts.geocode</b> 실행 후 새로고침하거나, 위 ‘구 단위’로 보세요.</Notice></div>}
  {!ready&&!err&&<div style={{padding:10}}><Skeleton h={180} r={12}/></div>}
 </div>);
}
function HeatTab({ptype,mapCfg,onOpen,onGu}){
 const type=(ptype&&ptype!=="전체")?ptype:"apartment";
 const [level,setLevel]=useState("district");
 const [hm,setHm]=useState(null);
 useEffect(()=>{let on=true;setHm(null);
  fetch(`${API}/dashboard/heatmap?property_type=${type}`).then(r=>r.json()).then(j=>{if(on)setHm(j);}).catch(()=>{if(on)setHm(demoHeatmap(type));});
  return ()=>{on=false;};},[type]);
 const isDist=level==="district";
 return (<div style={{marginTop:6}}>
  <div style={{display:"flex",alignItems:"center",gap:8}}>
   <span style={{fontSize:12.5,color:MUTED}}>{TYPE_LABEL[type]||"아파트"} 시세 히트맵</span>
   <div style={{marginLeft:"auto",display:"flex",gap:6}}>
    <button className={"tog "+(isDist?"on":"")} onClick={()=>setLevel("district")}>구 단위</button>
    <button className={"tog "+(!isDist?"on":"")} onClick={()=>setLevel("complex")}>단지 단위</button>
   </div>
  </div>
  <div className="card" style={{padding:14,marginTop:10}}>
   {!hm?<div style={{marginTop:10}}><SkeletonCard/><SkeletonCard/></div>:<HeatMap data={hm} mapCfg={mapCfg} onOpen={onOpen} onGu={onGu} level={level}/>}
   <div style={{display:"flex",alignItems:"center",gap:8,marginTop:12,fontSize:12,color:MUTED}}>
    <span>낮음</span>
    <div style={{flex:1,height:10,borderRadius:5,background:"linear-gradient(90deg,hsl(220,75%,48%),hsl(120,75%,48%),hsl(0,75%,48%))"}}/>
    <span>높음 (만원/평)</span>
   </div>
   {hm&&(isDist?(hm.district_min!=null&&<div className="num" style={{fontSize:11.5,color:MUTED,marginTop:4}}>{hm.district_min.toLocaleString()} ~ {hm.district_max.toLocaleString()} 만원/평 · 구 평균 · 핀 클릭 시 구 시세</div>)
    :(hm.min_pyeong!=null&&<div className="num" style={{fontSize:11.5,color:MUTED,marginTop:4}}>{hm.min_pyeong.toLocaleString()} ~ {hm.max_pyeong.toLocaleString()} 만원/평 · {hm.total||0}개 단지 · 핀 클릭 시 단지 상세</div>))}
  </div>
 </div>);
}

/* ---------------- 단지 상세 (M3) ---------------- */
function TrendBlock({ts}){
 // 지침서 2.3: 시세 시계열(1·3·5년·전체 토글) + 거래량 추이 + 전월/전년 등락. 데이터는 timeseries(월별 avg·count) 재사용.
 const full=(ts||[]).filter(t=>t&&t.avg!=null);
 const defRng=full.length>12?"36":"12";
 const [rng,setRng]=useState(defRng);
 if(full.length<2)return null;
 const opts=[["12","1년"],["36","3년"],["60","5년"],["all","전체"]]
   .filter(([k])=>k==="12"||(k==="36"&&full.length>12)||(k==="60"&&full.length>36)||(k==="all"&&full.length>60));
 const view=rng==="all"?full:full.slice(-Number(rng));
 // 전월/전년 등락(전체 이력 기준 — 뷰 필터와 무관하게 정확히)
 const last=full[full.length-1], prev=full[full.length-2];
 const mom=(last&&prev&&prev.avg)?Math.round((last.avg-prev.avg)/prev.avg*1000)/10:null;
 let yoy=null;
 if(last){const [y,m]=last.month.split("-");const tgt=`${Number(y)-1}-${m}`;const past=full.find(t=>t.month===tgt);
  if(past&&past.avg)yoy=Math.round((last.avg-past.avg)/past.avg*1000)/10;}
 // 차트 좌표(가격 라인 + 거래량 막대, X 공유)
 const W=520,L=46,R=10,pT=8,pB=140,vT=152,vB=196,H=212,n=view.length;
 const X=i=>L+(W-L-R)*(n<=1?0.5:i/(n-1));
 const av=view.map(t=>t.avg),mn=Math.min(...av),mx=Math.max(...av),sp=(mx-mn)||1;
 const Y=v=>pT+(pB-pT)*(1-(v-mn)/sp);
 const cmax=Math.max(...view.map(t=>t.count||0),1);
 const bw=Math.max(2,Math.min(14,(W-L-R)/n*0.55));
 const lbEvery=Math.max(1,Math.ceil(n/6));
 return (<div style={{marginTop:12}}>
  <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
   <span style={{fontSize:12,color:MUTED,fontWeight:700}}>매매가·거래량 추이</span>
   <span style={{marginLeft:"auto",display:"flex",gap:4}}>
    {opts.map(([k,l])=><button key={k} onClick={()=>setRng(k)} style={{border:"none",cursor:"pointer",fontSize:11.5,fontWeight:rng===k?800:600,padding:"4px 9px",borderRadius:8,background:rng===k?"var(--surface-solid)":"transparent",color:rng===k?INK:MUTED,boxShadow:rng===k?"0 1px 3px rgba(30,64,90,.14)":"none"}}>{l}</button>)}
   </span>
  </div>
  {(mom!=null||yoy!=null)&&<div style={{display:"flex",gap:12,margin:"7px 0 2px",fontSize:12.5}}>
   {mom!=null&&<span>전월 대비 <Delta v={mom}/></span>}
   {yoy!=null&&<span>전년 동월 대비 <Delta v={yoy}/></span>}
  </div>}
  <svg viewBox={`0 0 ${W} ${H}`} style={{width:"100%",height:220}}>
   {[mn,mn+sp/2,mx].map((t,i)=>(<g key={i}><line x1={L} x2={W-R} y1={Y(t)} y2={Y(t)} stroke="var(--line)"/>
     <text x="0" y={Y(t)+3} fontSize="10" fill={MUTED}>{(t/10000).toFixed(2)}억</text></g>))}
   <polyline fill="none" stroke={TEAL} strokeWidth="2.4" points={view.map((t,i)=>`${X(i)},${Y(t.avg)}`).join(" ")}/>
   {n<=24&&view.map((t,i)=><circle key={i} cx={X(i)} cy={Y(t.avg)} r="2.6" fill={TEAL}/>)}
   {view.map((t,i)=>{const h=(t.count||0)/cmax*(vB-vT);return <rect key={i} x={X(i)-bw/2} y={vB-h} width={bw} height={Math.max(h,(t.count||0)>0?2:0)} rx="1.5" fill={TEAL} opacity="0.42"/>;})}
   <text x="0" y={vT+8} fontSize="10" fill={MUTED}>거래량</text>
   {view.map((t,i)=>i%lbEvery===0?<text key={i} x={X(i)} y={H-3} fontSize="10" fill={MUTED} textAnchor="middle">{t.month.slice(2).replace("-",".")}</text>:null)}
  </svg>
  <div style={{fontSize:10.5,color:MUTED,marginTop:2}}>월평균 매매가(거래 있던 달 기준)·월 거래건수. 표본이 적은 달은 변동이 커 보일 수 있어요.</div>
 </div>);
}
function DetailLine({months,values}){
 const W=520,H=180,L=46,R=10,T=10,B=22;
 const all=values.filter(v=>v!=null);
 if(all.length<2)return <div style={{color:MUTED,fontSize:13,padding:14}}>추이를 그릴 데이터가 부족합니다(2개월 이상 거래 필요).</div>;
 const min=Math.min(...all),max=Math.max(...all),span=(max-min)||1;
 const X=i=>L+(W-L-R)*(months.length<=1?0.5:i/(months.length-1)),Y=v=>T+(H-T-B)*(1-(v-min)/span);
 const pts=values.map((v,i)=>v==null?null:[X(i),Y(v)]).filter(Boolean);
 return (<svg viewBox={`0 0 ${W} ${H}`} style={{width:"100%",height:180}}>
  {[min,min+span/2,max].map((t,i)=>(<g key={i}><line x1={L} x2={W-R} y1={Y(t)} y2={Y(t)} stroke="#EEF1F1"/>
    <text x="0" y={Y(t)+3} fontSize="10" fill={MUTED}>{(t/10000).toFixed(2)}억</text></g>))}
  {months.map((m,i)=>(<text key={i} x={X(i)} y={H-6} fontSize="10" fill={MUTED} textAnchor="middle">{m}</text>))}
  <polyline fill="none" stroke={TEAL} strokeWidth="2.4" points={pts.map(p=>p.join(",")).join(" ")}/>
  {pts.map((p,i)=><circle key={i} cx={p[0]} cy={p[1]} r="3" fill={TEAL}/>)}
 </svg>);
}
const GU_COLORS={"상당구":"#3B6FE0","서원구":"#F08A24","흥덕구":"#18A957","청원구":"#9B59B6"};
const guColor=name=>GU_COLORS[(name||"").replace("청주시 ","")]||TEAL;
function MultiLine({months,series}){
 const W=520,H=200,L=46,R=10,T=10,B=22;
 const all=series.flatMap(s=>(s.values||[]).filter(v=>v!=null));
 if(all.length<2)return <div style={{color:MUTED,fontSize:13,padding:14}}>추이를 그릴 데이터가 부족합니다.</div>;
 const min=Math.min(...all),max=Math.max(...all),span=(max-min)||1;
 const n=months.length;
 const X=i=>L+(W-L-R)*(n<=1?0.5:i/(n-1)),Y=v=>T+(H-T-B)*(1-(v-min)/span);
 return (<div>
  <svg viewBox={`0 0 ${W} ${H}`} style={{width:"100%",height:200}}>
   {[min,min+span/2,max].map((t,i)=>(<g key={i}><line x1={L} x2={W-R} y1={Y(t)} y2={Y(t)} stroke="#EEF1F1"/>
     <text x="0" y={Y(t)+3} fontSize="10" fill={MUTED}>{(t/10000).toFixed(2)}억</text></g>))}
   {months.map((m,i)=>((n<=6||i%2===0)?<text key={i} x={X(i)} y={H-6} fontSize="9.5" fill={MUTED} textAnchor="middle">{m.slice(2)}</text>:null))}
   {series.map((s,si)=>{const col=guColor(s.name);
    const segs=[];let cur=[];
    (s.values||[]).forEach((v,i)=>{if(v==null){if(cur.length>1)segs.push(cur);cur=[];}else cur.push([X(i),Y(v)]);});
    if(cur.length>1)segs.push(cur);
    return <g key={si}>
     {segs.map((seg,k)=><polyline key={k} fill="none" stroke={col} strokeWidth="2.4" points={seg.map(p=>p.join(",")).join(" ")}/>)}
     {(s.values||[]).map((v,i)=>v==null?null:<circle key={i} cx={X(i)} cy={Y(v)} r="2.6" fill={col}/>)}
    </g>;})}
  </svg>
  <div style={{display:"flex",flexWrap:"wrap",gap:"6px 14px",marginTop:6}}>
   {series.map((s,i)=>(<span key={i} style={{display:"inline-flex",alignItems:"center",gap:5,fontSize:12,fontWeight:600}}>
    <span style={{width:11,height:11,borderRadius:3,background:guColor(s.name)}}/>{(s.name||"").replace("청주시 ","")}</span>))}
  </div>
 </div>);
}
function demoDetail(sel){
 const _all=DEMO_TX.filter(t=>t.complex_name===sel.name&&t.lawd_cd===sel.lawd_cd);
 const rows=_all.filter(t=>!t.is_canceled);
 const canceled_count=_all.filter(t=>t.is_canceled).length;
 const _rel=n=>n<3?"low":n<7?"fair":"ok";
 const _flag=(r,ref)=>({corrected:!!r.corrected_at,direct:r.trade_method==="direct",outlier:!!(r.deal_type==="trade"&&ref&&r.deal_amount&&r.exclusive_area&&Math.abs(Math.round(r.deal_amount/(r.exclusive_area/PY))-ref)/ref>0.30)});
 const trades=rows.filter(t=>t.deal_type==="trade"&&t.deal_amount);
 const mon={}; trades.forEach(t=>{const k=(t.contract_date||"").slice(0,7);(mon[k]=mon[k]||[]).push(t.deal_amount);});
 const ts=Object.keys(mon).sort().map(k=>({month:k,avg:Math.round(mon[k].reduce((a,b)=>a+b,0)/mon[k].length),count:mon[k].length}));
 const peak=trades.length?Math.max(...trades.map(t=>t.deal_amount)):null;
 const latestTx=trades.slice().sort((a,b)=>(b.contract_date||"").localeCompare(a.contract_date||""))[0];
 const latest=latestTx?latestTx.deal_amount:null;
 const am={}; trades.forEach(t=>{const a=Math.round(t.exclusive_area*10)/10;(am[a]=am[a]||[]).push(t);});
 const areas=Object.keys(am).map(a=>{
  const rs=am[a];
  const tr2=rs.filter(r=>r.deal_type==="trade"&&r.deal_amount);
  const tamts=tr2.map(r=>r.deal_amount).sort((x,y)=>x-y);
  const med2=tamts.length?tamts[Math.floor(tamts.length/2)]:null;
  const tg=tamts[0]??null,pk=tamts[tamts.length-1]??null;
  const lat2=tr2.length?tr2.slice().sort((x,y)=>(y.contract_date||"").localeCompare(x.contract_date||""))[0].deal_amount:null;
  const jl=rs.filter(r=>r.deal_type==="jeonse"&&r.deposit).map(r=>r.deposit).sort((x,y)=>x-y);
  const jmed=jl.length?jl[Math.floor(jl.length/2)]:null;
  const jr2=(jmed&&med2)?Math.round(jmed/med2*100):null;
  const ppm2=med2?Math.round(med2/(+a/PY)):null;
  const mm={}; tr2.forEach(t=>{const k=(t.contract_date||"").slice(0,7);(mm[k]=mm[k]||[]).push(t.deal_amount);});
  const ts2=Object.keys(mm).sort().map(k=>({month:k,avg:Math.round(mm[k].reduce((p,q)=>p+q,0)/mm[k].length),count:mm[k].length}));
  const rec2=rs.slice().sort((x,y)=>(y.contract_date||"").localeCompare(x.contract_date||"")).slice(0,8)
   .map(r=>({deal_type:r.deal_type,exclusive_area:r.exclusive_area,floor:r.floor,contract_date:r.contract_date,deal_amount:r.deal_amount,deposit:r.deposit,monthly_rent:r.monthly_rent,is_sample:true,..._flag(r,ppm2)}));
  return {area:+a,label:(+a)+"㎡",trade_count:tr2.length,reliability:_rel(tr2.length),latest_amount:lat2,price_median:med2,price_min:tg,price_max:pk,
   from_peak_pct:(pk&&lat2)?Math.round((lat2-pk)/pk*1000)/10:null,
   from_trough_pct:(tg&&lat2)?Math.round((lat2-tg)/tg*1000)/10:null,
   jeonse_ratio:jr2,ppm_median:ppm2,amounts:tr2.map(t=>t.deal_amount).sort((x,y)=>x-y),timeseries:ts2,recent:rec2};
 }).sort((x,y)=>(y.trade_count-x.trade_count)||(x.area-y.area));
 const amts=trades.map(t=>t.deal_amount).sort((x,y)=>x-y);
 const trough=amts.length?amts[0]:null;
 const pmed=amts.length?amts[Math.floor(amts.length/2)]:null;
 const jdep=rows.filter(r=>r.deal_type==="jeonse"&&r.deposit).map(r=>r.deposit).sort((x,y)=>x-y);
 const jmedAll=jdep.length?jdep[Math.floor(jdep.length/2)]:null;
 const jrate=(jmedAll&&pmed)?Math.round(jmedAll/pmed*1000)/10:null;
 const fb=[];
 const areaPpm={}; areas.forEach(a=>{areaPpm[a.area]=a.ppm_median;});
 const recent=rows.slice().sort((x,y)=>(y.contract_date||"").localeCompare(x.contract_date||"")).slice(0,12)
  .map(r=>({deal_type:r.deal_type,exclusive_area:r.exclusive_area,floor:r.floor,contract_date:r.contract_date,deal_amount:r.deal_amount,deposit:r.deposit,monthly_rent:r.monthly_rent,is_sample:true,..._flag(r,areaPpm[Math.round((r.exclusive_area||0)*10)/10])}));
 return {found:rows.length>0,name:sel.name,gu:GU_FULL(sel.lawd_cd),dong:rows[0]?rows[0].dong:null,property_type:sel.property_type,
  build_year:null,lat:null,lng:null,latest_amount:latest,peak_amount:peak,
  from_peak_pct:(peak&&latest)?Math.round((latest-peak)/peak*1000)/10:null,
  trough_amount:trough,from_trough_pct:(trough&&latest)?Math.round((latest-trough)/trough*1000)/10:null,
  price_min:amts[0]??null,price_max:amts[amts.length-1]??null,price_median:pmed,jeonse_ratio:jrate,floor_bands:fb,
  trade_count:trades.length,reliability:_rel(trades.length),canceled_count:canceled_count,timeseries:ts,volume:ts.map(t=>({month:t.month,count:t.count})),areas,recent,
  poi:{"지하철":[{name:"[예시] OO역",distance:520}],"마트":[{name:"[예시] OO마트",distance:340}],"학교":[{name:"[예시] OO초",distance:280}],"병원":[{name:"[예시] OO병원",distance:900}]},
  living_score:{total:90,grade:"최상",radius:1500,categories:[{label:"교통",score:89,count:1,nearest_m:520},{label:"편의",score:98,count:1,nearest_m:340},{label:"학교",score:100,count:1,nearest_m:280},{label:"의료",score:70,count:1,nearest_m:900}]},
  contains_sample_data:true};
}
const DEMO_DESTS=[
 {id:1,key:"osong_ktx",name:"오송역(KTX)",category:"transit",gu:"흥덕구",lat:36.6207,lng:127.3271,has_coord:true},
 {id:2,key:"ochang_complex",name:"오창 과학산업단지",category:"job",gu:"청원구",lat:36.71,lng:127.44,has_coord:true},
 {id:3,key:"city_hall",name:"청주시청",category:"public",gu:"상당구",lat:36.6424,lng:127.489,has_coord:true},
 {id:4,key:"cbnu",name:"충북대학교",category:"education",gu:"서원구",lat:36.6296,lng:127.4565,has_coord:true}];
const DEMO_CX_COORDS={"샘플센트럴파크":[36.638,127.430],"샘플리버뷰":[36.635,127.436],"샘플그린아파트":[36.640,127.500],
 "샘플파크자이":[36.620,127.470],"샘플숲속마을":[36.705,127.490],"샘플테크노폴리스":[36.640,127.440],"샘플빌라":[36.710,127.440]};
function demoCommuteSearch(destId,mode,maxMin,ptype){
 const dest=DEMO_DESTS.find(d=>d.id===destId)||DEMO_DESTS[0];
 const kmh=mode==="transit"?22:38; const seen={}, out=[];
 DEMO_TX.forEach(t=>{ if(t.is_canceled||!t.complex_name||seen[t.complex_name])return;
  if(ptype!=="전체"&&t.property_type!==ptype)return;
  const c=DEMO_CX_COORDS[t.complex_name]; if(!c)return; seen[t.complex_name]=1;
  const dM=havM(c[0],c[1],dest.lat,dest.lng)*1.3, min=Math.max(1,Math.round(dM/1000/kmh*60));
  if(min>maxMin)return;
  const tr=DEMO_TX.filter(x=>x.complex_name===t.complex_name&&x.deal_type==="trade"&&x.deal_amount&&!x.is_canceled).map(x=>x.deal_amount).sort((a,b)=>a-b);
  out.push({complex_id:t.complex_name,name:t.complex_name,lawd_cd:t.lawd_cd,gu:GU_NAME[t.lawd_cd],property_type:t.property_type,
   lat:c[0],lng:c[1],minutes:min,method:"haversine",price:tr.length?tr[Math.floor(tr.length/2)]:null});});
 out.sort((a,b)=>a.minutes-b.minutes);
 return {found:true,destination:{id:dest.id,name:dest.name,category:dest.category},mode,max_minutes:maxMin,
  method_summary:"추정(직선거리)",results:out,count:out.length,is_sample:true};
}
function demoAffordable(cash,income,consent,ptype,lawds){
 const budget=Math.round((+cash||0)/0.30);  // 자기자본 30%(LTV70 가정) → 간이 예산
 const codes=lawds&&lawds.length?new Set(lawds.map(String)):null;
 const seen={},items=[];
 DEMO_TX.forEach(t=>{ if(t.is_canceled||t.deal_type!=="trade"||!t.deal_amount||!t.complex_name||seen[t.complex_name])return;
  if(ptype&&ptype!=="all"&&t.property_type!==ptype)return;
  if(codes&&!codes.has(String(t.lawd_cd)))return;
  const tr=DEMO_TX.filter(x=>x.complex_name===t.complex_name&&x.deal_type==="trade"&&x.deal_amount&&!x.is_canceled).map(x=>x.deal_amount).sort((a,b)=>a-b);
  const med=tr[Math.floor(tr.length/2)]; if(med>budget)return; seen[t.complex_name]=1;
  const loan=Math.min(Math.round(med*0.7),Math.max(0,med-(+cash))), own=med-loan;
  items.push({name:t.complex_name,lawd_cd:t.lawd_cd,gu:GU_NAME[t.lawd_cd],property_type:t.property_type,
   median_price:med,trade_count:tr.length,own_capital:own,loan_needed:loan,monthly_payment:Math.round(_pmt(loan,4.0,30)),contains_sample_data:true});});
 items.sort((a,b)=>b.median_price-a.median_price);
 return {budget_max:budget,mode:(consent&&income)?"personalized":"simple",rate_pct:4.0,years:30,
  count:items.length,items:items.slice(0,8),is_sample:true,
  disclaimer:"미리보기 예시입니다. 실서버에서는 실제 청주 시세로 추천됩니다."};
}
function BackBtn({onBack}){
 return <button onClick={onBack} aria-label="뒤로" style={{position:"fixed",zIndex:60,
   left:"max(16px, calc(50% - 504px))",bottom:76,
   display:"inline-flex",alignItems:"center",gap:5,
   background:"var(--surface-solid)",WebkitBackdropFilter:"blur(8px)",backdropFilter:"blur(8px)",
   border:"1px solid var(--line)",borderRadius:24,boxShadow:"0 6px 20px rgba(30,64,90,.22)",
   color:INK,fontWeight:800,fontSize:14,padding:"10px 16px 10px 12px",cursor:"pointer"}}>
   <span style={{fontSize:19,lineHeight:1,marginTop:-1}}>‹</span>뒤로</button>;
}
function ExternalListings({d}){
 const gu=(d.gu||"").replace("청주시 ","");
 const base=`${d.name} ${gu}`.trim();
 const naverSearch=`https://search.naver.com/search.naver?query=${encodeURIComponent(base+" 매물")}`;
 const naverMap=`https://map.naver.com/p/search/${encodeURIComponent(base)}`;
 return (<div className="card" style={{padding:"14px 15px",marginTop:12}}>
  <div style={{display:"flex",alignItems:"center",gap:6}}>
   <span style={{fontSize:18}}>🏷️</span>
   <span style={{fontWeight:800,fontSize:14.5}}>이 단지 매물 보러가기</span>
   <Info text="실제 매물·호가는 외부 부동산 사이트에서 확인하세요. 본 서비스는 실거래 분석만 제공하며 매물 중개·광고와는 무관합니다."/>
  </div>
  <div style={{fontSize:12,color:MUTED,marginTop:3}}>본 서비스는 실거래 분석 도구예요. 지금 나온 매물은 외부에서 확인하세요.</div>
  <div style={{display:"flex",gap:8,marginTop:11}}>
   <a href={naverSearch} target="_blank" rel="noopener noreferrer" style={{flex:1,textAlign:"center",textDecoration:"none",border:"1px solid "+TEAL,background:"rgba(15,118,110,.08)",color:TEAL,fontWeight:800,fontSize:13,borderRadius:10,padding:"11px 0"}}>네이버 매물 검색 ↗</a>
   <a href={naverMap} target="_blank" rel="noopener noreferrer" style={{flex:1,textAlign:"center",textDecoration:"none",border:"1px solid var(--line)",background:"var(--surface-2)",color:"var(--ink)",fontWeight:800,fontSize:13,borderRadius:10,padding:"11px 0"}}>지도에서 보기 ↗</a>
  </div>
  <div style={{fontSize:10.5,color:MUTED,marginTop:8,lineHeight:1.6}}>※ 외부 사이트로 이동합니다. 매물·호가는 해당 사이트 기준이며 본 서비스와 직접 관련이 없습니다.</div>
 </div>);
}
function LivingScore({data}){
 const gc=data.grade==="아쉬움"?MUTED:data.grade==="보통"?"#9A6B00":TEAL;
 const distM=m=>m==null?"—":(m<1000?m+"m":(m/1000).toFixed(1)+"km");
 const barC=s=>s>=60?TEAL:s>=40?"#9A6B00":"#C8322A";
 return (<div className="card" style={{padding:"15px 16px",marginTop:12}}>
  <div style={{display:"flex",alignItems:"center",gap:6}}>
   <span style={{fontSize:18}}>🧭</span>
   <span style={{fontWeight:800,fontSize:15}}>생활권 점수</span>
   <Info text="단지 반경 1.5km 내 교통(지하철)·편의(마트)·학교·의료(병원)까지의 최단 거리로 매긴 참고 점수입니다. 300m 이내 만점, 1.5km 40점, 반경 내 없으면 0점. 실거주 만족도(소음·평판 등)와 다를 수 있어요. 출처: 카카오 장소."/>
   <span className="num" style={{marginLeft:"auto",fontWeight:800,fontSize:24,color:gc,lineHeight:1}}>{data.total}<span style={{fontSize:13,color:MUTED,fontWeight:700}}>/100</span></span>
   <span className="pill" style={{background:"rgba(15,118,110,.12)",color:gc,fontWeight:800,marginLeft:6}}>{data.grade}</span>
  </div>
  <div style={{marginTop:13,display:"flex",flexDirection:"column",gap:10}}>
   {(data.categories||[]).map((c,i)=>(<div key={i} style={{display:"flex",alignItems:"center",gap:9}}>
    <span style={{width:30,fontSize:12.5,fontWeight:700,flex:"none"}}>{c.label}</span>
    <div style={{flex:1,height:7,borderRadius:4,background:"var(--surface-2)",overflow:"hidden"}}><div style={{width:Math.max(3,c.score)+"%",height:"100%",background:barC(c.score),borderRadius:4}}/></div>
    <span className="num" style={{width:26,textAlign:"right",fontSize:12,fontWeight:700,flex:"none"}}>{c.score}</span>
    <span className="num" style={{width:66,textAlign:"right",fontSize:11,color:MUTED,flex:"none"}}>{c.nearest_m!=null?"최단 "+distM(c.nearest_m):"없음"}</span>
   </div>))}
  </div>
  <div style={{fontSize:10.5,color:MUTED,marginTop:11,lineHeight:1.6}}>※ 반경 1.5km 시설까지 거리 기준 참고치예요. 실제 생활 편의는 노선·시간대·개인 상황에 따라 다릅니다. (출처: 카카오 장소)</div>
 </div>);
}
function VolumeSignal({volume}){
 const v=(volume||[]).filter(x=>x&&x.month);
 if(v.length<2)return null;
 const recent=v.slice(-3), prior=v.slice(-6,-3);
 const rc=recent.reduce((s,x)=>s+(x.count||0),0);
 const pc=prior.reduce((s,x)=>s+(x.count||0),0);
 if(rc+pc<2)return null;
 let label,color,bg,desc,icon;
 if(rc>=2&&rc>=pc*1.3){label="거래 활발";color=TEAL;bg="rgba(15,118,110,.12)";desc="최근 거래가 직전보다 늘었어요";icon="🔥";}
 else if(pc>0&&rc<=pc*0.7){label="거래 한산";color=MUTED;bg="var(--surface-2)";desc="최근 거래가 직전보다 줄었어요";icon="💤";}
 else {label="거래 보통";color=MUTED;bg="var(--surface-2)";desc="거래량이 직전과 비슷해요";icon="≈";}
 return (<div className="card" style={{padding:"12px 14px",marginTop:12,display:"flex",alignItems:"center",gap:10}}>
  <span className="pill" style={{background:bg,color,fontWeight:800,fontSize:12.5,padding:"5px 11px",flex:"none"}}>{icon} {label}</span>
  <div style={{minWidth:0,flex:1}}>
   <div style={{fontSize:12.5,fontWeight:700}}>{desc}</div>
   <div className="num" style={{fontSize:11.5,color:MUTED,marginTop:1}}>최근 3개월 {rc}건 · 직전 3개월 {pc}건</div>
  </div>
  <span style={{flex:"none"}}><Info text="최근 3개월 매매 신고 건수를 직전 3개월과 비교한 거래 동향입니다. 가격만으로는 알기 어려운 ‘거래를 동반한 변화’인지 참고하세요. 표본이 적으면 변동이 크니 참고용입니다."/></span>
 </div>);
}
function FairPriceCheck({a}){
 const [v,setV]=useState("");
 const amts=(a.amounts||[]).filter(x=>x!=null);
 const med=a.price_median, lo=a.price_min, hi=a.price_max;
 if(med==null||!amts.length)return null;
 const price=v===""?null:+v;
 const span=(hi!=null&&lo!=null&&hi>lo)?hi-lo:null;
 let pct=null,below=null,P=null,verdict=null,vc=INK,note=null,markerPos=50;
 if(price!=null&&price>0){
  pct=Math.round((price-med)/med*1000)/10;
  below=amts.filter(x=>x<price).length; P=Math.round(below/amts.length*100);
  markerPos=span?Math.max(0,Math.min(100,(price-lo)/span*100)):50;
  if(pct<=-7){verdict="시세보다 저렴한 편";vc=DOWN;}
  else if(pct>=7){verdict="시세보다 비싼 편";vc=UP;}
  else {verdict="대체로 시세 수준";vc=INK;}
  if(lo!=null&&price<lo)note="최근 실거래 최저가보다 낮아요(급매·특수거래일 수 있어요).";
  else if(hi!=null&&price>hi)note="최근 실거래 최고가보다 높아요(신고가 수준).";
 }
 const medPos=span?Math.max(0,Math.min(100,(med-lo)/span*100)):50;
 return (<div style={{marginTop:14,padding:"12px 13px",background:"var(--surface-2)",borderRadius:12}}>
  <div style={{fontSize:12.5,fontWeight:800,display:"flex",alignItems:"center",gap:5}}>적정가 체크<Info text="입력한 가격이 이 평형의 최근 실거래 분포에서 어디쯤인지 보여줍니다. 층·향·동·시점에 따라 실제 적정가는 다를 수 있는 참고용 정보예요."/></div>
  <div style={{fontSize:11.5,color:MUTED,marginTop:3}}>매물·호가를 넣어보면 이 평형 시세 대비 위치를 알려드려요.</div>
  <div style={{display:"flex",alignItems:"center",gap:8,marginTop:9}}>
   <input value={v} onChange={e=>setV(e.target.value.replace(/[^0-9]/g,""))} inputMode="numeric" placeholder="예: 35000" style={{flex:1,minWidth:0,border:"1px solid var(--line)",borderRadius:9,padding:"10px 12px",fontSize:14,background:"var(--surface-solid)",color:"var(--ink)"}}/>
   <span className="num" style={{fontSize:12.5,color:MUTED,flex:"none"}}>만원{price?` · ${eok(price)}`:""}</span>
  </div>
  {price!=null&&price>0&&<div style={{marginTop:13}}>
   <div style={{display:"flex",alignItems:"baseline",gap:8,flexWrap:"wrap"}}>
    <span style={{fontWeight:800,fontSize:15,color:vc}}>{verdict}</span>
    <span className="num" style={{fontSize:12.5,color:vc,fontWeight:700}}>중앙값 대비 {pct>0?"+":""}{pct}%</span>
   </div>
   <div style={{position:"relative",height:8,borderRadius:5,marginTop:13,background:"linear-gradient(90deg,rgba(30,95,196,.30),rgba(99,120,128,.18),rgba(200,50,42,.30))"}}>
    <div style={{position:"absolute",left:`${medPos}%`,top:-3,width:2,height:14,background:MUTED,transform:"translateX(-1px)"}}/>
    <div style={{position:"absolute",left:`${markerPos}%`,top:-5,transform:"translateX(-50%)",width:13,height:18,borderRadius:4,background:vc,border:"2px solid var(--surface-solid)",boxShadow:"0 1px 4px rgba(0,0,0,.25)"}}/>
   </div>
   <div className="num" style={{display:"flex",justifyContent:"space-between",fontSize:10.5,color:MUTED,marginTop:6}}><span>저점 {eok(lo)}</span><span>중앙 {eok(med)}</span><span>고점 {eok(hi)}</span></div>
   <div style={{fontSize:11.5,color:MUTED,marginTop:9}}>최근 거래 {amts.length}건 중 이 가격보다 낮은 거래 {below}건 (하위 {P}%){amts.length<5?" · 표본 적어 참고만":""}</div>
   {note&&<div style={{fontSize:11.5,color:vc,marginTop:4,fontWeight:600}}>※ {note}</div>}
  </div>}
  <div style={{fontSize:10.5,color:MUTED,marginTop:9,lineHeight:1.6}}>※ 같은 평형 최근 실거래 기준 참고 위치예요. 층·향·동·시점·옵션에 따라 실제 적정가는 달라지며, 신고 지연·정정·이상거래가 섞일 수 있습니다.</div>
 </div>);
}
function AreaSection({a,unit,onLoan,open=true}){
 const months=(a.timeseries||[]).map(t=>t.month.slice(5)), vals=(a.timeseries||[]).map(t=>t.avg);
 return (<Collapsible icon="price" defaultOpen={open}
   title={<span>{areaTxt(a,unit)}</span>}
   right={<span className="num" style={{fontSize:12,color:MUTED}}>{a.trade_count}건</span>}>
  <div style={{padding:"6px 14px 12px"}}>
   <div style={{display:"flex",alignItems:"flex-end",gap:10,flexWrap:"wrap"}}>
    <div style={{minWidth:0}}><div style={{fontSize:12,color:MUTED}}>최근 매매가</div>
     <div className="num" style={{fontSize:24,fontWeight:800,lineHeight:1.1,marginTop:2}}>{eok(a.latest_amount)}</div></div>
    <div style={{marginLeft:"auto",textAlign:"right",flex:"none"}}>
     <div style={{fontWeight:800}}><Delta v={a.from_peak_pct}/></div>
     <div className="num" style={{fontSize:11,color:MUTED,marginTop:1}}>전고점 {eok(a.price_max)} 대비</div></div>
   </div>
   <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:"11px 8px",marginTop:13}}>
    <DMetric label="중앙값" val={a.price_median!=null?eok(a.price_median):"—"}/>
    <DMetric label="전저점 대비" val={<Delta v={a.from_trough_pct}/>} sub={a.price_min!=null?`저점 ${eok(a.price_min)}`:null}/>
    <JeonseMetric ratio={a.jeonse_ratio}/>
    <DMetric label={<React.Fragment>평단가<Info text="전용 1평(3.3㎡)당 가격(만원). 면적이 다른 단지·평형을 비교할 때 씁니다."/></React.Fragment>} val={a.ppm_median!=null?a.ppm_median.toLocaleString("ko-KR"):"—"} sub="만원/평"/>
    <DMetric label="매매 거래" val={`${a.trade_count}건`}/>
   </div>
   <FairPriceCheck a={a}/>
   {months.length>0&&<div style={{marginTop:14}}><div style={{fontSize:12,color:MUTED,fontWeight:700,marginBottom:4}}>매매 시세 추이</div><DetailLine months={months} values={vals}/></div>}
   {(a.recent||[]).length>0&&<div style={{marginTop:14}}>
    <div style={{fontSize:12,color:MUTED,fontWeight:700,marginBottom:2}}>최근 실거래<Info text="정정=신고 후 금액이 정정된 거래 · 직거래=중개 없이 거래(가족 등 특수관계가 섞일 수 있어 시세 해석 주의) · 이상치=같은 평형 중앙 평단가 대비 ±30% 넘게 벗어난 거래."/>{a.reliability&&a.reliability!=="ok"&&<span className="pill" style={{marginLeft:6,background:"rgba(178,106,0,.14)",color:"#9A6B00",fontWeight:700}}>표본 적음 {a.trade_count}건</span>}</div>
    <MoreList items={a.recent} initial={10} step={10} render={(r,i)=>{const isTrade=r.deal_type==="trade";
     const amt=isTrade?won(r.deal_amount):r.deal_type==="jeonse"?`보증 ${won(r.deposit)}`:`${won(r.deposit)}/월${r.monthly_rent}만`;
     const dc=isTrade?INK:r.deal_type==="jeonse"?TEAL:"#9A6B00";
     return <div key={i} className="listrow">
      <span style={{color:dc,fontWeight:700,fontSize:12.5,minWidth:34}}>{DEAL_LABEL[r.deal_type]}</span>
      <span style={{color:MUTED,fontSize:12.5}}>{r.floor??"—"}층 {r.is_sample&&<span className="pill ex">모의</span>}<TxFlags r={r}/></span>
      <span style={{marginLeft:"auto",textAlign:"right"}}><span className="num" style={{fontWeight:700,textDecoration:r.outlier?"line-through":"none",opacity:r.outlier?.6:1}}>{amt}</span>
       <span className="num" style={{color:MUTED,fontSize:11.5}}> · {r.contract_date||"—"}</span></span>
     </div>;}}/>
   </div>}
   <button onClick={onLoan} style={{marginTop:14,width:"100%",border:"1px solid "+TEAL,background:"rgba(15,118,110,.08)",color:TEAL,fontWeight:700,fontSize:13.5,padding:"10px",borderRadius:10,cursor:"pointer"}}>이 면적으로 대출 계산 →</button>
  </div>
 </Collapsible>);
}
function CommuteMap({dest,rows,mapCfg,onOpen}){
 const {ready,err}=useNaver(mapCfg.key,mapCfg.enabled);
 const ref=React.useRef(null);
 const [sel,setSel]=useState(null);
 const pts=(rows||[]).filter(r=>r.lat&&r.lng);
 const minColor=m=>m<=15?"#1d7a4d":m<=30?"#0F766E":m<=45?"#9A6B00":"#C8322A";
 const sig=(dest?`${dest.lat},${dest.lng}|`:"")+pts.map(r=>`${r.lat},${r.lng}:${r.minutes}`).join("|");
 useEffect(()=>{
  if(!ready||!ref.current||!window.naver||!dest||dest.lat==null)return;
  const n=window.naver; setSel(null);
  const map=new n.maps.Map(ref.current,{center:new n.maps.LatLng(dest.lat,dest.lng),zoom:12});
  const bounds=new n.maps.LatLngBounds(new n.maps.LatLng(dest.lat,dest.lng),new n.maps.LatLng(dest.lat,dest.lng));
  new n.maps.Marker({position:new n.maps.LatLng(dest.lat,dest.lng),map,zIndex:1000,
   icon:{content:`<div style="transform:translate(-50%,-100%);background:#1B2733;color:#fff;font-size:12px;font-weight:800;padding:6px 11px;border-radius:13px;box-shadow:0 2px 8px rgba(0,0,0,.5);white-space:nowrap">🏢 ${dest.name}</div>`,anchor:new n.maps.Point(0,0)}});
  pts.forEach(r=>{const c=minColor(r.minutes); bounds.extend(new n.maps.LatLng(r.lat,r.lng));
   const mk=new n.maps.Marker({position:new n.maps.LatLng(r.lat,r.lng),map,
    icon:{content:`<div style="transform:translate(-50%,-50%);background:${c};color:#fff;font-size:11px;font-weight:800;padding:3px 8px;border-radius:12px;box-shadow:0 1px 5px rgba(0,0,0,.4);white-space:nowrap;cursor:pointer">${r.minutes}분</div>`,anchor:new n.maps.Point(0,0)}});
   n.maps.Event.addListener(mk,"click",()=>setSel(r));});
  if(pts.length){try{map.fitBounds(bounds);}catch(e){}}
 },[ready,sig]);
 if(!mapCfg.enabled)return <Notice>지도를 보려면 서버 <b>.env</b> 에 <b>NAVER_MAP_CLIENT_ID</b> 설정 후 새로고침하세요.</Notice>;
 if(err)return <Notice>네이버 지도 인증 실패 — 클라이언트 ID/도메인을 확인하세요.</Notice>;
 return (<div style={{position:"relative"}}>
  <div ref={ref} style={{width:"100%",height:400,borderRadius:14,overflow:"hidden",background:"var(--chip)"}}/>
  {ready&&!pts.length&&<div style={{marginTop:8}}><Notice>표시할 단지 좌표가 없습니다. (운영: 단지 지오코딩 필요)</Notice></div>}
  {sel&&<div style={{position:"absolute",left:10,right:10,bottom:10,background:"var(--surface-solid)",borderRadius:13,boxShadow:"0 5px 20px rgba(20,40,60,.22)",padding:"12px 14px",zIndex:5}}>
   <div style={{display:"flex",alignItems:"flex-start",gap:8}}>
    <div style={{minWidth:0,flex:1}}>
     <div style={{fontWeight:800,fontSize:14,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{sel.name} {sel.is_sample&&<ExBadge/>}</div>
     <div style={{fontSize:12,color:MUTED,marginTop:2}}>{[(sel.gu||"").replace("청주시 ",""),TYPE_LABEL[sel.property_type],sel.method==="haversine"?"추정":"실측"].filter(Boolean).join(" · ")}</div>
    </div>
    <span onClick={()=>setSel(null)} aria-label="닫기" role="button" tabIndex={0} onKeyDown={onEnter(()=>setSel(null))} style={{cursor:"pointer",color:MUTED,fontWeight:700,fontSize:17,flex:"none",lineHeight:1}}>×</span>
   </div>
   <div style={{display:"flex",alignItems:"center",gap:10,marginTop:9}}>
    <span className="num" style={{fontWeight:800,fontSize:16,color:TEAL}}>{sel.minutes}분</span>
    {sel.price!=null&&<span className="num" style={{fontWeight:800,fontSize:15}}>{eok(sel.price)}</span>}
    <button onClick={()=>onOpen&&onOpen({complex_name:sel.name,lawd_cd:sel.lawd_cd,property_type:sel.property_type})} style={{marginLeft:"auto",border:"none",background:TEAL,color:"#fff",fontWeight:700,fontSize:12.5,borderRadius:9,padding:"8px 14px",cursor:"pointer"}}>단지 상세 →</button>
   </div>
  </div>}
 </div>);
}
function CommuteSearch({onClose,onOpen,mapCfg}){
 const [dests,setDests]=useState(null);
 const [destId,setDestId]=useState(null);
 const [mode,setMode]=useState("car");
 const [maxMin,setMaxMin]=useState(30);
 const [ptype,setPtype]=useState("전체");
 const [res,setRes]=useState(null);
 const [loading,setLoading]=useState(false);
 const [view,setView]=useState("list");
 const [quick,setQuick]=useState(null);
 const CAT={transit:"교통",job:"직장",public:"공공",education:"교육",medical:"의료"};
 useEffect(()=>{let on=true;
  fetch(`${API}/commute/destinations`).then(r=>r.json()).then(j=>{if(!on)return;
   const items=(j.items||[]).filter(d=>d.has_coord!==false); const use=items.length?items:DEMO_DESTS;
   setDests(use); setDestId(use[0]?use[0].id:null);})
   .catch(()=>{if(!on)return; setDests(DEMO_DESTS); setDestId(DEMO_DESTS[0].id);});
  return ()=>{on=false;};},[]);
 useEffect(()=>{if(destId==null)return; let on=true; setLoading(true);
  const q=`dest_id=${destId}&mode=${mode}&max_minutes=${maxMin}`+(ptype!=="전체"?`&property_type=${ptype}`:"");
  fetch(`${API}/commute/search?${q}`).then(r=>r.json()).then(j=>{if(!on)return;
   setRes(j&&j.found?j:demoCommuteSearch(destId,mode,maxMin,ptype)); setLoading(false);})
   .catch(()=>{if(!on)return; setRes(demoCommuteSearch(destId,mode,maxMin,ptype)); setLoading(false);});
  return ()=>{on=false;};},[destId,mode,maxMin,ptype]);
 const dest=(dests||[]).find(d=>d.id===destId);
 const rows=res&&res.results||[];
 return (<div style={{marginTop:6}}>
  <div style={{display:"flex",alignItems:"center",gap:10,margin:"2px 0 10px"}}>
   <button onClick={onClose} style={{border:"none",background:"var(--chip)",borderRadius:9,width:34,height:34,cursor:"pointer",fontSize:17,fontWeight:800,color:"var(--ink)",flex:"none"}}>‹</button>
   <div style={{fontWeight:800,fontSize:17}}>🧭 통근권으로 찾기</div>
  </div>
  <div className="card" style={{padding:13}}>
   <div style={{fontSize:12,color:MUTED,fontWeight:700,marginBottom:6}}>어디로 출근하세요?</div>
   <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
    {(dests||[]).map(d=>(<button key={d.id} onClick={()=>setDestId(d.id)} className={"tog "+(destId===d.id?"on":"")} style={{padding:"7px 11px",fontSize:12.5}}>
     <span style={{opacity:.7,fontSize:10.5,marginRight:4}}>{CAT[d.category]||""}</span>{d.name}</button>))}
    {!dests&&<span style={{fontSize:12,color:MUTED}}>불러오는 중…</span>}
   </div>
   <div style={{display:"flex",gap:8,marginTop:12,flexWrap:"wrap",alignItems:"center"}}>
    <div style={{display:"flex",gap:3,background:"var(--chip)",borderRadius:9,padding:3}}>
     {[["car","🚗 자동차"],["transit","🚌 대중교통"]].map(([k,l])=><button key={k} onClick={()=>setMode(k)} style={{border:"none",cursor:"pointer",fontWeight:700,fontSize:12,padding:"7px 11px",borderRadius:7,background:mode===k?"var(--surface-solid)":"transparent",color:mode===k?TEAL:MUTED}}>{l}</button>)}
    </div>
    <select className="sel" style={{maxWidth:130}} value={ptype} onChange={e=>setPtype(e.target.value)}>
     <option value="전체">전체 유형</option>
     {Object.entries(TYPE_LABEL).map(([v,l])=><option key={v} value={v}>{l}</option>)}
    </select>
   </div>
   <div style={{display:"flex",alignItems:"center",gap:9,marginTop:12}}>
    <span style={{fontSize:12,color:MUTED,fontWeight:700,flex:"none"}}>{maxMin}분 이내</span>
    <input type="range" aria-label="통근 시간(분)" min="10" max="60" step="5" value={maxMin} onChange={e=>setMaxMin(+e.target.value)} style={{flex:1,accentColor:"#0F766E"}}/>
   </div>
  </div>
  <div style={{display:"flex",alignItems:"center",gap:7,margin:"12px 2px 8px"}}>
   <span style={{fontWeight:800,fontSize:14}}>{dest?dest.name:"—"}까지 {maxMin}분 이내</span>
   <span className="num" style={{fontSize:12.5,color:MUTED}}>{loading?"…":`${rows.length}곳`}</span>
   <div style={{marginLeft:"auto",display:"flex",gap:3,background:"var(--chip)",borderRadius:9,padding:3}}>
    {[["list","리스트"],["map","지도"]].map(([k,l])=><button key={k} onClick={()=>setView(k)} style={{border:"none",cursor:"pointer",fontWeight:700,fontSize:11.5,padding:"5px 11px",borderRadius:7,background:view===k?"var(--surface-solid)":"transparent",color:view===k?TEAL:MUTED}}>{l}</button>)}
   </div>
  </div>
  {res&&res.method_summary&&<div style={{margin:"-2px 2px 8px"}}><span className="pill" style={{background:"var(--chip)",color:MUTED,fontWeight:700}}>{res.method_summary}<Info text="‘실측’은 자동차 길찾기 기준, ‘추정’은 직선거리에 우회·평균속도를 보정한 값입니다. 실제와 다를 수 있어요."/></span></div>}
  {view==="map"
   ? <CommuteMap dest={dest} rows={rows} mapCfg={mapCfg} onOpen={onOpen}/>
   : (loading&&!rows.length?<SkeletonCard lines={3}/>:
      rows.length===0?<Empty>{maxMin}분 이내 단지가 없어요. 시간을 늘리거나 다른 목적지를 골라보세요.</Empty>:
      <div className="card" style={{padding:0,overflow:"hidden"}}>
       {rows.map((r,i)=>(<div key={i} className="txrow" style={{cursor:"pointer"}} tabIndex={0} role="button" onKeyDown={onEnter(()=>setQuick(r))} onClick={()=>setQuick(r)}>
        <div style={{flex:"none",textAlign:"center",minWidth:52}}>
         <div className="num" style={{fontWeight:800,fontSize:18,color:TEAL,lineHeight:1}}>{r.minutes}</div>
         <div style={{fontSize:10,color:MUTED}}>분</div>
        </div>
        <div style={{minWidth:0,flex:1}}>
         <div style={{fontWeight:700,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{r.name} {r.is_sample&&<ExBadge/>}</div>
         <div style={{fontSize:12,color:MUTED,marginTop:1}}>{[r.gu,TYPE_LABEL[r.property_type],r.method==="haversine"?"추정":"실측"].filter(Boolean).join(" · ")}</div>
        </div>
        <div style={{textAlign:"right",flex:"none"}}>
         <div className="num" style={{fontWeight:800}}>{r.price!=null?eok(r.price):"—"}</div>
         <span style={{color:MUTED,fontSize:16}}>›</span>
        </div>
       </div>))}
      </div>)}
  <div style={{fontSize:11,color:MUTED,marginTop:10,lineHeight:1.6}}>통근시간은 참고용 추정입니다. 좌표·도로·시간대에 따라 실제와 다를 수 있어요. 단지를 누르면 요약이 뜨고, 거기서 상세로 이동합니다.</div>
  <div style={{height:16}}/>
  {quick&&<Sheet title={quick.name} onClose={()=>setQuick(null)}>
   <div style={{display:"flex",gap:14,flexWrap:"wrap",padding:"2px 4px 4px"}}>
    <div><div style={{fontSize:11,color:MUTED}}>{dest?dest.name:"목적지"}까지</div><div className="num" style={{fontSize:20,fontWeight:800,color:TEAL}}>{quick.minutes}분</div></div>
    <div><div style={{fontSize:11,color:MUTED}}>시세(중앙)</div><div className="num" style={{fontSize:20,fontWeight:800}}>{quick.price!=null?eok(quick.price):"—"}</div></div>
   </div>
   <div style={{fontSize:12.5,color:MUTED,padding:"2px 4px 12px"}}>{[quick.gu,TYPE_LABEL[quick.property_type],quick.method==="haversine"?"통근 추정":"통근 실측"].filter(Boolean).join(" · ")}</div>
   <button onClick={()=>{onOpen&&onOpen({complex_name:quick.name,lawd_cd:quick.lawd_cd,property_type:quick.property_type});setQuick(null);}} style={{width:"100%",border:"none",background:TEAL,color:"#fff",fontWeight:800,fontSize:14,borderRadius:11,padding:"13px",cursor:"pointer"}}>단지 상세 보기 →</button>
   <div style={{height:8}}/>
  </Sheet>}
 </div>);
}
function CautionSignals({card,d}){
 // 흩어진 주의 '사실'을 한 장으로 통합 — 새 수치를 만들지 않고 이미 표시되는 실거래 사실만 모음(왜곡 없음).
 // 판정("사지 마세요") 금지 = 사실+근거+면책. 신호가 없으면 숨김(안전을 암시하지 않기 위해).
 const f=[];
 if(card.jr!=null && card.jr>=75)
  f.push(["전세가율 "+card.jr+"%","매매가 대비 보증금 비중이 커요 — 역전세·깡통전세 유의(단정 아님)"]);
 if(card.fromPeak!=null && card.fromPeak<=-15)
  f.push(["최근 "+AGG_MONTHS+"개월 고점 대비 "+card.fromPeak+"%","하락 구간일 수 있어요(추세 단정 아님)"]);
 if((d.reliability==="low"||d.reliability==="fair") || (card.count!=null&&card.count<5))
  f.push(["최근 거래 "+(card.count!=null?card.count:0)+"건","표본이 적어 시세가 흔들릴 수 있어요"]);
 if(d.canceled_count>0)
  f.push(["신고 후 해제(취소) "+d.canceled_count+"건","실제 성사 거래가 아니라 시세 집계에서 제외했어요"]);
 if(!f.length) return null;
 return (<div className="card" style={{padding:"12px 14px",marginTop:10,background:"var(--callout-bg)",border:"none"}}>
  <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:6}}>
   <span style={{fontWeight:800,fontSize:13.5,color:"var(--callout-fg)"}}>⚠️ 참고 주의 신호</span>
   <Info text="이 단지에서 참고할 만한 사실을 모았어요. 매수·매도 판단이 아니라 확인용이며, 각 항목은 이 앱 실거래 데이터의 사실입니다."/>
  </div>
  {f.map(([t,why],i)=>(<div key={i} style={{display:"flex",gap:8,padding:"5px 0",borderTop:i>0?"1px solid var(--line)":"none"}}>
   <span style={{color:"#C77A1A",fontSize:13,flex:"none",lineHeight:1.5}}>•</span>
   <div style={{minWidth:0}}>
    <div style={{fontSize:13,fontWeight:700,color:"var(--ink)"}}>{t}</div>
    <div style={{fontSize:11.5,color:MUTED,marginTop:1,lineHeight:1.5}}>{why}</div>
   </div>
  </div>))}
  <div style={{fontSize:10.5,color:MUTED,marginTop:8,lineHeight:1.5}}>참고용 신호 모음이며 매수·매도 판단이 아니에요.</div>
 </div>);
}
function Detail({sel,mapCfg,onBack,isFav,onToggleFav,inCompare,onToggleCompare,onOpen}){
 const unit=useUnit();
 const [d,setD]=useState(null);
 const [loanArea,setLoanArea]=useState(null);
 const [cardOpen,setCardOpen]=useState(false);
 const [tabPy,setTabPy]=useState(sel.area!=null?Math.round(sel.area/PY):null);   // 평형 탭(단지 전체=null)
 useEffect(()=>{let on=true;setD(null);
  const q=`name=${encodeURIComponent(sel.name)}&lawd_cd=${sel.lawd_cd}`+(sel.property_type?`&property_type=${sel.property_type}`:"");
  fetch(`${API}/complex/detail?${q}`).then(r=>r.json()).then(j=>{if(on)setD(j);}).catch(()=>{if(on)setD(demoDetail(sel));});
  return ()=>{on=false;};},[sel.name,sel.lawd_cd,sel.property_type]);
 useEffect(()=>{setLoanArea(null);setTabPy(sel.area!=null?Math.round(sel.area/PY):null);},[sel.name,sel.lawd_cd,sel.property_type,sel.area]);
 if(!d)return <div style={{marginTop:6}}><div style={{height:8}}/><SkeletonCard lines={4}/><SkeletonCard/></div>;
 if(!d.found)return <div style={{marginTop:6}}><Empty>이 단지의 거래 데이터를 찾지 못했습니다.</Empty></div>;
 const mapItem=[{rank:1,complex_name:d.name,lat:d.lat,lng:d.lng,deal_amount:d.latest_amount}];
 const areas=d.areas||[];
 const focusPy=tabPy;
 const pyList=[...new Set(areas.map(a=>Math.round(a.area/PY)).filter(x=>x))].sort((a,b)=>a-b);
 const matched=focusPy!=null?areas.filter(a=>Math.round(a.area/PY)===focusPy):[];
 const useAreas=matched.length?matched:areas;
 const narrowed=matched.length>0&&matched.length<areas.length;
 const jrVals=useAreas.map(a=>a.jeonse_ratio).filter(v=>v!=null).sort((x,y)=>x-y);
 const jr=narrowed?(jrVals.length?jrVals[Math.floor(jrVals.length/2)]:null):d.jeonse_ratio;
 const repArea=narrowed?useAreas[0]:null;
 const ppmComplex=(()=>{const v=areas.map(a=>a.ppm_median).filter(x=>x!=null).sort((x,y)=>x-y);return v.length?v[Math.floor(v.length/2)]:null;})();
 const card={name:d.name,sub:[guOf(d.gu),d.dong,TYPE_LABEL[d.property_type],d.build_year?`${d.build_year}년`:null].filter(Boolean).join(" · "),
  scope:narrowed?(matched.map(a=>areaTxt(a,unit)).join("·")+" 평형"):"단지 전체",
  latest:repArea?repArea.latest_amount:d.latest_amount, fromPeak:repArea?repArea.from_peak_pct:d.from_peak_pct,
  peak:repArea?repArea.price_max:d.peak_amount, median:repArea?repArea.price_median:d.price_median,
  ppm:repArea?repArea.ppm_median:ppmComplex, jr:jr, count:repArea?repArea.trade_count:d.trade_count,
  ts:(repArea?repArea.timeseries:d.timeseries)||[], sample:d.contains_sample_data, agg:AGG_MONTHS};
 const goLoan=a=>{setLoanArea(a);setTimeout(()=>{const el=document.getElementById("detail-loan");if(el)el.scrollIntoView({behavior:"smooth"});},60);};
 const _elem=d.school_access&&d.school_access.elementary;
 const _elemD=_elem&&_elem.distance!=null?_elem.distance:null;
 const chopuma=_elemD!=null&&_elemD<=400;      // 초품아: 초등학교 도보 ~5분(≤400m)
 const elemWalk=_elemD!=null&&_elemD<=700;      // 초등 도보권(≤700m)
 const loanInit=loanArea?(loanArea.latest_amount||loanArea.price_median):(useAreas[0]?(useAreas[0].latest_amount||useAreas[0].price_median):null);
 return (<div style={{marginTop:6}}>
  
  <div style={{margin:"8px 2px 0",display:"flex",alignItems:"flex-start",gap:8}}>
   <div style={{minWidth:0}}>
    <div style={{fontSize:20,fontWeight:800,overflowWrap:"anywhere",lineHeight:1.25}}>{d.name} {d.contains_sample_data&&<span className="pill ex">모의</span>}</div>
    <div style={{fontSize:13,color:MUTED,marginTop:3}}>{guOf(d.gu)} · {d.dong||"—"} · {TYPE_LABEL[d.property_type]||"—"}{d.build_year?` · ${d.build_year}년`:""}</div>
    {(chopuma||elemWalk)&&<div style={{marginTop:6,display:"flex",gap:6,alignItems:"center",flexWrap:"wrap"}}>
     {chopuma
      ?<span className="pill" style={{background:"rgba(15,118,110,.13)",color:TEAL,fontWeight:800,fontSize:11.5}}>🏫 초품아</span>
      :<span className="pill" style={{background:"var(--chip)",color:MUTED,fontWeight:700,fontSize:11.5}}>🏫 초등 도보권</span>}
     {_elem&&_elem.name&&<span style={{fontSize:11.5,color:MUTED}}>{_elem.name} {distM(_elemD)}</span>}
    </div>}
   </div>
   {onToggleCompare&&<button onClick={()=>onToggleCompare({complex_name:d.name,lawd_cd:sel.lawd_cd,property_type:d.property_type,gu:d.gu,dong:d.dong})}
     title="비교 담기" style={{marginLeft:"auto",flex:"none",border:"1px solid var(--line)",borderRadius:9,padding:"7px 11px",cursor:"pointer",fontWeight:800,fontSize:12.5,
       background:inCompare&&inCompare({complex_name:d.name,lawd_cd:sel.lawd_cd,property_type:d.property_type})?"var(--teal)":"var(--surface-2)",
       color:inCompare&&inCompare({complex_name:d.name,lawd_cd:sel.lawd_cd,property_type:d.property_type})?"#fff":MUTED}}>
    {inCompare&&inCompare({complex_name:d.name,lawd_cd:sel.lawd_cd,property_type:d.property_type})?"✓ 비교중":"⊕ 비교"}</button>}
   {onToggleFav&&<button onClick={()=>onToggleFav({complex_name:d.name,lawd_cd:sel.lawd_cd,property_type:d.property_type,gu:d.gu,dong:d.dong})}
     style={{border:"none",background:"none",cursor:"pointer",padding:4,flex:"none"}} title="관심 등록">
    <Icon name="star" active={isFav&&isFav(favId({complex_name:d.name,lawd_cd:sel.lawd_cd,property_type:d.property_type}))} size={26}/>
   </button>}
  </div>
  {pyList.length>1&&<div style={{display:"flex",gap:6,overflowX:"auto",margin:"12px 0 0",paddingBottom:2}}>
   <button onClick={()=>setTabPy(null)} className={"tog "+(focusPy==null?"on":"")} style={{whiteSpace:"nowrap",flex:"none"}}>전체</button>
   {pyList.map(py=><button key={py} onClick={()=>setTabPy(py)} className={"tog "+(focusPy===py?"on":"")} style={{whiteSpace:"nowrap",flex:"none"}}>{py}평</button>)}
  </div>}
  <div className="card" style={{padding:16,marginTop:12}}>
   <div style={{display:"flex",alignItems:"flex-end",gap:10,flexWrap:"wrap"}}>
    <div style={{minWidth:0}}>
     <div style={{fontSize:12.5,color:MUTED}}>{narrowed?`전용 ${card.scope} 최근 매매가`:"단지 전체 최근 매매가"} <span style={{fontSize:10.5}}>· 최근 {AGG_MONTHS}개월 기준</span></div>
     <div className="num" style={{fontSize:26,fontWeight:800,lineHeight:1.1,marginTop:3}}>{card.latest!=null?eok(card.latest):"—"}</div>
    </div>
    <div style={{marginLeft:"auto",textAlign:"right",flex:"none"}}>
     <div style={{fontSize:17,fontWeight:800}}><Delta v={card.fromPeak}/></div>
     <div className="num" style={{fontSize:11,color:MUTED,marginTop:2}}>최근 {AGG_MONTHS}개월 고점 {card.peak!=null?eok(card.peak):"—"} 대비</div>
    </div>
   </div>
   {!narrowed&&d.vs_region&&<div style={{marginTop:11,padding:"10px 12px",borderRadius:11,background:"var(--surface-2)",display:"flex",alignItems:"center",gap:8,flexWrap:"wrap"}}>
    <span style={{fontSize:13}}>📍</span>
    <span style={{fontSize:13,fontWeight:700}}>{d.vs_region.gu} 평균 대비</span>
    <span className="num" style={{fontSize:16,fontWeight:800,color:d.vs_region.pct>0?UP:d.vs_region.pct<0?DOWN:INK}}>{d.vs_region.pct>0?"+":""}{d.vs_region.pct}%</span>
    <span style={{fontSize:11.5,color:MUTED,marginLeft:"auto"}}>평단가 {d.vs_region.complex_ppm?.toLocaleString?.()||d.vs_region.complex_ppm} vs {d.vs_region.gu_ppm?.toLocaleString?.()||d.vs_region.gu_ppm} 만원/평</span>
   </div>}
   {(card.ts||[]).length>1&&<TrendBlock ts={card.ts}/>}
   <div style={{height:1,background:"rgba(99,120,128,.12)",margin:"13px 0 11px"}}/>
   <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:"11px 10px"}}>
    <DMetric label="매매 거래" val={`${card.count!=null?card.count:0}건`}/>
    <JeonseMetric ratio={card.jr}/>
    {narrowed?<DMetric label={<React.Fragment>평단가<Info text="전용 1평(3.3㎡)당 가격(만원)."/></React.Fragment>} val={card.ppm!=null?card.ppm.toLocaleString("ko-KR"):"—"} sub="만원/평"/>:<DMetric label="면적 타입" val={`${areas.length}개`}/>}
   </div>
  </div>
  <CautionSignals card={card} d={d}/>
  <VolumeSignal volume={d.volume}/>
  <JeonseSafety ratio={card.jr} scope={card.scope} note={!narrowed?(d.rent_signal&&d.rent_signal.note):null}/>
  <PriceCheck name={d.name} lawd={d.lawd_cd||sel.lawd_cd} pt={d.property_type||sel.property_type}/>
  <Collapsible icon="map" defaultOpen={true} title="위치">
   <div style={{padding:14}}><RankMap items={mapItem} mapCfg={mapCfg}/></div>
  </Collapsible>
  {d.poi&&<Collapsible icon="search" defaultOpen={true} title="인근 인프라">
   <div style={{padding:"4px 14px"}}>
    {Object.entries(d.poi).map(([label,items])=>(<div key={label} className="listrow" style={{alignItems:"flex-start"}}>
     <span style={{fontWeight:700,minWidth:48,flex:"none"}}>{label}</span>
     <div style={{minWidth:0}}>
      {items.length?items.map((it,i)=>(<div key={i} style={{fontSize:13.5,marginBottom:1}}>{it.name} <span style={{color:MUTED,fontSize:12}}>{distM(it.distance)}</span></div>))
       :<span style={{color:MUTED,fontSize:12.5}}>반경 내 없음</span>}
     </div>
    </div>))}
    {d.poi&&d.poi["중개업소"]&&<div style={{fontSize:11,color:MUTED,padding:"6px 2px 8px"}}>※ 중개업소는 단지 인근 참고 정보이며, 위 실거래를 중개한 업소가 아닙니다.</div>}
   </div>
  </Collapsible>}
  <WorkAccess items={d.work_access}/>
  <ComplexTalk name={d.name} lawd={d.lawd_cd||sel.lawd_cd}/>
  <button onClick={()=>setCardOpen(true)} style={{width:"100%",marginTop:12,border:"1px solid rgba(15,118,110,.28)",background:"var(--surface-2)",color:TEAL,fontWeight:800,fontSize:14,borderRadius:12,padding:"13px 0",cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center",gap:7}}>📤 이 시세 카드 공유하기</button>
  {cardOpen&&<ShareCard card={card} onClose={()=>setCardOpen(false)}/>}
  {d.complex_meta&&<Collapsible icon="search" defaultOpen={true} title="단지 정보">
   <div style={{padding:"8px 14px 12px"}}>
    <div style={{display:"grid",gridTemplateColumns:"repeat(2,1fr)",gap:"9px 14px"}}>
     {[["세대수",d.complex_meta.households!=null?`${d.complex_meta.households.toLocaleString()}세대`:"—"],
       ["동수",d.complex_meta.dong_count!=null?`${d.complex_meta.dong_count}개동`:"—"],
       ["사용승인",d.complex_meta.approval_date||"—"],
       ["난방",d.complex_meta.heating||"—"],
       ["연면적",d.complex_meta.total_area!=null?`${Math.round(d.complex_meta.total_area).toLocaleString()}㎡`:"—"],
       ["시공사",d.complex_meta.builder||"—"],
       ["총주차",d.complex_meta.parking!=null?`${d.complex_meta.parking.toLocaleString()}대`:"—"],
       ["공시가격",d.complex_meta.price_official!=null?`${eok(d.complex_meta.price_official)}${d.complex_meta.price_basis_date?` (${d.complex_meta.price_basis_date} 기준)`:""}`:"—"]
      ].map(([l,v])=>(<div key={l} style={{display:"flex",justifyContent:"space-between",fontSize:13.5,borderBottom:"1px solid rgba(99,120,128,.08)",paddingBottom:5}}>
       <span style={{color:MUTED}}>{l}</span><span style={{fontWeight:700,textAlign:"right",minWidth:0}}>{v}</span>
      </div>))}
    </div>
    <div style={{fontSize:11,color:MUTED,marginTop:9}}>자료: 공동주택관리정보(K-apt)·국토부 공동주택 공시가격 · 아파트 한정 · 누락 항목은 미제공</div>
   </div>
  </Collapsible>}
  <ExternalListings d={d}/>
  <Collapsible icon="search" defaultOpen={narrowed} title={`면적별 상세${narrowed?" (선택 평형)":""}`}>
   <div style={{padding:"2px 0"}}>
   {useAreas.length?[...useAreas].sort((a,b)=>(a.area||0)-(b.area||0)).map((a,i)=><AreaSection key={i} a={a} unit={unit} onLoan={()=>goLoan(a)} open={narrowed||useAreas.length===1}/>)
    :<Empty>면적 정보가 있는 거래가 없습니다.</Empty>}
   </div>
  </Collapsible>
  {d.living_score&&<LivingScore data={d.living_score}/>}
  <KidsEnv places={d.places}/>
  {d.places&&Object.keys(d.places).length>0&&<Collapsible icon="search" defaultOpen={true} title="주변 학원·운동·생활">
   <div style={{padding:"4px 14px"}}>
    {Object.entries(d.places).sort((a,b)=>b[1].count-a[1].count).map(([sub,info])=>(<div key={sub} className="listrow" style={{alignItems:"flex-start"}}>
     <span style={{fontWeight:700,minWidth:62,flex:"none"}}>{info.label} <span style={{color:TEAL,fontWeight:800}}>{info.count}</span></span>
     <div style={{minWidth:0}}>
      {(info.items||[]).slice(0,4).map((it,i)=>(<div key={i} style={{fontSize:13.5,marginBottom:1}}>{it.name}{it.tuition?<span style={{color:MUTED,fontSize:12}}> · {Math.round(it.tuition/10000*10)/10}만원</span>:""} <span style={{color:MUTED,fontSize:12}}>{distM(it.distance)}</span></div>))}
     </div>
    </div>))}
    <div style={{fontSize:11,color:MUTED,padding:"6px 2px 8px"}}>자료: 공공데이터(학원·체육·도서관·의료 등). 공개분 수강료/사용료만 표시. 반경 약 1.2km.</div>
   </div>
  </Collapsible>}
  {d.landmarks&&d.landmarks.length>0&&<Collapsible icon="trend" defaultOpen={true} title="주변 개발 호재">
   <div style={{padding:"4px 14px"}}>
    {d.landmarks.map(L=>{const sc=L.status==="confirmed"?TEAL:L.status==="ongoing"?"#C77A1A":MUTED;return (
     <div key={L.id} style={{padding:"9px 0",borderBottom:"1px solid var(--line)"}}>
      <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
       <span style={{fontSize:10.5,fontWeight:800,color:"#fff",background:sc,borderRadius:6,padding:"2px 7px"}}>{L.status_label}</span>
       <span style={{fontWeight:700}}>{L.name}</span>
       <span style={{fontSize:11.5,color:MUTED}}>{L.category_label}{L.expected_year?` · ${L.expected_year}년`:""}{L.distance!=null?` · ${distM(L.distance)}`:""}</span>
      </div>
      {L.summary&&<div style={{fontSize:12.5,color:INK,marginTop:4,lineHeight:1.5}}>{L.summary}</div>}
      {L.source_name&&<div style={{fontSize:11,color:MUTED,marginTop:3}}>출처: {L.source_url?<a href={L.source_url} target="_blank" rel="noreferrer" style={{color:MUTED,textDecoration:"underline"}}>{L.source_name}</a>:L.source_name}</div>}
     </div>);})}
    <div style={{fontSize:11,color:MUTED,padding:"7px 2px 8px",lineHeight:1.5}}>※ 개발 단계(확정/추진/계획)와 출처를 함께 표기한 참고 정보입니다. 집값 변동을 보장하지 않으며 투자 판단은 본인 책임입니다.</div>
   </div>
  </Collapsible>}
  <div id="detail-loan"/>
  <Collapsible key={loanArea?("la"+loanArea.area):"none"} icon="loan" defaultOpen={!!loanArea} title={<React.Fragment>대출 계산 <span style={{fontWeight:500,color:MUTED,fontSize:12}}>· 참고용</span></React.Fragment>}>
   <div style={{padding:"6px 14px 10px"}}>
    {useAreas.length>0&&<React.Fragment>
     <div style={{fontSize:12,color:MUTED,marginBottom:7}}>면적을 고르면 그 면적 최근 매매가로 자동 입력됩니다.</div>
     <div style={{display:"flex",gap:6,flexWrap:"wrap",marginBottom:6}}>
      {useAreas.map((a,i)=>{const on=(loanArea?loanArea.area:useAreas[0].area)===a.area;
        return <button key={i} className={"tog "+(on?"on":"")} onClick={()=>setLoanArea(a)}>{areaTxt(a,unit)} · {eok(a.latest_amount||a.price_median)}</button>;})}
     </div>
    </React.Fragment>}
    <Loan key={loanArea?loanArea.area:(useAreas[0]?useAreas[0].area:"none")} initialPrice={loanInit} onOpen={onOpen}/>
   </div>
  </Collapsible>
  <div style={{height:16}}/>
 </div>);
}

/* ---------------- 랭킹: 셀렉트박스 ---------------- */
function Rank({ptype,d,mapCfg,onOpen}){
 const rk=d.ranking||{};
 const [metric,setMetric]=useState("amount");
 const [page,setPage]=useState(1);
 const PER=10;
 const pt=(ptype&&ptype!=="전체")?ptype:"apartment";
 const changeMetric=e=>{setMetric(e.target.value);setPage(1);};
 const needType=metric!=="active";
 const byBand=(metric==="amount"||metric==="ppm");
 const METRICS=[["amount","매매가 순"],["ppm","평단가(만원/평) 순"],["mover","등락폭 순"],["high","신고가"],["low","신저가"],["active","거래 활발 구"]];
 const BANDS3=[["small","소형 (~60㎡)"],["medium","중형 (60~85㎡)"],["large","대형 (85㎡~)"]];
 const bandOf=a=>a==null?null:(a<60?"small":a<85?"medium":"large");
 const LISTS={amount:rk.top_trades,ppm:rk.top_by_ppm,mover:rk.top_movers,high:rk.newly_high,low:rk.newly_low,active:rk.active_regions};
 const full=LISTS[metric]||[];
 const paged=full.slice((page-1)*PER,page*PER);
 const mapItems=metric==="amount"?(rk.top_trades||[]):metric==="ppm"?(rk.top_by_ppm||[]):[];
 return (<div style={{marginTop:6}}>
  <div style={{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap"}}>
   <select className="sel" style={{flex:"2 1 150px"}} value={metric} onChange={changeMetric}>
    {METRICS.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>
   {needType&&<span style={{fontSize:12,color:MUTED}}>{TYPE_LABEL[pt]||"아파트"} 기준</span>}
  </div>
  <div style={{fontSize:12,color:MUTED,margin:"8px 2px 0"}}>{metric==="active"?"전 유형 합산":byBand?"대표 평형별 · 같은 단지·면적은 묶고 대표값(중앙값)":"실거래 신고 기준"} · 총 {full.length}건</div>
  {/* 지도: 매매가·평단가 순위에서 단지 위치 (맨 위) */}
  <Collapsible icon="map" defaultOpen={true} title="지도에서 보기">
   <div style={{padding:14}}>
   {(metric==="amount"||metric==="ppm")
    ? <RankMap items={mapItems} mapCfg={mapCfg}/>
    : <Notice>지도는 ‘매매가 순/평단가 순’에서 단지 위치로 표시됩니다. 위 기준을 선택해 보세요.</Notice>}
   </div>
  </Collapsible>
  {byBand
   ? BANDS3.map(([k,label])=>{const groups=rankGroups(full.filter(r=>bandOf(r.exclusive_area)===k),metric);
      return (<Collapsible key={k} icon="rank" defaultOpen={true} title={label}
        right={<span className="num" style={{fontSize:12,color:MUTED}}>{groups.length}</span>}>
       <div style={{padding:"4px 14px"}}>
        {groups.length?<RankGroups rows={groups.slice(0,30)} unit={metric} onOpen={onOpen}/>:<Empty>해당 평형 거래가 없습니다.</Empty>}
       </div>
      </Collapsible>);})
   : <div className="card" style={{padding:14,marginTop:8}}>
      {metric==="mover"&&<RankMovers rows={paged}/>}
      {metric==="high"&&<RankHigh rows={paged}/>}
      {metric==="low"&&<RankLow rows={paged}/>}
      {metric==="active"&&<RankActive rows={paged}/>}
      <Pager page={page} setPage={setPage} total={full.length} per={PER}/>
     </div>}
 </div>);
}
function RankTrades({rows,unit,onOpen}){
 const au=useUnit();
 if(!rows.length)return <Empty>해당 유형의 매매 데이터가 없습니다.</Empty>;
 return rows.map(r=>{const clickable=onOpen&&r.complex_name;
  return (<div key={r.rank} tabIndex={clickable?0:undefined} role={clickable?"button":undefined} onKeyDown={clickable?onEnter(()=>onOpen(r)):undefined} className="listrow" onClick={clickable?()=>onOpen(r):undefined} style={clickable?{cursor:"pointer"}:undefined}>
  <span className={"rankno "+(r.rank<=3?"top":"")}>{r.rank}</span>
  <div style={{minWidth:0}}>
   <div style={{fontWeight:600,overflow:"hidden",textOverflow:"ellipsis"}}>{r.complex_name||"— (단독)"} {r.is_sample&&<ExBadge/>}</div>
   <div style={{fontSize:12,color:MUTED}}>{r.dong||"—"} · {guOf(r.gu)} · {fmtArea(r.exclusive_area,au)}{r.floor?` · ${r.floor}층`:""}</div>
  </div>
  <div style={{marginLeft:"auto",textAlign:"right",flex:"none"}}>
   <div className="num" style={{fontWeight:800}}>{unit==="ppm"?pyeong(r.pyeong_unit):eok(r.deal_amount)}</div>
   <div className="num" style={{fontSize:11.5,color:MUTED}}>{unit==="ppm"?won(r.deal_amount):pyeong(r.pyeong_unit)}{clickable?" ›":""}</div>
  </div>
 </div>);});
}
/* 랭킹: 같은 단지·같은 면적 묶기 → 대표값(중앙값) + 탭하면 개별거래 펼침 */
function rankGroups(rows,unit){
 const groups={},singles=[];
 (rows||[]).forEach(r=>{
  if(!r.complex_name){singles.push(r);return;}
  const k=r.complex_name+"|"+(r.exclusive_area!=null?Math.round(r.exclusive_area):"?");
  (groups[k]=groups[k]||{key:k,complex_name:r.complex_name,gu:r.gu,dong:r.dong,exclusive_area:r.exclusive_area,is_sample:r.is_sample,items:[]}).items.push(r);
 });
 const med=a=>{const s=[...a].sort((x,y)=>x-y);return s.length?s[Math.floor((s.length-1)/2)]:null;};
 const arr=Object.values(groups).map(g=>{
  g.items.sort((a,b)=>(b.deal_amount||0)-(a.deal_amount||0));
  g.count=g.items.length;
  g.rep_price=med(g.items.map(x=>x.deal_amount||0));
  const pp=g.items.map(x=>x.pyeong_unit).filter(v=>v!=null);
  g.rep_ppm=pp.length?med(pp):null;
  return g;
 });
 singles.forEach((s,i)=>arr.push({key:"single|"+(s.rank||i),complex_name:s.complex_name,gu:s.gu,dong:s.dong,exclusive_area:s.exclusive_area,is_sample:s.is_sample,items:[s],count:1,rep_price:s.deal_amount,rep_ppm:s.pyeong_unit,single:true}));
 const kv=g=>unit==="ppm"?(g.rep_ppm||0):(g.rep_price||0);
 arr.sort((a,b)=>kv(b)-kv(a));
 arr.forEach((g,i)=>g.rank=i+1);
 return arr;
}
function RankGroups({rows,unit,onOpen}){
 const au=useUnit();
 const [open,setOpen]=useState({});
 if(!rows.length)return <Empty>해당 유형의 매매 데이터가 없습니다.</Empty>;
 const toggle=k=>setOpen(o=>({...o,[k]:!o[k]}));
 return rows.map(g=>{
  const isOpen=!!open[g.key];
  const rep=unit==="ppm"?pyeong(g.rep_ppm):eok(g.rep_price);
  const sub=unit==="ppm"?won(g.rep_price):(g.rep_ppm!=null?pyeong(g.rep_ppm):null);
  return (<div key={g.key} style={{borderBottom:"1px solid rgba(99,120,128,.10)"}}>
   <div className="listrow" style={{borderBottom:"none",cursor:"pointer"}}
     onClick={()=>g.count>1?toggle(g.key):(onOpen&&g.complex_name&&onOpen(g.items[0]))}>
    <span className={"rankno "+(g.rank<=3?"top":"")}>{g.rank}</span>
    <div style={{minWidth:0}}>
     <div style={{fontWeight:600,overflow:"hidden",textOverflow:"ellipsis"}}>{g.complex_name||"— (단독)"} {g.is_sample&&<ExBadge/>}
      {g.count>1&&<span className="pill" style={{background:"rgba(15,118,110,.12)",color:TEAL,marginLeft:4}}>{g.count}건</span>}</div>
     <div style={{fontSize:12,color:MUTED}}>{g.dong||"—"} · {guOf(g.gu)} · {fmtArea(g.exclusive_area,au)}</div>
    </div>
    <div style={{marginLeft:"auto",textAlign:"right",flex:"none"}}>
     <div className="num" style={{fontWeight:800}}>{rep}</div>
     <div className="num" style={{fontSize:11.5,color:MUTED}}>{g.count>1?(isOpen?"접기 ▴":"펼치기 ▾"):(sub||"")}</div>
    </div>
   </div>
   {isOpen&&g.count>1&&<div style={{padding:"0 0 8px 40px"}}>
    {g.items.map((t,i)=>(<div key={i} onClick={()=>onOpen&&t.complex_name&&onOpen(t)}
      style={{display:"flex",alignItems:"baseline",gap:10,padding:"3px 14px 3px 0",cursor:onOpen?"pointer":"default",fontSize:12.5}}>
     <span className="num" style={{color:MUTED,minWidth:52}}>{t.contract_date?t.contract_date.slice(2).replace(/-/g,"."):"—"}</span>
     <span className="num" style={{color:MUTED}}>{t.floor?`${t.floor}층`:"—"}</span>
     <span className="num" style={{marginLeft:"auto",fontWeight:700}}>{unit==="ppm"?pyeong(t.pyeong_unit):eok(t.deal_amount)}</span>
    </div>))}
   </div>}
  </div>);
 });
}
function RankMovers({rows}){
 if(!rows.length)return <Empty>2개월 이상 거래된 단지가 적어 등락 표본이 부족합니다.</Empty>;
 return rows.map(r=>(<div key={r.rank} className="listrow">
  <span className={"rankno "+(r.rank<=3?"top":"")}>{r.rank}</span>
  <div style={{minWidth:0}}><div style={{fontWeight:600}}>{r.complex_name}</div>
   <div style={{fontSize:12,color:MUTED}}>{guOf(r.gu)} · {won(r.prev_amount)}→{won(r.latest_amount)}</div></div>
  <span style={{marginLeft:"auto"}}><ChangeChip pct={r.change_pct} dir={r.direction}/></span>
 </div>));
}
function RankHigh({rows}){
 if(!rows.length)return <Empty>신고가 판정에 필요한 표본(2개월 이상)이 부족합니다.</Empty>;
 return rows.map((r,i)=>(<div key={i} className="listrow">
  <span className="rankno top">↑</span>
  <div style={{minWidth:0}}><div style={{fontWeight:600}}>{r.complex_name}</div>
   <div style={{fontSize:12,color:MUTED}}>{guOf(r.gu)} · {r.area_label} · 직전최고 {eok(r.prev_high)}</div></div>
  <div style={{marginLeft:"auto",textAlign:"right"}}><div className="num" style={{fontWeight:800}}>{eok(r.latest_amount)}</div>
   <div className="num" style={{fontSize:12,color:UP,fontWeight:700}}>+{r.change_pct}%</div></div>
 </div>));
}
function RankLow({rows}){
 if(!rows.length)return <Empty>신저가 판정에 필요한 표본(2개월 이상)이 부족합니다.</Empty>;
 return rows.map((r,i)=>(<div key={i} className="listrow">
  <span className="rankno" style={{background:DOWN,color:"#fff"}}>↓</span>
  <div style={{minWidth:0}}><div style={{fontWeight:600}}>{r.complex_name}</div>
   <div style={{fontSize:12,color:MUTED}}>{guOf(r.gu)} · {r.area_label} · 직전최저 {eok(r.prev_low)}</div></div>
  <div style={{marginLeft:"auto",textAlign:"right"}}><div className="num" style={{fontWeight:800}}>{eok(r.latest_amount)}</div>
   <div className="num" style={{fontSize:12,color:DOWN,fontWeight:700}}>{r.change_pct}%</div></div>
 </div>));
}
function RankActive({rows}){
 return rows.map(r=>(<div key={r.code} className="listrow">
  <span className={"rankno "+(r.rank<=3?"top":"")}>{r.rank}</span>
  <span style={{fontWeight:600}}>{guOf(r.name)}</span>
  <span style={{marginLeft:"auto",color:MUTED}} className="num">최근 {r.recent_count}건 · 누적 {r.total_count}건</span>
 </div>));
}

/* ---------------- 시세(검색) ---------------- */
/* 가격 분포 히스토그램 (현재 필터된 거래 기준) */
function priceBins(rows,deal){
 const eff=deal==="전체"?"trade":deal;
 const basis=eff==="jeonse"?"deposit":eff==="wolse"?"monthly_rent":"deal_amount";
 const vals=rows.map(r=>r[basis]).filter(v=>v&&v>0).sort((a,b)=>a-b);
 if(vals.length<8) return null;
 const lo=vals[0],hi=vals[vals.length-1];
 const cands=eff==="wolse"?[10,20,50,100,200]:[2500,5000,10000,20000,50000,100000];
 let w=cands[cands.length-1];
 for(const c of cands){if((hi-lo)/c<=12){w=c;break;}}
 const start=Math.floor(lo/w)*w,bins=[];
 for(let e=start;e<=hi;e+=w){const n=e+w;
  bins.push({lo:e,hi:n,count:vals.filter(v=>v>=e&&(v<n||(n>hi&&v===hi))).length});}
 const pct=p=>{const k=(vals.length-1)*p,f=Math.floor(k);
  return f>=vals.length-1?vals[vals.length-1]:Math.round(vals[f]*(1-(k-f))+vals[f+1]*(k-f));};
 return {bins,median:pct(.5),p25:pct(.25),p75:pct(.75),count:vals.length,width:w,lo,hi,eff};
}
function Histogram({rows,deal,bare}){
 const d=priceBins(rows,deal);
 const isWolse=(deal==="wolse");
 const basisLabel=deal==="jeonse"?"전세 보증금":deal==="wolse"?"월세":"매매가";
 const fmt=v=>isWolse?`${v}만`:eok(v);
 const wrap=inner=>bare?<div style={{padding:"6px 0 2px"}}>{inner}</div>:<div className="card" style={{padding:"12px 14px",marginTop:12}}>{inner}</div>;
 if(!d) return wrap(<React.Fragment>
   <div style={{fontWeight:700,marginBottom:2}}>가격 분포 <span style={{fontSize:11.5,color:MUTED,fontWeight:600}}>· {basisLabel}</span></div>
   <div style={{fontSize:12.5,color:MUTED}}>표본 부족(8건 이상일 때 표시).</div></React.Fragment>);
 const max=Math.max(...d.bins.map(b=>b.count))||1;
 const inMed=b=>d.median>=b.lo&&d.median<b.hi;
 return wrap(<React.Fragment>
  <div style={{display:"flex",alignItems:"baseline",gap:8,flexWrap:"wrap"}}>
   <div style={{fontWeight:700}}>가격 분포</div>
   <span style={{fontSize:11.5,color:MUTED,fontWeight:600}}>{basisLabel} · {d.count}건</span>
   <span className="num" style={{marginLeft:"auto",fontSize:12,color:MUTED}}>중앙값 <b style={{color:INK}}>{fmt(d.median)}</b></span>
  </div>
  <div style={{display:"flex",alignItems:"flex-end",gap:3,height:84,marginTop:10}}>
   {d.bins.map((b,i)=>(<div key={i} title={`${fmt(b.lo)}~${fmt(b.hi)} · ${b.count}건`}
     style={{flex:1,display:"flex",flexDirection:"column",justifyContent:"flex-end",alignItems:"center",minWidth:0}}>
    <div style={{fontSize:9.5,color:MUTED,marginBottom:2}}>{b.count||""}</div>
    <div style={{width:"100%",borderRadius:"4px 4px 0 0",background:inMed(b)?TEAL:"rgba(15,118,110,.32)",height:Math.max(3,Math.round(b.count/max*64))}}/>
   </div>))}
  </div>
  <div className="num" style={{display:"flex",justifyContent:"space-between",fontSize:10.5,color:MUTED,marginTop:4}}>
   <span>{fmt(d.lo)}</span><span>중앙 {fmt(d.median)}</span><span>{fmt(d.hi)}</span></div>
  <div style={{fontSize:11.5,color:MUTED,marginTop:6}}>가운데 50%({fmt(d.p25)}~{fmt(d.p75)}). 막대=거래건수.</div>
 </React.Fragment>);
}
/* 공통 접기/펼치기 카드 */
function Collapsible({title,icon,right,defaultOpen,children}){
 const [open,setOpen]=useState(defaultOpen!==false);
 return (<div className="card" style={{marginTop:12,overflow:"hidden",padding:0}}>
  <div tabIndex={0} role="button" onKeyDown={onEnter(()=>setOpen(o=>!o))} onClick={()=>setOpen(o=>!o)} style={{display:"flex",alignItems:"center",gap:7,padding:"12px 14px",cursor:"pointer",userSelect:"none"}}>
   {icon&&<Icon name={icon} active size={18}/>}
   <span style={{fontWeight:800,fontSize:15}}>{title}</span>
   {right}
   <span style={{marginLeft:"auto",color:MUTED,fontSize:13,transition:"transform .15s",transform:open?"rotate(180deg)":"none"}}>▾</span>
  </div>
  {open&&<div className="collapse-body">{children}</div>}
 </div>);
}
/* 시세: 거래유형별(매매/전세/월세) 섹션 — 10개씩 페이징 */
function TxRow({t,deal,onOpen,unit,compact}){
 const color=deal==="trade"?TEAL:deal==="jeonse"?"#1E5FC4":"#9A6B00";
 const isTrade=t.deal_type==="trade";
 const amt=isTrade?eok(t.deal_amount):t.deal_type==="jeonse"?`보증 ${eok(t.deposit)}`:`${eok(t.deposit)}/월${t.monthly_rent}`;
 const pp=(isTrade&&t.deal_amount&&t.exclusive_area)?Math.round(t.deal_amount/(t.exclusive_area/PY)):null;
 const cd=t.contract_date?t.contract_date.slice(2).replace(/-/g,"."):"—";
 const clickable=onOpen&&t.complex_name;
 const meta=[fmtArea(t.exclusive_area,unit),t.floor!=null?`${t.floor}층`:null,cd].filter(Boolean).join(" · ");
 return (<div tabIndex={clickable?0:undefined} role={clickable?"button":undefined} onKeyDown={clickable?onEnter(()=>onOpen(t)):undefined} className="txrow" onClick={clickable?()=>onOpen(t):undefined} style={clickable?undefined:{cursor:"default"}}>
  <div style={{minWidth:0,flex:1}}>
   {compact?<div className="num" style={{fontSize:12.5}}>{meta}</div>
    :<React.Fragment>
     <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
      <span style={{fontWeight:700,overflowWrap:"anywhere"}}>{t.complex_name||<span style={{color:MUTED}}>단독·다가구</span>}</span>
      <span className="pill" style={{background:"var(--hd)",color:MUTED,fontWeight:700}}>{TYPE_LABEL[t.property_type]}</span>
      {t.is_sample&&<span className="pill ex">모의</span>}
     </div>
     <div className="num" style={{color:MUTED,fontSize:12,marginTop:2}}>{[t.dong,meta].filter(Boolean).join(" · ")}</div>
    </React.Fragment>}
  </div>
  <div style={{textAlign:"right",flex:"none"}}>
   <div className="num" style={{fontWeight:800,color:color,fontSize:14.5}}>{amt}</div>
   {pp&&<div className="num" style={{fontSize:11,color:MUTED,marginTop:1}}>{pp.toLocaleString("ko-KR")}/평</div>}
  </div>
 </div>);
}
function ComplexGroup({g,deal,onOpen,unit}){
 const [open,setOpen]=useState(false);
 const color=deal==="trade"?TEAL:deal==="jeonse"?"#1E5FC4":"#9A6B00";
 const isTrade=deal==="trade";
 const repTxt=isTrade?eok(g.rep):deal==="jeonse"?`보증 ${eok(g.rep)}`:`${eok(g.rep)}/월`;
 return (<div style={{borderTop:"1px solid rgba(99,120,128,.08)"}}>
  <div className="txrow" tabIndex={0} role="button" onKeyDown={onEnter(()=>setOpen(o=>!o))} onClick={()=>setOpen(o=>!o)} style={{cursor:"pointer"}}>
   <div style={{minWidth:0,flex:1}}>
    <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
     <span style={{fontWeight:700,overflowWrap:"anywhere"}}>{g.complex_name}</span>
     <span className="num" style={{fontSize:11.5,color:MUTED}}>{g.count}건</span>
     {g.is_sample&&<span className="pill ex">모의</span>}
    </div>
    <div className="num" style={{color:MUTED,fontSize:12,marginTop:2}}>{[g.dong,g.ppm!=null?`평단가 ${g.ppm.toLocaleString("ko-KR")}`:null].filter(Boolean).join(" · ")}</div>
   </div>
   <div style={{textAlign:"right",flex:"none",display:"flex",alignItems:"center",gap:7}}>
    <div>
     <div className="num" style={{fontWeight:800,color,fontSize:14.5}}>{repTxt}</div>
     <div className="num" style={{fontSize:10,color:MUTED}}>대표가·중앙</div>
    </div>
    <span style={{color:MUTED,fontSize:16,flex:"none",transform:open?"rotate(90deg)":"none",transition:"transform .2s"}}>›</span>
   </div>
  </div>
  {open&&<div style={{background:"rgba(99,120,128,.035)"}}>
   <MoreList items={g.items} initial={10} step={10} render={(t,i)=><TxRow key={i} t={t} deal={deal} onOpen={onOpen} unit={unit} compact/>}/>
   {onOpen&&<div onClick={()=>onOpen({complex_name:g.complex_name,lawd_cd:g.items[0].lawd_cd,property_type:g.items[0].property_type,dong:g.dong})} style={{textAlign:"center",padding:"9px",fontSize:12,color:TEAL,fontWeight:700,cursor:"pointer"}}>단지 상세 보기 ›</div>}
  </div>}
 </div>);
}
function BandList({rows,deal,onOpen,unit,label,sort}){
 const [page,setPage]=useState(1);
 const PER=8;
 useEffect(()=>{setPage(1);},[rows]);
 const color=deal==="trade"?TEAL:deal==="jeonse"?"#1E5FC4":"#9A6B00";
 if(!rows.length) return null;   // 빈 면적대는 숨김(가독성)
 const ppmOf=t=>(t.deal_amount&&t.exclusive_area)?Math.round(t.deal_amount/(t.exclusive_area/PY)):null;
 const repVal=t=>deal==="trade"?t.deal_amount:t.deposit;
 const med=a=>{const s=a.filter(v=>v!=null).sort((x,y)=>x-y);return s.length?s[Math.floor((s.length-1)/2)]:null;};
 const gmap={},singles=[];
 rows.forEach(r=>{
  if(!r.complex_name){singles.push(r);return;}
  const g=gmap[r.complex_name]=gmap[r.complex_name]||{complex_name:r.complex_name,dong:r.dong,is_sample:false,items:[]};
  g.items.push(r); if(r.is_sample)g.is_sample=true;
 });
 const groups=Object.values(gmap).map(g=>{
  g.items.sort((a,b)=>(b.contract_date||"").localeCompare(a.contract_date||""));
  g.count=g.items.length; g.rep=med(g.items.map(repVal));
  const pp=g.items.map(ppmOf).filter(v=>v!=null); g.ppm=pp.length?med(pp):null;
  return g;
 });
 const latestOf=g=>(g.items[0]&&g.items[0].contract_date)||"";
 groups.sort((a,b)=>sort==="ppm"?((b.ppm||0)-(a.ppm||0)):sort==="date"?latestOf(b).localeCompare(latestOf(a)):((b.rep||0)-(a.rep||0)));
 const allPpm=rows.map(ppmOf).filter(v=>v!=null).sort((x,y)=>x-y);
 const ppmMed=deal==="trade"&&allPpm.length?allPpm[Math.floor(allPpm.length/2)]:null;
 const units=[...groups,...singles.map(s=>({single:true,row:s}))];
 const paged=units.slice((page-1)*PER,page*PER);
 return (<div className="card" style={{padding:0,marginBottom:11,overflow:"hidden"}}>
  <div style={{display:"flex",alignItems:"center",gap:8,padding:"10px 14px",borderBottom:"1px solid rgba(99,120,128,.1)",background:"rgba(99,120,128,.035)"}}>
   <span style={{width:7,height:7,borderRadius:7,background:color,flex:"none"}}/>
   <span style={{fontWeight:800,fontSize:13.5}}>{label}</span>
   <span className="num" style={{fontSize:11.5,color:MUTED}}>{groups.length+singles.length}개 단지 · {rows.length}건</span>
   {ppmMed!=null&&<span className="num" style={{marginLeft:"auto",fontSize:11.5,color:MUTED,display:"inline-flex",alignItems:"center"}}>평단가 중앙 {ppmMed.toLocaleString("ko-KR")}<Info text="전용 1평(3.3㎡)당 가격(만원). 면적이 다른 단지·평형을 비교할 때 씁니다."/></span>}
  </div>
  <div>{paged.map((u,i)=>u.single
    ?<TxRow key={"s"+i} t={u.row} deal={deal} onOpen={onOpen} unit={unit}/>
    :<ComplexGroup key={u.complex_name} g={u} deal={deal} onOpen={onOpen} unit={unit}/>)}</div>
  {units.length>PER&&<div style={{padding:"6px 12px 8px"}}><Pager page={page} setPage={setPage} total={units.length} per={PER}/></div>}
 </div>);
}
function DealSection({rows,deal,onOpen,unit,sort,defaultOpen}){
 const BANDS3=[["small","소형 (~60㎡)"],["medium","중형 (60~85㎡)"],["large","대형 (85㎡~)"],["na","면적 미상"]];
 const bandOf=a=>a==null?"na":(a<60?"small":a<85?"medium":"large");
 const color=deal==="trade"?TEAL:deal==="jeonse"?"#1E5FC4":"#9A6B00";
 return (<Collapsible defaultOpen={defaultOpen}
   title={<span style={{color}}>{DEAL_LABEL[deal]}</span>}
   right={<span className="num" style={{fontSize:12,color:MUTED}}>{rows.length}건</span>}>
  {rows.length?<div style={{padding:"8px 0 6px"}}>
   {BANDS3.map(([k,label])=><BandList key={k} label={label} deal={deal} onOpen={onOpen} unit={unit} sort={sort}
     rows={rows.filter(r=>bandOf(r.exclusive_area)===k)}/>)}
  </div>:<div style={{padding:"4px 14px 12px"}}><Empty>해당 거래가 없습니다.</Empty></div>}
 </Collapsible>);
}
function demoOverview(code,ptype,band){
 const _band=a=>a==null?"na":(a<60?"small":a<85?"medium":"large");
 const med=a=>{const s=a.filter(v=>v!=null).sort((x,y)=>x-y);return s.length?s[Math.floor((s.length-1)/2)]:null;};
 const inScope=t=>(!code||String(t.lawd_cd)===String(code))&&(ptype==="all"||ptype==="전체"||t.property_type===ptype)&&(band==="all"||_band(t.exclusive_area)===band);
 const rows=DEMO_TX.filter(t=>!t.is_canceled&&t.complex_name&&inScope(t));
 const trades=rows.filter(t=>t.deal_type==="trade"&&t.deal_amount);
 const jeon=rows.filter(t=>t.deal_type==="jeonse"&&t.deposit).map(t=>t.deposit);
 const mtr=med(trades.map(t=>t.deal_amount)), mje=med(jeon);
 const mm={}; trades.forEach(t=>{const k=(t.contract_date||"").slice(0,7);if(k)(mm[k]=mm[k]||[]).push(t.deal_amount);});
 const keys=Object.keys(mm).sort(); let dM=null;
 if(keys.length>=2){const a=med(mm[keys[keys.length-1]]),b=med(mm[keys[keys.length-2]]);if(a&&b)dM=Math.round((a-b)/b*1000)/10;}
 const g={}; trades.forEach(t=>{const k=t.complex_name+"__"+t.lawd_cd;
   if(!g[k])g[k]={name:t.complex_name,lawd_cd:t.lawd_cd,gu:GU_NAME[t.lawd_cd],dong:t.dong,property_type:t.property_type,amts:[],last:""};
   g[k].amts.push(t.deal_amount); const dt=t.contract_date||"";if(dt>g[k].last)g[k].last=dt; if(!g[k].dong&&t.dong)g[k].dong=t.dong;});
 const complexes=Object.values(g).map(o=>({name:o.name,lawd_cd:o.lawd_cd,gu:o.gu,dong:o.dong,property_type:o.property_type,median:med(o.amts),count:o.amts.length,last_date:o.last||null,contains_sample_data:true})).sort((a,b)=>(b.count-a.count)||(b.median-a.median));
 return {gu:code?GU_NAME[code]:null,property_type:ptype,summary:{median:mtr,ratio:(mtr&&mje)?Math.round(mje/mtr*100):null,count:trades.length,dM},complexes};
}
function PriceHub({view,setView,tx,onOpen,initialGu,d,mapCfg,onGu,favs,demo}){
 const V=view==="map"?"map":"list";
 const [gu,setGu]=useState(initialGu||"전체");
 useEffect(()=>{if(initialGu)setGu(initialGu);},[initialGu]);
 const [ptype,setPtype]=useState("apartment");
 const [q,setQ]=useState("");
 const [band,setBand]=useState("all");
 const [sort,setSort]=useState("volume");
 const [more,setMore]=useState(false);
 const lawdFor=g=>({"상당구":"43111","서원구":"43112","흥덕구":"43113","청원구":"43114"}[g]||"");
 const [ov,setOv]=useState(null);
 const [ovLoading,setOvLoading]=useState(false);
 useEffect(()=>{let on=true;
  const code=lawdFor(gu);
  if(demo){setOv(demoOverview(code,ptype,band));setOvLoading(false);return ()=>{on=false;};}
  setOvLoading(true);
  const ctrl=new AbortController(); const tmr=setTimeout(()=>ctrl.abort(),4000);
  const qs=`property_type=${ptype}&band=${band}`+(code?`&lawd_cd=${code}`:"");
  fetch(`${API}/price/overview?${qs}`,{signal:ctrl.signal}).then(r=>r.json())
   .then(j=>{if(!on)return;clearTimeout(tmr);setOv(j&&j.summary?j:demoOverview(code,ptype,band));setOvLoading(false);})
   .catch(()=>{if(!on)return;clearTimeout(tmr);setOv(demoOverview(code,ptype,band));setOvLoading(false);});
  return ()=>{on=false;clearTimeout(tmr);};
 },[gu,ptype,band,demo]);
 const summary=(ov&&ov.summary)||{};
 const complexes=useMemo(()=>{
  let arr=[...((ov&&ov.complexes)||[])];
  const qq=q.trim();
  if(qq)arr=arr.filter(o=>(o.name&&o.name.includes(qq))||(o.dong&&o.dong.includes(qq)));
  arr.sort((a,b)=>sort==="price"?(b.median-a.median):sort==="recent"?((b.last_date||"").localeCompare(a.last_date||"")):((b.count-a.count)||(b.median-a.median)));
  return arr;
 },[ov,q,sort]);
 const GUS=[["전체","전체"],["상당구","상당"],["서원구","서원"],["흥덕구","흥덕"],["청원구","청원"]];
 const SORTS=[["volume","거래 많은 순"],["price","가격 높은 순"],["recent","최신순"]];
 const BANDS=[["all","전체"],["small","소형"],["medium","중형"],["large","대형"]];
 const guLabel=gu==="전체"?"청주시 전체":gu;
 const segChip=active=>({border:"none",cursor:"pointer",fontWeight:800,fontSize:13,padding:"9px 0",borderRadius:8,flex:1,minHeight:38,background:active?"var(--surface-solid)":"transparent",color:active?TEAL:MUTED,boxShadow:active?"0 1px 4px rgba(30,64,90,.12)":"none"});
 return (<div style={{marginTop:6}}>
  <div className="seg" style={{display:"flex",gap:4,background:"var(--chip)",borderRadius:11,padding:4,marginBottom:10}}>
   {[["list","리스트"],["map","지도"]].map(([k,l])=><button key={k} onClick={()=>{setView(k);window.scrollTo(0,0);}} style={segChip(V===k)}>{l}</button>)}
  </div>
  {V==="map"?<div>
   <div className="card" style={{padding:"9px 12px",marginBottom:10,display:"flex",alignItems:"center",gap:8}}>
    <span style={{fontSize:12,color:MUTED,fontWeight:700}}>유형</span>
    <select className="sel" style={{maxWidth:150}} value={ptype} onChange={e=>setPtype(e.target.value)}>
     <option value="전체">전체 유형</option>
     {Object.entries(TYPE_LABEL).map(([v,l])=><option key={v} value={v}>{l}</option>)}
    </select>
    {ptype==="전체"&&<span style={{fontSize:11,color:MUTED}}>지도는 아파트 기준</span>}
   </div>
   <HeatTab ptype={ptype} mapCfg={mapCfg} onOpen={onOpen} onGu={onGu}/>
  </div>:<div>
   <div className="seg" style={{display:"flex",gap:3,background:"var(--chip)",borderRadius:10,padding:3,marginBottom:10}}>
    {GUS.map(([v,l])=><button key={v} onClick={()=>setGu&&setGu(v)} style={segChip(gu===v)}>{l}</button>)}
   </div>
   <div className="card" style={{padding:"14px 15px"}}>
    <div style={{fontSize:12.5,color:MUTED}}>{guLabel} <span style={{fontSize:10.5}}>· {TYPE_LABEL[ptype]||"전체"} · 최근 {AGG_MONTHS}개월</span></div>
    <div style={{display:"flex",alignItems:"flex-end",gap:14,flexWrap:"wrap",marginTop:6}}>
     <div><div style={{fontSize:11,color:MUTED,display:"inline-flex",alignItems:"center",gap:3}}>평균 매매(중앙)<Info text={`선택 지역·유형의 최근 ${AGG_MONTHS}개월 매매 실거래가 중앙값입니다. 평균이 아닌 중앙값이라 초고가·초저가 이상치에 덜 흔들려요. 자료: 국토교통부 실거래가(참고용, 법적 효력 없음).`}/></div><div className="num" style={{fontSize:23,fontWeight:800,lineHeight:1.1}}>{summary.median!=null?eok(summary.median):"—"}</div>{summary.dM!=null&&<div style={{fontSize:11,marginTop:1}}>전월 <Delta v={summary.dM}/></div>}</div>
     <div style={{marginLeft:"auto",textAlign:"right"}}><div style={{fontSize:11,color:MUTED,display:"inline-flex",alignItems:"center",gap:3}}>전세가율<Info text={`전세 보증금 중앙값 ÷ 매매가 중앙값 × 100(근사). 최근 ${AGG_MONTHS}개월 실거래 기준. 높을수록 매매가 대비 보증금 비중이 커, 시세 하락 시 보증금 회수가 어려워질 수 있어요.`}/></div><div className="num" style={{fontSize:17,fontWeight:800,color:TEAL}}>{summary.ratio!=null?summary.ratio+"%":"—"}</div><div className="num" style={{fontSize:11,color:MUTED,marginTop:2}}>거래 {summary.count}건</div></div>
    </div>
   </div>
   <div style={{display:"flex",alignItems:"center",gap:7,background:"var(--chip)",borderRadius:10,padding:"9px 12px",marginTop:10}}>
    <span style={{color:MUTED,fontSize:14}}>🔎</span>
    <input value={q} onChange={e=>setQ(e.target.value)} placeholder={guLabel+" 단지·동 검색"} style={{flex:1,border:"none",background:"transparent",outline:"none",fontSize:13.5,color:"var(--ink)",minWidth:0}}/>
    {q&&<span aria-label="검색어 지우기" role="button" tabIndex={0} onKeyDown={onEnter(()=>setQ(""))} style={{cursor:"pointer",color:MUTED,fontWeight:700,fontSize:15}} onClick={()=>setQ("")}>×</span>}
   </div>
   <div style={{display:"flex",alignItems:"center",marginTop:10,marginBottom:2}}>
    <span style={{fontSize:13,fontWeight:800}}>단지 {complexes.length}곳{ovLoading&&<span style={{fontSize:11,fontWeight:600,color:MUTED,marginLeft:6}}>불러오는 중…</span>}</span>
    <select className="sel" style={{marginLeft:"auto",maxWidth:140,fontSize:12.5}} value={sort} onChange={e=>setSort(e.target.value)}>
     {SORTS.map(([v,l])=><option key={v} value={v}>{l}</option>)}
    </select>
    <button onClick={()=>setMore(m=>!m)} style={{marginLeft:8,border:"1px solid var(--line)",background:"var(--surface-2)",color:more?TEAL:MUTED,fontWeight:700,fontSize:12,borderRadius:8,padding:"6px 10px",cursor:"pointer"}}>상세 {more?"▲":"▼"}</button>
   </div>
   {more&&<div className="card" style={{padding:"11px 13px",marginTop:8}}>
    <div style={{display:"flex",gap:8,alignItems:"center"}}>
     <span style={{fontSize:11.5,color:MUTED,fontWeight:700,width:28,flex:"none"}}>유형</span>
     <select className="sel" style={{flex:1}} value={ptype} onChange={e=>setPtype(e.target.value)}>
      <option value="전체">전체 유형</option>
      {Object.entries(TYPE_LABEL).map(([v,l])=><option key={v} value={v}>{l}</option>)}
     </select>
    </div>
    <div style={{display:"flex",alignItems:"center",gap:10,marginTop:9}}>
     <span style={{fontSize:11.5,color:MUTED,fontWeight:700,width:28,flex:"none"}}>평형</span>
     <div style={{display:"flex",gap:3,background:"var(--chip)",borderRadius:9,padding:3,flex:1}}>
      {BANDS.map(([k,l])=><button key={k} onClick={()=>setBand(k)} style={{flex:1,border:"none",cursor:"pointer",fontWeight:700,fontSize:12,padding:"7px 0",borderRadius:7,background:band===k?"var(--surface-solid)":"transparent",color:band===k?TEAL:MUTED}}>{l}</button>)}
     </div>
    </div>
   </div>}
   <div style={{marginTop:8}}>
    {ovLoading&&!complexes.length?<SkeletonList rows={6}/>:complexes.length?<MoreList items={complexes} initial={12} step={12} render={(c,i)=>(<div key={i} className="txrow" style={{cursor:"pointer"}} tabIndex={0} role="button" onKeyDown={onEnter(()=>onOpen&&onOpen({complex_name:c.name,lawd_cd:c.lawd_cd,property_type:c.property_type,gu:c.gu,dong:c.dong}))} onClick={()=>onOpen&&onOpen({complex_name:c.name,lawd_cd:c.lawd_cd,property_type:c.property_type,gu:c.gu,dong:c.dong})}>
     <div style={{minWidth:0,flex:1}}>
      <div style={{fontWeight:700,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{c.name} {c.contains_sample_data&&<ExBadge/>}</div>
      <div style={{fontSize:12,color:MUTED,marginTop:1}}>{[(c.gu||"").replace("청주시 ",""),c.dong,TYPE_LABEL[c.property_type]].filter(Boolean).join(" · ")}</div>
     </div>
     <div style={{textAlign:"right",flex:"none"}}>
      <div className="num" style={{fontWeight:800,fontSize:14}}>{eok(c.median)}</div>
      <div className="num" style={{fontSize:11,color:MUTED,marginTop:1}}>거래 {c.count}건</div>
     </div>
    </div>)}/>:<div className="card" style={{padding:18,marginTop:4}}><Empty action={q?<button onClick={()=>setQ("")} style={{border:"1px solid var(--line)",background:"var(--surface-2)",color:INK,fontWeight:700,fontSize:13,padding:"9px 16px",borderRadius:10,cursor:"pointer"}}>검색 지우기</button>:null}>{q?"검색 결과가 없어요.":"이 조건의 거래가 아직 없어요. 구·유형을 바꿔보세요."}</Empty></div>}
   </div>
   <div style={{fontSize:10.5,color:MUTED,margin:"12px 2px 0",lineHeight:1.6}}>자료: 국토교통부 실거래가(참고용·법적 효력 없음). 대표 시세=최근 {AGG_MONTHS}개월 매매 실거래 중앙값, 평단가=거래금액÷(전용면적÷3.3058), 전세가율=전세보증금 중앙값÷매매가 중앙값. 신고 지연·정정·해제로 값이 바뀔 수 있어요. 단지를 누르면 평형별 상세·적정가 체크를 볼 수 있습니다.</div>
  </div>}
 </div>);
}
function Price({ptype,onTypeChange,gu,setGu,tx,onOpen,favs}){
 const unit=useUnit();
 const [sort,setSort]=useState("price");   // price | ppm | date
 const [q,setQ]=useState("");
 const [band,setBand]=useState("all");      // all | small | medium | large
 const [favOnly,setFavOnly]=useState(false);
 const type=ptype||"전체";
 const favSet=useMemo(()=>new Set((favs||[]).filter(f=>f.target_type!=="region")
   .map(f=>`${f.name}__${(f.meta&&f.meta.lawd_cd)||""}`)),[favs]);
 const bandOf=a=>a==null?"na":(a<60?"small":a<85?"medium":"large");
 const ppmOf=t=>(t.deal_amount&&t.exclusive_area)?t.deal_amount/(t.exclusive_area/PY):0;
 const pkey=t=>t.deal_amount||t.deposit||0;
 const qq=q.trim();
 const base=useMemo(()=>tx.filter(t=>
    !t.is_canceled&&
    (gu==="전체"||GU_NAME[t.lawd_cd]===gu)&&
    (type==="전체"||t.property_type===type)&&
    (band==="all"||bandOf(t.exclusive_area)===band)&&
    (!favOnly||favSet.has(`${t.complex_name}__${t.lawd_cd}`))&&
    (!qq||(t.complex_name&&t.complex_name.includes(qq))||(t.dong&&t.dong.includes(qq))))
  .sort((a,b)=>sort==="price"?(pkey(b)-pkey(a)):sort==="ppm"?(ppmOf(b)-ppmOf(a)):(b.contract_date||"").localeCompare(a.contract_date||"")),
  [tx,gu,type,band,favOnly,favSet,qq,sort]);
 const byDeal=d=>base.filter(t=>t.deal_type===d);
 const BANDS=[["all","전체"],["small","소형"],["medium","중형"],["large","대형"]];
 const SORTS=[["price","가격순"],["ppm","평단가순"],["date","최신순"]];
 const segBtn=(active)=>({flex:1,border:"none",cursor:"pointer",fontWeight:700,fontSize:12,padding:"7px 0",borderRadius:7,minHeight:32,background:active?"var(--surface-solid)":"transparent",color:active?TEAL:MUTED,boxShadow:active?"0 1px 3px rgba(30,64,90,.12)":"none"});
 const reset=()=>{setQ("");setBand("all");setSort("price");setFavOnly(false);setGu&&setGu("전체");onTypeChange&&onTypeChange("apartment");};
 const active=(gu!=="전체")+(type!=="apartment"&&type!=="전체")+(band!=="all")+(qq?1:0)+(favOnly?1:0);
 return (<div style={{marginTop:6}}>
  <div className="card sticky-filter" style={{padding:13}}>
   {/* 검색 */}
   <div style={{display:"flex",alignItems:"center",gap:7,background:"var(--chip)",borderRadius:10,padding:"9px 12px"}}>
    <span style={{color:MUTED,fontSize:14}}>🔎</span>
    <input value={q} onChange={e=>setQ(e.target.value)} placeholder="단지·동 이름으로 검색"
      style={{flex:1,border:"none",background:"transparent",outline:"none",fontSize:13.5,color:"var(--ink)",minWidth:0}}/>
    {q&&<span aria-label="검색어 지우기" role="button" tabIndex={0} onKeyDown={onEnter(()=>setQ(""))} style={{cursor:"pointer",color:MUTED,fontWeight:700,fontSize:15}} onClick={()=>setQ("")}>×</span>}
   </div>
   {/* 유형 · 구 */}
   <div style={{display:"flex",gap:8,marginTop:9}}>
    <select className="sel" style={{flex:1,minWidth:0}} value={type} onChange={e=>onTypeChange&&onTypeChange(e.target.value)}>
     <option value="전체">전체 유형</option>
     {Object.entries(TYPE_LABEL).map(([v,l])=><option key={v} value={v}>{l}</option>)}
    </select>
    <select className="sel" style={{flex:1,minWidth:0}} value={gu} onChange={e=>setGu&&setGu(e.target.value)}>
     <option value="전체">전체 구</option>
     {Object.values(GU_NAME).map(n=><option key={n} value={n}>{n}</option>)}
    </select>
   </div>
   {/* 평형 */}
   <div style={{display:"flex",alignItems:"center",gap:10,marginTop:10}}>
    <span style={{fontSize:11.5,color:MUTED,fontWeight:700,width:28,flex:"none"}}>평형</span>
    <div style={{display:"flex",gap:3,background:"var(--chip)",borderRadius:9,padding:3,flex:1}}>
     {BANDS.map(([k,l])=><button key={k} onClick={()=>setBand(k)} style={segBtn(band===k)}>{l}</button>)}
    </div>
   </div>
   {/* 정렬 */}
   <div style={{display:"flex",alignItems:"center",gap:10,marginTop:8}}>
    <span style={{fontSize:11.5,color:MUTED,fontWeight:700,width:28,flex:"none"}}>정렬</span>
    <div style={{display:"flex",gap:3,background:"var(--chip)",borderRadius:9,padding:3,flex:1}}>
     {SORTS.map(([k,l])=><button key={k} onClick={()=>setSort(k)} style={segBtn(sort===k)}>{l}</button>)}
    </div>
   </div>
   {/* 결과 + 관심만 + 초기화 */}
   <div style={{display:"flex",alignItems:"center",gap:8,marginTop:11}}>
    <span className="num" style={{fontSize:12.5,color:MUTED}}>총 <b style={{color:"var(--ink)"}}>{base.length.toLocaleString("ko-KR")}</b>건</span>
    {active>0&&<button onClick={reset} style={{border:"none",background:"none",color:MUTED,fontSize:11.5,fontWeight:700,cursor:"pointer",textDecoration:"underline",padding:0}}>초기화</button>}
    {favSet.size>0&&<button className={"tog "+(favOnly?"on":"")} style={{marginLeft:"auto",padding:"6px 12px",fontSize:12}} onClick={()=>setFavOnly(v=>!v)}>★ 관심만</button>}
   </div>
  </div>
  <DealSection rows={byDeal("trade")} deal="trade" onOpen={onOpen} unit={unit} sort={sort} defaultOpen={true}/>
  <DealSection rows={byDeal("jeonse")} deal="jeonse" onOpen={onOpen} unit={unit} sort={sort} defaultOpen={false}/>
  <DealSection rows={byDeal("wolse")} deal="wolse" onOpen={onOpen} unit={unit} sort={sort} defaultOpen={false}/>
 </div>);
}

/* ---------------- 대출 추천 (M4) ---------------- */
const LRULES={ltv:{base:0.70,first:0.80},dsr:0.40,rate:4.0,years:30,as_of:"2025-11",region:"비규제지역(청주)"};
const LPRODUCTS=[
 {id:"didimdol",name:"디딤돌대출",kind:"정책",rate_min:2.65,rate_max:3.95,method:"원리금균등",limit:25000,req:"무주택·소득요건",is_sample:true},
 {id:"bogeumjari",name:"보금자리론",kind:"정책",rate_min:3.70,rate_max:4.00,method:"원리금균등",limit:36000,req:"무주택·주택가격 6억↓",is_sample:true},
 {id:"bank_a",name:"은행 주택담보대출 A",kind:"은행",rate_min:3.90,rate_max:5.20,method:"원리금균등",limit:50000,req:"신용·소득 심사",is_sample:true},
 {id:"bank_b",name:"은행 주택담보대출 B",kind:"은행",rate_min:4.10,rate_max:5.60,method:"원리금/원금균등",limit:50000,req:"신용·소득 심사",is_sample:true}];
const LDISC="공시·정책 정보 기반 참고용 추정치입니다. 실제 승인·금리·한도는 개인 신용/소득과 금융회사 심사로 달라집니다. 본 서비스는 금융자문업이 아니며, 최종 상담은 금융회사·정부 콜센터로 문의하세요.";
function _pmt(P,rate,years){const i=rate/100/12,n=years*12;if(P<=0)return 0;if(i===0)return P/n;return P*i/(1-(1+i)**(-n));}
function _prin(M,rate,years){const i=rate/100/12,n=years*12;if(M<=0)return 0;if(i===0)return M*n;return M*(1-(1+i)**(-n))/i;}
const CRULES={broker:[[5000,0.006,25],[20000,0.005,80],[90000,0.004,null],[120000,0.005,null],[150000,0.006,null],[Infinity,0.007,null]],ftCredit:200,farm:0.002,edu:0.10,beopmu:50};
function _acqRate(p){const e=p/10000;if(e<=6)return 0.01;if(e<=9)return (e*2/3-3)/100;return 0.03;}
function _brokerFee(p){for(const [cap,rate,lim] of CRULES.broker){if(p<cap){let f=p*rate;if(lim!=null)f=Math.min(f,lim);return Math.round(f);}}return 0;}
function purchaseCosts(p,over85,first){const ar=_acqRate(p),acq=p*ar;let cr=0;if(first&&p<=120000)cr=Math.min(acq,CRULES.ftCredit);
 const acqA=acq-cr,edu=acq*CRULES.edu,farm=over85?p*CRULES.farm:0,taxT=acqA+edu+farm,br=_brokerFee(p),bm=CRULES.beopmu;
 return {acq_rate:ar,acquisition_tax:Math.round(acqA),first_time_credit:Math.round(cr),edu_tax:Math.round(edu),farm_tax:Math.round(farm),over_85:over85,broker_fee:br,beopmu_estimate:bm,tax_total:Math.round(taxT),total:Math.round(taxT+br+bm)};}
function CostRow({label,val,note}){return <div className="listrow"><span>{label}{note&&<span style={{color:"#1d6b3a",fontSize:11.5,marginLeft:6}}>{note}</span>}</span><span style={{marginLeft:"auto"}} className="num">{won(val)}</span></div>;}
function loanLocal(inp){
 const rate=inp.rate??LRULES.rate,years=inp.years??LRULES.years;
 const ltvR=inp.is_first_time?LRULES.ltv.first:LRULES.ltv.base, ltv=Math.round(inp.price*ltvR);
 const simple=!inp.consent||inp.annual_income==null;
 let dsr=null;
 if(!simple){const ma=inp.annual_income*LRULES.dsr-(inp.existing||0);dsr=Math.max(0,Math.round(_prin(ma/12,rate,years)));}
 const limit=simple?ltv:Math.min(ltv,dsr),binding=(simple||limit===ltv)?"LTV":"DSR";
 const needed=Math.max(0,Math.round(inp.price-limit)),i=rate/100/12,n=years*12,m=_pmt(limit,rate,years);
 const sims=limit<=0?[]:[
  {method:"원리금균등",monthly:Math.round(m),total_interest:Math.round(m*n-limit)},
  {method:"원금균등",monthly_first:Math.round(limit/n+limit*i),monthly_last:Math.round(limit/n+(limit/n)*i),total_interest:Math.round(i*limit*(n+1)/2)},
  {method:"만기일시",monthly:Math.round(limit*i),total_interest:Math.round(limit*i*n)}];
 const prods=LPRODUCTS.map(p=>({...p,eligible:!(p.kind==="정책"&&!inp.is_no_house)}))
  .sort((a,b)=>((a.kind==="정책"&&a.eligible?0:1)-(b.kind==="정책"&&b.eligible?0:1))||(a.rate_min-b.rate_min));
 const cost=purchaseCosts(inp.price,!!inp.over_85,!!inp.is_first_time);
 const total_cash_needed=Math.round(needed+cost.total);
 const total_cash_gap=inp.self_capital==null?null:Math.max(0,Math.round(total_cash_needed-inp.self_capital));
 const aff=(simple||inp.self_capital==null||inp.annual_income==null||inp.annual_income<=0)?null:(()=>{
  const req=Math.max(0,Math.round(inp.price-inp.self_capital)), within=req<=limit, mi=inp.annual_income/12;
  const mp=_pmt(within?req:limit,rate,years), burden=mi?mp/mi:null, short=!!(total_cash_gap&&total_cash_gap>0);
  let lv,lb;
  if(!within||short){lv=4;lb="무리";}
  else if(burden==null){lv=0;lb="정보부족";}
  else if(burden<=0.25){lv=1;lb="적정";}
  else if(burden<=0.35){lv=2;lb="가능하나 빠듯";}
  else{lv=3;lb="부담 큼";}
  return {level:lv,label:lb,required_loan:req,within_limit:within,monthly_payment:Math.round(mp),
   burden_ratio:burden==null?null:Math.round(burden*1000)/10,monthly_income:Math.round(mi),
   cash_gap:total_cash_gap,reason:!within?"loan_over_limit":short?"cash_short":"ok"};
 })();
 return {mode:simple?"simple":"personalized",as_of:LRULES.as_of,region:LRULES.region,rate_pct:rate,years,
  ltv_ratio:ltvR,ltv_amount:ltv,dsr_ratio:LRULES.dsr,dsr_amount:dsr,limit,binding,
  self_capital:inp.self_capital??null,needed_cash:needed,
  cash_gap:inp.self_capital==null?null:Math.max(0,Math.round(needed-inp.self_capital)),
  costs:cost,total_cash_needed,total_cash_gap,affordability:aff,
  simulations:sims,products:prods,disclaimer:LDISC,stored:false};
}
function LegalModal({doc,onClose}){
 const [d,setD]=useState(null);
 useEffect(()=>{let on=true;setD(null);
  fetch(`${API}/legal/${doc}`).then(r=>r.ok?r.json():Promise.reject()).then(j=>{if(on)setD(j);}).catch(()=>{if(on)setD({content:"문서를 불러오지 못했습니다.",version:""});});
  return ()=>{on=false;};},[doc]);
 const render=(txt)=>(txt||"").split("\n").map((ln,i)=>{
  const clean=s=>s.replace(/\*\*/g,"");
  if(ln.startsWith("## "))return <div key={i} style={{fontWeight:800,fontSize:15,marginTop:15}}>{clean(ln.slice(3))}</div>;
  if(ln.startsWith("# "))return <div key={i} style={{fontWeight:900,fontSize:19,marginBottom:8}}>{clean(ln.slice(2))}</div>;
  if(ln.startsWith("> "))return <div key={i} style={{background:"var(--callout-bg)",color:"var(--callout-fg)",borderRadius:8,padding:"10px 12px",margin:"8px 0",fontSize:12.5,lineHeight:1.6}}>{clean(ln.replace(/^>\s*/,""))}</div>;
  if(ln.startsWith("- "))return <div key={i} style={{fontSize:13,color:INK,lineHeight:1.7,paddingLeft:10}}>· {clean(ln.slice(2))}</div>;
  if(!ln.trim())return <div key={i} style={{height:6}}/>;
  return <div key={i} style={{fontSize:13,color:INK,lineHeight:1.7}}>{clean(ln)}</div>;
 });
 return (<div onClick={onClose} style={{position:"fixed",inset:0,background:"rgba(20,30,35,.45)",zIndex:120,display:"flex",justifyContent:"center",alignItems:"flex-start",padding:"24px 12px",overflowY:"auto"}}>
  <div onClick={e=>e.stopPropagation()} style={{background:"var(--surface-solid)",width:"100%",maxWidth:480,borderRadius:14,padding:"20px 18px",maxHeight:"86vh",overflowY:"auto"}}>
   <div style={{display:"flex",alignItems:"center",marginBottom:6}}>
    <div style={{fontSize:12,color:MUTED}}>{d&&d.version?`버전 ${d.version}`:""}</div>
    <button onClick={onClose} style={{marginLeft:"auto",border:"none",background:"none",color:MUTED,fontWeight:700,cursor:"pointer"}}>닫기</button>
   </div>
   {d===null?<div style={{marginTop:10}}><SkeletonCard/><SkeletonCard/></div>:<div>{render(d.content)}</div>}
  </div>
 </div>);
}
function ConsentGate({onChoose}){
 const [showDoc,setShowDoc]=useState(null);
 const agree=()=>{
  try{fetch(`${API}/legal/consent`,{method:"POST",headers:{"Content-Type":"application/json",...authHeader()},body:JSON.stringify({device_id:deviceId(),kind:"privacy_loan"})}).catch(()=>{});}catch(_){}
  onChoose(true);
 };
 return (<div style={{marginTop:6}}>
  <div className="card" style={{padding:18}}>
   <div style={{fontWeight:800,fontSize:16}}>대출 한도 추정 — 동의 안내</div>
   <div style={{marginTop:10,background:"rgba(15,118,110,.08)",border:"1px solid rgba(15,118,110,.18)",borderRadius:10,padding:"10px 12px",fontSize:12.5,color:INK,lineHeight:1.6}}>
    <b>회원가입·신용조회 없이</b> 입력값만으로 한도를 미리 계산합니다. 신용점수는 직접 고른 <b>구간</b>만 쓰고, 신용조회 기록이 남지 않아요.
   </div>
   <div style={{fontSize:13,color:MUTED,lineHeight:1.7,marginTop:10}}>
    맞춤 추정을 위해 <b>연소득·기존 부채</b> 등을 입력받습니다.<br/>
    · 수집 항목: 매매가·보유현금·연소득·기존부채·무주택/생애최초 여부<br/>
    · 목적: 대출 한도(LTV·DSR)·월상환 추정에만 사용<br/>
    · 보관: <b>서버에 저장하지 않고 계산 즉시 폐기</b>. '저장' 선택 시 본인 기기(브라우저)에만 보관<br/>
    · 제3자 제공·마케팅 이용 없음. 주민번호·계좌 등은 수집하지 않음
   </div>
   <div style={{marginTop:10}}>
    <button onClick={()=>setShowDoc("privacy")} style={{border:"none",background:"none",color:TEAL,fontWeight:700,fontSize:12.5,cursor:"pointer",padding:0,textDecoration:"underline"}}>개인정보처리방침 보기</button>
   </div>
   <div style={{display:"flex",gap:8,marginTop:14,flexWrap:"wrap"}}>
    <button className="tog on" style={{padding:"11px 16px"}} onClick={agree}>동의하고 맞춤 추정</button>
    <button className="tog" style={{padding:"11px 16px"}} onClick={()=>onChoose(false)}>동의 없이 간이 추정</button>
   </div>
   <div style={{fontSize:11.5,color:MUTED,marginTop:12}}>※ 본 결과는 참고용 추정치이며 금융자문이 아닙니다.</div>
  </div>
  {showDoc&&<LegalModal doc={showDoc} onClose={()=>setShowDoc(null)}/>}
 </div>);
}
function LoanField({label,val,set,suf,ph}){
 return (<label style={{display:"block"}}>
  <div style={{fontSize:12.5,color:MUTED,marginBottom:5,fontWeight:600}}>{label}</div>
  <div style={{display:"flex",alignItems:"center",gap:6,background:"var(--surface-2)",border:"1px solid var(--line)",borderRadius:11,padding:"0 12px"}}>
   <input type="number" inputMode="numeric" value={val} placeholder={ph||""} onChange={e=>set(e.target.value)}
    style={{flex:1,minWidth:0,border:"none",background:"transparent",outline:"none",font:"inherit",fontSize:15,padding:"11px 0",color:"var(--ink)"}}/>
   <span style={{fontSize:12.5,color:MUTED,flex:"none"}}>{suf}</span>
  </div>
 </label>);
}
function AffordVerdict({a}){
 if(!a) return null;
 const M={1:["#1d7a4d","rgba(29,122,77,.10)"],2:["#1E5FC4","rgba(30,95,196,.10)"],3:["#9A6B00","rgba(178,106,0,.12)"],4:["#C8322A","rgba(200,50,42,.10)"]};
 const C=M[a.level]||["#566069","var(--chip)"];
 const msg = a.reason==="loan_over_limit" ? "대출 한도로는 이 매매가를 감당하기 어려워요. 자기자본을 더 마련하거나 예산을 낮춰보세요."
  : a.reason==="cash_short" ? `계약금·세금까지 필요한 현금이 ${eok(a.cash_gap)} 부족해요.`
  : a.burden_ratio!=null ? `월 상환액이 소득의 ${a.burden_ratio}% 수준이에요.`+(a.level===1?" 여유 있는 편입니다.":a.level===2?" 가능하지만 금리가 오르면 빠듯할 수 있어요.":" 부담이 큰 편입니다.")
  : "";
 return (<div className="card" style={{padding:"13px 15px",marginTop:12,background:C[1],border:"none"}}>
  <div style={{display:"flex",alignItems:"center",gap:8}}>
   <span style={{fontSize:12.5,color:MUTED,fontWeight:700}}>실구매력 진단<Info text="매매가 대비 필요한 대출이 LTV·DSR 한도 안에 드는지, 월 상환액이 소득에서 차지하는 비중(부담률)이 얼마인지로 판정합니다. 참고용 추정이며 실제 심사와 다를 수 있어요."/></span>
   <span className="pill" style={{background:"var(--surface-solid)",color:C[0],fontWeight:800,fontSize:13,marginLeft:"auto"}}>{a.label}</span>
  </div>
  <div style={{display:"flex",gap:18,marginTop:10,flexWrap:"wrap"}}>
   <div><div style={{fontSize:11,color:MUTED}}>월 예상 상환</div><div className="num" style={{fontSize:18,fontWeight:800}}>{won(a.monthly_payment)}</div></div>
   {a.burden_ratio!=null&&<div><div style={{fontSize:11,color:MUTED}}>소득 대비 부담률</div><div className="num" style={{fontSize:18,fontWeight:800,color:C[0]}}>{a.burden_ratio}%</div></div>}
   {!a.within_limit&&<div><div style={{fontSize:11,color:MUTED}}>필요 대출</div><div className="num" style={{fontSize:18,fontWeight:800,color:C[0]}}>{eok(a.required_loan)}</div></div>}
  </div>
  {msg&&<div style={{fontSize:12.5,color:"var(--ink)",marginTop:10,lineHeight:1.6}}>{msg}</div>}
  <div style={{fontSize:10.5,color:MUTED,marginTop:7,lineHeight:1.6}}>부담률 25% 이하 적정 · 25~35% 빠듯 · 35%↑ 부담. 정책·은행 심사, 금리 변동에 따라 실제와 달라질 수 있습니다.</div>
 </div>);
}
function Loan({initialPrice,onOpen}){
 const saved=React.useMemo(()=>loadLoanProfile(),[]);
 const [consent,setConsent]=useState(saved?(saved.consent?true:false):null);
 const [price,setPrice]=useState(initialPrice!=null?initialPrice:(saved&&saved.price!=null?saved.price:30000)),[cash,setCash]=useState(saved&&saved.cash!=null?saved.cash:""),[income,setIncome]=useState(saved&&saved.income!=null?saved.income:""),[debt,setDebt]=useState(saved&&saved.debt!=null?saved.debt:"");
 const [noHouse,setNoHouse]=useState(saved?!!saved.noHouse:true),[first,setFirst]=useState(saved?!!saved.first:false),[over85,setOver85]=useState(saved?!!saved.over85:false),[rate,setRate]=useState(saved&&saved.rate!=null?saved.rate:4.0),[years,setYears]=useState(saved&&saved.years!=null?saved.years:30);
 const [remember,setRemember]=useState(!!saved),[hasSaved,setHasSaved]=useState(!!saved);
 const [res,setRes]=useState(null);
 const calc=async()=>{
  if(remember){saveLoanProfile({consent:consent===true,price,cash,income,debt,noHouse,first,over85,rate,years});setHasSaved(true);}
  else{clearLoanProfile();setHasSaved(false);}
  const inp={price:+price||0,consent:consent===true,self_capital:cash===""?null:+cash,
   annual_income:(consent===true&&income!=="")?+income:null,existing_annual_payment:debt===""?0:+debt,
   is_no_house:noHouse,is_first_time:first,over_85:over85,rate_pct:rate,years};
  try{const r=await fetch(`${API}/loan/estimate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(inp)}).then(x=>x.json());setRes(r);}
  catch(e){setRes(loanLocal({price:+price||0,consent:consent===true,self_capital:cash===""?null:+cash,
   annual_income:(consent===true&&income!=="")?+income:null,existing:debt===""?0:+debt,is_no_house:noHouse,is_first_time:first,over_85:over85,rate,years}));}
 };
 const forget=()=>{clearLoanProfile();setHasSaved(false);setRemember(false);};
 if(consent===null)return <ConsentGate onChoose={setConsent}/>;
 const priceEok=(+price)?`약 ${((+price)/10000).toFixed(2)}억` : "";
 return (<div style={{marginTop:6}}>
  <div style={{display:"flex",alignItems:"center",gap:8}}>
   <span className="pill" style={{background:consent?"rgba(31,166,118,.16)":"rgba(225,120,40,.14)",color:consent?"#1d6b3a":"#A85420"}}>{consent?"맞춤 추정":"간이 추정"}</span>
   {hasSaved&&<span className="pill" style={{background:"rgba(15,118,110,.12)",color:TEAL}}>저장된 정보 불러옴</span>}
   <button className="tog" style={{marginLeft:"auto"}} onClick={()=>{setConsent(null);setRes(null);}}>동의 다시 선택</button>
  </div>
  <div className="card" style={{padding:16,marginTop:10}}>
   <div className="grid2">
    <LoanField label="매매가" val={price} set={setPrice} suf="만원"/>
    <LoanField label="보유 현금(자기자본)" val={cash} set={setCash} suf="만원" ph="선택"/>
    {consent&&<LoanField label="연소득(부부합산)" val={income} set={setIncome} suf="만원"/>}
    {consent&&<LoanField label="기존 부채 연상환액" val={debt} set={setDebt} suf="만원/년" ph="0"/>}
   </div>
   {priceEok&&<div className="num" style={{fontSize:12,color:MUTED,marginTop:6}}>매매가 {priceEok}</div>}

   <div style={{fontSize:12.5,color:MUTED,fontWeight:600,margin:"16px 0 6px"}}>내 조건</div>
   <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
    <button className={"tog "+(noHouse?"on":"")} onClick={()=>setNoHouse(v=>!v)}>무주택</button>
    <button className={"tog "+(first?"on":"")} onClick={()=>setFirst(v=>!v)}>생애최초</button>
    <button className={"tog "+(over85?"on":"")} onClick={()=>setOver85(v=>!v)}>전용 85㎡ 초과</button>
   </div>

   <div style={{marginTop:16}}>
    <div style={{display:"flex",justifyContent:"space-between",fontSize:12.5,color:MUTED,fontWeight:600}}><span>금리</span><span className="num">{rate.toFixed(1)}%</span></div>
    <input type="range" aria-label="금리(%)" min="2.5" max="7" step="0.1" value={rate} onChange={e=>setRate(+e.target.value)} style={{width:"100%",accentColor:TEAL}}/>
    <div style={{display:"flex",justifyContent:"space-between",fontSize:12.5,color:MUTED,fontWeight:600,marginTop:8}}><span>상환 기간</span><span className="num">{years}년</span></div>
    <input type="range" aria-label="대출 기간(년)" min="10" max="40" step="5" value={years} onChange={e=>setYears(+e.target.value)} style={{width:"100%",accentColor:TEAL}}/>
   </div>
   <button onClick={calc} style={{marginTop:16,width:"100%",border:"none",background:TEAL,color:"#fff",fontWeight:800,fontSize:15,padding:"13px",borderRadius:12,cursor:"pointer"}}>한도 계산하기</button>
   <label style={{display:"flex",alignItems:"center",gap:7,marginTop:10,fontSize:12.5,color:MUTED,cursor:"pointer"}}>
    <input type="checkbox" checked={remember} onChange={e=>setRemember(e.target.checked)} style={{accentColor:TEAL,width:16,height:16}}/>
    이 기기에 내 정보 저장(다음에 자동 입력)
   </label>
   <div style={{fontSize:11,color:MUTED,marginTop:6}}>
    {remember?"내 정보는 이 기기에만 저장되고 서버로 전송되지 않습니다.":"입력값은 저장되지 않고 계산에만 쓰입니다."}
    {hasSaved&&<span> · <span style={{color:UP,cursor:"pointer",fontWeight:700}} onClick={forget}>저장 정보 삭제</span></span>}
   </div>
  </div>
  {res&&res.affordability&&<AffordVerdict a={res.affordability}/>}
  {res&&<LoanResult res={res}/>}
 </div>);
}
function LoanResult({res}){
 return (<div>
  <Collapsible icon="loan" defaultOpen={true} title="예상 대출 한도">
   <div style={{padding:18}}>
   <div style={{fontSize:12,color:MUTED}}>실질 한도 (LTV·DSR 중 낮은 값)</div>
   <div className="num" style={{fontSize:30,fontWeight:800,margin:"4px 0"}}>{eok(res.limit)}</div>
   <div style={{fontSize:12.5,color:MUTED}}>제약: <b style={{color:INK}}>{res.binding}</b> · LTV {eok(res.ltv_amount)}({Math.round(res.ltv_ratio*100)}%) · DSR {res.dsr_amount!=null?eok(res.dsr_amount):"—(간이)"}</div>
   <div style={{display:"flex",gap:14,marginTop:12,flexWrap:"wrap"}}>
    <div><div style={{fontSize:12,color:MUTED}}>필요 자기자본</div><div className="num" style={{fontWeight:700}}>{eok(res.needed_cash)}</div></div>
    {res.cash_gap!=null&&<div><div style={{fontSize:12,color:MUTED}}>현금 부족분</div><div className="num" style={{fontWeight:700,color:res.cash_gap>0?UP:"#1d6b3a"}}>{res.cash_gap>0?eok(res.cash_gap):"충족"}</div></div>}
   </div>
   </div>
  </Collapsible>
  <Collapsible icon="loan" defaultOpen={true} title="이 집을 사려면 · 총 필요현금">
   <div style={{padding:18}}>
   <div className="num" style={{fontSize:28,fontWeight:800}}>{eok(res.total_cash_needed)}</div>
   <div style={{fontSize:12.5,color:MUTED,marginTop:4}}>계약금성 자기자본 {eok(res.needed_cash)} + 매수 부대비용 {won(res.costs.total)}</div>
   {res.total_cash_gap!=null&&<div style={{marginTop:10,fontWeight:800,color:res.total_cash_gap>0?UP:"#1d6b3a"}}>
    {res.total_cash_gap>0?`보유 현금 대비 ${eok(res.total_cash_gap)} 부족`:"보유 현금으로 충족 ✓"}</div>}
   </div>
  </Collapsible>
  <Collapsible icon="doc" defaultOpen={true} title="매수 부대비용 상세">
   <div style={{padding:"4px 14px"}}>
   <CostRow label={`취득세 (${(res.costs.acq_rate*100).toFixed(2)}%)`} val={res.costs.acquisition_tax} note={res.costs.first_time_credit>0?`생애최초 -${res.costs.first_time_credit}만`:null}/>
   <CostRow label="지방교육세" val={res.costs.edu_tax}/>
   {res.costs.farm_tax>0&&<CostRow label="농어촌특별세 (85㎡↑)" val={res.costs.farm_tax}/>}
   <CostRow label="중개보수 (상한)" val={res.costs.broker_fee}/>
   <CostRow label="법무·등기 (예상)" val={res.costs.beopmu_estimate}/>
   <div className="listrow" style={{fontWeight:800}}><span>부대비용 합계</span><span style={{marginLeft:"auto"}} className="num">{won(res.costs.total)}</span></div>
   </div>
  </Collapsible>
  <Collapsible icon="rank" defaultOpen={true} title="월 상환액 시뮬레이션">
   <div style={{padding:"4px 14px"}}>
   {res.simulations.length?res.simulations.map((s,i)=>(<div key={i} className="listrow">
    <span style={{fontWeight:600}}>{s.method}</span>
    <span style={{marginLeft:"auto",textAlign:"right"}}>
     <span className="num" style={{fontWeight:800}}>{s.monthly!=null?won(s.monthly)+"/월":`${won(s.monthly_first)}→${won(s.monthly_last)}`}</span>
     <span className="num" style={{display:"block",fontSize:11.5,color:MUTED}}>총이자 {eok(s.total_interest)}</span></span>
   </div>)):<Empty>한도가 0이라 시뮬레이션이 없습니다.</Empty>}
   </div>
  </Collapsible>
  <Collapsible icon="doc" defaultOpen={true} title={<React.Fragment>상품 비교 {res.rates_live
    ? <span className="pill" style={{background:"#E4F2E8",color:"#1d6b3a"}}>은행 실시간 공시</span>
    : <span className="pill ex">예시</span>}</React.Fragment>}>
   <div style={{padding:"4px 14px"}}>
   {res.products.map((p,i)=>(<div key={i} className="listrow" style={{opacity:p.eligible?1:0.5}}>
    <div style={{minWidth:0}}>
     <div style={{fontWeight:600,overflow:"hidden",textOverflow:"ellipsis"}}>{p.name} <span className="pill" style={{background:p.kind==="정책"?"#E7EEF6":"#EEF1F1",color:p.kind==="정책"?"#1E5FC4":MUTED}}>{p.kind}</span> {p.is_sample&&<ExBadge/>}</div>
     <div style={{fontSize:12,color:MUTED}}>{p.req}{p.eligible?"":" · 자격 미해당"}{p.as_of?` · 공시 ${p.as_of}`:""}</div>
    </div>
    <span style={{marginLeft:"auto",textAlign:"right"}}><span className="num" style={{fontWeight:700}}>{p.rate_min}~{p.rate_max}%</span>
     <span className="num" style={{display:"block",fontSize:11.5,color:MUTED}}>{p.limit?`~${eok(p.limit)}`:p.method}</span></span>
   </div>))}
   </div>
  </Collapsible>
  <div style={{background:"var(--callout-bg)",color:"var(--callout-fg)",borderRadius:12,padding:"11px 14px",fontSize:11.5,fontWeight:600,lineHeight:1.6,margin:"14px 0"}}>
   ⓘ 기준 {res.as_of} · {res.region}. {res.disclaimer} 금리·한도는 공시·정책 변경에 따라 달라집니다.
   {res.rates_live?" 은행 금리는 finlife 공시 실시간이며, 정책대출은 예시입니다.":" 상품 금리는 finlife 미연동 상태의 예시입니다."}
   {" 취득세 등 부대비용은 1주택 일반과세 기준 추정이며 다주택 중과·감면 요건·국민주택채권·법무 실비는 별도입니다."}
  </div>
 </div>);
}

ReactDOM.createRoot(document.getElementById("root")).render(<ErrorBoundary><App/></ErrorBoundary>);

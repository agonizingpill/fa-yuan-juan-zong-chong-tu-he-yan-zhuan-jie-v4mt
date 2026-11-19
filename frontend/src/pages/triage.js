import {store} from '../stores/workspace.js';
import {field,input,select,table,badge} from '../components/controls.js';
import {topics,tiers,auditStates} from '../constants/enums.js';
import {esc,date} from '../utils/format.js';
import {bindForm,request} from '../utils/forms.js';
const pct=v=>(v*100).toFixed(1)+'%';
const rateText=b=>b.rate_low===b.rate_high?pct(b.rate_low):pct(b.rate_low)+' ~ '+pct(b.rate_high);
let audit={openId:null};
export function render(){
 const rows=store.data.triages.filter(t=>t.intake_id===store.selected),last=rows.at(-1);
 return `<h2>咨询主题与专长分流</h2>
 <p class="intro">依据模拟文本推荐劳动、住房或消费方向。置信度低于68%退回人工；所有转介均需主管确认主题。</p>
 <div class="two-col">
  <form id="enqueue" class="paper-form"><h3>按当前事实提交分流</h3><p>提取当前版本描述，送交主题分类。完成后刷新收件夹。</p><button>提交行政主题识别</button><p class="hint">本页不生成事实判断、法律意见或办案建议。</p></form>
  <form id="review" class="paper-form"><h3>主管主题复核</h3>
   ${field('待复核记录',select('id',rows.filter(t=>t.status==='done').map(t=>`<option value="${t.id}">#${t.id} / 版本${t.facts_version} / ${topics[t.predicted]} ${Math.round(t.confidence*100)}%</option>`).join('')))}
   ${field('确认专长方向',select('topic',Object.entries(topics).map(([v,l])=>`<option value="${v}">${l}</option>`).join('')))}
   ${field('行政核验说明',input('note','text','已核对来访描述和机构接待范围'))}
   <button>确认专长方向</button></form>
 </div>
 ${table(['记录 / 事实版本','推荐主题','置信度 / 人工','复核进度'],rows.slice().reverse().map(t=>['#'+t.id+' / v'+t.facts_version,topics[t.predicted]||'待识别',t.confidence===null?'—':Math.round(t.confidence*100)+'% / '+(t.manual_required?'低置信退回人工':'等待主管确认'),badge(t.status==='reviewed'?topics[t.approved]+' 已确认':t.status==='done'?'待复核':t.status)]))}
 <section class="validation">
  <div><span class="kicker">内部留出评价</span><h3>TF-IDF + 朴素贝叶斯</h3><p>${esc(last?.metrics?.source||'尚无结果')}</p><p>训练 ${last?.metrics?.train_count||0} / 留出 ${last?.metrics?.test_count||0} / seed 34</p></div>
  <div><b>Macro F1 ${last?.metrics?.macro_f1?.toFixed(4)||'—'}</b>${last?.metrics?.confusion_matrix?table(['实际\\预测','劳动','住房','消费'],last.metrics.confusion_matrix.map((r,i)=>[topics[last.metrics.labels[i]],...r])):''}</div>
 </section>
 <section id="audit-root"><h3>抽检复核 · 主题错分</h3><p class="hint">正在载入抽检批次…</p></section>`;
}
export function bind(r){
 bindForm('enqueue',()=>request('/triages',{intake_id:store.selected}),r);
 bindForm('review',d=>request('/triages/'+d.id+'/review',{topic:d.topic,note:d.note}),r);
 loadAudit(r);
}
async function loadAudit(r){
 const root=document.getElementById('audit-root');if(!root)return;
 try{
  const batches=await request('/audit-batches');
  const detail=audit.openId?await request('/audit-batches/'+audit.openId).catch(()=>null):null;
  root.innerHTML=auditHtml(batches,detail);
  bindAudit(root,r);
 }catch(e){root.innerHTML=`<h3>抽检复核 · 主题错分</h3><p class="error">${esc(e.message)}</p>`;}
}
function auditHtml(batches,detail){
 const rows=batches.map(b=>['#'+b.id,
  auditStates[b.status]||b.status,
  b.status==='sealed'?rateText(b):`已核定 ${b.determined} / 应核定 ${b.total-b.stale}`+(b.stale?` · 将记缺样 ${b.stale}`:''),
  date(b.created_at),
  `<button class="text-button" data-open="${b.id}">${detail&&detail.id===b.id?'收起':'查看'}</button>`]);
 return `<h3>抽检复核 · 主题错分</h3>
 <p class="intro">留出分高不等于接待准。按推荐主题 × 置信档分层随机抽卷，复核人盲核定题（定题前看不到原推荐），封批后按抽样前各档卷量加权公布错分率；封批前更正事实的卷记缺样，成绩给出缺样全对 ~ 全错区间，复核未办完不出成绩。</p>
 <div class="two-col">
  <form id="audit-create" class="paper-form"><h3>新建抽检批次</h3>
   ${field('抽样总量',input('sample_size','number','8','min="1" max="200"'))}
   ${field('随机种子（可选，用于复现）','<input name="seed" type="number" min="0" placeholder="留空自动生成">')}
   <button>分层随机抽卷</button>
   <p class="hint">同卷在同一开放批次只入样一次；未封批批次中的卷不重复入样。</p></form>
  <div>${table(['批次','状态','进度 / 加权错分率','建批时间',''],rows,'尚无抽检批次。')}</div>
 </div>
 ${detail?detailHtml(detail):''}`;
}
function detailHtml(b){
 const sealed=b.status==='sealed';
 const head=sealed
  ?`<b>加权错分率 ${rateText(b)}</b><p class="hint">按抽样前各档卷量加权${b.stale?`；含缺样 ${b.stale} 份，区间为缺样全对 ~ 全错`:'；本批无缺样'}</p>`
  :`<b>复核中，暂不出成绩</b><p class="hint">已核定 ${b.determined} / 应核定 ${b.total-b.stale}${b.stale?` · 将记缺样 ${b.stale}`:''}；全部办完并封批后公布成绩</p>`;
 const forms=b.samples.filter(s=>!s.stale&&!sealed).map(s=>`<form class="paper-form determine" data-id="${s.id}">
  <h3>盲核定题 · ${esc(s.code)}</h3>
  <p class="snapshot">${esc(s.facts_snapshot)}</p>
  ${field('核定主题',select('topic',Object.entries(topics).map(([v,l])=>`<option value="${v}" ${s.determined===v?'selected':''}>${l}</option>`).join('')))}
  <button>${s.determined?'重新核定':'提交核定'}</button>
  ${s.attempts?`<p class="hint">已提交 ${s.attempts} 次，重试不重复计分</p>`:''}
 </form>`).join('');
 const sampleRows=b.samples.map(s=>{
  const revealed=sealed||s.determined;
  return [`#${s.id} · ${esc(s.code)}`,
   s.missing?badge('缺样 · 不计分'):s.stale?badge('事实已更正 · 将记缺样'):s.determined?badge('已核定'):badge('待核定'),
   revealed?`${topics[s.recommended]} ${Math.round(s.confidence*100)}%`:'<span class="hint">推荐已隐藏</span>',
   revealed?(topics[s.determined]||'—'):'—',
   sealed&&!s.missing&&s.determined?(s.determined===s.recommended?'一致':'错分'):''];
 });
 const strata=sealed?table(['层 · 主题 × 置信档','抽样前卷量','样本','错分','缺样','层错分率'],b.strata.map(st=>[`${topics[st.topic]} × ${tiers[st.tier]}`,st.population,st.sample_size,st.errors,st.missing,st.rate_low===st.rate_high?pct(st.rate_low):pct(st.rate_low)+' ~ '+pct(st.rate_high)])):'';
 return `<section class="audit-detail">
  <div class="detail-head"><h3>批次 #${b.id} · ${auditStates[b.status]} · seed ${b.seed}</h3>${head}${sealed?'':`<button data-seal="${b.id}" class="secondary">复核办完，封批出分</button>`}</div>
  ${forms?`<div class="two-col">${forms}</div>`:''}
  ${table(['样本 · 卷宗','状态','原推荐','核定主题','结果'],sampleRows)}
  ${strata}
 </section>`;
}
function bindAudit(root,r){
 const notice=()=>document.getElementById('notice');
 bindForm('audit-create',d=>{const body={sample_size:+d.sample_size};if(d.seed!=='')body.seed=+d.seed;return request('/audit-batches',body);},r);
 root.querySelectorAll('[data-open]').forEach(btn=>btn.onclick=()=>{audit.openId=audit.openId===+btn.dataset.open?null:+btn.dataset.open;loadAudit(r);});
 root.querySelectorAll('form.determine').forEach(form=>form.onsubmit=async e=>{
  e.preventDefault();
  const button=form.querySelector('button');button.disabled=true;
  try{await request('/audit-samples/'+form.dataset.id+'/determine',Object.fromEntries(new FormData(form)));notice().textContent='核定已记录，原推荐已揭晓';await loadAudit(r);}
  catch(error){notice().textContent=error.message;}
  finally{button.disabled=false;}
 });
 const seal=root.querySelector('[data-seal]');
 if(seal)seal.onclick=async()=>{
  seal.disabled=true;
  try{await request('/audit-batches/'+seal.dataset.seal+'/seal',{});notice().textContent='批次已封批，成绩已公布';await loadAudit(r);}
  catch(error){notice().textContent=error.message;}
  finally{seal.disabled=false;}
 };
}

/* ===== DOMヘルパ ===== */
const $  = (q)=>document.querySelector(q);
const $$ = (q)=>Array.from(document.querySelectorAll(q));

async function fetchJSON(url,opt={}){
  const hasBody = opt && typeof opt.body !== "undefined";
  const headers = Object.assign({'Content-Type':'application/json'}, (opt.headers||{}));
  const res = await fetch(url, Object.assign({headers}, opt));
  if(!res.ok){ throw new Error(await res.text()); }
  return await res.json();
}

/* ===== 設定UI（配当入力→確率は自動計算プレビュー、保存時はサーバが再計算） ===== */
function rowTemplate(s={id:"",label:"",payout_3:0,color:"#888888",prob:0}){
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><input class="sid" type="text" value="${s.id ?? ''}"></td>
    <td><input class="label" type="text" value="${s.label ?? ''}"></td>
    <td><input class="p3" type="number" step="0.01" min="0" value="${Number(s.payout_3||0)}"></td>
    <td><input class="prob" type="number" step="0.0001" value="${Number(s.prob||0).toFixed(4)}" disabled></td>
    <td style="display:flex;align-items:center;gap:.4rem">
      <input class="color" type="color" value="${s.color || '#888888'}">
      <span class="color-swatch" style="background:${s.color || '#888888'}"></span>
    </td>
    <td style="text-align:right"><button type="button" class="sub del">削除</button></td>`;
  return tr;
}

function readRows(){
  const arr = [];
  for(const tr of $$('#rows tr')){
    const id = tr.querySelector('.sid').value.trim();
    const label = tr.querySelector('.label').value.trim() || id;
    const payout_3 = parseFloat(tr.querySelector('.p3').value||"0");
    const color = tr.querySelector('.color').value;
    if(!id) continue;
    arr.push({id, label, payout_3: isFinite(payout_3)? payout_3:0, color});
  }
  return arr;
}

/* ===== 期待値ターゲットに一致する確率分布（指数傾斜） ===== */
function solveProbsForTarget(payouts, targetE1){
  if(!payouts.length) return [];
  const vmin = Math.min(...payouts), vmax = Math.max(...payouts);

  if(!(isFinite(targetE1)) || targetE1<=0){
    const inv = payouts.map(v => v>0 ? 1/v : 0);
    const S = inv.reduce((a,b)=>a+b,0) || 1;
    return inv.map(x => x/S);
  }
  if(targetE1 <= vmin + 1e-12){
    return payouts.map(v => v===vmin ? 1 : 0);
  }
  if(targetE1 >= vmax - 1e-12){
    return payouts.map(v => v===vmax ? 1 : 0);
  }

  const E = beta => {
    const w = payouts.map(v => Math.exp(beta * v));
    const Z = w.reduce((a,b)=>a+b,0);
    const p = w.map(x => x/Z);
    return p.reduce((s,pi,i)=> s + pi * payouts[i], 0);
  };

  let lo = -1, hi = 1;
  for(let i=0;i<60;i++){
    const elo = E(lo), ehi = E(hi);
    if(elo > targetE1){ lo *= 2; continue; }
    if(ehi < targetE1){ hi *= 2; continue; }
    break;
  }
  for(let i=0;i<80;i++){
    const mid = (lo+hi)/2;
    const em = E(mid);
    if(em < targetE1) lo = mid; else hi = mid;
  }
  const beta = (lo+hi)/2;
  const w = payouts.map(v => Math.exp(beta * v));
  const Z = w.reduce((a,b)=>a+b,0);
  return w.map(x => x/Z);
}

/* ===== 配当表レンダリング（図柄と配当のみ・配当降順） ===== */
function renderPayoutTableFromRows(){
  const rows  = readRows();
  const tbody = $('#payout-rows');
  if(!tbody) return;

  tbody.innerHTML = '';

  // 配当が大きい順に並べ替えて描画
  const sorted = [...rows].sort((a,b)=>(b.payout_3||0)-(a.payout_3||0));

  sorted.forEach((r)=>{
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><span class="badge" style="background:${r.color || '#4f46e5'}">${r.label || r.id}</span></td>
      <td style="text-align:right">${Number(r.payout_3 || 0)}</td>
    `;
    tbody.appendChild(tr);
  });
}

/* ===== プレビュー再計算（期待値>0は指数傾斜、0は反比例） ===== */
function previewRecalcProb(){
  const expected5 = parseFloat($('#expected-total-5')?.value||"0");
  const rows = readRows();
  const payouts = rows.map(r => Math.max(0, +r.payout_3));

  let probs1 = [];
  if(expected5 > 0){
    const targetE1 = expected5 / 5.0;
    probs1 = solveProbsForTarget(payouts, targetE1);
  }else{
    const inv = payouts.map(v => v>0 ? 1/v : 0);
    const S = inv.reduce((a,b)=>a+b,0) || 1;
    probs1 = inv.map(x => x/S);
  }

  const trs = $$('#rows tr');
  let sum = 0;
  probs1.forEach((p,i)=>{
    const pct = p*100;
    sum += pct;
    if(trs[i]) trs[i].querySelector('.prob').value = pct.toFixed(4);
  });
  $('#prob-total').textContent = sum.toFixed(4);
  $('#prob-warn').style.display = (Math.abs(sum-100) > 0.05) ? 'inline' : 'none';

  renderPayoutTableFromRows();
}

async function loadConfig(){
  const cfg = await fetchJSON('/config');
  window.__symbols = cfg.symbols;
  $('#rows').innerHTML = '';
  (cfg.symbols || []).forEach(s => $('#rows').appendChild(rowTemplate(s)));
  if($('#expected-total-5')) $('#expected-total-5').value = cfg.expected_total_5 ?? 2500;
  bindRowEvents();
  buildAllReels(cfg.symbols);
  previewRecalcProb();
}

function bindRowEvents(){
  $$('#rows .del').forEach(btn=>btn.onclick=(e)=>{ e.target.closest('tr').remove(); previewRecalcProb(); });
  $$('#rows .color').forEach(inp=>inp.oninput=(e)=>{ e.target.closest('td').querySelector('.color-swatch').style.background = e.target.value; });
  $$('#rows .p3, #rows .sid, #rows .label').forEach(inp=> inp.oninput = previewRecalcProb);

  const exp = $('#expected-total-5');
  if(exp) exp.addEventListener('input', previewRecalcProb);
}

async function saveConfig(){
  const adminEl = $('#admin-token');
  const adminToken = adminEl ? (adminEl.value || '').trim() : '';

  const symbols = readRows();
  if(symbols.length === 0){ alert('行がありません'); return; }

  const body = {
    target_expected_total_5: parseFloat($('#expected-total-5')?.value||"0") || undefined,
    symbols,
    reels: 3,
    base_bet: 1
  };

  const headers = {'Content-Type':'application/json'};
  if(adminToken) headers['X-Admin-Token'] = adminToken;

  await fetchJSON('/config', { method:'POST', headers, body: JSON.stringify(body) });
  await loadConfig();
  alert('保存しました（確率を再計算して保存）');
}

/* ===== リール見た目生成 ===== */
const STRIP_REPEAT = 8;
const CELL_H = (() => {
  const v = getComputedStyle(document.documentElement).getPropertyValue('--cell-h') || '120px';
  const n = parseInt(String(v).replace('px','').trim(), 10);
  return Number.isFinite(n) ? n : 120;
})();

function buildStripHTML(symbols){
  const html = [];
  for(let r=0;r<STRIP_REPEAT;r++){
    for(const s of symbols){
      html.push(`<div class="cell" style="color:${s.color || '#fff'}">${s.label}</div>`);
    }
  }
  return html.join('');
}

function buildAllReels(symbols){
  $$('#reels .reel').forEach((reel)=>{
    const strip = reel.querySelector('.strip');
    strip.innerHTML = buildStripHTML(symbols);
    strip.style.transition = 'none';
    strip.style.transform = 'translateY(0)';
    strip.style.animation = 'none';
  });
}

/* ===== スピン演出（上→下に回る；CSSの@keyframes scroll 使用） ===== */
let spinning = false;

function startSpinVisual(){
  $$('#reels .reel').forEach((reel, i)=>{
    const strip = reel.querySelector('.strip');
    strip.style.transition = 'none';
    strip.style.transform = 'translateY(0)';
    const speed = 0.45 + i * 0.07;
    strip.style.animation = `scroll ${speed}s linear infinite`;
  });
}

function stopReelVisual(reelIndex, targetSymbolId){
  const reel = $(`#reels .reel[data-reel="${reelIndex}"]`);
  const strip = reel.querySelector('.strip');
  strip.style.animation = 'none';

  const order = (window.__symbols || []).map(s=>s.id);
  const oneLoopLen = order.length * STRIP_REPEAT;
  const baseIndex  = order.length * (STRIP_REPEAT - 2);
  const within     = Math.max(0, order.indexOf(targetSymbolId));
  const targetIndex = Math.min(oneLoopLen - 1, baseIndex + within);

  requestAnimationFrame(()=>{
    strip.style.transition = 'transform 620ms cubic-bezier(.18,.8,.2,1)';
    strip.style.transform  = `translateY(-${targetIndex * CELL_H}px)`;
  });
}

/* ===== 5回分のスピンを順番に再生 ===== */
async function animateFiveSpins(spins){
  $('#status').textContent = 'SPIN...';
  $('#round-indicator').textContent = '';

  let total = 0;
  for(let i=0;i<spins.length;i++){
    const one = spins[i];

    startSpinVisual();
    await new Promise(r=>setTimeout(r, 500));
    stopReelVisual(0, one.id);
    await new Promise(r=>setTimeout(r, 420));
    stopReelVisual(1, one.id);
    await new Promise(r=>setTimeout(r, 420));
    stopReelVisual(2, one.id);
    await new Promise(r=>setTimeout(r, 700));

    total += one.payout;
    $('#round-indicator').textContent = `Round ${i+1}/5：${one.label} (+${one.payout})`;
  }
  return total;
}

/* ===== メイン操作 ===== */
async function play(){
  if(spinning) return;
  spinning = true;

  let data;
  try{
    data = await fetchJSON('/spin', { method:'POST', body: JSON.stringify({}) });
  }catch(e){
    $('#status').textContent = 'エラー: ' + (e.message || e);
    spinning = false;
    return;
  }

  const total = await animateFiveSpins(data.spins);

  $('#status').textContent = `合計: ${total}`;
  const li = document.createElement('li');
  const ts = new Date(data.ts*1000).toLocaleString();
  li.innerHTML = data.spins.map(s => `<span class="badge" style="background:${s.color || '#4f46e5'}">${s.label}</span>`).join(' ')
    + ` <span class="muted">${ts}</span> / 合計: ${total}`;
  $('#history').insertBefore(li, $('#history').firstChild);

  renderPayoutTableFromRows();
  spinning = false;
}

/* ===== 初期化 ===== */
document.addEventListener('DOMContentLoaded', ()=>{
  // 設定ダイアログ
  $('#btn-open')?.addEventListener('click', ()=>$('#dlg').showModal());
  $('#btn-cancel')?.addEventListener('click', ()=>$('#dlg').close());
  $('#add')?.addEventListener('click', ()=>{
    $('#rows').appendChild(rowTemplate());
    bindRowEvents();
    previewRecalcProb();
  });
  $('#btn-save')?.addEventListener('click', async (e)=>{
    e.preventDefault();
    await saveConfig();
    $('#dlg').close();
  });

  // n以上〜n'以下の確率計算ツール（存在する場合だけバインド）
  $('#btn-calc-prob')?.addEventListener('click', async ()=>{
    const minStr = $('#threshold-min')?.value ?? '';
    const maxStr = $('#threshold-max')?.value ?? '';
    const tmin = minStr.trim()==='' ? 0 : parseFloat(minStr);
    const tmax = maxStr.trim()==='' ? null : parseFloat(maxStr);

    const payload = { spins: 5, threshold_min: tmin };
    if(tmax !== null && Number.isFinite(tmax)) payload.threshold_max = tmax;

    try{
      const j = await fetchJSON('/calc_prob', { method:'POST', body: JSON.stringify(payload) });
      const el = $('#prob-result');
      if(!el) return;
      if('prob_range' in j && tmax !== null){
        el.textContent = `5回合計が ${tmin} 以上 ${tmax} 以下になる確率： ${(j.prob_range*100).toFixed(2)} %`;
      }else{
        el.textContent = `5回合計が ${tmin} 以上になる確率： ${(j.prob_ge*100).toFixed(2)} %`;
      }
    }catch(e){
      const el = $('#prob-result');
      if(el) el.textContent = `計算エラー: ${e.message || e}`;
    }
  });

  // プレイ
  $('#btn-spin')?.addEventListener('click', ()=>play());

  // アンケートリセット
  $('#btn-reset-survey')?.addEventListener('click', async ()=>{
    if(confirm('アンケートをリセットして最初からやり直しますか？')){
      try{
        await fetchJSON('/reset_survey', { method:'POST', body: JSON.stringify({}) });
        window.location.href = '/survey';
      }catch(e){
        alert('リセットに失敗しました: ' + (e.message || e));
      }
    }
  });

  loadConfig();
});

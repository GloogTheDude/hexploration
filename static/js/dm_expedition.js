import { formatGameDate, formatDurationMinutes } from './game_time.js';
import { axialToPixel, pixelToAxial, hexDistance } from './hex_math.js';
import { authReady, authFetch } from './auth.js';

const params = new URLSearchParams(location.search);
let userId = 0;
const campaignId = Number(params.get('campaign'));
const expeditionId = Number(params.get('expedition'));
const $ = s => document.querySelector(s);
const canvas = $('#map');
const ctx = canvas.getContext('2d');
const ui = {
  title: $('#title'), clock: $('#clock'), position: $('#position'), ping: $('#ping'),
  selection: $('#selection'), move: $('#move'), moveMessage: $('#move-message'),
  fit: $('#fit'), refresh: $('#refresh'), playerMap: $('#player-map'), back: $('#back-dm'),
  poiList: $('#poi-list'), poiCount: $('#poi-count'), poiDetail: $('#poi-detail'),
  days: $('#duration-days'), hours: $('#duration-hours'), minutes: $('#duration-minutes'),
  toast: $('#toast'), showHiddenPois: $('#show-hidden-pois'), undoMove: $('#undo-move'), redoMove: $('#redo-move'), dmPing: $('#dm-ping'), dmPingColor: $('#dm-ping-color'),
};

const DIRECTIONS = [
  {q:1,r:0},{q:1,r:-1},{q:0,r:-1},{q:-1,r:0},{q:-1,r:1},{q:0,r:1},
];
const terrainFallback={PLAIN:'#7b9655',SEA:'#3f6d99',SWAMP:'#5d7052',HILL:'#8d8057',FOREST:'#426742',DEEP_FOREST:'#294a34',LOW_MOUNTAIN:'#77736c',MOUNTAIN:'#6c6a69',HIGH_MOUNTAIN:'#9a9996'};
let expedition=null,workbench=null,playerMap=null,visibility=null,pingState=null,dmPingState=null,terrains={},selected=null,selectedPoi=null;
let view={scale:1,offsetX:0,offsetY:0},dragging=false,dragStart=null,dragMoved=false;
let arrowTargets=[];
let redoStack=[];

function esc(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
async function api(path,options={}){const r=await authFetch(path,{cache:'no-store',headers:{'Content-Type':'application/json',...(options.headers||{})},...options});if(!r.ok){let d=`${r.status} ${r.statusText}`;try{const b=await r.json();d=typeof b.detail==='string'?b.detail:JSON.stringify(b.detail)}catch{}throw new Error(d)}return r.status===204?null:r.json()}
function toast(m){ui.toast.textContent=m;ui.toast.classList.remove('hidden');setTimeout(()=>ui.toast.classList.add('hidden'),2200)}
function offsetToAxial(col,row,w,h){const q=col-Math.floor(w/2),centered=row-Math.floor(h/2),r=centered-Math.floor((q+(q&1))/2);return{q,r}}
function sync(){const w=Math.max(1,canvas.clientWidth),h=Math.max(1,canvas.clientHeight),ratio=Math.max(1,devicePixelRatio||1);if(canvas.width!==Math.round(w*ratio)||canvas.height!==Math.round(h*ratio)){canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio)}ctx.setTransform(ratio,0,0,ratio,0,0);return{w,h}}
function world(q,r){const p=axialToPixel(q,r,(workbench?.hex_size||32)*view.scale);return{x:canvas.clientWidth/2+view.offsetX+p.x,y:canvas.clientHeight/2+view.offsetY+p.y}}
function screen(x,y){return pixelToAxial(x-canvas.clientWidth/2-view.offsetX,y-canvas.clientHeight/2-view.offsetY,(workbench?.hex_size||32)*view.scale)}
function path(x,y,size){ctx.beginPath();for(let i=0;i<6;i++){const a=Math.PI/180*60*i,px=x+size*Math.cos(a),py=y+size*Math.sin(a);i?ctx.lineTo(px,py):ctx.moveTo(px,py)}ctx.closePath()}
function color(k){return terrains[k]?.color||terrainFallback[k]||'#59697a'}
function overrideMap(){return new Map((workbench?.hexes||[]).map(h=>[`${h.q},${h.r}`,h]))}
function knowledgeMap(){return new Map((playerMap?.hexes||[]).map(h=>[`${h.q},${h.r}`,h]))}
function visibleSet(){return new Set((visibility?.visible_hexes||[]).map(h=>`${h.q},${h.r}`))}
function knownPoiSet(){return new Set((playerMap?.pois||[]).map(p=>p.poi_id))}
function currentPing(){return pingState || {q:playerMap?.ping_q??expedition?.ping_q,r:playerMap?.ping_r??expedition?.ping_r,game_minute:playerMap?.ping_game_minute??expedition?.ping_game_minute}}
function currentDmPing(){return dmPingState || {q:null,r:null}}

function drawMoveArrows(size){
  arrowTargets=[];
  if(!expedition || expedition.status!=='ACTIVE') return;
  const cur=world(expedition.current_q, expedition.current_r);
  const ping=currentPing();
  for(const d of DIRECTIONS){
    const q=expedition.current_q+d.q, r=expedition.current_r+d.r;
    const n=world(q,r);
    const dx=n.x-cur.x,dy=n.y-cur.y,len=Math.hypot(dx,dy)||1;
    const ux=dx/len,uy=dy/len;
    const cx=cur.x+ux*Math.max(18,size*.76),cy=cur.y+uy*Math.max(18,size*.76);
    const radius=Math.max(9,Math.min(14,size*.28));
    arrowTargets.push({x:cx,y:cy,radius,q,r});
    ctx.save();
    ctx.beginPath();ctx.arc(cx,cy,radius,0,Math.PI*2);
    const isPing=ping.q===q&&ping.r===r;
    ctx.fillStyle=isPing?'rgba(255,83,105,.95)':'rgba(25,48,63,.92)';ctx.fill();
    ctx.strokeStyle=isPing?'#ffd0d6':'#b8d8ea';ctx.lineWidth=1.8;ctx.stroke();
    ctx.beginPath();
    const tipX=cx+ux*radius*.55,tipY=cy+uy*radius*.55;
    const bx=cx-ux*radius*.35,by=cy-uy*radius*.35;
    const px=-uy,py=ux;
    ctx.moveTo(tipX,tipY);ctx.lineTo(bx+px*radius*.38,by+py*radius*.38);ctx.lineTo(bx-px*radius*.38,by-py*radius*.38);ctx.closePath();
    ctx.fillStyle='#eef7ff';ctx.fill();ctx.restore();
  }
}

function draw(){
  const {w,h}=sync();ctx.clearRect(0,0,w,h);ctx.fillStyle='#090d12';ctx.fillRect(0,0,w,h);if(!workbench||!expedition)return;
  const size=workbench.hex_size*view.scale,overrides=overrideMap(),known=knowledgeMap(),visible=visibleSet();
  const logical=workbench.width*workbench.height,cells=[];
  if(logical<=100000){for(let row=0;row<workbench.height;row++)for(let col=0;col<workbench.width;col++)cells.push(offsetToAxial(col,row,workbench.width,workbench.height))}
  else{for(const h of workbench.hexes)cells.push({q:h.q,r:h.r});for(let dq=-20;dq<=20;dq++)for(let dr=-20;dr<=20;dr++)if((Math.abs(dq)+Math.abs(dq+dr)+Math.abs(dr))/2<=20)cells.push({q:expedition.current_q+dq,r:expedition.current_r+dr})}
  const uniq=new Set();
  for(const c of cells){
    const k=`${c.q},${c.r}`;if(uniq.has(k))continue;uniq.add(k);
    const p=world(c.q,c.r),row=overrides.get(k),terrain=row?.terrain_key||workbench.default_terrain_key||'SEA';
    path(p.x,p.y,size-1);ctx.fillStyle=color(terrain);ctx.globalAlpha=.96;ctx.fill();ctx.globalAlpha=1;ctx.strokeStyle='#26333f';ctx.lineWidth=1;ctx.stroke();
    if(!known.has(k)){path(p.x,p.y,size-1);ctx.fillStyle='rgba(4,8,12,.58)';ctx.fill()}
    else if(!visible.has(k)){path(p.x,p.y,size-1);ctx.fillStyle='rgba(5,9,12,.34)';ctx.fill()}
    if(visible.has(k)){path(p.x,p.y,size-2);ctx.strokeStyle='#a9d99a';ctx.lineWidth=2.4;ctx.stroke()}
  }
  for(const area of workbench.areas||[]){for(const c of area.cells||[]){const p=world(c.q,c.r);path(p.x,p.y,size-2);ctx.fillStyle=area.feature_type==='LAKE'||area.feature_type==='INLAND_SEA'?'rgba(80,145,190,.28)':'rgba(160,145,90,.13)';ctx.fill()}}
  for(const edge of workbench.edges||[]){const a=world(edge.from_q,edge.from_r),b=world(edge.to_q,edge.to_r);ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.strokeStyle=edge.feature_type==='RIVER'?'#6fbce8':edge.feature_type==='ROAD'?'#d9c178':'#c8a2d8';ctx.lineWidth=Math.max(2,3*view.scale);ctx.stroke()}
  const knownPois=knownPoiSet();
  for(const poi of workbench.pois||[]){
    const hidden=!knownPois.has(poi.feature_id)&&poi.requires_discovery;
    if(hidden&&!ui.showHiddenPois.checked) continue;
    const p=world(poi.q,poi.r);ctx.beginPath();ctx.arc(p.x,p.y-size*.12,Math.max(4,6*view.scale),0,Math.PI*2);ctx.fillStyle=knownPois.has(poi.feature_id)?'#ffd66b':hidden?'#d27f95':'#e4b66c';ctx.fill();ctx.strokeStyle=hidden?'#fff':'#111820';ctx.lineWidth=2;ctx.stroke();
  }
  const ping=currentPing();if(ping.q!=null&&ping.r!=null){const age=ping.created_at?Date.now()-new Date(ping.created_at).getTime():0;if(age<3200&&Math.floor(age/280)%2===0){const p=world(ping.q,ping.r);ctx.beginPath();ctx.arc(p.x,p.y,Math.max(10,13*view.scale),0,Math.PI*2);ctx.strokeStyle=ping.color||'#ff5369';ctx.lineWidth=4;ctx.stroke();ctx.beginPath();ctx.moveTo(p.x-9,p.y);ctx.lineTo(p.x+9,p.y);ctx.moveTo(p.x,p.y-9);ctx.lineTo(p.x,p.y+9);ctx.stroke()}}
  const dmPing=currentDmPing();if(dmPing.q!=null&&dmPing.r!=null){const age=dmPing.created_at?Date.now()-new Date(dmPing.created_at).getTime():0;if(age<3200&&Math.floor(age/280)%2===0){const p=world(dmPing.q,dmPing.r),r=Math.max(11,14*view.scale);ctx.save();ctx.translate(p.x,p.y);ctx.rotate(Math.PI/4);ctx.strokeStyle=dmPing.color||'#55c7ff';ctx.lineWidth=4;ctx.strokeRect(-r*.65,-r*.65,r*1.3,r*1.3);ctx.rotate(-Math.PI/4);ctx.beginPath();ctx.moveTo(-8,-8);ctx.lineTo(8,8);ctx.moveTo(8,-8);ctx.lineTo(-8,8);ctx.stroke();ctx.restore()}}
  if(selected){const p=world(selected.q,selected.r);path(p.x,p.y,size-3);ctx.strokeStyle='#fff';ctx.lineWidth=3;ctx.stroke()}
  const cur=world(expedition.current_q,expedition.current_r);ctx.beginPath();ctx.arc(cur.x,cur.y,Math.max(6,8*view.scale),0,Math.PI*2);ctx.fillStyle='#eef7ff';ctx.fill();ctx.strokeStyle='#1d76b8';ctx.lineWidth=4;ctx.stroke();
  drawMoveArrows(size);
}

function fit(){if(!workbench||!expedition)return;const logical=workbench.width*workbench.height;let coords=[];if(logical<=100000){coords=[offsetToAxial(0,0,workbench.width,workbench.height),offsetToAxial(workbench.width-1,0,workbench.width,workbench.height),offsetToAxial(0,workbench.height-1,workbench.width,workbench.height),offsetToAxial(workbench.width-1,workbench.height-1,workbench.width,workbench.height)]}else coords=[{q:expedition.current_q-20,r:expedition.current_r},{q:expedition.current_q+20,r:expedition.current_r},{q:expedition.current_q,r:expedition.current_r-20},{q:expedition.current_q,r:expedition.current_r+20}];const pts=coords.map(c=>axialToPixel(c.q,c.r,workbench.hex_size));const minX=Math.min(...pts.map(p=>p.x)),maxX=Math.max(...pts.map(p=>p.x)),minY=Math.min(...pts.map(p=>p.y)),maxY=Math.max(...pts.map(p=>p.y));view.scale=Math.min(2,Math.max(.16,Math.min(canvas.clientWidth/(maxX-minX+workbench.hex_size*4),canvas.clientHeight/(maxY-minY+workbench.hex_size*4))*.9));view.offsetX=-(minX+maxX)/2*view.scale;view.offsetY=-(minY+maxY)/2*view.scale;draw()}
function renderHeader(){ui.title.textContent=expedition.name;ui.clock.textContent=`${formatGameDate(expedition.current_game_minute)} · ${expedition.status}`;ui.position.innerHTML=`Position <strong>(${expedition.current_q}, ${expedition.current_r})</strong><br>Carte <strong>${esc(workbench.map_name)} · v${workbench.version}</strong><br>Météo <strong>${esc(visibility?.weather_key||'—')}</strong>`;const ping=currentPing();ui.ping.innerHTML=ping.q==null?'Aucun ping joueur.':`Ping ${esc(ping.username||'joueur')} : <strong>(${ping.q}, ${ping.r})</strong>${ping.game_minute!=null?`<br>${formatGameDate(ping.game_minute)}`:''}`;ui.playerMap.href=`/player.html?expedition=${expedition.id}&display=1&user=${userId}`;ui.back.href=`/dm.html?user=${userId}&campaign=${campaignId}`}
function renderSelection(){if(!selected){ui.selection.textContent='Clique un hex ou utilise une flèche autour du pion.';ui.move.disabled=true;ui.dmPing.disabled=true;return}const d=hexDistance({q:expedition.current_q,r:expedition.current_r},selected);const ping=currentPing();ui.selection.innerHTML=`<strong>(${selected.q}, ${selected.r})</strong><br>${d===1?'Adjacent':'Distance '+d}${ping.q===selected.q&&ping.r===selected.r?' · ping joueurs':''}`;const actionable=d===1&&expedition.status==='ACTIVE';ui.move.disabled=!actionable;ui.dmPing.disabled=!actionable;draw()}
function renderPois(){const known=knownPoiSet();const rows=(workbench.pois||[]).filter(p=>ui.showHiddenPois.checked||known.has(p.feature_id)||!p.requires_discovery);ui.poiCount.textContent=`${rows.length}/${workbench.pois.length}`;ui.poiList.innerHTML=rows.map(p=>`<button class="poi-row ${known.has(p.feature_id)?'known':'hidden-poi'}" data-poi="${p.id}"><strong>${esc(p.name)}</strong><span>${esc(p.kind||'POI')} · (${p.q}, ${p.r}) · ${known.has(p.feature_id)?'connu joueurs':'non découvert'}</span></button>`).join('');ui.poiList.querySelectorAll('[data-poi]').forEach(b=>b.addEventListener('click',()=>selectPoi(Number(b.dataset.poi))))}
async function selectPoi(id){selectedPoi=workbench.pois.find(p=>p.id===id)||null;if(!selectedPoi)return;selected={q:selectedPoi.q,r:selectedPoi.r};renderSelection();const state=await api(`/api/campaigns/${campaignId}/pois/${id}/state?game_minute=${expedition.current_game_minute}`);const known=(playerMap.pois||[]).some(p=>p.poi_id===selectedPoi.feature_id),here=selectedPoi.q===expedition.current_q&&selectedPoi.r===expedition.current_r;ui.poiDetail.innerHTML=`<h2>${esc(selectedPoi.name)}</h2><div class="small">${esc(selectedPoi.kind||'POI')} #${selectedPoi.feature_id} · ${state.state} · ${selectedPoi.requires_discovery?'caché / révélation MJ nécessaire':(state.visible_at_distance?'visible à distance':'visible localement')}</div><div class="poi-description"><strong>MJ</strong><br>${esc(selectedPoi.dm_description||'—')}<br><br><strong>Joueurs</strong><br>${esc(selectedPoi.player_description||'—')}</div><section><h2>Connaissance joueurs</h2><div class="knowledge-actions">${known?'<button id="hide-poi" class="secondary">Cacher aux joueurs</button>':here?'<button id="reveal-poi">Révéler aux joueurs maintenant</button>':'<button disabled>Révéler aux joueurs</button>'}<span class="small">${known?'Actuellement connu du groupe.':here?'Actuellement caché/inconnu du groupe.':'Caché/inconnu · révélation possible depuis son hex.'}</span></div></section><section><h2>Événement monde à l'instant T</h2><div class="event-grid"><label>Type<select id="event-type"><option>POI_STATE_CHANGED</option><option>POI_VISIBILITY_CHANGED</option><option>POI_DAMAGED</option><option>POI_DESTROYED</option><option>POI_REBUILT</option><option>POI_OCCUPIED</option><option>POI_ABANDONED</option></select></label><label>État<select id="event-state"><option>ACTIVE</option><option>DAMAGED</option><option>DESTROYED</option><option>OCCUPIED</option><option>ABANDONED</option></select></label><label>Visible à distance<select id="event-visible"><option value="unchanged">inchangé</option><option value="true">oui</option><option value="false">non</option></select></label><label>Note MJ<input id="event-note"></label><button id="create-event">Créer à ${formatGameDate(expedition.current_game_minute)}</button></div><p class="small">« Visible à distance » modifie la vérité du monde. Révéler/Cacher ci-dessus modifie uniquement ce que les joueurs connaissent.</p></section>`;ui.poiDetail.querySelector('#reveal-poi')?.addEventListener('click',revealPoi);ui.poiDetail.querySelector('#hide-poi')?.addEventListener('click',hidePoi);ui.poiDetail.querySelector('#create-event')?.addEventListener('click',createPoiEvent)}
async function revealPoi(){await api(`/api/campaigns/${campaignId}/dm-expeditions/${expedition.id}/pois/${selectedPoi.id}/reveal?user_id=${userId}`,{method:'POST'});toast('POI révélé aux personnages présents.');await load(false);await selectPoi(selectedPoi.id)}
async function hidePoi(){await api(`/api/campaigns/${campaignId}/dm-expeditions/${expedition.id}/pois/${selectedPoi.id}/hide?user_id=${userId}`,{method:'POST'});toast('POI caché de la carte des joueurs.');await load(false);await selectPoi(selectedPoi.id)}
async function createPoiEvent(){const type=$('#event-type').value,payload={};if(type==='POI_STATE_CHANGED')payload.state=$('#event-state').value;if($('#event-visible').value!=='unchanged')payload.visible_at_distance=$('#event-visible').value==='true';await api(`/api/campaigns/${campaignId}/dm-pois/${selectedPoi.id}/world-events?user_id=${userId}`,{method:'POST',body:JSON.stringify({game_minute:expedition.current_game_minute,expedition_id:expedition.id,event_type:type,payload,dm_note:$('#event-note').value.trim()||null})});toast('WorldEvent créé.');await load(false);await selectPoi(selectedPoi.id)}
function baseMinutes(){return Number(ui.days.value||0)*1440+Number(ui.hours.value||0)*60+Number(ui.minutes.value||0)}
async function moveTo(q,r,{clearRedo=true}={}){const duration=baseMinutes();if(duration<=0){ui.moveMessage.textContent='La durée doit être positive.';return}ui.move.disabled=true;try{const m=await api(`/api/expeditions/${expedition.id}/move`,{method:'POST',body:JSON.stringify({to_q:q,to_r:r,base_duration_minutes:duration})});if(clearRedo)redoStack=[];toast(`Déplacement résolu : ${formatDurationMinutes(m.effective_duration_minutes)}.`);selected=null;await load(false)}catch(e){ui.moveMessage.textContent=e.message}finally{renderSelection();renderHistoryButtons()}}
async function move(){if(selected)await moveTo(selected.q,selected.r)}
async function undoMove(){try{const result=await api(`/api/expeditions/${expedition.id}/move/undo`,{method:'POST'});redoStack.push(result.movement);toast('Dernier déplacement annulé.');selected=null;await load(false);renderHistoryButtons()}catch(e){toast(e.message)}}
async function redoMove(){const movement=redoStack.pop();if(!movement)return;ui.days.value=Math.floor(movement.base_duration_minutes/1440);ui.hours.value=Math.floor((movement.base_duration_minutes%1440)/60);ui.minutes.value=movement.base_duration_minutes%60;try{await moveTo(movement.to_q,movement.to_r,{clearRedo:false})}catch(e){redoStack.push(movement);throw e}renderHistoryButtons()}
function renderHistoryButtons(){ui.redoMove.disabled=redoStack.length===0}
async function loadDmPingColor(){try{const user=await api(`/api/users/${userId}`);ui.dmPingColor.value=user.ping_color||'#55c7ff'}catch{}}
async function saveDmPingColor(){try{const user=await api(`/api/users/${userId}/ping-color`,{method:'PUT',body:JSON.stringify({ping_color:ui.dmPingColor.value})});ui.dmPingColor.value=user.ping_color}catch(e){toast(e.message)}}
async function placeDmPing(){if(!selected)return;try{dmPingState={q:selected.q,r:selected.r,game_minute:expedition.current_game_minute,user_id:userId,color:ui.dmPingColor.value,created_at:new Date().toISOString()};draw();dmPingState=await api(`/api/expeditions/${expedition.id}/dm-ping?user_id=${userId}`,{method:'PUT',body:JSON.stringify({q:selected.q,r:selected.r})});draw()}catch(e){toast(e.message);dmPingState=null;draw()}}
async function load(doFit=true){if(!userId||!campaignId||!expeditionId){ui.clock.textContent='Paramètres user/campaign/expedition manquants.';return}try{terrains=Object.keys(terrains).length?terrains:await api('/api/terrains');const dashboard=await api(`/api/campaigns/${campaignId}/dm-dashboard?user_id=${userId}`);expedition=dashboard.expeditions.find(e=>e.id===expeditionId);if(!expedition)throw new Error('Expédition introuvable dans cette campagne.');workbench=await api(`/api/campaigns/${campaignId}/dm-map-workbench?user_id=${userId}&map_version_id=${expedition.current_map_version_id}`);[playerMap,visibility,pingState,dmPingState]=await Promise.all([api(`/api/expeditions/${expedition.id}/player-map`),api(`/api/expeditions/${expedition.id}/visibility`),api(`/api/expeditions/${expedition.id}/ping`),api(`/api/expeditions/${expedition.id}/dm-ping`)]);renderHeader();renderSelection();renderPois();renderHistoryButtons();if(doFit)fit();else draw()}catch(e){ui.clock.textContent=e.message}}

canvas.addEventListener('pointerdown',e=>{dragging=true;dragMoved=false;dragStart={x:e.clientX,y:e.clientY,ox:view.offsetX,oy:view.offsetY};canvas.setPointerCapture(e.pointerId)});
canvas.addEventListener('pointermove',e=>{if(!dragging)return;const dx=e.clientX-dragStart.x,dy=e.clientY-dragStart.y;if(Math.abs(dx)+Math.abs(dy)>4)dragMoved=true;view.offsetX=dragStart.ox+dx;view.offsetY=dragStart.oy+dy;draw()});
canvas.addEventListener('pointerup',e=>{if(!dragging)return;dragging=false;if(!dragMoved){const rect=canvas.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top;const arrow=arrowTargets.find(a=>Math.hypot(x-a.x,y-a.y)<=a.radius+4);if(arrow){moveTo(arrow.q,arrow.r);return}selected=screen(x,y);renderSelection()}});
canvas.addEventListener('wheel',e=>{e.preventDefault();view.scale=Math.max(.12,Math.min(3.5,view.scale*(e.deltaY<0?1.12:.89)));draw()},{passive:false});
ui.move.addEventListener('click',move);ui.dmPing.addEventListener('click',placeDmPing);ui.dmPingColor.addEventListener('change',saveDmPingColor);ui.fit.addEventListener('click',fit);ui.refresh.addEventListener('click',()=>load(false));ui.showHiddenPois.addEventListener('change',()=>{renderPois();draw()});ui.undoMove.addEventListener('click',undoMove);ui.redoMove.addEventListener('click',redoMove);
window.addEventListener('keydown',e=>{if(!(e.ctrlKey||e.metaKey))return;if(['INPUT','TEXTAREA','SELECT'].includes(e.target?.tagName))return;const key=e.key.toLowerCase();if(key==='z'){e.preventDefault();undoMove()}else if(key==='y'){e.preventDefault();redoMove()}});
new ResizeObserver(draw).observe(canvas.parentElement);authReady.then(async()=>{userId=(await import('./auth.js')).getCurrentUser()?.id||0;loadDmPingColor();load(true);setInterval(()=>{if(document.visibilityState==='visible')load(false)},700);setInterval(()=>{if(pingState?.created_at||dmPingState?.created_at)draw()},140)});

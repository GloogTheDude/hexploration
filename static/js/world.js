const $ = s => document.querySelector(s);
const params = new URL(location.href).searchParams;
const userId = Number(params.get('user'));
const campaignId = Number(params.get('campaign'));
let versionId = Number(params.get('version')) || null;
let workbench = null, dashboard = null;
let selectedHexes = [], selectedPoiId = null, selectedEdgeId = null, selectedEdgeIds = [], selectedAreaId = null;
let activeTool = 'select', spaceDown = false, undoStack = [], redoStack = [], editorDirty = false, worldMinute = 0;
let poiTemporalStates = new Map();

const ui = {
  version:$('#world-version'),load:$('#world-load'),fit:$('#world-fit'),message:$('#world-message'),status:$('#world-status'),title:$('#world-map-title'),canvas:$('#world-map-canvas'),terrainLink:$('#world-terrain-link'),dmLink:$('#world-dm-link'),selected:$('#world-selected-hex'),selectionCount:$('#world-selection-count'),
  inspectorTitle:$('#inspector-title'),inspectorSummary:$('#inspector-summary'),inspectorClose:$('#inspector-close'),
  poiForm:$('#world-poi-form'),poiId:$('#world-poi-id'),poiName:$('#world-poi-name'),poiKind:$('#world-poi-kind'),poiDescription:$('#world-poi-description'),poiLandmark:$('#world-poi-landmark'),poiNew:$('#world-poi-new'),poiDelete:$('#world-poi-delete'),poiExisting:$('#poi-existing-actions'),poiTimeline:$('#poi-timeline'),
  poiEventForm:$('#world-poi-event-form'),poiEventMinute:$('#world-poi-event-minute'),poiEventType:$('#world-poi-event-type'),poiEventPayload:$('#world-poi-event-payload'),poiEventNote:$('#world-poi-event-note'),poiEventState:$('#world-poi-event-state'),poiEventStateRow:$('#world-poi-event-state-row'),poiEventVisibility:$('#world-poi-event-visibility'),
  edgeForm:$('#world-edge-form'),edgeType:$('#world-edge-type'),edgeName:$('#world-edge-name'),edgeSelection:$('#world-edge-selection'),edgeDelete:$('#world-edge-delete'),edgeMerge:$('#world-edge-merge'),linearExisting:$('#linear-existing'),linearMeta:$('#linear-meta'),linearTimeline:$('#linear-timeline'),
  edgeEventForm:$('#world-edge-event-form'),edgeEventMinute:$('#world-edge-event-minute'),edgeEventType:$('#world-edge-event-type'),edgeEventPayload:$('#world-edge-event-payload'),edgeEventNote:$('#world-edge-event-note'),
  areaForm:$('#world-area-form'),areaType:$('#world-area-type'),areaName:$('#world-area-name'),areaDelete:$('#world-area-delete'),areaExisting:$('#area-existing'),areaMeta:$('#area-meta'),areaSelectionInfo:$('#area-selection-info'),
  linearEditForm:$('#world-linear-edit-form'),linearEditName:$('#world-linear-edit-name'),areaEditForm:$('#world-area-edit-form'),areaEditName:$('#world-area-edit-name'),
  poiEventId:$('#world-poi-event-id'),poiEventList:$('#world-poi-event-list'),poiEventNew:$('#world-poi-event-new'),poiEventCancel:$('#world-poi-event-cancel'),poiEventSubmit:$('#world-poi-event-submit'),poiEventFeedback:$('#world-poi-event-feedback'),edgeEventId:$('#world-edge-event-id'),edgeEventList:$('#world-edge-event-list'),edgeEventNew:$('#world-edge-event-new'),edgeEventCancel:$('#world-edge-event-cancel'),edgeEventSubmit:$('#world-edge-event-submit'),edgeEventFeedback:$('#world-edge-event-feedback'),
  poiList:$('#world-poi-list'),edgeList:$('#world-edge-list'),areaList:$('#world-area-list'),browser:$('#world-object-browser'),browserToggle:$('#world-objects-toggle'),browserClose:$('#world-objects-close'),browserSearch:$('#world-object-search'),undo:$('#world-undo'),redo:$('#world-redo'),save:$('#world-save'),saveState:$('#world-save-state'),worldTime:$('#world-time'),worldTimeApply:$('#world-time-apply'),modeLabel:$('#world-mode-label'),exportPng:$('#world-export-png'),exportJpeg:$('#world-export-jpeg'),exportPdf:$('#world-export-pdf'),exportLayer:$('#world-export-layer')
};
const TERRAIN_COLORS={PLAIN:'#88cc66',SEA:'#245f8f',SWAMP:'#496d3a',HILL:'#7aa04f',FOREST:'#356f3b',DEEP_FOREST:'#204d2a',LOW_MOUNTAIN:'#68757b',MOUNTAIN:'#596164',HIGH_MOUNTAIN:'#40484d'};
const SQRT3=Math.sqrt(3), HEX_DIRS=[[1,0],[1,-1],[0,-1],[-1,0],[-1,1],[0,1]];
const view={scale:1,panX:0,panY:0,dragging:false,moved:false,lastX:0,lastY:0};
let initialFitPending=false, fitRetryFrame=null;

async function api(path,options={}){const response=await fetch(path,{headers:{'Content-Type':'application/json',...(options.headers||{})},...options});if(!response.ok){let detail=`${response.status} ${response.statusText}`;try{const body=await response.json();detail=typeof body.detail==='string'?body.detail:JSON.stringify(body.detail)}catch(_){}throw new Error(detail)}return response.status===204?null:response.json()}
function esc(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function parseJSON(input){
  const raw=typeof input==='string'?input:input?.value;
  try{return JSON.parse((raw??'').trim()||'{}')}catch(_){throw new Error('Payload JSON invalide')}
}
function msg(text,error=false){ui.message.textContent=text||'';ui.message.classList.toggle('error',error)}
function setDirty(value=true){editorDirty=value;ui.saveState.textContent=value?'Modifié':'Sauvegardé';ui.saveState.classList.toggle('dirty',value)}
async function saveCheckpoint(){if(!workbench)return;await editorSnapshot();setDirty(false);msg('État du World Editor sauvegardé. Les opérations restent persistées transactionnellement au fil de l’édition.')}

const GAME_MONTHS_PER_YEAR=12,GAME_DAYS_PER_MONTH=30,GAME_MINUTES_PER_DAY=1440,GAME_MINUTES_PER_MONTH=43200,GAME_MINUTES_PER_YEAR=518400;
function datePartsFromGameMinute(total){total=Math.max(0,Math.floor(Number(total)||0));const year=Math.floor(total/GAME_MINUTES_PER_YEAR);total%=GAME_MINUTES_PER_YEAR;const month=Math.floor(total/GAME_MINUTES_PER_MONTH)+1;total%=GAME_MINUTES_PER_MONTH;const day=Math.floor(total/GAME_MINUTES_PER_DAY)+1;total%=GAME_MINUTES_PER_DAY;const hour=Math.floor(total/60),minute=total%60;return{year,month,day,hour,minute}}
function gameMinuteFromDatePrefix(prefix){const get=s=>Number(document.getElementById(`${prefix}-${s}`)?.value);const year=get('year'),month=get('month'),day=get('day'),hour=get('hour'),minute=get('minute');if(!Number.isInteger(year)||year<0)throw new Error('Année invalide');if(!Number.isInteger(month)||month<1||month>12)throw new Error('Mois invalide (1–12)');if(!Number.isInteger(day)||day<1||day>30)throw new Error('Jour invalide (1–30)');if(!Number.isInteger(hour)||hour<0||hour>23)throw new Error('Heure invalide (0–23)');if(!Number.isInteger(minute)||minute<0||minute>59)throw new Error('Minute invalide (0–59)');return year*GAME_MINUTES_PER_YEAR+(month-1)*GAME_MINUTES_PER_MONTH+(day-1)*GAME_MINUTES_PER_DAY+hour*60+minute}
function setDatePrefix(prefix,total){const p=datePartsFromGameMinute(total);for(const k of['year','month','day','hour','minute']){const el=document.getElementById(`${prefix}-${k}`);if(el)el.value=String(p[k])}}
function formatGameDate(total){const p=datePartsFromGameMinute(total);return `A${p.year} · M${p.month} · J${p.day} · ${String(p.hour).padStart(2,'0')}:${String(p.minute).padStart(2,'0')}`}
function syncHiddenMinute(prefix,hidden){const value=gameMinuteFromDatePrefix(prefix);hidden.value=String(value);return value}
function configurePoiEventFields(setDefaults=false){const type=ui.poiEventType.value;ui.poiEventStateRow.classList.toggle('hidden',type!=='POI_STATE_CHANGED');if(setDefaults){if(type==='POI_CREATED'||type==='POI_REBUILT')ui.poiEventVisibility.value='true';else if(type==='POI_DESTROYED')ui.poiEventVisibility.value='false';else if(type==='POI_VISIBILITY_CHANGED'&&ui.poiEventVisibility.value==='unchanged')ui.poiEventVisibility.value='false'}}
async function loadPoiTemporalStates(){poiTemporalStates=new Map();if(!workbench)return;const rows=await Promise.all((workbench.pois||[]).map(async p=>{try{return[p.id,await api(`/api/campaigns/${campaignId}/pois/${p.id}/state?game_minute=${worldMinute}`)]}catch(_){return[p.id,null]}}));for(const[id,state]of rows)if(state)poiTemporalStates.set(id,state)}
async function applyWorldMinute(){try{worldMinute=syncHiddenMinute('world-time',ui.worldTime);await loadPoiTemporalStates();updateInspector();renderLists();draw();msg(`WorldState · ${formatGameDate(worldMinute)} · minute ${worldMinute}.`)}catch(err){msg(err.message,true)}}

function axialDistance(a,b){return (Math.abs(a.q-b.q)+Math.abs(a.q+a.r-b.q-b.r)+Math.abs(a.r-b.r))/2}
function hexWorld(q,r,size=34){return{x:size*1.5*q,y:size*SQRT3*(r+q/2)}}
function polygon(ctx,x,y,size){ctx.beginPath();for(let i=0;i<6;i++){const a=Math.PI/3*i,px=x+size*Math.cos(a),py=y+size*Math.sin(a);i?ctx.lineTo(px,py):ctx.moveTo(px,py)}ctx.closePath()}
function offsetBounds(q,r){if(!workbench)return false;const col=q+Math.floor(workbench.width/2),row=r+Math.floor(workbench.height/2)+Math.floor((q+(q&1))/2);return col>=0&&col<workbench.width&&row>=0&&row<workbench.height}
function materialized(q,r){return workbench?.hexes.find(h=>h.q===q&&h.r===r)||null}
function virtualHex(q,r){if(!offsetBounds(q,r))return null;const h=materialized(q,r);if(h)return h;const key=workbench.default_terrain_key||'SEA';return{id:null,q,r,terrain_key:key,elevation:0,visibility_score:0,travel_cost:key==='SEA'?2:1,extra_data:{}}}
function sameHex(a,b){return a&&b&&a.q===b.q&&a.r===b.r}
function screenCenter(q,r){const rect=ui.canvas.getBoundingClientRect(),p=hexWorld(q,r);return{x:rect.width/2+view.panX+p.x*view.scale,y:rect.height/2+view.panY+p.y*view.scale}}
function featureGroups(){const groups=new Map();for(const e of workbench?.edges||[]){const key=`${e.feature_type}:${e.feature_id}`;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(e)}for(const g of groups.values())g.sort((a,b)=>(a.segment_index??0)-(b.segment_index??0));return [...groups.values()]}
function orderedPath(group){if(!group.length)return[];const pts=[];for(const e of group){const pf=e.extra_data?.path_from||{q:e.from_q,r:e.from_r},pt=e.extra_data?.path_to||{q:e.to_q,r:e.to_r};if(!pts.length)pts.push(pf);const last=pts[pts.length-1];if(last.q!==pf.q||last.r!==pf.r)pts.push(pf);pts.push(pt)}return pts.filter((p,i,a)=>i===0||p.q!==a[i-1].q||p.r!==a[i-1].r)}
function edgeGroupSelected(group){return group.some(e=>selectedEdgeIds.includes(e.id))}
function selectedEdgeGroups(){return featureGroups().filter(edgeGroupSelected)}
function waterAreaAt(h){return (workbench?.areas||[]).find(a=>['LAKE','INLAND_SEA'].includes(a.feature_type)&&(a.cells||[]).some(c=>sameHex(c,h)))||null}
function isWaterHex(h){if(!h)return false;const vh=virtualHex(h.q,h.r);return vh?.terrain_key==='SEA'||Boolean(waterAreaAt(h))}
function shorelinePoint(water,land,center){const a=center(water),b=center(land);return{x:(a.x+b.x)/2,y:(a.y+b.y)/2}}
function riverDisplayPoints(group,center){
  const path=orderedPath(group);if(path.length<2)return path.map(center);const pts=path.map(center);
  if(isWaterHex(path[0])&&!isWaterHex(path[1]))pts[0]=shorelinePoint(path[0],path[1],center);
  const n=path.length;if(isWaterHex(path[n-1])&&!isWaterHex(path[n-2]))pts[n-1]=shorelinePoint(path[n-1],path[n-2],center);
  return pts
}
function fitView(){
  if(!workbench)return false;
  const rect=ui.canvas.getBoundingClientRect();
  // The editor can be loaded before CSS Grid has given the stage its final size.
  // Never fit against a 0×0/near-zero canvas: that collapses the whole map to a dot.
  if(rect.width<80||rect.height<80){
    initialFitPending=true;
    if(fitRetryFrame===null)fitRetryFrame=requestAnimationFrame(()=>{fitRetryFrame=null;fitView()});
    return false;
  }
  const q0=-Math.floor(workbench.width/2),q1=q0+workbench.width-1,
    r0=-Math.floor(workbench.height/2)-Math.floor((q0+(q0&1))/2),
    r1=workbench.height-1-Math.floor(workbench.height/2)-Math.floor((q1+(q1&1))/2),
    a=hexWorld(q0,r0),b=hexWorld(q1,r1),
    spanX=Math.abs(b.x-a.x)+100,spanY=Math.abs(b.y-a.y)+100;
  view.scale=Math.max(.0005,Math.min(rect.width/spanX,rect.height/spanY,1.35));
  view.panX=-(a.x+b.x)/2*view.scale;
  view.panY=-(a.y+b.y)/2*view.scale;
  initialFitPending=false;
  draw();
  return true;
}

function drawArea(ctx,area,center,size){
  const cells=area.cells||[],water=['LAKE','INLAND_SEA'].includes(area.feature_type),selected=area.id===selectedAreaId,set=new Set(cells.map(c=>`${c.q},${c.r}`));
  ctx.save();
  // Water areas should read as one continuous body, not as highlighted individual tiles.
  // Slightly overlap the area fill so the base-map grid disappears inside the lake.
  ctx.fillStyle=water?(area.feature_type==='LAKE'?'rgba(43,145,196,.72)':'rgba(30,103,158,.76)'):'rgba(218,180,89,.28)';
  for(const cell of cells){const c=center(cell);polygon(ctx,c.x,c.y,Math.max(3,size*1.005));ctx.fill()}
  if(size>3){
    const rad=size*.965;
    const boundary=new Path2D();
    for(const cell of cells){
      const c=center(cell);
      for(let i=0;i<6;i++){
        const [dq,dr]=HEX_DIRS[i];
        if(set.has(`${cell.q+dq},${cell.r+dr}`))continue;
        // For the flat-top axial layout, neighbour i faces the side centred on
        // 30° - i*60°. The old +/-30° formula was rotated by one half-side,
        // which produced the crossed / star-shaped lake borders.
        const a1=-i*Math.PI/3,a2=(1-i)*Math.PI/3;
        boundary.moveTo(c.x+rad*Math.cos(a1),c.y+rad*Math.sin(a1));
        boundary.lineTo(c.x+rad*Math.cos(a2),c.y+rad*Math.sin(a2));
      }
    }
    ctx.lineCap='round';ctx.lineJoin='round';
    // Dark bank underneath + thin bright shoreline on top keeps the contour
    // readable without drawing internal hex borders.
    ctx.strokeStyle=selected?'rgba(105,79,20,.95)':water?'rgba(10,55,76,.95)':'rgba(92,70,28,.9)';
    ctx.lineWidth=selected?Math.max(5,5*view.scale):Math.max(3,4*view.scale);ctx.stroke(boundary);
    ctx.strokeStyle=selected?'#ffd166':water?'rgba(126,218,255,.95)':'rgba(236,201,112,.85)';
    ctx.lineWidth=selected?Math.max(2.5,2.4*view.scale):Math.max(1.25,1.5*view.scale);ctx.stroke(boundary);
  }
  ctx.restore();
}
function corridorKey(edge){const d=edge.extra_data||{},a=d.path_from||{q:edge.from_q,r:edge.from_r},b=d.path_to||{q:edge.to_q,r:edge.to_r};const ak=`${a.q},${a.r}`,bk=`${b.q},${b.r}`;return ak<bk?`${ak}|${bk}`:`${bk}|${ak}`}
function sharedCorridorKeys(group,allGroups){
  if(group[0]?.feature_type!=='ROAD')return new Set();
  const riverKeys=new Set();
  for(const other of allGroups){if(other[0]?.feature_type!=='RIVER')continue;for(const edge of other)riverKeys.add(corridorKey(edge))}
  return new Set(group.map(corridorKey).filter(key=>riverKeys.has(key)));
}
function offsetPolyline(points,amount){if(!amount||points.length<2)return points;const normals=[];for(let i=0;i<points.length-1;i++){const a=points[i],b=points[i+1],dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1;normals.push({x:-dy/len,y:dx/len})}return points.map((p,i)=>{let n;if(i===0)n=normals[0];else if(i===points.length-1)n=normals[normals.length-1];else{const x=normals[i-1].x+normals[i].x,y=normals[i-1].y+normals[i].y,l=Math.hypot(x,y)||1;n={x:x/l,y:y/l}}return{x:p.x+n.x*amount,y:p.y+n.y*amount}})}
function tracePolyline(ctx,points,smooth=false){
  if(points.length<2)return;
  ctx.beginPath();ctx.moveTo(points[0].x,points[0].y);
  if(!smooth||points.length===2){for(let i=1;i<points.length;i++)ctx.lineTo(points[i].x,points[i].y);return}
  // One continuous quadratic path removes the visible segment seams while
  // still following the exact ordered hex path.
  for(let i=1;i<points.length-1;i++){
    const p=points[i],n=points[i+1],mx=(p.x+n.x)/2,my=(p.y+n.y)/2;
    ctx.quadraticCurveTo(p.x,p.y,mx,my);
  }
  ctx.lineTo(points[points.length-1].x,points[points.length-1].y);
}
function riverSegmentKey(a,b){const ak=`${a.q},${a.r}`,bk=`${b.q},${b.r}`;return ak<bk?`${ak}|${bk}`:`${bk}|${ak}`}
function riverNetwork(groups){
  const segments=new Map(),degree=new Map();
  for(const group of groups.filter(g=>g[0]?.feature_type==='RIVER')){
    for(const edge of group){
      const d=edge.extra_data||{},a=d.path_from||{q:edge.from_q,r:edge.from_r},b=d.path_to||{q:edge.to_q,r:edge.to_r},key=riverSegmentKey(a,b);
      const clipStart=isWaterHex(a)&&!isWaterHex(b),clipEnd=isWaterHex(b)&&!isWaterHex(a);
      if(!segments.has(key))segments.set(key,{a,b,clipStart:Boolean(clipStart),clipEnd:Boolean(clipEnd)});
      else{const seg=segments.get(key);seg.clipStart ||= Boolean(clipStart);seg.clipEnd ||= Boolean(clipEnd)}
      const ak=`${a.q},${a.r}`,bk=`${b.q},${b.r}`;if(!clipStart)degree.set(ak,(degree.get(ak)||0)+1);if(!clipEnd)degree.set(bk,(degree.get(bk)||0)+1);
    }
  }
  return{segments:[...segments.values()],degree};
}
function strokeRiverNetwork(ctx,groups,center){
  const net=riverNetwork(groups);if(!net.segments.length)return;
  const stroke=(style,width)=>{ctx.beginPath();for(const {a,b,clipStart,clipEnd} of net.segments){let p=center(a),q=center(b);if(clipStart)p=shorelinePoint(a,b,center);if(clipEnd)q=shorelinePoint(b,a,center);ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y)}ctx.strokeStyle=style;ctx.lineWidth=width;ctx.lineCap='round';ctx.lineJoin='round';ctx.stroke();};
  ctx.save();
  stroke('rgba(12,55,76,.95)',Math.max(6,11*view.scale));
  stroke('#55c5f2',Math.max(3.5,6.5*view.scale));
  // Fill confluence nodes explicitly. A merged river feature is a graph, not
  // an ordered polyline, so 3+ incoming branches share one visual water node.
  for(const [key,count] of net.degree){if(count<3)continue;const [q,r]=key.split(',').map(Number),p=center({q,r});ctx.beginPath();ctx.arc(p.x,p.y,Math.max(1.75,3.25*view.scale),0,Math.PI*2);ctx.fillStyle='#55c5f2';ctx.fill();}
  // Selection is also rendered from concrete corridors. Using orderedPath()
  // here would invent fake connectors when one semantic river has branches.
  for(const selected of groups.filter(g=>g[0]?.feature_type==='RIVER'&&edgeGroupSelected(g))){
    const selectedStroke=(style,width)=>{ctx.beginPath();for(const edge of selected){const d=edge.extra_data||{},a=d.path_from||{q:edge.from_q,r:edge.from_r},b=d.path_to||{q:edge.to_q,r:edge.to_r};let p=center(a),q=center(b);if(isWaterHex(a)&&!isWaterHex(b))p=shorelinePoint(a,b,center);if(isWaterHex(b)&&!isWaterHex(a))q=shorelinePoint(b,a,center);ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y)}ctx.strokeStyle=style;ctx.lineWidth=width;ctx.lineCap='round';ctx.lineJoin='round';ctx.stroke()};
    selectedStroke('#ffffff',Math.max(8,13*view.scale));selectedStroke('#55c5f2',Math.max(3.5,6.5*view.scale));
  }
  ctx.restore();
}
function edgePoints(edge,center){const d=edge.extra_data||{},a=d.path_from||{q:edge.from_q,r:edge.from_r},b=d.path_to||{q:edge.to_q,r:edge.to_r};return[center(a),center(b)]}
function drawLinear(ctx,group,allGroups,center){
  const f=group[0];if(f.feature_type==='RIVER')return;
  const selected=edgeGroupSelected(group),base=f.feature_type==='BRIDGE'?'#ead9b9':'#d9b26f';
  const sharedKeys=sharedCorridorKeys(group,allGroups);
  ctx.save();ctx.lineJoin='round';ctx.lineCap='round';
  // A ROAD can share only part of its graph with a RIVER. Offset exactly those
  // physical corridors; offsetting the whole semantic road creates ghost dots
  // at every unshifted junction when just one segment follows a river.
  const segments=group.map(edge=>{let pts=edgePoints(edge,center);const shared=sharedKeys.has(corridorKey(edge));if(shared)pts=offsetPolyline(pts,Math.max(4,5*view.scale));return{pts,shared,edge}});
  const stroke=(style,width)=>{ctx.beginPath();for(const {pts} of segments){ctx.moveTo(pts[0].x,pts[0].y);ctx.lineTo(pts[1].x,pts[1].y)}ctx.strokeStyle=style;ctx.lineWidth=width;ctx.stroke()};
  if(selected)stroke('#ffffff',Math.max(7,9*view.scale));
  stroke(base,Math.max(2.5,4.2*view.scale));
  // Junction fillers are only valid when all incident ROAD segments meet at
  // the canonical node. A shared ROAD/RIVER segment is visually offset, so a
  // filler at the original center would appear as the beige dots seen on the
  // road. Round caps already close the shifted corridor cleanly.
  if(f.feature_type==='ROAD'){
    const counts=new Map(),pos=new Map(),sharedNodes=new Set();
    for(const {edge,shared} of segments){const d=edge.extra_data||{},a=d.path_from||{q:edge.from_q,r:edge.from_r},b=d.path_to||{q:edge.to_q,r:edge.to_r};for(const h of[a,b]){const k=`${h.q},${h.r}`;counts.set(k,(counts.get(k)||0)+1);pos.set(k,center(h));if(shared)sharedNodes.add(k)}}
    for(const[k,n]of counts){if(n<2||sharedNodes.has(k))continue;const p=pos.get(k);ctx.beginPath();ctx.arc(p.x,p.y,Math.max(1.4,2.1*view.scale),0,Math.PI*2);ctx.fillStyle=base;ctx.fill()}
  }
  ctx.restore();
}
function draw(){const canvas=ui.canvas,ctx=canvas.getContext('2d'),rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2),width=Math.max(1,Math.round(rect.width*dpr)),height=Math.max(1,Math.round(rect.height*dpr));if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height}ctx.setTransform(dpr,0,0,dpr,0,0);const w=rect.width,h=rect.height;ctx.fillStyle='#071016';ctx.fillRect(0,0,w,h);if(!workbench)return;const size=32*view.scale,cx=w/2+view.panX,cy=h/2+view.panY,center=hx=>{const p=hexWorld(hx.q,hx.r);return{x:cx+p.x*view.scale,y:cy+p.y*view.scale}};
  if(size<1.2&&workbench.default_terrain_key){const approxW=(1.5*34*(workbench.width-1)+68)*view.scale,approxH=SQRT3*34*(workbench.height+.5)*view.scale;ctx.fillStyle=TERRAIN_COLORS[workbench.default_terrain_key]||'#245f8f';ctx.fillRect(cx-approxW/2,cy-approxH/2,approxW,approxH);for(const hx of workbench.hexes){const c=center(hx);ctx.fillStyle=TERRAIN_COLORS[hx.terrain_key]||'#52636e';ctx.fillRect(c.x-1.5,c.y-1.5,3,3)}}else{const worldLeft=(-cx-50)/view.scale,worldRight=(w-cx+50)/view.scale;let c0=Math.max(0,Math.floor(worldLeft/(1.5*34)+workbench.width/2)-2),c1=Math.min(workbench.width-1,Math.ceil(worldRight/(1.5*34)+workbench.width/2)+2);for(let col=c0;col<=c1;col++){const q=col-Math.floor(workbench.width/2),parity=q&1,worldTop=(-cy-50)/view.scale,worldBottom=(h-cy+50)/view.scale;let row0=Math.max(0,Math.floor(worldTop/(SQRT3*34)+workbench.height/2+parity/2)-2),row1=Math.min(workbench.height-1,Math.ceil(worldBottom/(SQRT3*34)+workbench.height/2+parity/2)+2);for(let row=row0;row<=row1;row++){const r=row-Math.floor(workbench.height/2)-Math.floor((q+parity)/2),hx=virtualHex(q,r),c=center(hx);polygon(ctx,c.x,c.y,size*.96);ctx.fillStyle=TERRAIN_COLORS[hx.terrain_key]||'#52636e';ctx.fill();ctx.strokeStyle='#172a38';ctx.lineWidth=1.2;ctx.stroke()}}}
  for(const area of workbench.areas||[])drawArea(ctx,area,center,size);
  const groups=featureGroups();groups.sort((a,b)=>({RIVER:0,ROAD:1,BRIDGE:2,PASSAGE:3,TRAVERSAL:4}[a[0]?.feature_type]??9)-({RIVER:0,ROAD:1,BRIDGE:2,PASSAGE:3,TRAVERSAL:4}[b[0]?.feature_type]??9));strokeRiverNetwork(ctx,groups,center);for(const g of groups)drawLinear(ctx,g,groups,center);
  for(const p of workbench.pois||[]){const temporal=poiTemporalStates.get(p.id),state=temporal?.state||'ACTIVE';if(temporal?.exists===false&&state!=='DESTROYED')continue;const c=center(p),rad=Math.max(4.5,6*view.scale),visible=temporal?.visible_at_distance??p.is_landmark;if(p.id===selectedPoiId){ctx.beginPath();ctx.arc(c.x,c.y,rad+3.2,0,Math.PI*2);ctx.strokeStyle='#65d8ff';ctx.lineWidth=2.4;ctx.stroke()}ctx.beginPath();ctx.arc(c.x,c.y,rad,0,Math.PI*2);ctx.fillStyle='#ffd84d';ctx.fill();ctx.strokeStyle=visible?'#111820':'#ffffff';ctx.lineWidth=2.6;ctx.stroke();if(state==='DESTROYED'){ctx.beginPath();ctx.moveTo(c.x-rad*.55,c.y-rad*.55);ctx.lineTo(c.x+rad*.55,c.y+rad*.55);ctx.moveTo(c.x+rad*.55,c.y-rad*.55);ctx.lineTo(c.x-rad*.55,c.y+rad*.55);ctx.strokeStyle='#8e3d46';ctx.lineWidth=Math.max(1.5,2*view.scale);ctx.stroke()}if(view.scale>.55){ctx.fillStyle='#f5f8fb';ctx.font='11px sans-serif';ctx.fillText(p.name,c.x+9,c.y-8)}}
  selectedHexes.forEach((hx,i)=>{const c=center(hx);polygon(ctx,c.x,c.y,Math.max(4,size*.88));ctx.strokeStyle=i===selectedHexes.length-1?'#7bc3ff':'#b7ddff';ctx.lineWidth=i===selectedHexes.length-1?4:3;ctx.stroke()});
}

function nearestHex(x,y){if(!workbench)return null;const rect=ui.canvas.getBoundingClientRect(),cx=rect.width/2+view.panX,cy=rect.height/2+view.panY,wx=(x-cx)/view.scale,wy=(y-cy)/view.scale,size=34,qf=(2/3*wx)/size,rf=(-1/3*wx+SQRT3/3*wy)/size;let xq=qf,z=rf,yc=-xq-z,rx=Math.round(xq),ry=Math.round(yc),rz=Math.round(z),xd=Math.abs(rx-xq),yd=Math.abs(ry-yc),zd=Math.abs(rz-z);if(xd>yd&&xd>zd)rx=-ry-rz;else if(yd>zd)ry=-rx-rz;else rz=-rx-ry;return virtualHex(rx,rz)}
function pointSegDist(p,a,b){const dx=b.x-a.x,dy=b.y-a.y,l2=dx*dx+dy*dy;if(!l2)return Math.hypot(p.x-a.x,p.y-a.y);let t=((p.x-a.x)*dx+(p.y-a.y)*dy)/l2;t=Math.max(0,Math.min(1,t));return Math.hypot(p.x-(a.x+t*dx),p.y-(a.y+t*dy))}
function hitObject(x,y){for(const p of workbench?.pois||[]){const temporal=poiTemporalStates.get(p.id);if(temporal?.exists===false&&(temporal?.state||'ACTIVE')!=='DESTROYED')continue;const c=screenCenter(p.q,p.r);if(Math.hypot(x-c.x,y-c.y)<=12)return{type:'poi',id:p.id}}let best=null,bestD=10;for(const g of featureGroups()){for(const edge of g){const pts=edgePoints(edge,h=>screenCenter(h.q,h.r)),d=pointSegDist({x,y},pts[0],pts[1]);if(d<bestD){bestD=d;best={type:'edge',id:g[0].id}}}}return best}

function setTool(tool){activeTool=tool;document.querySelectorAll('.tool[data-tool]').forEach(b=>b.classList.toggle('active',b.dataset.tool===tool));selectedPoiId=null;selectedEdgeId=null;selectedEdgeIds=[];selectedAreaId=null;selectedHexes=[];if(tool==='road')ui.edgeType.value='ROAD';if(tool==='river')ui.edgeType.value='RIVER';if(tool==='bridge')ui.edgeType.value='BRIDGE';showPanel(tool==='poi'?'poi':['road','river','bridge'].includes(tool)?'linear':tool==='area'?'area':'selection');updateInspector();draw()}
function showPanel(name){document.querySelectorAll('.inspector-panel').forEach(p=>p.classList.toggle('active',p.id===`panel-${name}`))}
function clearObjectSelection(){selectedPoiId=null;selectedEdgeId=null;selectedEdgeIds=[];selectedAreaId=null;selectedHexes=[];clearPoiForm(false);if(activeTool!=='select')setTool(activeTool);else{showPanel('selection');updateInspector();draw()}}
function updateInspector(){ui.selectionCount.textContent=`${selectedHexes.length} hex`;renderSelection();renderEdgeSelection();ui.areaSelectionInfo.textContent=selectedHexes.length?`${selectedHexes.length} hex dans la future zone.`:'Clique les hex à inclure dans la zone.';const p=workbench?.pois.find(x=>x.id===selectedPoiId),selectedGroups=selectedEdgeGroups(),g=selectedGroups.length===1?selectedGroups[0]:null,a=workbench?.areas.find(x=>x.id===selectedAreaId);if(p){const temporal=poiTemporalStates.get(p.id),state=temporal?.state||'ACTIVE',exists=temporal?.exists!==false||state==='DESTROYED',visible=temporal?.visible_at_distance??p.is_landmark;ui.inspectorTitle.textContent=p.name;ui.inspectorSummary.innerHTML=`${esc(p.kind||'POI')} #${p.feature_id} · (${p.q}, ${p.r})<div class="poi-world-state"><strong>${exists?esc(state):'PAS ENCORE CRÉÉ'}</strong> @ ${esc(formatGameDate(worldMinute))}${exists?` · ${visible?'visible de loin':'non visible de loin'}`:''}</div>`;showPanel('poi');ui.poiExisting.classList.remove('hidden');ui.poiTimeline.classList.remove('hidden');loadTargetTimeline('POI',p.feature_id,'poi')}else if(selectedGroups.length>1){const types=[...new Set(selectedGroups.map(x=>x[0].feature_type))],mergeable=types.length===1&&['ROAD','RIVER'].includes(types[0]);ui.inspectorTitle.textContent=`${selectedGroups.length} features sélectionnées`;ui.inspectorSummary.textContent=`${selectedGroups.reduce((n,x)=>n+x.length,0)} segment(s) · ${types.join(', ')}`;showPanel('linear');ui.edgeForm.classList.add('hidden');ui.linearExisting.classList.remove('hidden');ui.linearEditForm.classList.add('hidden');ui.linearMeta.innerHTML=`<strong>${selectedGroups.length} features</strong><br>${selectedGroups.map(x=>`${esc(x[0].feature_type)} #${x[0].feature_id}`).join(' · ')}`;ui.edgeMerge.classList.toggle('hidden',!mergeable);ui.edgeDelete.classList.add('hidden');ui.linearTimeline.classList.add('hidden');}else if(g){const f=g[0];ui.inspectorTitle.textContent=f.name||f.feature_type;ui.inspectorSummary.textContent=`${f.feature_type} #${f.feature_id} · ${g.length} segment(s)`;showPanel('linear');ui.edgeForm.classList.add('hidden');ui.linearExisting.classList.remove('hidden');ui.linearEditForm.classList.remove('hidden');ui.linearMeta.innerHTML=`<strong>${esc(f.feature_type)} #${f.feature_id}</strong><br>${g.length} segment(s) · ${orderedPath(g).length} points`;ui.linearEditName.value=f.name||'';loadTargetTimeline(f.feature_type,f.feature_id,'edge');ui.edgeMerge.classList.add('hidden');ui.edgeDelete.classList.remove('hidden');ui.linearTimeline.classList.remove('hidden');}else if(a){ui.inspectorTitle.textContent=a.name||a.feature_type;ui.inspectorSummary.textContent=`${a.feature_type} #${a.feature_id} · ${(a.cells||[]).length} hex`;showPanel('area');ui.areaForm.classList.add('hidden');ui.areaExisting.classList.remove('hidden');ui.areaMeta.innerHTML=`<strong>${esc(a.feature_type)} #${a.feature_id}</strong><br>${(a.cells||[]).length} hex`;ui.areaEditName.value=a.name||'';}else{ui.poiExisting.classList.add('hidden');ui.poiTimeline.classList.add('hidden');ui.linearExisting.classList.add('hidden');ui.linearEditForm.classList.remove('hidden');ui.edgeMerge.classList.add('hidden');ui.edgeDelete.classList.remove('hidden');ui.linearTimeline.classList.remove('hidden');ui.edgeForm.classList.remove('hidden');ui.areaExisting.classList.add('hidden');ui.areaForm.classList.remove('hidden');const labels={select:'Sélection',poi:'Nouveau POI',road:'Nouvelle route',river:'Nouvelle rivière',area:'Nouvelle zone'};ui.inspectorTitle.textContent=labels[activeTool]||'Sélection';ui.inspectorSummary.textContent=activeTool==='select'?'Clic = hex/objet · Shift+clic force l’hex · Alt+clic = zone · Delete = nettoyer hex.':activeTool==='river'?(selectedHexes.length?`${selectedHexes.length} waypoint(s) · sélectionne directement un hex SEA/LAKE pour connecter l’eau.`:'Clique les waypoints, y compris l’hex SEA/LAKE exact pour une connexion à l’eau.'):(selectedHexes.length?`${selectedHexes.length} hex sélectionné(s).`:'Clique sur la carte pour commencer.')}renderLists()}
function renderSelection(){if(!selectedHexes.length){ui.selected.innerHTML='Aucun hex sélectionné.';return}ui.selected.innerHTML=`<strong>${selectedHexes.map(h=>`(${h.q}, ${h.r})`).join(' → ')}</strong><div class="hint">${selectedHexes.length===1?esc(selectedHexes[0].terrain_key):'Ordre = waypoints'}</div>`}
function renderEdgeSelection(){if(!selectedHexes.length)ui.edgeSelection.textContent='Aucun waypoint.';else ui.edgeSelection.textContent=`${selectedHexes.length} waypoint(s) · ${selectedHexes.map(h=>`(${h.q},${h.r})`).join(' → ')}`}
function selectHex(h,additive=false){if(!h)return;if(!additive)selectedHexes=[h];else{const i=selectedHexes.findIndex(x=>sameHex(x,h));i>=0?selectedHexes.splice(i,1):selectedHexes.push(h)}selectedPoiId=selectedEdgeId=selectedAreaId=null;selectedEdgeIds=[];updateInspector();draw()}
function addWaypoint(h){if(!h)return;if(selectedHexes.length&&sameHex(selectedHexes[selectedHexes.length-1],h))return;selectedHexes.push(h);updateInspector();draw()}
function toggleAreaHex(h){if(!h)return;const i=selectedHexes.findIndex(x=>sameHex(x,h));i>=0?selectedHexes.splice(i,1):selectedHexes.push(h);updateInspector();draw()}
function selectPoi(id){const p=workbench?.pois.find(x=>x.id===id);if(!p)return;activeTool='select';document.querySelectorAll('.tool[data-tool]').forEach(b=>b.classList.toggle('active',b.dataset.tool==='select'));selectedPoiId=id;selectedEdgeId=selectedAreaId=null;selectedEdgeIds=[];selectedHexes=[virtualHex(p.q,p.r)];ui.poiId.value=p.id;ui.poiName.value=p.name;ui.poiKind.value=p.kind||'';ui.poiDescription.value=p.dm_description||'';ui.poiLandmark.checked=p.is_landmark;updateInspector();draw()}
function selectEdge(id,additive=false){activeTool='select';document.querySelectorAll('.tool[data-tool]').forEach(b=>b.classList.toggle('active',b.dataset.tool==='select'));const group=featureGroups().find(g=>g.some(e=>e.id===id));if(!group)return;const rep=group[0].id;if(additive){const i=selectedEdgeIds.indexOf(rep);i>=0?selectedEdgeIds.splice(i,1):selectedEdgeIds.push(rep)}else selectedEdgeIds=[rep];selectedEdgeId=selectedEdgeIds.length?selectedEdgeIds[selectedEdgeIds.length-1]:null;selectedPoiId=selectedAreaId=null;selectedHexes=[];updateInspector();draw()}
function selectArea(id){activeTool='select';document.querySelectorAll('.tool[data-tool]').forEach(b=>b.classList.toggle('active',b.dataset.tool==='select'));selectedAreaId=id;selectedPoiId=selectedEdgeId=null;selectedEdgeIds=[];selectedHexes=[];updateInspector();draw()}
function clearPoiForm(redraw=true){ui.poiId.value='';ui.poiName.value='';ui.poiKind.value='';ui.poiDescription.value='';ui.poiLandmark.checked=false;if(redraw)draw()}

function renderLists(){const q=(ui.browserSearch?.value||'').trim().toLowerCase(),match=(...xs)=>!q||xs.some(x=>String(x||'').toLowerCase().includes(q));ui.poiList.innerHTML=(workbench?.pois||[]).filter(p=>match(p.name,p.kind,'poi')).map(p=>{const temporal=poiTemporalStates.get(p.id),state=temporal?.state||'ACTIVE',exists=temporal?.exists!==false||state==='DESTROYED',visible=temporal?.visible_at_distance??p.is_landmark;return`<button type="button" class="world-row ${p.id===selectedPoiId?'selected':''} ${exists?'':'future'}" data-poi="${p.id}"><strong>${esc(p.name)}</strong><span>${esc(p.kind||'POI')} #${p.feature_id} · ${exists?`${esc(state)} · ${visible?'visible':'caché'}`:'pas encore créé'}</span></button>`}).join('')||'<div class="muted hint">Aucun POI.</div>';ui.poiList.querySelectorAll('[data-poi]').forEach(el=>el.addEventListener('click',()=>selectPoi(Number(el.dataset.poi))));const groups=featureGroups().filter(g=>match(g[0].name,g[0].feature_type));ui.edgeList.innerHTML=groups.map(g=>{const f=g[0];return`<button type="button" class="world-row ${edgeGroupSelected(g)?'selected':''}" data-edge="${f.id}"><strong>${esc(f.name||f.feature_type)}</strong><span>${f.feature_type} #${f.feature_id} · ${g.length} segment(s)</span></button>`}).join('')||'<div class="muted hint">Aucune feature linéaire.</div>';ui.edgeList.querySelectorAll('[data-edge]').forEach(el=>el.addEventListener('click',e=>selectEdge(Number(el.dataset.edge),e.ctrlKey||e.metaKey)));ui.areaList.innerHTML=(workbench?.areas||[]).filter(a=>match(a.name,a.feature_type)).map(a=>`<button type="button" class="world-row ${a.id===selectedAreaId?'selected':''}" data-area="${a.id}"><strong>${esc(a.name||a.feature_type)}</strong><span>${a.feature_type} #${a.feature_id} · ${(a.cells||[]).length} hex</span></button>`).join('')||'<div class="muted hint">Aucune zone.</div>';ui.areaList.querySelectorAll('[data-area]').forEach(el=>el.addEventListener('click',()=>selectArea(Number(el.dataset.area))))}

async function loadVersions(){if(!campaignId||!userId){msg('Ouvre cette page depuis une campagne MJ.',true);return}dashboard=await api(`/api/campaigns/${campaignId}/dm-dashboard?user_id=${userId}`);ui.version.innerHTML='<option value="">— Choisir —</option>'+dashboard.maps.flatMap(m=>m.versions.map(v=>`<option value="${v.id}">${esc(m.name)} · v${v.version}${v.name?` · ${esc(v.name)}`:''}</option>`)).join('');if(versionId)ui.version.value=String(versionId);worldMinute=Math.max(0,Number(dashboard.campaign_game_minute)||0);ui.worldTime.value=String(worldMinute);setDatePrefix('world-time',worldMinute);setDatePrefix('world-poi-event',worldMinute);setDatePrefix('world-edge-event',worldMinute);ui.poiEventMinute.value=worldMinute;ui.edgeEventMinute.value=worldMinute;ui.dmLink.href=`/dm.html?user=${userId}&campaign=${campaignId}`}
async function editorSnapshot(){return api(`/api/campaigns/${campaignId}/dm-map-versions/${workbench.map_version_id}/world-editor-snapshot?user_id=${userId}`)}
function rememberMutation(snapshot,label){undoStack.push({snapshot,label});if(undoStack.length>100)undoStack.shift();redoStack=[];updateHistoryButtons()}
function updateHistoryButtons(){if(ui.undo){ui.undo.disabled=!undoStack.length;ui.undo.title=undoStack.length?`Annuler : ${undoStack[undoStack.length-1].label}`:'Rien à annuler'}if(ui.redo){ui.redo.disabled=!redoStack.length;ui.redo.title=redoStack.length?`Rétablir : ${redoStack[redoStack.length-1].label}`:'Rien à rétablir'}}
async function restoreEditorSnapshot(snapshot){await api(`/api/campaigns/${campaignId}/dm-map-versions/${workbench.map_version_id}/world-editor-snapshot?user_id=${userId}`,{method:'PUT',body:JSON.stringify(snapshot)});await loadWorkbench(false);clearObjectSelection()}
async function undoWorld(){const cmd=undoStack.pop();if(!cmd)return null;const current=await editorSnapshot();await restoreEditorSnapshot(cmd.snapshot);redoStack.push({snapshot:current,label:cmd.label});updateHistoryButtons();return cmd.label}
async function redoWorld(){const cmd=redoStack.pop();if(!cmd)return null;const current=await editorSnapshot();await restoreEditorSnapshot(cmd.snapshot);undoStack.push({snapshot:current,label:cmd.label});updateHistoryButtons();return cmd.label}
function contentOnHex(h){if(!h||!workbench)return[];const items=[];for(const p of workbench.pois||[])if(p.q===h.q&&p.r===h.r)items.push(`POI ${p.name}`);for(const a of workbench.areas||[])if((a.cells||[]).some(c=>sameHex(c,h)))items.push(`${a.feature_type} #${a.feature_id} (retirer cet hex)`);const seen=new Set();for(const e of workbench.edges||[]){const d=e.extra_data||{},a=d.path_from||{q:e.from_q,r:e.from_r},b=d.path_to||{q:e.to_q,r:e.to_r};if((sameHex(a,h)||sameHex(b,h))&&!seen.has(`${e.feature_type}:${e.feature_id}`)){seen.add(`${e.feature_type}:${e.feature_id}`);items.push(`${e.feature_type} #${e.feature_id} (segments touchant l'hex)`)}}return items}
async function clearSelectedHex(){if(selectedHexes.length!==1)return msg('Sélectionne exactement un hex à nettoyer.',true);const h=selectedHexes[0],items=contentOnHex(h);if(!items.length)return msg('Aucune feature enregistrée sur cet hex.');if(!confirm(`Nettoyer l’hex (${h.q}, ${h.r}) ?\n\n${items.map(x=>`• ${x}`).join('\n')}\n\nLe terrain ne sera pas modifié.`))return;const before=await editorSnapshot();try{await api(`/api/campaigns/${campaignId}/dm-map-versions/${workbench.map_version_id}/hex-features?user_id=${userId}`,{method:'DELETE',body:JSON.stringify({q:h.q,r:h.r})});rememberMutation(before,`nettoyage hex (${h.q}, ${h.r})`);await loadWorkbench(false);selectedHexes=[virtualHex(h.q,h.r)];updateInspector();draw();msg(`Hex (${h.q}, ${h.r}) nettoyé.`)}catch(err){msg(err.message,true)}}

function updateExportLinks(){
  if(!workbench)return;
  const mode=ui.exportLayer?.checked?'world':'terrain';
  const base=`/api/campaigns/${campaignId}/dm-map-versions/${workbench.map_version_id}/export?user_id=${userId}&quality=high&mode=${mode}`;
  ui.exportPng.href=`${base}&format=png`;
  ui.exportJpeg.href=`${base}&format=jpeg`;
  ui.exportPdf.href=`${base}&format=pdf`;
}
ui.exportLayer?.addEventListener('change',updateExportLinks);

async function loadWorkbench(fit=true){versionId=Number(ui.version.value)||versionId;if(!versionId)return msg('Choisis une version.',true);msg('Chargement…');try{workbench=await api(`/api/campaigns/${campaignId}/dm-map-workbench?user_id=${userId}&map_version_id=${versionId}`);await loadPoiTemporalStates();selectedHexes=[];selectedPoiId=selectedEdgeId=selectedAreaId=null;selectedEdgeIds=[];ui.title.textContent=`${workbench.map_name} · v${workbench.version}`;ui.terrainLink.href=`/?user=${userId}&campaign=${campaignId}&map=${workbench.map_id}&version=${workbench.map_version_id}`;updateExportLinks();history.replaceState(null,'',`/world.html?user=${userId}&campaign=${campaignId}&version=${versionId}`);updateInspector();if(fit){initialFitPending=true;requestAnimationFrame(()=>fitView())}else draw();msg(`${(workbench.width*workbench.height).toLocaleString('fr-FR')} hex · ${workbench.pois.length} POI · ${featureGroups().length} features linéaires · ${(workbench.areas||[]).length} zones`)}catch(e){msg(e.message,true)}}


function resetEventEditor(kind){
  const isPoi=kind==='poi', form=isPoi?ui.poiEventForm:ui.edgeEventForm, hidden=isPoi?ui.poiEventMinute:ui.edgeEventMinute, prefix=isPoi?'world-poi-event':'world-edge-event';
  (isPoi?ui.poiEventId:ui.edgeEventId).value='';
  const feedback=isPoi?ui.poiEventFeedback:ui.edgeEventFeedback,submit=isPoi?ui.poiEventSubmit:ui.edgeEventSubmit;if(feedback){feedback.textContent='';feedback.classList.remove('error')}if(submit){submit.disabled=false;submit.textContent=isPoi?'Ajouter l’événement':'Ajouter l’événement'}
  hidden.value=String(worldMinute||0);setDatePrefix(prefix,worldMinute||0);
  (isPoi?ui.poiEventPayload:ui.edgeEventPayload).value='{}';
  (isPoi?ui.poiEventNote:ui.edgeEventNote).value='';
  if(isPoi){ui.poiEventType.value='POI_STATE_CHANGED';ui.poiEventState.value='ACTIVE';ui.poiEventVisibility.value='unchanged';configurePoiEventFields(false)}
  form.classList.add('hidden');
}
function openEventEditor(kind,event=null){
  const isPoi=kind==='poi',form=isPoi?ui.poiEventForm:ui.edgeEventForm,hidden=isPoi?ui.poiEventMinute:ui.edgeEventMinute,prefix=isPoi?'world-poi-event':'world-edge-event',minute=event?.game_minute??worldMinute??0;
  (isPoi?ui.poiEventId:ui.edgeEventId).value=event?.id||'';hidden.value=String(minute);setDatePrefix(prefix,minute);const feedback=isPoi?ui.poiEventFeedback:ui.edgeEventFeedback,submit=isPoi?ui.poiEventSubmit:ui.edgeEventSubmit;if(feedback){feedback.textContent=event?`Modification de l’événement #${event.id}`:'Nouvel événement';feedback.classList.remove('error')}if(submit){submit.disabled=false;submit.textContent=event?'Enregistrer les modifications':'Ajouter l’événement'}
  if(event)(isPoi?ui.poiEventType:ui.edgeEventType).value=event.event_type;
  const payload={...(event?.payload||{})};
  if(isPoi){ui.poiEventState.value=String(payload.state||'ACTIVE').toUpperCase();ui.poiEventVisibility.value=payload.visible_at_distance===true?'true':payload.visible_at_distance===false?'false':'unchanged';delete payload.state;delete payload.visible_at_distance;configurePoiEventFields(!event)}
  (isPoi?ui.poiEventPayload:ui.edgeEventPayload).value=JSON.stringify(payload);
  (isPoi?ui.poiEventNote:ui.edgeEventNote).value=event?.dm_note||'';
  form.classList.remove('hidden');
}
const EVENT_LABELS={POI_CREATED:'Création / apparition',POI_STATE_CHANGED:'Changement d’état',POI_VISIBILITY_CHANGED:'Visibilité modifiée',POI_DAMAGED:'Endommagé',POI_DESTROYED:'Détruit',POI_REBUILT:'Reconstruit',POI_OCCUPIED:'Occupé',POI_ABANDONED:'Abandonné'};
function eventLabel(type){return EVENT_LABELS[type]||type}
async function loadTargetTimeline(targetType,targetId,kind){
  const list=kind==='poi'?ui.poiEventList:ui.edgeEventList;
  if(!list||!targetType||!targetId)return;
  list.innerHTML='<div class="muted timeline-loading">Chargement des événements…</div>';
  try{
    const events=(await api(`/api/campaigns/${campaignId}/world-events?target_type=${encodeURIComponent(targetType)}&target_id=${targetId}`))
      .sort((a,b)=>a.game_minute-b.game_minute||a.id-b.id);
    list.innerHTML=events.length?events.map(ev=>`<div class="event-card ${ev.game_minute<=worldMinute?'current':''}" data-event-id="${ev.id}"><div class="event-head"><strong><span class="event-date">${esc(formatGameDate(ev.game_minute))}</span> ${esc(eventLabel(ev.event_type))}</strong><span class="event-id">#${ev.id}</span></div>${ev.dm_note?`<div class="event-note">${esc(ev.dm_note)}</div>`:''}<div class="event-payload">${esc(JSON.stringify(ev.payload||{}))}</div><div class="event-actions"><button type="button" class="secondary" data-event-edit="${ev.id}">Modifier</button><button type="button" class="danger" data-event-delete="${ev.id}">Supprimer</button></div></div>`).join(''):'<div class="muted timeline-empty">Aucun WorldEvent pour cet objet.</div>';
    list.querySelectorAll('[data-event-edit]').forEach(b=>b.addEventListener('click',()=>openEventEditor(kind,events.find(e=>e.id===Number(b.dataset.eventEdit)))));
    list.querySelectorAll('[data-event-delete]').forEach(b=>b.addEventListener('click',async()=>{const id=Number(b.dataset.eventDelete);if(!confirm('Supprimer cet événement de la timeline ?'))return;const before=await editorSnapshot();try{await api(`/api/world-events/${id}`,{method:'DELETE'});rememberMutation(before,'suppression événement');await loadPoiTemporalStates();await loadTargetTimeline(targetType,targetId,kind);updateInspector();renderLists();draw();msg('Événement supprimé.')}catch(err){msg(err.message,true)}}));
  }catch(err){list.innerHTML=`<div class="error">Impossible de charger la timeline : ${esc(err.message)}</div>`}
}
async function saveLinearEdit(e){e.preventDefault();if(!selectedEdgeId)return;const before=await editorSnapshot();try{await api(`/api/campaigns/${campaignId}/dm-linear-features/${selectedEdgeId}?user_id=${userId}`,{method:'PATCH',body:JSON.stringify({name:ui.linearEditName.value.trim()||null})});rememberMutation(before,'renommage feature');const wanted=selectedEdgeId;await loadWorkbench(false);selectEdge(wanted,false);msg('Feature renommée.')}catch(err){msg(err.message,true)}}
async function saveAreaEdit(e){e.preventDefault();if(!selectedAreaId)return;const before=await editorSnapshot();try{await api(`/api/campaigns/${campaignId}/dm-area-features/${selectedAreaId}?user_id=${userId}`,{method:'PATCH',body:JSON.stringify({name:ui.areaEditName.value.trim()||null})});rememberMutation(before,'renommage zone');const wanted=selectedAreaId;await loadWorkbench(false);selectArea(wanted);msg('Zone renommée.')}catch(err){msg(err.message,true)}}
async function savePoi(e){e.preventDefault();if(selectedHexes.length!==1)return msg('Sélectionne exactement un hex pour le POI.',true);const payload={name:ui.poiName.value.trim(),kind:ui.poiKind.value.trim()||null,dm_description:ui.poiDescription.value.trim()||null,is_landmark:ui.poiLandmark.checked};const before=await editorSnapshot();try{let createdPoiId=null;if(selectedPoiId)await api(`/api/campaigns/${campaignId}/dm-pois/${selectedPoiId}?user_id=${userId}`,{method:'PATCH',body:JSON.stringify(payload)});else{const h=selectedHexes[0];const created=await api(`/api/campaigns/${campaignId}/dm-map-versions/${workbench.map_version_id}/pois?user_id=${userId}`,{method:'POST',body:JSON.stringify({...payload,q:h.q,r:h.r,creation_game_minute:worldMinute})});createdPoiId=created.id}rememberMutation(before,selectedPoiId?'modification POI':'création POI');await loadWorkbench(false);setTool('select');if(createdPoiId){selectPoi(createdPoiId);msg(`POI créé à ${formatGameDate(worldMinute)}. L’événement Création / apparition a été ajouté automatiquement.`)}else msg('POI enregistré.')}catch(err){msg(err.message,true)}}
async function savePoiEvent(e){
  e.preventDefault();
  if(!selectedPoiId)return msg('Sélectionne un POI.',true);
  const p=workbench?.pois.find(x=>x.id===selectedPoiId);if(!p)return;
  let gameMinute;try{gameMinute=syncHiddenMinute('world-poi-event',ui.poiEventMinute)}catch(err){if(ui.poiEventFeedback){ui.poiEventFeedback.textContent=err.message;ui.poiEventFeedback.classList.add('error')}return msg(err.message,true)}
  const eventType=ui.poiEventType.value;let eventPayload;
  try{eventPayload=parseJSON(ui.poiEventPayload)}catch(err){if(ui.poiEventFeedback){ui.poiEventFeedback.textContent=err.message;ui.poiEventFeedback.classList.add('error')}return msg(err.message,true)}
  if(eventType==='POI_STATE_CHANGED')eventPayload.state=ui.poiEventState.value;
  if(ui.poiEventVisibility.value!=='unchanged')eventPayload.visible_at_distance=ui.poiEventVisibility.value==='true';
  if(eventType==='POI_VISIBILITY_CHANGED'&&ui.poiEventVisibility.value==='unchanged')return msg('Choisis Oui ou Non pour la visibilité.',true);
  const before=await editorSnapshot(),id=Number(ui.poiEventId.value)||null,payload={game_minute:gameMinute,event_type:eventType,payload:eventPayload,dm_note:ui.poiEventNote.value.trim()||null};
  if(ui.poiEventSubmit){ui.poiEventSubmit.disabled=true;ui.poiEventSubmit.textContent=id?'Enregistrement…':'Ajout…'}
  if(ui.poiEventFeedback){ui.poiEventFeedback.textContent=id?`Mise à jour de l’événement #${id}…`:'Création de l’événement…';ui.poiEventFeedback.classList.remove('error')}
  try{
    const saved=id?await api(`/api/world-events/${id}`,{method:'PATCH',body:JSON.stringify(payload)}):await api(`/api/campaigns/${campaignId}/dm-pois/${selectedPoiId}/world-events?user_id=${userId}`,{method:'POST',body:JSON.stringify(payload)});
    rememberMutation(before,id?'modification événement POI':'événement temporel POI');
    await loadPoiTemporalStates();
    updateInspector();renderLists();draw();
    await loadTargetTimeline('POI',p.feature_id,'poi');
    resetEventEditor('poi');
    msg(id?`Événement #${saved?.id??id} modifié à ${formatGameDate(saved?.game_minute??gameMinute)}.`:`WorldEvent #${saved?.id??''} ajouté à ${formatGameDate(saved?.game_minute??gameMinute)}.`);
  }catch(err){
    if(ui.poiEventFeedback){ui.poiEventFeedback.textContent=err.message;ui.poiEventFeedback.classList.add('error')}
    if(ui.poiEventSubmit){ui.poiEventSubmit.disabled=false;ui.poiEventSubmit.textContent=id?'Enregistrer les modifications':'Ajouter l’événement'}
    msg(err.message,true)
  }
}
async function saveEdge(e){e.preventDefault();const type=ui.edgeType.value;if(selectedHexes.length<2)return msg('Sélectionne au moins deux waypoints.',true);if(!['ROAD','RIVER','PASSAGE','TRAVERSAL'].includes(type))return msg('Type linéaire non supporté.',true);const before=await editorSnapshot();try{const created=await api(`/api/campaigns/${campaignId}/dm-map-versions/${workbench.map_version_id}/linear-features?user_id=${userId}`,{method:'POST',body:JSON.stringify({waypoints:selectedHexes.map(h=>({q:h.q,r:h.r})),feature_type:type,name:ui.edgeName.value.trim()||null,extra_data:{}})});rememberMutation(before,`création ${type}`);ui.edgeName.value='';await loadWorkbench(false);setTool('select');msg(`${type} créé : ${created.length} segment(s).`)}catch(err){msg(err.message,true)}}
async function saveArea(e){e.preventDefault();if(!selectedHexes.length)return msg('Sélectionne au moins un hex.',true);const before=await editorSnapshot();try{const area=await api(`/api/campaigns/${campaignId}/dm-map-versions/${workbench.map_version_id}/area-features?user_id=${userId}`,{method:'POST',body:JSON.stringify({cells:selectedHexes.map(h=>({q:h.q,r:h.r})),feature_type:ui.areaType.value,name:ui.areaName.value.trim()||null,extra_data:{}})});rememberMutation(before,`création ${area.feature_type}`);ui.areaName.value='';await loadWorkbench(false);setTool('select');msg(`${area.feature_type} #${area.feature_id} créé.`)}catch(err){msg(err.message,true)}}
async function saveEdgeEvent(e){e.preventDefault();if(!selectedEdgeId)return msg('Sélectionne une feature linéaire.',true);const g=selectedEdgeGroups()[0],f=g?.[0];if(!f)return;const before=await editorSnapshot(),id=Number(ui.edgeEventId.value)||null,gameMinute=syncHiddenMinute('world-edge-event',ui.edgeEventMinute),payload={game_minute:gameMinute,event_type:ui.edgeEventType.value,payload:parseJSON(ui.edgeEventPayload),dm_note:ui.edgeEventNote.value.trim()||null};try{if(id)await api(`/api/world-events/${id}`,{method:'PATCH',body:JSON.stringify(payload)});else await api(`/api/campaigns/${campaignId}/dm-map-edges/${selectedEdgeId}/world-events?user_id=${userId}`,{method:'POST',body:JSON.stringify(payload)});rememberMutation(before,id?'modification événement feature':'événement temporel feature');resetEventEditor('edge');await loadTargetTimeline(f.feature_type,f.feature_id,'edge');msg(id?'Événement modifié.':'WorldEvent de feature ajouté.')}catch(err){msg(err.message,true)}}
async function mergeSelectedLinear(){const groups=selectedEdgeGroups();if(groups.length<2)return msg('Sélectionne au moins deux routes ou deux rivières avec Ctrl+clic.',true);const type=groups[0][0].feature_type;if(!['ROAD','RIVER'].includes(type)||groups.some(g=>g[0].feature_type!==type))return msg('La fusion exige uniquement des ROAD ou uniquement des RIVER.',true);const before=await editorSnapshot();try{const merged=await api(`/api/campaigns/${campaignId}/dm-linear-features/merge?user_id=${userId}`,{method:'POST',body:JSON.stringify({edge_ids:selectedEdgeIds})});rememberMutation(before,`fusion ${type}`);await loadWorkbench(false);if(merged.length)selectEdge(merged[0].id,false);msg(`${type} fusionné : ${merged.length} segment(s), une seule feature.`)}catch(err){msg(err.message,true)}}
async function deleteSelected(kind){let path,label;if(kind==='poi'&&selectedPoiId){path=`/api/campaigns/${campaignId}/dm-pois/${selectedPoiId}?user_id=${userId}`;label='ce POI'}else if(kind==='edge'&&selectedEdgeId){path=`/api/campaigns/${campaignId}/dm-linear-features/${selectedEdgeId}?user_id=${userId}`;label='cette feature linéaire'}else if(kind==='area'&&selectedAreaId){path=`/api/campaigns/${campaignId}/dm-area-features/${selectedAreaId}?user_id=${userId}`;label='cette zone'}else return;if(!confirm(`Supprimer définitivement ${label} ?\n\nSi la feature possède déjà une timeline ou de la connaissance joueur, le serveur refusera la suppression.`))return;const before=await editorSnapshot();try{await api(path,{method:'DELETE'});rememberMutation(before,`suppression ${label}`);await loadWorkbench(false);setTool('select');msg('Feature supprimée.')}catch(err){msg(err.message,true)}}

function handleCanvasClick(e){if(view.moved)return;const rect=ui.canvas.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top,h=nearestHex(x,y);if(activeTool==='select'){if(e.shiftKey)return selectHex(h,e.ctrlKey||e.metaKey);const hit=hitObject(x,y);if(hit?.type==='poi')return selectPoi(hit.id);if(hit?.type==='edge')return selectEdge(hit.id,e.ctrlKey||e.metaKey);if(e.altKey&&h){const area=(workbench?.areas||[]).find(a=>(a.cells||[]).some(c=>sameHex(c,h)));if(area)return selectArea(area.id)}return selectHex(h,e.ctrlKey||e.metaKey)}if(activeTool==='poi'){selectHex(h,false);showPanel('poi');clearPoiForm(false);updateInspector();return}if(['road','river'].includes(activeTool)){addWaypoint(h);return}if(activeTool==='area')toggleAreaHex(h)}
function setToolFromKey(k){const map={v:'select',p:'poi',r:'road',w:'river',a:'area'};if(map[k])setTool(map[k])}

document.querySelectorAll('.tool[data-tool]').forEach(b=>b.addEventListener('click',()=>setTool(b.dataset.tool)));
ui.poiEventType.addEventListener('change',()=>configurePoiEventFields(true));
ui.save.addEventListener('click',()=>saveCheckpoint().catch(e=>msg(e.message,true)));
ui.worldTimeApply.addEventListener('click',applyWorldMinute);
ui.load.addEventListener('click',()=>loadWorkbench(true));ui.version.addEventListener('change',()=>loadWorkbench(true));ui.fit.addEventListener('click',fitView);ui.poiForm.addEventListener('submit',savePoi);ui.linearEditForm.addEventListener('submit',saveLinearEdit);ui.areaEditForm.addEventListener('submit',saveAreaEdit);ui.poiNew.addEventListener('click',()=>{selectedPoiId=null;clearPoiForm();updateInspector()});ui.poiEventForm.addEventListener('submit',savePoiEvent);ui.poiEventNew.addEventListener('click',()=>openEventEditor('poi'));ui.poiEventCancel.addEventListener('click',()=>resetEventEditor('poi'));ui.edgeForm.addEventListener('submit',saveEdge);ui.edgeEventForm.addEventListener('submit',saveEdgeEvent);ui.edgeEventNew.addEventListener('click',()=>openEventEditor('edge'));ui.edgeEventCancel.addEventListener('click',()=>resetEventEditor('edge'));ui.areaForm.addEventListener('submit',saveArea);ui.poiDelete.addEventListener('click',()=>deleteSelected('poi'));ui.edgeDelete.addEventListener('click',()=>deleteSelected('edge'));ui.edgeMerge.addEventListener('click',mergeSelectedLinear);ui.areaDelete.addEventListener('click',()=>deleteSelected('area'));ui.inspectorClose.addEventListener('click',clearObjectSelection);ui.browserToggle.addEventListener('click',()=>ui.browser.classList.toggle('hidden'));ui.browserClose.addEventListener('click',()=>ui.browser.classList.add('hidden'));ui.browserSearch.addEventListener('input',renderLists);ui.undo.addEventListener('click',async()=>{try{const label=await undoWorld();msg(label?`Annulé : ${label}.`:'Rien à annuler.')}catch(e){msg(e.message,true)}});ui.redo.addEventListener('click',async()=>{try{const label=await redoWorld();msg(label?`Rétabli : ${label}.`:'Rien à rétablir.')}catch(e){msg(e.message,true)}});updateHistoryButtons();
ui.canvas.addEventListener('mousedown',e=>{if(e.button===1||spaceDown||activeTool==='select'){view.dragging=true;view.moved=false;view.lastX=e.clientX;view.lastY=e.clientY;ui.canvas.classList.add('dragging')}});window.addEventListener('mouseup',()=>{view.dragging=false;ui.canvas.classList.remove('dragging')});ui.canvas.addEventListener('mousemove',e=>{if(!view.dragging)return;const dx=e.clientX-view.lastX,dy=e.clientY-view.lastY;if(Math.abs(dx)+Math.abs(dy)>2)view.moved=true;view.panX+=dx;view.panY+=dy;view.lastX=e.clientX;view.lastY=e.clientY;draw()});ui.canvas.addEventListener('click',handleCanvasClick);ui.canvas.addEventListener('wheel',e=>{e.preventDefault();view.scale=Math.max(.0005,Math.min(3,view.scale*(e.deltaY<0?1.1:.9)));draw()},{passive:false});
window.addEventListener('keydown',async e=>{const target=e.target,editable=target instanceof HTMLElement&&(target.matches('input,textarea,select')||target.isContentEditable);if(e.code==='Space'&&!editable){spaceDown=true;e.preventDefault()}if(editable)return;const mod=e.ctrlKey||e.metaKey;if(mod&&e.key.toLowerCase()==='s'){e.preventDefault();try{await saveCheckpoint()}catch(err){msg(err.message,true)}return}if(mod&&e.key.toLowerCase()==='z'){e.preventDefault();try{const label=e.shiftKey?await redoWorld():await undoWorld();msg(label?(e.shiftKey?`Rétabli : ${label}.`:`Annulé : ${label}.`):(e.shiftKey?'Rien à rétablir.':'Rien à annuler.'))}catch(err){msg(err.message,true)}return}if(e.key==='Escape'){clearObjectSelection();return}if(e.key==='Backspace'&&['road','river'].includes(activeTool)&&selectedHexes.length){e.preventDefault();selectedHexes.pop();updateInspector();draw();return}if(e.key==='Enter'&&['road','river'].includes(activeTool)&&selectedHexes.length>=2){e.preventDefault();ui.edgeForm.requestSubmit();return}if(e.key==='Delete'){if(selectedPoiId)return deleteSelected('poi');if(selectedEdgeId)return deleteSelected('edge');if(selectedAreaId)return deleteSelected('area');if(selectedHexes.length)return clearSelectedHex()}setToolFromKey(e.key.toLowerCase())});window.addEventListener('keyup',e=>{if(e.code==='Space')spaceDown=false});window.addEventListener('blur',()=>spaceDown=false);new ResizeObserver(()=>{if(initialFitPending)fitView();else draw()}).observe(ui.canvas.parentElement);
(async()=>{try{await loadVersions();if(versionId){ui.version.value=String(versionId);await loadWorkbench(true)}setTool('select')}catch(e){msg(e.message,true)}})();

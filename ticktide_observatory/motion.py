"""Fixed SVG scenes with browser-side replay of recorded events; no physics jitter."""
import html
import json
import math
import streamlit as st
import streamlit.components.v1 as components

ICONS = {'core':'▤','edge':'⬡','access':'⌁','sequence':'→','fallback':'⑂','retry':'↻','condition':'?','action':'◆','kafka':'◉','database':'▱','request':'↗','service':'ƒ'}

def scene(nodes, edges, events=None, *, title='Execution canvas', subtitle='Recorded evidence · fixed positions', animate=True, height=630, layout='flow'):
    nodes=[dict(n, id=str(n['id'])) for n in nodes]
    ids={n['id'] for n in nodes}
    edges=[dict(e,source=str(e['source']),target=str(e['target'])) for e in edges if str(e['source']) in ids and str(e['target']) in ids]
    parents={};children={k:[] for k in ids}
    for e in edges:
        children[e['source']].append(e['target']);parents.setdefault(e['target'],e['source'])
    positions={}
    if layout=='tree':
        leaf=[0];visiting=set()
        def place(k, depth):
            if k in visiting:return positions.get(k,(120,depth*128+70))[0]
            visiting.add(k)
            cs=list(dict.fromkeys(children[k]))
            xs=[place(c,depth+1) for c in cs if c not in visiting]
            if xs:x=sum(xs)/len(xs)
            else:x=100+leaf[0]*170;leaf[0]+=1
            positions[k]=(x,65+depth*128)
            return x
        for root in [k for k in ids if k not in parents]:place(root,0)
        for k in ids:
            if k not in positions:place(k,0)
        width=max(1000,max(x for x,y in positions.values())+105)
        canvas_height=max(520,max(y for x,y in positions.values())+90)
        if {'ROOT','SEL','SEQ_A','SEQ_B','SEQ_R'}.issubset(ids):
            positions['REQUEST']=(320,65)
            positions.update({'ROOT':(580,65),'F1':(95,185),'F2':(325,185),'SEL':(580,185),'F11':(835,185),'F12':(1065,185),'SEQ_A':(225,305),'SEQ_B':(580,305),'SEQ_R':(935,305)})
            for keys,x in [(['C1','F3','RA','C2','F5'],225),(['C3','F6','RB','C4','F8'],580),(['F9','F10'],935)]:
                for i,k in enumerate(keys):
                    if k in ids:positions[k]=(x,425+i*105)
            if 'F4' in ids:positions['F4']=(405,635)
            if 'F7' in ids:positions['F7']=(760,635)
            width=1160;canvas_height=930
    elif layout=='network':
        width=1060;canvas_height=500
        fixed={'core':(530,95),'edge1':(270,255),'edge2':(790,255),'access1':(530,420)}
        for i,n in enumerate(nodes):positions[n['id']]=fixed.get(n['id'],(100+i*170,250))
    else:
        width=max(1000,min(len(nodes),5)*215);canvas_height=max(440,math.ceil(len(nodes)/5)*155+130)
        for i,n in enumerate(nodes):
            r,c=divmod(i,5);positions[n['id']]=(110+(c if r%2==0 else 4-c)*215,100+r*155)
    for n in nodes:
        n['x'],n['y']=positions[n['id']]
        n['kind']=n.get('kind','service');n['icon']=ICONS.get(n['kind'],ICONS.get(n['id'], '◆'))
    if events is None:
        events=[{'node_id':n['id'],'status':'ACTIVE','detail':'Graph reveal · illustrative order'} for n in nodes]
    events=[dict(e,node_id=str(e['node_id'])) for e in events if str(e['node_id']) in ids]
    payload=json.dumps({'nodes':nodes,'edges':edges,'events':events,'width':width,'height':canvas_height,'auto':animate,'replay':st.session_state.get('motion_nonce',0)},ensure_ascii=False).replace('</',r'<\/')
    template=r'''<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;background:#0b1423;color:#f0f6ff;font:14px Inter,Arial,sans-serif}.shell{border:1px solid #34475e;border-radius:20px;overflow:hidden;background:radial-gradient(ellipse at 50% 0,#172b43,#0b1423 70%)}.top{display:flex;justify-content:space-between;align-items:center;padding:17px 21px;border-bottom:1px solid #2b3c52;gap:12px}.title{font-size:16px;font-weight:750;letter-spacing:-.02em}.sub{color:#b8cce3;font-size:11px;margin-top:5px;letter-spacing:.04em}.brand{color:#68f5cd;font-weight:700;white-space:nowrap}.wave{display:inline-block;animation:wave 2s infinite;margin-right:8px;font-size:24px}.controls{display:flex;align-items:center;gap:8px;padding:12px 18px;flex-wrap:wrap;background:#101e31}button,select{background:#20354e;border:1px solid #4c6582;color:#f2f8ff;border-radius:8px;padding:8px 12px;font:600 12px Arial;cursor:pointer}button:hover{border-color:#61efc0;background:#2a4961}.primary{background:#58e5b7;color:#06231f;border-color:#58e5b7}label{color:#c9dbed;font-size:12px;margin-left:8px}.board{overflow:auto;height:__BOARD_HEIGHT__px;position:relative;scrollbar-color:#54708d #111d2b;background-image:radial-gradient(#2d405c 1px,transparent 1px);background-size:22px 22px}svg{display:block;min-width:0;width:100%;height:100%;min-height:480px}svg text{pointer-events:none}.node{cursor:pointer}.node rect{fill:#192c44;stroke:#587493;stroke-width:1.3;transition:fill .3s,stroke .3s}.node[data-kind="core"] rect{fill:#352b5b;stroke:#c0a5ff}.node[data-kind="edge"] rect{fill:#123f44;stroke:#72dacb}.node[data-kind="access"] rect{fill:#193b60;stroke:#90c5ff}.node[data-kind="kafka"] rect{fill:#4a3524;stroke:#ffd092}.node[data-kind="database"] rect{fill:#332b58;stroke:#c2b2ff}.node.done rect{fill:#12513f;stroke:#68f5b6;stroke-width:2}.node.running rect{fill:#16744f;stroke:#acffcc;stroke-width:2.6;filter:url(#glow)}.node.failed rect{fill:#5d283c;stroke:#ff9ab4}.node .halo{opacity:0;fill:none;stroke:#7bffbe;stroke-width:2}.node.running .halo{animation:halo 1.1s infinite}.node.running .light{fill:#b4ffd0;animation:blink .5s infinite alternate}.wire{stroke:#51647e;stroke-width:1.7;fill:none;opacity:.85}.wire.hot{stroke:#74f6c4;stroke-width:2.8;stroke-dasharray:7 7;animation:flow .7s linear infinite}.packet{fill:#d0ffeb;filter:url(#glow)}.footer{display:flex;align-items:center;gap:14px;padding:16px 20px;background:#102237;border-top:1px solid #34475e;min-height:75px}.status-icon{font-size:25px;color:#7cf4cc}.status{flex:1;line-height:1.6}.event{font-weight:650;color:#edfff9}.detail{color:#b9d1e8;font-size:12px}.count{color:#7ef6d0;font:700 18px monospace}.track{height:3px;background:#223751}.fill{height:100%;width:0%;background:linear-gradient(90deg,#5e9fff,#69fbc4);transition:width .35s}.legend{padding:10px 20px;color:#b6cde4;font-size:11px;display:flex;gap:18px;flex-wrap:wrap}.green{color:#7affba}.rose{color:#ffa3bd}.blue{color:#a9caff}.shell:fullscreen .board{height:calc(100vh - 240px)!important}.shell:fullscreen{background:#0b1423}
@keyframes halo{0%{opacity:.9;transform:scale(1);transform-origin:center}100%{opacity:0;transform:scale(1.13);transform-origin:center}}@keyframes blink{to{opacity:.3}}@keyframes flow{to{stroke-dashoffset:-28}}@keyframes wave{50%{transform:scaleX(1.25);opacity:.6}}@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style></head><body><div class="shell" id="shell"><div class="top"><div><div class="title">__TITLE__</div><div class="sub">__SUBTITLE__</div></div><div class="brand"><span class="wave">∿</span>tick wave</div></div><div class="controls"><button id="play" class="primary">▶ Play request</button><button id="pause">Ⅱ Pause</button><button id="step">↦ Step</button><button id="reset">↺ Reset</button><label for="speed">Speed</label><select id="speed"><option value="1500">0.5×</option><option value="850" selected>1×</option><option value="420">2×</option></select><button id="fit">⊡ Fit</button><button id="zoom">＋ Zoom</button><button id="full">⛶ Fullscreen</button></div><div class="board" id="board"><svg id="svg" role="img" aria-label="Fixed research graph with animated event replay" xmlns="http://www.w3.org/2000/svg"><defs><filter id="glow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#88bba9"/></marker></defs><g id="wires"></g><g id="nodes"></g><g id="packets"></g></svg></div><div class="track"><div class="fill" id="fill"></div></div><div class="footer"><span class="status-icon" id="statusIcon">◌</span><div class="status"><div class="event" id="event">Request ready. Follow the wave.</div><div class="detail" id="detail">Stable layout · pulse indicates the current recorded event</div></div><div class="count" id="count">00 / 00</div></div><div class="legend"><span class="blue">● Waiting / structural node</span><span class="green">● Activated / visited</span><span class="rose">● Recorded failure</span><span>↗ Moving light = illustrative event flow, not elapsed network time</span></div></div><script>
const D=__DATA__,NS='http://www.w3.org/2000/svg',svg=document.getElementById('svg'),nodesEl=document.getElementById('nodes'),wires=document.getElementById('wires'),packets=document.getElementById('packets');svg.setAttribute('viewBox',`0 0 ${D.width} ${D.height}`);svg.style.height=D.height+'px';const byId={},elements={},paths={},parents={},done=new Map();let index=0,playing=false,timer=null,frame=null,generation=0;
function el(tag,attrs,text){const e=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e}
D.nodes.forEach(n=>byId[n.id]=n);
D.edges.forEach((e,i)=>{const a=byId[e.source],b=byId[e.target];parents[e.target]??=e.source;let path;
if(Math.abs(a.y-b.y)>70){const sy=a.y+37,ty=b.y-37;if(a.x===b.x&&b.y-a.y>170){const rail=a.x-94;path=`M${a.x-76},${a.y} L${rail},${a.y} L${rail},${b.y} L${b.x-76},${b.y}`}else path=`M${a.x},${sy} C${a.x},${(sy+ty)/2} ${b.x},${(sy+ty)/2} ${b.x},${ty}`}
else{const dx=b.x>=a.x?1:-1;path=`M${a.x+dx*76},${a.y} Q${(a.x+b.x)/2},${a.y-40} ${b.x-dx*76},${b.y}`}
const p=el('path',{d:path,class:'wire','marker-end':'url(#arrow)'});wires.append(p);paths[e.source+'|'+e.target]=p;
if(e.label){const x=(a.x+b.x)/2,y=(a.y+b.y)/2;const t=el('text',{x,y:y-8,fill:'#d2e1f3','font-size':11,'text-anchor':'middle','paint-order':'stroke',stroke:'#0b1423','stroke-width':4},e.label);wires.append(t)}});
D.nodes.forEach(n=>{const g=el('g',{class:'node','data-kind':n.kind,transform:`translate(${n.x},${n.y})`});g.append(el('rect',{x:-81,y:-41,width:162,height:82,rx:15,class:'halo'}));g.append(el('rect',{x:-76,y:-36,width:152,height:72,rx:12}));const ico=el('g',{transform:'translate(-60,-26)',fill:'none',stroke:'#9bdbff','stroke-width':1.7,'stroke-linecap':'round','stroke-linejoin':'round'});
const designs={core:['M1 1h20v7H1z M1 12h20v7H1z M5 4h2 M5 15h2 M15 4h3 M15 15h3'],edge:['M4 4h14v14H4z M8 8h6v6H8z M0 7h4 M0 14h4 M18 7h4 M18 14h4 M7 0v4 M14 0v4 M7 18v4 M14 18v4'],access:['M1 6Q11 -3 21 6 M5 11Q11 5 17 11 M9 15Q11 13 13 15 M11 19h.1'],request:['M1 3h20v15H1z M1 3l10 8L21 3 M14 21h8 M19 18l3 3-3 3'],database:['M2 5C2 0 20 0 20 5C20 10 2 10 2 5 M2 5v14c0 5 18 5 18 0V5 M2 12c0 5 18 5 18 0'],kafka:['M10 5v13 M10 5l10 5 M10 18l10-5'],service:['M5 1h13 M10 1L6 21 M3 9h13']};
if(designs[n.kind]){designs[n.kind].forEach(d=>ico.append(el('path',{d})));if(n.kind==='kafka')[[10,3],[10,19],[21,10]].forEach(([cx,cy])=>ico.append(el('circle',{cx,cy,r:3,fill:'#112a3b'})));g.append(ico)}else g.append(el('text',{x:-57,y:-10,fill:'#a6d3ff','font-size':23},n.icon));g.append(el('text',{x:-24,y:-12,fill:'#f6fbff','font-size':14,'font-weight':750},n.id));g.append(el('circle',{cx:59,cy:-16,r:4,fill:'#7893b0',class:'light'}));const label=(n.name||n.label||n.id).replaceAll('\n',' · ');g.append(el('text',{x:0,y:12,fill:'#f3f8ff','font-size':12,'font-weight':550,'text-anchor':'middle'},label.length>23?label.slice(0,22)+'…':label));g.append(el('text',{x:0,y:28,fill:'#bcd8ee','font-size':9,'letter-spacing':1,'text-anchor':'middle'},n.kind.toUpperCase()));g.append(el('title',{},n.title||label));g.onclick=()=>{document.getElementById('event').textContent=n.id+' · '+(n.name||n.label||'');document.getElementById('detail').textContent=n.title||n.kind};nodesEl.append(g);elements[n.id]=g});
function ui(){document.getElementById('count').textContent=String(index).padStart(2,'0')+' / '+String(D.events.length).padStart(2,'0');document.getElementById('fill').style.width=(D.events.length?index/D.events.length*100:0)+'%'}
function stop(){playing=false;clearTimeout(timer);document.getElementById('play').textContent='▶ Resume request'}
function reset(){stop();generation++;if(frame)cancelAnimationFrame(frame);packets.replaceChildren();index=0;done.clear();Object.values(elements).forEach(e=>e.setAttribute('class','node'));Object.values(paths).forEach(e=>e.setAttribute('class','wire'));ui();document.getElementById('event').textContent='Request ready. Follow the wave.';document.getElementById('detail').textContent='Press Play to replay the selected recorded path.';document.getElementById('play').textContent='▶ Play request'}
function pulse(path){if(!path)return;const dot=el('circle',{r:5,class:'packet'});packets.append(dot);const start=performance.now(),duration=Number(document.getElementById('speed').value)*.8,len=path.getTotalLength(),g=generation;function move(t){if(g!==generation){dot.remove();return}const p=Math.min((t-start)/duration,1),pt=path.getPointAtLength(len*p);dot.setAttribute('cx',pt.x);dot.setAttribute('cy',pt.y);if(p<1)frame=requestAnimationFrame(move);else dot.remove()}frame=requestAnimationFrame(move)}
function next(){if(index>=D.events.length){stop();Object.values(paths).forEach(e=>e.classList.remove('hot'));document.getElementById('event').textContent=D.events.some(e=>['SUCCESS','FAILURE','RUNNING'].includes(e.status))?'✓ Replay complete · all recorded events visited':'✓ Motion preview complete · illustrative flow';Object.entries(elements).forEach(([id,e])=>e.setAttribute('class','node '+(done.get(id)||'')));document.getElementById('play').textContent='↺ Replay request';return false}
Object.entries(elements).forEach(([id,e])=>e.setAttribute('class','node '+(done.get(id)||'')));Object.values(paths).forEach(e=>e.classList.remove('hot'));
const evt=D.events[index++],id=evt.node_id;let cur=id,seen=new Set();while(parents[cur]&&!seen.has(cur)){seen.add(cur);const p=parents[cur];if(elements[p]){elements[p].classList.add('done');done.set(p,'done')}const path=paths[p+'|'+cur];if(path){path.classList.add('hot');pulse(path)}cur=p}
const failed=evt.status==='FAILURE';done.set(id,failed?'failed':'done');elements[id].setAttribute('class','node running'+(failed?' failed':''));
if(index>1){const prev=D.events[index-2].node_id;pulse(paths[prev+'|'+id])}
document.getElementById('statusIcon').textContent=failed?'!':'↗';document.getElementById('event').textContent=id+' · '+(byId[id].name||byId[id].label||'')+' · '+evt.status;document.getElementById('detail').textContent=(evt.attempt?'Attempt '+evt.attempt+' · ':'')+(evt.operations!==undefined?evt.operations+' synthetic operations · ':'')+(evt.detail||'');ui();return true}
function loop(){if(!playing)return;if(next())timer=setTimeout(loop,Number(document.getElementById('speed').value));}
document.getElementById('play').onclick=()=>{if(playing)return;if(index>=D.events.length)reset();playing=true;document.getElementById('play').textContent='● Request in motion';loop()};document.getElementById('pause').onclick=stop;document.getElementById('step').onclick=()=>{stop();next()};document.getElementById('reset').onclick=reset;
document.getElementById('fit').onclick=()=>{svg.style.minWidth='0';svg.style.width='100%';svg.style.height='100%'};document.getElementById('zoom').onclick=()=>{svg.style.minWidth='1050px';svg.style.width=Math.max(document.getElementById('board').clientWidth,parseFloat(svg.style.width)||D.width)*1.2+'px';svg.style.height=D.height+'px'};
document.getElementById('full').onclick=()=>{if(document.fullscreenElement)document.exitFullscreen();else document.getElementById('shell').requestFullscreen().catch(()=>{})};
ui();if(D.auto&&!matchMedia('(prefers-reduced-motion: reduce)').matches)timer=setTimeout(()=>document.getElementById('play').click(),800);
</script></body></html>'''
    board_height=height-238
    if st.session_state.get('_tick_wave_edition')=='ocean':
        from ocean_theme import ocean_markup
        template=ocean_markup(template,mode='scene')
    rendered=template.replace('__DATA__',payload).replace('__TITLE__',html.escape(title)).replace('__SUBTITLE__',html.escape(subtitle)).replace('__BOARD_HEIGHT__',str(board_height))
    components.html(rendered,height=height+8,scrolling=False)


def behavior_scene(bt, events, animate=True):
    nodes=[];edges=[]
    for k,v in bt['nodes'].items():
        nodes.append({'id':k,'name':v.get('name',k),'kind':v.get('type','action'),'title':json.dumps(v,ensure_ascii=False)})
        for ch in v.get('children',[v['child']] if v.get('child') else []):edges.append({'source':k,'target':ch})
    if bt.get('root')=='ROOT':
        nodes.append({'id':'REQUEST','name':'Incoming request','kind':'request','title':'Visual replay start marker; not a separate recorded event'})
        edges.insert(0,{'source':'REQUEST','target':'ROOT'})
        events=[{'node_id':'REQUEST','status':'REPLAY START','detail':'Visual ingress marker · recorded decisions follow'}]+list(events)
    scene(nodes,edges,events,title='The living behavior tree',subtitle='Recorded event order · every branch remains visible · green pulses follow actual visits',animate=animate,height=990,layout='tree')


def kafka_scene(animate=True):
    nodes=[{'id':'WATCHER','name':'Recorded SG watcher','kind':'request'}, {'id':'SG READY','name':'ticktide.sg.ready','kind':'kafka'}, {'id':'SOLVER','name':'HiGHS + independent audit','kind':'service'}, {'id':'PLACEMENT','name':'ticktide.placement.completed','kind':'kafka'}, {'id':'NEO4J','name':'Graph writer','kind':'database'}, {'id':'ERRORS','name':'ticktide.pipeline.errors','kind':'kafka'}]
    edges=[{'source':a,'target':b} for a,b in [('WATCHER','SG READY'),('SG READY','SOLVER'),('SOLVER','PLACEMENT'),('PLACEMENT','NEO4J'),('SOLVER','ERRORS'),('NEO4J','ERRORS')]]
    events=[{'node_id':k,'status':'ARCHITECTURE PREVIEW','detail':'Illustrative message flow · broker connection and delivery have not been verified'} for k in ['WATCHER','SG READY','SOLVER','PLACEMENT','NEO4J']]
    scene(nodes,edges,events,title='From event stream to knowledge graph',subtitle='KAFKA ARCHITECTURE PREVIEW · NOT CONNECTED / NOT VERIFIED',animate=animate,height=670)

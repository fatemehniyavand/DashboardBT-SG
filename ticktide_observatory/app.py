"""Evidence-based, local TickTide research observatory."""
from __future__ import annotations
import html
import json
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
sys.path.insert(0, str(Path(__file__).resolve().parent))
from motion import scene, behavior_scene, kafka_scene
from wall import prepare_wall, render_wall

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OCEAN_EDITION=globals().get('TICK_WAVE_EDITION')=='ocean'
st.set_page_config(page_title='tick wave · Ocean Edition' if OCEAN_EDITION else 'tick wave · Research in Motion', page_icon='🌊' if OCEAN_EDITION else '∿', layout='wide')
st.session_state['_tick_wave_edition']='ocean' if OCEAN_EDITION else 'classic'
st.session_state['_tick_wave_surge']=bool(globals().get('TICK_WAVE_SURGE',False))
STAGES = ['Behavior tree', 'Execution trace', 'Executed trees', 'Prolog → service graph', 'Resource model', 'Physical network', 'MILP placement', 'Routing & audit', 'Experiment atlas', 'Kafka & provenance']
COLORS = ['#60e7c6', '#77a9ff', '#bd9cff', '#ffbc76', '#ff7e9f', '#96d7ff']
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root{color-scheme:dark}.stApp{background:radial-gradient(ellipse at 85% 0%,#172943 0%,#090f1b 45%);color:#e4edf8;font-family:'DM Sans',sans-serif}
.block-container{max-width:1900px;padding-top:2rem}h1,h2,h3{font-family:'Space Grotesk',sans-serif!important;letter-spacing:-.045em!important;color:#eef5ff!important}
[data-testid="stSidebar"]{background:#0d1625;border-right:1px solid #213049}[data-testid="stSidebar"] *{font-family:'DM Sans',sans-serif}
.hero{padding:30px 34px;border:1px solid #2a3c56;border-radius:22px;background:linear-gradient(115deg,#15273b,#111b30 60%,#1b2141);position:relative;overflow:hidden;margin-bottom:22px;animation:rise .6s ease both}
.hero:after{content:'◈';position:absolute;right:40px;top:-70px;font-size:260px;color:#60e7c610;transform:rotate(15deg)}
.eyebrow{font-size:11px;letter-spacing:.23em;color:#60e7c6;font-weight:700}.hero h1{font-size:44px;margin:12px 0 8px;line-height:1.1}.muted{color:#9aaec6;font-size:14px;max-width:800px;line-height:1.7}
.pill{display:inline-block;border:1px solid #3c5867;color:#9debd8;border-radius:30px;padding:5px 11px;font-size:11px;margin-top:14px;margin-right:7px}
[data-testid="stMetric"]{background:#111e30;border:1px solid #27374d;border-radius:15px;padding:17px 20px}[data-testid="stMetricLabel"]{color:#9aaec6}[data-testid="stMetricValue"]{font-family:'Space Grotesk';color:#d5fff1}
.stButton>button{border-radius:10px;border:1px solid #324960;transition:all .2s}.stButton>button:hover{border-color:#60e7c6;transform:translateY(-2px)}.stButton>button[kind="primary"]{background:#60e7c6;color:#071c20;border:0;font-weight:700}
.caption{color:#8fa3bc;font-size:12px}.step{padding:12px 0;border-bottom:1px solid #25344b;color:#b6c6d8}div[data-testid="stExpander"]{border-color:#27374d;border-radius:12px}
@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}

button[kind="primary"] p,button[kind="primary"] span{color:#072c27!important;font-weight:750!important}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p{color:#d9eaff!important}
[data-testid="stCaptionContainer"] p{color:#b6cce4!important} [data-testid="stMetricLabel"] p{color:#d0e3f7!important}
.stApp [data-testid="stMarkdownContainer"]>p{color:#dfebfa;line-height:1.7}
.hero{border-color:#42607d;background:radial-gradient(ellipse at 95% 20%,#21544c77,transparent 55%),linear-gradient(125deg,#172c48,#121b32);padding:28px 34px}
.hero:after{content:'∿';font-size:260px;top:-50px;right:40px;color:#64fbd51a;animation:tide 5s ease-in-out infinite}
.hero h1{font-size:42px}.muted{color:#c1d5eb;font-size:15px}.pill{color:#bdffe7;background:#102c2b88;border-color:#487d70}.eyebrow{color:#8affdb}
[data-testid="stSidebar"]{background:linear-gradient(#111e30,#101827)}
[data-testid="stSidebar"] h2{font-size:32px!important;color:#91ffda!important;letter-spacing:-.05em}
.stProgress [role="progressbar"]>div{background:linear-gradient(90deg,#83b7ff,#6effcb)!important}
@keyframes tide{50%{transform:translateX(-25px) scaleX(1.15);opacity:.5}}
</style>''', unsafe_allow_html=True)

if OCEAN_EDITION:
    from ocean_theme import apply_ocean_shell, ocean_header, ocean_sidebar, PALETTE
    apply_ocean_shell()
    COLORS=PALETTE

@st.cache_data(show_spinner=False)
def read_json(path):
    return json.loads(Path(path).read_text())

@st.cache_data(show_spinner=False)
def csv(path):
    return pd.read_csv(path)

@st.cache_data(show_spinner=False)
def record(path, run_id):
    with Path(path).open() as f:
        for line in f:
            row = json.loads(line)
            if row.get('run_id') == run_id:
                return row
    return None

@st.cache_data(show_spinner=False)
def case_index(seed, scenario):
    rows = []
    for p in sorted((ROOT/'results_multiseed'/f'seed_{seed}'/scenario).glob('*/placement_result.json')):
        d = read_json(str(p))
        rows.append((int(d['run_id']), str(p)))
    return dict(sorted(rows))

def graph(nodes, edges, tree=False, animate=True, height=630):
    for n in nodes:
        nid=str(n['id']).lower()
        if nid=='core':n.update(kind='core',name='Core compute')
        elif nid.startswith('edge'):n.update(kind='edge',name='Edge compute')
        elif nid.startswith('access'):n.update(kind='access',name='Access gateway')
    physical=any(str(n['id']).startswith('access') for n in nodes)
    scene(nodes,edges,title='Infrastructure in motion' if physical else 'Connected workflow',subtitle='Fixed layout · inspect nodes · replay the flow',animate=animate,height=max(height,660),layout='network' if physical else 'tree' if tree else 'flow')

def tree(bt, highlight=(), animate=True):
    events=[e for e in trace_events if e['node_id'] in bt.get('nodes',{})]
    behavior_scene(bt,events,animate=animate)

def plot(fig):
    fig.update_layout(template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font={'family':'Arial','color':'#e4efff','size':13},margin={'l':18,'r':18,'t':65,'b':35},colorway=COLORS,legend={'orientation':'h','y':1.16},transition={'duration':650,'easing':'cubic-in-out'})
    fig.update_xaxes(gridcolor='#263951',tickfont={'color':'#d6e9ff'})
    fig.update_yaxes(gridcolor='#263951',tickfont={'color':'#d6e9ff'})
    # Frames reveal the actual final values; they are presentation interpolation, not observations.
    if fig.data and all(t.type=='bar' for t in fig.data):
        fig.frames=[go.Frame(name=str(i),data=[go.Bar(y=[float(v)*i/20 for v in t.y]) for t in fig.data]) for i in range(21)]
        maximum=max((float(v) for t in fig.data for v in t.y),default=1)
        fig.update_yaxes(range=[0,maximum*1.15])
        fig.update_layout(updatemenus=[{'type':'buttons','direction':'left','x':0,'y':1.25,'bgcolor':'#22405a','font':{'color':'#ffffff'},'buttons':[{'label':'▶ Animate values','method':'animate','args':[None,{'frame':{'duration':40,'redraw':False},'transition':{'duration':40},'fromcurrent':False}]},{'label':'Ⅱ Pause','method':'animate','args':[[None],{'mode':'immediate','frame':{'duration':0,'redraw':False}}]}]}])
    st.plotly_chart(fig,width='stretch',config={'displaylogo':False,'scrollZoom':False})


def evidence(path, data=None):
    with st.expander('Source artifact · inspect & download'):
        st.code(str(Path(path).relative_to(ROOT)),language=None)
        payload=json.dumps(data,indent=2) if data is not None else Path(path).read_text()
        st.download_button('Download source',payload,file_name=Path(path).name,key='download_'+str(path))
        if data is not None:st.json(data,expanded=False)

def launch_wall(ids, current):
    """Callback runs before widget construction, so advancing selection stays legal."""
    if st.session_state.get('wall_started',False):
        current_index=ids.index(current)
        st.session_state.selected_run_id=ids[(current_index+1)%len(ids)]
    st.session_state.wall_launch=True
    st.session_state.motion_nonce=st.session_state.get('motion_nonce',0)+1

folders=sorted([p for p in (ROOT/'TickTide/outputs').iterdir() if p.is_dir() and (p/'execution_service_graphs.jsonl').exists()],key=lambda p:p.name)
preferred=[p for p in folders if p.name.startswith('n1000_seed')]
if not folders:st.error('No recorded execution_service_graphs.jsonl found. Run the project experiment first.');st.stop()
if OCEAN_EDITION:
    ocean_header()
st.markdown('#### Choose your current → then Run' if OCEAN_EDITION else '#### Choose your scenario → then Run')
scenario=st.radio('Placement scenario',['baseline','ingress_only','latency_only','latency_path','capacity_stress','combined'],index=5,horizontal=True,format_func=lambda x:x.replace('_',' ').title(),key='scenario_choice')
scenario_descriptions={
    'baseline':'Unrestricted cost optimization · no ingress pin or added delay bound.',
    'ingress_only':'F1 must be hosted on Edge 1 · other services remain optimized.',
    'latency_only':'2 ms synthetic link delay · 4 ms per data dependency · no ingress pin.',
    'latency_path':'F1 on Edge 1 plus the 4 ms per-dependency propagation limit.',
    'capacity_stress':'Core limited to 600 blocks · offered request rate increased 5×.',
    'combined':'Core limited to 600 blocks · 5× request rate · F1 on Edge 1 · 4 ms dependency limit.'}
st.caption(scenario_descriptions[scenario])
with st.sidebar:
    if OCEAN_EDITION:
        ocean_sidebar()
    else:
        st.markdown('## ∿ tick wave')
        st.caption('RESEARCH, IN MOTION')
    seed=st.selectbox('Research seed',[42,123,2026])
    target=f'n1000_seed{seed}'
    folder=st.selectbox('Recorded experiment',folders,index=next((i for i,p in enumerate(folders) if p.name==target),0),format_func=lambda p:p.name)
    st.caption('Choose a recorded experiment, then follow one request through the full research pipeline.')
    cases=case_index(seed,scenario)
    runs=csv(str(folder/'run_summary.csv'))
    route=st.selectbox('Recorded strategy path',['All paths']+sorted(runs.selected_strategy.unique().tolist()))
    eligible=runs if route=='All paths' else runs[runs.selected_strategy==route]
    run_id=st.selectbox('Execution / Run ID',eligible.run_id.astype(int).tolist(),key='selected_run_id')
    view=st.selectbox('Workspace',['Six-card live wall','Detailed chapter view'])
    if view=='Detailed chapter view':
        animate=st.toggle('Autoplay motion scenes',value=True)
        stage=st.radio('RESEARCH JOURNEY',range(len(STAGES)),format_func=lambda i:f'{i+1:02d}  {STAGES[i]}',key='stage')
    else:
        animate=True
        stage=0
    st.divider()
    st.caption('Local artifacts · no database credentials required')

sg=record(str(folder/'execution_service_graphs.jsonl'),run_id)
if not sg:st.error('Selected run has no recorded Prolog graph.');st.stop()
# Match both topology and per-service workload before reusing an archived result.
matched=None
for rid,p in cases.items():
    d=read_json(p)
    demands=d.get('demands',{})
    if set(demands)==set(sg['service_nodes']) and all(int(demands[k]['workload_ops'])==int(v['total_operations']) and int(demands[k]['invocations'])==int(v['invocation_count']) for k,v in sg['service_nodes'].items()):
        if sorted((e['source'],e['target'],e.get('data_key',''),e.get('dependency_type','')) for e in d.get('logical_edges',[]))==sorted((e['source'],e['target'],e.get('data_key',''),e.get('dependency_type','')) for e in sg['sg_edges']):
            matched=p;break
context=(str(folder),run_id,scenario,seed)
if st.session_state.get('context')!=context:
    st.session_state.context=context;st.session_state.generated={0};st.session_state.pop('fresh',None);st.session_state.wall_started=False
if st.session_state.pop('wall_launch',False):
    st.session_state.wall_started=True
result=st.session_state.get('fresh') or (read_json(matched) if matched else None)
row=runs[runs.run_id==run_id].iloc[0]
trace=csv(str(folder/'execution_log.csv'))
trace=trace[trace.run_id==run_id]
trace_events=json.loads(trace.fillna('').to_json(orient='records'))
if view=='Six-card live wall':
    left,right=st.columns([4,1])
    with left:
        st.markdown('### Follow the current · Six connected views.' if OCEAN_EDITION else '### ∿ tick wave · One request. Six connected views.')
        st.caption(f'RUN {run_id:04d} · STRATEGY {row.selected_strategy} · {scenario.replace("_"," ").upper()} · six independent loops · continuous motion')
    with right:
        st.button('▶ Run next execution' if st.session_state.get('wall_started') else '▶ Run selected path',key='run_wall',type='primary',width='stretch',on_click=launch_wall,args=(eligible.run_id.astype(int).tolist(),run_id))
    with st.spinner('Preparing the selected workflow and independent audit…'):
        wall_data=prepare_wall(str(ROOT),sg,result,scenario)
    if result and set(result.get('placement',{}).values())=={'core'}:
        st.caption('Recorded solution: all services are hosted on Core in this scenario. Co-located dependencies use zero physical hops; no Edge placement is forced for visual effect.')
    render_wall(wall_data,trace_events,started=st.session_state.get('wall_started',False),nonce=st.session_state.get('motion_nonce',0),run_id=run_id,strategy=str(row.selected_strategy),scenario=scenario,seed=seed)
    st.stop()

st.markdown(f'''<div class="hero"><div class="eyebrow">TICK WAVE / FOLLOW THE SIGNAL</div><h1>A request. A ripple.<br>A whole system in motion.</h1><div class="muted">Watch decisions light up. Follow each recorded request from behavior to service graph, through edge–cloud optimization, and into a traceable event pipeline.</div><span class="pill">∿ RECORDED REQUEST REPLAY</span><span class="pill">RUN {run_id:04d}</span><span class="pill">{html.escape(scenario.upper().replace('_',' '))}</span></div>''',unsafe_allow_html=True)
a,b,c,d=st.columns(4)
a.metric('Recorded executions',f'{len(runs):,}');b.metric('Topology families',runs.topology_signature.nunique());c.metric('Selected strategy',str(row.selected_strategy));d.metric('Synthetic work / request',f'{sg["total_operations"]:,}')
st.write('')
st.progress((stage+1)/len(STAGES),text=f'CHAPTER {stage+1:02d} / {len(STAGES):02d} · {STAGES[stage].upper()}')
l,r=st.columns([3,2])
with l:st.subheader(STAGES[stage])
with r:
    if st.button(['▶ Replay this behavior tree','↗ Follow this request','⑂ Reveal executed branches','◆ Build service dependencies','▥ Calculate resource demands','⬡ Illuminate infrastructure','▤ Reveal placement','✓ Trace routes & verify','▥ Explore experiment results','◉ Preview event pipeline'][stage],type='primary',width='stretch'):
        st.session_state.generated.add(stage)
        st.session_state.motion_nonce=st.session_state.get('motion_nonce',0)+1
st.caption('Recorded events power the replay. Use the canvas controls to pause, step through, change speed or expand the view.')
if stage not in st.session_state.generated:
    st.info('Your next transformation is ready. Use the highlighted action above to reveal it.');
    a,b=st.columns(2)
    if stage>0:a.button('← Previous chapter',on_click=lambda:st.session_state.update(stage=stage-1))
    if stage<len(STAGES)-1:b.button('Next chapter →',on_click=lambda:st.session_state.update(stage=stage+1))
    st.stop()

if stage==0:
    st.write('A sequence coordinates initialization, strategy selection, recovery and finalization. Fallback evaluates alternatives in order; retry decorators allow repeated attempts.')
    tree(read_json(str(ROOT/'TickTide/config/generic_bt.json')),animate=animate)
    st.caption('The entire tree remains in place. Green light follows actual visits; rose marks recorded failures. Replay another Run to inspect a different path.')
    evidence(ROOT/'TickTide/config/generic_bt.json')
elif stage==1:
    st.write('One request, every decision. Watch the selected execution travel through the full behavior tree; unvisited branches stay visible for context.')
    behavior_scene(read_json(str(ROOT/'TickTide/config/generic_bt.json')),trace_events,animate=animate)
    with st.expander('Recorded event ledger'):
        st.dataframe(trace,width='stretch',hide_index=True)
    st.caption('Replay follows recorded event order. Playback speed is a presentation control, not measured runtime.')
elif stage==2:
    x,y=st.tabs(['Visited behavior tree','Resolved service path'])
    for tab,filename,key in [(x,'executed_bts.jsonl','executed_bt'),(y,'executed_path_bts.jsonl','executed_path_bt')]:
        with tab:
            item=record(str(folder/filename),run_id)
            if item:tree(item[key],animate=animate);evidence(folder/filename,item)
            else:st.warning('Artifact unavailable for this run.')
    st.info('Failed actions that actually ran remain part of the workflow. Retry multiplicity contributes work without implying simultaneous replicas.')
elif stage==3:
    mode=st.radio('Dependency layer',['All dependencies','Data','Control'],horizontal=True)
    edges=[dict(e,label=e.get('data_key') or 'control',color='#60e7c6' if e.get('data_key') else '#a897dd',dashes=not bool(e.get('data_key'))) for e in sg['sg_edges'] if mode=='All dependencies' or e.get('dependency_type','').lower()==mode.lower()]
    graph([{'id':k,'label':f'{k} · {v["name"]}\n{v["invocation_count"]} invocation(s)','title':json.dumps(v)} for k,v in sg['service_nodes'].items()],edges,animate=animate)
    st.code('\n'.join(sg.get('prolog_raw_edges',[])),language='prolog')
    st.caption('Raw Prolog edge(dependent, dependency, reason) is displayed above; graph arrows follow normalized source → target dependencies.')
    evidence(folder/'execution_service_graphs.jsonl',sg)
elif stage==4:
    from integration.pipeline import derive_demands, PROFILES
    from run_experiments import scenarios
    import csv as csv_module
    cfg={name:config for name,config,_ in scenarios(read_json(str(ROOT/'config/research_scenario_strict.json')))}[scenario]
    with PROFILES.open() as f:profiles={v['task_id']:v for v in csv_module.DictReader(f)}
    demands,bw,_=derive_demands(sg,cfg,profiles)
    frame=pd.DataFrame.from_dict(demands,orient='index').rename_axis('service').reset_index()
    st.latex(r'CPU_i=\max(CPU_{min},\;work_i\,\lambda\,h / throughput)')
    x,y=st.columns(2)
    with x:plot(px.bar(frame,x='service',y='cpu',labels={'cpu':'Equivalent vCPU'},color_discrete_sequence=COLORS))
    with y:plot(px.bar(frame,x='service',y='memory',labels={'memory':'Resident memory (MB)'},color_discrete_sequence=[COLORS[1]]))
    st.dataframe(frame,width='stretch',hide_index=True)
    st.json(cfg,expanded=False)
    st.caption('Synthetic planning assumptions. Arrival rate is requests/second; Monte Carlo run count is a replication count. Pure control edges do not create traffic.')
elif stage==5:
    from integration.pipeline import setup_network
    net,sites,links=setup_network()
    graph([{'id':n['id'],'label':n['id'].upper(),'title':json.dumps(sites.get(n['id'],n)),'color':'#514376' if n['id']=='core' else '#235750'} for n in net['nodes']],[{'source':a,'target':b,'label':f'{v["capacity"]:g} Mbps'} for (a,b),v in links.items()],animate=animate)
    st.dataframe(pd.DataFrame(sites).T,width='stretch')
    st.caption('Original physical network. Capacity and propagation overlays are applied by scenario during optimization; values are synthetic.')
    evidence(ROOT/'Team3_Orchestrator_original/input_json/ng.json')
elif stage==6:
    from integration.pipeline import run_model_calibrated
    from run_experiments import scenarios
    st.write('Minimize site and connection block costs subject to service placement, CPU/RAM, routing, pinning and scenario constraints.')
    if st.button('▶ Run live HiGHS optimization',type='primary'):
        with st.spinner('Solving selected recorded workflow with the configured MILP time limit…'):
            cfg={name:config for name,config,_ in scenarios(read_json(str(ROOT/'config/research_scenario_strict.json')))}[scenario]
            try:
                fresh=run_model_calibrated(sg,cfg)
                st.session_state.fresh=fresh;result=fresh
            except Exception as exc:st.error(f'Optimization failed: {exc}')
    if result:
        st.caption('LIVE SOLVE · current session' if st.session_state.get('fresh') else f'ARCHIVED SOLUTION · equivalent topology and workload · representative run {result["run_id"]}')
        a,b,c=st.columns(3);a.metric('Solver status',result['status']);b.metric('Reference cost',f'{result.get("objective",0):,.2f}');c.metric('Reported MILP gap',str(result.get('gap','unavailable')))
        nodes=[{'id':site,'label':site.upper(),'color':'#514376'} for site in result.get('site_usage',{})]
        nodes += [{'id':k,'label':f'{k} · {sg["service_nodes"][k]["name"]}','color':'#235750'} for k in result.get('placement',{})]
        graph(nodes,[{'source':site,'target':s,'label':'hosts'} for s,site in result.get('placement',{}).items()],tree=True,animate=animate)
        st.dataframe(pd.DataFrame(result.get('site_usage',{})).T,width='stretch')
        st.json(result.get('scenario',{}),expanded=False)
    else:st.warning('No matching archived solution. Run live optimization to calculate this workflow.')
elif stage==7:
    if not result:st.warning('Generate a placement in chapter 07 first.');st.stop()
    from validate_all_workloads import independent_audit
    audit=independent_audit(sg,result,result['scenario'])
    st.success('Independent recomputation: PASS') if audit['pass'] else st.error('Independent recomputation: FAIL — inspect checks below')
    routes=result.get('routing',[])
    from integration.pipeline import setup_network
    net,_,links=setup_network()
    active={tuple(h) for r in routes for h in r['path']}
    graph([{'id':n['id'],'label':n['id'].upper()} for n in net['nodes']],[{'source':a,'target':b,'color':'#60e7c6' if (a,b) in active else '#31405a','label':f'{result.get("link_usage",{}).get(a+"->"+b,0):g} Mbps'} for a,b in links],animate=animate,height=420)
    st.dataframe(pd.DataFrame(routes).assign(path=lambda f:f.path.map(lambda p:' → '.join([p[0][0]]+[h[1] for h in p]) if p else 'Co-located · no physical hops')),width='stretch',hide_index=True)
    st.dataframe(pd.DataFrame(audit['checks']),width='stretch',hide_index=True)
    st.caption('Feasibility audit validates implemented constraints and objective arithmetic. Delay limits concern individual dependency propagation, not an end-to-end SLA.')
elif stage==8:
    comp=csv(str(ROOT/'results_multiseed/three_seed_comparison.csv'))
    chosen=st.multiselect('Seeds to compare',sorted(comp.seed.unique()),default=sorted(comp.seed.unique()))
    comp=comp[comp.seed.isin(chosen)].copy();comp['seed_label']=comp.seed.astype(str)
    if comp.empty:st.info('Select at least one seed.');st.stop()
    a,b,c=st.columns(3);a.metric('Archived optimization cases',int(comp.groups.sum()));b.metric('Reported audit failures',int(comp.audit_failures.sum()));c.metric('Distinct simulation executions',int(comp.groupby('seed').executions.max().sum()))
    plot(px.bar(comp,x='scenario',y='weighted_mean_cost',color='seed_label',barmode='group',labels={'weighted_mean_cost':'Frequency-weighted reference cost','seed_label':'Seed'},color_discrete_sequence=COLORS))
    x,y=st.columns(2)
    with x:plot(px.histogram(runs,x='total_operations',nbins=30,labels={'total_operations':'Synthetic work per request'},color_discrete_sequence=[COLORS[1]]))
    with y:plot(px.pie(runs,names='selected_strategy',hole=.7,color_discrete_sequence=COLORS))
    conv=csv(str(folder/'convergence_summary.csv'))
    plot(px.line(conv,x='runs',y=['p_strategy_a','p_strategy_b','p_recovery'],markers=True,labels={'value':'Observed strategy frequency','runs':'Monte Carlo executions'}))
    st.dataframe(comp.drop(columns='seed_label'),width='stretch',hide_index=True)
    st.caption('Weighted cost = Σ(group frequency × group cost) / Σ(group frequency). Three seeds provide descriptive replication. Equal latency-only cost is a valid negative result; synthetic parameters do not establish measured industry performance.')
    evidence(ROOT/'results_multiseed/three_seed_comparison.csv')
elif stage==9:
    st.write('A service graph becomes an event. A solver transforms it into placement. A writer carries the audited result into Neo4j.')
    kafka_scene(animate=animate)
    a,b,c=st.columns(3)
    a.metric('Kafka broker','Not verified')
    b.metric('Delivery status','Not verified')
    c.metric('Pipeline mode','Architecture preview')
    st.caption('This motion scene follows automation.py topic wiring. It does not claim a live broker connection or publish messages.')
    with st.expander('Pipeline launch commands · run in separate terminals'):
        st.code('.venv/bin/python ticktide_kafka_automation/automation.py watch\n.venv/bin/python ticktide_kafka_automation/automation.py solve\n.venv/bin/python ticktide_kafka_automation/automation.py write',language='bash')
    st.divider()
    st.subheader('Evidence that travels with the result')
    for title,path in [('Generic workflow',ROOT/'TickTide/config/generic_bt.json'),('Prolog conversion rules',ROOT/'TickTide/prolog/btsg.pl'),('Execution service graphs',folder/'execution_service_graphs.jsonl'),('Physical infrastructure',ROOT/'Team3_Orchestrator_original/input_json/ng.json'),('Scientific methodology',ROOT/'README_RESEARCH_METHOD.md')]:
        st.markdown(f'**{title}**');st.code(str(path.relative_to(ROOT)),language=None)
    bundle={'experiment':folder.name,'run_id':run_id,'archive_seed':seed,'scenario':scenario,'service_graph':sg,'placement_result':result,'solution_mode':'live' if st.session_state.get('fresh') else 'archived_equivalent_workload' if result else 'unavailable','synthetic_inputs':True}
    st.download_button('↓ Download selected research evidence',json.dumps(bundle,indent=2),file_name=f'ticktide_run{run_id}_{scenario}.json',mime='application/json',type='primary')
    if result:
        from integration.pipeline import to_cypher,setup_network
        st.download_button('↓ Export Neo4j Cypher',to_cypher(sg,result,setup_network()[0]),file_name=f'ticktide_run{run_id}.cypher')
    st.markdown((ROOT/'README_RESEARCH_METHOD.md').read_text())

st.divider()
a,b=st.columns(2)
if stage>0:a.button('← Previous chapter',on_click=lambda:st.session_state.update(stage=stage-1))
if stage<len(STAGES)-1:b.button('Next chapter →',on_click=lambda:st.session_state.update(stage=stage+1))
st.caption('TICK WAVE / RESEARCH IN MOTION     ·     Synthetic model inputs     ·     Evidence before inference')

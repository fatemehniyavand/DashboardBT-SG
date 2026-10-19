"""One clock, six fixed panels, a repeating evidence-backed research story."""
import json
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

@st.cache_data(show_spinner=False)
def prepare_wall(root, sg, result, scenario):
    from integration.pipeline import setup_network, derive_demands, PROFILES
    from run_experiments import scenarios
    from validate_all_workloads import independent_audit
    import csv
    root=Path(root)
    cfg={name:c for name,c,_ in scenarios(json.loads((root/'config/research_scenario_strict.json').read_text()))}[scenario]
    with PROFILES.open() as f:profiles={r['task_id']:r for r in csv.DictReader(f)}
    demands,bw,_=derive_demands(sg,cfg,profiles)
    net,sites,links=setup_network()
    site_evidence=[]
    for site,cap in sites.items():
        limit=cfg.get('site_max_blocks_override',{}).get(site,min(cap['cpu']/cap['cpu_per_block'],cap['memory']/cap['memory_per_block']))
        usage=(result or {}).get('site_usage',{}).get(site,{})
        hosted=[service for service,target in (result or {}).get('placement',{}).items() if target==site]
        site_evidence.append({'id':site,'services':hosted,'cpu_used':usage.get('cpu',0),'cpu_limit':limit*cap['cpu_per_block'],'ram_used':usage.get('memory_MB',0),'ram_limit':limit*cap['memory_per_block'],'block_limit':limit,'blocks':(result or {}).get('solver_site_blocks',{}).get(site,0),'cost_per_block':cap['cost_block']})
    return {'bt':json.loads((root/'TickTide/config/generic_bt.json').read_text()),'sg':sg,'result':result,'demands':demands,'scenario_config':cfg,'bandwidth':[{'source':a,'target':b,'Mbps':v} for (a,b),v in bw.items()],'network':net,'sites':sites,'links':[dict(source=a,target=b,**v) for (a,b),v in links.items()], 'site_evidence':site_evidence, 'audit':independent_audit(sg,result,result['scenario']) if result else None}

def render_wall(data, events, *, started=False, nonce=0, run_id=1, strategy='', scenario='', seed=42):
    payload=json.dumps(dict(data,events=events,started=started,nonce=nonce,run_id=run_id,strategy=strategy,scenario=scenario,seed=seed),ensure_ascii=False).replace('</',r'<\/')
    template=Path(__file__).with_name('wall.html').read_text()
    if st.session_state.get('_tick_wave_edition')=='ocean':
        from ocean_theme import ocean_markup
        template=ocean_markup(template)
    components.html(template.replace('__DATA__',payload),height=900,scrolling=True)

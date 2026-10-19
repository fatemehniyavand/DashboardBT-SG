"""Research scenarios on all seven topology families from validated REAL Prolog outputs.
Requires an existing execution_service_graphs.jsonl (run_research.py generates it).
No synthetic SGs; all changes to ng capacities are experiment-only in memory.
"""
import argparse, collections, copy, csv, json
from pathlib import Path
from integration.pipeline import record, read_json, write_json, run_model_calibrated, setup_network, to_cypher
BASE=Path(__file__).resolve().parent

def key(run):
    return json.dumps({'nodes':sorted(run['service_nodes']), 'edges':sorted((e['source'],e['target'],e.get('data_key',''),e.get('dependency_type','')) for e in run['sg_edges'])},sort_keys=True)

def scenarios(base):
    initial=copy.deepcopy(base)
    yield 'baseline',initial,{'purpose':'Unrestricted cost-minimization with original network'}
    # Independent controls: separate ingress anchoring from per-hop delay bounds.
    ingress=copy.deepcopy(base)
    ingress['pinned_services']={'F1':'edge1'}
    yield 'ingress_only',ingress,{'purpose':'F1 anchored at edge1; no additional path-delay bound'}
    latency_only=copy.deepcopy(base)
    _,_,latency_links=setup_network()
    latency_only['synthetic_link_delays_ms']={f'{u}->{v}':2.0 for u,v in latency_links}
    latency_only['max_data_path_delay_ms']=4.0
    yield 'latency_only',latency_only,{'purpose':'Synthetic 2ms/hop and max 4ms/data-dependency; no ingress anchor'}
    # Anchor at access-adjacent edge1; a 2 ms-per-hop synthetic scenario is an ASSUMPTION.
    delay=copy.deepcopy(base)
    delay['pinned_services']={'F1':'edge1'}
    _,_,links=setup_network()
    delay['synthetic_link_delays_ms']={f'{u}->{v}':2.0 for u,v in links}
    delay['max_data_path_delay_ms']=4.0
    yield 'latency_path',delay,{'purpose':'Ingress anchored at edge1; max 4ms propagation per dependency, not end-to-end'}
    stress=copy.deepcopy(base)
    stress['site_max_blocks_override']={'core':600}
    stress['request_arrival_rate_rps']=base['request_arrival_rate_rps']*5
    yield 'capacity_stress',stress,{'purpose':'Core availability capped to 600 blocks, arrival rate 5x; synthetic stress'}
    combined=copy.deepcopy(stress)
    combined['pinned_services']={'F1':'edge1'}
    combined['synthetic_link_delays_ms']={f'{u}->{v}':2.0 for u,v in links}
    combined['max_data_path_delay_ms']=4.0
    yield 'combined',combined,{'purpose':'Stress with edge ingress and per-dependency path latency bound'}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--jsonl',type=Path,default=BASE/'TickTide/outputs/n1000_seed42/execution_service_graphs.jsonl')
    ap.add_argument('--scenario',type=Path,default=BASE/'config/research_scenario.json')
    ap.add_argument('--output',type=Path,default=BASE/'results_experiments')
    a=ap.parse_args()
    if not a.jsonl.exists():raise SystemExit('Run python run_research.py --runs 1000 --seed 42 --run-id 1 first')
    original=list(record(a.jsonl))
    if not original:raise SystemExit('No Prolog executions found')
    seen={};freq=collections.Counter()
    for r in original:
        k=key(r);freq[k]+=1
        seen.setdefault(k,r)
    print('Real runs:',len(original),'Distinct graph families:',len(seen))
    a.output.mkdir(parents=True,exist_ok=True)
    base=read_json(a.scenario);rows=[];network=setup_network()[0]
    columns=['scenario','run_id','topology_family','frequency','status','objective','core_memory_MB','edge1_memory_MB','edge2_memory_MB','sites_used','physical_routed_dependencies','max_path_propagation_ms','model_gap','note']
    for family,(k,run) in enumerate(sorted(seen.items(),key=lambda e:e[1]['run_id']),1):
        for name,sc,meta in scenarios(base):
            folder=a.output/name/f'topology_{family:02d}_run_{run["run_id"]}'
            folder.mkdir(parents=True,exist_ok=True)
            try:
                result=run_model_calibrated(run,sc)
                write_json(folder/'placement_result.json',result)
                write_json(folder/'scenario.json',sc)
                if result['status']=='OPTIMAL' and result.get('validated_capacity'):
                    (folder/'neo4j_import.cypher').write_text(to_cypher(run,result,network))
                row={'scenario':name,'run_id':run['run_id'],'topology_family':family,'frequency':freq[k],
                     'status':result['status'],'objective':result.get('objective',''),
                     'sites_used':','.join(sorted(set(result.get('placement',{}).values()))),
                     'physical_routed_dependencies':result.get('routed_dependency_count',''),
                     'max_path_propagation_ms':result.get('max_routed_path_delay_ms',''),
                     'model_gap':result.get('gap',''),'note':meta['purpose']}
                for site in ('core','edge1','edge2'):row[f'{site}_memory_MB']=result.get('site_usage',{}).get(site,{}).get('memory_MB','')
            except Exception as e:
                row={'scenario':name,'run_id':run['run_id'],'topology_family':family,'frequency':freq[k], 'status':'ERROR','note':str(e)}
            rows.append(row)
            print(name,'family',family,'run',run['run_id'],'=>',row['status'],'sites',row.get('sites_used',''))
    with (a.output/'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)
    write_json(a.output/'provenance.json',{'source':str(a.jsonl),'runs':len(original),'families':len(seen),'models_are_synthetic':True,'original_network_unchanged':True,'latency_model':'per-dependency path propagation with synthetic 2ms/link, not E2E','scope':'one representative run per unique topology; not aggregate/averaged traffic across 1000 runs'})
    print('Done:',len(rows),'experiment cases ->',a.output/'comparison.csv')
if __name__=='__main__':main()

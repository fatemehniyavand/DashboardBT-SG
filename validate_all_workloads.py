"""Independent post-solve feasibility audit + topology/workload grouping.
All inputs must be the original SWI-Prolog-derived JSONL; no generated SGs.
"""
import argparse, collections, csv, json, math
from pathlib import Path
from integration.pipeline import record, read_json, write_json, setup_network, run_model_calibrated, derive_demands, PROFILES
from run_experiments import key as topology_key, scenarios

ROOT=Path(__file__).resolve().parent

def workload_key(run):
    return json.dumps({'topology':topology_key(run),'service_workload':sorted((s,int(n['invocation_count']),int(n['total_operations'])) for s,n in run['service_nodes'].items())},sort_keys=True)

def independent_audit(run, result, scenario, atol=1e-5):
    checks=[]
    def check(name, good, detail=''):
        checks.append({'check':name,'pass':bool(good),'detail':str(detail)})
    net,sites,links=setup_network()
    for site,blocks in scenario.get('site_max_blocks_override',{}).items():
        if site not in sites: raise ValueError('Unknown site override')
        sites[site]['cpu']=blocks*sites[site]['cpu_per_block']
        sites[site]['memory']=blocks*sites['%s'%site]['memory_per_block']
    with PROFILES.open() as f:profiles={r['task_id']:r for r in csv.DictReader(f)}
    expected_demand,expected_bw,_=derive_demands(run,scenario,profiles)
    placement=result.get('placement',{});routes=result.get('routing',[])
    check('status_optimal',result.get('status')=='OPTIMAL',result.get('status'))
    check('all_services_placed_once',set(placement)==set(run['service_nodes']) and all(p in sites for p in placement.values()),placement)
    for s,d in expected_demand.items():
        reported=result.get('demands',{}).get(s,{})
        check(f'demand_{s}', all(math.isclose(float(reported.get(k,float('nan'))),float(d[k]),rel_tol=1e-9,abs_tol=atol) for k in ('cpu','memory','workload_ops','invocations')),reported)
    for s,p in scenario.get('pinned_services',{}).items():
        if s in run['service_nodes']:check(f'pin_{s}',placement.get(s)==p,placement.get(s))
    cpu=collections.defaultdict(float);ram=collections.defaultdict(float);link_bw=collections.defaultdict(float)
    for s,p in placement.items():
        if p in sites and s in expected_demand:
            cpu[p]+=expected_demand[s]['cpu'];ram[p]+=expected_demand[s]['memory']
    blocks={}
    for p,site in sites.items():
        blocks[p]=math.ceil(max(cpu[p]/site['cpu_per_block'],ram[p]/site['memory_per_block'])-1e-9)
        maxblocks=min(site['cpu']/site['cpu_per_block'],site['memory']/site['memory_per_block'])
        check(f'cpu_{p}',cpu[p]<=site['cpu']+atol,f'{cpu[p]} / {site["cpu"]}')
        check(f'ram_{p}',ram[p]<=site['memory']+atol,f'{ram[p]} / {site["memory"]}')
        check(f'blocks_{p}',blocks[p]<=maxblocks+atol,f'{blocks[p]} / {maxblocks}')
        rep=result.get('site_usage',{}).get(p,{})
        check(f'usage_report_{p}',abs(float(rep.get('cpu',0))-cpu[p])<atol and abs(float(rep.get('memory_MB',0))-ram[p])<atol,'reported vs independently computed')
    route_count=collections.Counter((r.get('source'),r.get('target')) for r in routes)
    check('every_data_dependency_routed_once',route_count==collections.Counter(expected_bw.keys()),f'expected={len(expected_bw)}, observed={len(routes)}')
    limit=scenario.get('max_data_path_delay_ms');delay_overrides=scenario.get('synthetic_link_delays_ms',{})
    for i,r in enumerate(routes):
        pair=(r.get('source'),r.get('target'));src=placement.get(pair[0]);dst=placement.get(pair[1]);path=[tuple(z) for z in r.get('path',[])]
        good=(src is not None and dst is not None and r.get('from')==src and r.get('to')==dst)
        cur=src;delay=0.0
        for hop in path:
            if len(hop)!=2 or hop not in links or hop[0]!=cur:good=False;break
            cur=hop[1];delay+=float(delay_overrides.get(f'{hop[0]}->{hop[1]}',links[hop]['delay_ms']))
            link_bw[hop]+=float(r.get('bandwidth_Mbps',0))
        if cur!=dst or (src==dst and path):good=False
        check(f'path_{i}',good, f'{pair}: {src}->{dst}: {path}')
        check(f'bandwidth_demand_{i}',pair in expected_bw and math.isclose(float(r.get('bandwidth_Mbps',-1)),expected_bw.get(pair,-2),abs_tol=atol,rel_tol=1e-8),r.get('bandwidth_Mbps'))
        if limit is not None:check(f'path_delay_{i}',delay<=limit+atol,f'{delay} <= {limit} ms')
    linkblocks={}
    for hop,info in links.items():
        linkblocks[hop]=math.ceil(link_bw[hop]/info['per_block']-1e-9)
        check('link_capacity_'+str(hop),link_bw[hop]<=info['capacity']+atol,f'{link_bw[hop]} / {info["capacity"]}')
        check('link_blocks_'+str(hop),linkblocks[hop]<=info['capacity']/info['per_block']+atol)
        check('link_usage_report_'+str(hop),math.isclose(float(result.get('link_usage',{}).get(f'{hop[0]}->{hop[1]}',0)),link_bw[hop],abs_tol=atol))
    recomputed=sum(blocks[p]*sites[p]['cost_block'] for p in sites)+sum(linkblocks[h]*links[h]['cost_block'] for h in links)
    check('objective_recomputed',math.isclose(float(result.get('objective',float('nan'))),recomputed,abs_tol=1e-3,rel_tol=1e-7),f'reported={result.get("objective")}, recomputed={recomputed}')
    return {'pass':all(c['pass'] for c in checks),'checks':checks,'independent_objective':recomputed,'site_blocks':blocks,'link_blocks':{f'{u}->{v}':v0 for (u,v),v0 in linkblocks.items()}}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--jsonl',type=Path,default=ROOT/'TickTide/outputs/n1000_seed42/execution_service_graphs.jsonl')
    ap.add_argument('--scenario',type=Path,default=ROOT/'config/research_scenario.json')
    ap.add_argument('--output',type=Path,default=ROOT/'results_validation')
    ap.add_argument('--scenarios',choices=('all','baseline','combined'),default='all')
    ap.add_argument('--max-groups',type=int,default=0,help='0=all unique workload groups')
    a=ap.parse_args()
    if not a.jsonl.is_file():ap.error('Missing original Prolog JSONL: run run_research.py first')
    runs=list(record(a.jsonl));base=read_json(a.scenario)
    grouped={};weights=collections.Counter();topo=collections.Counter()
    for r in runs:
        k=workload_key(r);grouped.setdefault(k,r);weights[k]+=1;topo[topology_key(r)]+=1
    selected=sorted(grouped.items(),key=lambda kv:int(kv[1]['run_id']))
    if a.max_groups>0:selected=selected[:a.max_groups]
    a.output.mkdir(parents=True,exist_ok=True)
    scenario_defs=[(name,sc,meta) for name,sc,meta in scenarios(base) if a.scenarios=='all' or name==a.scenarios]
    rows=[];fails=0
    print('Total executions',len(runs),'Unique topologies',len(topo),'Unique topology+workload signatures',len(grouped))
    for index,(k,run) in enumerate(selected,1):
        for name,sc,meta in scenario_defs:
            res=run_model_calibrated(run,sc)
            audit=independent_audit(run,res,sc) if res.get('placement') else {'pass':False,'checks':[{'check':'no_solution','pass':False,'detail':res['status']}]}
            folder=a.output/name/f'group_{index:03d}_run_{run["run_id"]}'
            folder.mkdir(parents=True,exist_ok=True)
            write_json(folder/'placement_result.json',res);write_json(folder/'independent_audit.json',audit)
            if not audit['pass']:fails+=1
            rows.append({'scenario':name,'group':index,'representative_run':run['run_id'],'frequency':weights[k], 'status':res['status'],'audit_pass':audit['pass'],'violations':sum(not c['pass'] for c in audit['checks']),'objective':res.get('objective',''),'sites':','.join(sorted(set(res.get('placement',{}).values()))),'workload_ops':run['total_operations'],'topology_service_count':len(run['service_nodes']),'retry_F4':run['service_nodes'].get('F4',{}).get('invocation_count',0),'retry_F7':run['service_nodes'].get('F7',{}).get('invocation_count',0)})
            print(name,'run',run['run_id'],'frequency',weights[k],res['status'],'AUDIT', 'PASS' if audit['pass'] else 'FAIL')
    with (a.output/'all_workload_comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else []);w.writeheader();w.writerows(rows)
    write_json(a.output/'summary.json',{'total_runs':len(runs),'unique_topologies':len(topo),'unique_topology_workload_signatures':len(grouped),'workload_groups_processed':len(selected),'scenarios_per_group':len(scenario_defs),'audited_solutions':len(rows),'audit_failures':fails,'all_input_values_synthetic':True,'scope':'one representative per unique topology+per-service invocations and operations; weighted frequency retained; no time-dependent schedule'})
    print('Finished:',len(rows),'cases; audit failures:',fails,'Output:',a.output)
    if fails:raise SystemExit(2)

if __name__=='__main__':main()

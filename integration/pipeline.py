"""Evidence-preserving TickTide->Network MILP->Neo4j research integration.
Requires output produced by the UNCHANGED SWI-Prolog conversion in TickTide.
No artificial data is passed off as Prolog-derived.
"""
from __future__ import annotations
import argparse, csv, json, math, pathlib, collections
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import lil_matrix
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
NETWORK=ROOT/'Team3_Orchestrator_original/input_json/ng.json'
PROFILES=ROOT/'TickTide/config/task_profiles.csv'
SCALE=50000  # synthetic normalized work units / vCPU / planning window, NOT measured
MEMORY={'Light':128,'Light-Medium':192,'Medium':256,'Heavy':512}
BANDWIDTH=1.0 # synthetic Mbps / data-dependency; NOT measured; set to zero for pure logical edges

def read_json(path): return json.loads(pathlib.Path(path).read_text())
def write_json(path,obj):pathlib.Path(path).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def cyq(x):return json.dumps(str(x),ensure_ascii=False)
def record(path):
    with open(path) as f:
        for line in f:
            if line.strip():yield json.loads(line)

def setup_network():
    net=read_json(NETWORK)['cloudnet_graph']
    sites={}; links={}
    for node in net['nodes']:
        for cap in node['capabilities']:
            if cap['type']=='computation':
                d={r['type']:float(r['capacity']['value']) for r in cap['resources']}
                sites[node['id']]={'cpu':d['cpu']*cap['max_blocks'],'memory':d['memory']*cap['max_blocks'], 'cpu_per_block':d['cpu'],'memory_per_block':d['memory'], 'cost_block':float(cap['cost_per_block']['value']), 'capability':cap['id']}
    for e in net['links']:
        if e['type']=='wireline':
            r=next(r for r in e['resources'] if r['type']=='bandwidth')
            links[(e['origin'],e['target'])]={'capacity':float(r['capacity']['value'])*e['max_blocks'],'per_block':float(r['capacity']['value']),'cost_block':float(e['cost_per_block']['value']),'delay_ms':float(e['propagation_delay']['value'])}
    return net,sites,links

def candidates(src,dst,links):
    if src==dst:return [[]]
    adj=collections.defaultdict(list)
    for a,b in links:adj[a].append(b)
    paths=[]
    def dfs(cur,seen,path):
        if cur==dst:
            paths.append(path[:]);return
        for b in sorted(adj[cur]):
            if b not in seen:dfs(b,seen|{b},path+[(cur,b)])
    dfs(src,{src},[])
    return paths

def run_model(run, data_edge_policy='assume_all', bw=BANDWIDTH):
    net,sites,links=setup_network()
    # Experiment-only overrides; original ng.json is unchanged.
    overrides=scenario.get('site_max_blocks_override',{})
    for site,blocks in overrides.items():
        if site not in sites or not (0 <= blocks <= sites[site]['cpu']/sites[site]['cpu_per_block']):
            raise ValueError('Invalid capacity override: '+site)
        sites[site]['cpu']=blocks*sites[site]['cpu_per_block']
        sites[site]['memory']=blocks*sites[site]['memory_per_block']
    with PROFILES.open() as f:profiles={p['task_id']:p for p in csv.DictReader(f)}
    nodes=run['service_nodes']; edges=run['sg_edges']; ordered=sorted(nodes)
    if not nodes:raise ValueError('empty executed graph')
    assert sum(int(n['total_operations']) for n in nodes.values())==int(run['total_operations'])
    demands={}
    for id,n in nodes.items():
        assert int(n['operations_per_invocation'])*int(n['invocation_count'])==int(n['total_operations'])
        clazz=profiles[id]['workload_class']
        demands[id]={'cpu':max(1,math.ceil(int(n['total_operations'])/SCALE)),'memory':MEMORY[clazz], 'workload_ops':int(n['total_operations']),'invocations':int(n['invocation_count'])}
    if data_edge_policy=='assume_all':
        data_edges=sorted({(e['source'],e['target']) for e in edges if e['source']!=e['target']})
    elif data_edge_policy=='explicit_data_key':
        data_edges=sorted({(e['source'],e['target']) for e in edges if e.get('data_key') and e['source']!=e['target']})
    else:raise ValueError('Unknown data edge policy')
    if any(a not in nodes or b not in nodes for a,b in data_edges):raise ValueError('Prolog edge references unknown service')
    # Binary x_{service,site}; binary z_{dependency, origin_site, target_site, path}.
    # Use exact linear coupling: each selected site pair chooses exactly one path.
    snames=sorted(sites)
    xs=[('x',s,p) for s in ordered for p in snames]
    zs=[]
    for ei,(a,b) in enumerate(data_edges):
        for p in snames:
            for q in snames:
                for pi,path in enumerate(candidates(p,q,links)):
                    zs.append(('z',ei,p,q,pi,tuple(path)))
    variables=xs+zs
    ix={v:i for i,v in enumerate(variables)}
    c=np.zeros(len(variables))
    # Physical resource blocks cost max(cpu block, ram block) per site.
    # To linearize max, allocate integer b_site >= sum_cpu, sum_memory; and minimize cost.
    bs=[('block',p) for p in snames]
    # Link allocated blocks continuous upper bound integer, similarly.
    ls=[('link_block',a,b) for a,b in sorted(links)]
    variables+=bs+ls; ix={v:i for i,v in enumerate(variables)}
    c=np.zeros(len(variables));integer=np.ones(len(variables),dtype=int)
    for v in bs:c[ix[v]]=sites[v[1]]['cost_block']
    for v in ls:c[ix[v]]=links[v[1:]]['cost_block']
    rows=[]
    def constraint(coeff,low=-np.inf,high=np.inf):rows.append((coeff,low,high))
    for s in ordered:constraint({ix[('x',s,p)]:1 for p in snames},1,1)
    for ei,(a,b) in enumerate(data_edges):
        # exact origin assignment marginal and destination marginal
        for p in snames:
            zlist=[ix[z] for z in zs if z[1]==ei and z[2]==p]
            d={j:1 for j in zlist};d[ix[('x',a,p)]]=-1;constraint(d,0,0)
        for q in snames:
            zlist=[ix[z] for z in zs if z[1]==ei and z[3]==q]
            d={j:1 for j in zlist};d[ix[('x',b,q)]]=-1;constraint(d,0,0)
    for p in snames:
        site=sites[p]
        for resource in ('cpu','memory'):
            coeff={ix[('x',s,p)]:demands[s][resource]/site[resource+'_per_block'] for s in ordered}
            coeff[ix[('block',p)]]=-1
            constraint(coeff,high=0)
        constraint({ix[('block',p)]:1},high=min(site['cpu']/site['cpu_per_block'],site['memory']/site['memory_per_block']))
    for (a,b),info in links.items():
        coeff={ix[z]:bw/info['per_block'] for z in zs if (a,b) in z[5]}
        coeff[ix[('link_block',a,b)]]=-1
        constraint(coeff,high=0)
        constraint({ix[('link_block',a,b)]:1},high=info['capacity']/info['per_block'])
    mat=lil_matrix((len(rows),len(variables)),dtype=float)
    for i,(d,lo,hi) in enumerate(rows):
        for j,v in d.items():mat[i,j]=v
    res=milp(c, integrality=integer,bounds=Bounds(np.zeros(len(variables)),np.full(len(variables),np.inf)),constraints=LinearConstraint(mat.tocsr(),np.array([r[1] for r in rows]),np.array([r[2] for r in rows])),options={'time_limit':90,'mip_rel_gap':0.01})
    status={0:'OPTIMAL',1:'LIMIT',2:'INFEASIBLE',3:'UNBOUNDED',4:'ERROR'}.get(res.status,'UNKNOWN')
    base={'run_id':run['run_id'],'provenance':'Actual Prolog output loaded from TickTide execution_service_graphs.jsonl','status':status,'solver':'SciPy/HiGHS mixed-integer placement & path formulation; separate from preserved original Team3 solver','objective_units':'synthetic mixed per-block reference cost units, not monetary predictions','demand_assumptions':{'synthetic_work_units_per_vcpu':SCALE,'memory_MB_by_class':MEMORY,'dependency_bandwidth_Mbps':bw,'edge_policy':data_edge_policy,'concurrent_window':'one normalized planning interval; retries treated as aggregate load','no_measured_latency':True},'demands':demands,'data_edges':data_edges,'logical_edges':edges}
    if res.x is None:return base
    if status not in ('OPTIMAL','LIMIT'):return base
    placement={s:next(p for p in snames if res.x[ix[('x',s,p)]]>.5) for s in ordered}
    routing=[]
    for z in zs:
        if res.x[ix[z]]>.5:
            ei,p,q,pi,path=z[1:];routing.append({'source':data_edges[ei][0],'target':data_edges[ei][1],'from':p,'to':q,'path':[list(e) for e in path],'bandwidth_Mbps':bw})
    cpu_used=collections.Counter();ram_used=collections.Counter();bw_used=collections.Counter()
    for s,p in placement.items():cpu_used[p]+=demands[s]['cpu'];ram_used[p]+=demands[s]['memory']
    for r in routing:
        for u,v in r['path']:bw_used[(u,v)]+=bw
    violations=[]
    for p in snames:
        if cpu_used[p]>sites[p]['cpu']+1e-5 or ram_used[p]>sites[p]['memory']+1e-5:violations.append('capacity '+p)
    for e in links:
        if bw_used[e]>links[e]['capacity']+1e-5:violations.append('bandwidth '+str(e))
    if violations:raise AssertionError(violations)
    base.update({'placement':placement,'routing':routing,'objective':float(res.fun),'site_usage':{p:{'cpu':cpu_used[p],'memory_MB':ram_used[p]} for p in snames},'link_usage':{f'{a}->{b}':bw_used[(a,b)] for a,b in links},'validated_capacity':True,'gap':getattr(res,'mip_gap',None)})
    return base


def derive_demands(run, scenario, profiles):
    """Steady-state demand. Workload per run feeds average number of executed operations/request.
    rps * ops/request / throughput [ops/(s vCPU)] yields vCPU. No direct ops->cores shortcut.
    """
    rps=float(scenario['request_arrival_rate_rps']);speed=float(scenario['reference_cpu_capacity_ops_per_second_per_vcpu'])
    head=float(scenario['cpu_headroom_factor']); minimum=float(scenario['minimum_cpu_vcpu'])
    if not (rps>0 and speed>0 and head>=1 and minimum>=0):raise ValueError('Invalid CPU/rate calibration')
    mem_factor=float(scenario['memory_headroom_factor'])
    if mem_factor<=0:raise ValueError('Invalid memory factor')
    demands={}
    for sid,node in run['service_nodes'].items():
        operations=int(node['total_operations']);n=int(node['invocation_count']);per=int(node['operations_per_invocation'])
        if operations<0 or n<0 or per*n!=operations:raise ValueError('Inconsistent trace operation count: '+sid)
        clazz=profiles[sid]['workload_class']
        cpu=max(minimum,operations*rps/speed*head)
        mem=math.ceil(scenario['memory_MB_by_class'][clazz]*mem_factor)
        demands[sid]={'cpu':cpu,'memory':mem,'workload_ops':operations,'invocations':n,
                      'cpu_seconds_per_request':operations/speed,'cpu_seconds_per_second':operations*rps/speed}
    policy=scenario['data_edge_policy']
    if policy not in ('explicit_data_key','assume_all'):raise ValueError('Unknown policy')
    edge_bw={};dropped=[]
    for edge in run['sg_edges']:
        u,v=edge['source'],edge['target'];key=edge.get('data_key') or ''
        if u==v:continue
        if policy=='explicit_data_key' and not key:
            dropped.append((u,v));continue
        size_kB=float(scenario['message_size_kB_by_data_key'].get(key,scenario['default_message_size_kB']))
        if size_kB<0:raise ValueError('negative message size')
        # 1 decimal kB = 1000 bytes, so 8 kB * rps / 1000 = Mbps
        rate=8*size_kB*rps/1000*float(scenario['traffic_multiplier'])
        edge_bw[(u,v)]=edge_bw.get((u,v),0)+rate
    meta={'request_arrival_rate_rps':rps,'cpu_capacity_ops_per_second_per_vcpu':speed,
          'cpu_headroom_factor':head,'memory_headroom_factor':mem_factor,
          'planning_window_seconds':scenario['planning_window_seconds'],
          'data_edge_policy':policy,'excluded_logical_edges':dropped,
          'all_values_synthetic':True,'ram_not_derived_from_operations':True,
          'retry_aggregates_sequential_work':True,
          'unit_convention':'decimal kB, MB and Mbps'}
    return demands,edge_bw,meta

def run_model_calibrated(run, scenario):
    net,sites,links=setup_network()
    # Experiment-only overrides; original ng.json is unchanged.
    overrides=scenario.get('site_max_blocks_override',{})
    for site,blocks in overrides.items():
        if site not in sites or not (0 <= blocks <= sites[site]['cpu']/sites[site]['cpu_per_block']):
            raise ValueError('Invalid capacity override: '+site)
        sites[site]['cpu']=blocks*sites[site]['cpu_per_block']
        sites[site]['memory']=blocks*sites[site]['memory_per_block']
    with PROFILES.open() as f:profiles={p['task_id']:p for p in csv.DictReader(f)}
    nodes=run['service_nodes']; edges=run['sg_edges']; ordered=sorted(nodes)
    if not nodes:raise ValueError('empty executed graph')
    if sum(int(n['total_operations']) for n in nodes.values())!=int(run['total_operations']):
        raise ValueError('Service work sum differs from trace total')
    demands,edge_bandwidth,meta=derive_demands(run,scenario,profiles)
    data_edges=sorted(edge_bandwidth)
    if any(a not in nodes or b not in nodes for a,b in data_edges):raise ValueError('SG edge references unknown service')
    # Binary x_{service,site}; binary z_{dependency, origin_site, target_site, path}.
    # Use exact linear coupling: each selected site pair chooses exactly one path.
    snames=sorted(sites)
    xs=[('x',s,p) for s in ordered for p in snames]
    zs=[]
    for ei,(a,b) in enumerate(data_edges):
        for p in snames:
            for q in snames:
                for pi,path in enumerate(candidates(p,q,links)):
                    zs.append(('z',ei,p,q,pi,tuple(path)))
    variables=xs+zs
    ix={v:i for i,v in enumerate(variables)}
    c=np.zeros(len(variables))
    # Physical resource blocks cost max(cpu block, ram block) per site.
    # To linearize max, allocate integer b_site >= sum_cpu, sum_memory; and minimize cost.
    bs=[('block',p) for p in snames]
    # Link allocated blocks continuous upper bound integer, similarly.
    ls=[('link_block',a,b) for a,b in sorted(links)]
    variables+=bs+ls; ix={v:i for i,v in enumerate(variables)}
    c=np.zeros(len(variables));integer=np.ones(len(variables),dtype=int)
    for v in bs:c[ix[v]]=sites[v[1]]['cost_block']
    for v in ls:c[ix[v]]=links[v[1:]]['cost_block']
    rows=[]
    def constraint(coeff,low=-np.inf,high=np.inf):rows.append((coeff,low,high))
    for s in ordered:constraint({ix[('x',s,p)]:1 for p in snames},1,1)
    # An explicit service anchor models the location where a request enters.
    for service,site in scenario.get('pinned_services',{}).items():
        if service in ordered:
            if site not in snames:raise ValueError('Pin site not computable: '+site)
            constraint({ix[('x',service,site)]:1},1,1)
    # Per-dependency path propagation bound, NOT end-to-end latency.
    limit=scenario.get('max_data_path_delay_ms')
    delays=scenario.get('synthetic_link_delays_ms',{})
    if limit is not None:
        if limit<0:raise ValueError('negative delay budget')
        for z in zs:
            path=z[5]
            path_delay=sum(float(delays.get(f'{u}->{v}',links[(u,v)]['delay_ms'])) for u,v in path)
            if path_delay>limit+1e-9:constraint({ix[z]:1},0,0)
    for ei,(a,b) in enumerate(data_edges):
        # exact origin assignment marginal and destination marginal
        for p in snames:
            zlist=[ix[z] for z in zs if z[1]==ei and z[2]==p]
            d={j:1 for j in zlist};d[ix[('x',a,p)]]=-1;constraint(d,0,0)
        for q in snames:
            zlist=[ix[z] for z in zs if z[1]==ei and z[3]==q]
            d={j:1 for j in zlist};d[ix[('x',b,q)]]=-1;constraint(d,0,0)
    for p in snames:
        site=sites[p]
        for resource in ('cpu','memory'):
            coeff={ix[('x',s,p)]:demands[s][resource]/site[resource+'_per_block'] for s in ordered}
            coeff[ix[('block',p)]]=-1
            constraint(coeff,high=0)
        constraint({ix[('block',p)]:1},high=min(site['cpu']/site['cpu_per_block'],site['memory']/site['memory_per_block']))
    for (a,b),info in links.items():
        coeff={ix[z]:edge_bandwidth[data_edges[z[1]]]/info['per_block'] for z in zs if (a,b) in z[5]}
        coeff[ix[('link_block',a,b)]]=-1
        constraint(coeff,high=0)
        constraint({ix[('link_block',a,b)]:1},high=info['capacity']/info['per_block'])
    mat=lil_matrix((len(rows),len(variables)),dtype=float)
    for i,(d,lo,hi) in enumerate(rows):
        for j,v in d.items():mat[i,j]=v
    res=milp(c, integrality=integer,bounds=Bounds(np.zeros(len(variables)),np.full(len(variables),np.inf)),constraints=LinearConstraint(mat.tocsr(),np.array([r[1] for r in rows]),np.array([r[2] for r in rows])),options={'time_limit':float(scenario.get('solver_time_limit_seconds',90)),'mip_rel_gap':float(scenario.get('solver_relative_gap',0.01))})
    status={0:'OPTIMAL',1:'LIMIT',2:'INFEASIBLE',3:'UNBOUNDED',4:'ERROR'}.get(res.status,'UNKNOWN')
    base={'run_id':run['run_id'],'provenance':'Original TickTide Prolog SG JSONL (never synthesized by solver)',
          'status':status,'solver':'SciPy HiGHS independent MILP; NOT the professor PuLP solver',
          'objective_units':'mixed reference block cost units (not real currency)',
          'demand_assumptions':meta,'demands':demands,
          'data_edges':[{'source':u,'target':v,'bandwidth_Mbps':rate} for (u,v),rate in edge_bandwidth.items()],
          'logical_edges':edges,'scenario':scenario,'latency_scope':'per data-dependency path propagation only; NOT end-to-end', 'network_capacity_overrides':overrides}

    if res.x is None:return base
    if status != 'OPTIMAL':return base  # no certified-optimal placement on time limit
    placement={s:next(p for p in snames if res.x[ix[('x',s,p)]]>.5) for s in ordered}
    routing=[]
    for z in zs:
        if res.x[ix[z]]>.5:
            ei,p,q,pi,path=z[1:];routing.append({'source':data_edges[ei][0],'target':data_edges[ei][1],'from':p,'to':q,'path':[list(e) for e in path],'bandwidth_Mbps':edge_bandwidth[data_edges[ei]]})
    cpu_used=collections.Counter();ram_used=collections.Counter();bw_used=collections.Counter()
    for s,p in placement.items():cpu_used[p]+=demands[s]['cpu'];ram_used[p]+=demands[s]['memory']
    for r in routing:
        for u,v in r['path']:bw_used[(u,v)]+=r['bandwidth_Mbps']
    violations=[]
    for p in snames:
        if cpu_used[p]>sites[p]['cpu']+1e-5 or ram_used[p]>sites[p]['memory']+1e-5:violations.append('capacity '+p)
    for e in links:
        if bw_used[e]>links[e]['capacity']+1e-5:violations.append('bandwidth '+str(e))
    if violations:raise AssertionError(violations)
    base.update({'placement':placement,'routing':routing,'objective':float(res.fun),'site_usage':{p:{'cpu':cpu_used[p],'memory_MB':ram_used[p]} for p in snames},'link_usage':{f'{a}->{b}':bw_used[(a,b)] for a,b in links},'validated_capacity':True,'gap':getattr(res,'mip_gap',None),'routed_dependency_count':sum(bool(x['path']) for x in routing),'max_routed_path_delay_ms':max([sum(float(scenario.get('synthetic_link_delays_ms',{}).get(f'{u}->{v}',links[(u,v)]['delay_ms'])) for u,v in r['path']) for r in routing] or [0]),'solver_site_blocks':{p:float(res.x[ix[('block',p)]]) for p in snames},'solver_link_blocks':{f'{a}->{b}':float(res.x[ix[('link_block',a,b)]]) for a,b in links},'solver_relative_gap_requested':float(scenario.get('solver_relative_gap',0.01)),'solver_time_limit_requested_seconds':float(scenario.get('solver_time_limit_seconds',90))})
    return base

def to_cypher(run,result,net):
    lines=['// Import into Neo4j Browser using :source or copy/paste; generated only after run validation.','CREATE CONSTRAINT physical_id IF NOT EXISTS FOR (n:PhysicalNode) REQUIRE n.id IS UNIQUE;','CREATE CONSTRAINT service_key IF NOT EXISTS FOR (n:TickTideService) REQUIRE (n.run_id,n.id) IS UNIQUE;']
    for n in net['nodes']:
        lines.append(f'MERGE (n:PhysicalNode {{id:{cyq(n["id"])}}}) SET n.label={cyq(n["label"])},n.layer={cyq(n["type"])};')
        for cap in n['capabilities']:
            vals={r['type']:r['capacity']['value'] for r in cap['resources']}
            lines.append(f'MATCH (n:PhysicalNode {{id:{cyq(n["id"])}}}) SET n.{cap["type"]}_max_blocks={int(cap["max_blocks"])};')
    for e in net['links']:
        if e['type']!='wireline':continue
        lines.append(f'MATCH (a:PhysicalNode {{id:{cyq(e["origin"])}}}),(b:PhysicalNode {{id:{cyq(e["target"])}}}) MERGE (a)-[r:PHYSICAL_LINK]->(b) SET r.capacity_Mbps={float(next(x for x in e["resources"] if x["type"]=="bandwidth")["capacity"]["value"])*float(e["max_blocks"])},r.delay_ms={float(e["propagation_delay"]["value"])};')
    rid=int(run['run_id'])
    for s,n in run['service_nodes'].items():
        d=result['demands'][s]
        lines.append(f'MERGE (s:TickTideService {{run_id:{rid},id:{cyq(s)}}}) SET s.name={cyq(n["name"])},s.operations={int(n["total_operations"])},s.invocations={int(n["invocation_count"])},s.cpu_synthetic={d["cpu"]},s.memory_synthetic_MB={d["memory"]};')
    for e in run['sg_edges']:
        lines.append(f'MATCH (a:TickTideService {{run_id:{rid},id:{cyq(e["source"])}}}),(b:TickTideService {{run_id:{rid},id:{cyq(e["target"])}}}) MERGE (a)-[r:DEPENDS_ON {{reason:{cyq(e.get("reason",""))},data_key:{cyq(e.get("data_key",""))}}}]->(b);')
    if 'placement' in result:
        for s,p in result['placement'].items():
            lines.append(f'MATCH (s:TickTideService {{run_id:{rid},id:{cyq(s)}}}),(p:PhysicalNode {{id:{cyq(p)}}}) MERGE (s)-[:DEPLOYED_ON]->(p);')
        for index,r in enumerate(result['routing']):
            for seq,(a,b) in enumerate(r['path']):
                lines.append(f'MATCH (a:PhysicalNode {{id:{cyq(a)}}})-[e:PHYSICAL_LINK]->(b:PhysicalNode {{id:{cyq(b)}}}) SET e.used_in_run_{rid}=true;')
    if 'routing' in result:
        for route_index,route in enumerate(result['routing']):
            eid=f"{rid}:{route_index}:{route['source']}:{route['target']}"
            lines.append(f'MERGE (r:NetworkRoute {{id:{cyq(eid)}}}) SET r.run_id={rid},r.source_service={cyq(route["source"])},r.target_service={cyq(route["target"])},r.bandwidth_Mbps={float(route["bandwidth_Mbps"])};')
            for hop_index,(u,v) in enumerate(route['path']):
                lines.append(f'MATCH (r:NetworkRoute {{id:{cyq(eid)}}}),(a:PhysicalNode {{id:{cyq(u)}}}),(b:PhysicalNode {{id:{cyq(v)}}}) MERGE (r)-[h:USES_HOP {{hop:{hop_index}}}]->(a) SET h.to_node={cyq(v)};')
    return '\n'.join(lines)+'\n' 

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--jsonl',required=True);ap.add_argument('--run-id',type=int,default=1);ap.add_argument('--output',default=str(ROOT/'results'));ap.add_argument('--edge-policy',choices=['assume_all','explicit_data_key'],default='explicit_data_key');ap.add_argument('--bandwidth',type=float,default=BANDWIDTH);a=ap.parse_args()
    if a.bandwidth<0:ap.error('bandwidth must be non-negative')
    out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=True)
    run=next((x for x in record(a.jsonl) if x['run_id']==a.run_id),None)
    if run is None:raise ValueError('Real Prolog run not found: do not fabricate.')
    res=run_model(run,a.edge_policy,a.bandwidth);net,_,_=setup_network()
    write_json(out/'placement_result.json',res)
    (out/'neo4j_import.cypher').write_text(to_cypher(run,res,net))
    print('Status:',res['status'],'Placement:',res.get('placement'),'Result:',out)
if __name__=='__main__':main()

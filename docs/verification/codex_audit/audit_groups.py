# 출처: Codex 2차 검토, bd93f79, 2026-11-02 (원본: /tmp/shopgraph_bd93f79_audit_f02im8mm/audit_groups.py, 아래 내용은 고치지 않음)
from pathlib import Path
import json
import graph, old_graph
from tests.fixtures import customers,products,purchases
from tests.helpers import snapshot

def outcome(g,cid):
    try:return ('return',g.group_of(cid))
    except Exception as exc:return ('raise',type(exc).__name__,str(exc))
old=old_graph.ShopGraph(customers(),products(),purchases());new=graph.ShopGraph(customers(),products(),purchases())
normal=0
for cid in old.customer_ids():
    assert outcome(old,cid)==outcome(new,cid);normal+=1
cases=0;different=[]
for cid in old.customer_ids():
    old_products={x for x in old._adj[cid] if x not in graph.GROUP_IDS}
    for mask in range(1<<len(graph.GROUP_IDS)):
        selected={gid for i,gid in enumerate(graph.GROUP_IDS) if mask & (1<<i)}
        old._adj[cid]=old_products|selected;new._adj[cid]=old_products|selected
        before=snapshot(new)
        a,b=outcome(old,cid),outcome(new,cid)
        if a!=b:different.append((cid,mask,a,b))
        assert snapshot(new)==before
        cases+=1
assert not different,different
class CountingSet(set):
    def __init__(self,items):super().__init__(items);self.contains_calls=0;self.iter_calls=0
    def __contains__(self,value):self.contains_calls+=1;return super().__contains__(value)
    def __iter__(self):self.iter_calls+=1;return super().__iter__()
counts=[]
for n in range(6):
    neighbors=CountingSet(['G-F-20']+new.product_ids()[:n])
    new._adj['C01']=neighbors
    assert new.group_of('C01')=='G-F-20'
    counts.append((len(neighbors),neighbors.contains_calls,neighbors.iter_calls))
assert all(contains==8 and iterations==0 for _,contains,iterations in counts)
print('normal customers:',normal,'adjacency group subsets:',cases,'differences:',len(different))
print('(neighbor count, membership checks, full iterations):',counts)
Path('group_results.json').write_text(json.dumps({'normal':normal,'group_subsets':cases,'differences':different,'operation_counts':counts},indent=2))

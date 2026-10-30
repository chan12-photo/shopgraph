"""계획서 5.5·부록 B 계약 전체를 구현한 검증용 시험 구현 (저장소에 넣지 않음)."""
import re, datetime, copy
KINDS=("상의","하의","아우터"); STYLES=("캐주얼","미니멀","스트릿","포멀"); CAP=3
GROUPS=[f"G-{g}-{b}" for g in "FM" for b in ("10","20","30","40+")]
def _int(x,lo,hi,msg):
    if isinstance(x,bool) or not isinstance(x,int) or not lo<=x<=hi: raise ValueError(msg)
def _name(n,mx,msg):
    if not isinstance(n,str) or not 1<=len(n.strip())<=mx: raise ValueError(msg)
    return n.strip()
def _date(s):
    if not isinstance(s,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",s): raise ValueError("날짜 형식")
    try: datetime.date.fromisoformat(s)
    except ValueError: raise ValueError("없는 날짜")
def _stock(st):
    if not isinstance(st,dict) or not st: raise ValueError("색상 1개 이상")
    out={}
    for c,v in st.items():
        c=_name(c,10,"색상명")
        if c in out: raise ValueError("중복 색상")
        _int(v,0,10**9,"재고"); out[c]=v
    return out
def band(a): return "10" if a<20 else "20" if a<30 else "30" if a<40 else "40+"
class ShopGraph:
    def __init__(s,customers=None,products=None,purchases=None):
        s._groups={g:{"id":g,"gender":"여" if g[2]=="F" else "남","band":g[4:]+"대" if g[4:]!="40+" else "40대 이상"} for g in GROUPS}
        s._customers={};s._products={};s._purchases={}
        for kind,lst,pre,w in (("고객",customers,"C",2),("상품",products,"P",2),("구매",purchases,"T",3)):
            for r in lst or []:
                if not isinstance(r.get("id"),str) or not re.fullmatch(pre+r"\d{%d}"%w,r["id"]) or int(r["id"][1:])==0: raise ValueError(f"{kind} ID 형식")
        for c in customers or []:
            if c["id"] in s._customers: raise ValueError("중복 ID")
            s._customers[c["id"]]={"id":c["id"],"name":_name(c["name"],20,"이름"),"gender":s._gender(c["gender"]),"age":c["age"]}; _int(c["age"],10,99,"나이")
        for p in products or []:
            if p["id"] in s._products: raise ValueError("중복 ID")
            s._check_prod(p["kind"],p["style"],p["price"])
            s._products[p["id"]]={"id":p["id"],"name":_name(p["name"],20,"상품명"),"kind":p["kind"],"style":p["style"],"price":p["price"],"stock":_stock(p["stock"])}
        for t in purchases or []:
            if t["id"] in s._purchases: raise ValueError("중복 ID")
            s._check_pur(t["customer_id"],t["product_id"],t["color"],t["qty"],t["date"])
            s._purchases[t["id"]]=dict(t)
        mx=lambda d:max([int(x[1:]) for x in d]+[0])+1
        s._next_ids={"C":mx(s._customers),"P":mx(s._products),"T":mx(s._purchases)}
        s.rebuild()
    # ---- 검증 도우미
    def _gender(s,g):
        if g not in("남","여"): raise ValueError("성별")
        return g
    def _check_prod(s,kind,style,price):
        if kind not in KINDS or style not in STYLES: raise ValueError("종류/스타일")
        _int(price,0,10**9,"가격")
    def _check_pur(s,cid,pid,color,qty,date):
        s._need(s._customers,cid); s._need(s._products,pid)
        if color not in s._products[pid]["stock"]: raise ValueError("색상")
        _int(qty,1,99,"수량"); _date(date)
    def _need(s,d,i):
        if i not in d: raise ValueError("존재하지 않는 ID")
    def _issue(s,k,w):
        n=s._next_ids[k]
        if n>=10**w: raise ValueError("ID 한도 초과")
        s._next_ids[k]+=1; return f"{k}{n:0{w}d}"
    def _gid(s,c): return f"G-{'F' if c['gender']=='여' else 'M'}-{band(c['age'])}"
    # ---- 그래프 구축 (ID 카운터는 건드리지 않음)
    def _build(s):
        adj={g:set() for g in GROUPS}; edges={}
        for c in s._customers: adj[c]=set()
        for p in s._products: adj[p]=set()
        for cid,c in s._customers.items(): g=s._gid(c); adj[g].add(cid); adj[cid].add(g)
        for t in s._purchases.values():
            k=(t["customer_id"],t["product_id"])
            e=edges.setdefault(k,{"colors":set(),"count":0,"total_qty":0,"last_date":""})
            e["colors"].add(t["color"]);e["count"]+=1;e["total_qty"]+=t["qty"];e["last_date"]=max(e["last_date"],t["date"])
            adj[k[0]].add(k[1]);adj[k[1]].add(k[0])
        return adj,edges
    def rebuild(s): s._adj,s._edges=s._build()
    # ---- 조회 (복사본)
    def get_customer(s,i): s._need(s._customers,i); return dict(s._customers[i])
    def get_product(s,i): s._need(s._products,i); p=s._products[i]; return {**p,"stock":dict(p["stock"])}
    def get_purchase(s,i): s._need(s._purchases,i); return dict(s._purchases[i])
    def customer_ids(s): return sorted(s._customers)
    def product_ids(s): return sorted(s._products)
    def _byname(s,d,n):
        n=_name(n,10**6,"이름"); return sorted(i for i,x in d.items() if x["name"]==n)
    def find_customers_by_name(s,n): return s._byname(s._customers,n)
    def find_products_by_name(s,n): return s._byname(s._products,n)
    def neighbors(s,n):
        if n not in s._adj: raise ValueError("노드")
        return sorted(s._adj[n])
    def edge(s,c,p):
        s._need(s._customers,c); s._need(s._products,p)
        e=s._edges.get((c,p)); return None if e is None else {**e,"colors":sorted(e["colors"])}
    def weight(s,c,p):
        e=s.edge(c,p); return 0 if e is None else len(e["colors"])
    def group_of(s,c): s._need(s._customers,c); return s._gid(s._customers[c])
    def members(s,g):
        if g not in GROUPS: raise ValueError("그룹")
        return sorted(s._adj[g])
    def is_sold_out(s,p): s._need(s._products,p); return all(v==0 for v in s._products[p]["stock"].values())
    def available_colors(s,p): s._need(s._products,p); return sorted(k for k,v in s._products[p]["stock"].items() if v>0)
    def stats(s): return {"groups":len(GROUPS),"customers":len(s._customers),"products":len(s._products),"membership_edges":sum(len(s._adj[g]) for g in GROUPS),"purchase_edges":len(s._edges),"purchases":len(s._purchases)}
    # ---- 변경 (검증 전부 → 변경)
    def add_customer(s,name,gender,age):
        name=_name(name,20,"이름"); s._gender(gender); _int(age,10,99,"나이")
        cid=s._issue("C",2); s._customers[cid]={"id":cid,"name":name,"gender":gender,"age":age}; s.rebuild(); return cid
    def update_customer(s,cid,name=None,gender=None,age=None):
        s._need(s._customers,cid)
        if name is None and gender is None and age is None: raise ValueError("바꿀 항목이 없습니다")
        new=dict(s._customers[cid])
        if name is not None: new["name"]=_name(name,20,"이름")
        if gender is not None: new["gender"]=s._gender(gender)
        if age is not None: _int(age,10,99,"나이"); new["age"]=age
        s._customers[cid]=new; s.rebuild()
    def delete_customer(s,cid):
        s._need(s._customers,cid); ts=[t for t,v in s._purchases.items() if v["customer_id"]==cid]
        for t in ts: del s._purchases[t]
        del s._customers[cid]; s.rebuild(); return len(ts)
    def add_product(s,name,kind,style,price,stock):
        name=_name(name,20,"상품명"); s._check_prod(kind,style,price); st=_stock(stock)
        pid=s._issue("P",2); s._products[pid]={"id":pid,"name":name,"kind":kind,"style":style,"price":price,"stock":st}; s.rebuild(); return pid
    def update_product(s,pid,name=None,kind=None,style=None,price=None,stock=None):
        s._need(s._products,pid)
        if all(x is None for x in (name,kind,style,price,stock)): raise ValueError("바꿀 항목이 없습니다")
        new={**s._products[pid],"stock":dict(s._products[pid]["stock"])}
        if name is not None: new["name"]=_name(name,20,"상품명")
        if kind is not None: new["kind"]=kind
        if style is not None: new["style"]=style
        if price is not None: new["price"]=price
        s._check_prod(new["kind"],new["style"],new["price"])
        if stock is not None:
            st=_stock(stock); used={t["color"] for t in s._purchases.values() if t["product_id"]==pid}
            if not used<=set(st): raise ValueError("구매 기록이 있는 색상은 삭제 불가")
            new["stock"]=st
        s._products[pid]=new; s.rebuild()
    def delete_product(s,pid):
        s._need(s._products,pid); ts=[t for t,v in s._purchases.items() if v["product_id"]==pid]
        for t in ts: del s._purchases[t]
        del s._products[pid]; s.rebuild(); return len(ts)
    def add_purchase(s,cid,pid,color,qty,date):
        s._check_pur(cid,pid,color,qty,date)
        tid=s._issue("T",3); s._purchases[tid]={"id":tid,"customer_id":cid,"product_id":pid,"color":color,"qty":qty,"date":date}; s.rebuild(); return tid
    def update_purchase(s,tid,color=None,qty=None):
        s._need(s._purchases,tid)
        if color is None and qty is None: raise ValueError("바꿀 항목이 없습니다")
        new=dict(s._purchases[tid])
        if color is not None:
            if color not in s._products[new["product_id"]]["stock"]: raise ValueError("색상")
            new["color"]=color
        if qty is not None: _int(qty,1,99,"수량"); new["qty"]=qty
        s._purchases[tid]=new; s.rebuild()
    def delete_purchase(s,tid): s._need(s._purchases,tid); del s._purchases[tid]; s.rebuild()
    # ---- 무결성 (상태를 바꾸지 않음: 임시 구축 결과와 비교)
    def check_integrity(s):
        v=[]
        for (c,p) in s._edges:
            if p not in s._adj.get(c,()) or c not in s._adj.get(p,()): v.append(f"역방향 누락 {c}-{p}")
        for t in s._purchases.values():
            if t["customer_id"] not in s._customers or t["product_id"] not in s._products: v.append(f"없는 참조 {t['id']}")
            elif t["color"] not in s._products[t["product_id"]]["stock"]: v.append(f"색상 불일치 {t['id']}")
        for cid,c in s._customers.items():
            gs=[g for g in s._adj.get(cid,()) if g in GROUPS]
            if gs!=[s._gid(c)] or cid not in s._adj[s._gid(c)]: v.append(f"그룹 불일치 {cid}")
        adj,edges=s._build()
        if edges!=s._edges: v.append("집계가 원본 재구축 결과와 다름")
        if adj!=s._adj: v.append("인접 리스트가 원본 재구축 결과와 다름")
        return v
# ---------------- search.py
def find_products(g,kind=None,style=None,color=None,price_min=None,price_max=None):
    if kind is not None and kind not in KINDS: raise ValueError("종류")
    if style is not None and style not in STYLES: raise ValueError("스타일")
    for x in (price_min,price_max):
        if x is not None: _int(x,0,10**9,"가격")
    if price_min is not None and price_max is not None and price_min>price_max: raise ValueError("가격 범위")
    r=[]
    for pid in g.product_ids():
        p=g.get_product(pid)
        if kind and p["kind"]!=kind: continue
        if style and p["style"]!=style: continue
        if color and color not in p["stock"]: continue
        if price_min is not None and p["price"]<price_min: continue
        if price_max is not None and p["price"]>price_max: continue
        r.append(pid)
    return r
def products_of(g,cid):
    out=[]
    for p in g.neighbors(cid):
        if p.startswith("P"):
            e=g.edge(cid,p); out.append({"product_id":p,"name":g.get_product(p)["name"],"colors":e["colors"],"weight":len(e["colors"]),"count":e["count"],"total_qty":e["total_qty"],"last_date":e["last_date"]})
    return out
def customers_of(g,pid):
    out=[]
    for c in g.neighbors(pid):
        out.append({"customer_id":c,"name":g.get_customer(c)["name"],"group_id":g.group_of(c),"colors":g.edge(c,pid)["colors"]})
    return out
def members_of(g,gid): return g.members(gid)
def _score(g,peers):
    sc={};sup={}
    for c in peers:
        for p in g.neighbors(c):
            if p.startswith("P"): sc[p]=sc.get(p,0)+min(g.weight(c,p),CAP); sup.setdefault(p,[]).append(c)
    return sc,sup
def group_popular(g,gid,k=None):
    if k is not None: _int(k,1,10,"K")
    sc,sup=_score(g,g.members(gid))
    r=[{"product_id":p,"score":sc[p],"buyers":len(sup[p]),"sold_out":g.is_sold_out(p)} for p in sorted(sc,key=lambda p:(-sc[p],-len(sup[p]),p))]
    return r if k is None else r[:k]
def recommend(g,cid,k=3):
    _int(k,1,10,"K"); gid=g.group_of(cid); gender=gid[2]
    bought={p for p in g.neighbors(cid) if p.startswith("P")}
    scopes=[("group",[gid]),("gender",[x for x in GROUPS if x[2]==gender]),("all",GROUPS)]
    sel=[]
    for name,gs in scopes:
        peers=sorted({m for x in gs for m in g.members(x)}-{cid})
        sc,sup=_score(g,peers); chosen={r["product_id"] for r in sel}
        for p in sorted((p for p in sc if p not in bought and not g.is_sold_out(p) and p not in chosen),key=lambda p:(-sc[p],-len(sup[p]),p)):
            if len(sel)<k: sel.append({"product_id":p,"score":sc[p],"buyers":len(sup[p]),"scope":name,"supporters":sup[p],"available_colors":g.available_colors(p)})
        if len(sel)==k: break
    return sel

"""오류 주입 확인: 일부러 틀린 구현으로 바꿨을 때 test_spec의 어떤 테스트가 실패하는지 본다."""
import unittest, shop, test_spec
def run(label):
    suite=unittest.defaultTestLoader.loadTestsFromModule(test_spec)
    r=unittest.TextTestRunner(verbosity=0,stream=open("/dev/null","w")).run(suite)
    print(f"{label}: 실패 {[t[0].id().split('.',1)[1] for t in r.failures+r.errors]}")
# 1. 같은 성별 범위에서 동료가 있는 첫 연령대 그룹만 사용
orig_rec=shop.recommend
def wrong_rec(g,cid,k=3):
    shop._int(k,1,10,"K"); gid=g.group_of(cid); gender=gid[2]
    bought={p for p in g.neighbors(cid) if p.startswith("P")}
    first=[x for x in shop.GROUPS if x[2]==gender and set(g.members(x))-{cid}][:1]
    sel=[]
    for name,gs in [("group",[gid]),("gender",first),("all",shop.GROUPS)]:
        peers=sorted({m for x in gs for m in g.members(x)}-{cid}); sc,sup=shop._score(g,peers); chosen={r["product_id"] for r in sel}
        for p in sorted((p for p in sc if p not in bought and not g.is_sold_out(p) and p not in chosen),key=lambda p:(-sc[p],-len(sup[p]),p)):
            if len(sel)<k: sel.append({"product_id":p,"score":sc[p],"buyers":len(sup[p]),"scope":name,"supporters":sup[p],"available_colors":g.available_colors(p)})
        if len(sel)==k: break
    return sel
test_spec.recommend=wrong_rec; run("오류1 같은 성별 범위 합산 누락"); test_spec.recommend=orig_rec
# 2. 무결성 검사가 검사 중 ID 카운터를 바꿈
orig_ci=shop.ShopGraph.check_integrity
def wrong_ci(s): s._next_ids["C"]+=1; return orig_ci(s)
shop.ShopGraph.check_integrity=wrong_ci; run("오류2 검사 중 ID 카운터 변경"); shop.ShopGraph.check_integrity=orig_ci
# 3. 고객 수정에서 이름을 먼저 바꾼 뒤 나이를 검증
orig_uc=shop.ShopGraph.update_customer
def wrong_uc(s,cid,name=None,gender=None,age=None):
    if name is not None and cid in s._customers: s._customers[cid]["name"]=name
    return orig_uc(s,cid,None if name is not None and age is None and gender is None else name,gender,age) if (gender or age is not None) else orig_uc(s,cid,name,gender,age)
shop.ShopGraph.update_customer=wrong_uc; run("오류3 수정 중 부분 변경"); shop.ShopGraph.update_customer=orig_uc
run("정상 구현")

"""계획서 6장 기대값 전체 (검증용, 계획서 4차 재검토 기준)."""
import unittest, copy
from shop import *
from fixtures import poc_data as data, make_poc as make
from helpers import snapshot as snap
full=lambda r:[(x["product_id"],x["scope"],x["score"],x["buyers"],x["supporters"]) for x in r]
class W3(unittest.TestCase):
    def test_counts(s):
        g=make(); st=g.stats(); s.assertEqual((st["groups"]+st["customers"]+st["products"],st["membership_edges"],st["purchase_edges"],st["purchases"]),(19,6,9,13))
    def test_edges(s):
        g=make(); s.assertEqual(g.edge("C01","P01"),{"colors":["그레이","네이비","블랙","화이트"],"count":4,"total_qty":4,"last_date":"2026-10-01"})
        e=g.edge("C02","P02"); s.assertEqual((e["count"],e["total_qty"],e["last_date"]),(2,2,"2026-09-20"))
        s.assertEqual(g.edge("C05","P01"),None); s.assertEqual(g.weight("C05","P01"),0)
        for a in [("C99","P01"),("C01","P99")]:
            with s.assertRaises(ValueError): g.edge(*a)
            with s.assertRaises(ValueError): g.weight(*a)
    def test_names(s):
        g=make(); s.assertEqual(g.find_customers_by_name(" 고객1 "),["C01"]); s.assertEqual(g.find_customers_by_name("고객"),[])
    def test_copies(s):
        g=make(); x=g.get_customer("C01"); x["age"]=50; s.assertEqual(g.get_customer("C01")["age"],23); s.assertEqual(g.group_of("C01"),"G-F-20")
        e=g.edge("C01","P01"); e["colors"].append("레드"); s.assertEqual(g.edge("C01","P01")["colors"],["그레이","네이비","블랙","화이트"])
        p=g.get_product("P01"); p["stock"]["블랙"]=0; s.assertEqual(g.get_product("P01")["stock"]["블랙"],5)
    def test_input_not_shared(s):
        cs,ps,ts=data(); g=ShopGraph(cs,ps,ts); ps[0]["stock"]["블랙"]=0; cs[0]["age"]=50
        s.assertEqual(g.get_product("P01")["stock"]["블랙"],5); s.assertEqual(g.get_customer("C01")["age"],23)
    def test_ctor_invalid(s):
        cs,ps,ts=data(); cs[0]["id"]="C1"
        with s.assertRaises(ValueError): ShopGraph(cs,ps,ts)
        cs,ps,ts=data(); ts[0]["date"]="20260901"
        with s.assertRaises(ValueError): ShopGraph(cs,ps,ts)
        cs,ps,ts=data(); cs.append(dict(cs[0]))
        with s.assertRaises(ValueError): ShopGraph(cs,ps,ts)
        cs,ps,ts=data(); ts[0]["customer_id"]="C99"
        with s.assertRaises(ValueError): ShopGraph(cs,ps,ts)
class W4(unittest.TestCase):
    def test_ids(s):
        g=make(); s.assertEqual(g.add_customer("새","여",22),"C07"); g.delete_customer("C07"); g.rebuild(); s.assertEqual(g.add_customer("또","여",22),"C08")
    def test_failed_add_keeps_counter(s):
        g=make()
        with s.assertRaises(ValueError): g.add_customer("새","여",True)
        s.assertEqual(g.add_customer("새","여",22),"C07")
    def test_move(s):
        g=make(); g.update_customer("C04",age=34); s.assertEqual(g.group_of("C04"),"G-M-30"); s.assertEqual(g.members("G-M-20"),[])
    def test_delete_customer(s):
        g=make(); s.assertEqual(g.delete_customer("C02"),3); st=g.stats()
        s.assertEqual((st["purchases"],st["purchase_edges"],st["groups"]+st["customers"]+st["products"]),(10,7,18)); s.assertEqual(g.members("G-F-20"),["C01","C03"])
    def test_delete_product(s):
        g=make(); s.assertEqual(g.delete_product("P01"),5); st=g.stats(); s.assertEqual((st["purchases"],st["purchase_edges"]),(8,7))
    def test_stock(s):
        g=make(); g.update_product("P04",stock={"카키":4,"블랙":4,"그레이":1}); s.assertIn("그레이",g.available_colors("P04"))
        b=snap(g)
        with s.assertRaises(ValueError): g.update_product("P01",stock={"블랙":5})
        with s.assertRaises(ValueError): g.update_product("P04",stock={"카키":1," 카키 ":2})
        s.assertEqual(snap(g),b)
        st={"블랙":5}; pid=g.add_product("새 상품","상의","캐주얼",1000,st); st["블랙"]=0; s.assertEqual(g.get_product(pid)["stock"]["블랙"],5)
        st2={"카키":4,"블랙":4}; g.update_product("P04",stock=st2); st2["카키"]=0; s.assertEqual(g.get_product("P04")["stock"]["카키"],4)
    def test_mixed_invalid(s):
        g=make(); b=snap(g); st=g.stats()
        for f in [lambda:g.update_customer("C01",name="변경됨",age=True),lambda:g.update_customer("C01"),lambda:g.update_product("P01",name="변경됨",price=-1)]:
            with s.assertRaises(ValueError): f()
        s.assertEqual(snap(g),b); s.assertEqual(g.stats(),st)
    def test_same_name(s):
        g=make(); s.assertEqual(g.add_customer("고객1","남",30),"C07"); s.assertEqual(g.find_customers_by_name("고객1"),["C01","C07"])
    def test_gender_move(s):
        g=make(); g.update_customer("C01",gender="남"); s.assertEqual(g.group_of("C01"),"G-M-20")
        s.assertEqual(g.members("G-F-20"),["C02","C03"]); s.assertEqual(g.members("G-M-20"),["C01","C04"])
    def test_id_limit(s):
        cs,ps,ts=data(); cs.append({"id":"C99","name":"끝","gender":"여","age":20}); g=ShopGraph(cs,ps,ts); b=snap(g)
        with s.assertRaises(ValueError): g.add_customer("새","여",22)
        s.assertEqual(snap(g),b)
class W5(unittest.TestCase):
    def test_changes(s):
        g=make(); g.delete_purchase("T004"); e=g.edge("C01","P01"); s.assertEqual((len(e["colors"]),e["count"],e["last_date"]),(3,3,"2026-09-15"))
        g=make(); s.assertEqual(g.add_purchase("C02","P02","블랙",1,"2026-10-05"),"T014"); e=g.edge("C02","P02"); s.assertEqual((len(e["colors"]),e["count"],e["total_qty"],e["last_date"]),(2,3,3,"2026-10-05"))
        g=make(); g.update_purchase("T005",qty=3); e=g.edge("C01","P02"); s.assertEqual((e["total_qty"],e["count"],len(e["colors"])),(3,1,1))
        g=make(); g.delete_purchase("T005"); s.assertIsNone(g.edge("C01","P02")); st=g.stats(); s.assertEqual((st["purchases"],st["purchase_edges"]),(12,8))
        g=make(); g.update_purchase("T002",color="블랙"); e=g.edge("C01","P01"); s.assertEqual((len(e["colors"]),e["count"],e["total_qty"],e["last_date"]),(3,4,4,"2026-10-01"))
        s.assertEqual(g.check_integrity(),[])
    def test_invalid(s):
        g=make(); b=snap(g)
        bad=[("C99","P01","블랙",1,"2026-10-01"),("C01","P03","레드",1,"2026-10-01"),("C01","P01","블랙",0,"2026-10-01")]+[("C01","P01","블랙",1,d) for d in ["20261023","2026-W43-5","2026-02-30","2026-1-5"]]
        for a in bad:
            with s.assertRaises(ValueError): g.add_purchase(*a)
        s.assertEqual(snap(g),b); s.assertEqual(g.add_purchase("C01","P01","블랙",1,"2026-10-05"),"T014"); s.assertEqual(g.check_integrity(),[])
    def test_faults(s):
        def f1(g): g._adj["P01"].discard("C01")
        def f2(g): g._edges[("C01","P01")]["colors"].discard("블랙")
        def f3(g): g._adj["C01"].discard("G-F-20"); g._adj["C01"].add("G-F-30"); g._adj["G-F-30"].add("C01")
        def f4(g): g._edges[("C05","P01")]={"colors":{"블랙"},"count":1,"total_qty":1,"last_date":"2026-09-01"}; g._adj["C05"].add("P01"); g._adj["P01"].add("C05")
        for f in (f1,f2,f3,f4):
            g=make(); f(g); before=snap(g)
            s.assertTrue(g.check_integrity()); s.assertTrue(g.check_integrity())  # 두 번 불러도 위반이 남아 있음 = 복구하지 않음
            s.assertEqual(snap(g),before)
class W6W7(unittest.TestCase):
    def test_query(s):
        g=make(); s.assertEqual(find_products(g,color="네이비"),["P01","P03"]); s.assertEqual(find_products(g,kind="상의"),["P01","P03"])
        s.assertEqual(find_products(g,price_min=30000,price_max=50000),["P02","P03","P04"])
        with s.assertRaises(ValueError): find_products(g,price_min=50000,price_max=30000)
        s.assertEqual([(x["product_id"],x["weight"],x["count"],x["total_qty"],x["last_date"]) for x in products_of(g,"C01")],[("P01",4,4,4,"2026-10-01"),("P02",1,1,1,"2026-09-03")])
        s.assertEqual([x["customer_id"] for x in customers_of(g,"P05")],["C03","C04"])
        s.assertEqual(members_of(g,"G-F-20"),["C01","C02","C03"]); s.assertEqual(members_of(g,"G-F-30"),["C05"]); s.assertEqual(members_of(g,"G-F-10"),[])
        g.update_customer("C04",age=34); s.assertEqual(members_of(g,"G-M-20"),[])
    def test_s4(s):
        g=make(); s.assertEqual([(x["product_id"],x["score"],x["buyers"],x["sold_out"]) for x in group_popular(g,"G-F-20")],[("P02",3,2,False),("P01",3,1,False),("P03",2,2,False),("P05",1,1,True)])
        s.assertEqual([x["product_id"] for x in group_popular(g,"G-F-20",2)],["P02","P01"])
        for k in (0,11,True):
            with s.assertRaises(ValueError): group_popular(g,"G-F-20",k)
class W8(unittest.TestCase):
    def setUp(s): s.g=make(); s.g.add_customer("새","여",22)
    def test_cases(s):
        g=s.g
        s.assertEqual(full(recommend(g,"C07",3)),[("P02","group",3,2,["C01","C02"]),("P01","group",3,1,["C01"]),("P03","group",2,2,["C02","C03"])])
        s.assertEqual(recommend(g,"C07",3)[2]["available_colors"],["아이보리"])
        s.assertEqual(full(recommend(g,"C07",4))[3],("P04","all",1,1,["C04"]))
        s.assertEqual(full(recommend(g,"C02",3)),[("P01","group",3,1,["C01"]),("P04","all",1,1,["C04"])])
        r=recommend(g,"C06",3); s.assertEqual(full(r),[("P01","gender",1,1,["C04"]),("P04","gender",1,1,["C04"]),("P02","all",3,2,["C01","C02"])])
        s.assertEqual([x["available_colors"] for x in r],[["그레이","네이비","블랙","화이트"],["블랙","카키"],["베이지","블랙"]])
        for x in r: s.assertEqual(x["buyers"],len(x["supporters"]))
        for k in (0,11,True,"3"):
            with s.assertRaises(ValueError): recommend(g,"C07",k)
    def test_gender_union(s):
        g=s.g; g.add_purchase("C05","P04","카키",1,"2026-10-03")
        s.assertEqual(full(recommend(g,"C07",4)),[("P02","group",3,2,["C01","C02"]),("P01","group",3,1,["C01"]),("P03","group",2,2,["C02","C03"]),("P04","gender",1,1,["C05"])])
    def test_sold_out(s):
        g=s.g; g.update_product("P02",stock={"블랙":0,"베이지":0}); s.assertEqual([(x["product_id"],x["scope"]) for x in recommend(g,"C07",3)],[("P01","group"),("P03","group"),("P04","all")])
        for p in g.product_ids(): g.update_product(p,stock={c:0 for c in g.get_product(p)["stock"]})
        s.assertEqual(recommend(g,"C07",3),[])
if __name__=="__main__": unittest.main(verbosity=2)

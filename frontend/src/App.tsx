import { FormEvent, useEffect, useMemo, useState } from "react";

type Screen = "graph" | "customer" | "mutations" | "popular" | "product" | "integrity";
type Customer = { id: string; name: string; gender: string; age: number };
type Group = { id: string; label: string };
type Purchase = { product_id: string; name: string; colors: string[]; weight: number; count: number; total_qty: number; last_date: string };
type Product = { id: string; name: string; kind: string; style: string; price: number; stock: Record<string, number> };
type Buyer = { customer_id: string; name: string; group_id: string; colors: string[] };
type CustomerDetail = { customer: Customer; group: Group; purchases: Purchase[] };
type ProductDetail = { product: Product; buyers: Buyer[]; sold_out: boolean; available_colors: string[]; status_label: string };
type RecommendationItem = { product_id: string; product_name: string; score: number; buyers: number; scope: string; scope_label: string; supporters: string[]; available_colors: string[]; display_lines: string[] };
type Recommendations = { customer_id: string; k: number; items: RecommendationItem[]; header_line: string; notice_lines: string[]; lines: string[] };
type GraphNode = { id: string; kind: "group" | "customer" | "product"; label: string; neighbor_ids: string[] };
type GraphEdge = { kind: "membership" | "purchase"; source: string; target: string; weight: number | null };
type GraphData = { nodes: GraphNode[]; edges: GraphEdge[] };
type GroupRow = { id: string; label: string; members: Customer[] };
type GroupBranch = { gender: string; label: string; groups: GroupRow[] };
type GroupTree = { branches: GroupBranch[] };
type PopularItem = { product_id: string; product_name: string; score: number; buyers: number; sold_out: boolean; status_label: string };
type PopularResponse = { group: Group; k: number | null; items: PopularItem[] };
type Integrity = { violations: string[]; violation_count: number; lines: string[] };
type Stats = { groups: number; customers: number; products: number; membership_edges: number; purchase_edges: number; purchases: number };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const payload = await response.json() as T & { error?: string };
  if (!response.ok) throw new Error(payload.error ?? `HTTP ${response.status}`);
  return payload;
}

function ErrorBox({ error }: { error: string | null }) {
  return error ? <p className="error-box" role="alert">{error}</p> : null;
}

function GraphScreen({ data, onCustomer, onProduct }: { data: GraphData | null; onCustomer: (id: string) => void; onProduct: (id: string) => void }) {
  const [selected, setSelected] = useState<string | null>(null);
  const nodes = data?.nodes ?? [];
  const positions = useMemo(() => {
    const result: Record<string, { x: number; y: number }> = {};
    const columns = { group: 120, customer: 380, product: 640 } as const;
    const seen: Record<GraphNode["kind"], number> = { group: 0, customer: 0, product: 0 };
    nodes.forEach((node) => { result[node.id] = { x: columns[node.kind], y: 40 + seen[node.kind] * 38 }; seen[node.kind] += 1; });
    return result;
  }, [nodes]);
  if (!data) return <p>그래프를 불러오는 중입니다…</p>;
  const selectedNode = selected ? nodes.find((node) => node.id === selected) : undefined;
  return <section><div className="section-heading"><div><h2>그래프</h2><p>그룹 | 고객 | 상품 3단 배치 · 선 굵기는 서버가 준 가중치입니다.</p></div><p className="muted">노드를 클릭하면 이웃을 강조합니다.</p></div><div className="graph-wrap"><svg className="graph-svg" viewBox="0 0 760 700" role="img" aria-label="ShopGraph 그래프"><text x="120" y="20" textAnchor="middle" className="column-label">그룹</text><text x="380" y="20" textAnchor="middle" className="column-label">고객</text><text x="640" y="20" textAnchor="middle" className="column-label">상품</text>{data.edges.map((edge) => { const source = positions[edge.source]; const target = positions[edge.target]; if (!source || !target) return null; const active = selected === null || selected === edge.source || selected === edge.target; return <line key={`${edge.kind}-${edge.source}-${edge.target}`} x1={source.x} y1={source.y} x2={target.x} y2={target.y} className={active ? "graph-edge active" : "graph-edge dim"} strokeWidth={edge.weight ?? 1} />; })}{nodes.map((node) => { const point = positions[node.id]; const active = selected === null || selected === node.id || node.neighbor_ids.includes(selected); return <g key={node.id} className={active ? "graph-node active" : "graph-node dim"} onClick={() => setSelected(node.id)} role="button" tabIndex={0} onKeyDown={(event) => { if (event.key === "Enter") setSelected(node.id); }}><circle cx={point.x} cy={point.y} r="14" /><text x={point.x + 20} y={point.y + 5}>{node.id}</text><title>{node.label}</title></g>; })}</svg></div>{selectedNode && <div className="selected-card"><strong>{selectedNode.id} · {selectedNode.label}</strong><span>이웃: {selectedNode.neighbor_ids.length ? selectedNode.neighbor_ids.join(", ") : "없음"}</span>{selectedNode.kind === "customer" && <button onClick={() => onCustomer(selectedNode.id)}>고객 상세</button>}{selectedNode.kind === "product" && <button onClick={() => onProduct(selectedNode.id)}>상품 상세</button>}</div>}</section>;
}

function CustomerScreen({ customerId, refreshKey, onProduct }: { customerId: string; refreshKey: number; onProduct: (id: string) => void }) {
  const [detail, setDetail] = useState<CustomerDetail | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendations | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { let active = true; setError(null); Promise.all([api<CustomerDetail>(`/api/customers/${encodeURIComponent(customerId)}`), api<Recommendations>(`/api/customers/${encodeURIComponent(customerId)}/recommendations?k=3`)]).then(([nextDetail, nextRecommendations]) => { if (active) { setDetail(nextDetail); setRecommendations(nextRecommendations); } }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "고객 조회 실패"); }); return () => { active = false; }; }, [customerId, refreshKey]);
  return <section><div className="section-heading"><div><h2>고객 상세</h2><p>S1 구매 목록과 Python 추천 결과를 그대로 보여 줍니다.</p></div></div><ErrorBox error={error} />{detail && <div className="detail-grid"><article className="panel"><h3>{detail.customer.name} ({detail.customer.id})</h3><p>{detail.group.label} · {detail.customer.age}세 · {detail.customer.gender}</p><h4>S1: 산 상품</h4><ul>{detail.purchases.map((purchase) => <li key={purchase.product_id}><button className="link-button" onClick={() => onProduct(purchase.product_id)}>{purchase.name} ({purchase.product_id})</button> · 가중치 {purchase.weight} · {purchase.colors.join(", ")}</li>)}</ul></article><article className="panel recommendation-panel"><h3>{recommendations?.header_line ?? "추천을 불러오는 중입니다…"}</h3>{recommendations?.items.map((item, index) => <div className="recommendation-card" key={item.product_id}><div className="recommendation-title"><strong>{index + 1}. {item.product_name} ({item.product_id})</strong><span>점수 {item.score} · 구매 고객 {item.buyers}명 · {item.scope_label}</span></div><p>지지자: {item.supporters.length ? item.supporters.join(", ") : "없음"}</p><p>구매 가능 색상: {item.available_colors.length ? item.available_colors.join(", ") : "없음"}</p><div className="display-lines">{item.display_lines.map((line) => <span key={line}>{line}</span>)}</div><button onClick={() => onProduct(item.product_id)}>상품 상세</button></div>)}{recommendations?.notice_lines.map((line) => <p className="notice" key={line}>{line}</p>)}</article></div>}</section>;
}

function MutationScreen({ graph, onCustomerCreated, onChanged }: { graph: GraphData | null; onCustomerCreated: (id: string) => void; onChanged: () => void }) {
  const [customerForm, setCustomerForm] = useState({ name: "", gender: "여", age: "" });
  const [purchaseForm, setPurchaseForm] = useState({ customer_id: "C01", product_id: "P01", color: "", qty: "1", date: "2026-11-03" });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const products = graph?.nodes.filter((node) => node.kind === "product") ?? [];
  const submit = async (event: FormEvent, path: string, body: object, success: (payload: any) => void) => { event.preventDefault(); setError(null); setMessage(null); try { const result = await api<any>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); success(result); onChanged(); } catch (reason: unknown) { setError(reason instanceof Error ? reason.message : "변경 실패"); } };
  return <section><div className="section-heading"><div><h2>등록·구매</h2><p>변경 성공 뒤 그래프 간선·추천은 다시 Python API에서 읽습니다.</p></div></div><ErrorBox error={error} />{message && <p className="success-box">{message}</p>}<div className="form-grid"><form className="panel form-panel" onSubmit={(event) => submit(event, "/api/customers", { name: customerForm.name, gender: customerForm.gender, age: Number(customerForm.age) }, (result) => { setMessage(`${result.customer.id} 등록 완료 · ${result.group.label}`); onCustomerCreated(result.customer.id); })}><h3>고객 등록</h3><label>이름<input value={customerForm.name} onChange={(event) => setCustomerForm({ ...customerForm, name: event.target.value })} required /></label><label>성별<select value={customerForm.gender} onChange={(event) => setCustomerForm({ ...customerForm, gender: event.target.value })}><option value="여">여</option><option value="남">남</option></select></label><label>나이<input type="number" value={customerForm.age} onChange={(event) => setCustomerForm({ ...customerForm, age: event.target.value })} required /></label><button type="submit">등록 후 고객 상세 보기</button></form><form className="panel form-panel" onSubmit={(event) => submit(event, "/api/purchases", { ...purchaseForm, qty: Number(purchaseForm.qty) }, (result) => { setMessage(`${result.purchase_id} 구매 등록 · 가중치 ${result.weight}`); })}><h3>구매 등록</h3><label>고객 ID<input value={purchaseForm.customer_id} onChange={(event) => setPurchaseForm({ ...purchaseForm, customer_id: event.target.value })} required /></label><label>상품<select value={purchaseForm.product_id} onChange={(event) => setPurchaseForm({ ...purchaseForm, product_id: event.target.value })}>{products.map((product) => <option key={product.id} value={product.id}>{product.id} · {product.label}</option>)}</select></label><label>색상<input value={purchaseForm.color} onChange={(event) => setPurchaseForm({ ...purchaseForm, color: event.target.value })} required /></label><label>수량<input type="number" value={purchaseForm.qty} onChange={(event) => setPurchaseForm({ ...purchaseForm, qty: event.target.value })} required /></label><label>구매일<input type="date" value={purchaseForm.date} onChange={(event) => setPurchaseForm({ ...purchaseForm, date: event.target.value })} required /></label><button type="submit">구매 등록</button></form></div></section>;
}

function PopularScreen({ groupId, groups, refreshKey }: { groupId: string; groups: Group[]; refreshKey: number }) {
  const [items, setItems] = useState<PopularItem[]>([]);
  const [previous, setPrevious] = useState<PopularItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedGroup, setSelectedGroup] = useState(groupId);
  useEffect(() => { let active = true; api<PopularResponse>(`/api/groups/${encodeURIComponent(selectedGroup)}/popular`).then((response) => { if (active) { setPrevious(items.length ? items : null); setItems(response.items); } }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "인기 상품 조회 실패"); }); return () => { active = false; }; }, [selectedGroup, refreshKey]);
  const chart = (rows: PopularItem[], label: string) => <div className="bar-chart"><h3>{label}</h3><svg viewBox="0 0 620 260" role="img" aria-label={`${label} 막대 그래프`}>{rows.map((item, index) => <g key={item.product_id} transform={`translate(0 ${index * 42})`}><text x="0" y="18">{item.product_id}</text><rect x="62" y="4" width={item.score} height="22" className="score-bar" /><text x="76" y="20">{item.product_name} · {item.score}</text></g>)}</svg></div>;
  return <section><div className="section-heading"><div><h2>그룹 인기 S4</h2><p>점수와 순서는 서버 응답 그대로입니다.</p></div><select value={selectedGroup} onChange={(event) => setSelectedGroup(event.target.value)}>{groups.map((group) => <option key={group.id} value={group.id}>{group.label}</option>)}</select></div><ErrorBox error={error} /><div className="chart-grid">{chart(items, "현재")}{previous && chart(previous, "직전 조회")}</div><ol className="plain-list">{items.map((item) => <li key={item.product_id}>{item.product_id} · {item.product_name} · 구매자 {item.buyers}명 · {item.status_label}</li>)}</ol></section>;
}

function ProductScreen({ productId, refreshKey, onChanged }: { productId: string; refreshKey: number; onChanged: () => void }) {
  const [detail, setDetail] = useState<ProductDetail | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { let active = true; api<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`).then((next) => { if (active) { setDetail(next); setDraft(Object.fromEntries(Object.entries(next.product.stock).map(([color, count]) => [color, String(count)]))); } }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "상품 조회 실패"); }); return () => { active = false; }; }, [productId, refreshKey]);
  const updateStock = async (event: FormEvent) => { event.preventDefault(); setError(null); setMessage(null); const stock = Object.fromEntries(Object.entries(draft).map(([color, count]) => [color, Number(count)])); try { const result = await api<ProductDetail>(`/api/products/${encodeURIComponent(productId)}/stock`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ stock }) }); setDetail(result); setMessage("재고를 수정했습니다"); onChanged(); } catch (reason: unknown) { setError(reason instanceof Error ? reason.message : "재고 수정 실패"); } };
  return <section><div className="section-heading"><div><h2>상품 상세</h2><p>S2 고객 목록과 서버의 재고·품절 상태입니다.</p></div></div><ErrorBox error={error} />{message && <p className="success-box">{message}</p>}{detail && <div className="detail-grid"><article className="panel"><h3>{detail.product.name} ({detail.product.id})</h3><p>{detail.product.kind} · {detail.product.style} · {detail.product.price.toLocaleString()}원</p><p className="status-pill">{detail.status_label}</p><h4>S2 구매 고객</h4><ul>{detail.buyers.map((buyer) => <li key={buyer.customer_id}>{buyer.name} ({buyer.customer_id}) · {buyer.colors.join(", ")}</li>)}</ul><p>구매 가능 색상: {detail.available_colors.length ? detail.available_colors.join(", ") : "없음"}</p></article><form className="panel form-panel" onSubmit={updateStock}><h3>재고 수정</h3>{Object.entries(draft).map(([color, count]) => <label key={color}>{color}<input type="number" value={count} onChange={(event) => setDraft({ ...draft, [color]: event.target.value })} /></label>)}<button type="submit">색상별 재고 전체 저장</button></form></div>}</section>;
}

function IntegrityScreen({ refreshKey }: { refreshKey: number }) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [integrity, setIntegrity] = useState<Integrity | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { let active = true; Promise.all([api<{ stats: Stats }>("/api/stats"), api<Integrity>("/api/integrity")]).then(([statsResponse, integrityResponse]) => { if (active) { setStats(statsResponse.stats); setIntegrity(integrityResponse); } }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "검사 실패"); }); return () => { active = false; }; }, [refreshKey]);
  return <section><div className="section-heading"><div><h2>무결성 검사</h2><p>통계와 check_integrity() 결과를 서버에서 받습니다.</p></div></div><ErrorBox error={error} />{stats && <div className="stats-grid">{Object.entries(stats).map(([key, value]) => <div className="stat-card" key={key}><span>{key}</span><strong>{value}</strong></div>)}</div>}{integrity && <div className={integrity.violation_count ? "panel integrity-bad" : "panel integrity-good"}><h3>{integrity.violation_count ? `위반 ${integrity.violation_count}건` : "위반 없음"}</h3>{integrity.lines.map((line) => <p key={line}>{line}</p>)}</div>}</section>;
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("graph");
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [customerId, setCustomerId] = useState("C01");
  const [productId, setProductId] = useState("P01");
  const [refreshKey, setRefreshKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const refresh = () => { setRefreshKey((value) => value + 1); };
  useEffect(() => { let active = true; Promise.all([api<GraphData>("/api/graph"), api<GroupTree>("/api/groups")]).then(([nextGraph, tree]) => { if (active) { setGraph(nextGraph); setGroups(tree.branches.flatMap((branch) => branch.groups.map((group) => ({ id: group.id, label: group.label })))); } }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "초기 데이터 조회 실패"); }); return () => { active = false; }; }, [refreshKey]);
  const content = screen === "graph" ? <GraphScreen data={graph} onCustomer={(id) => { setCustomerId(id); setScreen("customer"); }} onProduct={(id) => { setProductId(id); setScreen("product"); }} /> : screen === "customer" ? <CustomerScreen customerId={customerId} refreshKey={refreshKey} onProduct={(id) => { setProductId(id); setScreen("product"); }} /> : screen === "mutations" ? <MutationScreen graph={graph} onCustomerCreated={(id) => { setCustomerId(id); setScreen("customer"); }} onChanged={refresh} /> : screen === "popular" ? <PopularScreen groupId="G-F-20" groups={groups} refreshKey={refreshKey} /> : screen === "product" ? <ProductScreen productId={productId} refreshKey={refreshKey} onChanged={refresh} /> : <IntegrityScreen refreshKey={refreshKey} />;
  return <div className="app-shell"><header className="app-header"><div><p className="eyebrow">자료구조 팀프로젝트</p><h1>ShopGraph</h1></div><span>Python 계산 · SVG 화면</span></header><nav className="tab-bar" aria-label="화면 선택">{([["graph", "그래프"], ["customer", "고객 상세"], ["mutations", "등록·구매"], ["popular", "그룹 인기"], ["product", "상품 상세"], ["integrity", "무결성"]] as const).map(([value, label]) => <button key={value} className={screen === value ? "tab active" : "tab"} onClick={() => setScreen(value)}>{label}</button>)}</nav><main className="content"><ErrorBox error={error} />{content}</main><footer>서버: 127.0.0.1 · 저장하지 않음 · 새로고침하면 초기 상태</footer></div>;
}

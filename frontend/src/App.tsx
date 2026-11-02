import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

type Screen = "graph" | "customer" | "mutations" | "popular" | "product" | "integrity";
type Customer = { id: string; name: string; gender: string; age: number };
type Group = { id: string; label: string };
type Purchase = { product_id: string; name: string; colors: string[]; weight: number };
type Product = { id: string; name: string; kind: string; style: string; price: number; stock: Record<string, number> };
type Buyer = { customer_id: string; name: string; group_id: string; colors: string[] };
type CustomerDetail = { customer: Customer; group: Group; purchases: Purchase[] };
type ProductDetail = { product: Product; buyers: Buyer[]; sold_out: boolean; available_colors: string[]; status_label: string };
type RecommendationItem = {
  product_id: string; product_name: string; score: number; buyers: number;
  scope: "group" | "gender" | "all"; scope_label: string; supporters: string[];
  available_colors: string[]; display_lines: string[];
};
type Recommendations = { items: RecommendationItem[]; header_line: string; notice_lines: string[] };
type GraphNode = { id: string; kind: "group" | "customer" | "product"; label: string; neighbor_ids: string[] };
type GraphEdge = { kind: "membership" | "purchase"; source: string; target: string; weight: number | null };
type GraphData = { nodes: GraphNode[]; edges: GraphEdge[] };
type GroupCount = Group & { count: number };
type GroupTree = { branches: { groups: GroupCount[] }[] };
type PopularItem = { product_id: string; product_name: string; score: number; buyers: number; status_label: string };
type PopularResponse = { group: Group; k: number | null; items: PopularItem[] };
type Integrity = { violation_count: number; lines: string[] };
type Stats = { groups: number; customers: number; products: number; membership_edges: number; purchase_edges: number; purchases: number };
type Meta = { k_default: number; k_max: number };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const payload = await response.json() as T & { error?: string };
  if (!response.ok) throw new Error(payload.error ?? `HTTP ${response.status}`);
  return payload;
}

function jsonRequest(method: string, body: object): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

function errorMessage(reason: unknown): string {
  return reason instanceof Error ? reason.message : "요청을 처리할 수 없습니다";
}

/** 이전 선택의 느린 응답은 폐기하고 최신 경로의 서버 응답만 표시한다. */
function useApi<T>(path: string, refreshKey: number, retainDuringRefresh = false) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(null);
    if (!retainDuringRefresh) setData(null);
    api<T>(path, { signal: controller.signal }).then((result) => {
      if (!controller.signal.aborted) setData(result);
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(errorMessage(reason));
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [path, refreshKey, retainDuringRefresh]);
  return { data, error, loading };
}

function ErrorBox({ error }: { error: string | null }) {
  return error ? <p className="error-box" role="alert">{error}</p> : null;
}

function NodeSelect({ label, nodes, value, onChange }: {
  label: string; nodes: GraphNode[]; value: string; onChange: (id: string) => void;
}) {
  return <label className="select-label">{label}
    <select value={value} onChange={(event) => onChange(event.target.value)}>
      {nodes.map((node) => <option key={node.id} value={node.id}>{node.id} · {node.label}</option>)}
    </select>
  </label>;
}

/** 노드 수에 따른 조절은 SVG 좌표뿐이며 서버 배열의 순서를 유지한다. */
function GraphScreen({ data, groups, onCustomer, onProduct }: {
  data: GraphData | null; groups: GroupCount[]; onCustomer: (id: string) => void; onProduct: (id: string) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const layout = useMemo(() => {
    const columns = [
      { kind: "group", label: "그룹", x: 26, backgroundX: 0, width: 350 },
      { kind: "customer", label: "고객", x: 382, backgroundX: 350, width: 365 },
      { kind: "product", label: "상품", x: 746, backgroundX: 715, width: 405 },
    ] as const;
    const points: Record<string, { x: number; y: number; radius: number; fontSize: number }> = {};
    columns.forEach((column) => {
      const rows = data?.nodes.filter((node) => node.kind === column.kind) ?? [];
      const gap = 464 / Math.max(rows.length, 1);
      rows.forEach((node, index) => {
        points[node.id] = { x: column.x, y: 37 + gap * (index + .5),
          radius: Math.min(6, gap * .28), fontSize: 13 };
      });
    });
    const groupNodes = data?.nodes.filter((node) => node.kind === "group") ?? [];
    const occupied: number[] = [];
    const empty: GraphNode[] = [];
    groupNodes.forEach((node) => {
      const memberPoints = node.neighbor_ids.map((id) => points[id]).filter(Boolean);
      if (memberPoints.length) {
        points[node.id].y = memberPoints.reduce((sum, point) => sum + point.y, 0) / memberPoints.length;
        occupied.push(points[node.id].y);
      } else empty.push(node);
    });
    // 빈 그룹만 여유 좌표에 서버 순서대로 배치한다. 그룹/고객 배열은 재정렬하지 않는다.
    empty.forEach((node) => {
      const spare = Array.from({ length: 18 }, (_, index) => 50 + index * 25)
        .find((y) => occupied.every((used) => Math.abs(used - y) >= 24));
      points[node.id].y = spare ?? points[node.id].y;
      occupied.push(points[node.id].y);
    });
    return { columns, points };
  }, [data]);
  if (!data) return <p>그래프를 불러오는 중입니다…</p>;
  const selectedNode = data.nodes.find((node) => node.id === selected);
  const neighbors = selectedNode?.neighbor_ids.map((id) => {
    const node = data.nodes.find((row) => row.id === id)!;
    const edge = data.edges.find((row) => (row.source === selected && row.target === id)
      || (row.target === selected && row.source === id))!;
    const relation = edge.kind === "purchase" ? `구매${node.kind === "customer" ? " 고객" : ""} · 가중치 ${edge.weight}`
      : node.kind === "group" ? "소속 그룹" : "소속 고객";
    return `${node.label}(${relation})`;
  }).join(", ");
  return <section className="graph-screen">
    <div className="section-heading"><div><h2>그래프</h2><p>노드를 선택하면 이웃과 연결 간선을 강조합니다.</p></div>
      <button className="secondary-button" disabled={!selected} onClick={() => setSelected(null)}>선택 해제</button></div>
    <div className="graph-legend"><span><i className="legend-membership" />소속 간선</span>
      <span><i className="legend-purchase" />구매 간선 · 굵기 = 가중치</span><span>전체 {data.nodes.length}개 노드</span></div>
    <div className="graph-wrap"><svg className="graph-svg" viewBox="0 0 1120 516" preserveAspectRatio="none" role="img" aria-label="ShopGraph 그래프">
      {layout.columns.map((column) => <g key={column.kind}>
        <rect className={`column-background ${column.kind}`} x={column.backgroundX} y="0" width={column.width} height="516" />
        <text x={column.x} y="23" className="column-label">{column.label}</text>
      </g>)}
      {data.edges.map((edge) => {
        const source = layout.points[edge.source]; const target = layout.points[edge.target];
        const active = selected === edge.source || selected === edge.target;
        return <line key={`${edge.kind}-${edge.source}-${edge.target}`} x1={source.x} y1={source.y}
          x2={target.x} y2={target.y} data-source={edge.source} data-target={edge.target}
          className={`graph-edge ${edge.kind} ${active ? "active" : selected ? "dim" : "rest"}`}
          strokeWidth={edge.weight ?? 1} vectorEffect="non-scaling-stroke" />;
      })}
      {data.nodes.map((node) => {
        const point = layout.points[node.id];
        const active = selected === node.id || selectedNode?.neighbor_ids.includes(node.id);
        const count = groups.find((group) => group.id === node.id)?.count;
        const text = node.kind === "group" ? `${node.label}${count === undefined ? "" : ` · ${count}명`}` : `${node.id} · ${node.label.length > 12 ? `${node.label.slice(0, 12)}…` : node.label}`;
        return <g key={node.id} data-node-id={node.id} aria-label={`${node.id} ${node.label}`}
          data-group-count={node.kind === "group" ? count : undefined}
          className={`graph-node ${active ? "active" : selected ? "dim" : "rest"} ${selected === node.id ? "selected" : ""}`}
          onClick={() => setSelected(node.id)} role="button" tabIndex={0}
          onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelected(node.id); } }}>
          <title>{node.id} · {node.label}</title><circle cx={point.x} cy={point.y} r={point.radius} />
          <text x={point.x + point.radius + 7} y={point.y} dominantBaseline="middle" fontSize={point.fontSize}>{text}</text>
        </g>;
      })}
    </svg></div>
    <div className="selected-card" aria-live="polite">{selectedNode ? <>
      <strong>{selectedNode.id} · {selectedNode.label}</strong>
      <span className="neighbor-summary" title={neighbors}>이웃: {neighbors || "없음"}</span>
      {selectedNode.kind === "customer" && <button onClick={() => onCustomer(selectedNode.id)}>고객 상세</button>}
      {selectedNode.kind === "product" && <button onClick={() => onProduct(selectedNode.id)}>상품 상세</button>}
    </> : <span>노드를 선택해 이름과 이웃을 확인하세요.</span>}</div>
  </section>;
}

function CustomerScreen({ customerId, customers, refreshKey, onCustomer, onProduct }: {
  customerId: string; customers: GraphNode[]; refreshKey: number;
  onCustomer: (id: string) => void; onProduct: (id: string) => void;
}) {
  const detail = useApi<CustomerDetail>(`/api/customers/${encodeURIComponent(customerId)}`, refreshKey);
  const recommendations = useApi<Recommendations>(`/api/customers/${encodeURIComponent(customerId)}/recommendations`, refreshKey);
  return <section>
    <div className="section-heading"><div><h2>고객 상세</h2><p>S1 구매 목록과 고객별 추천</p></div>
      <NodeSelect label="고객" nodes={customers} value={customerId} onChange={onCustomer} /></div>
    <ErrorBox error={detail.error ?? recommendations.error} />
    {detail.loading && <p>고객을 불러오는 중입니다…</p>}
    {detail.data && <div className="detail-grid customer-grid">
      <article className="panel"><h3>{detail.data.customer.name} ({detail.data.customer.id})</h3>
        <p>{detail.data.group.label} · {detail.data.customer.age}세</p><h4>S1: 산 상품</h4>
        <ul>{detail.data.purchases.map((purchase) => <li key={purchase.product_id}>
          <button className="link-button" onClick={() => onProduct(purchase.product_id)}>{purchase.name} ({purchase.product_id})</button>
          <span className="purchase-meta">가중치 {purchase.weight} · {purchase.colors.join(", ")}</span>
        </li>)}</ul>{detail.data.purchases.length === 0 && <p className="muted">구매 기록이 없습니다.</p>}
      </article>
      <article className="panel recommendation-panel"><h3>{recommendations.data?.header_line ?? "추천을 불러오는 중입니다…"}</h3>
        {recommendations.data && recommendations.data.notice_lines.length > 0 && <aside className="notice-box" aria-label="추천 안내">
          <strong>추천 안내</strong>{recommendations.data.notice_lines.map((line) => <p key={line}>{line}</p>)}
        </aside>}
        {recommendations.data?.items.map((item, index) => <div className="recommendation-card" key={item.product_id}>
          <div className="recommendation-title"><strong>{index + 1}. {item.product_name} ({item.product_id})</strong>
            <span className={`scope-badge ${item.scope}`}>{item.scope_label}</span></div>
          <p className="score-summary">점수 {item.score} · 구매 고객 {item.buyers}명</p>
          <p className="supporter-line">{item.display_lines[1].trimStart()}</p>
          <p>{item.display_lines[2]}</p>
          <div className="card-actions"><button onClick={() => onProduct(item.product_id)}>상품 상세</button>
            <details><summary>콘솔 출력 보기</summary><div className="display-lines">
              {item.display_lines.map((line) => <span key={line}>{line}</span>)}
            </div></details></div>
        </div>)}
      </article>
    </div>}
  </section>;
}

function MutationScreen({ customers, products, lastRegisteredId, onCustomerCreated, onChanged }: {
  customers: GraphNode[]; products: GraphNode[]; lastRegisteredId: string | null;
  onCustomerCreated: (id: string) => void; onChanged: () => void;
}) {
  const [customerForm, setCustomerForm] = useState({ name: "", gender: "여", age: "" });
  const [purchaseForm, setPurchaseForm] = useState({ customer_id: lastRegisteredId ?? customers[0]?.id ?? "", product_id: products[0]?.id ?? "", qty: "1", date: "2026-11-03" });
  const [color, setColor] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const product = useApi<ProductDetail>(`/api/products/${encodeURIComponent(purchaseForm.product_id)}`, 0);
  const colors = product.data ? Object.keys(product.data.product.stock) : [];
  useEffect(() => { setColor(""); }, [purchaseForm.product_id]);
  async function register(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError(null); setMessage(null);
    try {
      const result = await api<{ customer: Customer; group: Group }>("/api/customers", jsonRequest("POST", { ...customerForm, age: Number(customerForm.age) }));
      onChanged(); onCustomerCreated(result.customer.id);
    } catch (reason: unknown) { setError(errorMessage(reason)); } finally { setBusy(false); }
  }
  async function purchase(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError(null); setMessage(null);
    try {
      const result = await api<{ purchase_id: string; weight: number }>("/api/purchases", jsonRequest("POST", {
        ...purchaseForm, color: color || colors[0], qty: Number(purchaseForm.qty),
      }));
      setMessage(`${result.purchase_id} 구매 등록 · 가중치 ${result.weight}`); onChanged();
    } catch (reason: unknown) { setError(errorMessage(reason)); } finally { setBusy(false); }
  }
  return <section><div className="section-heading"><div><h2>등록·구매</h2><p>구매를 등록한 뒤 그래프와 추천의 변화를 확인하세요.</p></div></div>
    <ErrorBox error={error ?? product.error} />{message && <p className="success-box" role="status">{message}</p>}
    <div className="form-grid"><form className="panel form-panel" onSubmit={register}><h3>고객 등록</h3>
      <label>이름<input value={customerForm.name} onChange={(event) => setCustomerForm({ ...customerForm, name: event.target.value })} required /></label>
      <label>성별<select value={customerForm.gender} onChange={(event) => setCustomerForm({ ...customerForm, gender: event.target.value })}><option value="여">여</option><option value="남">남</option></select></label>
      <label>나이<input type="number" value={customerForm.age} onChange={(event) => setCustomerForm({ ...customerForm, age: event.target.value })} required /></label>
      <button disabled={busy} type="submit">등록 후 고객 상세 보기</button>
    </form><form className="panel form-panel" onSubmit={purchase}><h3>구매 등록</h3>
      <NodeSelect label="고객" nodes={customers} value={purchaseForm.customer_id} onChange={(id) => setPurchaseForm({ ...purchaseForm, customer_id: id })} />
      <NodeSelect label="상품" nodes={products} value={purchaseForm.product_id} onChange={(id) => setPurchaseForm({ ...purchaseForm, product_id: id })} />
      <label>색상<select value={color || colors[0] || ""} disabled={product.loading} required onChange={(event) => setColor(event.target.value)}>
        {product.loading && <option value="">색상을 불러오는 중…</option>}{colors.map((name) => <option key={name} value={name}>{name}</option>)}
      </select></label>
      <label>수량<input type="number" value={purchaseForm.qty} onChange={(event) => setPurchaseForm({ ...purchaseForm, qty: event.target.value })} required /></label>
      <label>구매일<input type="date" value={purchaseForm.date} onChange={(event) => setPurchaseForm({ ...purchaseForm, date: event.target.value })} required /></label>
      <button disabled={busy || product.loading || !product.data} type="submit">구매 등록</button>
    </form></div>
  </section>;
}

/** 점수는 재계산하지 않는다. 막대 좌표와 두 응답에서의 순번 비교만 표시용으로 만든다. */
function PopularChart({ response, label, other }: { response: PopularResponse; label: string; other: PopularResponse | null }) {
  const rows = response.items;
  const maxScore = Math.max(1, ...rows.map((item) => item.score));
  const height = Math.max(52, rows.length * 48 + 12);
  return <article className="bar-chart"><h3>{label} · {response.group.label}</h3>
    {rows.length === 0 ? <p className="muted">인기 상품이 없습니다.</p> : <>
      <svg viewBox={`0 0 520 ${height}`} style={{ aspectRatio: `520 / ${height}` }} role="img" aria-label={`${label} 막대 그래프`}>
        {rows.map((item, index) => {
          const otherRank = other?.items.findIndex((row) => row.product_id === item.product_id);
          const moved = otherRank !== undefined && otherRank !== index;
          return <g key={item.product_id} className={moved ? "rank-changed" : ""} transform={`translate(0 ${index * 48})`}>
            <title>{item.product_name} · 점수 {item.score}</title>
            <text x="0" y="16">{index + 1}. {item.product_id} · {item.product_name}{moved ? " · 순위 변경" : ""}</text>
            <rect x="0" y="24" width={464 * item.score / maxScore} height="15" rx="3" className="score-bar" />
            <text x="485" y="37" textAnchor="end" className="bar-score">{item.score}</text>
          </g>;
        })}
      </svg>
      <ol className="popular-list">{rows.map((item, index) => {
        const otherRank = other?.items.findIndex((row) => row.product_id === item.product_id);
        return <li key={item.product_id} className={otherRank !== undefined && otherRank !== index ? "rank-changed" : ""}>
          {item.product_id} · 점수 {item.score} · 구매자 {item.buyers}명 · {item.status_label}
        </li>;
      })}</ol>
    </>}
  </article>;
}

function PopularScreen({ groups, refreshKey, visible, meta }: { groups: Group[]; refreshKey: number; visible: boolean; meta: Meta | null }) {
  const [groupId, setGroupId] = useState("G-F-20");
  const [k, setK] = useState("");
  const [current, setCurrent] = useState<PopularResponse | null>(null);
  const [before, setBefore] = useState<PopularResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [requestKey, setRequestKey] = useState(0);
  useEffect(() => {
    if (!visible) return;
    const controller = new AbortController(); setLoading(true); setError(null);
    api<PopularResponse>(`/api/groups/${encodeURIComponent(groupId)}/popular${k ? `?k=${k}` : ""}`, { signal: controller.signal })
      .then((response) => { if (!controller.signal.aborted) setCurrent(response); })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(errorMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [groupId, k, refreshKey, requestKey, visible]);
  function changeFilter(nextGroup: string, nextK: string) {
    setBefore(null); setCurrent(null); setGroupId(nextGroup); setK(nextK);
  }
  return <section><div className="section-heading"><div><h2>그룹 인기 S4</h2><p>「전」을 고정한 뒤 구매를 등록하고 돌아와 「후」와 비교하세요.</p></div>
    <div className="toolbar"><label className="select-label">그룹<select value={groupId} onChange={(event) => changeFilter(event.target.value, k)}>
      {groups.map((group) => <option key={group.id} value={group.id}>{group.label}</option>)}</select></label>
      <label className="select-label">개수<select value={k} onChange={(event) => changeFilter(groupId, event.target.value)}>
        <option value="">전체</option>{Array.from({ length: meta?.k_max ?? 0 }, (_, index) => <option key={index + 1}>{index + 1}</option>)}
      </select></label></div></div>
    <div className="comparison-actions"><button disabled={!current || loading} onClick={() => setBefore(current)}>지금을 '전'으로 고정</button>
      <button className="secondary-button" disabled={loading} onClick={() => setRequestKey((value) => value + 1)}>다시 조회</button>
      {before && <><span className="comparison-hint">전 응답 고정 중 · 순위 변경 상품은 주황색</span><button className="secondary-button" onClick={() => setBefore(null)}>비교 해제</button></>}
    </div><ErrorBox error={error} />{loading && <p role="status">인기 상품을 갱신하는 중입니다…</p>}
    {current && <div className={before ? "chart-grid" : "single-chart"}>
      {before && <PopularChart response={before} label="전 · 고정" other={current} />}
      <PopularChart response={current} label={before ? "후 · 현재" : "현재"} other={before} />
    </div>}
  </section>;
}

function ProductScreen({ productId, products, refreshKey, onChanged, onProduct, lastCustomer, onRecommendations }: {
  productId: string; products: GraphNode[]; refreshKey: number; onChanged: () => void;
  onProduct: (id: string) => void; lastCustomer: GraphNode | undefined; onRecommendations: () => void;
}) {
  const detail = useApi<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`, refreshKey);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (detail.data) setDraft(Object.fromEntries(Object.entries(detail.data.product.stock).map(([color, count]) => [color, String(count)]))); }, [detail.data]);
  useEffect(() => { setSaved(false); setError(null); }, [productId]);
  async function updateStock(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError(null); setSaved(false);
    const stock = Object.fromEntries(Object.entries(draft).map(([color, count]) => [color, Number(count)]));
    try {
      await api<Pick<ProductDetail, "product" | "sold_out" | "available_colors" | "status_label">>(
        `/api/products/${encodeURIComponent(productId)}/stock`, jsonRequest("PUT", { stock }));
      setSaved(true); onChanged(); // S2를 포함한 전체 상품 상세는 GET으로 다시 읽는다.
    } catch (reason: unknown) { setError(errorMessage(reason)); } finally { setBusy(false); }
  }
  return <section><div className="section-heading"><div><h2>상품 상세</h2><p>S2 구매 고객 · 재고와 구매 가능 색상</p></div>
    <NodeSelect label="상품" nodes={products} value={productId} onChange={onProduct} /></div>
    <ErrorBox error={error ?? detail.error} />{saved && <div className="success-box" role="status"><span>재고를 수정했습니다.</span>
      {lastCustomer && <button onClick={onRecommendations}>{lastCustomer.label}({lastCustomer.id}) 고객 추천 다시 보기</button>}
    </div>}{detail.loading && <p>상품을 불러오는 중입니다…</p>}
    {detail.data && <div className="detail-grid"><article className="panel"><h3>{detail.data.product.name} ({detail.data.product.id})</h3>
      <p>{detail.data.product.kind} · {detail.data.product.style} · {detail.data.product.price.toLocaleString()}원</p><p className="status-pill">{detail.data.status_label}</p>
      <h4>S2 구매 고객</h4><ul>{detail.data.buyers.map((buyer) => <li key={buyer.customer_id}>{buyer.name} ({buyer.customer_id}) · {buyer.colors.join(", ")}</li>)}</ul>
      <p>구매 가능 색상: {detail.data.available_colors.join(", ") || "없음"}</p>
    </article><form className="panel form-panel" onSubmit={updateStock}><h3>재고 수정</h3>
      {Object.entries(draft).map(([color, count]) => <label key={color}>{color}<input type="number" required value={count} onChange={(event) => setDraft({ ...draft, [color]: event.target.value })} /></label>)}
      <button disabled={busy} type="submit">색상별 재고 전체 저장</button>
    </form></div>}
  </section>;
}

const STAT_LABELS: [keyof Stats, string][] = [
  ["groups", "그룹 노드"], ["customers", "고객 노드"], ["products", "상품 노드"],
  ["membership_edges", "소속 간선"], ["purchase_edges", "구매 간선"], ["purchases", "구매 기록"],
];

function IntegrityScreen({ refreshKey }: { refreshKey: number }) {
  const stats = useApi<{ stats: Stats }>("/api/stats", refreshKey);
  const integrity = useApi<Integrity>("/api/integrity", refreshKey);
  const values = stats.data?.stats;
  return <section><div className="section-heading"><div><h2>무결성 검사</h2><p>원본과 그래프의 일관성을 확인합니다.</p></div></div>
    <ErrorBox error={stats.error ?? integrity.error} />
    {values && <div className="stats-grid">{STAT_LABELS.map(([key, label]) => <div className="stat-card" key={key}><span>{label}</span><strong>{values[key]}</strong></div>)}</div>}
    {integrity.data && <div className={integrity.data.violation_count ? "panel integrity-bad" : "panel integrity-good"}>
      <h3>{integrity.data.violation_count ? `위반 ${integrity.data.violation_count}건` : "위반 없음"}</h3>{integrity.data.lines.map((line) => <p key={line}>{line}</p>)}
    </div>}
  </section>;
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("graph");
  const [customerId, setCustomerId] = useState("C01");
  const [lastViewedCustomerId, setLastViewedCustomerId] = useState<string | null>(null);
  const [lastRegisteredId, setLastRegisteredId] = useState<string | null>(null);
  const [productId, setProductId] = useState("P01");
  const [refreshKey, setRefreshKey] = useState(0);
  const graph = useApi<GraphData>("/api/graph", refreshKey, true);
  const tree = useApi<GroupTree>("/api/groups", refreshKey);
  const meta = useApi<Meta>("/api/meta", 0);
  const customers = graph.data?.nodes.filter((node) => node.kind === "customer") ?? [];
  const products = graph.data?.nodes.filter((node) => node.kind === "product") ?? [];
  const groups = tree.data?.branches.flatMap((branch) => branch.groups) ?? [];
  const lastCustomer = customers.find((node) => node.id === lastViewedCustomerId);
  function showCustomer(id: string) { setCustomerId(id); setLastViewedCustomerId(id); setScreen("customer"); }
  function showProduct(id: string) { setProductId(id); setScreen("product"); }
  function refresh() { setRefreshKey((value) => value + 1); }
  return <div className="app-shell">
    <header className="app-header"><div><p className="eyebrow">자료구조 팀프로젝트</p><h1>ShopGraph</h1></div><span>구매로 연결되는 고객과 상품</span></header>
    <nav className="tab-bar" aria-label="화면 선택">{([
      ["graph", "그래프"], ["customer", "고객 상세"], ["mutations", "등록·구매"],
      ["popular", "그룹 인기"], ["product", "상품 상세"], ["integrity", "무결성"],
    ] as const).map(([value, label]) => <button key={value} className={screen === value ? "tab active" : "tab"}
      onClick={() => value === "customer" ? showCustomer(customerId) : setScreen(value)}>{label}</button>)}</nav>
    <main className="content"><ErrorBox error={graph.error ?? tree.error ?? meta.error} />
      {screen === "graph" && <GraphScreen data={graph.data} groups={groups} onCustomer={showCustomer} onProduct={showProduct} />}
      {screen === "customer" && <CustomerScreen customerId={customerId} customers={customers} refreshKey={refreshKey} onCustomer={showCustomer} onProduct={showProduct} />}
      {screen === "mutations" && graph.data && <MutationScreen customers={customers} products={products} lastRegisteredId={lastRegisteredId} onChanged={refresh}
        onCustomerCreated={(id) => { setLastRegisteredId(id); showCustomer(id); }} />}
      {/* 비교용 '전'은 탭을 옮겨도 보존한다. 조회는 화면이 보일 때만 한다. */}
      <div hidden={screen !== "popular"}><PopularScreen groups={groups} refreshKey={refreshKey} visible={screen === "popular"} meta={meta.data} /></div>
      {screen === "product" && <ProductScreen productId={productId} products={products} refreshKey={refreshKey} onChanged={refresh} onProduct={setProductId}
        lastCustomer={lastCustomer} onRecommendations={() => { if (lastViewedCustomerId) showCustomer(lastViewedCustomerId); }} />}
      {screen === "integrity" && <IntegrityScreen refreshKey={refreshKey} />}
    </main><footer>저장하지 않음 · 서버를 다시 켜면 처음 상태</footer>
  </div>;
}

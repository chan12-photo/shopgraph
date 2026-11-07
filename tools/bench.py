"""X0 기준 측정(v3 부록 A bench2.py 기반), 표준 라이브러리 전용 개발 도구.

실행: python3 -B tools/bench.py time|mem|rss [C P T] [--seed 1] [--json 경로]
기본 규모: 고객 10,000명·상품 1,000개·구매 300,000건. 모드마다 별도
프로세스로 실행한다. time/RSS에는 tracemalloc을 켜지 않으며 mem의 RSS는 재지 않는다.
생성 시간은 입력 생성이 아닌 ShopGraph 생성자(검증·복사·그래프 구성) 시간이다.

현재 운영 ID는 C99·P99·T999까지다. 이 도구의 측정 프로세스 안에서만
graph._ID_PATTERNS·graph._ID_DIGITS를 6/6/7자리로 바꿔 끼우고 finally로 복구한다.
운영 코드는 바꾸지 않는다. X2에서 검증이 분리되면 이 방식이 바뀔 수 있다(v3 5.5).
X1 이후 정식 ID 규칙을 쓰도록 도구를 갱신해야 하며 지금 수치는 ID 패치 기준이다.
ID 상수 외에 운영 객체의 내부 속성에는 접근하지 않는다. main.py 경로에 포함되지 않는다.

모든 출력은 Codex 자체 확인이며 판정·승인은 찬일이 한다. 전부 품절은 스트레스
사례로 최악 시간을 증명하지 않는다. 웹 계층·브라우저 렌더링은 측정하지 않는다.
"""

import argparse
import gc
import hashlib
import json
import os
import pathlib
import platform
import random
import re
import resource
import statistics
import subprocess
import sys
import time
import tracemalloc
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import partial
from types import MappingProxyType

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import graph
import search

PALETTE = ("블랙", "화이트", "그레이", "네이비", "베이지", "카키", "아이보리", "브라운")
ID_NOTE = ("측정 프로세스 안에서만 graph의 ID 패턴·자릿수를 6/6/7로 바꿔 끼움. "
           "운영 코드 불변. X2에서 검증이 분리되면 이 방식이 바뀔 수 있다(v3 5.5).")
LABELS = MappingProxyType({
    "initialize": "생성(ShopGraph)", "add_customer": "고객 등록",
    "add_purchase": "구매 등록", "update_purchase": "구매 수정",
    "delete_purchase": "구매 삭제", "delete_customer": "고객 삭제",
    "recommend_k3": "추천 K=3", "recommend_k10": "추천 K=10",
    "sold_out_recommend": "전부 품절 추천", "s4": "S4",
    "integrity": "무결성 검사", "delete_popular_product": "인기 상품 삭제",
    "update_stock": "재고 변경", "move_group": "그룹 이동",
    "get_purchase": "구매 단건 조회(메모리, DB 없음)",
    "input": "입력 리스트", "retained": "입력 삭제 후 ShopGraph 보유",
    "initialization_peak": "입력+생성 추적 최댓값",
    "integrity_peak": "무결성 검사 중 추적 최댓값(보유량 포함)",
    "after_input": "입력 생성 후 최대 RSS",
    "after_graph": "그래프 생성 후 최대 RSS(입력 유지)",
    "after_integrity": "입력 삭제·무결성 검사 후 누적 최대 RSS",
})


@contextmanager
def measurement_ids() -> Iterator[None]:
    """목적: 측정 중에만 ID 확장. 인자: 없음. 반환: 문맥. 예외: 본문 예외를 전파."""
    patterns, digits = graph._ID_PATTERNS, graph._ID_DIGITS
    try:
        graph._ID_PATTERNS = MappingProxyType({
            prefix: re.compile(prefix + r"[0-9]{" + str(width) + "}")
            for prefix, width in (("C", 6), ("P", 6), ("T", 7))
        })
        graph._ID_DIGITS = MappingProxyType({"C": 6, "P": 6, "T": 7})
        yield
    finally:
        graph._ID_PATTERNS, graph._ID_DIGITS = patterns, digits


def make_records(c: int, p: int, t: int, seed: int = 1) -> tuple[list[dict], ...]:
    """목적: v3와 같은 순서의 시드 고정 생성. 인자: C/P/T·시드. 반환: 세 리스트. 예외: ValueError."""
    if not (1 <= c <= 999_988 and 1 <= p <= 999_999 and 1 <= t <= 9_999_989):
        raise ValueError("C/P/T는 양수이며 측정 ID 범위와 추가 등록 여유 안이어야 합니다")
    rnd = random.Random(seed)
    customers = [{"id": f"C{i:06d}", "name": f"고객{i}",
                  "gender": rnd.choice("여남"), "age": rnd.randint(10, 60)}
                 for i in range(1, c + 1)]
    products = []
    for i in range(1, p + 1):
        colors = rnd.sample(PALETTE, rnd.randint(2, 4))
        products.append({"id": f"P{i:06d}", "name": f"상품{i}",
                         "kind": rnd.choice(graph.KINDS), "style": rnd.choice(graph.STYLES),
                         "price": rnd.randint(1, 100) * 1000,
                         "stock": {color: rnd.randint(1, 5) for color in colors}})
    purchases = []
    for i in range(1, t + 1):
        product = (products[min(int(rnd.paretovariate(1.2)) - 1, p - 1)]
                   if rnd.random() < 0.5 else rnd.choice(products))
        purchases.append({"id": f"T{i:07d}", "customer_id": f"C{rnd.randint(1, c):06d}",
                          "product_id": product["id"], "color": rnd.choice(list(product["stock"])),
                          "qty": rnd.randint(1, 3),
                          "date": f"2026-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}"})
    return customers, products, purchases


def summarize(values: list[float], unit: str) -> dict:
    """목적: 표/JSON 공통 집계. 인자: 표본·단위. 반환: 통계. 예외: 빈 표본이면 StatisticsError."""
    return {"median": statistics.median(values), "max": max(values),
            "repeat": len(values), "unit": unit, "samples": values}


def measure(actions: list[Callable], keep_results: bool = False) -> tuple[dict, list]:
    """목적: 미리 정한 호출만 잼. 인자: 호출 목록·결과 보관. 반환: 통계/결과. 예외: 호출 예외 전파."""
    samples, results = [], []
    for action in actions:
        gc.collect()  # 준비/명시적 수집·결과 해제는 구간 밖, 호출 중 자동 GC는 기본값 유지
        start = time.perf_counter_ns()
        result = action()
        elapsed = (time.perf_counter_ns() - start) / 1_000_000
        samples.append(elapsed)
        if keep_results:
            results.append(result)
        del result  # 생성된 그래프의 해제 시간이 생성 시간에 섞이지 않는다
    return summarize(samples, "ms"), results


def require_integrity(g: graph.ShopGraph) -> None:
    """목적: 측정 밖 무결성 확인. 인자: 그래프. 반환: 없음. 예외: 위반 시 RuntimeError."""
    problems = g.check_integrity()
    if problems != []:
        raise RuntimeError(f"무결성 위반: {problems}")


def fingerprint(records: tuple[list[dict], ...]) -> str:
    """목적: 입력 동일성 기록. 인자: 세 리스트. 반환: SHA-256. 예외: 직렬화 오류 전파."""
    digest = hashlib.sha256()
    for rows in records:
        for row in rows:
            digest.update(json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()


def record_queries(g: graph.ShopGraph, cid: str, n: int, metrics: dict) -> dict:
    """목적: 같은 고객으로 읽기 측정. 인자: 그래프/고객/횟수/결과. 반환: 조건. 예외: 호출 예외 전파."""
    group_id = g.group_of(cid)
    for key, action in (("recommend_k3", partial(search.recommend, g, cid, 3)),
                        ("recommend_k10", partial(search.recommend, g, cid, 10)),
                        ("s4", partial(search.group_popular, g, group_id))):
        metrics[key], _ = measure([action] * n)
    items = search.recommend(g, cid, 10)
    return {"customer_id": cid, "gender": "여", "age": 25, "group_id": group_id,
            "group_members": len(g.members(group_id)), "s4_k": None,
            "k10_returned": len(items), "k10_scopes": [row["scope"] for row in items]}


def record_purchases(g: graph.ShopGraph, records: tuple, n: int, metrics: dict) -> dict:
    """목적: 구매 변경/단건 조회 측정. 인자: 그래프/입력/횟수/결과. 반환: 대상. 예외: 호출 예외 전파."""
    selected = records[2][:n]
    targets = []
    additions = Counter()
    for row in selected:
        edge = g.edge(row["customer_id"], row["product_id"])
        pair = (row["customer_id"], row["product_id"])
        targets.append({**row, "pair_records_before_add": edge["count"] + additions[pair]})
        additions[pair] += 1
    actions = [partial(g.add_purchase, row["customer_id"], row["product_id"],
                       row["color"], 1, "2026-10-01") for row in selected]
    metrics["add_purchase"], added = measure(actions, keep_results=True)
    require_integrity(g)
    metrics["update_purchase"], _ = measure([
        partial(g.update_purchase, tid, qty=2) for tid in added])
    require_integrity(g)
    metrics["get_purchase"], _ = measure([partial(g.get_purchase, tid) for tid in added])
    metrics["delete_purchase"], _ = measure([partial(g.delete_purchase, tid) for tid in added])
    require_integrity(g)
    return {"targets": targets, "added_ids": added, "updated_qty": 2,
            "sequence": "같은 대상의 등록→수정→단건 조회→추가분 삭제"}


def record_changes(g: graph.ShopGraph, records: tuple, n: int, metrics: dict) -> dict:
    """목적: 고객/재고/그룹 변경 측정. 인자: 그래프/입력/횟수/결과. 반환: 영향. 예외: 호출 예외 전파."""
    metrics["add_customer"], added = measure([
        partial(g.add_customer, f"추가{i}", "남", 30) for i in range(n)], keep_results=True)
    require_integrity(g)
    customers = records[0][:n]
    metrics["move_group"], _ = measure([
        partial(g.update_customer, row["id"], gender="남" if row["gender"] == "여" else "여")
        for row in customers])
    require_integrity(g)
    products = records[1][:n]
    metrics["update_stock"], _ = measure([
        partial(g.update_product, row["id"], stock={color: qty + 1 for color, qty in row["stock"].items()})
        for row in products])
    require_integrity(g)
    counts = Counter(row["customer_id"] for row in records[2])
    targets = [{"id": row["id"], "purchase_records": counts[row["id"]],
                "purchase_edges": sum(pid not in graph.GROUP_IDS for pid in g.neighbors(row["id"]))}
               for row in customers]
    metrics["delete_customer"], deleted = measure([
        partial(g.delete_customer, row["id"]) for row in targets], keep_results=True)
    if deleted != [row["purchase_records"] for row in targets]:
        raise RuntimeError("고객 삭제 영향 범위 불일치")
    require_integrity(g)
    return {"added_customer_ids": added, "delete_targets": targets,
            "group_moves": [{"id": row["id"], "from_gender": row["gender"],
                             "to_gender": "남" if row["gender"] == "여" else "여"} for row in customers],
            "stock_products": [row["id"] for row in products], "stock_change": "모든 기존 색상 +1"}


def record_stress(records: tuple, cid: str, n: int, metrics: dict) -> dict:
    """목적: 별도 입력의 품절/인기 삭제 측정. 인자: 입력/고객/횟수/결과. 반환: 조건. 예외: 호출 예외 전파."""
    customers, products, purchases = records
    new_customer = {"id": cid, "name": "신규", "gender": "여", "age": 25}
    sold_products = [{**row, "stock": {color: 0 for color in row["stock"]}} for row in products]
    sold_graph = graph.ShopGraph(customers + [new_customer], sold_products, purchases)
    metrics["sold_out_recommend"], results = measure(
        [partial(search.recommend, sold_graph, cid, 3)] * n, keep_results=True)
    if any(result != [] for result in results):
        raise RuntimeError("전부 품절 추천이 빈 리스트가 아닙니다")
    require_integrity(sold_graph)
    del sold_graph
    counts = Counter(row["product_id"] for row in purchases)
    pid = min(counts, key=lambda key: (-counts[key], key))
    samples, edge_count = [], 0
    for _ in range(n):
        g = graph.ShopGraph(*records)  # 같은 인기 상품·원본 상태, 준비는 측정 밖
        edge_count = len(g.neighbors(pid))
        metric, deleted = measure([partial(g.delete_product, pid)], keep_results=True)
        samples.extend(metric["samples"])
        if deleted != [counts[pid]]:
            raise RuntimeError("인기 상품 삭제 영향 범위 불일치")
        require_integrity(g)
        del g
    metrics["delete_popular_product"] = summarize(samples, "ms")
    return {"sold_out_k": 3, "sold_out_customer_id": cid, "sold_out_result": [],
            "popular_product_id": pid, "deleted_purchase_records": counts[pid],
            "deleted_purchase_edges": edge_count, "popular_delete_fresh_graph_each_sample": True}


def time_mode(c: int, p: int, t: int, seed: int, repeat: int | None) -> dict:
    """목적: 추적 없는 시간 측정. 인자: 규모/시드/반복 덮어쓰기. 반환: 결과. 예외: 측정 오류 전파."""
    records = make_records(c, p, t, seed)
    digest = fingerprint(records)
    n = min(repeat or 5, c, p, t)
    metrics = {}
    metrics["initialize"], _ = measure([partial(graph.ShopGraph, *records)] * (repeat or 3))
    g = graph.ShopGraph(*records)
    require_integrity(g)
    cid = g.add_customer("신규", "여", 25)  # K3/K10 동일 고객, 준비 비용 제외
    conditions = {"recommendation": record_queries(g, cid, n, metrics)}
    conditions["purchases"] = record_purchases(g, records, n, metrics)
    conditions["changes"] = record_changes(g, records, n, metrics)
    metrics["integrity"], results = measure([g.check_integrity] * (repeat or 3), keep_results=True)
    if any(result != [] for result in results):
        raise RuntimeError(f"무결성 위반: {results}")
    conditions["integrity_state"] = g.stats()
    del g
    gc.collect()
    conditions["stress"] = record_stress(records, cid, repeat or 3, metrics)
    return {"metrics": metrics, "conditions": conditions, "input_sha256": digest,
            "integrity_verified": True}


def max_rss_mib() -> float:
    """목적: RSS 단위 변환. 인자: 없음. 반환: MiB. 예외: 미지원 OS이면 RuntimeError."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return raw / (2 ** 20)  # macOS: bytes
    if sys.platform.startswith("linux"):
        return raw / 1024  # Linux: KiB
    raise RuntimeError("RSS는 macOS(바이트)·Linux(KiB)만 지원합니다")


def memory_mode(mode: str, c: int, p: int, t: int, seed: int) -> dict:
    """목적: 추적량 또는 일반 RSS 별도 측정. 인자: 모드/규모/시드. 반환: 결과. 예외: 측정 오류 전파."""
    metrics = {}
    gc.collect()
    if mode == "mem":
        tracemalloc.start()
    try:
        records = make_records(c, p, t, seed)
        if mode == "mem":
            metrics["input"] = summarize([tracemalloc.get_traced_memory()[0] / 1e6], "MB")
        else:
            metrics["after_input"] = summarize([max_rss_mib()], "MiB")
        g = graph.ShopGraph(*records)
        if mode == "rss":
            metrics["after_graph"] = summarize([max_rss_mib()], "MiB")
        del records
        gc.collect()
        if mode == "mem":
            current, peak = tracemalloc.get_traced_memory()
            metrics["retained"] = summarize([current / 1e6], "MB")
            metrics["initialization_peak"] = summarize([peak / 1e6], "MB")
            tracemalloc.reset_peak()
        require_integrity(g)
        if mode == "mem":
            metrics["integrity_peak"] = summarize([tracemalloc.get_traced_memory()[1] / 1e6], "MB")
        else:
            metrics["after_integrity"] = summarize([max_rss_mib()], "MiB")
    finally:
        if mode == "mem":
            tracemalloc.stop()
    return {"metrics": metrics, "integrity_verified": True}


def run_mode(mode: str, c: int, p: int, t: int, seed: int = 1, repeat: int | None = None) -> dict:
    """목적: 한 모드 실행/상수 복구. 인자: 모드/규모/시드/반복. 반환: 결과. 예외: 잘못된 인자 ValueError."""
    if mode not in ("time", "mem", "rss") or (repeat is not None and not 1 <= repeat <= 10):
        raise ValueError("모드는 time/mem/rss, --repeat은 1~10이어야 합니다")
    if tracemalloc.is_tracing():
        raise RuntimeError("이미 메모리 추적 중입니다. 모드마다 새 프로세스로 실행하세요")
    patterns, digits = graph._ID_PATTERNS, graph._ID_DIGITS
    with measurement_ids():
        result = (time_mode(c, p, t, seed, repeat) if mode == "time"
                  else memory_mode(mode, c, p, t, seed))
    return {"mode": mode, "size": {"customers": c, "products": p, "purchases": t},
            "seed": seed, "pid": os.getpid(), "verification": "Codex 자체 확인",
            "id_note": ID_NOTE, "tracing_enabled": mode == "mem",
            "id_constants_restored": graph._ID_PATTERNS is patterns and graph._ID_DIGITS is digits,
            **result}


def environment() -> dict:
    """목적: 실제 실행 환경 수집. 인자: 없음. 반환: 환경. 예외: 환경 명령 실패 전파."""
    root = pathlib.Path(__file__).resolve().parent.parent
    cpu = platform.processor()
    if sys.platform == "darwin":
        cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
    return {"os": platform.platform(), "macos": platform.mac_ver()[0], "cpu": cpu,
            "python": sys.version, "executable": sys.executable,
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip()}


def print_report(result: dict) -> None:
    """목적: JSON과 같은 통계의 표 출력. 인자: 결과. 반환: 없음. 예외: 출력 오류 전파."""
    print(f"Codex 자체 확인 | {result['mode']} | {result['size']} | seed={result['seed']}")
    print(result["id_note"])
    print("시간 ms / 추적 메모리 MB=10^6 바이트 / RSS MiB=2^20 바이트")
    print("RSS: macOS ru_maxrss=바이트, Linux=KiB. 누적 최댓값이며 객체 크기가 아님.")
    print("항목 | 중앙값 | 최댓값 | 반복 | 단위")
    print("--- | ---: | ---: | ---: | ---")
    for key, metric in result["metrics"].items():
        print(f"{LABELS[key]} | {metric['median']:.3f} | {metric['max']:.3f} | "
              f"{metric['repeat']} | {metric['unit']}")
    if "conditions" in result:
        print("측정 조건: " + json.dumps(result["conditions"], ensure_ascii=False, sort_keys=True))
    print(f"무결성 확인: {result['integrity_verified']}, ID 상수 복구: {result['id_constants_restored']}")
    print("전부 품절은 스트레스 사례. 웹 계층·브라우저 렌더링 미포함.")


def main(argv: list[str] | None = None) -> int:
    """목적: 단일 모드 CLI. 인자: 명령 인자 또는 None. 반환: 0. 예외: argparse/측정/파일 오류 전파."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("time", "mem", "rss"))
    parser.add_argument("c", nargs="?", type=int, default=10_000)
    parser.add_argument("p", nargs="?", type=int, default=1_000)
    parser.add_argument("t", nargs="?", type=int, default=300_000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--repeat", type=int, help="시간 모드의 모든 반복을 1~10회로 덮어쓰기(짧은 시험용)")
    parser.add_argument("--json", type=pathlib.Path, help="이번 실행 결과 JSON 경로(덮어쓰기)")
    args = parser.parse_args(argv)
    if args.repeat is not None and (not 1 <= args.repeat <= 10 or args.mode != "time"):
        if not (args.repeat == 1 and args.mode in ("mem", "rss")):
            parser.error("--repeat은 시간 모드 1~10회용입니다(mem/rss는 항상 1회)")
    env = environment()  # 자식 명령의 비용은 측정 전에, 추적을 켜기 전에 끝낸다
    started = datetime.now(timezone.utc).isoformat()
    result = run_mode(args.mode, args.c, args.p, args.t, args.seed, args.repeat)
    result.update({"environment": env, "started_utc": started,
                   "finished_utc": datetime.now(timezone.utc).isoformat(),
                   "argv": sys.argv if argv is None else argv})
    print_report(result)
    if args.json:
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

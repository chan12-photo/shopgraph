"""고장 검사(변형 검사) 실행 스크립트: 변형 패치를 하나씩 적용 → 테스트 → 복원한다.

개발용 검증 도구라 프로그램 실행 경로에 들어가지 않는다. 프로그램 모듈을 import하지 않는다.

- 변형: 같은 폴더의 *.patch (unified diff, 한 변형 = 한 파일의 한 곳). 설명은 manifest.json
- 실행 위치: 저장소 루트 안에 임시 git worktree(.wt_mutation, 기준 커밋 detached)를 만들고 그 안에서만 패치를 적용한다.
  작업 트리와 커밋은 건드리지 않고, 끝나면 worktree를 지운다
- 테스트: 시연 데이터(data.py)를 쓰는 tests/test_demo.py는 빼고 나머지 테스트 모듈만 돌린다
  (시연 기대값은 사람이 손계산하므로 시연 결과를 보지 않는다)
- 판정: 실패·오류가 1개 이상이면 "잡힘", 실행이 끝나지 않으면(중단·시간 초과) "잡힘(실행 중단)", 0개면 "못 잡음"

실행 (저장소 루트에서):
    python3 docs/verification/mutations/run_mutations.py            # 기준 = HEAD
    python3 docs/verification/mutations/run_mutations.py <커밋>     # 기준 커밋 지정
"""

import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
WORKTREE = REPO / ".wt_mutation"
TEST_MODULES = ["tests.test_graph", "tests.test_search", "tests.test_recommend", "tests.test_view", "tests.test_flow"]
TIMEOUT_SECONDS = 120


def _git(*args: str, cwd: pathlib.Path = REPO) -> str:
    """git 명령을 실행하고 표준 출력을 돌려준다.

    인자:
        *args: git 인자.
        cwd: 실행 위치.

    반환:
        표준 출력 문자열.

    예외:
        subprocess.CalledProcessError: git이 실패했을 때.
    """
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def _run_tests() -> tuple[str, list[str], str]:
    """임시 worktree에서 테스트를 돌리고 (요약 줄, 실패·오류 테스트 이름, 판정)을 돌려준다.

    인자:
        없음.

    반환:
        (unittest 요약 줄, 실패·오류 테스트 이름 정렬 리스트, "잡힘"·"잡힘(실행 중단)"·"못 잡음").

    예외:
        없음 (시간 초과는 판정으로 돌려준다).
    """
    try:
        result = subprocess.run([sys.executable, "-B", "-m", "unittest", *TEST_MODULES], cwd=WORKTREE,
                                capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return "시간 초과", [], "잡힘(실행 중단)"
    summary = re.search(r"^(OK.*|FAILED \(.*\))$", result.stderr, re.M)
    names = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+)", result.stderr, re.M)))
    if summary is None:
        last = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "출력 없음"
        return f"요약 없음: {last[:80]}", names, "잡힘(실행 중단)"
    return summary.group(1), names, "잡힘" if summary.group(1).startswith("FAILED") else "못 잡음"


def main() -> int:
    """기준 커밋에서 모든 변형을 차례로 적용·검사·복원하고 결과 표를 출력한다.

    인자:
        없음 (명령줄 첫 인자가 있으면 기준 커밋).

    반환:
        종료 코드 0. 기준 상태에서 테스트가 실패하면 변형 검사를 하지 않고 1.

    예외:
        subprocess.CalledProcessError: worktree 만들기·패치 적용·복원이 실패했을 때 (worktree는 지운다).
    """
    base = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    commit = _git("rev-parse", "--short", base).strip()
    _git("worktree", "add", "-q", "--detach", str(WORKTREE), commit)
    try:
        baseline, names, _ = _run_tests()
        print(f"기준 커밋 {commit}, 명령: python3 -B -m unittest {' '.join(TEST_MODULES)}")
        print(f"기준 상태: {baseline} {names}")
        if not baseline.startswith("OK"):
            return 1
        print("| 번호 | 파일 | 변형 | 결과 | 요약 | 실패·오류 테스트 |")
        print("|---|---|---|---|---|---|")
        caught = 0
        for mid in sorted(manifest):
            patch = HERE / f"{mid}.patch"
            _git("apply", str(patch), cwd=WORKTREE)
            try:
                summary, names, verdict = _run_tests()
            finally:
                _git("checkout", "--", ".", cwd=WORKTREE)
            caught += verdict.startswith("잡힘")
            info = manifest[mid]
            print(f"| {mid} | {info['file']} | {info['description']} | {verdict} | {summary} | {', '.join(names)} |")
        assert not _git("status", "--porcelain", cwd=WORKTREE).strip()
        print(f"\n총 {len(manifest)}종 중 {caught}종 잡힘, {len(manifest) - caught}종 못 잡음")
        return 0
    finally:
        _git("worktree", "remove", "--force", str(WORKTREE))


if __name__ == "__main__":
    sys.exit(main())

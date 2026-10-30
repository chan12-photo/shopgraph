"""테스트 전용 도우미. 내부 상태를 읽어 깊은 복사만 한다 (수정하지 않음)."""
import copy
def snapshot(g):
    return copy.deepcopy({"customers":g._customers,"products":g._products,"purchases":g._purchases,
                          "groups":g._groups,"adj":g._adj,"edges":g._edges,"next_ids":g._next_ids})

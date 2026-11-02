# 출처: Codex 2차 검토, bd93f79, 2026-11-02 (원본: /tmp/shopgraph_bd93f79_audit_f02im8mm/audit_screens.py, 아래 내용은 고치지 않음)
from pathlib import Path
from unittest import mock
from contextlib import redirect_stdout
import copy, io, json, re
import tests.test_demo as d
from tests.fixtures import make_graph
from search import recommend
from view import print_recommendation

ROOT=Path(__file__).resolve().parent
report={}

def capture(fn,*args):
    output=io.StringIO()
    with redirect_stdout(output):fn(*args)
    return output.getvalue()

def row(rank,pid,scope,score,buyers,supporters,colors):
    return dict(zip(['순위','상품 ID','범위','점수','구매자 수','지지자','구매 가능 색상'],[str(rank),pid,scope,str(score),str(buyers),supporters,colors]))

def rec_expected(rows,notes):
    return {'장면 2':{'추천 (C_new, K=3)':rows,'안내 줄':[{'안내':n,'있음/없음':v} for (n,_),v in zip(d._NOTES,notes)]}}

def check_rec(label,g,cid,expected,screen):
    try:d.TestW12Demo()._check_recommend(expected,'장면 2',g,cid,screen)
    except AssertionError:result='REJECTED'
    except Exception as exc:result='ERROR:'+type(exc).__name__
    else:result='ACCEPTED'
    report[label]=result;print(label+': '+result)

g=make_graph();cid=g.add_customer('고객7','여',22)
expected=rec_expected([row(1,'P02','같은 그룹',3,2,'C01, C02','베이지, 블랙'),row(2,'P01','같은 그룹',3,1,'C01','그레이, 네이비, 블랙, 화이트'),row(3,'P03','같은 그룹',2,2,'C02, C03','아이보리')],['없음']*3)
screen=capture(print_recommendation,g,cid,recommend(g,cid,3),3)
check_rec('normal_recommendation',g,cid,expected,screen)
lines=screen.splitlines()
first=next(i for i,x in enumerate(lines) if d._REC_ITEM.match(x))
for label,changed in [
 ('bare_supporter_without_reason_label',lines[:first+1]+['C01, C02']+lines[first+2:]),
 ('bare_color_without_label',lines[:first+2]+['베이지, 블랙']+lines[first+3:]),
 ('wrong_color_count_reason',[x.replace('2가지 색상','999가지 색상') for x in lines]),
 ('extra_malformed_item',lines+[' 4. 거짓상품 (P04) - 점수 -1, 구매 고객 1명 [전체 고객]','    근거: C04가 구매','    구매 가능 색상: 블랙']),
 ('duplicate_reason_after_items',lines+['    근거: C99가 구매']),
 ('wrong_header_count',[x.replace('님께 추천 (3개)','님께 추천 (4개)') for x in lines]),
 ('missing_item',lines[:first]+lines[first+3:]),
 ('duplicate_well_formed_item',lines+lines[first:first+3]),
 ('swapped_item_order',lines[:first]+lines[first+3:first+6]+lines[first:first+3]+lines[first+6:]),
 ('wrong_stock_color',[x.replace('구매 가능 색상: 베이지, 블랙','구매 가능 색상: 레드') for x in lines]),
]:check_rec(label,g,cid,expected,'\n'.join(changed)+'\n')

g=make_graph();cid='C02'
expected=rec_expected([row(1,'P01','같은 그룹',3,1,'C01','그레이, 네이비, 블랙, 화이트'),row(2,'P04','전체 고객',1,1,'C04','블랙, 카키')],['있음']*3)
screen=capture(print_recommendation,g,cid,recommend(g,cid,3),3)
check_rec('normal_short_recommendation',g,cid,expected,screen)
notes=[x for x in screen.splitlines() if x.startswith(' ※')]
check_rec('duplicated_notes',g,cid,expected,screen+'\n'.join(notes)+'\n')
check_rec('wrong_insufficient_count_note',g,cid,expected,screen.replace('상품이 2개뿐이라 3개를 채우지 못함','상품이 999개뿐이라 888개를 채우지 못함'))
check_rec('wrong_score_note',g,cid,expected,re.sub(r' ※ 점수는 각 범위 안에서.*',' ※ 점수는 각 범위 안에서 비교하지 말고 모두 더하세요',screen))
check_rec('missing_required_note',g,cid,expected,screen.replace(notes[0]+'\n',''))

# Scene 8 checking logic only: no real _run_scenes, no main.run, fixture graph only.
STATS=[['그룹 노드','8'],['고객 노드','6'],['상품 노드','5'],['소속 간선','6'],['구매 간선','9'],['구매 기록','13']]
def statistics_screen(rows,header='항목  개수',ending=''):
    return '[그래프 통계]\n'+header+'\n----  ----\n'+'\n'.join('  '.join(x) for x in rows)+'\n\n[무결성 검사] 위반 없음: 원본과 그래프가 일치함을 확인\n'+ending

def check_stats(label,rows,screen):
    expected={'장면 8':{'통계 표':[{'항목':name,'개수':value} for name,value in rows],'무결성 검사':[{'항목':'위반 수','값':'0'}]}}
    with mock.patch.object(d,'_load_expected',return_value=expected),mock.patch.object(d,'_require_through'),mock.patch.object(d,'_run_scenes',return_value=(screen,make_graph())):
        try:d.TestW12Demo().test_scene8_integrity()
        except AssertionError:result='REJECTED'
        except Exception as exc:result='ERROR:'+type(exc).__name__
        else:result='ACCEPTED'
    report[label]=result;print(label+': '+result)
check_stats('normal_stats',STATS,statistics_screen(STATS))
check_stats('wrong_stats_header',STATS,statistics_screen(STATS,header='전혀 다른 열  잘못된 단위'))
check_stats('extra_stats_row_after_blank',STATS,statistics_screen(STATS,ending='그룹 노드  999\n'))
check_stats('duplicate_integrity_verdict',STATS,statistics_screen(STATS,ending='[무결성 검사] 위반 없음: 원본과 그래프가 일치함을 확인\n'))
check_stats('contradictory_integrity_verdict',STATS,statistics_screen(STATS,ending='[무결성 검사] 위반 9건\n'))
subset=[x for x in STATS if x[0]!='상품 노드']
check_stats('missing_stat_in_expected_and_screen',subset,statistics_screen(subset))
check_stats('missing_stat_in_screen_only',STATS,statistics_screen(subset))
wrong=copy.deepcopy(STATS);wrong[2][1]='999'
check_stats('wrong_stat_number',STATS,statistics_screen(wrong))
(ROOT/'screen_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))

# 출처: Codex 2차 검토, bd93f79, 2026-11-02 (원본: /tmp/shopgraph_bd93f79_audit_f02im8mm/audit_guards.py, 아래 내용은 고치지 않음)
from pathlib import Path
from unittest import mock
from contextlib import redirect_stdout
import copy, io, json
import tests.test_demo as d

ROOT=Path(__file__).resolve().parent
TEMPLATE=(ROOT/'docs/demo_expected.md').read_text()
APPROVED='상태: 승인 (찬일, 2026-11-02) / AI 독립 계산 대조: 일치'
FIXED={'C_new':'C07','C_new7':'C08','P_top':'P01','P_top6':'P02','장면 3 색상 1':'블랙','장면 3 색상 2':'화이트'}
PATH=ROOT/'fake_expected.md'
METHODS=sorted(name for name in dir(d.TestW12Demo) if name.startswith('test_scene'))
class ReachedExecution(Exception): pass

def filled_template():
    out=[]; blanks=[]; section=table=''; header=[]
    for line in TEMPLATE.splitlines():
        if line.startswith('상태:'): line=APPROVED
        if line.startswith('## '): section=line[3:].split('.')[0].strip();table='';header=[]
        elif line.startswith('### '):table=line[4:].strip();header=[]
        elif line.startswith('|'):
            cells=[x.strip() for x in line.strip().strip('|').split('|')]
            if not header:header=cells
            elif not all(x and set(x)<={'-'} for x in cells):
                for i,value in enumerate(cells):
                    if value:continue
                    key=header[i]
                    if key=='값':
                        value=FIXED.get(cells[0], '0' if cells[0]=='위반 수' else 'G-M-10' if 'C_new7' in cells[0] else 'G-F-20')
                    else:value={'상품 ID':'P01','범위':'같은 그룹','지지자':'C01','구매 가능 색상':'블랙','구매 색상':'블랙','최근 구매일':'2026-10-31','상태':'판매 중','있음/없음':'없음'}.get(key,'1')
                    blanks.append((len(out),i,section,table,cells[0]))
                    cells[i]=value
                line='| '+' | '.join(cells)+' |'
        out.append(line)
    return '\n'.join(out)+'\n',blanks
BASE,BLANKS=filled_template()

def change_cell(text, section, table, column, value, first_key=None):
    lines=text.splitlines(); sec=tab='';header=[]
    for n,line in enumerate(lines):
        if line.startswith('## '):sec=line[3:].split('.')[0].strip();tab='';header=[]
        elif line.startswith('### '):tab=line[4:].strip();header=[]
        elif line.startswith('|'):
            cells=[x.strip() for x in line.strip().strip('|').split('|')]
            if not header:header=cells;continue
            if all(x and set(x)<={'-'} for x in cells):continue
            if sec==section and tab==table and (first_key is None or cells[0]==first_key):
                cells[header.index(column)]=value
                lines[n]='| '+' | '.join(cells)+' |'
                return '\n'.join(lines)+'\n'
    raise AssertionError((section,table,column))

def outcome(text,last=8):
    PATH.write_text(text)
    output=io.StringIO()
    with mock.patch.object(d,'_EXPECTED_PATH',PATH), mock.patch.object(d,'_run_scenes',side_effect=ReachedExecution), redirect_stdout(output):
        try:getattr(d.TestW12Demo(),METHODS[last-1])()
        except ReachedExecution:return 'EXECUTION_BOUNDARY_REACHED'
        except NotImplementedError:return 'BLOCKED'
        except Exception as e:return 'OTHER_ERROR:'+type(e).__name__
    return 'RETURNED_WITHOUT_EXECUTION'

cases={
 'filled_fake_baseline':BASE,
 'missing_approval':BASE.replace(APPROVED,'상태: 손계산 전'),
 'invalid_approval_date':BASE.replace('2026-11-02','2026-02-30',1),
 'blank_required_score':change_cell(BASE,'장면 2','추천 (C_new, K=3)','점수',''),
 'invalid_score':change_cell(BASE,'장면 2','추천 (C_new, K=3)','점수','abc'),
 'missing_score_column':BASE.replace('| 점수 |','| 점쑤 |'),
 'duplicate_score_header':BASE.replace('| 구매자 수 |','| 점수 |'),
 'bad_fixed_customer_id':change_cell(BASE,'확정값','확정값','값','not-an-id','C_new'),
 'bad_group_id':change_cell(BASE,'장면 1','그룹별 인원','그룹 ID','G-X-999'),
 'bad_last_date':change_cell(BASE,'장면 3','S1 (C_new)','최근 구매일','2026-02-30'),
 'bad_supporter_id':change_cell(BASE,'장면 2','추천 (C_new, K=3)','지지자','not-an-id'),
 'zero_rank':change_cell(BASE,'장면 2','추천 (C_new, K=3)','순위','0'),
 'dash_note':change_cell(BASE,'장면 2','안내 줄','있음/없음','-','넓힘 안내'),
 'duplicate_note_row_with_blank':BASE.replace('| 넓힘 안내 | 없음 |','| 넓힘 안내 | - |\n| 넓힘 안내 | 없음 |',1),
 'delete_stat_row':BASE.replace('| 상품 노드 | 1 |\n',''),
 'duplicate_stat_row':BASE.replace('| 상품 노드 | 1 |','| 상품 노드 | 1 |\n| 상품 노드 | 1 |'),
 'blank_overwritten_by_duplicate_header':change_cell(BASE.replace('| 구매자 수 |','| 점수 |'),'장면 2','추천 (C_new, K=3)','점수',''),
}
report={name:outcome(text) for name,text in cases.items()}
for name,result in report.items():print(name+': '+result)
# Fixed-ID row values are used by position. Swapped headers must be rejected, but are not.
reordered=BASE.replace('| 이름 | 값 | 정하는 근거 |','| 이름 | 정하는 근거 | 값 |')
report['reordered_fixed_headers']=outcome(reordered)
print('reordered_fixed_headers:',report['reordered_fixed_headers'])
# Duplicate section overwrites the earlier section (including its blank cell).
start=BASE.index('## 장면 2.');end=BASE.index('## 장면 3.')
section=BASE[start:end]
bad_section=change_cell(BASE,'장면 2','추천 (C_new, K=3)','점수','')[start:end-1]
duplicate=BASE[:start]+bad_section+'\n'+section+BASE[end:]
report['duplicate_section_hides_blank']=outcome(duplicate)
print('duplicate_section_hides_blank:',report['duplicate_section_hides_blank'])
# All originally blank required cells, one at a time, for each dependent scene.
blocked=total=0; failures=[]
for last in range(1,9):
    needed={k for n in range(1,last+1) for k in d._FIXED_BY_SCENE.get(n,())}
    for line_index,column,section,table,key in BLANKS:
        if not ((section.startswith('장면 ') and int(section.split()[1])<=last) or (section=='확정값' and key in needed)):continue
        lines=BASE.splitlines();cells=[x.strip() for x in lines[line_index].strip().strip('|').split('|')];cells[column]=''
        lines[line_index]='| '+' | '.join(cells)+' |'
        result=outcome('\n'.join(lines)+'\n',last)
        total+=1;blocked+=result=='BLOCKED'
        if result!='BLOCKED':failures.append([last,line_index+1,column,result])
print('single_blank_sweep:',total,'blocked:',blocked,'unexpected:',len(failures))
report['single_blank_sweep']={'total':total,'blocked':blocked,'unexpected':failures}
report['scene1_with_future_blank']=outcome(change_cell(BASE,'장면 8','통계 표','개수',''),1)
print('scene1_with_future_blank:',report['scene1_with_future_blank'])
(ROOT/'guard_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
PATH.write_text(BASE)
status_cases={
 'unapproved':BASE.replace(APPROVED,'상태: 손계산 전'),
 'missing_match_word':BASE.replace(' / AI 독립 계산 대조: 일치',''),
 'bad_date_shape':BASE.replace('2026-11-02','2026-1-2',1),
 'impossible_date':BASE.replace('2026-11-02','2026-02-30',1),
 'wrong_approver':BASE.replace('승인 (찬일,','승인 (다른사람,',1),
 'extra_suffix':BASE.replace(APPROVED,APPROVED+' 추가'),
 'missing_status':BASE.replace(APPROVED+'\n',''),
}
for name,text in status_cases.items():
    results=[outcome(text,last) for last in range(1,9)]
    assert results==['BLOCKED']*8,(name,results)
print('approval_invalid_matrix:',len(status_cases)*8,'blocked')
assert [outcome(BASE,last) for last in range(1,9)]==['EXECUTION_BOUNDARY_REACHED']*8
print('approved_fake_baseline: all 8 reach mock execution only')

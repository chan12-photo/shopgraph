// UI5 실제 화면 시연. Node 내장 API만 사용하며 Python 운영 진입점을 실행한다.
import assert from 'node:assert/strict';
import { spawn, execFileSync } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, mkdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
// 승인과 8장면 전체 양식을 먼저 검사한다. 그 전에는 서버·브라우저를 만들지 않는다.
const expected = JSON.parse(execFileSync('python3', ['-B', '-c',
  'import json; from tests.demo_expected_adapter import browser_expected; print(json.dumps(browser_expected(),ensure_ascii=False))'], {cwd:repo, encoding:'utf8'}));
const out = join(repo, 'docs/verification/ui5_screens');
await mkdir(out, {recursive:true});
const profile = await mkdtemp(join(tmpdir(), 'shopgraph-ui5-chrome-'));
const report = {scenes:[], external:[], exceptions:[]};
const server = spawn('python3', ['-u', '-B', 'main.py', '--web', '--port', '0'], {
  cwd:repo, env:{...process.env, BROWSER:'/usr/bin/true'},
});
let chrome, socket;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
try {
  const base = await new Promise((resolve, reject) => {
    let output='';
    server.stdout.on('data', data=>{output+=data;const match=output.match(/http:\/\/127\.0\.0\.1:\d+/);if(match)resolve(match[0]);});
    server.once('exit', code=>reject(new Error(`main.py exit ${code}`)));
  });
  chrome = spawn(process.env.CHROME_BIN ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', [
    '--headless=new','--disable-gpu','--disable-extensions','--no-first-run','--no-default-browser-check',
    '--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank',
  ]);
  const browserUrl = await new Promise((resolve,reject)=>{
    let text='';chrome.stderr.on('data', data=>{text+=data;const found=text.match(/DevTools listening on (ws:\/\/[^\s]+)/);if(found)resolve(found[1]);});
    chrome.once('exit', code=>reject(new Error(`Chrome exit ${code}`)));
  });
  const debugBase=browserUrl.replace('ws:','http:').split('/devtools/')[0];
  const pages=await (await fetch(debugBase+'/json/list')).json();
  socket=new WebSocket(pages.find(page=>page.type==='page').webSocketDebuggerUrl);
  await once(socket,'open');
  let counter=0;
  const pending=new Map();
  const command=(method,params={})=>new Promise((resolve,reject)=>{
    const id=++counter;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));
  });
  socket.onmessage=event=>{
    const message=JSON.parse(event.data);
    if(message.id){const task=pending.get(message.id);pending.delete(message.id);message.error?task.reject(message.error):task.resolve(message.result);}
    else if(message.method==='Runtime.exceptionThrown')report.exceptions.push(message.params);
    else if(message.method==='Network.requestWillBeSent'){
      const url=message.params.request.url;
      if(/^https?:/.test(url)&&new URL(url).hostname!=='127.0.0.1')report.external.push(url);
    } else if(message.method==='Fetch.requestPaused'){
      const {requestId,request}=message.params;
      const local=new URL(request.url).hostname==='127.0.0.1';
      command(local?'Fetch.continueRequest':'Fetch.failRequest',local?{requestId}:{requestId,errorReason:'BlockedByClient'})
        .catch(reason=>report.exceptions.push(reason));
    }
  };
  const evaluate=async expression=>{
    const answer=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});
    if(answer.exceptionDetails)throw new Error(JSON.stringify(answer.exceptionDetails));
    return answer.result.value;
  };
  const until=async expression=>{
    for(let i=0;i<150;i++){if(await evaluate(`Boolean(${expression})`))return;await delay(100);}
    throw new Error(`화면 대기 실패: ${expression}`);
  };
  const tab=async name=>{await evaluate(`[...document.querySelectorAll('nav button')].find(n=>n.textContent.trim()===${JSON.stringify(name)}).click()`);await delay(100);};
  const click=async name=>{await evaluate(`(()=>{const n=[...document.querySelectorAll('button')].find(n=>n.textContent.trim()===${JSON.stringify(name)});if(!n)throw Error('버튼 없음');n.click();})()`);await delay(50);};
  const field=async(formIndex,label,value)=>{
    await evaluate(`(()=>{const form=document.querySelectorAll('main form')[${formIndex}];
      const n=[...form.querySelectorAll('label')].find(l=>l.firstChild.textContent.trim()===${JSON.stringify(label)}).querySelector('input,select');
      Object.getOwnPropertyDescriptor(n.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype,'value').set.call(n,${JSON.stringify(value)});
      n.dispatchEvent(new Event(n.tagName==='SELECT'?'change':'input',{bubbles:true}));})()`);
  };
  const capture=async(name,scene,checks,fullPage=true)=>{
    const metrics=await command('Page.getLayoutMetrics');
    const shot=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:fullPage,
      ...(fullPage?{clip:{x:0,y:0,width:1440,height:metrics.cssContentSize.height,scale:1}}:{})});
    await writeFile(join(out,name),Buffer.from(shot.data,'base64'));
    report.scenes.push({scene,file:name,result:'일치',checks});console.log(`PASS 장면 ${scene}: ${name} / ${checks}`);
  };
  async function checkRecommendation(wanted){
    await until(`document.querySelectorAll('.recommendation-card').length>0`);
    const actual=await evaluate(String.raw`[...document.querySelectorAll('.recommendation-card')].map(card=>{
      const p=[...card.querySelectorAll('p')];const score=card.querySelector('.score-summary').textContent.match(/점수 (\d+) · 구매 고객 (\d+)명/);
      const proof=card.querySelector('.supporter-line').textContent;const note=proof.match(/ \((C[0-9]{2}[은는] .+) 색상 구매\)$/);
      return {product_id:card.querySelector('strong').textContent.match(/\((P[0-9]{2})\)/)[1],
        scope_label:card.querySelector('.scope-badge').textContent,score:Number(score[1]),buyers:Number(score[2]),
        supporters:proof.split(' 구매')[0].match(/C[0-9]{2}/g),
        available_colors:p.find(n=>n.textContent.trim().startsWith('구매 가능 색상:')).textContent.trim().replace('구매 가능 색상: ','').split(', '),
        color_note:note?note[1]:'-'};})`);
    const {items,notices}=wanted;
    assert.deepEqual(actual,items.map(({scope,...fields})=>fields));
    const lines=await evaluate(`[...document.querySelectorAll('.notice-box p')].map(n=>n.textContent)`);
    const flags={'넓힘 안내':lines.some(l=>l.includes(' ※ 같은 그룹(')), '개수 부족 안내':lines.some(l=>l.includes('개를 채우지 못함')), '점수 비교 안내':lines.some(l=>l.includes(' ※ 점수는 각 범위 안에서'))};
    assert.deepEqual(flags,notices);
    const full=notices['넓힘 안내']?[" ※ 같은 그룹(남성·10대)에 다른 고객이 없어 '남성 전체'로 넓혀 찾음"]:[];
    assert.deepEqual(lines,full);
  }
  async function checkS4(index,wanted){
    const rows=await evaluate(String.raw`[...document.querySelectorAll('.bar-chart')[${index}].querySelectorAll('.popular-list li')].map(n=>{
      const m=n.textContent.match(/(P[0-9]{2}) · 점수 (\d+) · 구매자 (\d+)명 · (판매 중|품절)/);
      return {product_id:m[1],score:Number(m[2]),buyers:Number(m[3]),status_label:m[4]};})`);
    assert.deepEqual(rows,wanted.map(({sold_out,...fields})=>fields));
  }
  async function buy(customer,product,color,date,weight){
    await tab('등록·구매');await field(1,'고객',customer);await field(1,'상품',product);
    await until(`!document.querySelectorAll('form')[1].querySelectorAll('select')[2].disabled`);
    await field(1,'색상',color);await field(1,'수량','1');await field(1,'구매일',date);
    await click('구매 등록');await until(`document.querySelector('.success-box') && !document.querySelectorAll('form')[1].querySelector('button').disabled`);
    const message=await evaluate(`document.querySelector('.success-box').textContent`);
    assert(message.endsWith(`구매 등록 · 가중치 ${weight}`),message);
  }
  async function register(name,gender,age,id){
    await tab('등록·구매');await field(0,'이름',name);await field(0,'성별',gender);await field(0,'나이',String(age));
    await click('등록 후 고객 상세 보기');await until(`document.querySelector('.panel h3')?.textContent===${JSON.stringify(`${name} (${id})`)} && document.querySelector('.recommendation-card')`);
  }
  await command('Page.enable');await command('Runtime.enable');await command('Network.enable');
  await command('Fetch.enable',{patterns:[{urlPattern:'http://*'},{urlPattern:'https://*'}]});
  await command('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
  report.browser=(await command('Browser.getVersion')).product;
  report.entry='python3 -B main.py --web --port 0';report.viewport=[1440,900];
  await command('Page.navigate',{url:base});
  await until(`document.querySelectorAll('[data-group-count]').length===8`);
  assert.deepEqual(await evaluate(`Object.fromEntries([...document.querySelectorAll('[data-group-count]')].map(n=>[n.dataset.nodeId,Number(n.dataset.groupCount)]))`),expected.groups);
  await capture('01_groups.png',1,'그룹 8개 인원 전체',false);

  const fixed=expected.fixed;
  await register('하람','여',25,fixed.C_new);await checkRecommendation(expected.recommendations['2']);
  await capture('02_registered_recommendation.png',2,'C_new ID·추천 3항목 전체·안내 없음');
  for(const [i,key,date] of [[0,'장면 3 색상 1','2026-10-30'],[1,'장면 3 색상 2','2026-10-31']]){
    await buy(fixed.C_new,fixed.P_top,fixed[key],date,expected.purchase_weights_3[i]);
  }
  await tab('고객 상세');await until(`document.querySelector('.purchase-meta')`);
  assert.deepEqual(await evaluate(`[...document.querySelectorAll('.purchase-meta')].map(n=>n.textContent)`),expected.s1.map(row=>`가중치 ${row.weight} · ${row.colors.join(', ')}`));
  await capture('03a_purchase_s1.png',3,'구매 가중치 1→2·S1 색상/가중치');
  await tab('그래프');await until(`document.querySelector('[data-node-id="${fixed.C_new}"]')`);
  await evaluate(`document.querySelector('[data-node-id="${fixed.C_new}"]').dispatchEvent(new MouseEvent('click',{bubbles:true}))`);
  assert((await evaluate(`document.querySelector('.neighbor-summary').textContent`)).includes(`가중치 ${expected.s1[0].weight}`));
  await capture('03b_graph_weight2.png',3,'선택 정보 이웃 이름·관계·가중치 2',false);

  await tab('고객 상세');await checkRecommendation(expected.recommendations['4']);
  await capture('04_recommend_again.png',4,'기구매 P_top 제외·추천 전체');
  await tab('그룹 인기');await until(`document.querySelector('.popular-list') && !document.querySelector('.comparison-actions button').disabled`);
  await checkS4(0,expected.popular_before);await click("지금을 '전'으로 고정");
  await capture('05a_popular_before.png',5,'S4 구매 전 9항목·점수·구매자·상태');
  for(const [i,color,date] of [[0,'블랙','2026-10-30'],[1,'그레이','2026-10-30'],[2,'네이비','2026-10-31']]){
    await buy('C09','P07',color,date,expected.purchase_weights_5[i]);
  }
  await tab('그룹 인기');await until(`document.querySelectorAll('.bar-chart').length===2 && !document.querySelector('.comparison-actions button').disabled`);
  await checkS4(0,expected.popular_before);await checkS4(1,expected.popular_after);
  await capture('05b_popular_after.png',5,'S4 전 고정·구매 후 9항목·순위 변화');

  await tab('고객 상세');await checkRecommendation(expected.before_stock);
  await capture('06a_before_stock.png',6,'품절 전 P_top6 1위·색상 수 안내 포함 추천 전체');
  await evaluate(`document.querySelector('.recommendation-card button').click()`);
  await until(`document.querySelector('form h3')?.textContent==='재고 수정'`);
  await evaluate(`document.querySelectorAll('form input').forEach(n=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(n,'0');n.dispatchEvent(new Event('input',{bubbles:true}));})`);
  await click('색상별 재고 전체 저장');await until(`document.querySelector('.success-box button') && document.querySelector('.status-pill')?.textContent==='품절'`);
  assert(await evaluate(`Object.values(Object.fromEntries([...document.querySelectorAll('form label')].map(l=>[l.firstChild.textContent,l.querySelector('input').value]))).every(v=>v==='0')`));
  await capture('06b_zero_stock.png',6,'모든 기존 색상 재고 0·품절·C_new 추천 복귀 버튼');
  await evaluate(`document.querySelector('.success-box button').click()`);await checkRecommendation(expected.recommendations['6']);
  await capture('06c_after_stock.png',6,'품절 후 P_top6 제외·다음 후보 포함 추천 전체');

  await register('새싹','남',15,fixed.C_new7);await checkRecommendation(expected.recommendations['7']);
  await capture('07_widen_gender.png',7,'남성 전체 3항목·점수/지지자/색상·넓힘 안내 원문');
  await tab('무결성');await until(`document.querySelectorAll('.stat-card').length===6 && document.querySelector('.integrity-good')`);
  assert.deepEqual(await evaluate(`Object.fromEntries([...document.querySelectorAll('.stat-card')].map(n=>[n.querySelector('span').textContent,Number(n.querySelector('strong').textContent)]))`),expected.stats);
  assert.equal(await evaluate(`document.querySelector('.integrity-good h3').textContent`),expected.violations===0?'위반 없음':`위반 ${expected.violations}건`);
  await capture('08_integrity.png',8,'통계 6항목·위반 수');
  assert.deepEqual(report.external,[]);assert.deepEqual(report.exceptions,[]);
  console.log('PASS 장면 1~8 전체 대조 / 외부 네트워크 0 / 브라우저 예외 0');
  await writeFile(join(repo,'docs/verification/ui5_browser_results.json'),JSON.stringify(report,null,2)+'\n');
} finally {
  if(socket)socket.close();
  if(chrome)chrome.kill('SIGTERM');
  server.kill('SIGINT');
}

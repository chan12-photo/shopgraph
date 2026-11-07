// UI9b 화면 결함 확인. Node 내장 API만 쓰고 실제 python3 main.py --web과 Chrome을 CDP로 조작한다.
// 실패하면 종료 코드 1이다. 항목별 결과를 모두 찍어 고장 주입에서 어느 검사가 잡았는지 보이게 한다.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const profile = await mkdtemp(join(tmpdir(), 'shopgraph-ui9b-chrome-'));
const delay = ms => new Promise(done => setTimeout(done, ms));
const server = spawn('python3', ['-u', '-B', 'main.py', '--web', '--port', '0'], {
  cwd:repo, env:{...process.env, BROWSER:'/usr/bin/true'},
});
let chrome, socket;
const failures = [], external = [], exceptions = [], posts = [];
const holds = [];  // {pattern, method, paused, arrived}

try {
  const base = await new Promise((done, fail) => {
    let output = '';
    server.stdout.on('data', data => {output += data; const m = output.match(/http:\/\/127\.0\.0\.1:\d+/); if (m) done(m[0]);});
    server.once('exit', code => fail(new Error(`main.py exit ${code}`)));
  });
  chrome = spawn(process.env.CHROME_BIN ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', [
    '--headless=new', '--disable-gpu', '--disable-extensions', '--no-first-run', '--no-default-browser-check',
    '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank',
  ]);
  const browserUrl = await new Promise((done, fail) => {
    let text = '';
    chrome.stderr.on('data', data => {text += data; const m = text.match(/DevTools listening on (ws:\/\/[^\s]+)/); if (m) done(m[1]);});
    chrome.once('exit', code => fail(new Error(`Chrome exit ${code}`)));
  });
  const pages = await (await fetch(browserUrl.replace('ws:', 'http:').split('/devtools/')[0] + '/json/list')).json();
  socket = new WebSocket(pages.find(page => page.type === 'page').webSocketDebuggerUrl);
  await once(socket, 'open');
  let counter = 0;
  const pending = new Map();
  const command = (method, params = {}) => new Promise((done, fail) => {
    const id = ++counter; pending.set(id, {done, fail}); socket.send(JSON.stringify({id, method, params}));
  });
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const task = pending.get(message.id); pending.delete(message.id);
      message.error ? task.fail(message.error) : task.done(message.result);
    } else if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params);
    else if (message.method === 'Network.requestWillBeSent') {
      const {url, method, postData} = message.params.request;
      if (/^https?:/.test(url) && new URL(url).hostname !== '127.0.0.1') external.push(url);
      if (method !== 'GET') posts.push({url:new URL(url).pathname, method, body:postData ? JSON.parse(postData) : null});
    } else if (message.method === 'Fetch.requestPaused') {
      const {requestId, request, responseStatusCode} = message.params;
      const url = new URL(request.url);
      if (url.hostname !== '127.0.0.1') {command('Fetch.failRequest', {requestId, errorReason:'BlockedByClient'}); return;}
      const hold = responseStatusCode !== undefined
        && holds.find(h => !h.paused && h.method === request.method && h.path === url.pathname);
      if (hold) {hold.paused = requestId; hold.arrived(); return;}
      command('Fetch.continueRequest', {requestId}).catch(reason => exceptions.push(reason));
    }
  };
  const evaluate = async expression => {
    const answer = await command('Runtime.evaluate', {expression, returnByValue:true, awaitPromise:true, userGesture:true});
    if (answer.exceptionDetails) throw new Error(JSON.stringify(answer.exceptionDetails));
    return answer.result.value;
  };
  const until = async expression => {
    for (let i = 0; i < 50; i++) {if (await evaluate(`Boolean(${expression})`)) return; await delay(100);}
    throw new Error(`화면 대기 실패: ${expression}`);
  };
  const get = async path => await (await fetch(base + path)).json();
  const tab = async name => {await evaluate(`[...document.querySelectorAll('nav button')].find(n=>n.textContent.trim()===${JSON.stringify(name)}).click()`); await delay(100);};
  const click = async name => {await evaluate(`(()=>{const n=[...document.querySelectorAll('button')].find(n=>n.textContent.trim()===${JSON.stringify(name)});if(!n)throw Error('버튼 없음: '+${JSON.stringify(name)});n.click();})()`); await delay(100);};
  const field = async (form, label, value) => evaluate(`(()=>{const f=document.querySelectorAll('main form')[${form}];
    const n=[...f.querySelectorAll('label')].find(l=>l.firstChild.textContent.trim()===${JSON.stringify(label)}).querySelector('input,select');
    Object.getOwnPropertyDescriptor(n.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype,'value').set.call(n,${JSON.stringify(value)});
    n.dispatchEvent(new Event(n.tagName==='SELECT'?'change':'input',{bubbles:true}));})()`);
  const realClick = async (x, y) => {
    for (const type of ['mousePressed', 'mouseReleased']) await command('Input.dispatchMouseEvent', {type, x, y, button:'left', clickCount:1});
    await delay(50);
  };
  const hold = (method, path) => {
    const entry = {method, path, paused:null}; entry.reached = new Promise(done => {entry.arrived = done;});
    holds.push(entry); return entry;
  };
  const release = async entry => {await command('Fetch.continueRequest', {requestId:entry.paused}); await delay(400);};
  const home = async () => {await command('Page.navigate', {url:base}); await until(`document.querySelectorAll('[data-group-count]').length===8`);};
  const check = async (name, body) => {
    try {await body(); console.log(`PASS ${name}`);}
    catch (error) {failures.push(name); console.log(`FAIL ${name}: ${String(error.message ?? error).split('\n').slice(0, 6).join(' ')}`);}
  };
  const purchaseReady = `document.querySelectorAll('main form')[1] && !document.querySelectorAll('main form')[1].querySelector('button').disabled`;

  await command('Page.enable'); await command('Runtime.enable'); await command('Network.enable');
  await command('Fetch.enable', {patterns:[{urlPattern:'*', requestStage:'Request'}, {urlPattern:'*/api/*', requestStage:'Response'}]});
  await command('Emulation.setDeviceMetricsOverride', {width:1440, height:900, deviceScaleFactor:1, mobile:false});
  await home();

  await check('4번 수량 입력 3종과 수량 2 전송', async () => {
    await tab('등록·구매'); await until(purchaseReady);
    const stats = async () => (await get('/api/stats')).stats.purchases;
    for (const bad of ['1.0000000000000001', '1e0']) {
      const before = await stats(), sent = posts.length;
      await field(1, '수량', bad); await click('구매 등록'); await delay(200);
      assert.equal(posts.length, sent, `${bad}: 요청 전송`);
      assert.equal(await stats(), before, `${bad}: 구매 저장`);
      const text = await evaluate(`document.querySelector('.error-box')?.textContent ?? ''`);
      assert.ok(text.startsWith('수량: 숫자만 입력하세요'), `${bad}: 오류 문구 ${text}`);
    }
    for (const [typed, qty] of [[' 2 ', 2], ['2', 2]]) {
      const edgeBefore = (await get('/api/customers/C01')).purchases.find(p => p.product_id === 'P01');
      await field(1, '고객', 'C01'); await field(1, '상품', 'P01'); await until(purchaseReady);
      await field(1, '수량', typed); await click('구매 등록');
      await until(`document.querySelector('.success-box')?.textContent.includes('구매 등록') && ${purchaseReady}`);
      assert.equal(posts.at(-1).body.qty, qty, `${JSON.stringify(typed)}: 전송 qty`);
      const edgeAfter = (await get('/api/customers/C01')).purchases.find(p => p.product_id === 'P01');
      assert.equal(edgeAfter.total_qty - (edgeBefore?.total_qty ?? 0), qty, `${JSON.stringify(typed)}: 저장 총수량 차이`);
      await evaluate(`document.querySelector('.success-box').remove`);
    }
  });

  await check('4번 나이·재고 입력 차단', async () => {
    await tab('등록·구매'); await until(purchaseReady);
    const sent = posts.length;
    await field(0, '이름', '입력검사'); await field(0, '나이', '2e1'); await click('등록 후 고객 상세 보기'); await delay(200);
    assert.equal(posts.length, sent, '나이 요청 전송');
    assert.ok((await evaluate(`document.querySelector('.error-box')?.textContent ?? ''`)).startsWith('나이: 숫자만'));
    await tab('상품 상세'); await until(`document.querySelector('main form input')`);
    await evaluate(`(()=>{const n=document.querySelector('main form input');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(n,'1.5');n.dispatchEvent(new Event('input',{bubbles:true}));})()`);
    await click('색상별 재고 전체 저장'); await delay(200);
    assert.equal(posts.length, sent, '재고 요청 전송');
    assert.ok((await evaluate(`document.querySelector('.error-box')?.textContent ?? ''`)).startsWith('P01 저장 실패: 재고('));
  });

  await check('5번 S1 세 수치', async () => {
    await home(); await tab('고객 상세'); await until(`document.querySelector('.customer-card li')`);
    const rows = (await get('/api/customers/C01')).purchases;
    const texts = await evaluate(`[...document.querySelectorAll('.customer-card li')].map(n=>n.textContent)`);
    assert.equal(texts.length, rows.length);
    rows.forEach((row, i) => assert.ok(texts[i].includes(`기록 ${row.count}건 · 총수량 ${row.total_qty}개 · 최근 구매일 ${row.last_date}`), texts[i]));
  });

  await check('5번 S2 그룹', async () => {
    await tab('상품 상세'); await until(`document.querySelector('.ledger-list li')`);
    const buyers = (await get('/api/products/P01')).buyers;
    const texts = await evaluate(`[...document.querySelectorAll('.ledger-list li')].map(n=>n.textContent)`);
    assert.equal(texts.length, buyers.length);
    buyers.forEach((row, i) => assert.ok(texts[i].includes(`그룹 ${row.group_id}`), texts[i]));
  });

  await check('5번 다시 검사는 GET만', async () => {
    await tab('무결성'); await until(`document.querySelector('.integrity-good')`);
    const sent = posts.length;
    const requests = [];
    const original = socket.onmessage;
    socket.onmessage = event => {
      const message = JSON.parse(event.data);
      if (message.method === 'Network.requestWillBeSent') requests.push(new URL(message.params.request.url).pathname);
      original(event);
    };
    await click('다시 검사'); await until(`document.querySelector('.integrity-good')`); await delay(200);
    socket.onmessage = original;
    assert.ok(requests.includes('/api/integrity'), `요청: ${requests}`);
    assert.equal(posts.length, sent, '변경 요청 전송');
  });

  await check('2번 늦은 재고 응답은 다른 상품에 문구 없음', async () => {
    await tab('상품 상세'); await until(`document.querySelector('main form input')`);
    const held = hold('PUT', '/api/products/P01/stock');
    await evaluate(`(()=>{const n=document.querySelector('main form input');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(n,'17');n.dispatchEvent(new Event('input',{bubbles:true}));})()`);
    await click('색상별 재고 전체 저장'); await held.reached;
    await evaluate(`(()=>{const n=document.querySelector('main > section .section-heading select');Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(n,'P02');n.dispatchEvent(new Event('change',{bubbles:true}));})()`);
    await until(`document.querySelector('.detail-grid h3')?.textContent.includes('P02')`);
    await release(held);
    assert.equal(await evaluate(`document.querySelector('.success-box')?.textContent ?? ''`), '');
    assert.ok(Object.values((await get('/api/products/P01')).product.stock).includes(17), 'P01 저장');
  });

  await check('2번 늦은 재고 실패 응답은 다른 상품에 오류 없음', async () => {
    const selectProduct = id => evaluate(`(()=>{const n=document.querySelector('main > section .section-heading select');Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(n,'${id}');n.dispatchEvent(new Event('change',{bubbles:true}));})()`);
    await selectProduct('P01');
    await until(`document.querySelector('.detail-grid h3')?.textContent.includes('P01') && document.querySelector('main form input')`);
    await delay(200);
    const before = JSON.stringify((await get('/api/products/P01')).product.stock);
    const held = hold('PUT', '/api/products/P01/stock');
    // 정수 표기는 맞고 서버가 거절하는 10자리 값으로 실패를 만든다.
    await evaluate(`(()=>{const n=document.querySelector('main form input');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(n,'1000000000');n.dispatchEvent(new Event('input',{bubbles:true}));})()`);
    await click('색상별 재고 전체 저장'); await held.reached;
    await selectProduct('P02');
    await until(`document.querySelector('.detail-grid h3')?.textContent.includes('P02')`);
    await release(held);
    assert.equal(await evaluate(`document.querySelector('.error-box')?.textContent ?? ''`), '');
    assert.equal(JSON.stringify((await get('/api/products/P01')).product.stock), before, 'P01 불변');
  });

  await check('2번 머문 상품 저장 실패는 ID 포함 오류', async () => {
    await evaluate(`(()=>{const n=document.querySelector('main > section .section-heading select');Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(n,'P01');n.dispatchEvent(new Event('change',{bubbles:true}));})()`);
    await until(`document.querySelector('.detail-grid h3')?.textContent.includes('P01') && document.querySelector('main form input')`);
    await delay(200);
    await evaluate(`(()=>{const n=document.querySelector('main form input');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(n,'1000000000');n.dispatchEvent(new Event('input',{bubbles:true}));})()`);
    await click('색상별 재고 전체 저장'); await until(`document.querySelector('.error-box')`);
    assert.ok((await evaluate(`document.querySelector('.error-box').textContent`)).startsWith('P01 저장 실패: '));
  });

  await check('2번 머문 상품 저장은 ID 포함 문구', async () => {
    await evaluate(`(()=>{const n=document.querySelector('main > section .section-heading select');Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(n,'P01');n.dispatchEvent(new Event('change',{bubbles:true}));})()`);
    await until(`document.querySelector('.detail-grid h3')?.textContent.includes('P01') && document.querySelector('main form input')`);
    await delay(200);
    await evaluate(`(()=>{const n=document.querySelector('main form input');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(n,'5');n.dispatchEvent(new Event('input',{bubbles:true}));})()`);
    await click('색상별 재고 전체 저장');
    await until(`document.querySelector('.success-box')`);
    assert.ok((await evaluate(`document.querySelector('.success-box').textContent`)).startsWith('P01 재고를 수정했습니다.'));
  });

  await check('3번 늦은 등록 응답은 탭 유지·데이터 갱신', async () => {
    await tab('등록·구매'); await until(purchaseReady);
    const before = (await get('/api/stats')).stats.customers;
    const held = hold('POST', '/api/customers');
    await field(0, '이름', '늦은등록'); await field(0, '나이', '22'); await click('등록 후 고객 상세 보기'); await held.reached;
    await tab('무결성'); await until(`document.querySelector('.stats-grid')`);
    await release(held);
    assert.equal(await evaluate(`document.querySelector('nav .active').textContent`), '무결성');
    assert.equal((await get('/api/stats')).stats.customers, before + 1);
    await until(`[...document.querySelectorAll('.stat-card')].find(n=>n.textContent.includes('고객 노드'))?.querySelector('strong').textContent===${JSON.stringify(String(before + 1))}`);
  });

  await check('3번 머문 등록은 고객 상세로 이동', async () => {
    await tab('등록·구매'); await until(purchaseReady);
    await field(0, '이름', '머문등록'); await field(0, '나이', '23'); await click('등록 후 고객 상세 보기');
    await until(`document.querySelector('nav .active')?.textContent==='고객 상세' && document.querySelector('.customer-card h3')?.textContent.includes('머문등록')`);
  });

  await check('1번 여성 40세 등록 뒤 모든 그룹 칩 중앙 클릭', async () => {
    await home();  // 서버 상태는 유지된다. 위 검사 고객은 G-F-40+가 아니다.
    const before = (await get('/api/groups')).branches.flatMap(b => b.groups).find(g => g.id === 'G-F-40+').count;
    await tab('등록·구매'); await until(purchaseReady);
    await field(0, '이름', '칩검사'); await field(0, '나이', '40'); await click('등록 후 고객 상세 보기');
    await until(`document.querySelector('.customer-card h3')?.textContent.includes('칩검사')`);
    await tab('그래프'); await until(`document.querySelector('[data-node-id="G-F-40+"]')?.dataset.groupCount===${JSON.stringify(String(before + 1))}`);
    const chips = await evaluate(`[...document.querySelectorAll('.graph-node.group')].map(n=>{const r=n.querySelector('rect').getBoundingClientRect();return {id:n.dataset.nodeId,x:r.x+r.width/2,y:r.y+r.height/2,top:r.top,bottom:r.bottom};})`);
    assert.equal(chips.length, 8);
    const overlaps = chips.flatMap((a, i) => chips.slice(i + 1).filter(b => a.top < b.bottom && b.top < a.bottom).map(b => `${a.id}/${b.id}`));
    assert.deepEqual(overlaps, []);
    for (const chip of chips) {
      await realClick(chip.x, chip.y);
      const selected = await evaluate(`document.querySelector('.selected-card strong')?.textContent ?? ''`);
      assert.ok(selected.startsWith(`${chip.id} `), `${chip.id} 클릭 → ${selected}`);
    }
  });

  await check('외부 네트워크 0·브라우저 예외 0', async () => {
    assert.deepEqual(external, []); assert.deepEqual(exceptions, []);
  });
  console.log(failures.length ? `FAIL ${failures.length}건: ${failures.join(' / ')}` : 'PASS UI9b 전체');
  process.exitCode = failures.length ? 1 : 0;
} finally {
  if (socket) socket.close();
  if (chrome) chrome.kill('SIGTERM');
  server.kill('SIGINT');
}

import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, mkdir, writeFile } from 'node:fs/promises';
import { once } from 'node:events';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// UI4b 화면 동작 검사. UI5 장면 기대값 검증과는 별도다. 추가 npm 패키지를 사용하지 않는다.
const repo = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const out = join(repo, 'docs/verification/ui4b_screens');
const profile = await mkdtemp(join(tmpdir(), 'shopgraph-ui4b-browser-'));
const server = spawn('python3', ['-u', '-B', '-c',
  'from data import initial_records; from graph import ShopGraph; from web import create_server; s=create_server(ShopGraph(*initial_records()),0); print(s.server_address[1],flush=True); s.serve_forever()'], {cwd: repo});
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let chrome;
let socket;
try {
  const [chunk] = await once(server.stdout, 'data');
  const base = `http://127.0.0.1:${String(chunk).trim()}`;
  chrome = spawn(process.env.CHROME_BIN ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', [
    '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--disable-extensions', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank',
  ]);
  const browserUrl = await new Promise((resolve, reject) => {
    let logs = '';
    chrome.stderr.on('data', data => {
      logs += data;
      const match = logs.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) resolve(match[1]);
    });
    chrome.once('exit', code => reject(new Error(`Chrome exit ${code}`)));
  });
  const debuggerBase = browserUrl.replace('ws:', 'http:').split('/devtools/')[0];
  const pages = await (await fetch(`${debuggerBase}/json/list`)).json();
  socket = new WebSocket(pages.find(page => page.type === 'page').webSocketDebuggerUrl);
  await once(socket, 'open');
  let nextId = 0;
  const waiting = new Map();
  const errors = [];
  const requests = [];
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const pending = waiting.get(message.id);
      waiting.delete(message.id);
      message.error ? pending.reject(message.error) : pending.resolve(message.result);
    } else if (message.method === 'Runtime.exceptionThrown') errors.push(message.params);
    else if (message.method === 'Network.requestWillBeSent') requests.push(message.params.request.url);
  };
  const command = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId; waiting.set(id, {resolve, reject});
    socket.send(JSON.stringify({id, method, params}));
  });
  const evaluate = async expression => {
    const result = await command('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true, userGesture: true});
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const until = async expression => {
    for (let attempt = 0; attempt < 120; attempt++) {
      if (await evaluate(`Boolean(${expression})`)) return;
      await delay(100);
    }
    throw new Error(`wait failed: ${expression}`);
  };
  const click = async text => {
    await evaluate(`(() => { const b=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()===${JSON.stringify(text)}); if(!b)throw Error('button missing'); b.click(); })()`);
  };
  const tab = async text => {
    await evaluate(`[...document.querySelectorAll('nav button')].find(b=>b.textContent.trim()===${JSON.stringify(text)}).click()`);
    await delay(100);
  };
  const field = async (formIndex, label, value) => {
    await evaluate(`(() => {
      const form=document.querySelectorAll('main form')[${formIndex}];
      const node=[...form.querySelectorAll('label')].find(l=>l.firstChild.textContent.trim()===${JSON.stringify(label)}).querySelector('input,select');
      Object.getOwnPropertyDescriptor(node.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype,'value').set.call(node,${JSON.stringify(value)});
      node.dispatchEvent(new Event(node.tagName==='SELECT'?'change':'input',{bubbles:true}));
    })()`);
  };
  const capture = async name => {
    const fullPage = name.startsWith('03_') || name.startsWith('04_');
    const metrics = fullPage ? await command('Page.getLayoutMetrics') : null;
    const shot = await command('Page.captureScreenshot', {format:'png', captureBeyondViewport:fullPage,
      ...(fullPage ? {clip:{x:0,y:0,width:1440,height:metrics.cssContentSize.height,scale:1}} : {})});
    await writeFile(join(out, name), Buffer.from(shot.data, 'base64'));
    console.log(`capture ${name}`);
  };
  await command('Runtime.enable'); await command('Network.enable'); await command('Page.enable');
  await command('Emulation.setDeviceMetricsOverride', {width:1440, height:900, deviceScaleFactor:1, mobile:false});
  await command('Page.navigate', {url:base});
  await until(`document.querySelectorAll('[data-node-id]').length > 0`);
  console.log('browser', (await command('Browser.getVersion')).product);

  // 개별 UI 동작 점검: 장면 1~8을 순서대로 실행하지 않는다.
  await tab('등록·구매');
  await field(0, '이름', '화면확인'); await field(0, '나이', '25');
  const mark = requests.length;
  await click('등록 후 고객 상세 보기');
  await until(`document.querySelector('.recommendation-card') && document.querySelector('.panel h3')?.textContent.includes('C31')`);
  assert(requests.slice(mark).some(url => url.endsWith('/api/customers/C31/recommendations')));
  console.log('PASS customer POST -> separate recommendations GET');
  await tab('그래프'); await until(`document.querySelector('[data-node-id="C31"]')`);
  const graphResponse = await (await fetch(`${base}/api/graph`)).json();
  assert.deepEqual(await evaluate(`[...document.querySelectorAll('[data-node-id]')].map(n=>n.dataset.nodeId)`), graphResponse.nodes.map(n=>n.id));
  const layout = await evaluate(`(() => {
    const svg=document.querySelector('.graph-svg'), box=svg.getBoundingClientRect();
    return {count:svg.querySelectorAll('[data-node-id]').length, viewport:[innerWidth,innerHeight],
      scrollHeight:document.documentElement.scrollHeight,
      circlesInside:[...svg.querySelectorAll('circle')].every(n=>{const b=n.getBoundingClientRect();return b.top>=box.top&&b.bottom<=box.bottom&&b.left>=box.left&&b.right<=box.right;}),
      labelsRight:[...svg.querySelectorAll('[data-node-id]')].every(n=>Number(n.querySelector('text').getAttribute('x'))>Number(n.querySelector('circle').getAttribute('cx'))+Number(n.querySelector('circle').getAttribute('r'))),
      restEdges:svg.querySelectorAll('.graph-edge.rest').length,
      activeEdges:svg.querySelectorAll('.graph-edge.active').length};
  })()`);
  console.log('graph measurements', JSON.stringify(layout));
  assert(layout.circlesInside && layout.labelsRight); assert(layout.scrollHeight <= 900);
  assert(layout.restEdges > 0 && layout.activeEdges === 0);
  console.log('PASS graph layout', JSON.stringify(layout));
  await capture('01_graph_overview.png');
  await evaluate(`document.querySelector('[data-node-id="C31"]').dispatchEvent(new MouseEvent('click',{bubbles:true}))`);
  assert(await evaluate(`document.querySelectorAll('.graph-edge.active').length === 1 && document.querySelectorAll('.graph-node.active').length === 2 && document.querySelectorAll('.graph-node.dim').length > 0`));
  assert(await evaluate(`document.documentElement.scrollHeight <= 900`));
  await capture('02_graph_C31.png');
  await click('선택 해제'); assert(await evaluate(`document.querySelectorAll('.graph-edge.active').length === 0`));

  await tab('고객 상세');
  await evaluate(`(() => {const n=document.querySelector('.section-heading select');n.value='C01';n.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  await until(`document.querySelector('.scope-badge.gender') && document.querySelector('.notice-box')`);
  assert(await evaluate(`document.querySelectorAll('details[open]').length === 0`));
  assert(await evaluate(`document.querySelector('.notice-box').compareDocumentPosition(document.querySelector('.recommendation-card')) & Node.DOCUMENT_POSITION_FOLLOWING`));
  const noticeText = await evaluate(`[...document.querySelectorAll('.notice-box p')].map(n=>n.textContent)`);
  const rec = await (await fetch(`${base}/api/customers/C01/recommendations`)).json();
  assert.deepEqual(noticeText, rec.notice_lines);
  await capture('03_customer_mixed_scopes.png');
  await evaluate(`document.querySelector('details summary').click()`);
  assert(await evaluate(`document.querySelectorAll('details[open]').length===1`));
  console.log('PASS mixed badges, notices before cards, console collapsed/expand');

  await tab('그룹 인기'); await until(`document.querySelector('.bar-chart svg') && !document.querySelector('.comparison-actions button').disabled`);
  const before = await evaluate(`[...document.querySelectorAll('.popular-list li')].map(n=>n.textContent)`);
  await click("지금을 '전'으로 고정");
  await tab('등록·구매');
  assert.equal(await evaluate(`document.querySelectorAll('form')[1].querySelector('select').value`), 'C31');
  await field(1, '상품', 'P07');
  await until(`!document.querySelectorAll('form')[1].querySelectorAll('select')[2].disabled`);
  const colors = await evaluate(`[...document.querySelectorAll('form')[1].querySelectorAll('select')[2].options].map(o=>o.value)`);
  const stock = (await (await fetch(`${base}/api/products/P07`)).json()).product.stock;
  assert.deepEqual(colors, Object.keys(stock));
  for (const color of colors.slice(0, 2)) {
    await field(1, '색상', color); await click('구매 등록');
    await until(`document.querySelector('.success-box') && !document.querySelectorAll('form')[1].querySelector('button').disabled`);
  }
  console.log('PASS server customer/color options and last registration selection');
  await tab('그룹 인기');
  await until(`document.querySelectorAll('.chart-grid .bar-chart').length===2 && document.querySelectorAll('.rank-changed').length>0 && !document.querySelector('.comparison-actions button').disabled`);
  assert.deepEqual(await evaluate(`[...document.querySelector('.bar-chart').querySelectorAll('.popular-list li')].map(n=>n.textContent)`), before);
  assert(await evaluate(`[...document.querySelectorAll('.bar-chart')].every(chart=>chart.querySelectorAll('svg g').length===chart.querySelectorAll('.popular-list li').length)`));
  assert(await evaluate(`[...document.querySelectorAll('.bar-chart')].every(chart=>[...chart.querySelectorAll('rect')].some(r=>Number(r.getAttribute('width'))===464))`));
  await capture('04_popular_before_after.png');
  await evaluate(`(() => {const n=[...document.querySelectorAll('.toolbar label')].find(l=>l.firstChild.textContent==='개수').querySelector('select');n.value='3';n.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  await until(`document.querySelector('.single-chart .bar-chart') && !document.querySelector('.comparison-actions button').disabled`);
  assert.equal(await evaluate(`document.querySelectorAll('.chart-grid .bar-chart').length`), 0);
  assert.equal(await evaluate(`document.querySelectorAll('.popular-list li').length`), 3);
  await click("지금을 '전'으로 고정");
  await evaluate(`(() => {const n=[...document.querySelectorAll('.toolbar label')].find(l=>l.firstChild.textContent==='그룹').querySelector('select');n.value='G-F-30';n.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  await until(`document.querySelector('.single-chart .bar-chart h3')?.textContent.includes('30대') && !document.querySelector('.comparison-actions button').disabled`);
  assert.equal(await evaluate(`document.querySelectorAll('.chart-grid .bar-chart').length`), 0);
  console.log('PASS frozen before, changed ranks, full chart rows, max width, filter reset');

  await tab('고객 상세'); await until(`document.querySelector('.recommendation-card')`);
  const firstId = await evaluate(`document.querySelector('.recommendation-card strong').textContent.match(/\((P[0-9]+)\)/)[1]`);
  await evaluate(`document.querySelector('.recommendation-card button').click()`);
  await until(`document.querySelector('form h3')?.textContent==='재고 수정'`);
  await evaluate(`document.querySelectorAll('form input').forEach(n=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(n,'0');n.dispatchEvent(new Event('input',{bubbles:true}));})`);
  await click('색상별 재고 전체 저장');
  await until(`document.querySelector('.success-box button') && document.querySelector('.status-pill')?.textContent==='품절'`);
  assert((await evaluate(`document.querySelector('.success-box button').textContent`)).includes('C01'));
  await evaluate(`document.querySelector('.success-box button').click()`);
  await until(`document.querySelector('.recommendation-card') && document.querySelector('.panel h3')?.textContent.includes('C01')`);
  assert(!(await evaluate(`document.querySelector('.recommendation-panel').textContent`)).includes(`(${firstId})`));
  console.log('PASS stock save -> last viewed customer -> fresh recommendations; no render exception');
  await tab('무결성'); await until(`document.querySelectorAll('.stat-card').length===6`);
  assert.deepEqual(await evaluate(`[...document.querySelectorAll('.stat-card span')].map(n=>n.textContent)`), ['그룹 노드','고객 노드','상품 노드','소속 간선','구매 간선','구매 기록']);
  assert.equal(await evaluate(`document.querySelector('footer').textContent`), '저장하지 않음 · 서버를 다시 켜면 처음 상태');
  await capture('05_integrity.png');

  assert.deepEqual(errors, []);
  const external = requests.filter(url => /^https?:/.test(url) && !url.startsWith(base + '/'));
  assert.deepEqual(external, []);
  console.log(`PASS external HTTP resources=${external.length}; browser exceptions=${errors.length}`);
  console.log('PASS all UI4b browser checks; UI5 scene sequence not run');
} finally {
  if (socket) socket.close();
  if (chrome) chrome.kill('SIGTERM');
  server.kill('SIGTERM');
}

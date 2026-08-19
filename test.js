/* node test.js — runs index.html's script in a stub DOM and asserts the parts
   that quietly rot: place naming and home/trip detection.
   Coordinate fixtures need no personal data. If ./lh.json (a Timeline export)
   exists, the end-to-end checks run too; otherwise they are skipped. */
const fs = require('fs'), vm = require('vm'), assert = require('assert');

const code = fs.readFileSync(__dirname + '/index.html', 'utf8')
  .match(/<script>([\s\S]*?)<\/script>/)[1];

const el = new Proxy({}, {
  get: (t, k) => k === 'classList' ? {add(){}, remove(){}}
    : k === 'style' ? {} : k === 'value' ? '80'
    : k === 'clientWidth' ? 900 : k === 'getContext' ? () => el
    : typeof k === 'string' && /^(querySelector|measureText|getBoundingClientRect)/.test(k) ? () => el
    : () => el,
  set: () => true,
});
const ctx = vm.createContext({
  document: {querySelector: () => el, querySelectorAll: () => [], createElement: () => el},
  addEventListener(){}, devicePixelRatio: 1, performance, console, setTimeout,
  fetch: () => Promise.resolve({json: () => JSON.parse(fs.readFileSync(__dirname + '/geo.json', 'utf8'))}),
});
vm.runInContext(code, ctx);

(async () => {
  await new Promise(r => setImmediate(r));           // let the geo.json fetch settle
  let n = 0;
  const eq = (got, want, what) => { assert.strictEqual(got, want, `${what}: ${got} != ${want}`); n++; };

  // --- place naming -------------------------------------------------------
  const name = (la, lo) => ctx.placeName(la, lo).name;
  eq(name(37.50173, 127.01317), '서울특별시 서초구', '서초');
  eq(name(34.76830, 128.40770), '경상남도 통영시', '통영');
  eq(name(36.97640, 127.99550), '충청북도 충주시', '충주');
  eq(name(35.81080, 127.15120), '전라북도 전주시 완산구', '전주 (시/구 분리)');
  eq(name(33.24970, 126.36090), '제주특별자치도 서귀포시', '서귀포');
  // a bigger city outranks a ward/neighbourhood at similar distance
  eq(name(35.70700, 139.77300), 'Tokyo, 일본', '도쿄 (Chuo 아님)');
  eq(name(37.78520, -122.40450), 'San Francisco, 미국', 'SF (Chinatown 아님)');
  // …but not when the small place is the one you actually stayed in
  eq(name(35.96850, -79.06840), 'Chapel Hill, 미국', '채플힐 (Durham 아님)');
  // Natural Earth has no Guam at 110m — the city index has to cover it
  eq(name(13.49290, 144.80690).split(', ')[1], '괌', '괌');
  // a sea point near Korea stays Korean instead of falling through to "대한민국"
  assert.ok(name(37.9716, 128.7656).startsWith('강원도'), '동해 앞바다 → 강원도'); n++;

  eq(ctx.shortName('충청남도 천안시 동남구'), '천안시', '라벨: 구 → 시');
  eq(ctx.shortName('Honolulu, 미국'), 'Honolulu', '라벨: 해외는 도시명');
  assert.ok(Math.abs(ctx.hav([37.5, 127], [37.5, 128]) - 88.3) < 1, 'haversine'); n++;

  // --- end-to-end (needs a real export) -----------------------------------
  if (fs.existsSync(__dirname + '/lh.json')) {
    const raw = JSON.parse(fs.readFileSync(__dirname + '/lh.json', 'utf8'));
    const A = ctx.analyse(raw);
    assert.ok(A.res.length >= 1, '거주지를 최소 1곳 찾는다'); n++;
    assert.ok(A.res.every(r => r.to - r.from >= 90), '거주지는 90일 이상'); n++;
    const T = ctx.trips(A, 80);
    assert.ok(T.length > 0 && T.every(t => t.km > 80), '여행은 모두 기준 거리 초과'); n++;
    assert.ok(T.every((t, i) => i === 0 || t.a > T[i-1].b), '여행 구간이 겹치지 않는다'); n++;

    // stripping the Home labels must not move the detected homes
    const bare = raw.map(r => r.visit
      ? {...r, visit: {...r.visit, topCandidate: (({semanticType, ...c}) => c)(r.visit.topCandidate)}}
      : r);
    const B = ctx.analyse(bare);
    assert.ok(B.H.inferred, 'Home 라벨이 없으면 심야 체류로 추정'); n++;
    eq(B.res.length, A.res.length, '추정 경로도 같은 수의 거주지');
    A.res.forEach((r, i) => {
      assert.ok(ctx.hav(r.pos, B.res[i].pos) < 2, `거주지 ${i} 오차 2km 미만`); n++;
    });
  } else console.log('lh.json 없음 — 종단 테스트 건너뜀');

  console.log(`ok — ${n} checks`);
})();

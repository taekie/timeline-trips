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
  fetch: (u) => Promise.resolve({json: () => JSON.parse(fs.readFileSync(
    __dirname + '/' + String(u).split('?')[0], 'utf8'))}),
});
vm.runInContext(code, ctx);

(async () => {
  await new Promise(r => setImmediate(r));           // let the geo.json fetch settle
  // 지역 파일은 지연 로딩이므로 테스트가 명시적으로 받아온다
  await ctx.ensureRegions(['KR', 'US', 'JP']);
  let n = 0;
  const eq = (got, want, what) => { assert.strictEqual(got, want, `${what}: ${got} != ${want}`); n++; };

  // --- place naming -------------------------------------------------------
  const name = (la, lo) => ctx.placeName(la, lo).name;
  const eval_ = e => vm.runInContext(e, ctx);
  eval_('HOME_CC = "KR"');
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
  // 지역 파일이 없는 나라는 도시 인덱스로 대체된다
  eq(eval_('REG.has("KR") && REG.has("US") && !REG.has("FR")'), true, '방문국 지역 파일만 로딩');
  // 해상 좌표는 국가 외곽선 밖이라 최근접 도시로 추정하면 엉뚱한 나라가 나온다
  assert.ok(name(37.9716, 128.7656).startsWith('강원도'), '동해 앞바다 → 강원도'); n++;
  assert.ok(name(36.9411, 126.7987).startsWith('충청남도') ||
            name(36.9411, 126.7987).startsWith('경기도'), '서해 앞바다 → 북한 아님'); n++;

  eq(ctx.shortName('충청남도 천안시 동남구'), '천안시', '라벨: 구 → 시');
  eq(ctx.shortName('Honolulu, 미국'), 'Honolulu', '라벨: 해외는 도시명');
  assert.ok(Math.abs(ctx.hav([37.5, 127], [37.5, 128]) - 88.3) < 1, 'haversine'); n++;

  // --- 날짜 칩 지명 ---------------------------------------------------------
  // 서초 3점 + 통영 1점이면 그 날은 서초로 대표된다 (가장 먼 곳이 아니라 가장 오래 있은 곳)
  eq(ctx.dayLabel([[37.50173,127.01317],[37.50180,127.01320],[37.50150,127.01300],
                   [34.76830,128.40770]]), '서초구', '칩 지명: 최다 군집');
  eq(ctx.dayLabel([]), '', '칩 지명: 기록 없는 날은 빈 문자열');
  // 해외는 "Tokyo, 일본" 꼴이라 국가명을 뗀다
  eq(ctx.dayLabel([[35.70700,139.77300]]), 'Tokyo', '칩 지명: 해외는 도시명만');
  // 해상 좌표는 "강원도 앞바다" 꼴이라 마지막 토큰만 떼면 "앞바다" 만 남는다
  eq(ctx.tightName('강원도 앞바다'), '강원도 앞바다', '좁은 칸 지명: 앞바다 접미사 유지');
  eq(ctx.tightName('충청남도 천안시 동남구'), '동남구', '좁은 칸 지명: 구를 떼지 않는다');
  eq(ctx.tightName('Honolulu, 미국'), 'Honolulu', '좁은 칸 지명: 해외는 도시명');
  // shortName 을 그대로 썼다면 여기서 '서울특별시'가 나와 첫 검사가 깨진다

  // --- 웹 메르카토르 --------------------------------------------------------
  const near = (a, b, tol, what) => { assert.ok(Math.abs(a - b) < tol, `${what}: ${a} != ${b}`); n++; };
  near(ctx.merc(0, 0, 0)[0], 128, 1e-6, 'z0 본초자오선은 타일 중앙 x');
  near(ctx.merc(0, 0, 0)[1], 128, 1e-6, 'z0 적도는 타일 중앙 y');
  near(ctx.merc(0, 180, 0)[0], 256, 1e-6, 'z0 동경 180도는 타일 우단');
  near(ctx.merc(85.05112878, 0, 0)[1], 0, 1e-6, 'z0 메르카토르 북단은 y=0');
  const seoul = ctx.merc(37.5665, 126.9780, 12);
  eq(Math.floor(seoul[0] / 256), 3492, 'z12 서울 타일 x');
  eq(Math.floor(seoul[1] / 256), 1586, 'z12 서울 타일 y');

  // fitTrip 은 주어진 지점을 모두 캔버스 안에 넣는다
  const W = 860, H = 420;
  const inside = (pts, what) => {
    const v = ctx.fitTrip(pts, W, H);
    assert.ok(v, `${what}: 뷰가 나온다`); n++;
    for (const p of pts) {
      const m = ctx.merc(p[0], v.wrap && p[1] < 0 ? p[1] + 360 : p[1], v.z);
      assert.ok(m[0] + v.ox >= 0 && m[0] + v.ox <= W && m[1] + v.oy >= 0 && m[1] + v.oy <= H,
        `${what}: ${p} 가 캔버스 안`); n++;
    }
    return v;
  };
  inside([[37.5665, 126.9780], [35.1796, 129.0756]], '서울-부산');
  inside([[35.6762, 139.6503], [35.6895, 139.6917], [35.7100, 139.8107]], '도쿄 시내');
  inside([[35.6762, 139.6503], [21.3069, -157.8583]], '도쿄-호놀룰루');
  const one = inside([[37.5665, 126.9780]], '한 점');
  assert.ok(one.z <= 14, `한 점짜리도 최소 스팬 때문에 과확대되지 않는다: z=${one.z}`); n++;
  assert.strictEqual(ctx.fitTrip([], W, H), null, '빈 입력은 null'); n++;

  // 날짜변경선을 건너는 여행은 지구 반대편이 아니라 태평양 쪽으로 잡는다
  const pac = ctx.fitTrip([[35.6762, 139.6503], [21.3069, -157.8583]], W, H);
  assert.ok(pac.wrap, '태평양 횡단은 경도를 풀어서 잡는다'); n++;
  assert.ok(pac.z >= 3, `태평양 횡단 줌이 과도하게 빠지지 않는다: z=${pac.z}`); n++;
  const px = (p, v) => ctx.merc(p[0], v.wrap && p[1] < 0 ? p[1] + 360 : p[1], v.z)[0] + v.ox;
  assert.ok(px([21.3069, -157.8583], pac) > px([35.6762, 139.6503], pac),
    '호놀룰루가 도쿄 오른쪽에 온다'); n++;
  // 날짜변경선을 안 건너는 여행은 경도를 풀지 않는다
  assert.ok(!ctx.fitTrip([[37.5665, 126.9780], [35.1796, 129.0756]], W, H).wrap,
    '국내 여행은 wrap 하지 않는다'); n++;

  // --- 하루 안 지점이 시간순으로 정렬된다 -----------------------------------
  const visit = (st, en, la, lo, type) => ({
    startTime: st, endTime: en,
    visit: {topCandidate: {placeLocation: `geo:${la},${lo}`, semanticType: type}},
  });
  const segs = [];
  for (let i = 1; i <= 25; i++) {              // buildHomes 는 Home 표 20개 이상을 요구한다
    const d = `2025-01-${String(i).padStart(2, '0')}`;
    segs.push(visit(`${d}T22:00:00.000+09:00`, `${d}T23:00:00.000+09:00`,
                    37.5665, 126.9780, 'INFERRED_HOME'));
  }
  // 같은 날의 세 체류를 파일에는 시간 역순으로 적어 둔다
  segs.push(visit('2025-01-26T18:00:00.000+09:00', '2025-01-26T19:00:00.000+09:00', 37.53, 127.0, 'UNKNOWN'));
  segs.push(visit('2025-01-26T09:00:00.000+09:00', '2025-01-26T10:00:00.000+09:00', 37.51, 127.0, 'UNKNOWN'));
  segs.push(visit('2025-01-26T13:00:00.000+09:00', '2025-01-26T14:00:00.000+09:00', 37.52, 127.0, 'UNKNOWN'));
  const ORD = ctx.analyse({semanticSegments: segs});
  // extract 는 체류마다 시작·종료 두 점을 넣으므로 그 날은 6점이다
  const mixed = [...ORD.days.entries()].find(([, ps]) => ps.length === 6);
  assert.ok(mixed, '역순으로 적은 날을 찾는다'); n++;
  // vm 컨텍스트에서 나온 배열은 프로토타입이 달라 deepStrictEqual 이 실패한다. 문자열로 비교한다.
  eq(mixed[1].map(p => p[0]).join(','),
     '37.51,37.51,37.52,37.52,37.53,37.53', '하루 안 지점이 시간순');

  // --- 집에 들렀다 다시 떠나면 별개 여행 -------------------------------------
  // 여행이 끝났다는 신호는 낮에 얼마나 멀리 갔느냐가 아니라 그 밤을 집에서 잤느냐다.
  // 기준 거리를 낮추면 집 앞 나들이까지 "먼 날"이 되어 두 여행 사이가 메워진다.
  const HOME = [37.5665, 126.9780], SUWON = [37.2636, 127.0286],   // 집에서 34km
        GANG = [37.7519, 128.8761], MOKPO = [34.7936, 126.3886],   // 168km / 313km
        SOKCHO = [38.2070, 128.5918];                              // 강릉에서 52km
  const dayN = n => new Date(Date.UTC(2025, 0, 1) + n * 864e5).toISOString().slice(0, 10);
  // 밤 체류는 현지 새벽 3시를 넘겨야 "그 곳에서 잤다"로 읽힌다
  const night = (n, p, type) => visit(`${dayN(n)}T22:00:00.000+09:00`,
    `${dayN(n + 1)}T08:00:00.000+09:00`, p[0], p[1], type);
  const noon = (n, p) => visit(`${dayN(n)}T12:00:00.000+09:00`,
    `${dayN(n)}T14:00:00.000+09:00`, p[0], p[1], 'RESTAURANT');
  // 집 120일 + 여행 A(강릉 5일) + 집 이틀(낮에는 수원) + 여행 B 5일
  const trip2 = (awayB) => {
    const g = [];
    for (let i = 0; i < 200; i++) {
      if (i >= 120 && i <= 131) continue;
      g.push(night(i, HOME, 'INFERRED_HOME'), noon(i, HOME));
    }
    for (let i = 120; i <= 124; i++) g.push(night(i, GANG, 'LODGING'), noon(i, GANG));
    for (let i = 125; i <= 126; i++) g.push(night(i, HOME, 'INFERRED_HOME'), noon(i, SUWON));
    for (let i = 127; i <= 131; i++) g.push(night(i, awayB, 'LODGING'), noon(i, awayB));
    return ctx.analyse({semanticSegments: g});
  };
  const FAR = trip2(MOKPO), NEAR = trip2(SOKCHO);
  // 기준 거리를 낮추면 수원 나들이가 빈틈을 메워 두 여행이 붙어 버렸다
  eq(ctx.trips(FAR, 80).length, 2, '기준 80km: 강릉·목포는 별개 여행');
  assert.ok(ctx.trips(FAR, 30).filter(t => t.nights >= 3).length === 2,
    '기준 30km: 집에서 잔 이틀이 강릉·목포를 갈라놓는다'); n++;
  // 목적지가 가까우면(강릉 → 속초) 두 번째 단계가 다시 붙인다
  eq(ctx.trips(NEAR, 80).length, 2, '기준 80km: 집에서 잤으면 가까운 목적지도 안 합친다');
  // 집에서 잔 밤이 없으면 예전처럼 하나로 이어져야 한다 (중간이 비어도 한 여행)
  const CONT = (() => {
    const g = [];
    for (let i = 0; i < 200; i++) {
      if (i >= 120 && i <= 131) continue;
      g.push(night(i, HOME, 'INFERRED_HOME'), noon(i, HOME));
    }
    for (let i = 120; i <= 124; i++) g.push(night(i, GANG, 'LODGING'), noon(i, GANG));
    for (let i = 125; i <= 126; i++) g.push(night(i, GANG, 'LODGING'));   // 낮 기록만 빠진 이틀
    for (let i = 127; i <= 131; i++) g.push(night(i, SOKCHO, 'LODGING'), noon(i, SOKCHO));
    return ctx.analyse({semanticSegments: g});
  })();
  eq(ctx.trips(CONT, 80).length, 1, '집에 안 들렀으면 낮 기록이 비어도 한 여행');

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

# 여행 상세 지도 모달 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 여행 표의 행을 클릭하면 모달이 열리고, 그 기간의 이동 경로를 날짜별로 짚어볼 수 있는 지도를 보여준다.

**Architecture:** 기존 `draw()`는 정거원통도법이라 타일 지도와 정합이 맞지 않는다. 모달은 웹 메르카토르 투영을 따로 갖고, 배경 레이어(벡터 기본 / CARTO 타일 옵트인)와 경로 레이어를 분리해 그린다. 팬·줌은 넣지 않고 여행 범위에 자동으로 맞춘다.

**Tech Stack:** 바닐라 JS, Canvas 2D, 단일 `index.html`. 외부 라이브러리 없음.

## Global Constraints

- **의존성 0 유지.** 외부 라이브러리·번들러·빌드 단계를 추가하지 않는다. 전체 앱은 `index.html` 한 파일이다.
- **새 순수 함수는 `function` 선언으로 쓴다.** `test.js`는 `vm.runInContext`로 스크립트를 실행한 뒤 `ctx.함수명`으로 접근한다. `const f = () => {}` 꼴은 `ctx.f`로 잡히지 않는다.
- **스크립트 로드 시점에 `localStorage` / `Image` / `requestAnimationFrame`을 건드리지 않는다.** `test.js`의 스텁 컨텍스트(test.js:18-23)에 이 셋이 없어서 최상위에서 참조하면 테스트가 즉시 죽는다. 반드시 런타임에 호출되는 함수 안에서만 쓰고, `localStorage`는 `try/catch`로 감싼다.
- **팬·줌 없음.** 여행 범위 자동 맞춤만 한다.
- **라이트 모드 고정.** 강조색 `var(--blue)` = `#3b82f6`. 한글은 `KoddiUD OnGothic`. 이미 `:root`에 정의된 CSS 변수만 쓰고 새 색을 직접 박아 넣지 않는다.
- **요청하지 않은 애니메이션·전환 효과를 넣지 않는다.**
- **모든 커밋은 `node test.js`가 통과한 상태에서 한다.** 현재 기준선은 `ok — 15 checks`다.
- 작업 브랜치는 `trip-detail-map`이다. 이미 `c6fa050`(날짜 포맷), `f28f595`(경로 곡선), `f4dffa1`(설계 문서)가 올라가 있다.

## 사전 준비

브라우저 확인 단계는 합성 데이터를 쓴다. 작업 트리에 `sample-kr.json` / `sample-us.json` / `sample-jp.json`이 있으면 그대로 쓴다 (추적되지 않는 작업 산출물이라 없을 수도 있다). 없으면 실제 Timeline 내보내기 파일이나, 아래 최소 형태를 만족하는 아무 합성 파일이면 된다.

- `{"semanticSegments":[...]}` 꼴이고 각 원소는 `startTime` / `endTime`(ISO, 오프셋 포함)과 `visit.topCandidate.placeLocation`(`"geo:위도,경도"`)을 갖는다
- `semanticType`이 `INFERRED_HOME`인 체류가 **20개 이상** 있어야 집이 잡힌다 (index.html:295)
- 집에서 기준거리(기본 자동, 50~150km) 밖인 날이 있어야 여행이 잡힌다
- 확인 대상이 넓으려면 국내 근거리·해외·연말연시 걸침·당일치기를 섞는다

서버는 다음으로 띄운다. `file://`로는 `geo.json`을 못 읽는다.

```sh
cd /Users/taekie/Works/vibecoding/timeline-trips
portless timeline-trips sh -c 'python3 -m http.server $PORT --bind 127.0.0.1'
```

브라우저 콘솔에서 데이터를 주입하는 방법 (파일 선택 UI를 거치지 않는다):

```js
ST = analyse(await fetch('/sample-jp.json').then(r=>r.json()));
document.querySelector('#out').classList.remove('hide');
await render();
```

## File Structure

이 프로젝트는 단일 파일 구조다. 새 파일을 만들지 않고 `index.html` 안의 세 구역에 나눠 넣는다.

| 구역 | 위치 | 담는 것 |
|---|---|---|
| CSS | `index.html:77` 뒤 (`</style>` 직전) | 모달·칩·저작자표시 스타일 |
| HTML | `index.html:133` (`<div id="tip">`) 직전 | 모달 마크업 |
| JS — 투영 | `index.html:496` 뒤 (`/* canvas map */` 직전) | `merc`, `fitTrip` |
| JS — 상세 | `draw()` 블록 끝 (`index.html:567` 뒤) | `tripDays`, `dayLabel`, `drawBackdrop`, `drawTiles`, `drawDetail`, `buildDays`, `openTrip`, `closeTrip` |
| JS — 핸들러 | 파일 끝 핸들러 구역 (`index.html:646` 부근) | 행 클릭, 마커 클릭, Esc, 칩 클릭, 토글 |
| 테스트 | `test.js` | 순수 함수 검증 |

---

### Task 1: 하루 안 지점을 시간순으로 정렬

`analyse`는 좌표를 날짜 바구니에 담으면서 시각을 버린다. 하루 안 순서가 파일 기록 순서에 의존하므로 경로를 선으로 이으면 뒤집힐 수 있다. 담기 전에 한 번 정렬한다. 추가 저장은 없다.

**Files:**
- Modify: `index.html:335-340`
- Test: `test.js`

**Interfaces:**
- Consumes: 없음
- Produces: `analyse(raw).days` — `Map<날짜인덱스, [위도,경도][]>`. 각 배열이 그 날의 **시간 오름차순** 경로다. 이후 모든 태스크가 이 순서를 전제한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`test.js`의 `eq(ctx.shortName(...))` 묶음 바로 뒤, `// --- end-to-end` 주석 앞에 넣는다.

```js
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
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node test.js`
Expected: FAIL — `하루 안 지점이 시간순: 37.53,37.53,37.51,37.51,37.52,37.52 != 37.51,37.51,37.52,37.52,37.53,37.53`

- [ ] **Step 3: 최소 구현**

`index.html:335`의 `const days=new Map();` 바로 앞에 한 줄을 넣는다.

```js
  pts.sort((x,y)=>x[0]-y[0]);   // 하루 안 경로를 시간순으로 잇기 위해 한 번만 정렬한다
  const days=new Map();
```

`trips()`의 `sum()`과 `dmax` 계산은 모두 순서에 무관하므로 기존 동작은 바뀌지 않는다.

- [ ] **Step 4: 통과를 확인한다**

Run: `node test.js`
Expected: PASS — `ok — 17 checks`

- [ ] **Step 5: 커밋**

```bash
git add index.html test.js
git commit -m "하루 안 지점을 시간순으로 정렬

경로를 선으로 이으려면 하루 안 순서가 필요한데, 지금은 파일 기록
순서에 의존한다. 날짜 바구니에 담기 전에 한 번 정렬한다. trips()와
dmax 는 순서에 무관하므로 기존 판정은 바뀌지 않는다."
```

---

### Task 2: 웹 메르카토르 투영과 범위 맞춤

기존 `draw()`의 투영(index.html:520-522)은 정거원통도법에 cos(중위도)로 가로만 줄인 방식이라 타일과 어긋난다. 상세 지도용 투영을 따로 만든다.

**Files:**
- Modify: `index.html:496` 뒤 (`/* canvas map */` 주석 앞)
- Test: `test.js`

**Interfaces:**
- Consumes: `D` (= `Math.PI/180`, index.html:137)
- Produces:
  - `merc(la, lo, z) -> [x, y]` — 줌 `z`에서의 전역 픽셀 좌표. 타일 한 변은 256px
  - `fitTrip(pts, W, H) -> {z, wrap, ox, oy} | null` — `pts`는 `[위도, 경도][]`. 빈 배열이면 `null`. 화면 좌표는 `merc(la, wrap&&lo<0?lo+360:lo, z)[0]+ox`, `merc(...)[1]+oy`
  - `wrap`은 여행이 날짜변경선을 건널 때 `true`다. 이때 음수 경도를 +360으로 풀어야 태평양 쪽 짧은 경로로 잡힌다. `merc`는 180도를 넘는 경도를 그대로 받아 세계 폭 밖 x를 돌려주며, 타일은 `((x%n)+n)%n`으로 감싸므로 그대로 맞아떨어진다
  - 상수 `TILE` (=256), `ZMAX` (=16)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`test.js`의 Task 1 묶음 뒤에 넣는다. 기대값은 표준 슬리피 타일 공식으로 계산해 검증한 값이다.

```js
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
      // 날짜변경선을 건너면 fitTrip 이 경도를 풀어서 잡으므로 여기서도 같은 규칙을 쓴다
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
  assert.ok(!ctx.fitTrip([[37.5665, 126.9780], [35.1796, 129.0756]], W, H).wrap,
    '국내 여행은 wrap 하지 않는다'); n++;
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node test.js`
Expected: FAIL — `ctx.merc is not a function`

- [ ] **Step 3: 최소 구현**

`index.html`의 `/* canvas map */` 주석 바로 앞에 넣는다.

```js
/* ---------- 웹 메르카토르 (상세 지도 전용) ----------
   위 draw() 는 정거원통도법이라 타일과 정합이 맞지 않는다. 상세 지도는
   타일과 같은 EPSG:3857 로 따로 잡는다. */
const TILE=256, ZMAX=16;
function merc(la,lo,z){
  const n=TILE*Math.pow(2,z), s=Math.sin(la*D);
  return [n*(lo+180)/360, n*(.5-Math.log((1+s)/(1-s))/(4*Math.PI))];
}
/* 지점 전체를 W×H 안에 담는 줌과 오프셋. 팬·줌이 없으므로 한 번만 계산한다. */
function fitTrip(pts,W,H){
  let la0=1/0,lo0=1/0,la1=-1/0,lo1=-1/0;
  for(const p of pts){
    if(p[0]<la0)la0=p[0]; if(p[0]>la1)la1=p[0];
    if(p[1]<lo0)lo0=p[1]; if(p[1]>lo1)lo1=p[1];
  }
  if(!isFinite(la0)) return null;
  let wrap=false;
  if(lo1-lo0>180){                     // 날짜변경선을 건너면 짧은 쪽으로 잡는다
    wrap=true; lo0=1/0; lo1=-1/0;
    for(const p of pts){
      const lo=p[1]<0?p[1]+360:p[1];
      if(lo<lo0)lo0=lo; if(lo>lo1)lo1=lo;
    }
  }
  const MIN=.02;                       // 한 점짜리 여행도 약 2km 폭은 보이게
  if(la1-la0<MIN){const c=(la0+la1)/2; la0=c-MIN/2; la1=c+MIN/2;}
  if(lo1-lo0<MIN){const c=(lo0+lo1)/2; lo0=c-MIN/2; lo1=c+MIN/2;}
  const pad=.12;
  let z=ZMAX;
  for(;z>0;z--){
    const a=merc(la1,lo0,z), b=merc(la0,lo1,z);
    if(b[0]-a[0]<=W*(1-pad*2)&&b[1]-a[1]<=H*(1-pad*2)) break;
  }
  const a=merc(la1,lo0,z), b=merc(la0,lo1,z);
  return {z, wrap, ox:(W-(b[0]-a[0]))/2-a[0], oy:(H-(b[1]-a[1]))/2-a[1]};
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `node test.js`
Expected: PASS — `ok — 41 checks` (기준선 15 + Task 1 의 2 + 이 태스크의 24)

- [ ] **Step 5: 커밋**

```bash
git add index.html test.js
git commit -m "상세 지도용 웹 메르카토르 투영 추가

기존 draw() 는 정거원통도법이라 타일 지도와 정합이 맞지 않는다.
상세 지도가 쓸 merc/fitTrip 을 EPSG:3857 로 따로 둔다. 줌은 16으로
자르고, 한 점짜리 여행은 최소 스팬 0.02도를 강제해 과확대를 막는다."
```

---

### Task 3: 모달 뼈대와 열고 닫기

**Files:**
- Modify: `index.html` — CSS(`</style>` 직전), HTML(`<div id="tip">` 직전), JS(파일 끝 핸들러 구역)
- Test: 브라우저 수동 확인 (스텁 DOM으로는 모달 조작을 볼 수 없다)

**Interfaces:**
- Consumes: `fmt`(index.html:424), `dstr`(index.html:288), `MK`(index.html:510), `ST.trips`
- Produces:
  - 전역 `CUR` — 열려 있는 여행 객체 또는 `null`
  - `openTrip(t)` / `closeTrip()`
  - `drawDetail()` — Task 4에서 채운다. 이 태스크에서는 빈 함수로 둔다
  - `buildDays(t)` — Task 5에서 채운다. 이 태스크에서는 빈 함수로 둔다

- [ ] **Step 1: CSS를 넣는다**

`index.html:77`의 `code{...}` 규칙 뒤, `</style>` 앞에 넣는다.

```css
#tbl tbody tr{cursor:pointer}
#modal{position:fixed;inset:0;background:rgba(17,24,39,.55);display:none;z-index:20;
  align-items:center;justify-content:center;padding:24px}
#modal.open{display:flex}
#modalBox{background:var(--bg);border-radius:10px;width:min(900px,100%);
  max-height:100%;overflow:auto;padding:18px 20px 16px}
#modalHead{display:flex;align-items:flex-start;gap:10px;margin-bottom:12px}
#modalTitle{flex:1;min-width:0}
#modalTitle .d{font-size:17px;font-weight:700;letter-spacing:-.01em;font-variant-numeric:tabular-nums}
#modalTitle .m{color:var(--ink2);font-size:13px;margin-left:6px}
#modalTitle .p{font-weight:600;margin-top:2px}
#mcv{width:100%;display:block;border-radius:8px;background:var(--bg2);border:1px solid var(--line)}
#days{display:flex;gap:6px;flex-wrap:wrap;margin-top:12px}
.chip{border:1px solid var(--line);border-radius:6px;padding:5px 9px;font-size:12.5px;
  cursor:pointer;background:var(--bg);line-height:1.35;text-align:left}
.chip b{display:block;font-variant-numeric:tabular-nums;font-weight:600}
.chip span{color:var(--ink2);font-size:11.5px}
.chip.on{border-color:var(--blue);background:var(--blue-l)}
.chip.empty span{color:var(--ink3)}
#tileNote{font-size:12.5px;color:var(--ink2);background:var(--bg2);
  border:1px solid var(--line);border-radius:6px;padding:9px 11px;margin-top:10px}
#tileNote button{margin-left:8px}
#attr{font-size:11.5px;color:var(--ink3);margin-top:6px}
#attr a{color:var(--ink2)}
```

- [ ] **Step 2: HTML을 넣는다**

`index.html:133`의 `<div id="tip"></div>` 바로 앞에 넣는다.

```html
<div id="modal">
  <div id="modalBox">
    <div id="modalHead">
      <div id="modalTitle"></div>
      <button id="tiles">배경 지도</button>
      <button id="modalClose">닫기</button>
    </div>
    <canvas id="mcv"></canvas>
    <div id="tileNote" class="hide">
      배경 지도를 켜면 지도 타일을 CARTO 서버에서 받아옵니다. 보고 있는 지역의 좌표가 그 서버로 전달됩니다.
      <button id="tileOk">켜기</button>
    </div>
    <div id="attr" class="hide">지도 데이터 ©
      <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> 기여자 · 타일 ©
      <a href="https://carto.com/attributions" target="_blank" rel="noopener">CARTO</a></div>
    <div id="days"></div>
  </div>
</div>
```

- [ ] **Step 3: 열고 닫기를 구현한다**

`index.html`의 `draw()` 함수 끝(`index.html:567`의 닫는 중괄호) 뒤에 넣는다.

```js
/* ---------- 여행 상세 모달 ---------- */
let CUR=null;                    // 열려 있는 여행
function drawDetail(){}          // Task 4
function buildDays(t){}          // Task 5

function openTrip(t){
  CUR=t;
  const y=dstr(t.a).slice(0,4);
  const range=fmt(t.a)+(t.nights?' ~ '+fmt(t.b):'');
  $('#modalTitle').innerHTML=
    `<span class="d">${y}.${range}</span><span class="m">${t.nights}박 · 최대 ${Math.round(t.km).toLocaleString()}km</span>
     <div class="p">${t.places.map(p=>p.name).join(' · ')||'—'}${t.abroad?'<span class="abroad">해외</span>':''}</div>`;
  $('#modal').classList.add('open');
  buildDays(t);
  drawDetail();
}
function closeTrip(){CUR=null;$('#modal').classList.remove('open');}
```

- [ ] **Step 4: 핸들러를 붙인다**

`index.html`의 `$('#dl').onclick=...` 블록 뒤, `</script>` 앞에 넣는다.

```js
/* 표 행과 지도 마커 둘 다 상세를 연다 */
$('#tbl').onclick=e=>{
  const tr=e.target.closest('tr[data-i]'); if(!tr) return;
  openTrip(ST.trips[+tr.dataset.i]);
};
$('#cv').onclick=e=>{
  const b=e.currentTarget.getBoundingClientRect(), x=e.clientX-b.left, y=e.clientY-b.top;
  for(const m of MK) if((m.x-x)**2+(m.y-y)**2<200){openTrip(m.t);return;}
};
$('#modalClose').onclick=closeTrip;
$('#modal').onclick=e=>{if(e.target===$('#modal')) closeTrip();};
addEventListener('keydown',e=>{if(e.key==='Escape'&&CUR) closeTrip();});
```

`#tbl`에 위임해서 붙이므로 `render()`가 tbody를 다시 그려도 핸들러가 살아 있다.

- [ ] **Step 5: 기존 테스트가 안 깨지는지 본다**

Run: `node test.js`
Expected: PASS — `ok — 41 checks` (모달은 스텁 DOM에서 검증하지 않는다. 최상위에서 `localStorage`·`Image`를 건드리지 않았는지가 여기서 걸린다)

- [ ] **Step 6: 브라우저로 확인한다**

서버를 띄우고 `sample-jp.json`을 주입한 뒤:

1. 표의 `03.07 ~ 03.11` 행을 클릭 → 모달이 열리고 제목이 `2025.03.07 ~ 03.11`, `4박 · 최대 392km`, `오사카부`로 나온다
2. `닫기` / `Esc` / 모달 바깥 어두운 영역 클릭 → 각각 닫힌다
3. 모달 안쪽(흰 상자)을 클릭 → 닫히지 **않는다**
4. 지도의 오키나와 마커를 클릭 → 같은 모달이 그 여행으로 열린다
5. 캔버스는 아직 비어 있다 (Task 4에서 채운다)

- [ ] **Step 7: 커밋**

```bash
git add index.html
git commit -m "여행 상세 모달 뼈대

표 행과 지도 마커 클릭으로 열고, 닫기 버튼·Esc·배경 클릭으로 닫는다.
표 핸들러는 #tbl 에 위임해서 render() 가 tbody 를 다시 그려도 살아
있게 한다. 지도와 날짜 축은 다음 커밋에서 채운다."
```

---

### Task 4: 상세 지도 그리기 — 벡터 배경, 경로, 마커

**Files:**
- Modify: `index.html` — Task 3에서 만든 `drawDetail()` 자리
- Test: 브라우저 수동 확인 + `node test.js` 회귀

**Interfaces:**
- Consumes: `merc`/`fitTrip`(Task 2), `CUR`(Task 3), `ST.days`, `ST.H.at(d)`, `REG`, `HOME_CC`, `t.top`, `t.places[].cc`
- Produces:
  - `tripDays(t) -> [{d, pts}]` — 여행 기간의 날짜별 지점. `pts`는 `[위도,경도][]`, 기록이 없는 날은 빈 배열
  - `drawBackdrop(g, V, W, H, X, Y)` — 배경 레이어. Task 6에서 타일 분기를 넣는다
  - 전역 `SEL` — 선택된 날짜 인덱스 또는 `null`. Task 5에서 설정한다

- [ ] **Step 1: 구현한다**

Task 3에서 넣은 두 줄

```js
let CUR=null;                    // 열려 있는 여행
function drawDetail(){}          // Task 4
```

을 아래 블록으로 교체한다. 바로 아래의 `function buildDays(t){}` 자리표시자는 **그대로 둔다** (Task 5에서 채운다).

```js
let CUR=null, SEL=null;          // 열려 있는 여행 / 선택된 날짜

/* 여행 기간의 날짜별 지점. trips() 의 sum() 이 쓰는 fp(집에서 기준거리 밖만)와
   달리 집을 떠나고 돌아오는 구간까지 담는다 — 그래야 이동이 읽힌다. */
function tripDays(t){
  const out=[];
  for(let d=t.a;d<=t.b;d++) out.push({d,pts:ST.days.get(d)||[]});
  return out;
}

/* 배경. 지금은 벡터뿐이고 Task 6 에서 타일 분기가 붙는다. */
function drawBackdrop(g,V,W,H,X,Y){
  const ccs=new Set(CUR.places.map(p=>p.cc).filter(Boolean));
  if(HOME_CC) ccs.add(HOME_CC);
  g.lineWidth=.6; g.strokeStyle='#fff'; g.fillStyle='#eceff3';
  for(const cc of ccs) for(const f of (REG.get(cc)||[])){
    for(let k=0;k<f[1].length;k++){
      const bb=f[3][k];                       // [최소경도,최소위도,최대경도,최대위도]
      const x0=X(bb[3],bb[0]), y0=Y(bb[3],bb[0]), x1=X(bb[1],bb[2]), y1=Y(bb[1],bb[2]);
      if(x1<0||x0>W||y1<0||y0>H) continue;    // 화면 밖 링은 건너뛴다
      const ring=f[1][k];
      g.beginPath(); g.moveTo(X(ring[1],ring[0]),Y(ring[1],ring[0]));
      for(let i=2;i<ring.length;i+=2) g.lineTo(X(ring[i+1],ring[i]),Y(ring[i+1],ring[i]));
      g.closePath(); g.fill(); g.stroke();
    }
  }
}

function drawDetail(){
  const t=CUR; if(!t) return;
  const cv=$('#mcv'), W=cv.clientWidth||860, H=Math.round(Math.min(W*.52,440));
  const dpr=devicePixelRatio||1;
  cv.width=W*dpr; cv.height=H*dpr; cv.style.height=H+'px';
  const g=cv.getContext('2d'); g.setTransform(dpr,0,0,dpr,0,0);
  g.clearRect(0,0,W,H);

  const DD=tripDays(t);
  const all=[].concat(...DD.map(r=>r.pts));
  // 날짜를 고르면 그 날에 맞춰 다시 확대한다. 전체 보기로는 도시 안 이동이 안 보인다.
  const fitPts=(SEL!=null&&(ST.days.get(SEL)||[]).length)?ST.days.get(SEL):all;
  const V=fitTrip(fitPts,W,H); if(!V) return;
  // 날짜변경선을 건너는 여행은 fitTrip 이 경도를 풀어서 잡았으므로 여기서도 같은 규칙을 쓴다
  const wl=lo=>V.wrap&&lo<0?lo+360:lo;
  const X=(la,lo)=>merc(la,wl(lo),V.z)[0]+V.ox, Y=(la,lo)=>merc(la,wl(lo),V.z)[1]+V.oy;

  drawBackdrop(g,V,W,H,X,Y);

  // 날짜별 경로 — 첫날이 가장 옅고 마지막 날이 가장 진하다
  const nd=Math.max(DD.length-1,1);
  DD.forEach((row,i)=>{
    if(row.pts.length<2) return;
    const on=SEL==null||SEL===row.d;
    g.globalAlpha=on?.9:.12;
    g.lineWidth=on?2.2:1.2;
    g.strokeStyle=`hsl(217,90%,${68-i/nd*32}%)`;
    g.beginPath();
    g.moveTo(X(row.pts[0][0],row.pts[0][1]),Y(row.pts[0][0],row.pts[0][1]));
    for(let k=1;k<row.pts.length;k++) g.lineTo(X(row.pts[k][0],row.pts[k][1]),Y(row.pts[k][0],row.pts[k][1]));
    g.stroke();
  });
  g.globalAlpha=1;

  for(const c of t.top){                       // 목적지 군집
    g.beginPath(); g.arc(X(c[0],c[1]),Y(c[0],c[1]),5,0,7);
    g.fillStyle='rgba(59,130,246,.85)'; g.fill();
    g.strokeStyle='#fff'; g.lineWidth=1.5; g.stroke();
  }
  const h=ST.H.at(t.a), hx=X(h[0],h[1]), hy=Y(h[0],h[1]);
  if(hx>=0&&hx<=W&&hy>=0&&hy<=H){              // 집은 범위 안일 때만
    g.beginPath(); g.arc(hx,hy,5,0,7); g.fillStyle='#111827'; g.fill();
    g.strokeStyle='#fff'; g.lineWidth=2; g.stroke();
    g.font='600 11px -apple-system,sans-serif'; g.fillStyle='#111827';
    g.fillText('집',hx+9,hy+4);
  }
}
```

- [ ] **Step 2: 회귀를 확인한다**

Run: `node test.js`
Expected: PASS — `ok — 41 checks`

- [ ] **Step 3: 브라우저로 확인한다**

`sample-jp.json` 주입 후:

1. `03.07 ~ 03.11` (오사카) 행 클릭 → 혼슈 서부가 회색 폴리곤으로 깔리고, 도쿄에서 오사카로 가는 선이 보이고, 집 마커와 목적지 마커가 찍힌다
2. 선 색이 첫날 옅은 파랑 → 마지막 날 진한 파랑으로 간다
3. `12.30 ~ 01.02` (나하) 행 클릭 → 도쿄와 오키나와가 모두 화면 안에 들어온다
4. `sample-us.json`으로 바꿔 `12.30 ~ 01.02` (호놀룰루) 클릭 → 태평양이 다 들어오고 폴리곤이 없는 바다 위에 선만 뜬다. 깨지지 않는다
5. 브라우저 콘솔에 오류가 없다

- [ ] **Step 4: 커밋**

```bash
git add index.html
git commit -m "상세 지도에 벡터 배경과 날짜별 경로를 그린다

경로 입력은 ST.days 의 기간 내 전체 지점이다. trips() 가 쓰는 fp 는
집에서 기준거리 밖 지점만이라 떠나고 돌아오는 구간이 빠진다.
선 색은 첫날이 옅고 마지막 날이 진한 램프로 진행 방향을 보인다.
폴리곤은 링 bbox 로 화면 밖을 걸러 낸다."
```

---

### Task 5: 날짜 칩 타임라인

**Files:**
- Modify: `index.html` — Task 3에서 비워 둔 `buildDays(t)`, 핸들러 구역
- Test: `test.js` (`dayLabel`) + 브라우저 수동 확인

**Interfaces:**
- Consumes: `tripDays`(Task 4), `SEL`(Task 4), `placeName`(index.html:231), `fmt`(index.html:424)
- Produces: `dayLabel(pts) -> string` — 그 날 지점이 가장 많은 군집의 지명. 빈 배열이면 `''`

**기존 `shortName`을 쓰지 않는다.** `shortName`(index.html:490)은 `/구$/`인 마지막 토큰을 떼어 내므로 `서울특별시 서초구` → `서울특별시`가 된다. 여행 전체의 목적지 라벨로는 맞지만, 여행 **안에서** 하루를 가리킬 때는 `서초구`가 `서울특별시`보다 정확하다. 칩 전용으로 마지막 토큰만 취하는 규칙을 `dayLabel` 안에 둔다.

**스펙에서 의도적으로 벗어나는 점 하나.** 스펙은 "호버·클릭하면 그 날 구간만 강조"라고 썼지만 클릭만 구현한다. 날짜 선택이 지도를 그 날 범위로 다시 확대하기 때문에, 호버로도 같은 일이 일어나면 표 위로 마우스가 지나갈 때마다 지도가 튄다. 호버 강조를 되살리려면 확대는 클릭에만 걸고 호버는 선 굵기만 바꾸는 식으로 둘을 분리해야 한다 — 지금은 넣지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`test.js`의 Task 2 묶음 뒤에 넣는다. `HOME_CC`는 앞에서 `"KR"`로 설정돼 있다.

```js
  // --- 날짜 칩 지명 ---------------------------------------------------------
  // 서초 3점 + 통영 1점이면 그 날은 서초로 대표된다 (가장 먼 곳이 아니라 가장 오래 있은 곳)
  eq(ctx.dayLabel([[37.50173,127.01317],[37.50180,127.01320],[37.50150,127.01300],
                   [34.76830,128.40770]]), '서초구', '칩 지명: 최다 군집');
  eq(ctx.dayLabel([]), '', '칩 지명: 기록 없는 날은 빈 문자열');
  // 해외는 "Tokyo, 일본" 꼴이라 국가명을 뗀다
  eq(ctx.dayLabel([[35.70700,139.77300]]), 'Tokyo', '칩 지명: 해외는 도시명만');
  // shortName 을 그대로 썼다면 여기서 '서울특별시'가 나와 첫 검사가 깨진다
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node test.js`
Expected: FAIL — `ctx.dayLabel is not a function`

- [ ] **Step 3: 구현한다**

`drawDetail()` 뒤에 넣고, Task 3에서 비워 둔 `function buildDays(t){}`를 지운 뒤 아래로 대체한다.

```js
/* 그 날 지점이 가장 많은 군집의 중심으로 이름을 붙인다. 집에서 가장 먼
   지점보다 그 날 실제로 보낸 곳을 대표한다. 격자 크기는 trips() 의 sum() 과 맞춘다. */
function dayLabel(pts){
  if(!pts.length) return '';
  const cl=new Map();
  for(const p of pts){
    const k=p[0].toFixed(1)+','+p[1].toFixed(1);
    if(!cl.has(k)) cl.set(k,{n:0,la:0,lo:0});
    const c=cl.get(k); c.n++; c.la+=p[0]; c.lo+=p[1];
  }
  let best=null;
  for(const c of cl.values()) if(!best||c.n>best.n) best=c;
  const nm=placeName(best.la/best.n,best.lo/best.n).name;
  // 칩이 좁으니 마지막 토큰만 쓴다. shortName 과 달리 구를 떼지 않는다 —
  // 여행 안에서 하루를 가리킬 때는 "서초구"가 "서울특별시"보다 정확하다.
  return nm.includes(', ')?nm.split(', ')[0]:nm.split(' ').pop();
}

function buildDays(t){
  SEL=null;
  $('#days').innerHTML=tripDays(t).map(r=>{
    const lb=dayLabel(r.pts);
    return `<button class="chip${lb?'':' empty'}" data-d="${r.d}">
      <b>${fmt(r.d)}</b><span>${lb||'기록 없음'}</span></button>`;
  }).join('');
}
```

- [ ] **Step 4: 핸들러를 붙인다**

Task 3에서 넣은 `addEventListener('keydown',...)` 뒤에 넣는다.

```js
/* 날짜를 고르면 그 날만 강조하고 그 날 범위로 다시 확대한다. 다시 누르면 전체로 돌아온다. */
$('#days').onclick=e=>{
  const c=e.target.closest('.chip'); if(!c) return;
  const d=+c.dataset.d;
  SEL=SEL===d?null:d;
  document.querySelectorAll('#days .chip').forEach(x=>x.classList.toggle('on',+x.dataset.d===SEL));
  drawDetail();
};
```

- [ ] **Step 5: 통과를 확인한다**

Run: `node test.js`
Expected: PASS — `ok — 44 checks` (41 + 이 태스크의 3)

- [ ] **Step 6: 브라우저로 확인한다**

`sample-jp.json` 주입 후 `03.07 ~ 03.11` 행 클릭:

1. 지도 아래에 칩 5개가 `03.07` ~ `03.11`로 뜨고 각각 아래에 지명이 붙는다
2. `03.09` 칩 클릭 → 파랗게 변하고, 지도가 그 날 범위로 확대되며 그 날 선만 진하게 남는다
3. 같은 칩을 다시 클릭 → 선택이 풀리고 전체 범위로 돌아온다
4. 다른 여행을 열면 선택이 초기화된 채로 열린다
5. 기록이 없는 날이 있으면 흐린 `기록 없음` 칩으로 남는다

- [ ] **Step 7: 커밋**

```bash
git add index.html test.js
git commit -m "상세 모달에 날짜 칩 타임라인 추가

하루당 칩 하나. 고르면 그 날 경로만 진하게 남기고 그 날 범위로 다시
확대한다 — 전체 보기로는 도시 안 이동이 안 보인다. 칩 지명은 그 날
지점이 가장 많은 군집으로 붙인다. 기록이 없는 날은 빈 칩으로 남겨
공백이 드러나게 한다."
```

---

### Task 6: 배경 지도 옵트인 토글

README가 "외부 API도 호출하지 않습니다"를 약속한다. 타일 요청의 z/x/y는 곧 방문지 좌표이므로 기본값으로 켜지 않는다. 명시적으로 켤 때만, 무엇이 나가는지 알린 뒤에 받아온다.

**Files:**
- Modify: `index.html` — `drawBackdrop` 분기, 새 `drawTiles`, 토글 핸들러
- Modify: `README.md` — 외부 요청 관련 문구
- Test: 브라우저 수동 확인 + `node test.js` 회귀

**Interfaces:**
- Consumes: `TILE`/`ZMAX`(Task 2), `drawDetail`(Task 4), `CUR`(Task 3)
- Produces: 전역 `TILES`(boolean), `drawTiles(g, V, W, H)`, `prefGet(k)`/`prefSet(k, v)`

- [ ] **Step 1: 타일 레이어를 구현한다**

`drawBackdrop` 함수 바로 앞에 넣는다.

```js
/* ---------- 배경 타일 (옵트인) ----------
   기본은 꺼짐. 켜야만 요청이 나간다. localStorage 와 Image 는 test.js 의
   스텁 컨텍스트에 없으므로 반드시 함수 안에서만 건드린다. */
let TILES=false;
const TILEC=new Map();
let TRAF=0;
function prefGet(k){try{return localStorage.getItem(k);}catch(e){return null;}}
function prefSet(k,v){try{localStorage.setItem(k,v);}catch(e){}}

function drawTiles(g,V,W,H){
  const n=Math.pow(2,V.z);
  const x0=Math.floor(-V.ox/TILE), x1=Math.floor((W-V.ox)/TILE);
  const y0=Math.max(0,Math.floor(-V.oy/TILE)), y1=Math.min(n-1,Math.floor((H-V.oy)/TILE));
  for(let x=x0;x<=x1;x++) for(let y=y0;y<=y1;y++){
    const tx=((x%n)+n)%n, k=V.z+'/'+tx+'/'+y;
    let im=TILEC.get(k);
    if(!im){
      im=new Image();       // crossOrigin 은 설정하지 않는다. 픽셀을 읽지 않으므로
                            // 불필요하고, CORS 헤더가 없는 응답에서 오히려 실패한다.
      // 타일이 도착할 때마다 다시 그린다. 프레임당 한 번으로 묶는다.
      im.onload=()=>{if(CUR&&!TRAF) TRAF=requestAnimationFrame(()=>{TRAF=0;drawDetail();});};
      im.onerror=()=>{};                      // 실패한 타일은 벡터 없이 빈 칸으로 둔다
      im.src='https://a.basemaps.cartocdn.com/light_all/'+V.z+'/'+tx+'/'+y+'.png';
      TILEC.set(k,im);
    }
    if(im.complete&&im.naturalWidth) g.drawImage(im,x*TILE+V.ox,y*TILE+V.oy,TILE,TILE);
  }
}
```

- [ ] **Step 2: `drawBackdrop`에 분기를 넣는다**

Task 4에서 쓴 `drawBackdrop`의 첫 줄에 한 줄을 추가한다.

```js
function drawBackdrop(g,V,W,H,X,Y){
  if(TILES) return drawTiles(g,V,W,H);
  const ccs=new Set(CUR.places.map(p=>p.cc).filter(Boolean));
```

- [ ] **Step 3: 토글 핸들러를 붙인다**

Task 5의 `$('#days').onclick` 뒤에 넣는다.

```js
/* 처음 켤 때는 무엇이 어디로 나가는지 알리고 한 번 더 누르게 한다. */
function setTiles(v){
  TILES=v; prefSet('tt.tiles',v?'1':'0');
  $('#tiles').classList.toggle('on',v);
  $('#attr').classList.toggle('hide',!v);
  drawDetail();
}
$('#tiles').onclick=()=>{
  if(TILES) return setTiles(false);
  if(prefGet('tt.tiles')===null) $('#tileNote').classList.remove('hide');
  else setTiles(true);
};
$('#tileOk').onclick=()=>{$('#tileNote').classList.add('hide'); setTiles(true);};
```

`openTrip`의 `$('#modal').classList.add('open');` 바로 앞에 저장된 선택을 반영하는 두 줄을 넣는다.

```js
  setTiles(prefGet('tt.tiles')==='1');
  $('#tileNote').classList.add('hide');
```

- [ ] **Step 4: README를 고친다**

`README.md`의 다음 문장을 찾는다.

> 파일은 브라우저 안에서만 처리합니다. 업로드하거나 서버에 저장하지 않으며, 외부 API도 호출하지 않습니다. 지명은 프로젝트에 포함된 경계와 도시 데이터로 찾습니다.

다음으로 교체한다.

> 파일은 브라우저 안에서만 처리합니다. 업로드하거나 서버에 저장하지 않습니다. 지명은 프로젝트에 포함된 경계와 도시 데이터로 찾으며, 기본 상태에서는 외부 API를 호출하지 않습니다.
>
> 예외는 여행 상세의 **배경 지도** 하나입니다. 기본값은 꺼짐이고, 직접 켤 때만 CARTO에서 지도 타일을 받아옵니다. 이때 보고 있는 지역의 타일 좌표가 그 서버로 전달됩니다. 위치 기록 파일 자체는 어느 경우에도 브라우저 밖으로 나가지 않습니다.

`## 알려진 한계` 목록에 한 줄을 추가한다.

```markdown
- 상세 지도의 배경 타일은 CARTO 무료 사용에 기대고 있어, 제공자 사정에 따라 나오지 않을 수 있습니다. 이때는 배경 없이 경로만 표시됩니다.
```

- [ ] **Step 5: 회귀를 확인한다**

Run: `node test.js`
Expected: PASS — `ok — 44 checks` (최상위에서 `localStorage`·`Image`·`requestAnimationFrame`을 건드렸다면 여기서 죽는다)

- [ ] **Step 6: 브라우저로 확인한다**

브라우저 개발자도구에서 `localStorage.removeItem('tt.tiles')`로 초기화한 뒤:

1. 여행을 열고 `배경 지도`를 누른다 → 타일이 바로 오지 **않고** 안내 문구와 `켜기` 버튼이 뜬다
2. Network 탭을 열어 둔 채 `켜기` → `basemaps.cartocdn.com` 요청이 그때 처음 나간다. 지도에 실제 지형이 깔리고 하단에 OpenStreetMap·CARTO 저작자 표시가 뜬다
3. 경로선과 마커가 타일과 어긋나지 않는다 (도로·해안선 위에 자연스럽게 얹힌다)
4. `배경 지도`를 다시 눌러 끈다 → 벡터 배경으로 돌아오고 저작자 표시가 사라진다
5. 모달을 닫고 다른 여행을 연다 → 마지막 선택이 유지된다. 페이지를 새로고침해도 유지된다
6. 안내 문구는 다시 뜨지 않는다
7. Network 탭에서 오프라인으로 바꾸고 새 여행을 열어 본다 → 타일이 빈 칸이지만 경로와 마커는 그려지고 콘솔 오류가 없다

- [ ] **Step 7: 커밋**

```bash
git add index.html README.md
git commit -m "상세 지도 배경 타일을 옵트인으로 추가

타일 요청의 z/x/y 는 곧 방문지 좌표라 기본값으로 켜지 않는다. 처음
켤 때 무엇이 어디로 나가는지 알리고 한 번 더 누르게 한다. 선택은
localStorage 에 남긴다. 제공자는 CARTO Positron — 밝은 저채도라
경로선이 잘 뜨고 API 키가 필요 없다. README 의 외부 요청 문구를
실제 동작에 맞춘다."
```

---

## 마무리

- [ ] **전체 회귀**

Run: `node test.js`
Expected: `ok — 44 checks`

- [ ] **세 가지 거주국으로 훑는다**

`sample-kr.json` / `sample-us.json` / `sample-jp.json`을 차례로 주입해 각 여행을 하나씩 열어 본다. 확인할 것: 모달이 열리고, 경로가 그려지고, 칩이 기간과 맞고, 콘솔 오류가 없다. 해외 여행(도쿄·서울)과 태평양 횡단(호놀룰루)이 특히 극단값이다.

- [ ] **스펙과 대조한다**

`docs/superpowers/specs/2026-08-20-trip-detail-map-design.md`를 다시 읽고 빠진 요구사항이 없는지 본다.

## 이 계획이 다루지 않는 것

- 팬·줌
- 지명 해상도 역전 (해외가 주·도 단위라 자국 여행이 타국보다 뭉뚱그려진다). README `알려진 한계`에 이미 있는 별건이다
- `sample-*.json`의 저장소 편입 여부 — 미결

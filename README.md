# 여행 타임라인

Google Timeline 내보내기(`location-history.json`)에서 **집을 찾아내고**, 집에서 멀리
떠났던 일정을 **여행으로 묶어** 지도·목록으로 보여주는 정적 페이지.

파일은 브라우저 밖으로 나가지 않는다. 업로드도, 서버 저장도, 외부 API 호출도 없다.
지명은 함께 배포되는 경계·도시 데이터(`geo.json`, 894KB)로 브라우저에서 직접 붙인다.

```
index.html   앱 전체 (파싱·집 추정·여행 판정·지명·지도)
geo.json     시·군·구 250개 경계 + 국가 177개 + 세계 도시 11,336개
prep.py      geo.json 빌드 (원본은 .cache/ 에 자동 내려받음)
test.js      node test.js
```

## 쓰기

```sh
python3 -m http.server 8000    # file:// 은 fetch가 막히므로 서버가 필요하다
```

내보내기 경로: Google 지도 앱 → 설정 → 위치 기록 → 타임라인 데이터 내보내기

## 어떻게 판정하나

**집** — `semanticType`이 `Home`인 체류를 ±60일 창으로 굴려가며 1km 격자에 모아
가장 오래 머문 격자의 가중 중심을 그 시점의 집으로 본다. 창을 굴리기 때문에
이사를 하면 기준 집도 따라 옮겨간다. 이게 없으면 이주 기간 전체가 여행 한 건으로 잡힌다.

Home 라벨이 없는 사용자는 현지 시각 03시에 걸친 체류로 대신 추정한다.
실측 데이터에서 두 방식의 결과 차이는 2km 미만이었다(`test.js`가 검증한다).

**여행** — 하루 중 집에서 가장 멀어진 거리가 기준을 넘는 날을 이어 붙인다.
기준 기본값은 일별 최대거리의 90분위 × 4 (50–150km로 제한)이고 슬라이더로 조정한다.
2일 이내 공백은 같은 여행으로 잇고, 6일 이내 공백이라도 목적지가 300km 안이면 합친다.

**지명** — 국내는 행정구역 경계에 대한 point-in-polygon이라 역지오코딩보다 정확하다.
해외는 국가 경계 + 인구 가중 최근접 도시(10배 작은 도시는 12km 더 가까워야 이긴다).
이 보정이 없으면 도쿄가 "Chuo", 샌프란시스코가 "Chinatown"으로 나온다.

## 알려진 한계

- 기록이 희박한 기간의 여행은 나타나지 않는다. 화면 상단 "기록 밀도"가 그 구간을 표시한다.
- 예전 Takeout 형식(`timelineObjects`)과 원시 `Records.json`은 감지만 하고 지원하지 않는다.
- 하루 안에 다녀온 먼 정기 방문(본가 등)도 여행으로 잡힌다.

## 데이터 출처

- 행정구역 경계 — [southkorea/southkorea-maps](https://github.com/southkorea/southkorea-maps) (KOSTAT 2018)
- 국가 경계·한글 국가명 — [Natural Earth](https://github.com/nvkelso/natural-earth-vector) 110m/50m
- 세계 도시 — [GeoNames](https://download.geonames.org/export/dump/) cities15000

## 테스트

```sh
node test.js
```

좌표 픽스처는 개인 데이터 없이 돈다. 본인 내보내기 파일을 `lh.json`으로 심볼릭 링크하면
집·여행 판정까지 종단 검증한다 (`.gitignore`에 들어 있다).

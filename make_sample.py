#!/usr/bin/env python3
"""sample.json 생성 — 실제 기록 없이 앱을 둘러볼 수 있게 만든 가상의 2년치 타임라인.

Google 지도 타임라인 내보내기(iPhone) 와 같은 모양으로 적는다: 최상위가 배열이고
visit / activity / timelinePath 세 종류의 구간이 시각순으로 늘어선다.
좌표·장소는 모두 지어낸 것이며 실존 인물의 기록이 아니다.

python3 make_sample.py > sample.json
"""
import json, math, random, sys
from datetime import datetime, timedelta, timezone

random.seed(20240101)                      # 돌릴 때마다 같은 파일이 나오게

KST = timezone(timedelta(hours=9))
ICT = timezone(timedelta(hours=7))         # 방콕 — 오프셋 파싱까지 훑는다

HOME  = (37.55590, 126.93680)              # 서울 서대문구
WORK  = (37.50060, 127.03660)              # 강남구 역삼
CAFE  = (37.55850, 126.94000)              # 집 앞 카페 — 30분 넘게 머문다
STORE = (37.55180, 126.94350)              # 역 앞 편의점 — 몇 분씩만 들른다.
                                           # 집에서 600m — 더 가까우면 집으로 걸러진다
GYM   = (37.56450, 126.94620)
STOP  = (37.50450, 127.02480)              # 회사 앞 지하철역 — 스쳐 가는 곳
MART  = (37.54200, 126.95200)
FOLKS = (37.35950, 127.10520)              # 분당 부모님 댁
VIA_M = (37.52600, 126.97400)              # 아침에 지나는 길
VIA_E = (37.53900, 126.95900)              # 저녁에 지나는 다른 길

PLACE = {HOME:('sample-home','Home'), WORK:('sample-work','Work'),
         CAFE:('sample-cafe','Unknown'), STORE:('sample-store','Unknown'),
         GYM:('sample-gym','Unknown'), MART:('sample-mart','Unknown'),
         STOP:('sample-stop','Unknown'),
         FOLKS:('sample-folks','Unknown')}

OUT = []

def iso(dt): return dt.strftime('%Y-%m-%dT%H:%M:%S.000%z')[:-2] + ':' + dt.strftime('%z')[-2:]
def geo(p):  return 'geo:%.5f,%.5f' % p      # 1m 남짓이면 충분하다 — 파일이 절반으로 준다

def visit(start, minutes, pos, pid=None, kind=None, tz=KST):
    pid  = pid  or PLACE.get(pos, ('sample-spot','Unknown'))[0]
    kind = kind or PLACE.get(pos, ('sample-spot','Unknown'))[1]
    OUT.append({'startTime': iso(start.astimezone(tz)),
                'endTime':   iso((start+timedelta(minutes=minutes)).astimezone(tz)),
                'visit': {'hierarchyLevel': '0', 'probability': '0.90',
                          'topCandidate': {'probability': '0.90', 'semanticType': kind,
                                           'placeID': pid, 'placeLocation': geo(pos)}}})

def hav(a, b):
    R, p1, p2 = 6371.0, math.radians(a[0]), math.radians(b[0])
    dp, dl = p2-p1, math.radians(b[1]-a[1])
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(min(1, math.sqrt(h)))

def move(start, minutes, a, b, via=None, n=5, jitter=0.0007, tz=KST):
    """이동 구간. 같은 시간대를 activity 와 timelinePath 로 한 번씩 적는다 —
       실제 내보내기도 그렇게 겹쳐 적는다."""
    end = start + timedelta(minutes=minutes)
    OUT.append({'startTime': iso(start.astimezone(tz)), 'endTime': iso(end.astimezone(tz)),
                'activity': {'start': geo(a), 'end': geo(b),
                             'distanceMeters': '%.1f' % (hav(a, b)*1000),
                             'topCandidate': {'type': 'in passenger vehicle', 'probability': '0.85'}}})
    knots = [a] + ([via] if via else []) + [b]
    pts = []
    for i in range(n+1):
        u = i/n * (len(knots)-1)
        k = min(int(u), len(knots)-2)
        f = u-k
        la = knots[k][0] + (knots[k+1][0]-knots[k][0])*f + random.uniform(-jitter, jitter)
        lo = knots[k][1] + (knots[k+1][1]-knots[k][1])*f + random.uniform(-jitter, jitter)
        pts.append({'point': geo((la, lo)),
                    'durationMinutesOffsetFromStartTime': str(round(minutes*i/n))})
    OUT.append({'startTime': iso(start.astimezone(tz)), 'endTime': iso(end.astimezone(tz)),
                'timelinePath': pts})

def at(day, h, m=0, tz=KST): return datetime(day.year, day.month, day.day, h, m, tzinfo=tz)

TRIPS = [  # (첫날, 마지막밤, 숙소, 볼거리, 시간대, placeID)
    (datetime(2024,5,3),  datetime(2024,5,5),  (37.75190,128.87610), (37.79500,128.91600), KST, 'sample-gangneung'),
    (datetime(2024,5,8),  datetime(2024,5,9),  (34.76040,127.66220), (34.74100,127.73400), KST, 'sample-yeosu'),
    (datetime(2024,8,10), datetime(2024,8,13), (33.49960,126.53120), (33.24970,126.36090), KST, 'sample-jeju'),
    (datetime(2025,2,14), datetime(2025,2,17), (35.67620,139.65030), (35.71010,139.81070), KST, 'sample-tokyo'),
    (datetime(2025,9,20), datetime(2025,9,22), (35.17960,129.07560), (35.15870,129.16030), KST, 'sample-busan'),
    (datetime(2025,11,5), datetime(2025,11,9), (13.75630,100.50180), (13.72460,100.49300), ICT, 'sample-bangkok'),
]

def trip_on(day):
    for a, b, hotel, spot, tz, pid in TRIPS:
        if a.date() <= day.date() <= (b + timedelta(days=1)).date():
            return a, b, hotel, spot, tz, pid
    return None

DAY0, DAY1 = datetime(2024,1,1), datetime(2025,12,31)
day = DAY0
while day <= DAY1:
    t = trip_on(day)
    if t:
        a, b, hotel, spot, tz, pid = t
        if day.date() == a.date():                       # 떠나는 날
            move(at(day,9), 60, HOME, hotel, tz=KST, n=10, jitter=0.004)
            visit(at(day,12,tz=tz), 240, spot, pid+'-spot', 'Unknown', tz=tz)
        elif day.date() == (b+timedelta(days=1)).date():  # 돌아오는 날
            move(at(day,11,tz=tz), 60, hotel, HOME, tz=KST, n=10, jitter=0.004)
            visit(at(day,22,30), 540, HOME)               # 그 밤은 집에서 잔다
        else:
            visit(at(day,10,tz=tz), 300, spot, pid+'-spot', 'Unknown', tz=tz)
        if day.date() <= b.date():
            visit(at(day,23,tz=tz), 480, hotel, pid, 'Unknown', tz=tz)   # 숙소에서 밤을 넘긴다
        day += timedelta(days=1); continue

    visit(at(day,22,30), 540, HOME)                       # 집에서 자는 밤 (새벽 3시를 넘긴다)
    wd = day.weekday()
    if wd < 5:                                            # 평일
        if random.random() < .55: visit(at(day,7,40), 35, CAFE)          # 방문
        move(at(day,8,20), 45, HOME, WORK, via=VIA_M)
        visit(at(day,9,10), 545, WORK)
        move(at(day,18,20), 50, WORK, HOME, via=VIA_E)
        if random.random() < .45: visit(at(day,8,58), 5, STOP)           # 경유
        if random.random() < .6:  visit(at(day,19,25), 7, STORE)         # 경유
        if random.random() < .35: visit(at(day,20,0), 70, GYM)           # 방문
    else:                                                 # 주말
        if random.random() < .4:  visit(at(day,14,0), 45, MART)
        if random.random() < .5:  visit(at(day,19,10), 6, STORE)
        if wd == 5 and day.day <= 7:                                     # 매달 첫 토요일
            move(at(day,11,0), 55, HOME, FOLKS, n=9, jitter=0.002)
            visit(at(day,12,0), 330, FOLKS)
            move(at(day,18,0), 60, FOLKS, HOME, n=9, jitter=0.002)
    day += timedelta(days=1)

OUT.sort(key=lambda r: r['startTime'])
json.dump(OUT, sys.stdout, ensure_ascii=False, separators=(',', ':'))

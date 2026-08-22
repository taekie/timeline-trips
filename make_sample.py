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
PDT = timezone(timedelta(hours=-7))        # 샌프란시스코 — 날짜변경선 건너편

HOME  = (37.55590, 126.93680)              # 서울 서대문구
WORK  = (37.50060, 127.03660)              # 첫 직장 — 강남구 역삼 (2024.9 까지)
WORK2 = (37.54470, 127.05590)              # 옮긴 직장 — 성동구 성수 (2024.10 부터)
CAFE  = (37.55850, 126.94000)              # 집 앞 카페 — 30분 넘게 머문다
STORE = (37.55180, 126.94350)              # 역 앞 편의점 — 몇 분씩만 들른다.
                                           # 집에서 600m — 더 가까우면 집으로 걸러진다
GYM   = (37.56450, 126.94620)
STOP  = (37.50450, 127.02480)              # 회사 앞 지하철역 — 스쳐 가는 곳
MART  = (37.54200, 126.95200)
FOLKS = (37.35950, 127.10520)              # 분당 부모님 댁
VIA_M = (37.52600, 126.97400)              # 아침에 흔히 지나는 길
VIA_M2= (37.51200, 126.99600)              # 가끔 도는 다른 길
VIA_E = (37.53900, 126.95900)              # 저녁에 지나는 또 다른 길

PLACE = {HOME:('sample-home','Home'), WORK:('sample-work','Work'),
         WORK2:('sample-work2','Work'),
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
    """이동 구간. 긴 이동은 activity 와 timelinePath 로 한 번씩 겹쳐 적는다 —
       실제 내보내기도 그렇게 적는다. 몇 분짜리 도보는 자취만 남긴다."""
    end = start + timedelta(minutes=minutes)
    if minutes >= 15:
        OUT.append({'startTime': iso(start.astimezone(tz)), 'endTime': iso(end.astimezone(tz)),
                    'activity': {'start': geo(a), 'end': geo(b),
                                 'distanceMeters': '%.1f' % (hav(a, b)*1000),
                                 'topCandidate': {'type': 'in passenger vehicle', 'probability': '0.85'}}})
    # 태평양을 건널 때 경도를 그냥 이으면 지구를 반대로 한 바퀴 돌아 대서양 위를
    # 지난다. 이웃한 지점끼리 180도를 넘지 않게 풀어 두고, 찍을 때 다시 접는다.
    knots = [a] + ([via] if via else []) + [b]
    un = [knots[0]]
    for q in knots[1:]:
        lo = q[1]
        while lo - un[-1][1] >  180: lo -= 360
        while lo - un[-1][1] < -180: lo += 360
        un.append((q[0], lo))
    knots = un
    pts = []
    for i in range(n+1):
        u = i/n * (len(knots)-1)
        k = min(int(u), len(knots)-2)
        f = u-k
        la = knots[k][0] + (knots[k+1][0]-knots[k][0])*f + random.uniform(-jitter, jitter)
        lo = knots[k][1] + (knots[k+1][1]-knots[k][1])*f + random.uniform(-jitter, jitter)
        lo = ((lo + 180) % 360) - 180
        pts.append({'point': geo((la, lo)),
                    'durationMinutesOffsetFromStartTime': str(round(minutes*i/n))})
    OUT.append({'startTime': iso(start.astimezone(tz)), 'endTime': iso(end.astimezone(tz)),
                'timelinePath': pts})

def at(day, h, m=0, tz=KST): return datetime(day.year, day.month, day.day, h, m, tzinfo=tz)

# 하루에 한 곳만 들르는 여행은 없다. 날마다 두세 곳씩 돌게 해야 상세 지도에
# 그날의 동선이 보인다. (첫날, 마지막밤, 숙소, 볼거리 여럿, 시간대, placeID)
TRIPS = [
    (datetime(2024,5,3),  datetime(2024,5,5),  (37.75190,128.87610),
     [(37.79550,128.89600),(37.77300,128.94700),(37.77900,128.87800)], KST, 'sample-gangneung'),
    (datetime(2024,5,8),  datetime(2024,5,9),  (34.76040,127.66220),
     [(34.74200,127.75400),(34.59900,127.81800)], KST, 'sample-yeosu'),
    (datetime(2024,8,10), datetime(2024,8,13), (33.49960,126.53120),
     [(33.45800,126.94200),(33.24970,126.56090),(33.39400,126.24000)], KST, 'sample-jeju'),
    (datetime(2025,2,14), datetime(2025,2,17), (35.67620,139.65030),
     [(35.71480,139.79670),(35.65800,139.70160),(35.63000,139.77600),(35.71380,139.77700)], KST, 'sample-tokyo'),
    (datetime(2025,6,12), datetime(2025,6,19), (37.78780,-122.40750),
     [(37.80800,-122.41770),(37.81990,-122.47830),(37.75440,-122.44770),
      (37.75960,-122.42690),(37.79550,-122.39370)], PDT, 'sample-sf'),
    (datetime(2025,9,20), datetime(2025,9,22), (35.17960,129.07560),
     [(35.15870,129.16030),(35.09750,129.01070),(35.15330,129.11860)], KST, 'sample-busan'),
    (datetime(2025,11,5), datetime(2025,11,9), (13.75630,100.50180),
     [(13.75000,100.49130),(13.75900,100.49700),(13.79990,100.55000)], ICT, 'sample-bangkok'),
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
        a, b, hotel, spots, tz, pid = t
        i = (day - a).days
        seen = None
        if day.date() == (b+timedelta(days=1)).date():    # 돌아오는 날
            # 돌아오는 자취는 집 시간으로 적는다 — 현지 시간으로 두면 날짜변경선을
            # 건널 때 하루 넘어가서 0박짜리 유령 여행이 하나 더 생긴다
            move(at(day,15), 60, hotel, HOME, n=10, jitter=0.004)
            visit(at(day,22,30), 540, HOME)               # 그 밤은 집에서 잔다
            day += timedelta(days=1); continue
        if day.date() == a.date():                        # 떠나는 날 — 도착하고 한 곳만
            move(at(day,9), 60, HOME, hotel, tz=KST, n=10, jitter=0.004)
            seen, cur = spots[:1], at(day,14,tz=tz)
        else:                                             # 날마다 도는 곳 수를 바꾼다
            k = min(len(spots), 2 + ((i+1) % 3))
            seen = [spots[(i*2+j) % len(spots)] for j in range(k)]
            cur = at(day,10,tz=tz)
        prev = hotel
        for sp in seen:
            move(cur, 25, prev, sp, tz=tz, n=5, jitter=0.0012)
            cur += timedelta(minutes=30)
            visit(cur, 100, sp, pid+'-s%d' % spots.index(sp), 'Unknown', tz=tz)
            cur += timedelta(minutes=110)
            prev = sp
        move(cur, 30, prev, hotel, tz=tz, n=5, jitter=0.0012)
        if day.date() <= b.date():
            visit(at(day,23,tz=tz), 480, hotel, pid, 'Unknown', tz=tz)   # 숙소에서 밤을 넘긴다
        day += timedelta(days=1); continue

    visit(at(day,22,30), 540, HOME)                       # 집에서 자는 밤 (새벽 3시를 넘긴다)
    wd = day.weekday()
    if wd < 5 and random.random() < .72:                   # 평일. 주 사흘쯤은 집에서 일한다
        office = WORK if day < datetime(2024,10,1) else WORK2      # 2024년 10월에 옮긴다
        if random.random() < .55:                                        # 방문
            move(at(day,7,33), 6, HOME, CAFE, n=3, jitter=0.0003)
            visit(at(day,7,40), 35, CAFE)
            move(at(day,8,16), 5, CAFE, HOME, n=3, jitter=0.0003)
        # 아침 길은 두 갈래다 — 늘 같은 길만 그리면 지도가 선 하나로 끝난다
        move(at(day,8,20), 45, HOME, office, via=VIA_M if random.random() < .65 else VIA_M2)
        visit(at(day,9,10), 545, office)
        move(at(day,18,20), 50, office, HOME, via=VIA_E)
        if random.random() < .45: visit(at(day,8,58), 5, STOP)           # 경유
        if random.random() < .6:  visit(at(day,19,25), 7, STORE)         # 경유
        if random.random() < .35:                                        # 방문
            move(at(day,19,52), 7, HOME, GYM, n=3, jitter=0.0004)
            visit(at(day,20,0), 70, GYM)
            move(at(day,21,11), 8, GYM, HOME, n=3, jitter=0.0004)
    elif wd >= 5:                                         # 주말
        if random.random() < .4:                                         # 방문
            move(at(day,13,48), 11, HOME, MART, n=4, jitter=0.0006)
            visit(at(day,14,0), 45, MART)
            move(at(day,14,46), 12, MART, HOME, n=4, jitter=0.0006)
        if random.random() < .5:  visit(at(day,19,10), 6, STORE)
        if wd == 5 and day.day <= 7:                                     # 매달 첫 토요일
            move(at(day,11,0), 55, HOME, FOLKS, n=9, jitter=0.002)
            visit(at(day,12,0), 330, FOLKS)
            move(at(day,18,0), 60, FOLKS, HOME, n=9, jitter=0.002)
    day += timedelta(days=1)

OUT.sort(key=lambda r: r['startTime'])
json.dump(OUT, sys.stdout, ensure_ascii=False, separators=(',', ':'))

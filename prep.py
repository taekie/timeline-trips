"""Build geo.json — the offline place-name bundle the app ships with.

Sources are downloaded on first run and are not meant to be committed:
  southkorea-maps (KOSTAT 2018)   시/도 + 시·군·구 boundaries
  natural-earth-vector 110m/50m   country outlines + Korean/English country names
  geonames cities15000            world city index

지명은 한글·영문 두 벌로 내보낸다 — 지역/국가는 [한글, 영문, 링(, cc)],
도시는 [도시명, 국가한글, 국가영문, 위도, 경도, 순위].

Run: python3 prep.py   ->   geo.json   (bump ?v= in index.html afterwards)
"""
import json, csv, re, os, subprocess

SRC = {
 'skorea-municipalities-2018-geo.json':
   'https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2018/json/skorea-municipalities-2018-geo.json',
 'skorea-provinces-2018-geo.json':
   'https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2018/json/skorea-provinces-2018-geo.json',
 'world.json':
   'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson',
 'world50.json':
   'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson',
 'admin1.geojson':
   'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson',
 'countryInfo.txt': 'https://download.geonames.org/export/dump/countryInfo.txt',
 'cities15000.zip': 'https://download.geonames.org/export/dump/cities15000.zip',
}
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cache')
os.makedirs(CACHE, exist_ok=True)
os.chdir(CACHE)
for f, url in SRC.items():
    if os.path.exists(f): continue
    print('downloading', f)
    subprocess.run(['curl','-sSL','--fail','-o',f,url], check=True)
if not os.path.exists('cities15000.txt'):
    import zipfile; zipfile.ZipFile('cities15000.zip').extractall('.')

def dp(pts, tol):
    """Douglas-Peucker, iterative."""
    if len(pts) < 3: return pts
    keep = [False]*len(pts); keep[0] = keep[-1] = True
    stack = [(0, len(pts)-1)]
    while stack:
        i, j = stack.pop()
        if j <= i+1: continue
        (x1,y1),(x2,y2) = pts[i], pts[j]
        dx, dy = x2-x1, y2-y1
        d2 = dx*dx + dy*dy
        best, bi = -1, -1
        for k in range(i+1, j):
            x, y = pts[k]
            if d2 == 0: dd = (x-x1)**2 + (y-y1)**2
            else:
                t = max(0, min(1, ((x-x1)*dx + (y-y1)*dy)/d2))
                dd = (x-(x1+t*dx))**2 + (y-(y1+t*dy))**2
            if dd > best: best, bi = dd, k
        if best > tol*tol:
            keep[bi] = True; stack += [(i,bi),(bi,j)]
    return [p for p,k in zip(pts, keep) if k]

def rings(geom, tol, prec):
    polys = geom['coordinates'] if geom['type']=='MultiPolygon' else [geom['coordinates']]
    out = []
    for poly in polys:
        r = dp([(round(x,prec), round(y,prec)) for x,y in poly[0]], tol)
        if len(r) >= 4: out.append([c for p in r for c in p])   # flat [x,y,x,y,...]
    return out

# --- Korea: 250 municipalities, province name joined via the code prefix ----
# 원본은 시/구가 붙은 곳의 영문을 "Suwonsijangangu" 처럼 통짜로 적는다. 시 이름만
# 알면 앞을 떼고 뒤의 -gu 를 잘라 나머지를 얻을 수 있어, 표는 시 열한 곳이면 된다.
CITY_EN = {'수원시':'Suwon','성남시':'Seongnam','안양시':'Anyang','안산시':'Ansan',
           '고양시':'Goyang','용인시':'Yongin','청주시':'Cheongju','천안시':'Cheonan',
           '전주시':'Jeonju','포항시':'Pohang','창원시':'Changwon'}

def split_two(name, eng):
    """'수원시장안구' → ('수원시 장안구', 'Suwon-si Jangan-gu')"""
    m = re.fullmatch(r'(.+시)(.+[구군])', name)
    if not m: return name, eng
    city_ko, sub_ko = m.group(1), m.group(2)
    city_en = CITY_EN.get(city_ko)
    if not city_en: return f'{city_ko} {sub_ko}', eng      # 표에 없으면 원본 그대로
    low, pre = eng.lower(), (city_en + 'si').lower()
    sub = eng[len(pre):] if low.startswith(pre) else eng   # 포항·창원은 구 이름만 적혀 있다
    sub = re.sub(r'-?gu[n]?$', '', sub, flags=re.I) or sub
    sfx = '-gun' if sub_ko.endswith('군') else '-gu'
    return f'{city_ko} {sub_ko}', f'{city_en}-si {sub[:1].upper() + sub[1:]}{sfx}'

pv = json.load(open('skorea-provinces-2018-geo.json'))['features']
prov    = {f['properties']['code']: f['properties']['name']     for f in pv}
prov_en = {f['properties']['code']: f['properties']['name_eng'] for f in pv}
kr = []
for f in json.load(open('skorea-municipalities-2018-geo.json'))['features']:
    p = f['properties']
    rs = rings(f['geometry'], 0.004, 4)
    name, name_en = split_two(p['name'], p['name_eng'])
    if rs: kr.append([(prov.get(p['code'][:2], '') + ' ' + name).strip(),
                      (prov_en.get(p['code'][:2], '') + ' ' + name_en).strip(), rs])

# --- World: country outlines, Korean names where Natural Earth has them -----
ko, en = {}, {}
world = []
for f in json.load(open('world.json'))['features']:
    p = f['properties']
    nm, nm_en = (p.get('NAME_KO') or p['NAME']), p['NAME']
    cc = next((p[k] for k in ('ISO_A2_EH','ISO_A2') if p.get(k) and p[k] != '-99'), '')
    if cc: ko.setdefault(cc, nm); en.setdefault(cc, nm_en)
    rs = rings(f['geometry'], 0.05, 2)
    if rs: world.append([nm, nm_en, rs, cc])

# 110m has no Guam/Macau/…; borrow Korean names from the 50m table (names only,
# geometry stays 110m) and fall back to GeoNames English for anything still missing
for f in json.load(open('world50.json'))['features']:
    p = f['properties']
    for k in ('ISO_A2_EH','ISO_A2'):
        if p.get(k) and p[k] != '-99':
            ko.setdefault(p[k], p.get('NAME_KO') or p['NAME']); en.setdefault(p[k], p['NAME'])
for line in open('countryInfo.txt', encoding='utf-8'):
    if line.startswith('#'): continue
    c = line.split('\t')
    if len(c) > 4: ko.setdefault(c[0], c[4]); en.setdefault(c[0], c[4])

# --- World cities: pop >= 50k, plus the largest place in every country ------
# PPLX is a *section* of a city ("Chinatown"); it outranks the city itself on
# distance and produces nonsense labels, so drop it.
csv.field_size_limit(10**7)
rows = [(r[2], r[8], round(float(r[4]),3), round(float(r[5]),3), int(r[14] or 0))
        for r in csv.reader(open('cities15000.txt', encoding='utf-8'), delimiter='\t')
        if r[8] != 'KR' and r[7] != 'PPLX']
biggest = {}
for r in rows:
    if r[4] > biggest.get(r[1], (0,0,0,0,-1))[4]: biggest[r[1]] = r
sel = {(r[0], r[1]): r for r in rows if r[4] >= 50000}
sel.update({(r[0], r[1]): r for r in biggest.values()})
# rank = log10(population)*10, so the app can prefer Tokyo over its Chuo ward
import math
cities = [[r[0], ko.get(r[1], r[1]), en.get(r[1], r[1]), r[2], r[3],
           round(math.log10(max(r[4],1000))*10)]
          for r in sorted(sel.values(), key=lambda x: -x[4])]

# --- Region files: one per country, fetched only when a trip lands there ----
# KR gets the 시·군·구 boundaries above; everywhere else gets Natural Earth
# admin-1 (state/province). Same shape either way: [displayName, rings].
OUT = os.path.join('..', 'regions')
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT): os.remove(os.path.join(OUT, f))

regions = {'KR': kr}
for f in json.load(open('admin1.geojson'))['features']:
    p = f['properties']
    cc = p.get('iso_a2')
    if not re.fullmatch(r'[A-Z]{2}', cc or '') or cc == 'KR': continue
    rs = rings(f['geometry'], 0.02, 3)
    if rs: regions.setdefault(cc, []).append(
        [p.get('name_ko') or p.get('name') or '', p.get('name') or '', rs])

manifest = {}
for cc, feats in sorted(regions.items()):
    blob = json.dumps(feats, ensure_ascii=False, separators=(',',':'))
    open(os.path.join(OUT, cc + '.json'), 'w').write(blob)
    manifest[cc] = len(blob.encode())

data = {'world': world, 'cities': cities, 'regions': manifest}
s = json.dumps(data, ensure_ascii=False, separators=(',',':'))
open(os.path.join('..','geo.json'),'w').write(s)
print(f'core   world {len(world)}  cities {len(cities)}  {len(s.encode())/1e6:.2f}MB')
print(f'regions {len(manifest)}개국  {sum(manifest.values())/1e6:.2f}MB  '
      f'(KR {manifest["KR"]//1024}KB, US {manifest.get("US",0)//1024}KB, JP {manifest.get("JP",0)//1024}KB)')

#!/usr/bin/env python3
"""index.html 을 다른 말로 옮겨 찍는다.

문구에 번호를 새로 붙이지 않고 한국어 원문을 그대로 열쇠로 쓴다. 코드 안에서
무슨 말인지 바로 보이고, 옮길 때 두 곳을 고칠 일이 없다. 대신 원문이 한 글자라도
바뀌면 열쇠가 어긋나므로, 못 찾은 열쇠와 남은 한글을 둘 다 소리 내어 알린다.

    python3 i18n/apply.py en > en/index.html
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lang = sys.argv[1] if len(sys.argv) > 1 else 'en'
pairs = json.load(open(os.path.join(ROOT, 'i18n', lang + '.json'), encoding='utf-8'))

s = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
missing, applied = [], 0
for src, dst in pairs:
    n = s.count(src)
    if n == 0:
        missing.append(src)
        continue
    s = s.replace(src, dst)
    applied += n

# 주석은 옮기지 않는다 — 코드를 읽는 사람 몫이다. 남은 한글을 셀 때도 뺀다.
def blank_comments(t):
    t = re.sub(r'/\*[\s\S]*?\*/', lambda m: re.sub(r'[가-힣]', ' ', m.group()), t)
    t = re.sub(r'(^|[^:])//[^\n]*', lambda m: m.group(1) + re.sub(r'[가-힣]', ' ', m.group()[len(m.group(1)):]), t)
    t = re.sub(r'<!--[\s\S]*?-->', lambda m: re.sub(r'[가-힣]', ' ', m.group()), t)
    return t

# 옮긴 글 안에 일부러 남긴 한글(언어 이름 같은 것)은 잔여가 아니다
keep = [d for _, d in pairs if re.search(r'[가-힣]', d)]
def drop_intended(t):
    for d in sorted(keep, key=len, reverse=True):
        t = t.replace(d, ' ')
    return t

left = [(i + 1, l.strip()) for i, l in enumerate(drop_intended(blank_comments(s)).split('\n'))
        if re.search(r'[가-힣]', l)]

for k in missing:
    print('못 찾은 열쇠: ' + json.dumps(k, ensure_ascii=False)[:110], file=sys.stderr)
for i, l in left:
    print(f'남은 한글 {i}행: {l[:110]}', file=sys.stderr)
print(f'{lang}: 옮긴 자리 {applied}  못 찾은 열쇠 {len(missing)}  남은 한글 {len(left)}행', file=sys.stderr)

sys.stdout.write(s)
sys.exit(1 if missing or left else 0)

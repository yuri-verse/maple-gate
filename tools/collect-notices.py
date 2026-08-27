#!/usr/bin/env python3
"""메이플키우기 공식 포럼 공지·이벤트 -> data/notices.json

넥슨 공식 커뮤니티 포럼(forum.nexon.com)의 공개 JSON API 를 그대로 읽는다.
게임 공식 소식이라 출처가 명확하고, 사이트 상단에 공개돼 있는 데이터다.

  https://forum.nexon.com/api/v1/community/607/stickyThreads?alias=maplestoryidle-kr
  community 607 = 메이플키우기 · 스티키 = 포럼이 '주요소식'으로 고정한 글

썸네일·제목·분류·날짜·링크만 담는다. 링크는 공식 포럼 글로 연결한다(재호스팅 아님).
"""
import json, os, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'notices.json')
API = ('https://forum.nexon.com/api/v1/community/607/stickyThreads'
       '?alias=maplestoryidle-kr&pageSize=30&hideType=WEB')
VIEW = 'https://forum.nexon.com/maplestoryidle-kr/{tid}'
UA = 'MapleIdleStageGate/1.0 (fan info site; contact successyr@gmail.com)'

# boardTitle -> 화면 분류
EVENT = {'이벤트'}
NOTICE = {'공지사항', '패치노트'}


def main():
    req = urllib.request.Request(API, headers={
        'User-Agent': UA, 'Accept-Language': 'ko',
        'Referer': 'https://forum.nexon.com/maplestoryidle-kr/'})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = json.load(r)
    threads = raw.get('stickyThreads', [])

    events, notices = [], []
    for t in threads:
        board = t.get('boardTitle', '')
        row = dict(
            title=t.get('title', '').strip(),
            board=board,
            tag=t.get('headlineName', '') or '',
            date=time.strftime('%Y-%m-%d', time.localtime(int(t.get('createDate', 0)))),
            thumb=t.get('thumbnailImageUrl') or '',
            url=VIEW.format(tid=t.get('threadId')))
        if board in EVENT:
            events.append(row)
        elif board in NOTICE:
            notices.append(row)
        # '지난 이벤트' '확인 중인 현상' 등은 홈에 안 띄운다

    out = dict(source='넥슨 공식 포럼 (forum.nexon.com/maplestoryidle-kr)',
               collectedAt=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
               notices=notices[:8], events=events[:8])
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f"notices.json  공지 {len(out['notices'])} · 이벤트 {len(out['events'])} "
          f"· 원본 {len(threads)}건")
    for r in (out['events'][:2] + out['notices'][:2]):
        print(f"  [{r['board']}] {r['tag']} {r['title'][:36]} ({r['date']})")


main()

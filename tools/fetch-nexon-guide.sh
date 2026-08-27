#!/usr/bin/env bash
# 넥슨 공식 전투 가이드 원문 (한국어). 브라우저 헤더가 없으면 403.
set -euo pipefail
OUT="${1:-reference/nexon-guide-$(date +%F).json}"
curl -sS --max-time 60 -L \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36' \
  -H 'Accept-Language: ko-KR,ko;q=0.9' \
  -H 'Referer: https://maplestoryidle.nexon.com/ko/guide' \
  -o "$OUT" "https://maplestoryidle.nexon.com/ko/guide/data"
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print('lastUpdated:',d['lastUpdated'],'| groups:',len(d['battleGroups']),'| statItems:',len(d['statItems']))" "$OUT"
echo "saved -> $OUT"

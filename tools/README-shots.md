# 화면 확인 (tools/shot.js)

CSS 를 눈 감고 쓰지 않으려면 이게 먼저다. 실제 크로미움으로 렌더해서 PNG 를 뽑는다.

```bash
export LD_LIBRARY_PATH="$(cat <스크래치패드>/ldpath.txt)"
node tools/shot.js home dark  shots/home.png 1280
node tools/shot.js stage light shots/stage.png 1440
# 탭: home | stage | sup | mon | enh      테마: dark | light
```

## 설치 (한 번만)

이 머신에는 root 권한이 없어서 시스템 패키지로 못 깐다. 대신 전부 사용자 홈에 넣었다.

```bash
npm i -D playwright
npx playwright install chromium        # --with-deps 는 sudo 가 필요해서 못 쓴다
```

크로미움이 요구하는 공유 라이브러리 13개(`libatk`, `libgbm`, `libXi`, `libXRes` 등)는
`apt-get download` 로 deb 만 받아서 `dpkg-deb -x` 로 풀고 `LD_LIBRARY_PATH` 로 물린다.
한글이 두부로 나오지 않게 `fonts-noto-cjk` 도 같은 방식으로 받아 `~/.fonts` 에 넣었다.

크로미움 실행 인자에 **`--single-process` 가 반드시 필요하다** — 없으면 시작하자마자 죽는다.

# 세무소식 · 네이버 블로그 연동 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사무소 네이버 블로그(tax5868)의 '세금이야기' 분류 글을 본문·사진까지 자동으로 가져와 `column/index.html` 을 채운다.

**Architecture:** `tools/update_column.py` 가 RSS → 분류 거르기 → 본문 긁기 → 사진 내려받아 축소 → HTML 표시자 사이 갈아끼우기 순서로 동작한다. 기존 `tools/update_news.py` 와 같은 구조이며, 같은 GitHub Actions 워크플로에 단계 하나로 붙는다. 사진은 네이버가 hotlink 를 막으므로 반드시 `column/img/` 에 내려받아 우리 도메인에서 서빙한다.

**Tech Stack:** Python 3.12 표준 라이브러리(`urllib`, `xml.etree.ElementTree`, `re`, `html`, `hashlib`) + Pillow(축소). 시험은 pytest 9.1.1. 프런트는 기존 `style.css` / 읽는 창(`.nv-*`) 재사용.

**Spec:** `docs/superpowers/specs/2026-09-04-column-blog-integration-design.md`

## Global Constraints

- RSS 주소는 `https://rss.blog.naver.com/tax5868.xml` 로 고정
- 가져올 분류는 `세금이야기` 하나뿐 (`<category>` 값과 정확히 일치)
- 본문 페이지 주소 형식 : `https://blog.naver.com/PostView.naver?blogId=tax5868&logNo={logNo}&redirect=Dlog&widgetTypeCall=true&noTrackingCode=true&directAccess=false`
- 본문 영역은 `<div class="se-main-container">` 안
- 사진 원본은 `postfiles.pstatic.net`. **Referer 를 보내면 403** 이므로 서버에서 받을 때 Referer 를 붙이지 않는다
- 내려받은 사진은 `column/img/` 에 저장, 가로 **900px** 이하, JPEG 품질 **80**, 한 글당 최대 **12장**
- 목록에 **날짜를 표시하지 않는다** (대리님 결정)
- 자동 갱신 구간 표시자는 `<!-- 글 여기부터 -->` / `<!-- 글 여기까지 -->`
- 상대 서버 배려로 글 사이 `time.sleep(0.25)`
- 받아오기 실패 시 **기존 파일을 건드리지 않고** 종료 코드 1 로 끝낸다
- 주석·출력 문구는 한국어. 변수명도 기존 `update_news.py` 처럼 한국어 사용 가능하나, **bash 로 넘어가는 이름은 ASCII**
- 커밋 메시지는 한국어

---

### Task 1: RSS 에서 '세금이야기' 글만 골라내기

**Files:**
- Create: `tools/update_column.py`
- Test: `tests/test_update_column.py`
- Fixture(이미 있음): `tests/fixtures/blog_rss.xml`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `고른글(원본: bytes) -> list[dict]` — 각 dict 는 `{'제목': str, '주소': str, '번호': str, '요약': str}`
  - `글번호(주소: str) -> str` — 블로그 주소에서 logNo 를 뽑는다. 못 뽑으면 `''`

- [ ] **Step 1: Write the failing test**

`tests/test_update_column.py` 를 만든다.

```python
# -*- coding: utf-8 -*-
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import update_column as uc

여기 = os.path.dirname(os.path.abspath(__file__))


def 자료(이름):
    with io.open(os.path.join(여기, 'fixtures', 이름), 'rb') as f:
        return f.read()


def test_세금이야기만_골라온다():
    글들 = uc.고른글(자료('blog_rss.xml'))
    assert len(글들) == 34
    assert all(g['제목'] for g in 글들)
    assert all(g['주소'].startswith('https://blog.naver.com/tax5868/') for g in 글들)


def test_사무소소개는_빠진다():
    import xml.etree.ElementTree as ET
    전체 = ET.fromstring(자료('blog_rss.xml')).find('channel').findall('item')
    assert len(전체) == 36                       # 전체 36건 중
    assert len(uc.고른글(자료('blog_rss.xml'))) == 34   # 세금이야기 34건만 남는다


def test_글번호를_뽑는다():
    assert uc.글번호('https://blog.naver.com/tax5868/223650102868?fromRss=true') == '223650102868'
    assert uc.글번호('https://blog.naver.com/tax5868/223650102868') == '223650102868'
    assert uc.글번호('https://example.com/그냥주소') == ''


def test_요약이_태그없이_들어온다():
    글들 = uc.고른글(자료('blog_rss.xml'))
    요약 = 글들[0]['요약']
    assert '<' not in 요약
    assert len(요약) > 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_update_column.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'update_column'`

- [ ] **Step 3: Write minimal implementation**

`tools/update_column.py` 를 만든다.

```python
# -*- coding: utf-8 -*-
"""사무소 네이버 블로그의 '세금이야기' 글을 받아 column/index.html 을 채웁니다.

  · 목록과 본문을 사이트 안에서 읽을 수 있게 넣습니다
  · 사진은 네이버가 직접 부르는 것을 막아두어, 내려받아 column/img/ 에 둡니다
  GitHub Actions 가 하루 두 번 자동으로 돌립니다.
  손으로 돌려보려면 :  python tools/update_column.py
"""
import html
import os
import re
import xml.etree.ElementTree as ET

RSS = 'https://rss.blog.naver.com/tax5868.xml'
분류 = '세금이야기'
요약길이 = 300


def 글번호(주소):
    """블로그 주소에서 글 번호(logNo)를 뽑습니다."""
    m = re.search(r'blog\.naver\.com/[^/]+/(\d+)', 주소 or '')
    return m.group(1) if m else ''


def 태그걷기(값):
    """태그를 걷어내고 글자만 남깁니다."""
    글 = re.sub(r'<[^>]+>', ' ', html.unescape(값 or ''))
    return re.sub(r'\s+', ' ', 글).strip()


def 고른글(원본):
    """RSS 에서 '세금이야기' 분류 글만 골라 옵니다."""
    항목 = ET.fromstring(원본).find('channel').findall('item')
    골라둠 = []
    for it in 항목:
        if (it.findtext('category') or '').strip() != 분류:
            continue
        주소 = (it.findtext('link') or '').strip().split('?')[0]
        번호 = 글번호(주소)
        제목 = (it.findtext('title') or '').strip()
        if not (주소 and 번호 and 제목):
            continue
        골라둠.append({
            '제목': 제목,
            '주소': 주소,
            '번호': 번호,
            '요약': 태그걷기(it.findtext('description'))[:요약길이],
        })
    return 골라둠
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_update_column.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add tools/update_column.py tests/test_update_column.py tests/fixtures/blog_rss.xml
git commit -m "세무소식 : 블로그 RSS 에서 세금이야기 글만 골라오기"
```

---

### Task 2: 본문 페이지에서 글자와 사진 주소 뽑아내기

**Files:**
- Modify: `tools/update_column.py`
- Modify: `tests/test_update_column.py`
- Fixture(이미 있음): `tests/fixtures/blog_post.html`

**Interfaces:**
- Consumes: Task 1 의 `태그걷기`
- Produces:
  - `본문뽑기(쪽: str) -> tuple[str, list[str]]` — `(글자, 사진주소목록)`. 문단은 줄바꿈(`\n`) 하나로 구분, 빈 줄은 없앤다. 본문 영역을 못 찾으면 `('', [])`

- [ ] **Step 1: Write the failing test**

`tests/test_update_column.py` 아래에 덧붙인다.

```python
def 자료글(이름):
    with io.open(os.path.join(여기, 'fixtures', 이름), encoding='utf-8', errors='replace') as f:
        return f.read()


def test_본문_글자를_뽑는다():
    글, 사진 = uc.본문뽑기(자료글('blog_post.html'))
    assert len(글) > 500
    assert '박성진 세무사입니다' in 글
    assert '<' not in 글


def test_본문에_사진주소가_들어있다():
    글, 사진 = uc.본문뽑기(자료글('blog_post.html'))
    assert len(사진) > 0
    assert all(u.startswith('https://') for u in 사진)
    assert all('pstatic.net' in u for u in 사진)


def test_본문영역이_없으면_빈값():
    글, 사진 = uc.본문뽑기('<html><body>아무것도 없음</body></html>')
    assert 글 == ''
    assert 사진 == []


def test_문단이_빈줄없이_나뉜다():
    글, 사진 = uc.본문뽑기(자료글('blog_post.html'))
    assert chr(10) * 2 not in 글
    assert 글 == 글.strip()


def test_본문에_페이지_찌꺼기가_안_섞인다():
    """본문 영역만 잘라야 한다. 너무 길면 댓글·이웃추가 같은 것이 섞인 것이다."""
    글, 사진 = uc.본문뽑기(자료글('blog_post.html'))
    assert len(글) < 20000, '본문이 너무 깁니다 : 자르는 지점을 다시 보세요'
    for 찌꺼기 in ('이웃추가', '공감한 사람 보기', '댓글쓰기'):
        assert 찌꺼기 not in 글
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_update_column.py -v`
Expected: FAIL — `AttributeError: module 'update_column' has no attribute '본문뽑기'`

- [ ] **Step 3: Write minimal implementation**

`tools/update_column.py` 에 덧붙인다.

```python
NL = chr(10)
지울것 = re.compile(r'<(script|style)[^>]*>.*?</\1>', re.S)


def 본문뽑기(쪽):
    """본문 영역에서 글자와 사진 주소를 뽑습니다.
       사진 주소는 게으른 불러오기(data-lazy-src)에 들어 있습니다."""
    m = re.search(r'<div class="se-main-container">(.*)', 쪽 or '', re.S)
    if not m:
        return '', []
    본 = m.group(1)

    끝 = 본.find('se_doc_footer')
    if 끝 != -1:
        본 = 본[:끝]

    사진 = []
    for u in re.findall(r'data-lazy-src="([^"]+)"', 본):
        u = html.unescape(u).split('?')[0]
        if 'pstatic.net' in u and u not in 사진:
            사진.append(u)

    글 = 지울것.sub(' ', 본)
    글 = re.sub(r'<br\s*/?>', NL, 글)
    글 = re.sub(r'</(p|div)>', NL, 글)
    글 = re.sub(r'<[^>]+>', ' ', 글)
    글 = html.unescape(글).replace(chr(0xa0), ' ').replace(chr(0x200b), '')
    글 = re.sub(r'[ \t]+', ' ', 글)
    글 = re.sub(NL + r'[ \t]*', NL, 글)
    글 = re.sub(NL + r'{2,}', NL, 글).strip()
    return 글, 사진
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_update_column.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add tools/update_column.py tests/test_update_column.py tests/fixtures/blog_post.html
git commit -m "세무소식 : 블로그 본문 글자와 사진 주소 뽑아내기"
```

---

### Task 3: 사진 내려받아 크기 줄여 저장하기

**Files:**
- Modify: `tools/update_column.py`
- Modify: `tests/test_update_column.py`
- Create(자동 생성): `column/img/`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `사진이름(주소: str) -> str` — 주소로부터 정해지는 파일 이름. 예 `a1b2c3d4e5f60718.jpg` (hashlib.sha1 앞 16자 + `.jpg`)
  - `사진저장(주소: str, 폴더: str, 받아오기=None) -> str | None` — 저장 성공 시 파일 이름, 실패 시 `None`. 이미 있으면 받지 않고 이름만 돌려준다. `받아오기` 는 시험에서 갈아끼우기 위한 자리로, `주소 -> bytes` 함수

- [ ] **Step 1: Write the failing test**

`tests/test_update_column.py` 아래에 덧붙인다.

```python
import io as _io

from PIL import Image


def 가짜사진(가로=1600, 세로=900):
    buf = _io.BytesIO()
    Image.new('RGB', (가로, 세로), (200, 210, 235)).save(buf, 'PNG')
    return buf.getvalue()


def test_사진이름은_주소마다_고정된다():
    a = uc.사진이름('https://postfiles.pstatic.net/aaa/bbb.png')
    b = uc.사진이름('https://postfiles.pstatic.net/aaa/bbb.png')
    c = uc.사진이름('https://postfiles.pstatic.net/aaa/ccc.png')
    assert a == b
    assert a != c
    assert a.endswith('.jpg')


def test_사진을_받아_가로900이하로_줄인다(tmp_path):
    이름 = uc.사진저장('https://postfiles.pstatic.net/x/y.png', str(tmp_path),
                    받아오기=lambda u: 가짜사진())
    assert 이름 is not None
    난것 = os.path.join(str(tmp_path), 이름)
    assert os.path.exists(난것)
    with Image.open(난것) as im:
        assert im.width <= 900
        assert im.format == 'JPEG'


def test_이미_있으면_다시_받지_않는다(tmp_path):
    부른횟수 = {'n': 0}

    def 받기(u):
        부른횟수['n'] += 1
        return 가짜사진()

    주소 = 'https://postfiles.pstatic.net/x/y.png'
    첫번 = uc.사진저장(주소, str(tmp_path), 받아오기=받기)
    두번 = uc.사진저장(주소, str(tmp_path), 받아오기=받기)
    assert 첫번 == 두번
    assert 부른횟수['n'] == 1


def test_받아오다_실패하면_None(tmp_path):
    def 터짐(u):
        raise OSError('안 열림')

    assert uc.사진저장('https://postfiles.pstatic.net/x/z.png', str(tmp_path),
                    받아오기=터짐) is None


def test_사진이_아니면_None(tmp_path):
    assert uc.사진저장('https://postfiles.pstatic.net/x/w.png', str(tmp_path),
                    받아오기=lambda u: b'this is not an image') is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_update_column.py -v`
Expected: FAIL — `AttributeError: module 'update_column' has no attribute '사진이름'`

- [ ] **Step 3: Write minimal implementation**

`tools/update_column.py` 맨 위 import 에 `import hashlib`, `import io`, `import urllib.request` 를 더하고 아래를 덧붙인다.

```python
가로최대 = 900
품질 = 80
글당사진 = 12


def 받아오기기본(주소):
    """네이버는 다른 사이트에서 부르면 막으므로 Referer 를 붙이지 않습니다."""
    요청 = urllib.request.Request(주소, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(요청, timeout=20) as 응답:
        return 응답.read()


def 사진이름(주소):
    """같은 주소면 늘 같은 이름이 나옵니다. 두 번 받지 않기 위해서입니다."""
    return hashlib.sha1((주소 or '').encode('utf-8')).hexdigest()[:16] + '.jpg'


def 사진저장(주소, 폴더, 받아오기=None):
    """사진을 받아 가로 900px 이하 JPEG 로 저장합니다.
       이미 있으면 받지 않고, 실패하면 None 을 돌려줍니다."""
    from PIL import Image

    이름 = 사진이름(주소)
    갈곳 = os.path.join(폴더, 이름)
    if os.path.exists(갈곳):
        return 이름

    try:
        자료 = (받아오기 or 받아오기기본)(주소)
        그림 = Image.open(io.BytesIO(자료))
        그림.load()
    except Exception:
        return None

    try:
        if 그림.mode not in ('RGB', 'L'):
            그림 = 그림.convert('RGB')
        if 그림.width > 가로최대:
            높이 = max(1, round(그림.height * 가로최대 / 그림.width))
            그림 = 그림.resize((가로최대, 높이), Image.LANCZOS)
        os.makedirs(폴더, exist_ok=True)
        그림.save(갈곳, 'JPEG', quality=품질, optimize=True)
    except Exception:
        if os.path.exists(갈곳):
            os.remove(갈곳)
        return None
    return 이름
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_update_column.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add tools/update_column.py tests/test_update_column.py
git commit -m "세무소식 : 블로그 사진을 받아 크기 줄여 저장"
```

---

### Task 4: 목록 HTML 만들고 표시자 사이에 갈아끼우기

**Files:**
- Modify: `tools/update_column.py`
- Modify: `tests/test_update_column.py`

**Interfaces:**
- Consumes: Task 1 `고른글`, Task 2 `본문뽑기`, Task 3 `사진저장`
- Produces:
  - `줄만들기(글: dict, 본문: str, 사진이름들: list[str]) -> str` — `<a class="news-row" …>` 한 덩어리
  - `갈아끼우기(s: str, 시작표: str, 끝표: str, 새내용: str, 들여: str) -> str | None` — 표시자를 못 찾으면 `None`

`data-body` 는 문단을 `&#10;` 으로 잇고, `data-img` 는 파일 이름을 `,` 로 잇는다. 둘 다 `html.escape` 를 거친다.

- [ ] **Step 1: Write the failing test**

```python
def test_줄에_필요한_것이_다_들어간다():
    글 = {'제목': '세금 이야기 "첫 번째"', '주소': 'https://blog.naver.com/tax5868/1', '번호': '1', '요약': '요약'}
    줄 = uc.줄만들기(글, '첫 문단' + chr(10) + '둘째 문단', ['aa.jpg', 'bb.jpg'])
    assert 'class="news-row"' in 줄
    assert 'href="https://blog.naver.com/tax5868/1"' in 줄
    assert '&quot;' in 줄                      # 제목의 따옴표가 안전하게 바뀐다
    assert 'data-img="aa.jpg,bb.jpg"' in 줄
    assert '&#10;' in 줄                       # 문단 구분
    assert 'news-date' not in 줄               # 날짜는 넣지 않는다


def test_사진이_없어도_줄이_만들어진다():
    글 = {'제목': '제목', '주소': 'https://blog.naver.com/tax5868/2', '번호': '2', '요약': '요약'}
    줄 = uc.줄만들기(글, '본문', [])
    assert 'data-img=""' in 줄


def test_표시자_사이를_갈아끼운다():
    s = 'A<!-- 시작 -->옛것<!-- 끝 -->B'
    난것 = uc.갈아끼우기(s, '<!-- 시작 -->', '<!-- 끝 -->', '새것', '  ')
    assert '옛것' not in 난것
    assert '새것' in 난것
    assert 난것.startswith('A') and 난것.endswith('B')


def test_표시자가_없으면_None():
    assert uc.갈아끼우기('아무것도 없음', '<!-- 시작 -->', '<!-- 끝 -->', '새것', '') is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_update_column.py -v`
Expected: FAIL — `AttributeError: module 'update_column' has no attribute '줄만들기'`

- [ ] **Step 3: Write minimal implementation**

```python
def 줄만들기(글, 본문, 사진이름들):
    """목록 한 줄을 만듭니다. 날짜는 넣지 않습니다."""
    몸 = html.escape(본문).replace(NL, '&#10;')
    return (
        '        <a class="news-row" href="%s" target="_blank" rel="noopener"' % html.escape(글['주소']) + NL +
        '           data-title="%s"' % html.escape(글['제목']) + NL +
        '           data-img="%s"' % html.escape(','.join(사진이름들)) + NL +
        '           data-body="%s">' % 몸 + NL +
        '          <span class="news-title">%s</span>' % html.escape(글['제목']) + NL +
        '        </a>'
    )


def 갈아끼우기(s, 시작표, 끝표, 새내용, 들여):
    a, b = s.find(시작표), s.find(끝표)
    if a == -1 or b == -1:
        return None
    return s[:a + len(시작표)] + NL + 새내용 + NL + 들여 + s[b:]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_update_column.py -v`
Expected: 17 passed

- [ ] **Step 5: Commit**

```bash
git add tools/update_column.py tests/test_update_column.py
git commit -m "세무소식 : 목록 줄 만들기와 갈아끼우기"
```

---

### Task 5: 전체를 잇는 main() 과 안전장치

**Files:**
- Modify: `tools/update_column.py`
- Modify: `tests/test_update_column.py`

**Interfaces:**
- Consumes: Task 1~4 전부
- Produces: `main() -> int` — 정상 0, 실패 1

- [ ] **Step 1: Write the failing test**

```python
def test_받아오기_실패하면_파일을_안_건드린다(tmp_path, monkeypatch):
    대상 = tmp_path / 'index.html'
    원래 = 'A<!-- 글 여기부터 -->옛것<!-- 글 여기까지 -->B'
    대상.write_text(원래, encoding='utf-8')

    monkeypatch.setattr(uc, '뿌리', str(tmp_path))
    monkeypatch.setattr(uc, '대상', 'index.html')

    def 터짐():
        raise OSError('인터넷 안 됨')

    monkeypatch.setattr(uc, '받아오기RSS', 터짐)

    assert uc.main() == 1
    assert 대상.read_text(encoding='utf-8') == 원래


def test_전체가_돌면_목록이_채워진다(tmp_path, monkeypatch):
    대상 = tmp_path / 'index.html'
    대상.write_text('A<!-- 글 여기부터 -->옛것<!-- 글 여기까지 -->B', encoding='utf-8')

    monkeypatch.setattr(uc, '뿌리', str(tmp_path))
    monkeypatch.setattr(uc, '대상', 'index.html')
    monkeypatch.setattr(uc, '사진폴더', 'img')
    monkeypatch.setattr(uc, '쉬는시간', 0)
    monkeypatch.setattr(uc, '받아오기RSS', lambda: 자료('blog_rss.xml'))
    monkeypatch.setattr(uc, '받아오기글', lambda 번호: 자료글('blog_post.html'))
    monkeypatch.setattr(uc, '사진저장', lambda u, f, 받아오기=None: 'zz.jpg')

    assert uc.main() == 0
    난것 = 대상.read_text(encoding='utf-8')
    assert '옛것' not in 난것
    assert 난것.count('class="news-row"') == 34
    assert 'data-img="zz.jpg' in 난것
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_update_column.py -v`
Expected: FAIL — `AttributeError: module 'update_column' has no attribute '받아오기RSS'`

- [ ] **Step 3: Write minimal implementation**

`tools/update_column.py` 에 `import sys`, `import time` 을 더하고 덧붙인다.

```python
대상 = 'column/index.html'
사진폴더 = 'column/img'
쉬는시간 = 0.25
시작표 = '<!-- 글 여기부터 -->'
끝표 = '<!-- 글 여기까지 -->'
본문주소 = ('https://blog.naver.com/PostView.naver?blogId=tax5868&logNo=%s'
        '&redirect=Dlog&widgetTypeCall=true&noTrackingCode=true&directAccess=false')

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def 받아오기RSS():
    요청 = urllib.request.Request(RSS, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(요청, timeout=25) as 응답:
        return 응답.read()


def 받아오기글(번호):
    요청 = urllib.request.Request(본문주소 % 번호, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(요청, timeout=25) as 응답:
        return 응답.read().decode('utf-8', 'replace')


def main():
    try:
        원본 = 받아오기RSS()
    except Exception as e:
        print('블로그에서 받아오지 못했습니다 :', e)
        return 1

    try:
        글들 = 고른글(원본)
    except Exception as e:
        print('블로그 목록을 읽지 못했습니다 :', e)
        return 1

    if not 글들:
        print("'%s' 분류 글이 없습니다. 그대로 둡니다." % 분류)
        return 1

    사진갈곳 = os.path.join(뿌리, 사진폴더)
    줄들 = []
    for n, 글 in enumerate(글들):
        try:
            쪽 = 받아오기글(글['번호'])
            본문, 사진주소 = 본문뽑기(쪽)
        except Exception:
            본문, 사진주소 = '', []

        if len(본문) < 200:
            본문 = 글['요약']
            사진주소 = []

        이름들 = []
        for u in 사진주소[:글당사진]:
            이름 = 사진저장(u, 사진갈곳)
            if 이름:
                이름들.append(이름)

        줄들.append(줄만들기(글, 본문, 이름들))
        if 쉬는시간:
            time.sleep(쉬는시간)
        if n % 10 == 9:
            print('  %d건 가져옴…' % (n + 1))

    경로 = os.path.join(뿌리, 대상)
    s = 원래 = io.open(경로, encoding='utf-8').read()
    s2 = 갈아끼우기(s, 시작표, 끝표, NL.join(줄들), '        ')
    if s2 is None:
        print('글 자리 표시를 찾지 못했습니다.')
        return 1

    if s2 == 원래:
        print('바뀐 것이 없습니다.')
        return 0

    io.open(경로, 'w', encoding='utf-8').write(s2)
    print('세무소식 %d건으로 갱신했습니다.' % len(줄들))
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_update_column.py -v`
Expected: 19 passed

- [ ] **Step 5: Commit**

```bash
git add tools/update_column.py tests/test_update_column.py
git commit -m "세무소식 : 블로그 연동 전체 잇기와 안전장치"
```

---

### Task 6: 세무소식 페이지가 사진을 보여주게 하기

**Files:**
- Modify: `column/index.html` (읽는 창 자바스크립트, `<div class="news-list" id="colList">` 아래 표시자)
- Modify: `style.css` (읽는 창 안 사진 스타일)

**Interfaces:**
- Consumes: Task 4 가 만든 `data-img` (파일 이름을 `,` 로 이은 문자열), `data-body`
- Produces: 없음 (화면 전용)

`column/index.html` 의 목록 안 표시자를 `<!-- 글 여기부터 -->` / `<!-- 글 여기까지 -->` 로 맞춘다(이미 그렇게 되어 있다). 읽는 창의 `열기()` 안, 문단을 넣은 **뒤** 사진을 붙인다.

- [ ] **Step 1: 사진을 붙이는 코드로 바꾼다**

`column/index.html` 의 `두루마리.scrollTop = 0;` **바로 앞**에 아래를 넣는다.

```javascript
    (a.dataset.img || '').split(',').forEach(function(이름){
      이름 = 이름.trim();
      if(!이름) return;
      var 그림 = document.createElement('img');
      그림.className = 'nv-img';
      그림.loading = 'lazy';
      그림.alt = '';
      그림.src = 'img/' + 이름;
      글칸.appendChild(그림);
    });
```

- [ ] **Step 1-2: 읽는 창에 '블로그에서 보기' 링크를 넣는다**

`column/index.html` 의 `.nv-src` 부분을 아래로 바꾼다.

```html
      <div class="nv-src">
        <span>박성진세무회계사무소 · 대표세무사 박성진</span>
        <a id="nvLink" href="#" target="_blank" rel="noopener">블로그에서 보기</a>
      </div>
```

그리고 읽는 창 자바스크립트 맨 위 변수 선언에 아래를 더한다.

```javascript
  var 원문   = document.getElementById('nvLink');
```

`열기()` 안 `두루마리.scrollTop = 0;` 바로 뒤에 아래를 더한다.

```javascript
    원문.href = a.getAttribute('href');
```

- [ ] **Step 2: 읽는 창 사진 스타일을 넣는다**

`style.css` 의 `.nv-body p:first-child{ … }` 줄 **다음**에 넣는다.

```css
.nv-img{
  display:block; width:100%; height:auto; margin:18px 0;
  border-radius:12px; background:var(--pale);
}
```

- [ ] **Step 3: 손으로 한 번 돌려 확인한다**

Run: `python tools/update_column.py`
Expected: `세무소식 34건으로 갱신했습니다.` 그리고 `column/img/` 에 사진 파일이 생긴다

확인:
```bash
ls column/img | head -5
python -c "import io,re;s=io.open('column/index.html',encoding='utf-8').read();print('줄',s.count('class=\"news-row\"'));print('네이버주소 남았나',('pstatic.net' in s))"
```
Expected: 줄 34, 네이버주소 남았나 False

- [ ] **Step 4: 화면으로 확인한다**

Run: `python -m http.server 8840` 후 `http://localhost:8840/column/` 에서
목록 34건 · 제목 클릭 시 창에 글과 사진 · 날짜 안 보임 · `블로그에서 보기` 링크 동작을 확인한다. 끝나면 서버를 끈다.

- [ ] **Step 5: Commit**

```bash
git add column/ style.css
git commit -m "세무소식 : 블로그 글과 사진을 사이트 안에서 보여주기"
```

---

### Task 7: 하루 두 번 자동으로 돌게 붙이기

**Files:**
- Modify: `.github/workflows/news.yml`

**Interfaces:**
- Consumes: Task 5 의 `tools/update_column.py`
- Produces: 없음

- [ ] **Step 1: Pillow 설치와 세무소식 단계를 넣는다**

`.github/workflows/news.yml` 의 `파이썬 준비` 단계 **다음**에 넣는다.

```yaml
      - name: 사진 줄이는 도구 준비
        run: python -m pip install --quiet Pillow
```

`세무사신문에서 새 기사 받아오기` 단계 **다음**에 넣는다.

```yaml
      - name: 블로그에서 세무소식 받아오기
        run: python tools/update_column.py || echo "세무소식은 이번에 건너뜁니다."
```

`|| echo` 를 붙이는 이유 : 블로그가 안 열려도 **세무뉴스 갱신은 계속되어야** 하기 때문이다.

- [ ] **Step 2: 올리는 단계가 세무소식도 함께 올리게 고친다**

`바뀐 것이 있으면 올리기` 단계의 `run:` 을 통째로 아래로 바꾼다.

```bash
          if [ -z "$(git status --porcelain news/index.html column/)" ]; then
            echo "새 글이 없어 올릴 것이 없습니다."
            exit 0
          fi
          git config user.name  "psjtax"
          git config user.email "tax0517109685@gmail.com"
          git add news/index.html column/
          git commit -m "세무뉴스·세무소식 자동 갱신 ($(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M'))"
          git push
```

- [ ] **Step 3: 문법을 확인한다**

```bash
python -c "import yaml,io;d=yaml.safe_load(io.open('.github/workflows/news.yml',encoding='utf-8').read());print('단계',len(d['jobs']['update']['steps']))"
```
Expected: 단계 7

```bash
python -c "
import subprocess,io,yaml
d=yaml.safe_load(io.open('.github/workflows/news.yml',encoding='utf-8').read())
for s in d['jobs']['update']['steps']:
    if 'run' in s and s['run'].count(chr(10))>1:
        r=subprocess.run(['bash','-n'],input=s['run'],capture_output=True,text=True)
        print(('OK ' if r.returncode==0 else 'ERR'), s['name'][:24], r.stderr.strip()[:100])
"
```
Expected: 모두 OK

- [ ] **Step 4: 시험 전체를 다시 돌린다**

Run: `python -m pytest tests/ -v`
Expected: 19 passed

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/news.yml
git commit -m "세무소식도 하루 두 번 자동으로 갱신되게"
```

---

### Task 8: 미리보기 만들어 대리님께 확인받기

**Files:**
- 없음 (확인 절차)

**Interfaces:**
- Consumes: Task 6 의 결과 화면
- Produces: 없음

- [ ] **Step 1: 미리보기 파일을 만든다**

Run: `python one_file.py column/index.html` (scratchpad 안에서)

사진이 `column/img/` 에 있으므로 `one_file.py` 가 data URI 로 넣는다. 파일이 너무 커지면(20MB 넘으면) 사진을 뺀 채로 만들고 그 사실을 말씀드린다.

- [ ] **Step 2: 대리님께 보내고 설명한다**

`SendUserFile` 로 보내고 아래를 설명한다.
- 목록 34건, 날짜 없음
- 제목을 누르면 창에 글과 사진
- 창 아래 `블로그에서 보기` 링크
- 사진은 우리 사이트에 복사된 것 (네이버가 막아서)
- 34건이 한 화면에 길지 않은지 (쪽 나누기가 필요한지)

- [ ] **Step 3: 확인받는다**

STOP. 대리님이 좋다고 하실 때까지 올리지 않는다. (`deploy-flow` 규칙)

- [ ] **Step 4: 승인 후 올린다**

```bash
git add -A
git commit -m "세무소식 : 블로그 글 자동 연동"
git push origin main
```

- [ ] **Step 5: 실제 사이트를 확인한다**

`https://www.psjtax.co.kr/column/` 에서 목록과 사진이 나오는지 본다.

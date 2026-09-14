# 인스타그램 카드 6칸 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사무소 인스타그램(@taxpsj) 최근 게시물을 세무소식 페이지 위에 카드 6칸으로 보여주고, 카드를 누르면 사이트 안 창에서 사진과 글을 읽게 한다. 이름표는 스스로 연장한다.

**Architecture:** `tools/update_insta.py` 가 Instagram Graph API → 설명글 다듬기 → 사진 내려받아 축소 → `column/index.html` 의 표시자 사이 갈아끼우기 순으로 동작한다. 사진 저장은 이미 검증된 `tools/update_column.py` 의 `사진저장`/`사진이름` 을 그대로 가져다 쓴다. 토큰 연장은 별도 파일 `tools/refresh_insta_token.py` 가 맡고, 실패해도 게시물 갱신을 막지 않는다. 화면은 세무뉴스의 카드 슬라이드(`.nc-*`)와 세무소식의 읽는 창(`.nv-*`)을 재사용한다.

**Tech Stack:** Python 3.12 표준 라이브러리(`urllib`, `json`, `re`, `os`, `base64`) + Pillow(사진 축소, 이미 설치) + PyNaCl(깃허브 금고 암호화, 워크플로에서 설치). 시험은 pytest 9.1.1.

**Spec:** `docs/superpowers/specs/2026-09-04-instagram-cards-design.md`

## Global Constraints

- API 주소는 `https://graph.instagram.com/v21.0/me/media` 로 고정
- 받아올 개수는 **6개** (`limit=6`), 카드 칸도 **6칸**
- 요청할 항목 : `id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,children{media_url}`
- 토큰은 환경변수 **`IG_ACCESS_TOKEN`** 에서만 읽는다. **코드에 적지 않고, 화면에 찍지 않는다**
- **대리님 컴퓨터의 `C:\수업\하네스실습\automation\.env` 는 절대 읽지 않는다**
- 설명글에서 **`051-710-9685` 가 들어있는 줄**과 **해시태그만으로 된 줄**은 지운다
- 내려받은 사진은 `column/insta/` 에 저장, 가로 **900px** 이하, JPEG 품질 **80**, 게시물당 최대 **12장**
- 자동 갱신 구간 표시자는 `<!-- 인스타 여기부터 -->` / `<!-- 인스타 여기까지 -->`
- 게시물이 **0건으로 오면 쓰지 않는다.** 있던 카드를 지우면 안 된다
- 파일 쓰기는 임시파일 + `os.replace` (원자적)
- `tools/update_column.py` 의 동작은 바꾸지 않는다 (가져다 쓰기만 한다)
- 주석·출력 문구는 한국어. 변수명도 한국어. **bash 로 넘어가는 이름은 ASCII**
- 커밋 메시지는 한국어

---

### Task 1: 설명글 다듬기와 게시물 정리

**Files:**
- Create: `tools/update_insta.py`
- Test: `tests/test_update_insta.py`
- Fixture(이미 있음): `tests/fixtures/insta_media.json`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `설명다듬기(글: str) -> str` — 전화번호 줄과 해시태그 줄을 뺀 글. 문단 사이 빈 줄은 하나로 줄인다
  - `게시물정리(자료: dict) -> list[dict]` — 각 dict 는 `{'아이디': str, '제목': str, '설명': str, '날짜': str, '주소': str, '사진': list[str]}`
    - `제목` 은 설명 첫 줄 (없으면 `'인스타그램 게시물'`)
    - `날짜` 는 `2026. 09. 04` 꼴
    - `사진` 은 `children` 이 있으면 낱장 주소들, 없으면 `media_url` 하나

- [ ] **Step 1: Write the failing test**

`tests/test_update_insta.py` 를 만든다.

```python
# -*- coding: utf-8 -*-
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import update_insta as ui

여기 = os.path.dirname(os.path.abspath(__file__))
NL = chr(10)


def 자료():
    with io.open(os.path.join(여기, 'fixtures', 'insta_media.json'), encoding='utf-8') as f:
        return json.load(f)


def test_전화번호_줄이_사라진다():
    원본 = 자료()['data'][0]['caption']
    assert '051-710-9685' in 원본          # 시험 자료에 정말 들어있는지 먼저 확인
    다듬 = ui.설명다듬기(원본)
    assert '051-710-9685' not in 다듬
    assert '05171' not in 다듬.replace('-', '').replace(' ', '')


def test_해시태그_줄이_사라진다():
    원본 = 자료()['data'][0]['caption']
    assert '#지급명세서' in 원본
    다듬 = ui.설명다듬기(원본)
    assert '#지급명세서' not in 다듬
    assert '#박성진세무회계사무소' not in 다듬


def test_본문은_남는다():
    다듬 = ui.설명다듬기(자료()['data'][0]['caption'])
    assert '간이지급명세서' in 다듬
    assert '2026년 9월 30일' in 다듬
    assert len(다듬) > 300


def test_문장_중간의_샵은_안_지운다():
    글 = '세금 신고는 #1 우선순위입니다.' + NL + '#세무사 #신고'
    다듬 = ui.설명다듬기(글)
    assert '#1 우선순위' in 다듬
    assert '#세무사' not in 다듬


def test_빈줄이_겹치지_않는다():
    글 = '첫째 줄' + NL * 4 + '둘째 줄'
    assert NL * 3 not in ui.설명다듬기(글)


def test_게시물을_정리한다():
    글들 = ui.게시물정리(자료())
    assert len(글들) == 1
    g = 글들[0]
    assert g['제목'] == '2026년 8월에 프리랜서나 일용직에게 대가를 지급하셨나요?'
    assert g['날짜'] == '2026. 09. 04'
    assert g['주소'] == 'https://www.instagram.com/p/Dc2cBIOkuHS/'
    assert len(g['사진']) == 8            # 여러 장짜리는 낱장을 쓴다
    assert '051-710-9685' not in g['설명']


def test_낱장이_없으면_대표사진_하나():
    자 = {'data': [{'id': '1', 'caption': '한 장짜리 글입니다.',
                   'media_type': 'IMAGE',
                   'media_url': 'https://example.com/a.jpg',
                   'permalink': 'https://www.instagram.com/p/AAA/',
                   'timestamp': '2026-09-01T00:00:00+0000'}]}
    g = ui.게시물정리(자)[0]
    assert g['사진'] == ['https://example.com/a.jpg']
    assert g['제목'] == '한 장짜리 글입니다.'


def test_설명이_없으면_기본제목():
    자 = {'data': [{'id': '2', 'media_type': 'IMAGE',
                   'media_url': 'https://example.com/b.jpg',
                   'permalink': 'https://www.instagram.com/p/BBB/',
                   'timestamp': '2026-09-01T00:00:00+0000'}]}
    g = ui.게시물정리(자)[0]
    assert g['제목'] == '인스타그램 게시물'
    assert g['설명'] == ''
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_update_insta.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'update_insta'`

- [ ] **Step 3: Write minimal implementation**

`tools/update_insta.py` 를 만든다.

```python
# -*- coding: utf-8 -*-
"""사무소 인스타그램(@taxpsj) 최근 게시물을 받아 세무소식 페이지의 카드를 채웁니다.

  · 설명글에서 사무실 전화번호 줄과 해시태그 줄은 빼고 보여줍니다
  · 사진은 인스타 주소가 만료되므로 내려받아 column/insta/ 에 둡니다
  GitHub Actions 가 하루 두 번 자동으로 돌립니다.
  손으로 돌려보려면 :  IG_ACCESS_TOKEN 을 환경변수로 주고  python tools/update_insta.py
"""
import re

NL = chr(10)
숨길번호 = '051-710-9685'
기본제목 = '인스타그램 게시물'


def 전화번호줄인가(줄):
    """사무실 번호가 들어있는 줄인지 봅니다. 하이픈이나 띄어쓰기가 달라도 잡습니다."""
    숫자 = re.sub(r'[^0-9]', '', 줄)
    return 숨길번호 in 줄 or re.sub(r'[^0-9]', '', 숨길번호) in 숫자


def 해시태그줄인가(줄):
    """줄 전체가 해시태그로만 되어 있는지 봅니다. 문장 중간의 # 은 건드리지 않습니다."""
    토막 = 줄.split()
    return bool(토막) and all(t.startswith('#') and len(t) > 1 for t in 토막)


def 설명다듬기(글):
    """홈페이지에 보여줄 수 있게 설명글을 다듬습니다."""
    남길것 = []
    for 줄 in (글 or '').split(NL):
        벗김 = 줄.strip()
        if 전화번호줄인가(벗김) or 해시태그줄인가(벗김):
            continue
        남길것.append(벗김)
    글 = NL.join(남길것)
    글 = re.sub(NL + r'{3,}', NL * 2, 글)
    return 글.strip()


def 날짜다듬기(값):
    """2026-09-04T02:11:07+0000  →  2026. 09. 04"""
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', (값 or '').strip())
    return '%s. %s. %s' % m.groups() if m else ''


def 게시물정리(자료):
    """API 가 준 것을 우리가 쓸 모양으로 바꿉니다."""
    정리됨 = []
    for it in (자료 or {}).get('data', []):
        주소 = (it.get('permalink') or '').strip()
        if not 주소:
            continue
        설명 = 설명다듬기(it.get('caption') or '')
        첫줄 = 설명.split(NL)[0].strip() if 설명 else ''
        낱장 = (it.get('children') or {}).get('data', [])
        사진 = [c.get('media_url') for c in 낱장 if c.get('media_url')]
        if not 사진:
            하나 = it.get('media_url') or it.get('thumbnail_url')
            사진 = [하나] if 하나 else []
        정리됨.append({
            '아이디': str(it.get('id') or ''),
            '제목': 첫줄 or 기본제목,
            '설명': 설명,
            '날짜': 날짜다듬기(it.get('timestamp')),
            '주소': 주소,
            '사진': 사진,
        })
    return 정리됨
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_update_insta.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add tools/update_insta.py tests/test_update_insta.py tests/fixtures/insta_media.json
git commit -m "인스타 : 게시물 정리와 설명글 다듬기"
```

---

### Task 2: 카드 HTML 만들기

**Files:**
- Modify: `tools/update_insta.py`
- Modify: `tests/test_update_insta.py`

**Interfaces:**
- Consumes: Task 1 의 `NL`
- Produces:
  - `카드만들기(글: dict, 사진이름들: list[str]) -> str` — `<a class="nc" …>` 한 덩어리
  - `준비중카드() -> str` — `<div class="nc nc-soon">` 한 덩어리 (`<a>` 가 아니므로 눌러도 반응 없음)
  - `여섯칸(카드들: list[str]) -> str` — 카드가 6개가 될 때까지 준비중 카드로 채운다. 6개를 넘으면 앞의 6개만 남긴다
  - `갈아끼우기(s: str, 시작표: str, 끝표: str, 새내용: str, 들여: str) -> str | None`

카드에 넣는 속성 : `href`(인스타 주소), `data-title`, `data-date`, `data-body`(문단을 `&#10;` 으로 이음), `data-img`(파일 이름을 `,` 로 이음), `data-imgdir="insta"`, `data-link-label="인스타그램에서 보기"`. 전부 `html.escape` 를 거친다.

- [ ] **Step 1: Write the failing test**

`tests/test_update_insta.py` 아래에 덧붙인다.

```python
def 보기글(설명='첫 문단' + NL + '둘째 문단'):
    return {'아이디': '1', '제목': '제목 "따옴표"', '설명': 설명,
            '날짜': '2026. 09. 04',
            '주소': 'https://www.instagram.com/p/AAA/', '사진': []}


def test_카드에_필요한_것이_다_들어간다():
    카드 = ui.카드만들기(보기글(), ['a.jpg', 'b.jpg'])
    assert 'class="nc"' in 카드
    assert 'href="https://www.instagram.com/p/AAA/"' in 카드
    assert '&quot;' in 카드                      # 제목의 따옴표가 안전하게 바뀐다
    assert 'data-img="a.jpg,b.jpg"' in 카드
    assert 'data-imgdir="insta"' in 카드
    assert 'data-link-label="인스타그램에서 보기"' in 카드
    assert '&#10;' in 카드                       # 문단 구분
    assert 'nc-date' in 카드 and '2026. 09. 04' in 카드


def test_카드_요약은_짧게_자른다():
    긴글 = '가' * 300
    카드 = ui.카드만들기(보기글(긴글), [])
    m = __import__('re').search(r'<span class="nc-sum">([^<]*)</span>', 카드)
    assert m is not None
    assert len(m.group(1)) <= 120


def test_준비중카드는_눌리지_않는다():
    카드 = ui.준비중카드()
    assert 'nc-soon' in 카드
    assert '<a ' not in 카드
    assert 'href' not in 카드
    assert '준비 중입니다' in 카드


def test_여섯칸을_준비중으로_채운다():
    난것 = ui.여섯칸([ui.카드만들기(보기글(), [])])
    assert 난것.count('class="nc"') == 6
    assert 난것.count('nc-soon') == 5


def test_여섯칸은_여섯개를_넘지_않는다():
    많이 = [ui.카드만들기(보기글(), []) for _ in range(9)]
    난것 = ui.여섯칸(많이)
    assert 난것.count('class="nc"') == 6
    assert 'nc-soon' not in 난것


def test_표시자_사이를_갈아끼운다():
    s = 'A<!-- 시작 -->옛것<!-- 끝 -->B'
    난것 = ui.갈아끼우기(s, '<!-- 시작 -->', '<!-- 끝 -->', '새것', '  ')
    assert '옛것' not in 난것 and '새것' in 난것
    assert 난것.startswith('A') and 난것.endswith('B')


def test_표시자가_없으면_None():
    assert ui.갈아끼우기('아무것도 없음', '<!-- 시작 -->', '<!-- 끝 -->', '새것', '') is None


def test_표시자를_흉내낸_제목도_안전하다():
    글 = 보기글()
    글['제목'] = '<!-- 인스타 여기까지 -->'
    카드 = ui.카드만들기(글, [])
    assert '<!-- 인스타 여기까지 -->' not in 카드     # 이스케이프되어 표시자 노릇을 못 한다
    assert '&lt;!--' in 카드
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_update_insta.py -v`
Expected: FAIL — `AttributeError: module 'update_insta' has no attribute '카드만들기'`

- [ ] **Step 3: Write minimal implementation**

`tools/update_insta.py` 맨 위 import 에 `import html` 을 더하고 아래를 덧붙인다.

```python
카드수 = 6
요약길이 = 110


def 카드만들기(글, 사진이름들):
    """카드 하나를 만듭니다. 세무뉴스 카드와 같은 모양입니다."""
    요약 = 글['설명'].replace(NL, ' ').strip()
    if len(요약) > 요약길이:
        요약 = 요약[:요약길이].rstrip() + '…'
    몸 = html.escape(글['설명']).replace(NL, '&#10;')
    return (
        '          <a class="nc" href="%s" target="_blank" rel="noopener"' % html.escape(글['주소']) + NL +
        '             data-title="%s"' % html.escape(글['제목']) + NL +
        '             data-date="%s"' % html.escape(글['날짜']) + NL +
        '             data-img="%s"' % html.escape(','.join(사진이름들)) + NL +
        '             data-imgdir="insta"' + NL +
        '             data-link-label="인스타그램에서 보기"' + NL +
        '             data-body="%s">' % 몸 + NL +
        '            <span class="nc-date">%s</span>' % html.escape(글['날짜']) + NL +
        '            <strong class="nc-title">%s</strong>' % html.escape(글['제목']) + NL +
        '            <span class="nc-sum">%s</span>' % html.escape(요약) + NL +
        '          </a>'
    )


def 준비중카드():
    """아직 게시물이 없는 칸입니다. 눌러도 아무 일이 없도록 <a> 가 아닌 <div> 로 만듭니다."""
    return (
        '          <div class="nc nc-soon">' + NL +
        '            <span class="nc-soon-mark">Instagram</span>' + NL +
        '            <strong class="nc-title">준비 중입니다</strong>' + NL +
        '            <span class="nc-sum">새 소식을 곧 전해 드리겠습니다.</span>' + NL +
        '          </div>'
    )


def 여섯칸(카드들):
    """카드가 6칸이 되도록 준비중 카드로 채웁니다."""
    골라둠 = list(카드들)[:카드수]
    while len(골라둠) < 카드수:
        골라둠.append(준비중카드())
    return NL.join(골라둠)


def 갈아끼우기(s, 시작표, 끝표, 새내용, 들여):
    a, b = s.find(시작표), s.find(끝표)
    if a == -1 or b == -1:
        return None
    return s[:a + len(시작표)] + NL + 새내용 + NL + 들여 + s[b:]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_update_insta.py -v`
Expected: 16 passed

- [ ] **Step 5: Commit**

```bash
git add tools/update_insta.py tests/test_update_insta.py
git commit -m "인스타 : 카드와 준비중 칸 만들기"
```

---

### Task 3: 전체를 잇는 main() 과 안전장치

**Files:**
- Modify: `tools/update_insta.py`
- Modify: `tests/test_update_insta.py`

**Interfaces:**
- Consumes: Task 1~2 전부. 그리고 같은 폴더의 `update_column` 에서 `사진저장`, `사진이름` 을 가져다 쓴다
- Produces: `main() -> int` — 정상 0, 실패 1

사진 저장은 **새로 만들지 않는다.** `tools/update_column.py` 의 `사진저장(주소, 폴더, 받아오기=None)` 과 `사진이름(주소)` 를 그대로 쓴다. 이미 시험을 거친 코드이고, 그 안의 `받아오기기본` 은 `pstatic.net` 일 때만 `?type=w966` 을 붙이므로 인스타 주소에는 아무 영향이 없다.

- [ ] **Step 1: Write the failing test**

`tests/test_update_insta.py` 아래에 덧붙인다.

```python
def 빈페이지(줄수=0):
    안 = NL.join('<a class="nc" href="#">옛것</a>' for _ in range(줄수))
    return 'A<!-- 인스타 여기부터 -->' + 안 + '<!-- 인스타 여기까지 -->B'


def 판깔기(tmp_path, monkeypatch, 자료값, 줄수=0):
    대상 = tmp_path / 'index.html'
    대상.write_text(빈페이지(줄수), encoding='utf-8')
    monkeypatch.setattr(ui, '뿌리', str(tmp_path))
    monkeypatch.setattr(ui, '대상', 'index.html')
    monkeypatch.setattr(ui, '사진폴더', 'insta')
    monkeypatch.setattr(ui, '받아오기', lambda: 자료값)
    monkeypatch.setattr(ui, '사진저장', lambda u, f: 'zz.jpg')
    monkeypatch.setenv('IG_ACCESS_TOKEN', '시험용가짜토큰')
    return 대상


def test_토큰이_없으면_파일을_안_건드린다(tmp_path, monkeypatch):
    대상 = 판깔기(tmp_path, monkeypatch, 자료())
    monkeypatch.delenv('IG_ACCESS_TOKEN', raising=False)
    원래 = 대상.read_bytes()
    assert ui.main() == 1
    assert 대상.read_bytes() == 원래


def test_받아오기_실패하면_파일을_안_건드린다(tmp_path, monkeypatch):
    대상 = 판깔기(tmp_path, monkeypatch, 자료())

    def 터짐():
        raise OSError('인터넷 안 됨')

    monkeypatch.setattr(ui, '받아오기', 터짐)
    원래 = 대상.read_bytes()
    assert ui.main() == 1
    assert 대상.read_bytes() == 원래


def test_게시물이_없으면_파일을_안_건드린다(tmp_path, monkeypatch):
    대상 = 판깔기(tmp_path, monkeypatch, {'data': []}, 줄수=3)
    원래 = 대상.read_bytes()
    assert ui.main() == 1
    assert 대상.read_bytes() == 원래


def test_전체가_돌면_여섯칸이_찬다(tmp_path, monkeypatch, capsys):
    대상 = 판깔기(tmp_path, monkeypatch, 자료())
    assert ui.main() == 0
    난것 = 대상.read_text(encoding='utf-8')
    assert 난것.count('class="nc"') == 6
    assert 난것.count('nc-soon') == 5
    assert '옛것' not in 난것
    assert 'data-img="zz.jpg' in 난것


def test_사진은_열두장까지만(tmp_path, monkeypatch):
    자 = 자료()
    자['data'][0]['children']['data'] = [
        {'media_url': 'https://example.com/i%02d.jpg' % n} for n in range(20)]
    대상 = 판깔기(tmp_path, monkeypatch, 자)
    monkeypatch.setattr(ui, '사진저장', lambda u, f: u.rsplit('/', 1)[-1])
    assert ui.main() == 0
    import re as _re
    m = _re.search(r'data-img="([^"]*)"', 대상.read_text(encoding='utf-8'))
    assert len(m.group(1).split(',')) == 12


def test_두번_돌리면_그대로다(tmp_path, monkeypatch, capsys):
    대상 = 판깔기(tmp_path, monkeypatch, 자료())
    assert ui.main() == 0
    한번째 = 대상.read_text(encoding='utf-8')
    assert ui.main() == 0
    assert 대상.read_text(encoding='utf-8') == 한번째
    assert '바뀐 것이 없습니다' in capsys.readouterr().out


def test_임시파일이_남지_않는다(tmp_path, monkeypatch):
    대상 = 판깔기(tmp_path, monkeypatch, 자료())
    assert ui.main() == 0
    남은것 = [f for f in os.listdir(str(tmp_path)) if f != 'index.html' and f != 'insta']
    assert 남은것 == []


def test_토큰은_화면에_안_찍힌다(tmp_path, monkeypatch, capsys):
    판깔기(tmp_path, monkeypatch, 자료())
    monkeypatch.setenv('IG_ACCESS_TOKEN', '아주비밀스러운값12345')
    ui.main()
    assert '아주비밀스러운값12345' not in capsys.readouterr().out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_update_insta.py -v`
Expected: FAIL — `AttributeError: module 'update_insta' has no attribute '뿌리'`

- [ ] **Step 3: Write minimal implementation**

`tools/update_insta.py` 맨 위 import 에 `import json`, `import os`, `import sys`, `import tempfile`, `import urllib.parse`, `import urllib.request` 를 더하고, 그 아래에 형제 파일을 가져오는 줄과 본체를 덧붙인다.

```python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from update_column import 사진저장, 사진이름          # 이미 시험을 거친 사진 저장 기능을 그대로 씁니다

API = 'https://graph.instagram.com/v21.0/me/media'
항목 = ('id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,'
      'children{media_url}')
게시물당사진 = 12
대상 = 'column/index.html'
사진폴더 = 'column/insta'
시작표 = '<!-- 인스타 여기부터 -->'
끝표 = '<!-- 인스타 여기까지 -->'

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def 받아오기():
    """인스타에 최근 게시물을 물어봅니다. 토큰은 환경변수에서만 읽습니다."""
    토큰 = os.environ.get('IG_ACCESS_TOKEN', '').strip()
    주소 = API + '?' + urllib.parse.urlencode({
        'fields': 항목, 'limit': str(카드수), 'access_token': 토큰})
    요청 = urllib.request.Request(주소, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(요청, timeout=25) as 응답:
        return json.loads(응답.read().decode('utf-8'))


def main():
    if not os.environ.get('IG_ACCESS_TOKEN', '').strip():
        print('금고에 IG_ACCESS_TOKEN 이 없습니다. 그대로 둡니다.')
        return 1

    try:
        자료 = 받아오기()
    except Exception as e:
        print('인스타에서 받아오지 못했습니다 :', 탈없는말(e))
        return 1

    글들 = 게시물정리(자료)
    if not 글들:
        print('게시물이 하나도 오지 않았습니다. 있던 카드를 그대로 둡니다.')
        return 1

    사진갈곳 = os.path.join(뿌리, 사진폴더)
    카드들 = []
    for 글 in 글들:
        이름들 = []
        for u in 글['사진'][:게시물당사진]:
            이름 = 사진저장(u, 사진갈곳)
            if 이름:
                이름들.append(이름)
        카드들.append(카드만들기(글, 이름들))

    경로 = os.path.join(뿌리, 대상)
    with io.open(경로, encoding='utf-8') as f:
        원래 = f.read()
    새것 = 갈아끼우기(원래, 시작표, 끝표, 여섯칸(카드들), '        ')
    if 새것 is None:
        print('카드 자리 표시를 찾지 못했습니다.')
        return 1
    if 새것 == 원래:
        print('바뀐 것이 없습니다.')
        return 0

    쓰기(경로, 새것)
    print('인스타 카드 %d칸을 갱신했습니다. (실제 게시물 %d건)' % (카드수, len(카드들)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

그리고 위쪽(`카드만들기` 앞)에 도우미 둘을 넣는다. `import io` 도 맨 위에 더한다.

```python
def 탈없는말(e):
    """오류 메시지에 토큰이 섞여 나오지 않게 지웁니다."""
    말 = str(e)
    토큰 = os.environ.get('IG_ACCESS_TOKEN', '').strip()
    if 토큰:
        말 = 말.replace(토큰, '(이름표)')
    return re.sub(r'access_token=[^&\s\'"]+', 'access_token=(이름표)', 말)


def 쓰기(경로, 내용):
    """임시파일에 쓴 뒤 바꿔치기합니다. 쓰다가 멈춰도 원래 파일이 깨지지 않습니다."""
    칸, 임시 = tempfile.mkstemp(dir=os.path.dirname(경로), suffix='.tmp')
    os.close(칸)
    try:
        with io.open(임시, 'w', encoding='utf-8') as f:
            f.write(내용)
        os.replace(임시, 경로)
    except Exception:
        if os.path.exists(임시):
            os.remove(임시)
        raise
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_update_insta.py -v`
Expected: 24 passed

또한 기존 시험이 깨지지 않았는지 본다.
Run: `python -m pytest tests/ -q`
Expected: 58 passed (기존 34 + 새 24)

- [ ] **Step 5: Commit**

```bash
git add tools/update_insta.py tests/test_update_insta.py
git commit -m "인스타 : 전체 잇기와 안전장치"
```

---

### Task 4: 세무소식 페이지에 카드 자리 만들기

**Files:**
- Modify: `column/index.html`
- Modify: `style.css`

**Interfaces:**
- Consumes: Task 2 가 만드는 카드 HTML (`data-img`, `data-imgdir`, `data-link-label`)
- Produces: 없음 (화면 전용)

- [ ] **Step 1: 카드 자리를 넣는다**

`column/index.html` 의 `<div class="narrow">` 바로 다음, `<!-- ================= 세무소식 =================` 주석 **앞**에 아래를 넣는다.

```html
    <!-- ================= 인스타그램 =================
         @taxpsj 최근 게시물을 하루 두 번 자동으로 받아옵니다.
         아래 '인스타 여기부터 ~ 인스타 여기까지' 사이는 자동으로 바뀌니
         손으로 고치지 말아 주세요. -->
    <div class="ig-box rv">
      <h2 class="ig-title">인스타그램</h2>
      <div class="nc-wrap">
        <button class="nc-arrow prev" id="ncPrev" type="button" aria-label="이전 게시물">
          <svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg>
        </button>
        <div class="nc-track" id="ncTrack">
          <!-- 인스타 여기부터 -->
          <!-- 인스타 여기까지 -->
        </div>
        <button class="nc-arrow next" id="ncNext" type="button" aria-label="다음 게시물">
          <svg viewBox="0 0 24 24"><path d="M9 5l7 7-7 7"/></svg>
        </button>
      </div>
    </div>
```

- [ ] **Step 2: 화살표 움직이는 코드를 가져온다**

`news/index.html` 안에 `세무사신문 카드 : 좌우 화살표로 넘겨 봅니다` 라는 주석으로 시작하는 `<script>` 블록이 있다. **그 블록을 통째로 그대로 복사**해서 `column/index.html` 의 마지막 `</script>` 다음에 붙인다. 주석의 첫 줄만 `인스타 카드 : 좌우 화살표로 넘겨 봅니다` 로 바꾼다.

그 블록은 `ncTrack` / `ncPrev` / `ncNext` 세 가지 id 를 쓰므로 Step 1 의 markup 과 그대로 맞는다. **코드는 한 글자도 고치지 말 것** — 이미 세무뉴스에서 잘 돌고 있는 것이다.

*(세무뉴스 쪽 파일은 건드리지 않는다. 두 페이지가 같은 코드를 각자 갖는 것은 이 저장소의 기존 방식이다 — 읽는 창 코드도 이미 그렇게 되어 있다.)*

- [ ] **Step 3: 읽는 창이 카드도 받아들이게 고친다**

`column/index.html` 의 읽는 창 코드에서 세 군데를 고친다.

첫째, 사진 폴더를 카드가 정하게 한다. 아래 줄을

```javascript
      그림.src = 'img/' + 이름;
```

이렇게 바꾼다.

```javascript
      그림.src = (a.dataset.imgdir || 'img') + '/' + 이름;
```

둘째, 원문 링크 글자를 카드가 정하게 한다. 아래 줄 다음에

```javascript
    원문.href = a.getAttribute('href');
```

이 줄을 더한다.

```javascript
    원문.textContent = a.dataset.linkLabel || '블로그에서 보기';
```

셋째, 카드도 눌리게 한다. 아래 줄을

```javascript
    var a = e.target.closest('.news-row');
```

이렇게 바꾼다.

```javascript
    var a = e.target.closest('.news-row, .nc');
```

- [ ] **Step 4: 준비중 카드와 제목 모양을 넣는다**

`style.css` 의 `.nv-note{ … }` 규칙 **다음**에 넣는다.

```css
/* --- 세무소식 페이지의 인스타 칸 --- */
.ig-box{ margin-bottom:54px; }
.ig-title{
  font-size:clamp(17px,2.2vw,22px); font-weight:700; color:var(--navy);
  margin-bottom:18px; letter-spacing:-.01em;
}
.nc-soon{
  display:flex; flex-direction:column; justify-content:center;
  background:var(--pale); border-top-color:var(--pale2);
  color:var(--t4); cursor:default;
}
.nc-soon .nc-title{ color:var(--t3); }
.nc-soon .nc-sum{ color:var(--t4); }
.nc-soon-mark{
  font-size:11px; font-weight:700; letter-spacing:.12em;
  color:var(--navy); opacity:.45; margin-bottom:8px;
}
@media (max-width:900px){ .ig-box{ margin-bottom:40px; } }
```

- [ ] **Step 5: 눈으로 확인하고 커밋한다**

카드가 아직 하나도 없으므로 지금은 **준비중 카드도 안 보인다.** 표시자 사이가 비어 있기 때문이다. 이 단계에서는 페이지가 깨지지 않는지만 본다.

Run: `python -m http.server 8860` 후 `http://localhost:8860/column/` 을 열어
세무소식 목록이 그대로 나오고, 자바스크립트 오류가 없으며, `인스타그램` 제목만 보이는지 확인한다. **끝나면 서버를 끈다.**

```bash
git add column/index.html style.css
git commit -m "인스타 : 세무소식 페이지에 카드 자리 만들기"
```

---

### Task 5: 실제로 한 번 돌려 카드를 채운다

**Files:**
- 생성됨: `column/insta/` (사진)
- 수정됨: `column/index.html` (표시자 사이)

**Interfaces:**
- Consumes: Task 3 의 `main()`, Task 4 의 카드 자리
- Produces: 없음

이 작업만 **인터넷과 진짜 토큰이 필요하다.** 토큰은 깃허브 금고에만 있으므로, 이 작업은 **깃허브에서 손으로 한 번 돌려서** 확인한다.

- [ ] **Step 1: 손으로 돌리는 단추를 만든다**

`.github/workflows/insta-check.yml` 을 아래로 바꾼다. (이름과 트리거는 그대로 두고 단계만 늘린다)

```yaml
# 인스타 이름표와 카드를 손으로 확인합니다.
# 저절로 돌지 않습니다. Actions 탭에서 "Run workflow" 를 눌러야만 돕니다.

name: 인스타 이름표 확인

on:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: 저장소 가져오기
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.NEWS_TOKEN || github.token }}

      - name: 파이썬 준비
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: 사진 줄이는 도구 준비
        run: python -m pip install --quiet Pillow || echo "사진 도구를 준비하지 못했습니다."

      - name: 이름표 확인
        env:
          IG_ACCESS_TOKEN: ${{ secrets.IG_ACCESS_TOKEN }}
        run: python tools/check_insta.py

      - name: 인스타 카드 채우기
        env:
          IG_ACCESS_TOKEN: ${{ secrets.IG_ACCESS_TOKEN }}
        run: python tools/update_insta.py

      - name: 바뀐 것이 있으면 올리기
        run: |
          if [ -z "$(git status --porcelain column/)" ]; then
            echo "바뀐 것이 없습니다."
            exit 0
          fi
          git config user.name  "psjtax"
          git config user.email "tax0517109685@gmail.com"
          git add column/
          git commit -m "인스타 카드 갱신 ($(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M'))"
          git push
```

- [ ] **Step 2: 문법을 확인한다**

```bash
python -c "import yaml,io;d=yaml.safe_load(io.open('.github/workflows/insta-check.yml',encoding='utf-8').read());s=d['jobs']['check']['steps'];print('단계',len(s));[print(i+1,x['name']) for i,x in enumerate(s)]"
```
Expected: 단계 6

```bash
python -c "
import subprocess,io,yaml
d=yaml.safe_load(io.open('.github/workflows/insta-check.yml',encoding='utf-8').read())
for s in d['jobs']['check']['steps']:
    if 'run' in s and s['run'].count(chr(10))>1:
        r=subprocess.run(['bash','-n'],input=s['run'],capture_output=True,text=True)
        print(('OK ' if r.returncode==0 else 'ERR'), s['name'][:24], r.stderr.strip()[:100])
"
```
Expected: 모두 OK

- [ ] **Step 3: 시험 전체를 돌린다**

Run: `python -m pytest tests/ -q`
Expected: 58 passed

- [ ] **Step 4: 커밋한다**

```bash
git add .github/workflows/insta-check.yml
git commit -m "인스타 : 손으로 카드를 채워보는 단추"
```

- [ ] **Step 5: 통제자에게 알린다**

이 단계는 **대리님이 깃허브에서 단추를 눌러야** 진행된다. 구현자는 여기서 멈추고, 통제자에게 "단추 누르기가 필요하다"고 보고한다. 구현자가 직접 push 하거나 워크플로를 실행하지 않는다.

---

### Task 6: 이름표 스스로 연장하기

**Files:**
- Create: `tools/refresh_insta_token.py`
- Create: `.github/insta-token-issued.txt` (내용은 `2026-09-04` 한 줄)
- Test: `tests/test_refresh_insta_token.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `발급일읽기(경로: str) -> datetime.date | None`
  - `발급일쓰기(경로: str, 날짜: datetime.date) -> None`
  - `연장필요한가(발급일: datetime.date, 오늘: datetime.date, 기준: int = 40) -> bool`
  - `연장하기(토큰: str, 부르기=None) -> tuple[str, int] | None` — `(새토큰, 남은초)`. 실패하면 `None`
  - `금고에넣기(주인: str, 저장소: str, 이름: str, 값: str, 깃허브토큰: str, 부르기=None) -> bool`
  - `main() -> int` — **언제나 0 을 돌려준다.** 연장 실패가 게시물 갱신을 막으면 안 된다

**왜 발급일을 파일에 적어두나 (중요)**

인스타에는 "이 이름표 며칠 남았나" 만 알려주는 창구가 없다.
`refresh_access_token` 은 남은 날을 알려주지만 **그와 동시에 새 이름표를 발급해 버린다.**
그래서 그것으로 수명을 "확인"하면 돌 때마다 이름표가 바뀌고, 게다가 메타는 **24시간 안에 두 번 연장하는 것을 거부**한다.

따라서 **발급일을 저장소 파일에 적어두고 날짜 계산으로 판단한다.** 이 파일은 비밀이 아니다(날짜뿐).

- 기준 **40일** : 60일짜리 이름표이므로 40일이 지나면 약 20일 남은 셈이다
- 연장에 성공하면 그 파일에 **오늘 날짜**를 적는다
- 파일이 없으면 **오늘 날짜를 적고 이번에는 연장하지 않는다** (처음 도는 경우)

- [ ] **Step 1: Write the failing test**

`tests/test_refresh_insta_token.py` 를 만든다.

```python
# -*- coding: utf-8 -*-
import datetime
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import refresh_insta_token as rt

날 = datetime.date


def test_발급일을_읽고_쓴다(tmp_path):
    경로 = str(tmp_path / 'issued.txt')
    assert rt.발급일읽기(경로) is None
    rt.발급일쓰기(경로, 날(2026, 9, 4))
    assert rt.발급일읽기(경로) == 날(2026, 9, 4)


def test_망가진_파일은_None(tmp_path):
    경로 = str(tmp_path / 'issued.txt')
    io.open(경로, 'w', encoding='utf-8').write('이건 날짜가 아님')
    assert rt.발급일읽기(경로) is None


def test_사십일_지나면_연장한다():
    assert rt.연장필요한가(날(2026, 9, 4), 날(2026, 10, 14)) is True   # 40일
    assert rt.연장필요한가(날(2026, 9, 4), 날(2026, 11, 1)) is True


def test_아직_이르면_연장하지_않는다():
    assert rt.연장필요한가(날(2026, 9, 4), 날(2026, 9, 14)) is False   # 10일
    assert rt.연장필요한가(날(2026, 9, 4), 날(2026, 10, 13)) is False  # 39일


def test_연장에_성공하면_새토큰을_돌려준다():
    def 가짜(주소):
        assert 'refresh_access_token' in 주소
        assert 'ig_refresh_token' in 주소
        return {'access_token': '새이름표', 'expires_in': 5184000}

    assert rt.연장하기('옛이름표', 부르기=가짜) == ('새이름표', 5184000)


def test_연장이_실패하면_None():
    def 터짐(주소):
        raise OSError('안 열림')

    assert rt.연장하기('옛이름표', 부르기=터짐) is None


def test_답이_이상하면_None():
    assert rt.연장하기('옛', 부르기=lambda u: {'error': {'message': '만료됨'}}) is None
    assert rt.연장하기('옛', 부르기=lambda u: {'access_token': ''}) is None


def test_금고에_넣을_때_값을_봉인한다():
    import base64
    from nacl import encoding, public
    쌍 = public.PrivateKey.generate()
    공개키 = 쌍.public_key.encode(encoding.Base64Encoder).decode()
    보낸것 = {}

    def 가짜(방법, 주소, 몸=None, 토큰=None):
        if 방법 == 'GET':
            return {'key': 공개키, 'key_id': '12345'}
        보낸것.update({'주소': 주소, '몸': 몸})
        return {}

    assert rt.금고에넣기('psjtax', 'company-website', 'IG_ACCESS_TOKEN',
                     '비밀값', '깃허브토큰', 부르기=가짜) is True
    assert 보낸것['주소'].endswith('/actions/secrets/IG_ACCESS_TOKEN')
    assert 보낸것['몸']['key_id'] == '12345'
    assert 보낸것['몸']['encrypted_value'] != '비밀값'
    열림 = public.SealedBox(쌍).decrypt(base64.b64decode(보낸것['몸']['encrypted_value']))
    assert 열림.decode() == '비밀값'


def test_금고에_못_넣으면_False():
    def 터짐(방법, 주소, 몸=None, 토큰=None):
        raise OSError('안 됨')

    assert rt.금고에넣기('a', 'b', 'C', 'd', 'e', 부르기=터짐) is False


def 판깔기(tmp_path, monkeypatch, 발급일=None):
    경로 = str(tmp_path / 'issued.txt')
    if 발급일:
        rt.발급일쓰기(경로, 발급일)
    monkeypatch.setattr(rt, '발급일파일', 경로)
    monkeypatch.setenv('IG_ACCESS_TOKEN', '가짜인스타토큰')
    monkeypatch.setenv('GITHUB_TOKEN_FOR_SECRETS', '가짜깃허브토큰')
    monkeypatch.setenv('GITHUB_REPOSITORY', 'psjtax/company-website')
    return 경로


def test_토큰이_없으면_조용히_넘어간다(tmp_path, monkeypatch, capsys):
    판깔기(tmp_path, monkeypatch, 날(2026, 1, 1))
    monkeypatch.delenv('IG_ACCESS_TOKEN', raising=False)
    assert rt.main() == 0
    assert '없습니다' in capsys.readouterr().out


def test_발급일_파일이_없으면_오늘로_적고_넘어간다(tmp_path, monkeypatch, capsys):
    경로 = 판깔기(tmp_path, monkeypatch)
    불렀나 = {'응': False}
    monkeypatch.setattr(rt, '연장하기',
                        lambda t, 부르기=None: 불렀나.update(응=True) or ('x', 1))
    assert rt.main() == 0
    assert 불렀나['응'] is False
    assert rt.발급일읽기(경로) == datetime.date.today()


def test_아직_이르면_아무것도_안_한다(tmp_path, monkeypatch, capsys):
    판깔기(tmp_path, monkeypatch, datetime.date.today() - datetime.timedelta(days=5))
    monkeypatch.setattr(rt, '연장하기', lambda t, 부르기=None: ('안돼', 1))
    assert rt.main() == 0
    assert '아직' in capsys.readouterr().out


def test_연장하면_발급일이_오늘로_바뀐다(tmp_path, monkeypatch):
    경로 = 판깔기(tmp_path, monkeypatch, datetime.date.today() - datetime.timedelta(days=45))
    monkeypatch.setattr(rt, '연장하기', lambda t, 부르기=None: ('새토큰', 5184000))
    monkeypatch.setattr(rt, '금고에넣기',
                        lambda 주인, 저장소, 이름, 값, 깃허브토큰, 부르기=None: True)
    assert rt.main() == 0
    assert rt.발급일읽기(경로) == datetime.date.today()


def test_금고에_못_넣으면_발급일을_안_바꾼다(tmp_path, monkeypatch, capsys):
    옛날 = datetime.date.today() - datetime.timedelta(days=45)
    경로 = 판깔기(tmp_path, monkeypatch, 옛날)
    monkeypatch.setattr(rt, '연장하기', lambda t, 부르기=None: ('새토큰', 5184000))
    monkeypatch.setattr(rt, '금고에넣기',
                        lambda 주인, 저장소, 이름, 값, 깃허브토큰, 부르기=None: False)
    assert rt.main() == 0
    assert rt.발급일읽기(경로) == 옛날          # 실패했으니 다음 번에 다시 시도해야 한다


def test_연장이_실패해도_0으로_끝난다(tmp_path, monkeypatch, capsys):
    판깔기(tmp_path, monkeypatch, datetime.date.today() - datetime.timedelta(days=45))
    monkeypatch.setattr(rt, '연장하기', lambda t, 부르기=None: None)
    assert rt.main() == 0
    assert '연장하지 못했습니다' in capsys.readouterr().out


def test_토큰은_화면에_안_찍힌다(tmp_path, monkeypatch, capsys):
    판깔기(tmp_path, monkeypatch, datetime.date.today() - datetime.timedelta(days=45))
    monkeypatch.setenv('IG_ACCESS_TOKEN', '아주비밀12345')
    monkeypatch.setenv('GITHUB_TOKEN_FOR_SECRETS', '깃허브비밀67890')
    monkeypatch.setattr(rt, '연장하기', lambda t, 부르기=None: ('새토큰abcde', 5184000))
    monkeypatch.setattr(rt, '금고에넣기',
                        lambda 주인, 저장소, 이름, 값, 깃허브토큰, 부르기=None: True)
    rt.main()
    나온말 = capsys.readouterr().out
    for 비밀 in ('아주비밀12345', '깃허브비밀67890', '새토큰abcde'):
        assert 비밀 not in 나온말
```

- [ ] **Step 2: Run test to verify it fails**

먼저 PyNaCl 을 넣는다.
Run: `python -m pip install --quiet PyNaCl`

Run: `python -m pytest tests/test_refresh_insta_token.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'refresh_insta_token'`

- [ ] **Step 3: Write minimal implementation**

`tools/refresh_insta_token.py` 를 만든다.

```python
# -*- coding: utf-8 -*-
"""인스타 이름표가 죽기 전에 스스로 연장하고, 깃허브 금고에 새로 넣어 둡니다.

  인스타 이름표는 60일이면 만료됩니다. 만료 없음으로 만들 수 없습니다(메타 정책).

  수명을 묻는 창구가 따로 없고, 연장 요청은 물어보는 순간 새 이름표를 발급해
  버립니다. 그래서 발급일을 파일에 적어두고 날짜로 판단합니다.
  (그 파일에는 날짜만 들어갑니다. 비밀이 아닙니다)

  ★ 이름표 값은 어떤 경우에도 화면에 찍지 않습니다.
  ★ 연장에 실패해도 0 으로 끝냅니다. 게시물 갱신을 막으면 안 되기 때문입니다.
"""
import base64
import datetime
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

기준일 = 40                      # 60일짜리이므로 40일이 지나면 약 20일 남은 셈입니다
연장주소 = 'https://graph.instagram.com/refresh_access_token'

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
발급일파일 = os.path.join(뿌리, '.github', 'insta-token-issued.txt')


def 발급일읽기(경로):
    """파일에 적힌 날짜를 읽습니다. 없거나 망가졌으면 None 입니다."""
    try:
        글 = io.open(경로, encoding='utf-8').read()
    except Exception:
        return None
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', 글)
    if not m:
        return None
    try:
        return datetime.date(*(int(x) for x in m.groups()))
    except ValueError:
        return None


def 발급일쓰기(경로, 날짜):
    """날짜만 한 줄 적습니다."""
    os.makedirs(os.path.dirname(경로), exist_ok=True)
    io.open(경로, 'w', encoding='utf-8').write(날짜.isoformat() + chr(10))


def 연장필요한가(발급일, 오늘, 기준=기준일):
    return (오늘 - 발급일).days >= 기준


def 열어보기(주소):
    요청 = urllib.request.Request(주소, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(요청, timeout=25) as 응답:
        return json.loads(응답.read().decode('utf-8'))


def 연장하기(토큰, 부르기=None):
    """60일짜리 새 이름표를 받습니다. 실패하면 None 입니다."""
    try:
        난것 = (부르기 or 열어보기)(연장주소 + '?' + urllib.parse.urlencode(
            {'grant_type': 'ig_refresh_token', 'access_token': 토큰}))
    except Exception:
        return None
    새것 = (난것 or {}).get('access_token') or ''
    if not 새것:
        return None
    return 새것, int((난것 or {}).get('expires_in') or 0)


def 깃허브부르기(방법, 주소, 몸=None, 토큰=None):
    자료 = json.dumps(몸).encode('utf-8') if 몸 is not None else None
    요청 = urllib.request.Request(주소, data=자료, method=방법, headers={
        'Authorization': 'Bearer %s' % 토큰,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
        'User-Agent': 'psjtax-site',
    })
    with urllib.request.urlopen(요청, timeout=25) as 응답:
        속 = 응답.read().decode('utf-8').strip()
        return json.loads(속) if 속 else {}


def 금고에넣기(주인, 저장소, 이름, 값, 깃허브토큰, 부르기=None):
    """깃허브 금고에 값을 넣습니다. 저장소 공개키로 봉인해서 보냅니다."""
    부르기 = 부르기 or 깃허브부르기
    바탕 = 'https://api.github.com/repos/%s/%s/actions/secrets' % (주인, 저장소)
    try:
        from nacl import encoding, public
        열쇠 = 부르기('GET', 바탕 + '/public-key', 토큰=깃허브토큰)
        공개키 = public.PublicKey(열쇠['key'].encode('utf-8'), encoding.Base64Encoder)
        봉인 = public.SealedBox(공개키).encrypt(값.encode('utf-8'))
        부르기('PUT', 바탕 + '/' + 이름, 몸={
            'encrypted_value': base64.b64encode(봉인).decode('utf-8'),
            'key_id': 열쇠['key_id'],
        }, 토큰=깃허브토큰)
        return True
    except Exception:
        return False


def main():
    토큰 = os.environ.get('IG_ACCESS_TOKEN', '').strip()
    if not 토큰:
        print('인스타 이름표가 없습니다. 연장은 건너뜁니다.')
        return 0

    깃허브토큰 = os.environ.get('GITHUB_TOKEN_FOR_SECRETS', '').strip()
    저장소전체 = os.environ.get('GITHUB_REPOSITORY', '').strip()
    if not 깃허브토큰 or '/' not in 저장소전체:
        print('금고에 넣을 권한이 없습니다. 연장은 건너뜁니다.')
        return 0
    주인, 저장소 = 저장소전체.split('/', 1)

    오늘 = datetime.date.today()
    발급일 = 발급일읽기(발급일파일)
    if 발급일 is None:
        발급일쓰기(발급일파일, 오늘)
        print('발급일을 처음 적어 두었습니다. 이번에는 연장하지 않습니다.')
        return 0

    지난날 = (오늘 - 발급일).days
    if not 연장필요한가(발급일, 오늘):
        print('이름표를 받은 지 %d일 되었습니다. 아직 넉넉해서 연장하지 않습니다.' % 지난날)
        return 0

    print('이름표를 받은 지 %d일 되었습니다. 연장을 받아 옵니다.' % 지난날)
    난것 = 연장하기(토큰)
    if not 난것:
        print('이름표를 연장하지 못했습니다. 다음 번에 다시 해봅니다.')
        return 0
    새토큰, 남은초 = 난것

    if 금고에넣기(주인, 저장소, 'IG_ACCESS_TOKEN', 새토큰, 깃허브토큰):
        발급일쓰기(발급일파일, 오늘)
        print('이름표를 연장해서 금고에 새로 넣었습니다. (%d일 더)' % (남은초 // 86400))
    else:
        print('연장은 받았지만 금고에 넣지 못했습니다. 다음 번에 다시 해봅니다.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: 발급일 파일을 만들고 시험을 돌린다**

`.github/insta-token-issued.txt` 를 만든다. 내용은 한 줄이다.

```
2026-09-04
```

*(대리님이 실제로 이름표를 발급받으신 날이다. 이 값으로 시작해야 만료일 계산이 맞는다)*

Run: `python -m pytest tests/test_refresh_insta_token.py -v`
Expected: 15 passed

Run: `python -m pytest tests/ -q`
Expected: 73 passed

- [ ] **Step 5: Commit**

```bash
git add tools/refresh_insta_token.py tests/test_refresh_insta_token.py .github/insta-token-issued.txt
git commit -m "인스타 : 이름표를 스스로 연장해 금고에 다시 넣기"
```

---

### Task 7: 하루 두 번 자동 갱신에 붙이기

**Files:**
- Modify: `.github/workflows/news.yml`

**Interfaces:**
- Consumes: Task 3 의 `tools/update_insta.py`, Task 6 의 `tools/refresh_insta_token.py` 와 `.github/insta-token-issued.txt`
- Produces: 없음

`.github/workflows/news.yml` 은 지금 7단계다. 반드시 지킬 것 :
- 체크아웃의 `token: ${{ secrets.NEWS_TOKEN || github.token }}` 줄은 건드리지 않는다
- 마지막 단계 `오래 조용했을 때만 살아있다는 도장 찍기` 는 **그대로 마지막**이어야 한다
- 이름표 연장은 `.github/insta-token-issued.txt` 를 고치므로 **올리기 단계보다 앞**에 와야 한다. 그래야 바뀐 날짜가 함께 올라간다

- [ ] **Step 1: 단계 세 개를 넣는다**

`블로그에서 세무소식 받아오기` 단계 **다음**에 아래 셋을 순서대로 넣는다.

```yaml
      - name: 금고 다루는 도구 준비
        run: python -m pip install --quiet PyNaCl || echo "금고 도구를 준비하지 못했습니다. 이름표 연장은 건너뜁니다."

      - name: 인스타에서 카드 받아오기
        env:
          IG_ACCESS_TOKEN: ${{ secrets.IG_ACCESS_TOKEN }}
        run: python tools/update_insta.py || echo "인스타는 이번에 건너뜁니다."

      - name: 인스타 이름표 수명 챙기기
        env:
          IG_ACCESS_TOKEN: ${{ secrets.IG_ACCESS_TOKEN }}
          GITHUB_TOKEN_FOR_SECRETS: ${{ secrets.NEWS_TOKEN }}
        run: python tools/refresh_insta_token.py || echo "이름표 연장은 이번에 건너뜁니다."
```

- [ ] **Step 2: 올리는 단계가 발급일 파일도 함께 올리게 한다**

`바뀐 것이 있으면 올리기` 단계의 `run:` 을 통째로 아래로 바꾼다.
(`column/insta/` 는 `column/` 아래라 따로 적지 않아도 된다)

```bash
          if [ -z "$(git status --porcelain news/index.html column/ .github/insta-token-issued.txt)" ]; then
            echo "새 글이 없어 올릴 것이 없습니다."
            exit 0
          fi
          git config user.name  "psjtax"
          git config user.email "tax0517109685@gmail.com"
          git add news/index.html column/ .github/insta-token-issued.txt
          git commit -m "세무뉴스·세무소식·인스타 자동 갱신 ($(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M'))"
          git push
```

- [ ] **Step 3: 문법과 차례를 확인한다**

```bash
python -c "import yaml,io;d=yaml.safe_load(io.open('.github/workflows/news.yml',encoding='utf-8').read());s=d['jobs']['update']['steps'];print('단계',len(s));[print(i+1,x['name']) for i,x in enumerate(s)]"
```
Expected: 단계 10. 차례는
1 저장소 가져오기 / 2 파이썬 준비 / 3 사진 줄이는 도구 준비 / 4 세무사신문에서 새 기사 받아오기 /
5 블로그에서 세무소식 받아오기 / 6 금고 다루는 도구 준비 / 7 인스타에서 카드 받아오기 /
8 인스타 이름표 수명 챙기기 / 9 바뀐 것이 있으면 올리기 / 10 오래 조용했을 때만 살아있다는 도장 찍기

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

- [ ] **Step 4: 시험 전체를 돌린다**

Run: `python -m pytest tests/ -q`
Expected: 73 passed

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/news.yml
git commit -m "인스타도 하루 두 번 자동으로 갱신되게"
```

---

### Task 8: 미리보기 만들어 대리님께 확인받기

**Files:**
- 없음 (확인 절차)

**Interfaces:**
- Consumes: Task 5 가 채운 카드
- Produces: 없음

- [ ] **Step 1: 눈으로 확인한다**

`python -m http.server 8860` 으로 띄워 `http://localhost:8860/column/` 을 열고 아래를 본다.
- 카드가 **6칸**이고 실제 게시물이 앞에, 준비중 카드가 뒤에 있는가
- 카드를 누르면 읽는 창에 **사진과 글**이 나오는가
- 설명글에 **`051-710-9685` 와 해시태그가 없는가**
- 창 아래 링크 글자가 **`인스타그램에서 보기`** 인가
- 아래 세무소식 목록에서 글을 누르면 링크 글자가 **`블로그에서 보기`** 로 돌아오는가
- 좌우 화살표가 동작하는가 (카드가 6개라 넘길 것이 있다)
- 휴대폰 크기(가로 375px)에서도 깨지지 않는가

**끝나면 서버를 끈다.**

- [ ] **Step 2: 미리보기 파일을 만든다**

scratchpad 의 `column_preview.py` 를 쓴다. 다만 그 스크립트는 (가) 사진을 `column/img` 에서만 찾고 (나) 읽는 창의 `그림.src = 'img/' + 이름;` 줄을 갈아끼우는데, Task 4 에서 그 줄이 바뀌었으므로 **둘 다 고쳐야 한다.**

사진 찾는 부분을 아래로 바꾼다.

```python
for 이름 in 이름들:
    길 = None
    for 폴더 in ('column/img', 'column/insta'):
        후보 = os.path.join(폴더, 이름)
        if os.path.exists(후보):
            길 = 후보
            break
    if 길:
        담김[이름] = uri(길)
        크기 += os.path.getsize(길)
```

갈아끼우는 부분을 아래로 바꾼다.

```python
옛 = "      그림.src = (a.dataset.imgdir || 'img') + '/' + 이름;"
새 = ("      var 자료 = (window.사진자료 || {})[이름];" + NL +
     "      if(!자료){ return; }                     /* 확인용 파일에 안 담긴 사진 */" + NL +
     "      그림.src = 자료;")
```

그리고 사진 이름을 모을 때 인스타 카드(`data-img` 가 카드에도 있다)를 앞쪽에 포함시킨다. 지금 코드는 `re.finditer(r'data-img="([^"]*)"', 쪽)` 로 앞에서부터 `담을글` 개만 가져오는데, 인스타 카드가 파일 앞쪽에 있으므로 **자동으로 먼저 잡힌다.** 따로 고칠 것은 없고, `담을글` 을 `7` 로 주어 인스타 1개 + 블로그 6개가 담기게 한다.

- [ ] **Step 3: 대리님께 보내고 설명한다**

`SendUserFile` 로 보내고 아래를 설명한다.
- 카드 6칸 (실제 1 + 준비중 5)
- 전화번호와 해시태그를 뺀 것
- 이름표가 스스로 연장되는 것
- 게시물을 올리시면 하루 두 번 자동으로 들어온다는 것

- [ ] **Step 4: 확인받는다**

STOP. 대리님이 좋다고 하실 때까지 올리지 않는다. (`deploy-flow` 규칙)

- [ ] **Step 5: 승인 후 올린다**

```bash
git push origin main
```

그리고 실제 사이트 `https://www.psjtax.co.kr/column/` 에서 카드가 나오는지 본다.

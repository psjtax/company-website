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
    for 찌꺼기 in ('이웃추가', '공감한 사람 보기', '댓글쓰기', '블로그 마켓', '서로이웃', '구독'):
        assert 찌꺼기 not in 글


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


def test_줄에_필요한_것이_다_들어간다():
    글 = {'제목': '세금 이야기 "첫 번째"', '주소': 'https://blog.naver.com/tax5868/1', '번호': '1', '요약': '요약'}
    줄 = uc.줄만들기(글, '첫 문단' + chr(10) + '둘째 문단', ['aa.jpg', 'bb.jpg'])
    assert 'class="news-row"' in 줄
    assert 'href="https://blog.naver.com/tax5868/1"' in 줄
    assert '&quot;' in 줄                      # 제목의 따옴표가 안전하게 바뀐다
    assert 'data-img="aa.jpg,bb.jpg"' in 줄
    assert '&#10;' in 줄                       # 문단 구분
    assert 'news-date' not in 줄               # 날짜는 넣지 않는다
    assert 'data-date' not in 줄               # 날짜 속성도 넣지 않는다


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

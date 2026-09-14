# -*- coding: utf-8 -*-
import html
import io
import os
import re
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


def test_문단이_자연스럽게_합쳐진다():
    """네이버는 줄마다 <p> 를 따로 씌우므로, 폭 없는 공백 줄로 표시된 진짜 문단
       구분만 살리고 나머지 줄은 한 문장으로 합쳐야 한다."""
    글, 사진 = uc.본문뽑기(자료글('blog_post.html'))
    문단들 = 글.split(chr(10))
    assert len(문단들) < 30                     # 94개 조각이 아니라 자연스러운 문단 수
    assert '안녕하세요. 세금 고민을 시원하게 해결하는 박성진 세무사입니다.' in 문단들


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


def test_사진주소에_원본크기를_붙인다():
    assert uc.사진주소크게('https://postfiles.pstatic.net/aaa/bbb.jpg') == \
        'https://postfiles.pstatic.net/aaa/bbb.jpg?type=w966'


def test_이미_크기가_있으면_그대로_둔다():
    주소 = 'https://postfiles.pstatic.net/aaa/bbb.jpg?type=w80'
    assert uc.사진주소크게(주소) == 주소


def test_네이버_사진이_아니면_그대로_둔다():
    주소 = 'https://example.com/aaa/bbb.jpg'
    assert uc.사진주소크게(주소) == 주소


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
    assert 난것.count('class="news-row"') == uc.목록수   # 최근 것부터 정해진 수만큼만
    assert 'data-img="zz.jpg' in 난것


def test_사진은_열두장까지만_들어간다(tmp_path, monkeypatch):
    대상 = tmp_path / 'index.html'
    대상.write_text('A<!-- 글 여기부터 -->옛것<!-- 글 여기까지 -->B', encoding='utf-8')

    monkeypatch.setattr(uc, '뿌리', str(tmp_path))
    monkeypatch.setattr(uc, '대상', 'index.html')
    monkeypatch.setattr(uc, '사진폴더', 'img')
    monkeypatch.setattr(uc, '쉬는시간', 0)
    monkeypatch.setattr(uc, '받아오기RSS', lambda: 자료('blog_rss.xml'))

    사진들 = ''.join(
        '<img data-lazy-src="https://postfiles.pstatic.net/x/img%02d.jpg">' % i
        for i in range(20)
    )
    합성쪽 = ('<div class="se-main-container"><p>%s</p>%s</div>'
             % ('본문 내용입니다. ' * 30, 사진들))
    monkeypatch.setattr(uc, '받아오기글', lambda 번호: 합성쪽)
    monkeypatch.setattr(uc, '사진저장', lambda u, f, 받아오기=None: uc.사진이름(u))

    assert uc.main() == 0
    난것 = 대상.read_text(encoding='utf-8')
    m = re.search(r'data-img="([^"]*)"', 난것)
    assert m is not None
    이름들 = m.group(1).split(',')
    assert len(이름들) == 12                    # 20장 중 12장까지만


def test_본문도_요약도_짧으면_건너뛴다(tmp_path, monkeypatch, capsys):
    """모든 글이 건너뛰어지면(본문·요약 모두 너무 짧음) 화면을 비우는 대신
       기존 화면을 그대로 지키고 실패로 보고해야 한다 (Finding 1)."""
    대상 = tmp_path / 'index.html'
    원래 = 'A<!-- 글 여기부터 -->옛것<!-- 글 여기까지 -->B'
    대상.write_text(원래, encoding='utf-8')
    원래바이트 = 대상.read_bytes()

    monkeypatch.setattr(uc, '뿌리', str(tmp_path))
    monkeypatch.setattr(uc, '대상', 'index.html')
    monkeypatch.setattr(uc, '사진폴더', 'img')
    monkeypatch.setattr(uc, '쉬는시간', 0)
    monkeypatch.setattr(uc, '받아오기RSS', lambda: b'')
    monkeypatch.setattr(uc, '고른글', lambda 원본: [
        {'제목': '본문이 짧은 글', '주소': 'https://blog.naver.com/tax5868/1',
         '번호': '1', '요약': '짧음'},
    ])
    monkeypatch.setattr(uc, '받아오기글', lambda 번호: '<html><body>본문 없음</body></html>')

    assert uc.main() == 1
    출력 = capsys.readouterr().out
    assert '본문을 못 가져와 건너뜁니다' in 출력
    assert '기존 화면을 그대로 둡니다' in 출력
    assert 대상.read_bytes() == 원래바이트          # 파일이 한 바이트도 바뀌지 않는다


def test_두번_돌리면_그대로다(tmp_path, monkeypatch, capsys):
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
    한번째 = 대상.read_text(encoding='utf-8')

    capsys.readouterr()                        # 첫 실행 출력은 비워둔다
    assert uc.main() == 0
    두번째 = 대상.read_text(encoding='utf-8')

    assert 두번째 == 한번째
    assert '바뀐 것이 없습니다.' in capsys.readouterr().out


# ── 이 아래는 최종 코드 리뷰에서 나온 안전장치들에 대한 테스트다 ──────────────

합성본문 = ('<div class="se-main-container"><p>'
         + '실제 본문 내용입니다. ' * 50 + '</p></div>')     # 길이 200자 넉넉히 넘음


def _가짜글목록(개수):
    return [
        {'제목': '글%d' % i, '주소': 'https://blog.naver.com/tax5868/%d' % i,
         '번호': str(i), '요약': '요약%d' % i}
        for i in range(개수)
    ]


def test_모두_건너뛰면_기존화면을_지킨다(tmp_path, monkeypatch, capsys):
    """Finding 1 : 모든 글이 건너뛰어져 줄들이 비면, 빈 화면을 올리는 대신
       기존 화면을 지키고 main() 은 1을 돌려줘야 한다."""
    대상 = tmp_path / 'index.html'
    원래 = 'A<!-- 글 여기부터 -->옛것<!-- 글 여기까지 -->B'
    대상.write_text(원래, encoding='utf-8')
    원래바이트 = 대상.read_bytes()

    monkeypatch.setattr(uc, '뿌리', str(tmp_path))
    monkeypatch.setattr(uc, '대상', 'index.html')
    monkeypatch.setattr(uc, '사진폴더', 'img')
    monkeypatch.setattr(uc, '쉬는시간', 0)
    monkeypatch.setattr(uc, '받아오기RSS', lambda: b'')
    monkeypatch.setattr(uc, '고른글', lambda 원본: [
        {'제목': '짧은 글 1', '주소': 'https://blog.naver.com/tax5868/1',
         '번호': '1', '요약': '짧음'},
        {'제목': '짧은 글 2', '주소': 'https://blog.naver.com/tax5868/2',
         '번호': '2', '요약': '짧음'},
    ])
    monkeypatch.setattr(uc, '받아오기글', lambda 번호: '<html><body>본문 없음</body></html>')

    assert uc.main() == 1
    assert '기존 화면을 그대로 둡니다' in capsys.readouterr().out
    assert 대상.read_bytes() == 원래바이트


def test_본문을_대부분_못받으면_중단한다(tmp_path, monkeypatch, capsys):
    """Finding 2 (폴백 과반 가드) : 절반을 넘는 글이 요약으로 대체되면
       (네이버가 요청을 막은 경우 등) 화면을 바꾸지 않고 중단해야 한다."""
    대상 = tmp_path / 'index.html'
    원래 = 'A<!-- 글 여기부터 -->옛것<!-- 글 여기까지 -->B'
    대상.write_text(원래, encoding='utf-8')
    원래바이트 = 대상.read_bytes()

    긴요약 = '나' * 90                              # 80자 문턱은 넘지만 본문은 아님
    글목록 = [
        {'제목': '글1', '주소': 'https://blog.naver.com/tax5868/1', '번호': '1', '요약': 긴요약},
        {'제목': '글2', '주소': 'https://blog.naver.com/tax5868/2', '번호': '2', '요약': 긴요약},
        {'제목': '글3', '주소': 'https://blog.naver.com/tax5868/3', '번호': '3', '요약': 긴요약},
        {'제목': '글4', '주소': 'https://blog.naver.com/tax5868/4', '번호': '4', '요약': 긴요약},
    ]

    monkeypatch.setattr(uc, '뿌리', str(tmp_path))
    monkeypatch.setattr(uc, '대상', 'index.html')
    monkeypatch.setattr(uc, '사진폴더', 'img')
    monkeypatch.setattr(uc, '쉬는시간', 0)
    monkeypatch.setattr(uc, '받아오기RSS', lambda: b'')
    monkeypatch.setattr(uc, '고른글', lambda 원본: 글목록)

    def 받아오기글(번호):
        if 번호 in ('1', '2', '3'):
            raise OSError('네이버가 막았습니다')      # 4건 중 3건이 요약으로 대체됨
        return 합성본문

    monkeypatch.setattr(uc, '받아오기글', 받아오기글)

    assert uc.main() == 1
    출력 = capsys.readouterr().out
    assert '본문을 제대로 못 받았습니다' in 출력
    assert '4건 중 3건' in 출력
    assert 대상.read_bytes() == 원래바이트


def test_기존보다_크게_줄면_중단한다(tmp_path, monkeypatch, capsys):
    """Finding 2 (줄어듦 가드) : 마커 위 안내 주석 속 예시 한 줄은 세지 않고,
       마커 사이의 34건이 3건으로 크게 줄면 중단해야 한다."""
    대상 = tmp_path / 'index.html'
    예시줄 = '<!-- 사용 예시 : <a class="news-row" href="#">이렇게 나옵니다</a> -->'
    기존행들 = uc.NL.join(
        '<a class="news-row" href="#">기존글%d</a>' % i for i in range(34))
    원래 = 예시줄 + uc.NL + uc.시작표 + uc.NL + 기존행들 + uc.NL + uc.끝표
    대상.write_text(원래, encoding='utf-8')
    원래바이트 = 대상.read_bytes()

    monkeypatch.setattr(uc, '뿌리', str(tmp_path))
    monkeypatch.setattr(uc, '대상', 'index.html')
    monkeypatch.setattr(uc, '사진폴더', 'img')
    monkeypatch.setattr(uc, '쉬는시간', 0)
    monkeypatch.setattr(uc, '받아오기RSS', lambda: b'')
    monkeypatch.setattr(uc, '고른글', lambda 원본: _가짜글목록(3))
    monkeypatch.setattr(uc, '받아오기글', lambda 번호: 합성본문)

    assert uc.main() == 1
    출력 = capsys.readouterr().out
    assert '크게 줄었습니다' in 출력
    assert 대상.read_bytes() == 원래바이트


def test_기존보다_조금_줄면_허용된다(tmp_path, monkeypatch):
    """Finding 2 (줄어듦 가드) : 한 건 줄어드는 것은 글쓴이가 직접 지운
       정상 상황일 수 있으므로 막지 않는다."""
    대상 = tmp_path / 'index.html'
    기존행들 = uc.NL.join(
        '<a class="news-row" href="#">기존글%d</a>' % i for i in range(uc.목록수))
    원래 = uc.시작표 + uc.NL + 기존행들 + uc.NL + uc.끝표
    대상.write_text(원래, encoding='utf-8')

    monkeypatch.setattr(uc, '뿌리', str(tmp_path))
    monkeypatch.setattr(uc, '대상', 'index.html')
    monkeypatch.setattr(uc, '사진폴더', 'img')
    monkeypatch.setattr(uc, '쉬는시간', 0)
    monkeypatch.setattr(uc, '받아오기RSS', lambda: b'')
    monkeypatch.setattr(uc, '고른글', lambda 원본: _가짜글목록(uc.목록수 - 1))
    monkeypatch.setattr(uc, '받아오기글', lambda 번호: 합성본문)

    assert uc.main() == 0
    난것 = 대상.read_text(encoding='utf-8')
    assert 난것.count('class="news-row"') == uc.목록수 - 1
    assert '기존글0' not in 난것


def test_글이_많아도_목록수까지만_쓴다(tmp_path, monkeypatch):
    """블로그에 34건이 있어도 화면에는 최근 목록수(10)건만 올린다."""
    대상 = tmp_path / 'index.html'
    대상.write_text(uc.시작표 + uc.NL + uc.끝표, encoding='utf-8')

    monkeypatch.setattr(uc, '뿌리', str(tmp_path))
    monkeypatch.setattr(uc, '대상', 'index.html')
    monkeypatch.setattr(uc, '사진폴더', 'img')
    monkeypatch.setattr(uc, '쉬는시간', 0)
    monkeypatch.setattr(uc, '받아오기RSS', lambda: b'')
    monkeypatch.setattr(uc, '고른글', lambda 원본: _가짜글목록(34))
    monkeypatch.setattr(uc, '받아오기글', lambda 번호: 합성본문)

    assert uc.main() == 0
    난것 = 대상.read_text(encoding='utf-8')
    assert 난것.count('class="news-row"') == uc.목록수


def test_일부_실패해도_요약으로_채워진다(tmp_path, monkeypatch):
    """Finding 2 관련 커버리지 : 한 글만 받아오기글 이 실패해도(네트워크 오류 등)
       그 글은 요약으로 대체되어 줄에 들어가고, main() 은 성공(0)해야 한다."""
    대상 = tmp_path / 'index.html'
    대상.write_text('A<!-- 글 여기부터 -->옛것<!-- 글 여기까지 -->B', encoding='utf-8')

    monkeypatch.setattr(uc, '뿌리', str(tmp_path))
    monkeypatch.setattr(uc, '대상', 'index.html')
    monkeypatch.setattr(uc, '사진폴더', 'img')
    monkeypatch.setattr(uc, '쉬는시간', 0)
    monkeypatch.setattr(uc, '받아오기RSS', lambda: b'')

    긴요약 = '실패한 글의 요약입니다. ' * 10          # 80자 문턱을 넉넉히 넘김
    글목록 = [
        {'제목': '실패한 글', '주소': 'https://blog.naver.com/tax5868/1',
         '번호': '1', '요약': 긴요약},
        {'제목': '성공한 글', '주소': 'https://blog.naver.com/tax5868/2',
         '번호': '2', '요약': '짧은 요약'},
    ]
    monkeypatch.setattr(uc, '고른글', lambda 원본: 글목록)

    def 받아오기글(번호):
        if 번호 == '1':
            raise OSError('타임아웃')
        return 합성본문

    monkeypatch.setattr(uc, '받아오기글', 받아오기글)

    assert uc.main() == 0
    난것 = 대상.read_text(encoding='utf-8')
    assert 난것.count('class="news-row"') == 2
    assert ('data-body="%s"' % html.escape(긴요약)) in 난것


def test_제목에_마커문구가_있어도_안전하다(tmp_path, monkeypatch):
    """Finding 3(마커 주입) : 글 제목에 끝표 마커와 똑같은 문구가 들어 있어도
       html.escape 덕분에 실제 마커로 오인되지 않아야 한다."""
    대상 = tmp_path / 'index.html'
    대상.write_text('A<!-- 글 여기부터 -->옛것<!-- 글 여기까지 -->B', encoding='utf-8')

    monkeypatch.setattr(uc, '뿌리', str(tmp_path))
    monkeypatch.setattr(uc, '대상', 'index.html')
    monkeypatch.setattr(uc, '사진폴더', 'img')
    monkeypatch.setattr(uc, '쉬는시간', 0)
    monkeypatch.setattr(uc, '받아오기RSS', lambda: b'')

    글목록 = [
        {'제목': '이상한 제목 <!-- 글 여기까지 --> 입니다',
         '주소': 'https://blog.naver.com/tax5868/1', '번호': '1', '요약': '요약'},
        {'제목': '평범한 제목', '주소': 'https://blog.naver.com/tax5868/2',
         '번호': '2', '요약': '요약'},
    ]
    monkeypatch.setattr(uc, '고른글', lambda 원본: 글목록)
    monkeypatch.setattr(uc, '받아오기글', lambda 번호: 합성본문)

    assert uc.main() == 0
    난것 = 대상.read_text(encoding='utf-8')
    assert 난것.count(uc.시작표) == 1
    assert 난것.count(uc.끝표) == 1
    assert 난것.count('class="news-row"') == 2


def test_성공하면_임시파일이_남지_않는다(tmp_path, monkeypatch):
    """Finding 4(원자적 쓰기) : 정상적으로 끝나면 임시로 만든 파일이
       폴더에 남아 있으면 안 된다."""
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
    남은파일들 = os.listdir(str(tmp_path))
    assert 남은파일들 == ['index.html']             # 임시 파일이 남아있지 않다

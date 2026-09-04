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
    for 찌꺼기 in ('이웃추가', '공감한 사람 보기', '댓글쓰기'):
        assert 찌꺼기 not in 글

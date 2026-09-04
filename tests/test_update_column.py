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

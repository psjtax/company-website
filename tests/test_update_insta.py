# -*- coding: utf-8 -*-
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import update_insta as ui


def 칸수(s):
    """카드 칸 수를 셉니다. class="nc" 와 class="nc nc-soon" 을 둘 다 셉니다."""
    import re as _re
    return len(_re.findall(r'class="nc[ "]', s))


def 준비중수(s):
    import re as _re
    return len(_re.findall(r'class="nc nc-soon"', s))


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


def test_날짜와_금액이_있는_줄은_안_지운다():
    글 = '2026년 05월 17일까지 109,685원 납부하세요'
    assert ui.설명다듬기(글) == 글


def test_다른_긴_숫자줄은_안_지운다():
    for 글 in ('신고기한 2026-09-30 까지입니다',
               '사업자등록번호 878-28-01274',
               '작년 매출 1,234,567,890원'):
        assert ui.설명다듬기(글) == 글


def test_띄어쓴_전화번호도_지운다():
    assert ui.설명다듬기('문의 051 710 9685') == ''
    assert ui.설명다듬기('문의 051-710-9685') == ''
    assert ui.설명다듬기('전화: 051.710.9685 입니다') == ''


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
    assert 'class="nc nc-soon"' in 카드
    assert '<a ' not in 카드
    assert 'href' not in 카드
    assert '준비 중입니다' in 카드


def test_여섯칸을_준비중으로_채운다():
    난것 = ui.여섯칸([ui.카드만들기(보기글(), [])])
    assert 칸수(난것) == 6
    assert 준비중수(난것) == 5


def test_여섯칸은_여섯개를_넘지_않는다():
    많이 = [ui.카드만들기(보기글(), []) for _ in range(9)]
    난것 = ui.여섯칸(많이)
    assert 칸수(난것) == 6
    assert 준비중수(난것) == 0


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

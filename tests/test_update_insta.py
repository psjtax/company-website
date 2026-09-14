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

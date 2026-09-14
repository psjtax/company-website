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
전화꼴 = re.compile(r'\d[\d\-.\u2010-\u2015\s]{7,}\d')
사무실숫자 = re.sub(r'[^0-9]', '', 숨길번호)


def 전화번호줄인가(줄):
    """사무실 번호가 들어있는 줄인지 봅니다.
       숫자 덩어리를 통째로 이어 붙이면 날짜·금액이 전화번호로 오인되므로,
       전화번호처럼 생긴 부분만 골라서 견줍니다."""
    줄 = 줄 or ''
    if 숨길번호 in 줄:
        return True
    for 조각 in 전화꼴.findall(줄):
        if 사무실숫자 in re.sub(r'[^0-9]', '', 조각):
            return True
    return False


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

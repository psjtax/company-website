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

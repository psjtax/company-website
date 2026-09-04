# -*- coding: utf-8 -*-
"""사무소 네이버 블로그의 '세금이야기' 글을 받아 column/index.html 을 채웁니다.

  · 목록과 본문을 사이트 안에서 읽을 수 있게 넣습니다
  · 사진은 네이버가 직접 부르는 것을 막아두어, 내려받아 column/img/ 에 둡니다
  GitHub Actions 가 하루 두 번 자동으로 돌립니다.
  손으로 돌려보려면 :  python tools/update_column.py
"""
import hashlib
import html
import io
import os
import re
import urllib.request
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


NL = chr(10)
지울것 = re.compile(r'<(script|style)[^>]*>.*?</\1>', re.S)

# 본문이 끝나고 태그·공감·댓글 같은 페이지 꾸밈이 시작되는 지점을 나타내는 표시들.
# 실제 글에는 이 중 어느 것이 먼저 나오는지 페이지마다 달라서, 가장 먼저 나오는 것을 기준으로 자른다.
본문끝표시 = ('post_footer', 'post_btn', 'wrap_postcomment', 'area_sympathy', 'se_doc_footer')


def 본문뽑기(쪽):
    """본문 영역에서 글자와 사진 주소를 뽑습니다.
       사진 주소는 게으른 불러오기(data-lazy-src)에 들어 있습니다."""
    m = re.search(r'<div class="se-main-container">(.*)', 쪽 or '', re.S)
    if not m:
        return '', []
    본 = m.group(1)

    끝후보 = [i for i in (본.find(표시) for 표시 in 본문끝표시) if i != -1]
    if 끝후보:
        본 = 본[:min(끝후보)]

    # 자르는 지점이 태그 한가운데일 수 있다 (예: '<div id="' 처럼 닫는 '>' 없이 끝남).
    # 그런 잘린 조각은 태그로 인식되지 못해 글자로 남아버리니 미리 잘라낸다.
    잘린조각 = re.search(r'<[^>]*$', 본)
    if 잘린조각:
        본 = 본[:잘린조각.start()]

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

# -*- coding: utf-8 -*-
"""사무소 인스타그램(@taxpsj) 최근 게시물을 받아 세무소식 페이지의 카드를 채웁니다.

  · 설명글에서 사무실 전화번호 줄과 해시태그 줄은 빼고 보여줍니다
  · 사진은 인스타 주소가 만료되므로 내려받아 column/insta/ 에 둡니다
  GitHub Actions 가 하루 두 번 자동으로 돌립니다.
  손으로 돌려보려면 :  IG_ACCESS_TOKEN 을 환경변수로 주고  python tools/update_insta.py
"""
import html
import io
import json
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request

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


카드수 = 6
요약길이 = 110


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

    try:
        쓰기(경로, 새것)
    except Exception as e:
        print('파일을 쓰지 못했습니다 :', 탈없는말(e))
        return 1
    print('인스타 카드 %d칸을 갱신했습니다. (실제 게시물 %d건)' % (카드수, len(카드들)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

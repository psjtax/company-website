# -*- coding: utf-8 -*-
"""세무사신문(한국세무사회) 새 기사를 받아 news/index.html 을 갱신합니다.

  두 곳을 채웁니다.
    · 카드 슬라이드 — 가장 최근 기사 6건 (제목 + 짧은 요약)
    · 목록          — 최근 기사 50건 (제목 + 날짜)

  기사 본문은 옮기지 않습니다. 제목을 누르면 세무사신문 원문으로 이동합니다.
  GitHub Actions 가 하루 두 번 자동으로 돌립니다.
  손으로 돌려보려면 :  python tools/update_news.py
"""
import html
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

RSS = 'https://webzine.kacta.or.kr/rss/allArticle.xml'
목록수 = 50          # 목록에 실을 기사 수 (한 쪽에 10건씩)
카드수 = 6           # 카드로 보여줄 최근 기사 수
요약길이 = 95        # 카드에 실을 요약 글자 수 (원문 전체가 아닌 앞부분만)

대상 = 'news/index.html'
표 = {
    '카드': ('<!-- 카드 여기부터 자동 -->', '<!-- 카드 여기까지 자동 -->'),
    '목록': ('<!-- 여기부터 자동 -->', '<!-- 여기까지 자동 -->'),
}

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def 받아오기():
    요청 = urllib.request.Request(RSS, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(요청, timeout=25) as 응답:
        return 응답.read()


def 정리(값):
    return html.escape((값 or '').strip())


def 날짜다듬기(값):
    """2026-09-03 14:57:24  →  2026. 09. 03"""
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', (값 or '').strip())
    return '%s. %s. %s' % m.groups() if m else 정리(값)[:10]


def 요약다듬기(값):
    """태그를 걷어내고 앞부분만 짧게 잘라옵니다."""
    글 = re.sub(r'<[^>]+>', ' ', html.unescape(값 or ''))
    글 = re.sub(r'[■▲▶◆●□]', ' ', 글)
    글 = re.sub(r'\s+', ' ', 글).strip()
    if len(글) > 요약길이:
        글 = 글[:요약길이].rstrip() + '…'
    return html.escape(글)


def 카드만들기(항목):
    줄 = []
    for it in 항목[:카드수]:
        제목, 주소 = 정리(it.findtext('title')), 정리(it.findtext('link'))
        if not 제목 or not 주소:
            continue
        줄.append(
            '          <a class="nc" href="%s" target="_blank" rel="noopener">\n'
            '            <span class="nc-date">%s</span>\n'
            '            <strong class="nc-title">%s</strong>\n'
            '            <span class="nc-sum">%s</span>\n'
            '          </a>' % (주소, 날짜다듬기(it.findtext('pubDate')), 제목,
                               요약다듬기(it.findtext('description'))))
    return '\n'.join(줄)


def 목록만들기(항목):
    줄 = []
    for it in 항목[:목록수]:
        제목, 주소 = 정리(it.findtext('title')), 정리(it.findtext('link'))
        if not 제목 or not 주소:
            continue
        줄.append(
            '        <a class="news-row" href="%s" target="_blank" rel="noopener">\n'
            '          <span class="news-title">%s</span>\n'
            '          <span class="news-date">%s</span>\n'
            '        </a>' % (주소, 제목, 날짜다듬기(it.findtext('pubDate'))))
    return '\n'.join(줄)


def 갈아끼우기(s, 시작표, 끝표, 새내용, 들여):
    a, b = s.find(시작표), s.find(끝표)
    if a == -1 or b == -1:
        return None
    return s[:a + len(시작표)] + '\n' + 새내용 + '\n' + 들여 + s[b:]


def main():
    try:
        원본 = 받아오기()
    except Exception as e:
        print('세무사신문에서 받아오지 못했습니다 :', e)
        return 1

    항목 = ET.fromstring(원본).find('channel').findall('item')
    if not 항목:
        print('기사가 하나도 없습니다. 그대로 둡니다.')
        return 1

    경로 = os.path.join(뿌리, 대상)
    s = 원래 = open(경로, encoding='utf-8').read()

    s2 = 갈아끼우기(s, 표['카드'][0], 표['카드'][1], 카드만들기(항목), '        ')
    if s2 is None:
        print('카드 자리 표시를 찾지 못했습니다.')
        return 1
    s = s2

    s2 = 갈아끼우기(s, 표['목록'][0], 표['목록'][1], 목록만들기(항목), '        ')
    if s2 is None:
        print('목록 자리 표시를 찾지 못했습니다.')
        return 1
    s = s2

    if s == 원래:
        print('새 기사가 없습니다.')
        return 0

    open(경로, 'w', encoding='utf-8').write(s)
    print('카드 %d건, 목록 %d건으로 갱신했습니다.'
          % (min(len(항목), 카드수), min(len(항목), 목록수)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""세무사신문(한국세무사회) 새 기사를 받아 news/index.html 을 갱신합니다.

  두 곳을 채웁니다.
    · 카드 슬라이드 — 가장 최근 기사 6건 (제목 + 짧은 요약)
    · 목록          — 최근 기사 50건 (제목 + 날짜)

  기사를 누르면 사이트 안 창에서 본문을 읽을 수 있고, 창 아래에 출처와 원문 링크가 있습니다.
  (한국세무사회 정회원 자격으로 이용합니다. 사진은 가져오지 않습니다)
  GitHub Actions 가 하루 두 번 자동으로 돌립니다.
  손으로 돌려보려면 :  python tools/update_news.py
"""
import html
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

RSS = 'https://webzine.kacta.or.kr/rss/allArticle.xml'
목록수 = 50          # 목록에 실을 기사 수 (한 쪽에 10건씩)
카드수 = 6           # 카드로 보여줄 최근 기사 수
요약길이 = 95        # 카드에 보이는 요약 글자 수
펼침길이 = 400       # 눌렀을 때 보여줄 요약 (RSS 가 주는 앞부분 발췌 그대로)

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


def 기사본문(주소):
    """기사 페이지에서 본문 글자만 가져옵니다. 사진은 가져오지 않습니다.
       (세무사회 정회원 자격으로 이용, 화면 아래에 출처를 밝힙니다)"""
    try:
        요청 = urllib.request.Request(주소, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(요청, timeout=20) as 응답:
            쪽 = 응답.read().decode('utf-8', 'replace')
    except Exception:
        return ''

    m = re.search(r'<article[^>]*itemprop="articleBody"[^>]*>(.*?)</article>', 쪽, re.S)
    if not m:
        return ''

    글 = m.group(1)
    글 = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', 글, flags=re.S)
    글 = re.sub(r'<figcaption[^>]*>.*?</figcaption>', ' ', 글, flags=re.S)   # 사진 설명
    글 = re.sub(r'<br\s*/?>', chr(10), 글)
    글 = re.sub(r'</(p|div)>', chr(10) * 2, 글)
    글 = re.sub(r'<[^>]+>', ' ', 글)
    글 = html.unescape(글).replace(chr(0xa0), ' ')
    글 = re.sub(r'\[[^\]]{0,40}(자료사진|사진|제공)[^\]]{0,20}\]', ' ', 글)
    글 = re.sub(r'[ \t]+', ' ', 글)
    글 = re.sub(chr(10) + r'[ \t]*', chr(10), 글)
    글 = re.sub(chr(10) + r'{3,}', chr(10) * 2, 글).strip()
    return 글


def 본문정리(값):
    """태그를 걷어낸 글만 남깁니다. (세무사신문 RSS 가 주는 앞부분 발췌)"""
    글 = re.sub(r'<[^>]+>', ' ', html.unescape(값 or ''))
    글 = re.sub(r'[■▲▶◆●□]', ' ', 글)
    return re.sub(r'\s+', ' ', 글).strip()


def 요약다듬기(값, 길이=None):
    글 = 본문정리(값)
    길이 = 길이 or 요약길이
    if len(글) > 길이:
        글 = 글[:길이].rstrip() + '…'
    return html.escape(글)


def 읽을거리(it):
    """본문을 가져오되, 못 가져오면 RSS 요약으로 대신합니다."""
    본문 = 기사본문((it.findtext('link') or '').strip())
    if len(본문) < 120:
        본문 = 본문정리(it.findtext('description'))
    return html.escape(본문).replace(chr(10), '&#10;')


def 카드만들기(항목):
    줄 = []
    for it in 항목[:카드수]:
        제목, 주소 = 정리(it.findtext('title')), 정리(it.findtext('link'))
        if not 제목 or not 주소:
            continue
        날짜 = 날짜다듬기(it.findtext('pubDate'))
        줄.append(
            '          <a class="nc" href="%s" data-title="%s" data-date="%s" data-body="%s">\n'
            '            <span class="nc-date">%s</span>\n'
            '            <strong class="nc-title">%s</strong>\n'
            '            <span class="nc-sum">%s</span>\n'
            '          </a>' % (주소, 제목, 날짜, 읽을거리(it),
                               날짜, 제목,
                               요약다듬기(it.findtext('description'))))
    return '\n'.join(줄)


def 목록만들기(항목):
    줄 = []
    for n, it in enumerate(항목[:목록수]):
        제목, 주소 = 정리(it.findtext('title')), 정리(it.findtext('link'))
        if not 제목 or not 주소:
            continue
        날짜 = 날짜다듬기(it.findtext('pubDate'))
        본문 = 읽을거리(it)
        time.sleep(0.25)                       # 상대 서버에 부담 주지 않게
        if n % 10 == 9:
            print('  본문 %d건 가져옴…' % (n + 1))
        줄.append(
            '        <a class="news-row" href="%s" data-title="%s" data-date="%s" data-body="%s">\n'
            '          <span class="news-title">%s</span>\n'
            '          <span class="news-date">%s</span>\n'
            '        </a>' % (주소, 제목, 날짜, 본문, 제목, 날짜))
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

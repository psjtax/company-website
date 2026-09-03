# -*- coding: utf-8 -*-
"""세무사신문(한국세무사회) 새 기사를 받아 news/index.html 목록을 갱신합니다.

  · 기사 제목 · 날짜 · 원문 주소만 싣고, 본문은 옮기지 않습니다.
    (제목을 누르면 세무사신문 원문으로 이동합니다)
  · GitHub Actions 가 하루 두 번 자동으로 돌립니다.
  · 손으로 돌려보려면 :  python tools/update_news.py
"""
import html
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

RSS = 'https://webzine.kacta.or.kr/rss/allArticle.xml'
개수 = 12                      # 화면에 보여줄 기사 수
대상 = 'news/index.html'
시작표 = '<!-- 여기부터 자동 -->'
끝표 = '<!-- 여기까지 자동 -->'

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


def 만들기(항목):
    줄 = []
    for it in 항목[:개수]:
        제목 = 정리(it.findtext('title'))
        주소 = 정리(it.findtext('link'))
        날짜 = 날짜다듬기(it.findtext('pubDate'))
        if not 제목 or not 주소:
            continue
        줄.append(
            '        <a class="news-item" href="%s" target="_blank" rel="noopener">\n'
            '          <span class="news-date">%s</span>\n'
            '          <span class="news-title">%s</span>\n'
            '        </a>' % (주소, 날짜, 제목))
    return '\n'.join(줄)


def main():
    try:
        원본 = 받아오기()
    except Exception as e:
        print('세무사신문에서 받아오지 못했습니다 :', e)
        return 1

    뿌리요소 = ET.fromstring(원본)
    항목 = 뿌리요소.find('channel').findall('item')
    if not 항목:
        print('기사가 하나도 없습니다. 그대로 둡니다.')
        return 1

    새목록 = 만들기(항목)
    경로 = os.path.join(뿌리, 대상)
    s = open(경로, encoding='utf-8').read()

    a = s.find(시작표)
    b = s.find(끝표)
    if a == -1 or b == -1:
        print('자동 갱신 자리 표시를 찾지 못했습니다.')
        return 1

    바뀐 = s[:a + len(시작표)] + '\n' + 새목록 + '\n        ' + s[b:]
    if 바뀐 == s:
        print('새 기사가 없습니다.')
        return 0

    open(경로, 'w', encoding='utf-8').write(바뀐)
    print('기사 %d건으로 갱신했습니다.' % min(len(항목), 개수))
    return 0


if __name__ == '__main__':
    sys.exit(main())

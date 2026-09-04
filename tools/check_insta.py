# -*- coding: utf-8 -*-
"""인스타 이름표가 쓸 수 있는 것인지 확인만 합니다. 아무것도 고치지 않습니다.

  깃허브 Actions 탭에서 "인스타 이름표 확인" 을 손으로 실행하면 돕니다.
  ★ 이름표 값은 절대 화면에 찍지 않습니다. 되는지 안 되는지와 게시물 정보만 보여줍니다.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

기준 = 'https://graph.instagram.com/v21.0/'


def 불러오기(토큰, 길, 항목):
    """인스타에 물어봅니다. 실패하면 (None, 사람이 읽을 수 있는 이유) 를 돌려줍니다."""
    항목 = dict(항목)
    항목['access_token'] = 토큰
    주소 = 기준 + 길 + '?' + urllib.parse.urlencode(항목)
    try:
        with urllib.request.urlopen(주소, timeout=25) as 응답:
            return json.loads(응답.read().decode('utf-8')), None
    except urllib.error.HTTPError as e:
        속 = e.read().decode('utf-8', 'replace')
        try:
            이유 = json.loads(속)['error'].get('message', 속[:200])
        except Exception:
            이유 = 속[:200]
        return None, '%d — %s' % (e.code, 이유)
    except Exception as e:
        return None, str(e)


def main():
    토큰 = os.environ.get('IG_ACCESS_TOKEN', '').strip()
    if not 토큰:
        print('금고에 IG_ACCESS_TOKEN 이 없습니다.')
        return 1
    print('이름표를 찾았습니다. (길이 %d글자 — 값은 보여드리지 않습니다)' % len(토큰))
    print()

    print('[1] 계정 확인')
    정보, 오류 = 불러오기(토큰, 'me', {'fields': 'id,username,account_type,media_count'})
    if 오류:
        print('    실패 :', 오류)
        print()
        print('이름표가 아직 안 됩니다. 위 메시지를 그대로 빵자에게 보여주세요.')
        return 1
    print('    아이디    :', 정보.get('username'))
    print('    계정 유형  :', 정보.get('account_type'))
    print('    게시물 수  :', 정보.get('media_count'))
    print()

    print('[2] 게시물 읽어오기 (최근 6개)')
    목록, 오류 = 불러오기(토큰, 'me/media', {
        'fields': 'id,caption,media_type,media_url,thumbnail_url,permalink,timestamp',
        'limit': '6',
    })
    if 오류:
        print('    실패 :', 오류)
        print()
        print('계정은 보이는데 게시물을 못 읽습니다. 권한(instagram_business_basic)을 확인해야 합니다.')
        return 1

    글들 = 목록.get('data', [])
    print('    받아온 개수 :', len(글들))
    for g in 글들:
        설명 = (g.get('caption') or '').replace(chr(10), ' ')
        print('    - %s | %s | 사진 %s | 설명 %d자'
              % (g.get('timestamp', '')[:10],
                 g.get('media_type'),
                 '있음' if (g.get('media_url') or g.get('thumbnail_url')) else '없음',
                 len(설명)))
    print()
    print('이름표가 잘 됩니다. 이대로 진행하면 됩니다.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

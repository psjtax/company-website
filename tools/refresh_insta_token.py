# -*- coding: utf-8 -*-
"""인스타 이름표가 죽기 전에 스스로 연장하고, 깃허브 금고에 새로 넣어 둡니다.

  인스타 이름표는 60일이면 만료됩니다. 만료 없음으로 만들 수 없습니다(메타 정책).

  수명을 묻는 창구가 따로 없고, 연장 요청은 물어보는 순간 새 이름표를 발급해
  버립니다. 그래서 발급일을 파일에 적어두고 날짜로 판단합니다.
  (그 파일에는 날짜만 들어갑니다. 비밀이 아닙니다)

  ★ 이름표 값은 어떤 경우에도 화면에 찍지 않습니다.
  ★ 연장에 실패해도 0 으로 끝냅니다. 게시물 갱신을 막으면 안 되기 때문입니다.
"""
import base64
import datetime
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

기준일 = 40                      # 60일짜리이므로 40일이 지나면 약 20일 남은 셈입니다
연장주소 = 'https://graph.instagram.com/refresh_access_token'

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
발급일파일 = os.path.join(뿌리, '.github', 'insta-token-issued.txt')


def 발급일읽기(경로):
    """파일에 적힌 날짜를 읽습니다. 없거나 망가졌으면 None 입니다."""
    try:
        글 = io.open(경로, encoding='utf-8').read()
    except Exception:
        return None
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', 글)
    if not m:
        return None
    try:
        return datetime.date(*(int(x) for x in m.groups()))
    except ValueError:
        return None


def 발급일쓰기(경로, 날짜):
    """날짜만 한 줄 적습니다."""
    os.makedirs(os.path.dirname(경로), exist_ok=True)
    io.open(경로, 'w', encoding='utf-8').write(날짜.isoformat() + chr(10))


def 연장필요한가(발급일, 오늘, 기준=기준일):
    return (오늘 - 발급일).days >= 기준


def 열어보기(주소):
    요청 = urllib.request.Request(주소, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(요청, timeout=25) as 응답:
        return json.loads(응답.read().decode('utf-8'))


def 연장하기(토큰, 부르기=None):
    """60일짜리 새 이름표를 받습니다. 실패하면 None 입니다."""
    try:
        난것 = (부르기 or 열어보기)(연장주소 + '?' + urllib.parse.urlencode(
            {'grant_type': 'ig_refresh_token', 'access_token': 토큰}))
    except Exception:
        return None
    새것 = (난것 or {}).get('access_token') or ''
    if not 새것:
        return None
    return 새것, int((난것 or {}).get('expires_in') or 0)


def 깃허브부르기(방법, 주소, 몸=None, 토큰=None):
    자료 = json.dumps(몸).encode('utf-8') if 몸 is not None else None
    요청 = urllib.request.Request(주소, data=자료, method=방법, headers={
        'Authorization': 'Bearer %s' % 토큰,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
        'User-Agent': 'psjtax-site',
    })
    with urllib.request.urlopen(요청, timeout=25) as 응답:
        속 = 응답.read().decode('utf-8').strip()
        return json.loads(속) if 속 else {}


def 금고에넣기(주인, 저장소, 이름, 값, 깃허브토큰, 부르기=None):
    """깃허브 금고에 값을 넣습니다. 저장소 공개키로 봉인해서 보냅니다."""
    부르기 = 부르기 or 깃허브부르기
    바탕 = 'https://api.github.com/repos/%s/%s/actions/secrets' % (주인, 저장소)
    try:
        from nacl import encoding, public
        열쇠 = 부르기('GET', 바탕 + '/public-key', 토큰=깃허브토큰)
        공개키 = public.PublicKey(열쇠['key'].encode('utf-8'), encoding.Base64Encoder)
        봉인 = public.SealedBox(공개키).encrypt(값.encode('utf-8'))
        부르기('PUT', 바탕 + '/' + 이름, 몸={
            'encrypted_value': base64.b64encode(봉인).decode('utf-8'),
            'key_id': 열쇠['key_id'],
        }, 토큰=깃허브토큰)
        return True
    except Exception:
        return False


def main():
    토큰 = os.environ.get('IG_ACCESS_TOKEN', '').strip()
    if not 토큰:
        print('인스타 이름표가 없습니다. 연장은 건너뜁니다.')
        return 0

    깃허브토큰 = os.environ.get('GITHUB_TOKEN_FOR_SECRETS', '').strip()
    저장소전체 = os.environ.get('GITHUB_REPOSITORY', '').strip()
    if not 깃허브토큰 or '/' not in 저장소전체:
        print('금고에 넣을 권한이 없습니다. 연장은 건너뜁니다.')
        return 0
    주인, 저장소 = 저장소전체.split('/', 1)

    오늘 = datetime.date.today()
    발급일 = 발급일읽기(발급일파일)
    if 발급일 is None:
        발급일쓰기(발급일파일, 오늘)
        print('발급일을 처음 적어 두었습니다. 이번에는 연장하지 않습니다.')
        return 0

    지난날 = (오늘 - 발급일).days
    if not 연장필요한가(발급일, 오늘):
        print('이름표를 받은 지 %d일 되었습니다. 아직 넉넉해서 연장하지 않습니다.' % 지난날)
        return 0

    print('이름표를 받은 지 %d일 되었습니다. 연장을 받아 옵니다.' % 지난날)
    난것 = 연장하기(토큰)
    if not 난것:
        print('이름표를 연장하지 못했습니다. 다음 번에 다시 해봅니다.')
        return 0
    새토큰, 남은초 = 난것

    if 금고에넣기(주인, 저장소, 'IG_ACCESS_TOKEN', 새토큰, 깃허브토큰):
        발급일쓰기(발급일파일, 오늘)
        print('이름표를 연장해서 금고에 새로 넣었습니다. (%d일 더)' % (남은초 // 86400))
    else:
        print('연장은 받았지만 금고에 넣지 못했습니다. 다음 번에 다시 해봅니다.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

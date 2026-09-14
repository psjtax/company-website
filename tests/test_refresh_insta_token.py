# -*- coding: utf-8 -*-
import datetime
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import refresh_insta_token as rt

날 = datetime.date


def test_발급일을_읽고_쓴다(tmp_path):
    경로 = str(tmp_path / 'issued.txt')
    assert rt.발급일읽기(경로) is None
    rt.발급일쓰기(경로, 날(2026, 9, 4))
    assert rt.발급일읽기(경로) == 날(2026, 9, 4)


def test_망가진_파일은_None(tmp_path):
    경로 = str(tmp_path / 'issued.txt')
    io.open(경로, 'w', encoding='utf-8').write('이건 날짜가 아님')
    assert rt.발급일읽기(경로) is None


def test_사십일_지나면_연장한다():
    assert rt.연장필요한가(날(2026, 9, 4), 날(2026, 10, 14)) is True   # 40일
    assert rt.연장필요한가(날(2026, 9, 4), 날(2026, 11, 1)) is True


def test_아직_이르면_연장하지_않는다():
    assert rt.연장필요한가(날(2026, 9, 4), 날(2026, 9, 14)) is False   # 10일
    assert rt.연장필요한가(날(2026, 9, 4), 날(2026, 10, 13)) is False  # 39일


def test_연장에_성공하면_새토큰을_돌려준다():
    def 가짜(주소):
        assert 'refresh_access_token' in 주소
        assert 'ig_refresh_token' in 주소
        return {'access_token': '새이름표', 'expires_in': 5184000}

    assert rt.연장하기('옛이름표', 부르기=가짜) == ('새이름표', 5184000)


def test_연장이_실패하면_None():
    def 터짐(주소):
        raise OSError('안 열림')

    assert rt.연장하기('옛이름표', 부르기=터짐) is None


def test_답이_이상하면_None():
    assert rt.연장하기('옛', 부르기=lambda u: {'error': {'message': '만료됨'}}) is None
    assert rt.연장하기('옛', 부르기=lambda u: {'access_token': ''}) is None


def test_금고에_넣을_때_값을_봉인한다():
    import base64
    from nacl import encoding, public
    쌍 = public.PrivateKey.generate()
    공개키 = 쌍.public_key.encode(encoding.Base64Encoder).decode()
    보낸것 = {}

    def 가짜(방법, 주소, 몸=None, 토큰=None):
        if 방법 == 'GET':
            return {'key': 공개키, 'key_id': '12345'}
        보낸것.update({'주소': 주소, '몸': 몸})
        return {}

    assert rt.금고에넣기('psjtax', 'company-website', 'IG_ACCESS_TOKEN',
                     '비밀값', '깃허브토큰', 부르기=가짜) is True
    assert 보낸것['주소'].endswith('/actions/secrets/IG_ACCESS_TOKEN')
    assert 보낸것['몸']['key_id'] == '12345'
    assert 보낸것['몸']['encrypted_value'] != '비밀값'
    열림 = public.SealedBox(쌍).decrypt(base64.b64decode(보낸것['몸']['encrypted_value']))
    assert 열림.decode() == '비밀값'


def test_금고에_못_넣으면_False():
    def 터짐(방법, 주소, 몸=None, 토큰=None):
        raise OSError('안 됨')

    assert rt.금고에넣기('a', 'b', 'C', 'd', 'e', 부르기=터짐) is False


def 판깔기(tmp_path, monkeypatch, 발급일=None):
    경로 = str(tmp_path / 'issued.txt')
    if 발급일:
        rt.발급일쓰기(경로, 발급일)
    monkeypatch.setattr(rt, '발급일파일', 경로)
    monkeypatch.setenv('IG_ACCESS_TOKEN', '가짜인스타토큰')
    monkeypatch.setenv('GITHUB_TOKEN_FOR_SECRETS', '가짜깃허브토큰')
    monkeypatch.setenv('GITHUB_REPOSITORY', 'psjtax/company-website')
    return 경로


def test_토큰이_없으면_조용히_넘어간다(tmp_path, monkeypatch, capsys):
    판깔기(tmp_path, monkeypatch, 날(2026, 1, 1))
    monkeypatch.delenv('IG_ACCESS_TOKEN', raising=False)
    assert rt.main() == 0
    assert '없습니다' in capsys.readouterr().out


def test_발급일_파일이_없으면_오늘로_적고_넘어간다(tmp_path, monkeypatch, capsys):
    경로 = 판깔기(tmp_path, monkeypatch)
    불렀나 = {'응': False}
    monkeypatch.setattr(rt, '연장하기',
                        lambda t, 부르기=None: 불렀나.update(응=True) or ('x', 1))
    assert rt.main() == 0
    assert 불렀나['응'] is False
    assert rt.발급일읽기(경로) == datetime.date.today()


def test_아직_이르면_아무것도_안_한다(tmp_path, monkeypatch, capsys):
    판깔기(tmp_path, monkeypatch, datetime.date.today() - datetime.timedelta(days=5))
    monkeypatch.setattr(rt, '연장하기', lambda t, 부르기=None: ('안돼', 1))
    assert rt.main() == 0
    assert '아직' in capsys.readouterr().out


def test_연장하면_발급일이_오늘로_바뀐다(tmp_path, monkeypatch):
    경로 = 판깔기(tmp_path, monkeypatch, datetime.date.today() - datetime.timedelta(days=45))
    monkeypatch.setattr(rt, '연장하기', lambda t, 부르기=None: ('새토큰', 5184000))
    monkeypatch.setattr(rt, '금고에넣기',
                        lambda 주인, 저장소, 이름, 값, 깃허브토큰, 부르기=None: True)
    assert rt.main() == 0
    assert rt.발급일읽기(경로) == datetime.date.today()


def test_금고에_못_넣으면_발급일을_안_바꾼다(tmp_path, monkeypatch, capsys):
    옛날 = datetime.date.today() - datetime.timedelta(days=45)
    경로 = 판깔기(tmp_path, monkeypatch, 옛날)
    monkeypatch.setattr(rt, '연장하기', lambda t, 부르기=None: ('새토큰', 5184000))
    monkeypatch.setattr(rt, '금고에넣기',
                        lambda 주인, 저장소, 이름, 값, 깃허브토큰, 부르기=None: False)
    assert rt.main() == 0
    assert rt.발급일읽기(경로) == 옛날          # 실패했으니 다음 번에 다시 시도해야 한다


def test_연장이_실패해도_0으로_끝난다(tmp_path, monkeypatch, capsys):
    판깔기(tmp_path, monkeypatch, datetime.date.today() - datetime.timedelta(days=45))
    monkeypatch.setattr(rt, '연장하기', lambda t, 부르기=None: None)
    assert rt.main() == 0
    assert '연장하지 못했습니다' in capsys.readouterr().out


def test_토큰은_화면에_안_찍힌다(tmp_path, monkeypatch, capsys):
    판깔기(tmp_path, monkeypatch, datetime.date.today() - datetime.timedelta(days=45))
    monkeypatch.setenv('IG_ACCESS_TOKEN', '아주비밀12345')
    monkeypatch.setenv('GITHUB_TOKEN_FOR_SECRETS', '깃허브비밀67890')
    monkeypatch.setattr(rt, '연장하기', lambda t, 부르기=None: ('새토큰abcde', 5184000))
    monkeypatch.setattr(rt, '금고에넣기',
                        lambda 주인, 저장소, 이름, 값, 깃허브토큰, 부르기=None: True)
    rt.main()
    나온말 = capsys.readouterr().out
    for 비밀 in ('아주비밀12345', '깃허브비밀67890', '새토큰abcde'):
        assert 비밀 not in 나온말

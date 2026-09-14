# -*- coding: utf-8 -*-
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import update_insta as ui


def 칸수(s):
    """카드 칸 수를 셉니다. class="nc" 와 class="nc nc-soon" 을 둘 다 셉니다."""
    import re as _re
    return len(_re.findall(r'class="nc[ "]', s))


def 준비중수(s):
    import re as _re
    return len(_re.findall(r'class="nc nc-soon"', s))


여기 = os.path.dirname(os.path.abspath(__file__))
NL = chr(10)


def 자료():
    with io.open(os.path.join(여기, 'fixtures', 'insta_media.json'), encoding='utf-8') as f:
        return json.load(f)


def test_전화번호_줄이_사라진다():
    원본 = 자료()['data'][0]['caption']
    assert '051-710-9685' in 원본          # 시험 자료에 정말 들어있는지 먼저 확인
    다듬 = ui.설명다듬기(원본)
    assert '051-710-9685' not in 다듬
    assert '05171' not in 다듬.replace('-', '').replace(' ', '')


def test_해시태그_줄이_사라진다():
    원본 = 자료()['data'][0]['caption']
    assert '#지급명세서' in 원본
    다듬 = ui.설명다듬기(원본)
    assert '#지급명세서' not in 다듬
    assert '#박성진세무회계사무소' not in 다듬


def test_본문은_남는다():
    다듬 = ui.설명다듬기(자료()['data'][0]['caption'])
    assert '간이지급명세서' in 다듬
    assert '2026년 9월 30일' in 다듬
    assert len(다듬) > 300


def test_문장_중간의_샵은_안_지운다():
    글 = '세금 신고는 #1 우선순위입니다.' + NL + '#세무사 #신고'
    다듬 = ui.설명다듬기(글)
    assert '#1 우선순위' in 다듬
    assert '#세무사' not in 다듬


def test_빈줄이_겹치지_않는다():
    글 = '첫째 줄' + NL * 4 + '둘째 줄'
    assert NL * 3 not in ui.설명다듬기(글)


def test_게시물을_정리한다():
    글들 = ui.게시물정리(자료())
    assert len(글들) == 1
    g = 글들[0]
    assert g['제목'] == '2026년 8월에 프리랜서나 일용직에게 대가를 지급하셨나요?'
    assert g['날짜'] == '2026. 09. 04'
    assert g['주소'] == 'https://www.instagram.com/p/Dc2cBIOkuHS/'
    assert len(g['사진']) == 8            # 여러 장짜리는 낱장을 쓴다
    assert '051-710-9685' not in g['설명']


def test_낱장이_없으면_대표사진_하나():
    자 = {'data': [{'id': '1', 'caption': '한 장짜리 글입니다.',
                   'media_type': 'IMAGE',
                   'media_url': 'https://example.com/a.jpg',
                   'permalink': 'https://www.instagram.com/p/AAA/',
                   'timestamp': '2026-09-01T00:00:00+0000'}]}
    g = ui.게시물정리(자)[0]
    assert g['사진'] == ['https://example.com/a.jpg']
    assert g['제목'] == '한 장짜리 글입니다.'


def test_설명이_없으면_기본제목():
    자 = {'data': [{'id': '2', 'media_type': 'IMAGE',
                   'media_url': 'https://example.com/b.jpg',
                   'permalink': 'https://www.instagram.com/p/BBB/',
                   'timestamp': '2026-09-01T00:00:00+0000'}]}
    g = ui.게시물정리(자)[0]
    assert g['제목'] == '인스타그램 게시물'
    assert g['설명'] == ''


def test_영상_항목은_섬네일을_이미지_항목은_media_url을_쓴다():
    영상 = {'id': '10', 'media_type': 'VIDEO',
          'media_url': 'https://example.com/v.mp4',
          'thumbnail_url': 'https://example.com/v_thumb.jpg',
          'permalink': 'https://www.instagram.com/p/VVV/',
          'timestamp': '2026-09-01T00:00:00+0000'}
    사진 = {'id': '11', 'media_type': 'IMAGE',
          'media_url': 'https://example.com/i.jpg',
          'thumbnail_url': 'https://example.com/i_thumb.jpg',
          'permalink': 'https://www.instagram.com/p/III/',
          'timestamp': '2026-09-01T00:00:00+0000'}
    g영상 = ui.게시물정리({'data': [영상]})[0]
    g사진 = ui.게시물정리({'data': [사진]})[0]
    assert g영상['사진'] == ['https://example.com/v_thumb.jpg']
    assert g사진['사진'] == ['https://example.com/i.jpg']
    assert not any('.mp4' in u for u in g영상['사진'])


def test_사진주소고르기_직접_확인():
    assert ui.사진주소고르기({'media_type': 'VIDEO', 'media_url': 'a.mp4',
                        'thumbnail_url': 'a.jpg'}) == 'a.jpg'
    assert ui.사진주소고르기({'media_type': 'IMAGE', 'media_url': 'a.jpg',
                        'thumbnail_url': 'a_t.jpg'}) == 'a.jpg'
    assert ui.사진주소고르기({'media_type': 'IMAGE'}) == ''


def test_캐러셀에서_영상은_섬네일_이미지는_media_url을_쓴다():
    자 = {'data': [{
        'id': '20', 'caption': '캐러셀 글', 'media_type': 'CAROUSEL_ALBUM',
        'permalink': 'https://www.instagram.com/p/CCC/',
        'timestamp': '2026-09-01T00:00:00+0000',
        'children': {'data': [
            {'media_type': 'IMAGE', 'media_url': 'https://example.com/c1.jpg',
             'thumbnail_url': 'https://example.com/c1_thumb.jpg'},
            {'media_type': 'VIDEO', 'media_url': 'https://example.com/c2.mp4',
             'thumbnail_url': 'https://example.com/c2_thumb.jpg'},
        ]},
    }]}
    g = ui.게시물정리(자)[0]
    assert g['사진'] == ['https://example.com/c1.jpg', 'https://example.com/c2_thumb.jpg']
    assert not any('.mp4' in u for u in g['사진'])


def test_아무_그림도_없는_캐러셀_자식은_건너뛴다():
    자 = {'data': [{
        'id': '21', 'caption': '글', 'media_type': 'CAROUSEL_ALBUM',
        'permalink': 'https://www.instagram.com/p/DDD/',
        'timestamp': '2026-09-01T00:00:00+0000',
        'children': {'data': [
            {'media_type': 'IMAGE', 'media_url': 'https://example.com/d1.jpg'},
            {'media_type': 'VIDEO'},
        ]},
    }]}
    g = ui.게시물정리(자)[0]
    assert g['사진'] == ['https://example.com/d1.jpg']


def test_날짜와_금액이_있는_줄은_안_지운다():
    글 = '2026년 05월 17일까지 109,685원 납부하세요'
    assert ui.설명다듬기(글) == 글


def test_다른_긴_숫자줄은_안_지운다():
    for 글 in ('신고기한 2026-09-30 까지입니다',
               '사업자등록번호 878-28-01274',
               '작년 매출 1,234,567,890원'):
        assert ui.설명다듬기(글) == 글


def test_띄어쓴_전화번호도_지운다():
    assert ui.설명다듬기('문의 051 710 9685') == ''
    assert ui.설명다듬기('문의 051-710-9685') == ''
    assert ui.설명다듬기('전화: 051.710.9685 입니다') == ''


def test_괄호_슬래시_가운데점_전각숫자_변형도_모두_지운다():
    """리뷰에서 살아남는 것으로 확인된 다섯 가지 변형이 모두 지워져야 한다."""
    변형들 = [
        '전화 051)710-9685 로 주세요',
        '(051)710-9685',
        '051 / 710 / 9685',
        '051·710·9685',
        '０５１-７１０-９６８５',
    ]
    for 줄 in 변형들:
        assert ui.설명다듬기(줄) == '', '지워지지 않음: %r' % (줄,)


def test_넓어진_전화꼴에도_안전한_여섯줄은_그대로_남는다():
    """전화번호 칸을 넓혀도 날짜·금액·사업자번호 같은 줄은 절대 지워지면 안 된다."""
    안전줄들 = [
        '2026년 05월 17일까지 109,685원 납부하세요',
        '신고기한 2026-09-30 까지입니다',
        '사업자등록번호 878-28-01274',
        '작년 매출 1,234,567,890원',
        '① 간이지급명세서 (거주자의 사업소득)',
        '출처: 국세청 (2026. 8. 25. 확인)',
    ]
    for 줄 in 안전줄들:
        assert ui.설명다듬기(줄) == 줄, '엉뚱하게 지워짐: %r' % (줄,)


def 보기글(설명='첫 문단' + NL + '둘째 문단'):
    return {'아이디': '1', '제목': '제목 "따옴표"', '설명': 설명,
            '날짜': '2026. 09. 04',
            '주소': 'https://www.instagram.com/p/AAA/', '사진': []}


def test_카드에_필요한_것이_다_들어간다():
    카드 = ui.카드만들기(보기글(), ['a.jpg', 'b.jpg'])
    assert 'class="nc"' in 카드
    assert 'href="https://www.instagram.com/p/AAA/"' in 카드
    assert '&quot;' in 카드                      # 제목의 따옴표가 안전하게 바뀐다
    assert 'data-img="a.jpg,b.jpg"' in 카드
    assert 'data-imgdir="insta"' in 카드
    assert 'data-link-label="인스타그램에서 보기"' in 카드
    assert '&#10;' in 카드                       # 문단 구분
    assert 'nc-date' in 카드 and '2026. 09. 04' in 카드


def test_카드_요약은_짧게_자른다():
    긴글 = '가' * 300
    카드 = ui.카드만들기(보기글(긴글), [])
    m = __import__('re').search(r'<span class="nc-sum">([^<]*)</span>', 카드)
    assert m is not None
    assert len(m.group(1)) <= 120


def test_준비중카드는_눌리지_않는다():
    카드 = ui.준비중카드()
    assert 'class="nc nc-soon"' in 카드
    assert '<a ' not in 카드
    assert 'href' not in 카드
    assert '준비 중입니다' in 카드


def test_여섯칸을_준비중으로_채운다():
    난것 = ui.여섯칸([ui.카드만들기(보기글(), [])])
    assert 칸수(난것) == 6
    assert 준비중수(난것) == 5


def test_여섯칸은_여섯개를_넘지_않는다():
    많이 = [ui.카드만들기(보기글(), []) for _ in range(9)]
    난것 = ui.여섯칸(많이)
    assert 칸수(난것) == 6
    assert 준비중수(난것) == 0


def test_표시자_사이를_갈아끼운다():
    s = 'A<!-- 시작 -->옛것<!-- 끝 -->B'
    난것 = ui.갈아끼우기(s, '<!-- 시작 -->', '<!-- 끝 -->', '새것', '  ')
    assert '옛것' not in 난것 and '새것' in 난것
    assert 난것.startswith('A') and 난것.endswith('B')


def test_표시자가_없으면_None():
    assert ui.갈아끼우기('아무것도 없음', '<!-- 시작 -->', '<!-- 끝 -->', '새것', '') is None


def test_표시자를_흉내낸_제목도_안전하다():
    글 = 보기글()
    글['제목'] = '<!-- 인스타 여기까지 -->'
    카드 = ui.카드만들기(글, [])
    assert '<!-- 인스타 여기까지 -->' not in 카드     # 이스케이프되어 표시자 노릇을 못 한다
    assert '&lt;!--' in 카드


def 빈페이지(줄수=0):
    안 = NL.join('<a class="nc" href="#">옛것</a>' for _ in range(줄수))
    return 'A<!-- 인스타 여기부터 -->' + 안 + '<!-- 인스타 여기까지 -->B'


def 판깔기(tmp_path, monkeypatch, 자료값, 줄수=0):
    대상 = tmp_path / 'index.html'
    대상.write_text(빈페이지(줄수), encoding='utf-8')
    monkeypatch.setattr(ui, '뿌리', str(tmp_path))
    monkeypatch.setattr(ui, '대상', 'index.html')
    monkeypatch.setattr(ui, '사진폴더', 'insta')
    monkeypatch.setattr(ui, '받아오기', lambda: 자료값)
    monkeypatch.setattr(ui, '사진저장', lambda u, f: 'zz.jpg')
    monkeypatch.setenv('IG_ACCESS_TOKEN', '시험용가짜토큰')
    return 대상


def test_토큰이_없으면_파일을_안_건드린다(tmp_path, monkeypatch):
    대상 = 판깔기(tmp_path, monkeypatch, 자료())
    monkeypatch.delenv('IG_ACCESS_TOKEN', raising=False)
    원래 = 대상.read_bytes()
    assert ui.main() == 1
    assert 대상.read_bytes() == 원래


def test_받아오기_실패하면_파일을_안_건드린다(tmp_path, monkeypatch):
    대상 = 판깔기(tmp_path, monkeypatch, 자료())

    def 터짐():
        raise OSError('인터넷 안 됨')

    monkeypatch.setattr(ui, '받아오기', 터짐)
    원래 = 대상.read_bytes()
    assert ui.main() == 1
    assert 대상.read_bytes() == 원래


def test_게시물이_없으면_파일을_안_건드린다(tmp_path, monkeypatch):
    대상 = 판깔기(tmp_path, monkeypatch, {'data': []}, 줄수=3)
    원래 = 대상.read_bytes()
    assert ui.main() == 1
    assert 대상.read_bytes() == 원래


def test_전체가_돌면_여섯칸이_찬다(tmp_path, monkeypatch, capsys):
    대상 = 판깔기(tmp_path, monkeypatch, 자료())
    assert ui.main() == 0
    난것 = 대상.read_text(encoding='utf-8')
    assert 칸수(난것) == 6
    assert 준비중수(난것) == 5
    assert '옛것' not in 난것
    assert 'data-img="zz.jpg' in 난것


def test_사진은_열두장까지만(tmp_path, monkeypatch):
    자 = 자료()
    자['data'][0]['children']['data'] = [
        {'media_url': 'https://example.com/i%02d.jpg' % n} for n in range(20)]
    대상 = 판깔기(tmp_path, monkeypatch, 자)
    monkeypatch.setattr(ui, '사진저장', lambda u, f: u.rsplit('/', 1)[-1])
    assert ui.main() == 0
    import re as _re
    m = _re.search(r'data-img="([^"]*)"', 대상.read_text(encoding='utf-8'))
    assert len(m.group(1).split(',')) == 12


def test_두번_돌리면_그대로다(tmp_path, monkeypatch, capsys):
    대상 = 판깔기(tmp_path, monkeypatch, 자료())
    assert ui.main() == 0
    한번째 = 대상.read_text(encoding='utf-8')
    assert ui.main() == 0
    assert 대상.read_text(encoding='utf-8') == 한번째
    assert '바뀐 것이 없습니다' in capsys.readouterr().out


def test_임시파일이_남지_않는다(tmp_path, monkeypatch):
    대상 = 판깔기(tmp_path, monkeypatch, 자료())
    assert ui.main() == 0
    남은것 = [f for f in os.listdir(str(tmp_path)) if f != 'index.html' and f != 'insta']
    assert 남은것 == []


def test_토큰은_화면에_안_찍힌다(tmp_path, monkeypatch, capsys):
    판깔기(tmp_path, monkeypatch, 자료())
    monkeypatch.setenv('IG_ACCESS_TOKEN', '아주비밀스러운값12345')
    ui.main()
    assert '아주비밀스러운값12345' not in capsys.readouterr().out


def test_탈없는말이_환경변수_토큰을_지운다(monkeypatch):
    monkeypatch.setenv('IG_ACCESS_TOKEN', '비밀토큰XYZ98765')
    말 = ui.탈없는말(Exception(
        'HTTP 400 for https://graph.instagram.com/v21.0/me/media?limit=6&access_token=비밀토큰XYZ98765'))
    assert '비밀토큰XYZ98765' not in 말
    assert '(이름표)' in 말


def test_탈없는말이_주소속_토큰도_지운다(monkeypatch):
    monkeypatch.delenv('IG_ACCESS_TOKEN', raising=False)
    말 = ui.탈없는말(Exception('열지 못함 access_token=AAABBBCCCDDD&limit=6 입니다'))
    assert 'AAABBBCCCDDD' not in 말
    assert '(이름표)' in 말


def test_받아오기가_실패해도_토큰이_화면에_안_나온다(tmp_path, monkeypatch, capsys):
    대상 = 판깔기(tmp_path, monkeypatch, 자료())
    monkeypatch.setenv('IG_ACCESS_TOKEN', '진짜비밀토큰98765')

    def 터짐():
        raise OSError('열지 못함: https://graph.instagram.com/v21.0/me/media'
                      '?limit=6&access_token=진짜비밀토큰98765')

    monkeypatch.setattr(ui, '받아오기', 터짐)
    원래 = 대상.read_bytes()
    assert ui.main() == 1
    assert 대상.read_bytes() == 원래
    assert '진짜비밀토큰98765' not in capsys.readouterr().out

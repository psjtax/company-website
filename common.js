/* ===========================================================
   모든 페이지가 함께 쓰는 기능
   · 스크롤하면 스르륵 나타나기
   · 좁은 화면용 햄버거 메뉴
   · 맨 위로 버튼
   =========================================================== */

/* 스크롤하면 스르륵 나타나기 */
var io = new IntersectionObserver(function(es){
  es.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('on'); io.unobserve(e.target); } });
},{ threshold:.1 });
document.querySelectorAll('.rv').forEach(function(el){ io.observe(el); });


/* ---------------------------------------------------------
   좁은 화면용 햄버거 메뉴
   --------------------------------------------------------- */
(function(){
  var btn = document.getElementById('menuBtn');
  var menu = document.getElementById('mMenu');
  if(!btn || !menu) return;

  function close(){
    menu.classList.remove('open');
    btn.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-label', '메뉴 열기');
  }
  btn.addEventListener('click', function(){
    var open = menu.classList.toggle('open');
    btn.classList.toggle('open', open);
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    btn.setAttribute('aria-label', open ? '메뉴 닫기' : '메뉴 열기');
  });
  /* 메뉴에서 항목을 고르면 닫힙니다 */
  menu.querySelectorAll('a').forEach(function(a){ a.addEventListener('click', close); });
  /* 화면이 넓어지면 닫습니다 */
  window.addEventListener('resize', function(){ if(window.innerWidth > 1024) close(); });
})();


/* ---------------------------------------------------------
   맨 위로 버튼
   조금 내려가면 나타나고, 누르면 부드럽게 맨 위로 올라갑니다
   --------------------------------------------------------- */
(function(){
  var btn = document.getElementById('topFab');
  if(!btn) return;
  function refresh(){
    btn.classList.toggle('show', window.scrollY > 400);
  }
  btn.addEventListener('click', function(e){
    e.preventDefault();
    window.scrollTo({ top:0, behavior:'smooth' });
  });
  window.addEventListener('scroll', refresh, { passive:true });
  refresh();
})();


/* ---------------------------------------------------------
   카카오톡 채널
   컴퓨터에서는 채널 홈으로, 휴대폰에서는 바로 대화창으로 갑니다
   --------------------------------------------------------- */
(function(){
  var 카톡 = document.querySelector('.kakao-fab');
  if(!카톡 || !카톡.dataset.mo) return;

  function 고르기(){
    var 휴대폰 = window.matchMedia('(max-width:900px), (pointer:coarse)').matches;
    카톡.href = 휴대폰 ? 카톡.dataset.mo : 카톡.dataset.pc;
  }
  고르기();
  window.addEventListener('resize', 고르기);
})();


/* 아직 주소(#)를 안 넣은 버튼은 눌러도 페이지가 움직이지 않게 막습니다.
   href 에 실제 주소를 넣으면 이 막음은 자동으로 풀립니다. */
document.querySelectorAll('.fab a').forEach(function(a){
  a.addEventListener('click', function(e){
    if(this.getAttribute('href') === '#') e.preventDefault();
  });
});

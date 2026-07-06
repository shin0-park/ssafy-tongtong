# 1. Django 서버 설정하는 법
### DJANGO_SECRET_KEY
- 내부 보안 기능에 사용하는 서버 비밀 문자열
- 없으면 `SECURITY WARNING: keep the secret key used in production secret!`이라는 오류가 난다.
- `startproject`로 프로젝트를 생성할 때 settings.py에 
  ```
  SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-..."
  )
  ```
  형태로 임시 개발용 secret key가 자동으로 생성된다.
- `.env`에 `DJANGO_SECRET_KEY`를 설정하여 사용한다.
- 
- 사용처
  - 쿠키 서명
  - CSRF 토큰 관련 보안 처리
  - password reset token 같은 서명 기반 토큰
  - session 데이터 보호
  - 일부 암호학적 signing 기능
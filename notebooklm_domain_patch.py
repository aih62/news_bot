"""
NotebookLM 도메인 이전(notebooklm.google.com -> notebook.google.com) 대응 패치.

배경
----
구글이 NotebookLM을 notebook.google.com 으로 이전했습니다. 그 결과:

  1. 옛 도메인(notebooklm.google.com)은 어떤 쿠키를 보내도 더 이상 인증되지 않고
     accounts.google.com 로그인 화면으로 리다이렉트됩니다. 브라우저로 방문해도
     옛 도메인용 OSID를 새로 발급해주지 않습니다.
  2. 세션 쿠키(OSID)는 새 도메인에 발급되는데, notebooklm-py 는 허용 쿠키 도메인
     목록에 새 도메인이 없어서 이 쿠키를 버리고 낡은 값을 전송합니다.

notebooklm-py 는 설치본 0.3.4 는 물론 최신 0.7.3 에서도 새 도메인을 모릅니다.
0.7.3 의 NOTEBOOKLM_BASE_URL 환경변수도 허용 호스트가 옛 도메인과 엔터프라이즈
도메인으로 제한되어 있어 우회할 수 없습니다.

그래서 라이브러리를 건드리지 않고 두 지점만 런타임에 교정합니다.

  A. HTTP 계층 - 옛 도메인으로 나가는 요청을 새 도메인으로 다시 씁니다.
  B. 쿠키 추출 - 새 도메인 쿠키를 라이브러리가 인정하는 도메인 이름으로 옮겨 심어
     올바른 OSID 가 전송되게 합니다.

둘 중 하나만으로는 인증되지 않습니다. 반드시 함께 적용되어야 합니다.

라이브러리가 새 도메인을 정식 지원하면 이 파일과 각 진입점의 apply() 호출을
지우면 됩니다.

사용법:
    import notebooklm_domain_patch
    notebooklm_domain_patch.apply()   # notebooklm 사용 전에 한 번만 호출
"""

from typing import Any

import httpx

import notebooklm.auth as _nblm_auth

LEGACY_HOST = "notebooklm.google.com"
NEW_HOST = "notebook.google.com"

_applied = False


def normalize_storage_state(storage_state: dict[str, Any]) -> dict[str, Any]:
    """새 도메인 쿠키를 라이브러리가 읽는 도메인 이름으로도 넣어줍니다.

    라이브러리는 같은 이름의 쿠키가 여러 도메인에 있으면 (.google.com 을 제외하고)
    먼저 나온 것을 씁니다. 따라서 새 도메인 쿠키의 사본을 목록 맨 앞에 두고,
    이름이 겹치는 낡은 옛 도메인 쿠키는 제거합니다.
    """
    cookies = storage_state.get("cookies", [])

    new_host_names = {
        c.get("name") for c in cookies if c.get("domain", "").lstrip(".") == NEW_HOST
    }
    if not new_host_names:
        # 새 도메인 쿠키가 없으면 손댈 것이 없습니다.
        return storage_state

    relabeled = [
        {**c, "domain": ("." if c.get("domain", "").startswith(".") else "") + LEGACY_HOST}
        for c in cookies
        if c.get("domain", "").lstrip(".") == NEW_HOST
    ]
    rest = [
        c
        for c in cookies
        if not (
            c.get("domain", "").lstrip(".") == LEGACY_HOST and c.get("name") in new_host_names
        )
    ]

    return {**storage_state, "cookies": relabeled + rest}


def _rewrite_host(request: httpx.Request) -> None:
    """요청 대상이 옛 도메인이면 새 도메인으로 바꿉니다."""
    if request.url.host != LEGACY_HOST:
        return

    request.url = request.url.copy_with(host=NEW_HOST)
    request.headers["Host"] = NEW_HOST
    for header in ("Origin", "Referer"):
        value = request.headers.get(header)
        if value and LEGACY_HOST in value:
            request.headers[header] = value.replace(LEGACY_HOST, NEW_HOST)


def apply() -> None:
    """패치를 적용합니다. 여러 번 호출해도 한 번만 적용됩니다."""
    global _applied
    if _applied:
        return
    _applied = True

    # A. HTTP 계층: 옛 도메인 -> 새 도메인
    original_async_send = httpx.AsyncClient.send
    original_sync_send = httpx.Client.send

    async def patched_async_send(self, request, **kwargs):
        _rewrite_host(request)
        return await original_async_send(self, request, **kwargs)

    def patched_sync_send(self, request, **kwargs):
        _rewrite_host(request)
        return original_sync_send(self, request, **kwargs)

    httpx.AsyncClient.send = patched_async_send
    httpx.Client.send = patched_sync_send

    # B. 쿠키 추출: 새 도메인의 OSID 가 선택되도록 정규화 후 넘깁니다.
    #    auth.py 내부(load_auth_from_storage)에서 모듈 전역으로 호출하므로
    #    여기서 교체하면 파일 경로와 NOTEBOOKLM_AUTH_JSON 경로 모두 적용됩니다.
    original_extract = _nblm_auth.extract_cookies_from_storage

    def patched_extract(storage_state: dict[str, Any]) -> dict[str, str]:
        return original_extract(normalize_storage_state(storage_state))

    _nblm_auth.extract_cookies_from_storage = patched_extract

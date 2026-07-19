# -*- coding: utf-8 -*-
"""
우리집 영어 단어 미션 — 학습 결과 카카오톡 발송
  --daily     오늘 아이들의 학습 현황 요약
  --weekly    이번 주 리포트 요약
  --auto      매일 발송 + 일요일이면 주간 리포트도 발송 (기본)
  --remind    오늘 미완료인 아이가 있으면 리마인드 발송 (저녁 스케줄용)
  --complete <k1|k2>   해당 아이의 '오늘 완료' 즉시 알림 (env COMPLETE_KID 도 가능)
  --dry       실제 전송 없이 메시지만 출력

카카오 토큰 갱신/전송은 기존 kakao_summary.py 로직을 재사용합니다.
"""
import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

load_dotenv(override=True)
from kakao_summary import refresh_kakao_token  # 토큰 갱신(+회전 시 Secret 저장) 재사용

KST = timezone(timedelta(hours=9))
API = "https://ajken.mycafe24.com/voca/api.php"
API_KEY = os.getenv("VOCA_API_KEY") or "fam-ajken-7Kq2"
REPORT_URL = "https://ajken.mycafe24.com/voca/report.html"

START = datetime(2026, 7, 18, tzinfo=KST)  # 프로그램 시작 (매일 1레슨)
LP = 200  # 레슨 수 (1000단어/5)

PROFILES = {
    "k2": {"name": "첫째 (중2)", "emoji": "🧑‍🎓", "level": "고등", "allowance": 3000},
    "k1": {"name": "둘째 (초3)", "emoji": "🧒", "level": "초6", "allowance": 2000},
}
ORDER = ["k2", "k1"]
NL = chr(10)


def fetch_state():
    r = requests.get(API, params={"k": API_KEY}, timeout=20)
    r.raise_for_status()
    try:
        return r.json() or {}
    except Exception:
        return {}


def week_lesson(now=None):
    now = now or datetime.now(KST)
    diff = (now.date() - START.date()).days
    if diff < 0:
        diff = 0
    lesson = diff % LP  # 매일 1레슨(주말 포함)
    return lesson, lesson // 5, lesson % 5, now


def _asdict(x):
    # PHP가 순차키 dict를 JSON 리스트로 저장하는 경우까지 흡수
    if isinstance(x, dict):
        return x
    if isinstance(x, list):
        return {str(i): v for i, v in enumerate(x)}
    return {}


def _learned(k):
    return _asdict(k.get("learned"))


def lesson_done(k, l):
    a = _learned(k).get(str(l))
    return bool(a) and len(a) == 5 and all(a)


def today_count(k, lesson):
    a = _learned(k).get(str(lesson)) or []
    return sum(1 for x in a if x)


def total_words(k):
    return sum(sum(1 for x in a if x) for a in _learned(k).values())


def days_in_week(k, w):
    return sum(1 for l in range(w * 5, w * 5 + 5) if lesson_done(k, l))


def words_in_week(k, w):
    n = 0
    for l in range(w * 5, w * 5 + 5):
        a = _learned(k).get(str(l))
        if a:
            n += sum(1 for x in a if x)
    return n


def streak(k, lesson):
    s = 0
    x = lesson if lesson_done(k, lesson) else lesson - 1
    while x >= 0:
        if lesson_done(k, x % LP):
            s += 1
        else:
            break
        x -= 1
    return s


def name_of(state, kid):
    return (state.get(kid) or {}).get("name") or PROFILES[kid]["name"]


def fmt_daily(state):
    lesson, week, dow, now = week_lesson()
    wd = "월화수목금토일"[now.weekday()]
    lines = [f"📚 오늘의 학습  {now.month}월 {now.day}일({wd})", ""]
    for kid in ORDER:
        k = state.get(kid) or {}
        p = PROFILES[kid]
        tc = today_count(k, lesson)
        status = "완료 ✅" if tc == 5 else (f"{tc}/5 진행 중" if tc > 0 else "아직 안 함 ⬜")
        lines.append(f"{p['emoji']} {name_of(state, kid)}")
        lines.append(f"  오늘 {status} · 연속 {streak(k, lesson)}일🔥 · 이번주 {days_in_week(k, week)}/5일")
    lines.append("")
    lines.append("👉 리포트에서 자세히 보기")
    return NL.join(lines)


def fmt_weekly(state):
    lesson, week, dow, now = week_lesson()
    mon = START + timedelta(days=week * 5)
    fri = mon + timedelta(days=4)
    lines = [f"📊 주간 리포트  {week + 1}주차 ({mon.month}/{mon.day}~{fri.month}/{fri.day})", ""]
    for kid in ORDER:
        k = state.get(kid) or {}
        p = PROFILES[kid]
        dw = days_in_week(k, week)
        ww = words_in_week(k, week)
        tests = _asdict(k.get("tests"))
        test = tests.get(str(week))
        testpass = isinstance(test, (int, float)) and test >= 70
        claimed = _asdict(k.get("claimed")).get(str(week))
        allowance = k.get("allowance") or p["allowance"]
        test_txt = (f"{int(test)}점 " + ("✅" if testpass else "❌")) if test is not None else "미응시"
        if claimed:
            mission = "미션 완료·용돈 지급 ✅"
        elif dw >= 4 and testpass:
            mission = f"미션 달성·용돈 ₩{allowance:,} 대기 🎁"
        else:
            mission = "미션 미완료"
        lines.append(f"{p['emoji']} {name_of(state, kid)}")
        lines.append(f"  학습 {dw}/5일 · {ww}단어 · 테스트 {test_txt}")
        lines.append(f"  {mission} · 누적 {total_words(k):,}단어")
        hard = list((k.get("hard") or {}).values())
        if hard:
            hw = ", ".join(h.get("en", "") for h in hard[:6] if h.get("en"))
            if hw:
                lines.append(f"  📌 복습 필요: {hw}")
        lines.append("")
    return NL.join(lines).strip()


def fmt_complete(state, kid):
    lesson, week, dow, now = week_lesson()
    k = state.get(kid) or {}
    p = PROFILES[kid]
    lines = [
        "🎉 오늘 학습 완료!",
        "",
        f"{p['emoji']} {name_of(state, kid)} 님이 오늘의 단어 5개를 모두 외웠어요.",
        f"연속 {streak(k, lesson)}일째 🔥 · 이번주 {days_in_week(k, week)}/5일",
    ]
    return NL.join(lines)


def fmt_remind(state):
    lesson, week, dow, now = week_lesson()
    pending = [(kid, state.get(kid) or {}) for kid in ORDER if today_count(state.get(kid) or {}, lesson) < 5]
    if not pending:
        return None
    lines = ["⏰ 오늘 학습 리마인드", ""]
    for kid, k in pending:
        p = PROFILES[kid]
        lines.append(f"{p['emoji']} {name_of(state, kid)} — 오늘 {today_count(k, lesson)}/5, 아직 미완료")
    lines.append("")
    lines.append("자기 전에 5개만 외우면 미션 성공! 📚")
    return NL.join(lines)


def send(message):
    tokens = refresh_kakao_token()
    if not tokens:
        kj = os.getenv("KAKAO_TOKEN_JSON")
        if not kj:
            print("KAKAO_TOKEN_JSON 없음 - 전송 불가")
            return False
        tokens = json.loads(kj)
    access_token = tokens.get("access_token")
    template = {
        "object_type": "text",
        "text": message,
        "link": {"web_url": REPORT_URL, "mobile_web_url": REPORT_URL},
        "button_title": "리포트 보기",
    }
    res = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template)},
        timeout=20,
    )
    if res.status_code == 200:
        print("카카오톡 전송 성공!")
        return True
    print(f"전송 실패: {res.status_code}, {res.text[:200]}")
    return False


def main():
    args = sys.argv
    dry = "--dry" in args
    state = fetch_state()
    now = datetime.now(KST)

    # 완료 즉시 알림
    if "--complete" in args:
        kid = os.getenv("COMPLETE_KID")
        i = args.index("--complete")
        if i + 1 < len(args) and not args[i + 1].startswith("--"):
            kid = args[i + 1]
        if kid not in ("k1", "k2"):
            print(f"잘못된 kid: {kid}")
            sys.exit(1)
        msg = fmt_complete(state, kid)
        print(msg)
        sys.exit(0 if (dry or send(msg)) else 1)

    # 미완료 리마인드
    if "--remind" in args:
        msg = fmt_remind(state)
        if not msg:
            print("모두 완료 - 리마인드 없음")
            sys.exit(0)
        print(msg)
        sys.exit(0 if (dry or send(msg)) else 1)

    # 매일 / 주간
    mode = "auto"
    if "--daily" in args:
        mode = "daily"
    elif "--weekly" in args:
        mode = "weekly"

    ok = True
    if mode in ("daily", "auto"):
        msg = fmt_daily(state)
        print(msg)
        if not dry:
            ok &= send(msg)
    if mode == "weekly" or (mode == "auto" and now.weekday() == 6):
        msg = fmt_weekly(state)
        print(msg)
        if not dry:
            ok &= send(msg)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

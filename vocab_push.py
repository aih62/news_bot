"""아이 아이폰으로 웹 푸시 알림 보내기.

사용법:
  --start    오후 4시  학습 시작 알림 (오늘 아직 다 못했을 때만)
  --remind   저녁 8시  미완료 리마인드 (오늘 아직 다 못했을 때만)
  --mission  주말      테스트/용돈 미션 알림
  --test     지금 바로 테스트 알림 (수동 확인용)

진도 계산은 vocab_report_kakao.py 의 것을 그대로 재사용한다(카카오 리포트와 숫자가 어긋나지 않도록).
구독 정보는 서버(push.php)에 있고, VAPID 비밀키는 여기(GitHub Secret)에만 있다.
"""
import os
import sys
import json
import argparse
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pywebpush import webpush, WebPushException

# 날짜/진도 계산은 카카오 리포트와 동일한 로직을 쓴다
from vocab_report_kakao import (
    KST, PROFILES, ORDER, fetch_state, week_lesson,
    today_count, days_in_week, streak, _asdict, name_of,
)

PUSH_API = "https://ajken.mycafe24.com/voca/push.php"
APP_URL = "https://ajken.mycafe24.com/voca/"

ADMIN_TOKEN = os.getenv("VOCA_PUSH_ADMIN")
VAPID_PRIVATE = os.getenv("VAPID_PRIVATE_KEY")
VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:ais@kisa.or.kr")


def get_subscriptions():
    r = requests.get(PUSH_API, params={"a": ADMIN_TOKEN, "list": 1}, timeout=20)
    r.raise_for_status()
    return (r.json() or {}).get("subscriptions", [])


def prune(endpoints):
    """애플이 죽었다고 응답한 구독을 서버에서 지운다."""
    if not endpoints:
        return
    try:
        r = requests.post(
            PUSH_API, params={"a": ADMIN_TOKEN},
            json={"action": "prune", "endpoints": endpoints}, timeout=20,
        )
        print(f"  만료 구독 정리: {r.json()}")
    except Exception as e:
        print(f"  구독 정리 실패: {e}")


def send_one(sub, payload):
    webpush(
        subscription_info={
            "endpoint": sub["endpoint"],
            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
        },
        data=json.dumps(payload, ensure_ascii=False),
        vapid_private_key=VAPID_PRIVATE,
        vapid_claims={"sub": VAPID_SUBJECT},
        ttl=3600,
    )


def deliver(messages, dry_run=False):
    """messages: {kid: {title, body, tag}} — 해당 아이의 기기에만 보낸다."""
    if not messages:
        print("보낼 알림 없음")
        return 0

    for kid, m in messages.items():
        print(f"[{kid}] {m['title']} — {m['body']}")
    if dry_run:
        print("(dry-run: 실제 발송 안 함)")
        return 0

    if not ADMIN_TOKEN or not VAPID_PRIVATE:
        print("VOCA_PUSH_ADMIN / VAPID_PRIVATE_KEY 가 설정되지 않았습니다", file=sys.stderr)
        return 1

    subs = get_subscriptions()
    print(f"등록된 기기 {len(subs)}대")

    sent = failed = 0
    dead = []
    for sub in subs:
        msg = messages.get(sub.get("kid"))
        if not msg:
            continue
        payload = dict(msg)
        payload["url"] = APP_URL
        try:
            send_one(sub, payload)
            sent += 1
            print(f"  보냄 -> {sub.get('kid')} ({sub['endpoint'][:45]}…)")
        except WebPushException as e:
            code = getattr(e.response, "status_code", None)
            if code in (404, 410):          # 구독이 만료됨(앱 삭제 등)
                dead.append(sub["endpoint"])
                print(f"  만료 -> {sub.get('kid')} (구독 삭제 예정)")
            else:
                failed += 1
                print(f"  실패 -> {sub.get('kid')}: {code} {e}")
        except Exception as e:
            failed += 1
            print(f"  실패 -> {sub.get('kid')}: {e}")

    prune(dead)
    print(f"결과: 성공 {sent} · 실패 {failed} · 만료 {len(dead)}")
    return 1 if failed else 0


def build(mode):
    """모드별로 아이마다 보낼 메시지를 만든다. 보낼 게 없으면 그 아이는 뺀다."""
    state = fetch_state()
    lesson, week, dow, now = week_lesson()
    msgs = {}

    for kid in ORDER:
        k = state.get(kid) or {}
        if not k:
            continue
        name = name_of(state, kid)
        done = today_count(k, lesson)      # 오늘 외운 단어 수 (0~5)
        left = 5 - done
        st = streak(k, lesson)

        if mode in ("start", "remind"):
            if left <= 0:
                continue                   # 오늘 다 했으면 방해하지 않는다
            if mode == "start":
                title = "오늘의 영어 단어 📚"
                body = (f"단어 5개가 기다리고 있어요!" if done == 0
                        else f"{left}개만 더 하면 오늘 끝이에요!")
                if st >= 3:
                    body += f" (연속 {st}일🔥)"
            else:
                title = "오늘 미션 아직 남았어요 ⏰"
                body = (f"자기 전에 단어 5개 어때요?" if done == 0
                        else f"{left}개만 더 하면 오늘 완료예요!")
                if st >= 3:
                    body += f" 연속 {st}일 이어가요🔥"
            msgs[kid] = {"title": title, "body": body, "tag": f"voca-{mode}"}

        elif mode == "mission":
            tests = _asdict(k.get("tests"))
            claimed = _asdict(k.get("claimed"))
            score = tests.get(str(week))
            passed = isinstance(score, (int, float)) and score >= 70
            dw = days_in_week(k, week)
            allowance = k.get("allowance") or PROFILES[kid]["allowance"]

            if dw >= 4 and passed and not claimed.get(str(week)):
                msgs[kid] = {
                    "title": "용돈 미션 완료! 🎉",
                    "body": f"이번 주 미션을 다 했어요. 용돈 {allowance:,}원 받기를 눌러주세요!",
                    "tag": "voca-mission",
                }
            elif score is None:
                need = max(0, 4 - dw)
                body = ("주말 테스트를 보면 용돈 미션이 끝나요!" if need == 0
                        else f"테스트까지 보면 완료! (학습 {dw}/5일)")
                msgs[kid] = {"title": "주말 테스트 볼까요? 📝", "body": body, "tag": "voca-mission"}
            elif not passed:
                msgs[kid] = {
                    "title": "테스트 다시 볼 수 있어요 📝",
                    "body": f"이번 주 {int(score)}점이에요. 70점 넘으면 용돈 미션 완료!",
                    "tag": "voca-mission",
                }
            elif dw < 4:
                # 테스트는 통과했는데 학습일이 모자란 경우. 이때 알려주지 않으면
                # 용돈을 받을 수 있는데도 아무 안내 없이 주가 끝나버린다.
                need = 4 - dw
                msgs[kid] = {
                    "title": "용돈까지 한 걸음! 🎁",
                    "body": f"테스트는 통과했어요. {need}일만 더 학습하면 용돈 {allowance:,}원!",
                    "tag": "voca-mission",
                }

        elif mode == "test":
            msgs[kid] = {
                "title": "알림 테스트 🔔",
                "body": f"{name} 알림이 잘 오고 있어요! (오늘 {done}/5)",
                "tag": "voca-test",
            }

    return msgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", action="store_true", help="오후 4시 학습 시작 알림")
    ap.add_argument("--remind", action="store_true", help="저녁 8시 미완료 리마인드")
    ap.add_argument("--mission", action="store_true", help="주말 테스트/용돈 미션 알림")
    ap.add_argument("--test", action="store_true", help="지금 바로 테스트 알림")
    ap.add_argument("--dry-run", action="store_true", help="실제 발송 없이 내용만 확인")
    a = ap.parse_args()

    mode = ("start" if a.start else "remind" if a.remind
            else "mission" if a.mission else "test" if a.test else None)
    if not mode:
        ap.error("모드를 지정하세요 (--start / --remind / --mission / --test)")

    print(f"모드: {mode}")
    sys.exit(deliver(build(mode), dry_run=a.dry_run))


if __name__ == "__main__":
    main()

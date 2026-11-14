#!/usr/bin/env python3
"""Select official film leads conservatively without guessing popularity from titles."""
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
DISCOVERY = ROOT / "data" / "official_film_discovery.json"
SCHEDULE = ROOT / "data" / "official_schedule.json"
EVIDENCE = ROOT / "data" / "official_film_editorial_evidence.json"
OUTPUT = ROOT / "data" / "official_film_selection.json"
JST = dt.timezone(dt.timedelta(hours=9))
HORIZON = 90
MAX_SOURCE_AGE = 2
ALLOWED_IMPORTANCE = {"major", "discovery"}
ALLOWED_BASIS = {
    "official_franchise", "official_cast", "official_adaptation",
    "official_cultural_subject", "official_award", "official_public_interest",
}


def normalize_title(value):
    return re.sub(r"[\\s　『』「」【】()（）・:：]|^(?:映画|劇場版)", "", value or "").lower().replace("公開", "")


def parse_day(value):
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def source_is_fresh(generated_at, today):
    generated = parse_day(str(generated_at)[:10])
    return generated is not None and today - dt.timedelta(days=MAX_SOURCE_AGE) <= generated <= today


def manual_keys(schedule):
    return {
        (normalize_title(event.get("name")), event.get("date"))
        for event in schedule.get("events", [])
        if isinstance(event, dict)
    }


def evaluate(item, reports, manual, today):
    reasons = []
    date = parse_day(item.get("date"))
    page = item.get("source_page_url") or item.get("official_url")
    report = next((x for x in reports if x.get("url") == page), None)
    if date is None:
        reasons.append("公式公開日がISO日付として確認できない")
    elif not today <= date <= today + dt.timedelta(days=HORIZON):
        reasons.append("公式公開日が保守的な90日範囲外")
    if item.get("category") != "映画":
        reasons.append("映画カテゴリではない")
    if item.get("status") != "要確認" or item.get("publishable") is not False:
        reasons.append("未確認候補としての安全な状態ではない")
    if item.get("verification", {}).get("status") != "unverified":
        reasons.append("検証状態がunverifiedではない")
    if not page or urlsplit(page).scheme != "https":
        reasons.append("HTTPSの公式ソースURLがない")
    if report is None or report.get("status") != "ok":
        reasons.append("対応する公式ソース取得が成功していない")
    if not source_is_fresh(item.get("_generated_at"), today):
        reasons.append("候補データが古い、未来日、または生成日時不明")
    if item.get("source_type") not in {"東宝公式映画公開予定", "ワーナー・ブラザース公式映画公開予定"}:
        reasons.append("日本国内の配給会社公式公開予定として確認できない")
    if item.get("verification", {}).get("japan_theatrical_release_date") != "official_lineup_candidate":
        reasons.append("日本国内劇場公開日の公式根拠が不足")
    if date is not None and (normalize_title(item.get("name")), item.get("date")) in manual:
        reasons.append("既存の公式予定に重複")
    importance = item.get("verification", {}).get("editorial_importance")
    if not isinstance(importance, dict):
        importance = {}
    decision = importance.get("decision")
    basis = importance.get("basis")
    if decision not in ALLOWED_IMPORTANCE:
        reasons.append("主要作品／意外な発見の判定が明示されていない")
    if not isinstance(basis, list) or not basis or any(x not in ALLOWED_BASIS for x in basis):
        reasons.append("重要度の公式根拠が許可された形式で記録されていない")
    evidence_url = importance.get("evidence_url")
    if not isinstance(evidence_url, str) or urlsplit(evidence_url).scheme != "https":
        reasons.append("重要度根拠の公式URLがない")
    if not source_is_fresh(importance.get("evidence_checked_on"), today):
        reasons.append("重要度根拠の確認日が古い、未来日、または不明")
    review_status = importance.get("review_status")
    if review_status != "approved":
        reasons.append("編集上の承認がない")
    if reasons:
        return "保留", False, reasons
    return ("主要作品" if decision == "major" else "意外な発見"), True, []


def select(discovery, schedule, today=None, evidence=None):
    today = today or dt.datetime.now(JST).date()
    reports = discovery.get("source_reports", [])
    manual = manual_keys(schedule)
    evidence = evidence or {}
    evidence_by_key = {(normalize_title(x.get("name")), x.get("date")): x.get("editorial_importance")
                       for x in evidence.get("items", []) if isinstance(x, dict)}
    generated_at = discovery.get("generated_at")
    selected = []
    for raw in discovery.get("items", []):
        item = dict(raw)
        key = (normalize_title(item.get("name")), item.get("date"))
        if key in evidence_by_key:
            item.setdefault("verification", {})["editorial_importance"] = evidence_by_key[key]
        item["_generated_at"] = generated_at
        label, eligible, reasons = evaluate(item, reports, manual, today)
        item.pop("_generated_at", None)
        item["selection"] = {
            "status": label,
            "publishable": eligible,
            "reasons": reasons,
            "basis": item.get("verification", {}).get("editorial_importance"),
        }
        selected.append(item)
    selected.sort(key=lambda x: (x.get("date", ""), x.get("name", "")))
    return {
        "data_kind": "conservative_official_film_selection",
        "generated_at": dt.datetime.now(JST).isoformat(timespec="seconds"),
        "policy": "題名の知名度を推定せず、国内公式公開日・鮮度・重複・明示的な重要度根拠・編集承認が揃うまで掲載しない。",
        "items": selected,
    }


def main():
    discovery = json.loads(DISCOVERY.read_text(encoding="utf-8"))
    schedule = json.loads(SCHEDULE.read_text(encoding="utf-8")) if SCHEDULE.exists() else {}
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8")) if EVIDENCE.exists() else {}
    result = select(discovery, schedule, evidence=evidence)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    publishable = sum(x["selection"]["publishable"] for x in result["items"])
    print(f"Film selection: {publishable}/{len(result['items'])} publishable")


if __name__ == "__main__":
    main()

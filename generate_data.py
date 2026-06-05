"""
generate_data.py
Creative Performance Analyzer — 합성 데이터 생성 스크립트

[데이터 설계 기준]
- 기본 CTR: 3.1% (MHI Growth Engine 2026, 뷰티 카테고리 Instagram Stories 기준)
- 기본 CVR: 2.5% (Triple Whale 2025, 뷰티/패션 CVR 2~3% 중간값)
- 소재 요소별 보정값은 업계 벤치마크 기반 설계 (각 항목 주석 참고)
- 소재 요소 간 독립 효과 가정 (상호작용 효과 미반영)
- 실제 캠페인 데이터 아님 — 시뮬레이션 목적

[실행 방법]
    python generate_data.py

[출력]
    data/synthetic_ads.csv
"""

import pandas as pd
import numpy as np
import os

# 재현 가능성을 위한 시드 고정
np.random.seed(42)

# ── 기본 설정 ──────────────────────────────────────────────────────────────
N_CAMPAIGNS = 50   # 캠페인 수
N_ADS       = 10   # 캠페인당 소재 수
N_ROWS      = N_CAMPAIGNS * N_ADS  # 총 500행

BASE_CTR = 3.1   # 기본 CTR (%)
BASE_CVR = 2.5   # 기본 CVR (%)
BASE_CPM = 15000 # 기본 CPM (원, 추정값)


# ── 소재 요소 정의 ────────────────────────────────────────────────────────
FORMAT_OPTIONS     = ['UGC', 'Brand', 'Carousel', 'Static']
COPY_OPTIONS       = ['Benefit', 'Emotional', 'Informational']
LENGTH_OPTIONS     = [15, 30, 60, 90]
CTA_OPTIONS        = ['Early', 'Middle', 'End']
PLATFORM_OPTIONS   = ['Feed', 'Stories', 'Reels']


# ── CTR 보정값 (업계 벤치마크 기반) ─────────────────────────────────────
# UGC: Billo.app 2026 — UGC 소재 최대 45% CTR 개선, 보수적 적용 (+0.8%p)
# 15초 이하: MHI Growth Engine 2026 — 15초 이하 영상 CTR 31% 우위 (+0.6%p)
# has_hook: Meta Creative Best Practice — 첫 3초 훅 포함 시 CTR 상승
# has_face: 업계 관찰 경향 (추정, 정량 출처 없음)

CTR_EFFECT_FORMAT = {
    'UGC':      +0.8,
    'Brand':     0.0,
    'Carousel': +0.3,
    'Static':   -0.4
}

CTR_EFFECT_LENGTH = {
    15:  +0.6,
    30:   0.0,
    60:  -0.3,
    90:  -0.6
}

CTR_EFFECT_PLATFORM = {
    'Reels':   +0.4,
    'Stories': +0.2,
    'Feed':     0.0
}

CTR_EFFECT_HOOK = +0.5   # Meta Creative Best Practice
CTR_EFFECT_FACE = +0.3   # 업계 관찰 경향 (추정)


# ── CVR 보정값 (업계 벤치마크 기반) ─────────────────────────────────────
# Benefit 카피: Meta Ads 업계 경향 — 혜택형 카피 CVR 상승
# CTA Early: 추정값 (정량 출처 없음)

CVR_EFFECT_COPY = {
    'Benefit':       +0.4,
    'Emotional':      0.0,
    'Informational': -0.2
}

CVR_EFFECT_CTA = {
    'Early':   +0.2,
    'Middle':   0.0,
    'End':     -0.1
}


# ── 데이터 생성 ────────────────────────────────────────────────────────────
def generate_data():

    # 소재 요소 랜덤 샘플링
    formats    = np.random.choice(FORMAT_OPTIONS,   N_ROWS)
    copy_types = np.random.choice(COPY_OPTIONS,     N_ROWS)
    lengths    = np.random.choice(LENGTH_OPTIONS,   N_ROWS)
    has_hooks  = np.random.randint(0, 2,            N_ROWS)
    cta_pos    = np.random.choice(CTA_OPTIONS,      N_ROWS)
    has_faces  = np.random.randint(0, 2,            N_ROWS)
    platforms  = np.random.choice(PLATFORM_OPTIONS, N_ROWS)

    # ── CTR 계산 ──
    ctr = np.full(N_ROWS, BASE_CTR, dtype=float)

    ctr += np.array([CTR_EFFECT_FORMAT[f]   for f in formats])
    ctr += np.array([CTR_EFFECT_LENGTH[l]   for l in lengths])
    ctr += np.array([CTR_EFFECT_PLATFORM[p] for p in platforms])
    ctr += has_hooks * CTR_EFFECT_HOOK
    ctr += has_faces * CTR_EFFECT_FACE

    # 노이즈 추가 (실제 광고 성과의 자연 분산 반영)
    ctr += np.random.normal(0, 0.3, N_ROWS)

    # 음수 방지
    ctr = np.clip(ctr, 0.1, None)
    ctr = np.round(ctr, 2)

    # ── CVR 계산 ──
    cvr = np.full(N_ROWS, BASE_CVR, dtype=float)

    cvr += np.array([CVR_EFFECT_COPY[c] for c in copy_types])
    cvr += np.array([CVR_EFFECT_CTA[c]  for c in cta_pos])

    cvr += np.random.normal(0, 0.25, N_ROWS)

    cvr = np.clip(cvr, 0.1, None)
    cvr = np.round(cvr, 2)

    # ── CPM 계산 ──
    # 예산 규모에 따른 CPM 상승 (KPI 시뮬레이터 로직과 동일)
    budgets = np.random.choice([300000, 500000, 1000000, 2000000, 3000000], N_ROWS)

    cpm = np.where(
        budgets < 1000000,
        BASE_CPM,
        BASE_CPM * (1 + 0.05 * np.floor((budgets - 1000000) / 1000000 + 1))
    )
    cpm += np.random.normal(0, 500, N_ROWS)
    cpm = np.clip(cpm, 8000, None).astype(int)

    # ── 메타 변수 ──
    campaign_ids = np.repeat([f'CMP_{str(i).zfill(3)}' for i in range(1, N_CAMPAIGNS + 1)], N_ADS)
    ad_ids       = [f'AD_{str(i).zfill(4)}' for i in range(1, N_ROWS + 1)]
    weeks        = np.random.randint(1, 13, N_ROWS)  # 1~12주차

    # ── DataFrame 생성 ──
    df = pd.DataFrame({
        'ad_id':        ad_ids,
        'campaign_id':  campaign_ids,
        'week':         weeks,
        'budget':       budgets,
        'platform':     platforms,
        'format':       formats,
        'copy_type':    copy_types,
        'video_length': lengths,
        'has_hook':     has_hooks,
        'cta_position': cta_pos,
        'has_face':     has_faces,
        'ctr':          ctr,
        'cvr':          cvr,
        'cpm':          cpm,
    })

    return df


# ── 저장 ───────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)

    df = generate_data()

    output_path = 'data/synthetic_ads.csv'
    df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"데이터 생성 완료: {output_path}")
    print(f"행 수: {len(df)}")
    print()
    print("── 기본 통계 ──────────────────────────")
    print(df[['ctr', 'cvr', 'cpm']].describe().round(2))
    print()
    print("── 포맷별 CTR 평균 ─────────────────────")
    print(df.groupby('format')['ctr'].mean().round(2).sort_values(ascending=False))
    print()
    print("── 카피 유형별 CVR 평균 ────────────────")
    print(df.groupby('copy_type')['cvr'].mean().round(2).sort_values(ascending=False))

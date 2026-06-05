"""
kpi_calc.py
Creative Performance Analyzer — KPI 계산 모듈

[역할]
- 개선된 CTR / CVR → 노출수, 클릭수, 전환수, 매출, ROAS, CPA 계산
- 현재 vs 개선 후 KPI 비교 반환 (Streamlit 탭 5에서 사용)

[계산 로직]
- 실제 CPM: 예산 < 100만원 → 기본 CPM 그대로
             예산 ≥ 100만원 → 기본 CPM × (1 + 0.05 × ⌊(예산 - 100만원) / 100만원 + 1⌋)
- 노출수   = 예산 ÷ 실제 CPM × 1,000
- 클릭수   = 노출수 × CTR
- 전환수   = 클릭수 × CVR
- 매출     = 전환수 × AOV
- ROAS     = (매출 ÷ 예산) × 100
- CPA      = 예산 ÷ 전환수
- 손익분기 ROAS = (1 ÷ 마진율) × 100

[참고]
- CPM 상승 로직: KPI 시뮬레이터와 동일한 설계 적용
- 실제 플랫폼 데이터 기반이 아닌 시뮬레이션 목적
"""

import math


# ── CPM 계산 ──────────────────────────────────────────────────────────────
def calc_actual_cpm(budget: float, base_cpm: float) -> float:
    """
    예산 규모에 따른 실제 CPM 계산.
    예산이 늘수록 경쟁 입찰 증가로 CPM 상승하는 실무 현상 반영.
    100만원 이상부터 100만원 증가마다 CPM +5% 가산.

    예) 예산 300만원 → steps 3 → CPM +15%
        예산 500만원 → steps 5 → CPM +25%
    """
    if budget < 1_000_000:
        return base_cpm

    steps = math.floor((budget - 1_000_000) / 1_000_000 + 1)
    return base_cpm * (1 + 0.05 * steps)


# ── KPI 계산 ──────────────────────────────────────────────────────────────
def calc_kpi(
    budget   : float,
    ctr      : float,
    cvr      : float,
    aov      : float,
    margin   : float,
    base_cpm : float = 15_000
) -> dict:
    """
    Parameters
    ----------
    budget   : 광고 예산 (원)
    ctr      : CTR (%, 예: 3.1)
    cvr      : CVR (%, 예: 2.5)
    aov      : 평균 주문 금액 (원)
    margin   : 마진율 (%, 예: 50)
    base_cpm : 기본 CPM (원, 기본값 15,000)

    Returns
    -------
    {
        'actual_cpm'     : float,
        'impressions'    : int,
        'clicks'         : int,
        'conversions'    : int,
        'revenue'        : float,
        'roas'           : float,
        'cpa'            : float,
        'breakeven_roas' : float,
        'is_profitable'  : bool,
    }
    """
    ctr_rate    = ctr / 100
    cvr_rate    = cvr / 100
    margin_rate = margin / 100

    actual_cpm   = calc_actual_cpm(budget, base_cpm)
    impressions  = int((budget / actual_cpm) * 1_000)
    clicks       = int(impressions * ctr_rate)
    conversions  = int(clicks * cvr_rate)

    revenue         = conversions * aov
    roas            = round((revenue / budget) * 100, 1) if budget > 0 else 0
    cpa             = round(budget / conversions, 0) if conversions > 0 else 0
    breakeven_roas  = round((1 / margin_rate) * 100, 1) if margin_rate > 0 else 0
    is_profitable   = roas >= breakeven_roas

    return {
        'actual_cpm'    : round(actual_cpm, 0),
        'impressions'   : impressions,
        'clicks'        : clicks,
        'conversions'   : conversions,
        'revenue'       : revenue,
        'roas'          : roas,
        'cpa'           : cpa,
        'breakeven_roas': breakeven_roas,
        'is_profitable' : is_profitable,
    }


# ── Before / After KPI 비교 ───────────────────────────────────────────────
def compare_kpi(
    budget      : float,
    current_ctr : float,
    current_cvr : float,
    improved_ctr: float,
    improved_cvr: float,
    aov         : float,
    margin      : float,
    base_cpm    : float = 15_000
) -> dict:
    """
    현재 vs 개선 후 KPI 전체 비교 반환.
    scenario.py의 compare_before_after() 결과를 받아서 사용.
    """
    current  = calc_kpi(budget, current_ctr,  current_cvr,  aov, margin, base_cpm)
    improved = calc_kpi(budget, improved_ctr, improved_cvr, aov, margin, base_cpm)

    roas_delta = round(improved['roas'] - current['roas'], 1)
    cpa_delta  = round(improved['cpa']  - current['cpa'],  0)

    return {
        'current' : current,
        'improved': improved,
        'roas_delta': roas_delta,
        'cpa_delta' : cpa_delta,
    }


# ── 단독 실행 시 결과 확인 ─────────────────────────────────────────────────
if __name__ == '__main__':

    # scenario.py 결과 기준 예시
    BUDGET       = 1_000_000   # 예산 100만원
    CURRENT_CTR  = 3.81
    CURRENT_CVR  = 1.95
    IMPROVED_CTR = 5.96
    IMPROVED_CVR = 2.61
    AOV          = 35_000      # 평균 주문 금액 35,000원
    MARGIN       = 50          # 마진율 50%
    BASE_CPM     = 15_000      # 기본 CPM 15,000원

    result = compare_kpi(
        BUDGET, CURRENT_CTR, CURRENT_CVR,
        IMPROVED_CTR, IMPROVED_CVR,
        AOV, MARGIN, BASE_CPM
    )

    c = result['current']
    i = result['improved']

    print("\n── KPI 비교 (예산 100만원 기준) ─────────────────────")
    print(f"{'항목':<16} {'현재':>12} {'개선 후':>12} {'변화':>10}")
    print("-" * 54)
    print(f"{'실제 CPM (원)':<16} {c['actual_cpm']:>12,.0f} {i['actual_cpm']:>12,.0f}")
    print(f"{'노출수':<16} {c['impressions']:>12,} {i['impressions']:>12,}")
    print(f"{'클릭수':<16} {c['clicks']:>12,} {i['clicks']:>12,}")
    print(f"{'전환수':<16} {c['conversions']:>12,} {i['conversions']:>12,}")
    print(f"{'매출 (원)':<16} {c['revenue']:>12,.0f} {i['revenue']:>12,.0f}")
    print(f"{'ROAS (%)':<16} {c['roas']:>12} {i['roas']:>12} "
          f"  {'+' if result['roas_delta'] >= 0 else ''}{result['roas_delta']}%p")
    print(f"{'CPA (원)':<16} {c['cpa']:>12,.0f} {i['cpa']:>12,.0f} "
          f"  {'+' if result['cpa_delta'] >= 0 else ''}{result['cpa_delta']:,.0f}원")
    print(f"{'손익분기 ROAS':<16} {c['breakeven_roas']:>12} {i['breakeven_roas']:>12}")
    print(f"{'수익성':<16} {'✓' if c['is_profitable'] else '✗':>12} "
          f"{'✓' if i['is_profitable'] else '✗':>12}")

"""
scenario.py
Creative Performance Analyzer — 개선 시나리오 계산 모듈

[변경사항]
- predict_performance / find_best_combination이 df 대신 미리 계산된 계수를 받도록 변경
- 회귀분석 중복 실행 제거 → 성능 개선
"""

import itertools
import pandas as pd
from regression import load_data, run_regression, get_coefficients


OPTIONS = {
    'format'       : ['Brand', 'UGC', 'Carousel', 'Static'],
    'copy_type'    : ['Benefit', 'Emotional', 'Informational'],
    'video_length' : [15, 30, 60, 90],
    'has_hook'     : [0, 1],
    'cta_position' : ['Early', 'Middle', 'End'],
    'has_face'     : [0, 1],
    'platform'     : ['Feed', 'Stories', 'Reels'],
}

BASE_CATEGORIES = {
    'format'       : 'Brand',
    'copy_type'    : 'Benefit',
    'cta_position' : 'Early',
    'platform'     : 'Feed',
}


# ── 모델에서 계수 추출 ────────────────────────────────────────────────────
def get_coef_dict_from_model(model) -> dict:
    """
    이미 학습된 statsmodels OLS 모델에서 계수 추출.
    app.py에서 캐싱된 model을 받아서 사용.
    """
    coef_df = get_coefficients(model)
    return dict(zip(coef_df['feature'], coef_df['coef']))


# ── 단일 소재 설정 CTR / CVR 예측 ────────────────────────────────────────
def predict_performance(
    setting  : dict,
    coef_ctr : dict,
    coef_cvr : dict,
    base_ctr : float,
    base_cvr : float
) -> dict:
    """
    미리 계산된 계수를 받아 예상 CTR / CVR 반환.
    회귀분석을 재실행하지 않음.
    """
    ctr_delta = 0.0
    cvr_delta = 0.0

    for col, val in setting.items():
        if col == 'video_length':
            if 'video_length' in coef_ctr:
                ctr_delta += coef_ctr['video_length'] * (val - 30)
            if 'video_length' in coef_cvr:
                cvr_delta += coef_cvr['video_length'] * (val - 30)

        elif col in ['has_hook', 'has_face']:
            if col in coef_ctr:
                ctr_delta += coef_ctr[col] * val
            if col in coef_cvr:
                cvr_delta += coef_cvr[col] * val

        else:
            base = BASE_CATEGORIES.get(col)
            if val == base:
                continue
            dummy_key = f'{col}_{val}'
            if dummy_key in coef_ctr:
                ctr_delta += coef_ctr[dummy_key]
            if dummy_key in coef_cvr:
                cvr_delta += coef_cvr[dummy_key]

    pred_ctr = round(max(base_ctr + ctr_delta, 0.1), 2)
    pred_cvr = round(max(base_cvr + cvr_delta, 0.1), 2)

    return {'ctr': pred_ctr, 'cvr': pred_cvr}


# ── 최적 조합 탐색 ────────────────────────────────────────────────────────
def find_best_combination(
    coef_ctr : dict,
    coef_cvr : dict,
    base_ctr : float,
    base_cvr : float
) -> dict:
    """
    모든 조합 중 CTR + CVR 합산이 가장 높은 조합 반환.
    계수 기반 계산이라 빠름 (회귀분석 재실행 없음).
    """
    keys   = list(OPTIONS.keys())
    values = list(OPTIONS.values())

    best_score   = -999
    best_setting = {}
    best_perf    = {}

    for combo in itertools.product(*values):
        setting = dict(zip(keys, combo))
        perf    = predict_performance(setting, coef_ctr, coef_cvr, base_ctr, base_cvr)
        score   = perf['ctr'] + perf['cvr']

        if score > best_score:
            best_score   = score
            best_setting = setting
            best_perf    = perf

    return {'setting': best_setting, 'performance': best_perf}


# ── Before / After 비교 ───────────────────────────────────────────────────
def compare_before_after(current: dict, improved: dict) -> dict:
    ctr_delta     = round(improved['ctr'] - current['ctr'], 2)
    cvr_delta     = round(improved['cvr'] - current['cvr'], 2)
    ctr_delta_pct = round((ctr_delta / current['ctr']) * 100, 1)
    cvr_delta_pct = round((cvr_delta / current['cvr']) * 100, 1)

    return {
        'current_ctr'  : current['ctr'],
        'current_cvr'  : current['cvr'],
        'improved_ctr' : improved['ctr'],
        'improved_cvr' : improved['cvr'],
        'ctr_delta'    : ctr_delta,
        'cvr_delta'    : cvr_delta,
        'ctr_delta_pct': ctr_delta_pct,
        'cvr_delta_pct': cvr_delta_pct,
    }


# ── 단독 실행 시 결과 확인 ─────────────────────────────────────────────────
if __name__ == '__main__':
    df = load_data()

    model_ctr, _ = run_regression(df, 'ctr')
    model_cvr, _ = run_regression(df, 'cvr')

    coef_ctr = get_coef_dict_from_model(model_ctr)
    coef_cvr = get_coef_dict_from_model(model_cvr)
    base_ctr = df['ctr'].mean()
    base_cvr = df['cvr'].mean()

    current_setting = {
        'format': 'Brand', 'copy_type': 'Emotional', 'video_length': 30,
        'has_hook': 0, 'cta_position': 'End', 'has_face': 0, 'platform': 'Feed',
    }
    improved_setting = {
        'format': 'UGC', 'copy_type': 'Benefit', 'video_length': 15,
        'has_hook': 1, 'cta_position': 'Early', 'has_face': 1, 'platform': 'Reels',
    }

    current_perf  = predict_performance(current_setting,  coef_ctr, coef_cvr, base_ctr, base_cvr)
    improved_perf = predict_performance(improved_setting, coef_ctr, coef_cvr, base_ctr, base_cvr)
    comparison    = compare_before_after(current_perf, improved_perf)

    print(f"\nCTR: {comparison['current_ctr']}% → {comparison['improved_ctr']}%  "
          f"({comparison['ctr_delta']:+.2f}%p / {comparison['ctr_delta_pct']:+.1f}%)")
    print(f"CVR: {comparison['current_cvr']}% → {comparison['improved_cvr']}%  "
          f"({comparison['cvr_delta']:+.2f}%p / {comparison['cvr_delta_pct']:+.1f}%)")

    best = find_best_combination(coef_ctr, coef_cvr, base_ctr, base_cvr)
    print(f"\n최적 조합: {best['setting']}")
    print(f"예상 CTR: {best['performance']['ctr']}% / CVR: {best['performance']['cvr']}%")

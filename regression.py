"""
regression.py
Creative Performance Analyzer — OLS 회귀분석 모듈

[역할]
- synthetic_ads.csv 로드
- 범주형 변수 더미 변수화
- CTR / CVR 각각 OLS 회귀분석 실행
- 계수(coefficient) 및 유의성 결과 반환 (Streamlit 탭 3에서 사용)
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm


# ── 소재 요소 변수 목록 ────────────────────────────────────────────────────
FEATURE_COLS = [
    'format',
    'copy_type',
    'video_length',
    'has_hook',
    'cta_position',
    'has_face',
    'platform'
]

CATEGORICAL_COLS = ['format', 'copy_type', 'cta_position', 'platform']
NUMERIC_COLS     = ['video_length', 'has_hook', 'has_face']


# ── 데이터 로드 ────────────────────────────────────────────────────────────
def load_data(path: str = 'data/synthetic_ads.csv') -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


# ── 전처리: 더미 변수화 ────────────────────────────────────────────────────
def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    범주형 변수를 더미 변수로 변환.
    drop_first=True: 다중공선성 방지 (기준 카테고리 제거)

    기준 카테고리 (계수 비교 기준):
    - format      → Brand
    - copy_type   → Benefit
    - cta_position → Early
    - platform    → Feed
    """
    df_encoded = pd.get_dummies(
        df[FEATURE_COLS],
        columns=CATEGORICAL_COLS,
        drop_first=True
    )
    # statsmodels 호환을 위해 bool → float 변환
    df_encoded = df_encoded.astype(float)
    return df_encoded


# ── OLS 회귀분석 실행 ─────────────────────────────────────────────────────
def run_regression(df: pd.DataFrame, target: str):
    """
    Parameters
    ----------
    df     : 원본 DataFrame
    target : 'ctr' 또는 'cvr'

    Returns
    -------
    model  : statsmodels OLS 결과 객체
    X      : 사용된 독립변수 DataFrame
    """
    X = preprocess(df)
    X = sm.add_constant(X)
    y = df[target]

    model = sm.OLS(y, X).fit()
    return model, X


# ── 계수 추출 (시각화용) ──────────────────────────────────────────────────
def get_coefficients(model, exclude_const: bool = True) -> pd.DataFrame:
    """
    회귀 계수, 표준오차, p-value, 유의성 여부를 DataFrame으로 반환.

    Parameters
    ----------
    exclude_const : 상수항(const) 제외 여부

    Returns
    -------
    DataFrame columns: feature / coef / std_err / p_value / significant
    """
    coef_df = pd.DataFrame({
        'feature'  : model.params.index,
        'coef'     : model.params.values,
        'std_err'  : model.bse.values,
        'p_value'  : model.pvalues.values
    })

    if exclude_const:
        coef_df = coef_df[coef_df['feature'] != 'const']

    # p-value < 0.05 → 통계적으로 유의한 변수 표시
    coef_df['significant'] = coef_df['p_value'] < 0.05

    coef_df = coef_df.sort_values('coef', ascending=False).reset_index(drop=True)
    return coef_df


# ── 모델 요약 지표 반환 ────────────────────────────────────────────────────
def get_model_summary(model) -> dict:
    """
    R-squared, Adj. R-squared, F-statistic, AIC 반환.
    Streamlit 탭 3 상단 메트릭 카드에서 사용.
    """
    return {
        'R-squared'      : round(model.rsquared, 4),
        'Adj. R-squared' : round(model.rsquared_adj, 4),
        'F-statistic'    : round(model.fvalue, 2),
        'AIC'            : round(model.aic, 2),
        'N'              : int(model.nobs)
    }


# ── 단독 실행 시 결과 확인 ─────────────────────────────────────────────────
if __name__ == '__main__':
    df = load_data()

    for target in ['ctr', 'cvr']:
        print(f"\n{'='*50}")
        print(f"[{target.upper()} 회귀분석 결과]")
        print(f"{'='*50}")

        model, X = run_regression(df, target)
        summary  = get_model_summary(model)
        coef_df  = get_coefficients(model)

        print(f"R-squared      : {summary['R-squared']}")
        print(f"Adj. R-squared : {summary['Adj. R-squared']}")
        print(f"F-statistic    : {summary['F-statistic']}")
        print()
        print("── 계수 (유의한 변수 강조) ──────────────────")
        print(coef_df.to_string(index=False))

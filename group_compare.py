"""
group_compare.py
Creative Performance Analyzer — 그룹 비교 분석 모듈

[역할]
- 소재 요소별 CTR / CVR 평균 비교
- Plotly 차트 반환 (Streamlit 탭 2에서 사용)
"""

import pandas as pd
import plotly.graph_objects as go
from regression import load_data


# ── 색상 설정 ─────────────────────────────────────────────────────────────
COLOR_CTR = '#6B93D6'
COLOR_CVR = '#7EC8A4'


# ── 그룹 평균 계산 ────────────────────────────────────────────────────────
def get_group_stats(df: pd.DataFrame, group_col: str, target: str) -> pd.DataFrame:
    """
    특정 소재 요소 기준으로 CTR 또는 CVR 평균 / 표준편차 계산.

    Parameters
    ----------
    group_col : 그룹 기준 컬럼 (예: 'format', 'copy_type')
    target    : 'ctr' 또는 'cvr'

    Returns
    -------
    DataFrame columns: group_col / mean / std
    """
    stats = (
        df.groupby(group_col)[target]
        .agg(['mean', 'std'])
        .reset_index()
        .rename(columns={'mean': 'mean', 'std': 'std'})
        .sort_values('mean', ascending=False)
    )
    stats['mean'] = stats['mean'].round(2)
    stats['std']  = stats['std'].round(2)
    return stats


# ── Bar Chart 생성 ────────────────────────────────────────────────────────
def plot_group_bar(
    df        : pd.DataFrame,
    group_col : str,
    target    : str,
    title     : str
) -> go.Figure:
    """
    그룹별 평균 Bar Chart 생성.
    에러바(표준편차) 포함.
    """
    stats = get_group_stats(df, group_col, target)
    color = COLOR_CTR if target == 'ctr' else COLOR_CVR
    label = 'CTR (%)' if target == 'ctr' else 'CVR (%)'

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x            = stats[group_col],
        y            = stats['mean'],
        error_y      = dict(type='data', array=stats['std'], visible=True,
                            color='rgba(0,0,0,0.2)', thickness=1.5, width=6),
        marker_color = color,
        text         = stats['mean'].apply(lambda x: f'{x:.2f}%'),
        textposition = 'inside',
        insidetextanchor = 'middle',
        textfont     = dict(color='white', size=12),
    ))

    fig.update_layout(
        title      = title,
        xaxis_title = group_col.replace('_', ' ').title(),
        yaxis_title = label,
        plot_bgcolor = 'white',
        height       = 400,
        margin       = dict(t=60, b=40, l=40, r=20),
        yaxis        = dict(gridcolor='#eeeeee'),
    )

    return fig


# ── 비디오 길이 구간별 분석 ───────────────────────────────────────────────
def plot_video_length(df: pd.DataFrame, target: str) -> go.Figure:
    """
    video_length 구간별 CTR/CVR 평균 Bar Chart.
    """
    label  = 'CTR (%)' if target == 'ctr' else 'CVR (%)'
    color  = COLOR_CTR if target == 'ctr' else COLOR_CVR
    title  = f'영상 길이별 평균 {target.upper()}'

    stats    = get_group_stats(df, 'video_length', target)
    x_labels = [f"{int(v)}초" for v in stats['video_length'].tolist()]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x            = x_labels,
        y            = stats['mean'],
        error_y      = dict(type='data', array=stats['std'], visible=True,
                            color='rgba(0,0,0,0.2)', thickness=1.5, width=6),
        marker_color = color,
        text         = stats['mean'].apply(lambda x: f'{x:.2f}%'),
        textposition = 'inside',
        insidetextanchor = 'middle',
        textfont     = dict(color='white', size=12),
    ))

    fig.update_layout(
        title        = title,
        xaxis_title  = '영상 길이',
        yaxis_title  = label,
        plot_bgcolor = 'white',
        height       = 400,
        margin       = dict(t=60, b=40, l=40, r=20),
        yaxis        = dict(gridcolor='#eeeeee'),
    )

    return fig


# ── 단독 실행 시 결과 확인 ─────────────────────────────────────────────────
if __name__ == '__main__':
    df = load_data()

    groups = [
        ('format',       'ctr', '포맷별 평균 CTR'),
        ('copy_type',    'cvr', '카피 유형별 평균 CVR'),
        ('platform',     'ctr', '플랫폼별 평균 CTR'),
        ('cta_position', 'cvr', 'CTA 위치별 평균 CVR'),
    ]

    for group_col, target, title in groups:
        stats = get_group_stats(df, group_col, target)
        print(f'\n── {title} ─────────────────')
        print(stats.to_string(index=False))

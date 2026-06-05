"""
app.py — Creative Performance Analyzer
실행: C:\\Users\\kp656\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe -m streamlit run app.py
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from regression    import load_data, run_regression, get_coefficients, get_model_summary
from group_compare import get_group_stats, plot_group_bar, plot_video_length
from scenario      import (
    get_coef_dict_from_model, predict_performance,
    find_best_combination, compare_before_after, OPTIONS, BASE_CATEGORIES
)
from kpi_calc import compare_kpi

# ── 색상 상수 ─────────────────────────────────────────────────────────────
C_BLUE  = '#6B93D6'
C_MINT  = '#7EC8A4'
C_GRAY  = '#cccccc'
BG_CARD = 'white'

# ── 한글 컬럼명 매핑 ──────────────────────────────────────────────────────
FEATURE_LABELS = {
    'format_UGC'            : 'UGC 포맷',
    'format_Carousel'       : 'Carousel 포맷',
    'format_Static'         : 'Static 포맷',
    'copy_type_Emotional'   : '감성형 카피',
    'copy_type_Informational': '정보형 카피',
    'video_length'          : '영상 길이',
    'has_hook'              : '훅 유무',
    'has_face'              : '얼굴 유무',
    'cta_position_Middle'   : 'CTA 중간',
    'cta_position_End'      : 'CTA 끝',
    'platform_Reels'        : 'Reels 지면',
    'platform_Stories'      : 'Stories 지면',
}

# ── 페이지 설정 ───────────────────────────────────────────────────────────
st.set_page_config(page_title="Creative Performance Analyzer", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #FAF8F4; }
.block-container { padding-top: 4rem; padding-bottom: 2rem; }
[data-testid="stMetric"],
[data-testid="metric-container"] {
    background: white;
    border: 0.5px solid rgba(0,0,0,0.07);
    border-radius: 14px;
    padding: 18px 22px;
}
[data-testid="stMetricValue"]  { font-size: 28px !important; font-weight: 500 !important; }
[data-testid="stMetricLabel"]  { font-size: 13px !important; text-transform: uppercase; letter-spacing: .5px; color: #888 !important; }
[data-testid="stMetricDelta"]  { font-size: 13px !important; }
.stMarkdown p  { font-size: 15px; }
.stCaption     { font-size: 13px !important; }
hr { border-color: rgba(0,0,0,0.06) !important; }
[data-testid="stExpander"] { border: 0.5px solid rgba(0,0,0,0.07) !important; border-radius: 10px !important; }
label, .stSelectbox label, .stRadio label { font-size: 14px !important; }
</style>
""", unsafe_allow_html=True)

# ── 헤더 ─────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
  <div>
    <span style="font-size:22px;font-weight:500;color:#1A1A1A">Creative Performance Analyzer</span><br>
    <span style="font-size:13px;color:#888;margin-top:2px;display:block">광고 소재 요소별 CTR / CVR 영향도 분석 및 개선 시나리오 도구</span>
  </div>
  <span style="font-size:12px;background:#dbeafe;color:#1d4ed8;border:0.5px solid #93c5fd;padding:5px 14px;border-radius:6px">
    합성 데이터 · 뷰티 Meta Ads 기준
  </span>
</div>
""", unsafe_allow_html=True)

# ── 캐싱 ─────────────────────────────────────────────────────────────────
@st.cache_data
def load():
    from generate_data import generate_data as gen_data
    return gen_data()

@st.cache_data
def get_models(_df):
    model_ctr, _ = run_regression(_df, 'ctr')
    model_cvr, _ = run_regression(_df, 'cvr')
    return model_ctr, model_cvr

@st.cache_data
def get_scenario_base(_df, _model_ctr, _model_cvr):
    coef_ctr = get_coef_dict_from_model(_model_ctr)
    coef_cvr = get_coef_dict_from_model(_model_cvr)
    base_ctr = float(_df['ctr'].mean())
    base_cvr = float(_df['cvr'].mean())
    best     = find_best_combination(coef_ctr, coef_cvr, base_ctr, base_cvr)
    return coef_ctr, coef_cvr, base_ctr, base_cvr, best

df                                            = load()
model_ctr, model_cvr                          = get_models(df)
coef_ctr, coef_cvr, base_ctr, base_cvr, best = get_scenario_base(df, model_ctr, model_cvr)

# ── 헬퍼 함수들 ───────────────────────────────────────────────────────────
def calc_elem_delta(col, val, coef):
    if col == 'video_length':
        return abs(coef.get('video_length', 0) * (val - 30))
    elif col in ['has_hook', 'has_face']:
        return max(coef.get(col, 0) * val, 0)
    else:
        base = BASE_CATEGORIES.get(col)
        return max(coef.get(f'{col}_{val}', 0), 0) if val != base else 0

ELEM_COLS   = ['format','copy_type','video_length','has_hook','cta_position','has_face','platform']
ELEM_LABELS = {'format':'포맷','copy_type':'카피 유형','video_length':'영상 길이',
               'has_hook':'훅','cta_position':'CTA 위치','has_face':'얼굴','platform':'플랫폼'}

def val_fmt(col, v):
    if col == 'video_length': return f'{v}초'
    if v == 1: return '있음'
    if v == 0: return '없음'
    return str(v)

def calc_delta_contributions(current_setting, best_setting, coef_ctr):
    """현재 소재 대비 최적 조합으로 바꿀 때 요소별 CTR 개선량"""
    rows = []
    for col in ELEM_COLS:
        cur_val  = current_setting[col]
        best_val = best_setting[col]
        delta    = max(calc_elem_delta(col, best_val, coef_ctr)
                       - calc_elem_delta(col, cur_val, coef_ctr), 0)
        rows.append({'label': ELEM_LABELS[col], 'val': val_fmt(col, best_val),
                     'delta': delta, 'optimal': cur_val == best_val or delta < 0.001})
    rows.sort(key=lambda x: x['delta'], reverse=True)
    mx = max(r['delta'] for r in rows) or 1
    for r in rows:
        r['pct'] = int(r['delta'] / mx * 100)
    return rows

def make_waterfall(current_setting, best_setting, coef_ctr, coef_cvr, base_ctr, base_cvr):
    """현재 소재 → 최적 조합 CTR 개선 Waterfall"""
    cur_ctr = predict_performance(current_setting, coef_ctr, coef_cvr, base_ctr, base_cvr)['ctr']

    pairs = []
    for col in ELEM_COLS:
        cur_val  = current_setting[col]
        best_val = best_setting[col]
        delta    = round(max(calc_elem_delta(col, best_val, coef_ctr)
                             - calc_elem_delta(col, cur_val, coef_ctr), 0), 3)
        if delta > 0.001:
            pairs.append((delta, f"{ELEM_LABELS[col]} → {val_fmt(col, best_val)}"))

    pairs.sort(reverse=True)
    deltas = [p[0] for p in pairs]
    labels = [p[1] for p in pairs]

    wf_labels = ['현재 CTR'] + labels + ['개선 후 CTR']
    wf_bases  = [0]
    wf_vals   = [cur_ctr]
    wf_colors = ['#e0dbd4']

    running = cur_ctr
    for d in deltas:
        wf_bases.append(running)
        wf_vals.append(d)
        wf_colors.append(C_BLUE)
        running = round(running + d, 3)

    wf_bases.append(0)
    wf_vals.append(round(running, 2))
    wf_colors.append(C_MINT)

    fig = go.Figure(go.Bar(
        x=wf_labels, y=wf_vals, base=wf_bases,
        marker_color=wf_colors,
        text=[f'{v:.2f}%' if i == 0 or i == len(wf_vals)-1 else f'+{v:.2f}%p'
              for i, v in enumerate(wf_vals)],
        textposition='outside', textfont=dict(size=12),
        width=0.55
    ))
    fig.update_layout(
        height=360, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor='rgba(0,0,0,0.05)', tickfont=dict(size=12),
                   ticksuffix='%'),
        xaxis=dict(tickfont=dict(size=12)),
        margin=dict(t=30, b=20, l=50, r=20),
        bargap=0.3
    )
    return fig, round(running, 2)

TAG_STYLE = {
    'info'   : 'background:#dbeafe;color:#1d4ed8;border:0.5px solid #93c5fd',
    'success': 'background:#dcfce7;color:#166534;border:0.5px solid #86efac',
    'neutral': 'background:#f3f4f6;color:#4b5563;border:0.5px solid #d1d5db',
}
def make_tag(label, style='neutral'):
    s = TAG_STYLE[style]
    return f'<span style="font-size:12px;padding:4px 10px;border-radius:6px;{s}">{label}</span>'

def make_tags_html(s):
    tags = [
        make_tag(s['format'], 'info'),
        make_tag(s['copy_type'], 'info'),
        make_tag(f"{s['video_length']}초", 'success'),
        make_tag('훅 있음' if s['has_hook']==1 else '훅 없음', 'success' if s['has_hook']==1 else 'neutral'),
        make_tag(s['cta_position'], 'neutral'),
        make_tag(s['platform'], 'neutral'),
    ]
    return '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:12px">'+''.join(tags)+'</div>'

# ── 탭 ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "데이터 개요","소재 유형 비교","영향도 분석","개선 시나리오","KPI 연결"
])


# ══════════════════════════════════════════════════════════════════════════
# 탭 1 — 데이터 개요
# ══════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("데이터 개요")

    kpi_html = f"""
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:28px">
      <div style="background:white;border-radius:14px;padding:22px 26px;border:0.5px solid rgba(0,0,0,0.07)">
        <div style="font-size:13px;color:#888;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">총 소재 수</div>
        <div style="font-size:34px;font-weight:500;color:#1a1a1a">{len(df):,}개</div>
      </div>
      <div style="background:white;border-radius:14px;padding:22px 26px;border:0.5px solid rgba(0,0,0,0.07)">
        <div style="font-size:13px;color:#888;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">평균 CTR</div>
        <div style="font-size:34px;font-weight:500;color:#1a1a1a">{df['ctr'].mean():.2f}%</div>
        <div style="font-size:12px;color:#6B93D6;margin-top:6px">MHI 2026 뷰티 기준 3.1% 대비</div>
      </div>
      <div style="background:white;border-radius:14px;padding:22px 26px;border:0.5px solid rgba(0,0,0,0.07)">
        <div style="font-size:13px;color:#888;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">평균 CVR</div>
        <div style="font-size:34px;font-weight:500;color:#1a1a1a">{df['cvr'].mean():.2f}%</div>
        <div style="font-size:12px;color:#7EC8A4;margin-top:6px">Triple Whale 2025 기준 2~3% 범위</div>
      </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)
    st.divider()

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**기본 통계**")
        stats_df = df[['ctr','cvr','cpm']].describe().round(2)
        row_labels = {
            'count':'N','mean':'평균','std':'표준편차',
            'min':'최솟값','25%':'1사분위','50%':'중앙값',
            '75%':'3사분위','max':'최댓값'
        }
        border = '1px solid rgba(0,0,0,0.12)'
        rows_html = ""
        for idx, row in stats_df.iterrows():
            cpm_v = f"{row['cpm']:,.0f}" if idx != 'count' else f"{int(row['cpm'])}"
            rows_html += f"""
            <tr>
              <td style="padding:11px 14px;font-size:14px;font-weight:700;color:#1d4ed8;background:#dbeafe;text-align:center;border:{border}">{row_labels.get(idx, idx)}</td>
              <td style="padding:11px 14px;font-size:14px;font-weight:700;color:#1a1a1a;background:white;text-align:center;border:{border}">{row['ctr']}</td>
              <td style="padding:11px 14px;font-size:14px;font-weight:700;color:#1a1a1a;background:white;text-align:center;border:{border}">{row['cvr']}</td>
              <td style="padding:11px 14px;font-size:14px;font-weight:700;color:#1a1a1a;background:white;text-align:center;border:{border}">{cpm_v}</td>
            </tr>"""
        table_html = f"""
        <div style="border-radius:12px;overflow:hidden;margin-top:4px;border:{border}">
          <table style="width:100%;border-collapse:collapse">
            <thead>
              <tr>
                <th style="padding:13px 14px;font-size:13px;font-weight:700;color:white;background:#3D6FBC;text-align:center;border:{border}"></th>
                <th style="padding:13px 14px;font-size:13px;font-weight:700;color:white;background:#3D6FBC;text-align:center;border:{border}">CTR (%)</th>
                <th style="padding:13px 14px;font-size:13px;font-weight:700;color:white;background:#3D6FBC;text-align:center;border:{border}">CVR (%)</th>
                <th style="padding:13px 14px;font-size:13px;font-weight:700;color:white;background:#3D6FBC;text-align:center;border:{border}">CPM (원)</th>
              </tr>
            </thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>"""
        st.markdown(table_html, unsafe_allow_html=True)
    with col_r:
        st.markdown("**소재 요소 분포**")
        selected = st.selectbox("변수 선택",
            ['format','copy_type','platform','cta_position','video_length'])
        dist = df[selected].value_counts().reset_index()
        dist.columns = [selected,'count']
        x_vals = [f"{v}초" if selected=='video_length' else str(v) for v in dist[selected].tolist()]
        fig = go.Figure(go.Bar(
            x=x_vals, y=dist['count'], marker_color=C_BLUE,
            text=dist['count'], textposition='outside',
            textfont=dict(size=13)
        ))
        fig.update_layout(height=300, plot_bgcolor='rgba(0,0,0,0)',
                          paper_bgcolor='rgba(0,0,0,0)',
                          margin=dict(t=20,b=20,l=20,r=20),
                          yaxis=dict(gridcolor='rgba(0,0,0,0.05)'),
                          font=dict(size=13))
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# 탭 2 — 소재 유형 비교
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("소재 유형 비교")
    st.caption("에러바는 표준편차입니다.")
    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(plot_group_bar(df,'format',  'ctr','포맷별 평균 CTR'),        use_container_width=True)
        st.plotly_chart(plot_group_bar(df,'platform','ctr','플랫폼별 평균 CTR'),       use_container_width=True)
        st.plotly_chart(plot_video_length(df,'ctr'),                                   use_container_width=True)
    with col_r:
        st.plotly_chart(plot_group_bar(df,'copy_type',   'cvr','카피 유형별 평균 CVR'),use_container_width=True)
        st.plotly_chart(plot_group_bar(df,'cta_position','cvr','CTA 위치별 평균 CVR'), use_container_width=True)
        st.plotly_chart(plot_video_length(df,'cvr'),                                   use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# 탭 3 — 영향도 분석
# ══════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("영향도 분석 (OLS 회귀)")
    st.caption("기준 카테고리: format=Brand / copy_type=Benefit / cta_position=Early / platform=Feed  |  p < 0.05 변수만 통계적으로 유의합니다.")

    with st.expander("변수 설명 보기"):
        st.markdown("""
| 표시명 | 의미 | 비교 기준 |
|--------|------|----------|
| UGC 포맷 | UGC 소재 포맷 사용 | Brand 대비 |
| Carousel 포맷 | Carousel 소재 포맷 사용 | Brand 대비 |
| Static 포맷 | 정적 이미지 포맷 사용 | Brand 대비 |
| 감성형 카피 | 감성 소구 카피 사용 | 혜택형(Benefit) 대비 |
| 정보형 카피 | 정보 전달형 카피 사용 | 혜택형(Benefit) 대비 |
| 영상 길이 | 영상 길이 1초 증가 시 변화율 | 연속형 변수 |
| 훅 유무 | 첫 3초 훅 포함 여부 | 없음 대비 |
| 얼굴 유무 | 사람 얼굴 포함 여부 | 없음 대비 |
| CTA 중간 | CTA를 중간에 배치 | Early 대비 |
| CTA 끝 | CTA를 끝에 배치 | Early 대비 |
| Reels 지면 | Instagram Reels 노출 | Feed 대비 |
| Stories 지면 | Instagram Stories 노출 | Feed 대비 |
        """)

    col_l, col_r = st.columns(2)

    for col, model, target_label, bar_color in [
        (col_l, model_ctr, "CTR", C_BLUE),
        (col_r, model_cvr, "CVR", C_MINT)
    ]:
        with col:
            summary = get_model_summary(model)
            coef_df = get_coefficients(model)
            coef_df['label'] = coef_df['feature'].map(FEATURE_LABELS).fillna(coef_df['feature'])

            st.markdown(f"**{target_label} 회귀 결과**")

            s_html = f"""
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px">
              <div style="background:white;border-radius:12px;padding:16px 18px;border:0.5px solid rgba(0,0,0,0.07)">
                <div style="font-size:12px;color:#888;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px">R-squared</div>
                <div style="font-size:24px;font-weight:500;color:#1a1a1a">{summary['R-squared']}</div>
              </div>
              <div style="background:white;border-radius:12px;padding:16px 18px;border:0.5px solid rgba(0,0,0,0.07)">
                <div style="font-size:12px;color:#888;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px">Adj. R²</div>
                <div style="font-size:24px;font-weight:500;color:#1a1a1a">{summary['Adj. R-squared']}</div>
              </div>
              <div style="background:white;border-radius:12px;padding:16px 18px;border:0.5px solid rgba(0,0,0,0.07)">
                <div style="font-size:12px;color:#888;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px">F-statistic</div>
                <div style="font-size:24px;font-weight:500;color:#1a1a1a">{summary['F-statistic']}</div>
              </div>
            </div>
            """
            st.markdown(s_html, unsafe_allow_html=True)

            colors = [
                bar_color if (sig and coef > 0) else
                '#e8a090' if (sig and coef < 0) else
                '#dddddd'
                for sig, coef in zip(coef_df['significant'], coef_df['coef'])
            ]
            fig = go.Figure(go.Bar(
                x=coef_df['coef'], y=coef_df['label'], orientation='h',
                marker_color=colors,
                text=coef_df['coef'].apply(lambda x: f'{x:+.3f}'),
                textposition='outside', textfont=dict(size=12)
            ))
            fig.update_layout(
                title=dict(text=f"{target_label}에 대한 소재 요소별 영향도", font=dict(size=14)),
                height=460, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=50,b=20,l=150,r=70),
                xaxis=dict(gridcolor='rgba(0,0,0,0.05)', zeroline=True, zerolinecolor='#aaaaaa',
                           tickfont=dict(size=12)),
                yaxis=dict(tickfont=dict(size=13)),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("색상: 양(+) 유의 / 연한 빨강: 음(-) 유의 / 회색: 비유의 (p ≥ 0.05)")
            with st.expander("계수 상세 테이블"):
                display_df = coef_df[['label','coef','p_value','significant']].round(4)
                display_df.columns = ['변수명','계수','p-value','유의 여부']
                st.dataframe(display_df, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# 탭 4 — 개선 시나리오
# ══════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("개선 시나리오")
    st.caption("소재 요소 간 독립 효과 단순 합산 방식 적용. 실제 조합 효과(상호작용)와 다를 수 있습니다.")

    col_input, col_result = st.columns([3, 7])

    with col_input:
        st.markdown("**현재 소재 설정**")
        current_setting = {
            'format'       : st.selectbox("포맷",       OPTIONS['format']),
            'copy_type'    : st.selectbox("카피 유형",  OPTIONS['copy_type']),
            'video_length' : st.select_slider("영상 길이 (초)", OPTIONS['video_length']),
            'has_hook'     : st.radio("훅 (첫 3초)", [0,1],
                                      format_func=lambda x: "있음" if x else "없음", horizontal=True),
            'cta_position' : st.selectbox("CTA 위치",   OPTIONS['cta_position']),
            'has_face'     : st.radio("얼굴 포함", [0,1],
                                      format_func=lambda x: "있음" if x else "없음", horizontal=True),
            'platform'     : st.selectbox("플랫폼",     OPTIONS['platform']),
        }

    with col_result:
        current_perf  = predict_performance(current_setting, coef_ctr, coef_cvr, base_ctr, base_cvr)
        improved_perf = best['performance']
        comparison    = compare_before_after(current_perf, improved_perf)

        ba = f"""
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;margin-bottom:20px">
          <div style="background:white;border-radius:12px;padding:18px 20px;border:0.5px solid rgba(0,0,0,0.07)">
            <div style="font-size:12px;color:#888;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px">현재 CTR</div>
            <div style="font-size:26px;font-weight:500;color:#1a1a1a">{current_perf['ctr']}%</div>
          </div>
          <div style="background:white;border-radius:12px;padding:18px 20px;border:0.5px solid rgba(0,0,0,0.07);border-top:3px solid {C_BLUE}">
            <div style="font-size:12px;color:#888;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px">개선 후 CTR</div>
            <div style="font-size:26px;font-weight:500;color:#1a1a1a">{improved_perf['ctr']}%</div>
            <div style="font-size:13px;color:#166534;margin-top:4px">{comparison['ctr_delta']:+.2f}%p ({comparison['ctr_delta_pct']:+.1f}%)</div>
          </div>
          <div style="background:white;border-radius:12px;padding:18px 20px;border:0.5px solid rgba(0,0,0,0.07)">
            <div style="font-size:12px;color:#888;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px">현재 CVR</div>
            <div style="font-size:26px;font-weight:500;color:#1a1a1a">{current_perf['cvr']}%</div>
          </div>
          <div style="background:white;border-radius:12px;padding:18px 20px;border:0.5px solid rgba(0,0,0,0.07);border-top:3px solid {C_MINT}">
            <div style="font-size:12px;color:#888;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px">개선 후 CVR</div>
            <div style="font-size:26px;font-weight:500;color:#1a1a1a">{improved_perf['cvr']}%</div>
            <div style="font-size:13px;color:#166534;margin-top:4px">{comparison['cvr_delta']:+.2f}%p ({comparison['cvr_delta_pct']:+.1f}%)</div>
          </div>
        </div>
        """
        st.markdown(ba, unsafe_allow_html=True)

        wf_col, bar_col = st.columns([1, 1])

        with wf_col:
            st.markdown("**현재 → 최적 CTR 개선 흐름**")
            fig_wf, improved_ctr_val = make_waterfall(
                current_setting, best['setting'], coef_ctr, coef_cvr, base_ctr, base_cvr)
            st.plotly_chart(fig_wf, use_container_width=True)

        with bar_col:
            st.markdown("**개선 필요 요소**")
            bar_data = calc_delta_contributions(current_setting, best['setting'], coef_ctr)

            has_improvement = any(not r['optimal'] for r in bar_data)
            if not has_improvement:
                st.markdown('<div style="font-size:14px;color:#166534;margin-top:16px">현재 설정이 이미 최적 조합입니다.</div>',
                            unsafe_allow_html=True)
            else:
                bar_items = ""
                for item in bar_data:
                    color  = C_BLUE if not item['optimal'] else '#e8e8e8'
                    label_suffix = '' if not item['optimal'] else ' ✓'
                    bar_items += f"""
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                      <span style="font-size:13px;color:#666;width:72px;text-align:right;flex-shrink:0">{item['label']}{label_suffix}</span>
                      <div style="flex:1;height:8px;background:#ebebeb;border-radius:4px;overflow:hidden">
                        <div style="width:{item['pct']}%;height:100%;background:{color};border-radius:4px"></div>
                      </div>
                      <span style="font-size:13px;color:#444;width:68px;flex-shrink:0">{item['val']}</span>
                    </div>"""
                st.markdown(f'<div style="margin:8px 0">{bar_items}</div>', unsafe_allow_html=True)
                st.markdown(make_tags_html(best['setting']), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# 탭 5 — KPI 연결
# ══════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("KPI 연결")
    st.caption("탭 4의 개선 시나리오 결과를 기반으로 ROAS 변화를 예측합니다.")

    col_input, col_result = st.columns([3, 7])

    with col_input:
        st.markdown("**캠페인 설정**")
        budget   = st.number_input("예산 (원)",               min_value=100_000, max_value=50_000_000, value=1_000_000, step=100_000)
        aov      = st.number_input("평균 주문 금액 — AOV (원)", min_value=1_000,   max_value=500_000,   value=35_000,  step=1_000)
        margin   = st.slider("마진율 (%)", min_value=10, max_value=90, value=50)
        base_cpm = st.number_input("기본 CPM (원)",            min_value=1_000,   max_value=100_000,   value=15_000,  step=500)
        st.divider()
        st.markdown("**CTR / CVR**")
        st.caption("탭 4 최적 조합 기준으로 자동 설정. 직접 수정 가능합니다.")
        current_ctr_in  = st.number_input("현재 CTR (%)",    value=round(base_ctr, 2), step=0.1)
        current_cvr_in  = st.number_input("현재 CVR (%)",    value=round(base_cvr, 2), step=0.1)
        improved_ctr_in = st.number_input("개선 후 CTR (%)", value=float(best['performance']['ctr']), step=0.1)
        improved_cvr_in = st.number_input("개선 후 CVR (%)", value=float(best['performance']['cvr']), step=0.1)

    with col_result:
        result = compare_kpi(budget, current_ctr_in, current_cvr_in,
                             improved_ctr_in, improved_cvr_in, aov, margin, base_cpm)
        c = result['current']
        i = result['improved']

        roas_html = f"""
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:24px">
          <div style="background:white;border-radius:14px;padding:22px 24px;border:0.5px solid rgba(0,0,0,0.07)">
            <div style="font-size:13px;color:#888;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">현재 ROAS</div>
            <div style="font-size:32px;font-weight:500;color:#1a1a1a">{c['roas']}%</div>
            <div style="font-size:13px;color:{'#166534' if c['is_profitable'] else '#991b1b'};margin-top:6px">
              {'수익 구간' if c['is_profitable'] else '손실 구간'}
            </div>
          </div>
          <div style="background:white;border-radius:14px;padding:22px 24px;border:0.5px solid rgba(0,0,0,0.07);border-top:3px solid {C_BLUE}">
            <div style="font-size:13px;color:#888;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">개선 후 ROAS</div>
            <div style="font-size:32px;font-weight:500;color:#1a1a1a">{i['roas']}%</div>
            <div style="font-size:14px;color:#166534;margin-top:6px">{result['roas_delta']:+.1f}%p</div>
          </div>
          <div style="background:white;border-radius:14px;padding:22px 24px;border:0.5px solid rgba(0,0,0,0.07)">
            <div style="font-size:13px;color:#888;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">손익분기 ROAS</div>
            <div style="font-size:32px;font-weight:500;color:#1a1a1a">{c['breakeven_roas']}%</div>
            <div style="font-size:13px;color:#888;margin-top:6px">마진율 {margin}% 기준</div>
          </div>
        </div>
        """
        st.markdown(roas_html, unsafe_allow_html=True)

        k_col, g_col = st.columns([1, 1])
        with k_col:
            border = '1px solid rgba(0,0,0,0.12)'
            rows = [
                ('실제 CPM (원)', f"{c['actual_cpm']:,.0f}", f"{i['actual_cpm']:,.0f}"),
                ('노출수',        f"{c['impressions']:,}",   f"{i['impressions']:,}"),
                ('클릭수',        f"{c['clicks']:,}",        f"{i['clicks']:,}"),
                ('전환수',        f"{c['conversions']:,}",   f"{i['conversions']:,}"),
                ('매출 (원)',     f"{c['revenue']:,.0f}",    f"{i['revenue']:,.0f}"),
                ('CPA (원)',      f"{c['cpa']:,.0f}",        f"{i['cpa']:,.0f}"),
                ('수익성',        '수익' if c['is_profitable'] else '손실',
                                  '수익' if i['is_profitable'] else '손실'),
            ]
            rows_html = ""
            for label, cur_val, imp_val in rows:
                rows_html += f"""
                <tr>
                  <td style="padding:11px 14px;font-size:14px;font-weight:700;color:#1a1a1a;background:#dbeafe;text-align:center;border:{border};width:33.33%">{label}</td>
                  <td style="padding:11px 14px;font-size:14px;font-weight:400;color:#1a1a1a;background:white;text-align:center;border:{border};width:33.33%">{cur_val}</td>
                  <td style="padding:11px 14px;font-size:14px;font-weight:700;color:#1d4ed8;background:#eef3fd;text-align:center;border:{border};width:33.33%">{imp_val}</td>
                </tr>"""
            table_html = f"""
            <div style="border-radius:12px;overflow:hidden;margin-top:4px;border:{border}">
              <table style="width:100%;border-collapse:collapse">
                <thead>
                  <tr>
                    <th style="padding:13px 14px;font-size:13px;font-weight:700;color:white;background:#3D6FBC;text-align:center;border:{border};width:33.33%">항목</th>
                    <th style="padding:13px 14px;font-size:13px;font-weight:700;color:white;background:#3D6FBC;text-align:center;border:{border};width:33.33%">현재</th>
                    <th style="padding:13px 14px;font-size:13px;font-weight:700;color:white;background:#3D6FBC;text-align:center;border:{border};width:33.33%">개선 후</th>
                  </tr>
                </thead>
                <tbody>{rows_html}</tbody>
              </table>
            </div>"""
            st.markdown(table_html, unsafe_allow_html=True)

        with g_col:
            fig = go.Figure(go.Bar(
                x=['현재', '개선 후', '손익분기'],
                y=[c['roas'], i['roas'], c['breakeven_roas']],
                marker_color=[C_GRAY, C_BLUE, C_MINT],
                text=[f"{c['roas']}%", f"{i['roas']}%", f"{c['breakeven_roas']}%"],
                textposition='outside', textfont=dict(size=14)
            ))
            fig.update_layout(
                title=dict(text='ROAS 비교', font=dict(size=15)),
                height=340, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                yaxis=dict(gridcolor='rgba(0,0,0,0.05)', tickfont=dict(size=13)),
                xaxis=dict(tickfont=dict(size=14)),
                margin=dict(t=50,b=20,l=40,r=20),
            )
            st.plotly_chart(fig, use_container_width=True)

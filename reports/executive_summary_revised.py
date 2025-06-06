import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from kpi_design import render_kpi_card
import locale

# Set Indian number formatting globally for this session
try:
    locale.setlocale(locale.LC_ALL, 'en_IN')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')  # fallback if system locale not available

def indian_format(value):
    try:
        return locale.format_string('%d', int(value), grouping=True)
    except:
        return value

def format_financial_year(fy_code):
    # Replace 'FY-26' with 'Financial Year 2026'
    if fy_code and fy_code.startswith("FY-"):
        return f"Financial Year 20{fy_code[-2:]}"
    return fy_code

def get_last_fy_list(current_fy, n=5):
    return [f"FY-{str(current_fy-i)[-2:]}" for i in range(n-1,-1,-1)]

def prepare_manpower_growth_data(df, fy_list):
    if 'date_of_joining' not in df.columns: return pd.DataFrame(columns=['FY','Headcount'])
    df = df.copy()
    df['FY'] = pd.to_datetime(df['date_of_joining'], errors='coerce').dt.year.apply(lambda y: f"FY-{str(y)[-2:]}" if pd.notnull(y) else None)
    grouped = df.groupby('FY').size().reset_index(name='Headcount')
    grouped = grouped[grouped['FY'].isin(fy_list)]
    grouped = grouped.set_index('FY').reindex(fy_list).reset_index().fillna(0)
    return grouped

def prepare_manpower_cost_data(df, fy_list):
    if 'date_of_joining' not in df.columns or 'total_ctc_pa' not in df.columns: return pd.DataFrame(columns=['FY','Total Cost'])
    df = df.copy()
    df['FY'] = pd.to_datetime(df['date_of_joining'], errors='coerce').dt.year.apply(lambda y: f"FY-{str(y)[-2:]}" if pd.notnull(y) else None)
    grouped = df.groupby('FY')['total_ctc_pa'].sum().reset_index(name='Total Cost')
    grouped = grouped[grouped['FY'].isin(fy_list)]
    grouped = grouped.set_index('FY').reindex(fy_list).reset_index().fillna(0)
    return grouped

def prepare_attrition_data(df, fy_list):
    if 'date_of_exit' not in df.columns: return pd.DataFrame(columns=['FY','Attrition %'])
    df = df.copy()
    df['FY'] = pd.to_datetime(df['date_of_exit'], errors='coerce').dt.year.apply(lambda y: f"FY-{str(y)[-2:]}" if pd.notnull(y) else None)
    attrition_df = df[df['date_of_exit'].notna()].groupby('FY').size().reset_index(name='Leavers')
    headcount_df = df.groupby('FY').size().reset_index(name='Headcount')
    merged = pd.merge(attrition_df, headcount_df, on='FY', how='left')
    merged['Attrition %'] = (merged['Leavers'] / merged['Headcount']) * 100
    merged = merged[merged['FY'].isin(fy_list)]
    merged = merged.set_index('FY').reindex(fy_list).reset_index().fillna(0)
    return merged[['FY', 'Attrition %']]

def prepare_gender_data(df):
    if 'gender' not in df.columns: return pd.DataFrame(columns=['Gender','Count'])
    df = df.copy()
    if 'date_of_exit' in df.columns:
        df = df[df['date_of_exit'].isna()]
    counts = df['gender'].value_counts().reset_index()
    counts.columns = ['Gender', 'Count']
    return counts

def prepare_age_distribution(df):
    if 'date_of_birth' not in df.columns: return pd.DataFrame(columns=['Age Group','Count'])
    df = df.copy()
    if 'date_of_exit' in df.columns:
        df = df[df['date_of_exit'].isna()]
    bins = [0, 20, 25, 30, 35, 40, 45, 50, 55, 60, 100]
    labels = ['<20', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60+']
    df['Age'] = df['date_of_birth'].apply(lambda dob: (pd.Timestamp.now() - pd.to_datetime(dob, errors='coerce')).days // 365 if pd.notnull(dob) else 0)
    df['Age Group'] = pd.cut(df['Age'], bins=bins, labels=labels)
    counts = df['Age Group'].value_counts().reset_index()
    counts.columns = ['Age Group', 'Count']
    return counts.sort_values('Age Group')

def prepare_tenure_distribution(df):
    if 'total_exp_yrs' not in df.columns: return pd.DataFrame(columns=['Tenure Group','Count'])
    df = df.copy()
    if 'date_of_exit' in df.columns:
        df = df[df['date_of_exit'].isna()]
    bins = [0, 0.5, 1, 3, 5, 10, 40]
    labels = ['0-6 Months', '6-12 Months', '1-3 Years', '3-5 Years', '5-10 Years', '10+ Years']
    df['Tenure Group'] = pd.cut(df['total_exp_yrs'], bins=bins, labels=labels)
    counts = df['Tenure Group'].value_counts().reset_index()
    counts.columns = ['Tenure Group', 'Count']
    return counts.sort_values('Tenure Group')

def prepare_experience_distribution(df):
    if 'total_exp_yrs' not in df.columns: return pd.DataFrame(columns=['Experience Group','Count'])
    df = df.copy()
    if 'date_of_exit' in df.columns:
        df = df[df['date_of_exit'].isna()]
    bins = [0, 1, 3, 5, 10, 40]
    labels = ['<1 Year', '1-3 Years', '3-5 Years', '5-10 Years', '10+ Years']
    df['Experience Group'] = pd.cut(df['total_exp_yrs'], bins=bins, labels=labels)
    counts = df['Experience Group'].value_counts().reset_index()
    counts.columns = ['Experience Group', 'Count']
    return counts.sort_values('Experience Group')

def prepare_education_distribution(df):
    if 'qualification_type' not in df.columns: return pd.DataFrame(columns=['Qualification','Count'])
    df = df.copy()
    if 'date_of_exit' in df.columns:
        df = df[df['date_of_exit'].isna()]
    counts = df['qualification_type'].value_counts().reset_index()
    counts.columns = ['Qualification', 'Count']
    return counts

def render_line_chart(df, x, y):
    template = st.session_state.get("plotly_template", "plotly")
    if df.empty or x not in df.columns or y not in df.columns:
        st.write("No Data")
        return

    # Format Y values for data labels
    df['label'] = df[y].apply(indian_format)
    # Replace FY with full form in X labels
    df[x] = df[x].apply(format_financial_year)
    max_val = df[y].max()

    fig = px.line(df, x=x, y=y, markers=True, template=template, text='label')
    fig.update_traces(
        textposition="top center",
        textfont=dict(size=14),
        hovertemplate=f"<b>%{{x}}</b><br>{y}: %{{text}}"
    )
    fig.update_yaxes(
        range=[0, max_val * 1.2],
        tickformat=",",  # Use comma, but data labels are already Indian format
        title=None
    )
    fig.update_layout(margin=dict(l=30, r=20, t=30, b=30))
    st.plotly_chart(fig, use_container_width=True)

def render_bar_chart(df, x, y):
    template = st.session_state.get("plotly_template", "plotly")
    if df.empty or x not in df.columns or y not in df.columns:
        st.write("No Data")
        return

    df['label'] = df[y].apply(indian_format)
    df[x] = df[x].apply(format_financial_year)
    max_val = df[y].max()

    fig = px.bar(df, x=x, y=y, template=template, text='label')
    fig.update_traces(
        textposition='outside',
        texttemplate='%{text}',
        hovertemplate=f"<b>%{{x}}</b><br>{y}: %{{text}}"
    )
    fig.update_yaxes(
        range=[0, max_val * 1.2],
        tickformat=",",
        title=None
    )
    fig.update_layout(margin=dict(l=30, r=20, t=30, b=30))
    st.plotly_chart(fig, use_container_width=True)

def render_pie_chart(df, names, values):
    template = st.session_state.get("plotly_template", "plotly")
    if df.empty or names not in df.columns or values not in df.columns:
        st.write("No Data")
        return

    # Sort data for correct legend order (descending by values)
    df = df.sort_values(values, ascending=False)
    # Format numbers for labels
    df['label'] = df[values].apply(indian_format)
    fig = px.pie(
        df,
        names=names,
        values=values,
        template=template,
        hole=0,
        category_orders={names: list(df[names])},
    )
    fig.update_traces(
        textinfo='label+percent+value',
        textposition='outside',
        pull=[0.05] * len(df),  # separate slices for clarity
        showlegend=True
    )
    # Remove legend inside chart, keep only external
    fig.update_layout(
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.0,
            font=dict(size=13),
            traceorder='normal'
        ),
        margin=dict(l=30, r=20, t=30, b=30)
    )
    st.plotly_chart(fig, use_container_width=True)

def render_donut_chart(df, names, values):
    template = st.session_state.get("plotly_template", "plotly")
    if df.empty or names not in df.columns or values not in df.columns:
        st.write("No Data")
        return

    df = df.sort_values(values, ascending=False)
    df['label'] = df[values].apply(indian_format)
    fig = px.pie(
        df,
        names=names,
        values=values,
        template=template,
        hole=0.5,
        category_orders={names: list(df[names])},
    )
    fig.update_traces(
        textinfo='label+percent+value',
        textposition='outside',
        pull=[0.05] * len(df),
        showlegend=True
    )
    fig.update_layout(
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.0,
            font=dict(size=13),
            traceorder='normal'
        ),
        margin=dict(l=30, r=20, t=30, b=30)
    )
    st.plotly_chart(fig, use_container_width=True)

def run_report(data, config):
    st.markdown(
        """
        <style>
            .block-container {padding-top:2.1rem;}
        </style>
        """, unsafe_allow_html=True
    )
    st.title("Executive Summary")
    df = data.get("employee_master", pd.DataFrame())
    now = datetime.now()
    current_fy = now.year + 1 if now.month >= 4 else now.year
    fy_list = get_last_fy_list(current_fy, n=5)

    today = pd.Timestamp.now().normalize()
    fy_start = pd.Timestamp(f"{current_fy-1}-04-01")
    fy_end = pd.Timestamp(f"{current_fy}-03-31")

    mask_active = (df['date_of_joining'] <= today) & ((df['date_of_exit'].isna()) | (df['date_of_exit'] > today))
    active = mask_active.sum()
    leavers = df['date_of_exit'].between(fy_start, fy_end).sum() if 'date_of_exit' in df.columns else 0
    headcount_start = ((df['date_of_joining'] <= fy_start) & ((df['date_of_exit'].isna()) | (df['date_of_exit'] > fy_start))).sum()
    headcount_end = ((df['date_of_joining'] <= fy_end) & ((df['date_of_exit'].isna()) | (df['date_of_exit'] > fy_end))).sum()
    avg_headcount = (headcount_start + headcount_end) / 2 if (headcount_start + headcount_end) else 1
    attrition = (leavers / avg_headcount) * 100 if avg_headcount else 0
    joiners = df['date_of_joining'].between(fy_start, fy_end).sum() if 'date_of_joining' in df.columns else 0
    total_cost = df['total_ctc_pa'].sum() if 'total_ctc_pa' in df.columns else 0
    female = mask_active & (df['gender'] == 'Female') if 'gender' in df.columns else 0
    total_active = mask_active.sum()
    female_ratio = (female.sum() / total_active * 100) if isinstance(female, pd.Series) and total_active > 0 else 0
    avg_tenure = df['total_exp_yrs'].mean() if 'total_exp_yrs' in df.columns else 0

    def calc_age(dob):
        if pd.isnull(dob): return None
        return (now - pd.to_datetime(dob, errors='coerce')).days // 365
    avg_age = df['date_of_birth'].apply(calc_age).mean() if 'date_of_birth' in df.columns else 0
    avg_total_exp = df['total_exp_yrs'].mean() if 'total_exp_yrs' in df.columns else 0

    kpis = [
        {"label": "Active Employees", "value": active, "type": "Integer"},
        {"label": f"Attrition Rate (FY {str(current_fy-1)[-2:]}-{str(current_fy)[-2:]})", "value": attrition, "type": "Percentage"},
        {"label": f"Joiners (FY {str(current_fy-1)[-2:]}-{str(current_fy)[-2:]})", "value": joiners, "type": "Integer"},
        {"label": "Total Cost (INR)", "value": total_cost, "type": "Currency"},
        {"label": "Female Ratio", "value": female_ratio, "type": "Percentage"},
        {"label": "Average Tenure", "value": avg_tenure, "type": "Years"},
        {"label": "Average Age", "value": avg_age, "type": "Years"},
        {"label": "Average Total Exp", "value": avg_total_exp, "type": "Years"},
    ]

    for i in range(0, len(kpis), 4):
        cols = st.columns(4)
        for j in range(4):
            idx = i + j
            if idx >= len(kpis): break
            kpi = kpis[idx]
            with cols[j]:
                st.markdown(render_kpi_card(kpi['label'], kpi['value'], kpi['type']), unsafe_allow_html=True)

    charts = [
        ("Manpower Growth", lambda df: prepare_manpower_growth_data(df, fy_list), render_line_chart, {"x": "FY", "y": "Headcount"}),
        ("Manpower Cost Trend", lambda df: prepare_manpower_cost_data(df, fy_list), render_bar_chart, {"x": "FY", "y": "Total Cost"}),
        ("Attrition Trend", lambda df: prepare_attrition_data(df, fy_list), render_line_chart, {"x": "FY", "y": "Attrition %"}),
        ("Gender Diversity", prepare_gender_data, render_donut_chart, {"names": "Gender", "values": "Count"}),
        ("Age Distribution", prepare_age_distribution, render_pie_chart, {"names": "Age Group", "values": "Count"}),
        ("Tenure Distribution", prepare_tenure_distribution, render_pie_chart, {"names": "Tenure Group", "values": "Count"}),
        ("Total Experience Distribution", prepare_experience_distribution, render_bar_chart, {"x": "Experience Group", "y": "Count"}),
        ("Education Type Distribution", prepare_education_distribution, render_donut_chart, {"names": "Qualification", "values": "Count"}),
    ]

    for i in range(0, len(charts), 2):
        cols = st.columns(2, gap="large")
        for j in range(2):
            idx = i + j
            if idx >= len(charts): break
            title, prepare_func, render_func, params = charts[idx]
            with cols[j]:
                st.markdown(f"##### {title}")
                df_chart = prepare_func(df)
                if isinstance(params, dict):
                    render_func(df_chart, **params)
                else:
                    render_func(df_chart, params)

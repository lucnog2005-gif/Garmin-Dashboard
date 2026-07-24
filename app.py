from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from collector import collect_all_data
from metrics import extract_metrics, prepare_metrics
from storage import save_metrics

from analysis import (
    generate_insights,
    calculate_acwr,
    calculate_recovery_score,
    recovery_status,
    daily_recommendation,
    calculate_fitness,
    calculate_fatigue,
    calculate_form,
    ai_coach_messages
)

from recovery_engine import (
    calculate_sleep_debt,
    calculate_strain_score,
    calculate_readiness_score,
    calculate_body_battery,
    recovery_trend
)
from performance_trend import (
    calculate_performance_trend
)

# ============================================
# HELPER: CÁLCULO DE PROJEÇÃO (BANISTER MODEL)
# ============================================

def calculate_projection(history_df, future_schedule):
    if history_df.empty or not future_schedule:
        return pd.DataFrame()

    # Prepara cópia do histórico ordenado
    df = history_df.copy()
    if "fitness" not in df.columns or "fatigue" not in df.columns:
        # Se fitness/fatigue ainda não foram injetados no dataframe, calcula
        df["fitness"] = [calculate_fitness(df.iloc[:i+1]) for i in range(len(df))]
        df["fatigue"] = [calculate_fatigue(df.iloc[:i+1]) for i in range(len(df))]

    last_row = df.iloc[-1]
    last_ctl = float(last_row.get("fitness", 0))
    last_atl = float(last_row.get("fatigue", 0))
    last_date = pd.to_datetime(last_row["date"])

    proj_rows = []

    for item in future_schedule:
        item_date = pd.to_datetime(item["date"])
        if item_date <= last_date:
            continue

        load = float(item.get("training_load", 0))

        # Modelo Banister de Decay
        last_ctl = last_ctl + (load - last_ctl) / 42.0
        last_atl = last_atl + (load - last_atl) / 7.0
        form = last_ctl - last_atl

        proj_rows.append({
            "date": item_date,
            "fitness": round(last_ctl, 1),
            "fatigue": round(last_atl, 1),
            "form": round(form, 1),
            "is_future": True
        })

    return pd.DataFrame(proj_rows)


# ============================================
# CONFIG
# ============================================

st.set_page_config(
    page_title="Garmin Performance Dashboard",
    page_icon="🏃",
    layout="wide"
)

# ============================================
# LOAD & TREAT DATA
# ============================================

data = collect_all_data()
metrics = extract_metrics(data)

history = data.get("history", [])
future_schedule = data.get("future_schedule", [])
history_df = pd.DataFrame(history)

if not history_df.empty and "date" in history_df.columns:
    history_df["date"] = pd.to_datetime(history_df["date"])
    history_df = history_df.sort_values("date").reset_index(drop=True)

# ------------------------------------------------------------------
# TRATAMENTO DE SONO
# ------------------------------------------------------------------
current_sleep = metrics.get("sleep_hours")

if not current_sleep or float(current_sleep) == 0:
    if not history_df.empty and "sleep_hours" in history_df.columns:
        valid_sleep_series = history_df[history_df["sleep_hours"] > 0]["sleep_hours"]
        if not valid_sleep_series.empty:
            current_sleep = float(valid_sleep_series.iloc[-1])
            metrics["sleep_hours"] = current_sleep

if not history_df.empty and "sleep_hours" in history_df.columns and current_sleep:
    if history_df.iloc[-1]["sleep_hours"] == 0:
        history_df.loc[history_df.index[-1], "sleep_hours"] = float(current_sleep)

metrics = prepare_metrics(metrics)
save_metrics(metrics)

# ============================================
# PERFORMANCE METRICS (APÓS TRATAMENTO)
# ============================================

acwr = calculate_acwr(history)
recovery_score = calculate_recovery_score(metrics)
recovery = recovery_status(recovery_score)
recommendation = daily_recommendation(recovery_score, acwr)

fitness = calculate_fitness(history_df)
fatigue = calculate_fatigue(history_df)
form = calculate_form(fitness, fatigue)

# Injeta colunas dinâmicas para o histórico acumulado
if not history_df.empty:
    history_df["fitness"] = [calculate_fitness(history_df.iloc[:i+1]) for i in range(len(history_df))]
    history_df["fatigue"] = [calculate_fatigue(history_df.iloc[:i+1]) for i in range(len(history_df))]
    history_df["form"] = history_df["fitness"] - history_df["fatigue"]

# ============================================
# RECOVERY ENGINE
# ============================================

sleep_debt = calculate_sleep_debt(history_df)
strain_score = calculate_strain_score(metrics)
readiness_score = calculate_readiness_score(recovery_score, sleep_debt, form)

body_battery = calculate_body_battery(
    recovery_score,
    metrics.get("stress_avg", 0),
    metrics.get("sleep_hours") or 0
)

trend = recovery_trend(history_df)
performance_trend = calculate_performance_trend(history_df)

# ============================================
# INSIGHTS & AI COACH
# ============================================

insights = generate_insights(metrics)
ai_messages = ai_coach_messages(metrics, recovery_score, acwr, form)

# ============================================
# HEADER
# ============================================

st.title("🏃 Garmin Performance Dashboard")

# ============================================
# MAIN METRICS
# ============================================

st.header("📊 Métricas")

col1, col2, col3 = st.columns(3)

sleep_val = metrics.get("sleep_hours")
sleep_display = f"{round(sleep_val, 2)} h" if sleep_val is not None else "Sincronizando..."

with col1:
    st.metric("😴 Sono", sleep_display)
    st.metric("👣 Passos", metrics.get("steps_display", "Sincronizando..."))

with col2:
    st.metric("❤️ FC repouso", f"{metrics.get('resting_hr', 0)} bpm" if metrics.get('resting_hr') else "--")
    st.metric("🔥 Stress", metrics.get("stress_avg", 0))

with col3:
    st.metric("🏃 VO2max", metrics.get("vo2max", 0))
    st.metric("⚡ Training Effect", metrics.get("training_effect", 0.0))

# ============================================
# LAST ACTIVITY
# ============================================

st.divider()
st.header("🏋️ Última atividade")

col4, col5, col6 = st.columns(3)

with col4:
    st.subheader(metrics.get("last_activity", "Sem atividade"))

with col5:
    st.metric("📏 Distância", f"{metrics.get('last_distance_km', 0.0)} km")

with col6:
    st.metric("❤️ FC média", metrics.get("last_avg_hr", 0))

# ============================================
# DAILY STATUS
# ============================================

st.divider()
st.header("🧠 Status diário")

col7, col8, col9 = st.columns(3)

with col7:
    if recovery_score >= 80:
        st.success("🟢 Recuperação excelente")
    elif recovery_score >= 60:
        st.warning("🟡 Recuperação moderada")
    else:
        st.error("🔴 Recuperação ruim")

with col8:
    if acwr > 1.5:
        st.error("🔴 Carga muito alta")
    elif acwr > 1.2:
        st.warning("🟡 Carga moderada")
    else:
        st.success("🟢 Carga controlada")

with col9:
    te = metrics.get("training_effect", 0)
    if te >= 4:
        st.success("🟢 Performance em evolução")
    elif te >= 3:
        st.info("🟢 Performance estável")
    else:
        st.warning("🟡 Estímulo leve")

# ============================================
# DAILY BRIEFING
# ============================================

st.divider()
st.header("📋 Briefing diário")

for insight in insights:
    if "Excelente" in insight:
        st.success(f"🔥 {insight}")
    elif "adequada" in insight or "controlado" in insight:
        st.success(f"🟢 {insight}")
    else:
        st.warning(f"🟡 {insight}")

# ============================================
# ACTION OF THE DAY
# ============================================

st.divider()
st.header("🎯 Ação do dia")
st.info(recommendation)

# ============================================
# ADVANCED METRICS
# ============================================

st.divider()
st.header("📈 Indicadores avançados")

col10, col11, col12 = st.columns(3)

with col10:
    st.metric("Recovery Score", round(recovery_score, 1))

with col11:
    st.metric("ACWR", round(acwr, 2))

with col12:
    if acwr > 1.5:
        risk = "ALTO"
    elif acwr > 1.2:
        risk = "MODERADO"
    else:
        risk = "BAIXO"
    st.metric("Risco de fadiga", risk)

# ============================================
# FITNESS / FATIGUE / FORM (COM FILTRO DE PERÍODO)
# ============================================

st.divider()
st.header("🏋️ Fitness / Fatigue / Form & Projeção Tapering")

col13, col14, col15 = st.columns(3)

with col13:
    st.metric("Fitness (CTL)", round(fitness, 1))

with col14:
    st.metric("Fatigue (ATL)", round(fatigue, 1))

with col15:
    if form >= 10:
        status = "🟢 Recuperado"
    elif form >= -10:
        status = "🟡 Normal"
    elif form >= -25:
        status = "🟠 Fadiga moderada"
    else:
        status = "🔴 Recuperação necessária"
    st.metric("Form (TSB)", f"{round(form, 1)} ({status})")

# RENDERIZANDO O GRÁFICO CONTINUO + PROJEÇÃO COM FILTRO
if not history_df.empty:

    # Seletor de período interativo
    periodo_opcao = st.radio(
        "Selecione o período de visualização do gráfico:",
        options=["30 dias", "60 dias", "90 dias", "Todo o ciclo (180 dias)"],
        index=3,  # Padrão: Todo o ciclo
        horizontal=True,
        key="radio_fff"
    )

    dias_map = {
        "30 dias": 30,
        "60 dias": 60,
        "90 dias": 90,
        "Todo o ciclo (180 dias)": 180
    }

    dias_filtro = dias_map[periodo_opcao]
    data_limite = datetime.now() - timedelta(days=dias_filtro)

    # Filtra o DataFrame apenas para exibição no gráfico (o cálculo Banister mantém a base completa)
    history_filtered = history_df[history_df["date"] >= data_limite].copy()

    proj_df = calculate_projection(history_df, future_schedule)
    fig_fff = go.Figure()

    # --- HISTÓRICO REAL FILTRADO (LINHAS SÓLIDAS) ---
    fig_fff.add_trace(go.Scatter(
        x=history_filtered["date"], y=history_filtered["fitness"],
        mode="lines", name="Fitness (CTL)", line=dict(color="#FF5722", width=2.5)
    ))
    fig_fff.add_trace(go.Scatter(
        x=history_filtered["date"], y=history_filtered["fatigue"],
        mode="lines", name="Fatigue (ATL)", line=dict(color="#9E9E9E", width=1.5)
    ))
    fig_fff.add_trace(go.Scatter(
        x=history_filtered["date"], y=history_filtered["form"],
        mode="lines", name="Form (TSB)", line=dict(color="#00796B", width=2.5)
    ))

    # --- PROJEÇÃO CALENDÁRIO (LINHAS PONTILHADAS) ---
    if not proj_df.empty:
        last_real = history_df.iloc[[-1]]
        proj_extended = pd.concat([last_real, proj_df], ignore_index=True)

        fig_fff.add_trace(go.Scatter(
            x=proj_extended["date"], y=proj_extended["fitness"],
            mode="lines", name="Fitness (Projeção)", line=dict(color="#FF5722", width=2, dash="dot"),
            showlegend=False
        ))
        fig_fff.add_trace(go.Scatter(
            x=proj_extended["date"], y=proj_extended["fatigue"],
            mode="lines", name="Fatigue (Projeção)", line=dict(color="#9E9E9E", width=1.5, dash="dot"),
            showlegend=False
        ))
        fig_fff.add_trace(go.Scatter(
            x=proj_extended["date"], y=proj_extended["form"],
            mode="lines", name="Form (Projeção Tapering)", line=dict(color="#00796B", width=2, dash="dot"),
            showlegend=False
        ))

    # Faixa verde de Sweet Spot para o dia da prova (+10 a +25)
    fig_fff.add_hrect(
        y0=10, y1=25, fillcolor="green", opacity=0.1, line_width=0,
        annotation_text="Zona Ideal de Prova (Freshness)", annotation_position="top left"
    )

    fig_fff.update_layout(
        title="Fitness & Freshness (Evolução + Treinos Futuros Garmin)",
        xaxis_title="Data",
        yaxis_title="Pontuação",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=50, b=20)
    )

    st.plotly_chart(fig_fff, use_container_width=True)

# ============================================
# PERFORMANCE TREND
# ============================================

st.divider()
st.header("📈 Performance Trend")

col16, col17, col18, col19 = st.columns(4)

with col16:
    st.metric("Trend", performance_trend.get("trend", "--"))

with col17:
    st.metric("Fitness Δ", performance_trend.get("fitness_change", 0))

with col18:
    st.metric("VO2 Δ", performance_trend.get("vo2_change", 0))

with col19:
    st.metric("Volume Δ", performance_trend.get("volume_change", 0))

# ============================================
# AI COACH
# ============================================

st.divider()
st.header("🤖 AI Coach")

for msg in ai_messages:
    if "🔴" in msg:
        st.error(msg)
    elif "🟡" in msg:
        st.warning(msg)
    else:
        st.success(msg)

# ============================================
# RECOVERY ENGINE
# ============================================

st.divider()
st.header("🧠 Recovery Engine")

col20, col21, col22 = st.columns(3)

with col20:
    st.metric("Sleep Debt", f"{sleep_debt} h")
    st.metric("Recovery Trend", trend)

with col21:
    st.metric("Strain Score", strain_score)
    st.metric("Body Battery", body_battery)

with col22:
    st.metric("Readiness", readiness_score)
    if readiness_score >= 80:
        st.success("🟢 Ready to perform")
    elif readiness_score >= 60:
        st.warning("🟡 Moderately recovered")
    else:
        st.error("🔴 Recovery compromised")

# ============================================
# HISTORY & CHARTS (COM FILTRO DE PERÍODO)
# ============================================

st.divider()
st.header("📉 Tendência Garmin")

available_metrics = [
    "steps",
    "sleep_hours",
    "stress_avg",
    "resting_hr",
    "vo2max",
    "training_effect",
    "training_load"
]

col_m1, col_m2 = st.columns([1, 2])

with col_m1:
    selected_metric = st.selectbox("Escolha uma métrica", available_metrics)

with col_m2:
    periodo_metrica = st.radio(
        "Período:",
        options=["30 dias", "60 dias", "90 dias", "Todo o ciclo (180 dias)"],
        index=0,  # Padrão 30 dias para métricas pontuais
        horizontal=True,
        key="radio_metric"
    )

if not history_df.empty and selected_metric in history_df.columns:
    dias_m_map = {
        "30 dias": 30,
        "60 dias": 60,
        "90 dias": 90,
        "Todo o ciclo (180 dias)": 180
    }
    limite_m = datetime.now() - timedelta(days=dias_m_map[periodo_metrica])
    history_m_filtered = history_df[history_df["date"] >= limite_m]

    fig = px.line(
        history_m_filtered,
        x="date",
        y=selected_metric,
        markers=True,
        title=f"{selected_metric} - histórico ({periodo_metrica})"
    )
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# HISTORY TABLE
# ============================================

if not history_df.empty:
    st.dataframe(history_df, use_container_width=True)

# ============================================
# FOOTER
# ============================================

st.divider()
st.caption("Garmin AI Performance System • v6.0")
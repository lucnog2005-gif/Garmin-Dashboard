import streamlit as st
import pandas as pd
import plotly.express as px

from collector import collect_all_data
from metrics import extract_metrics
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
# CONFIG
# ============================================

st.set_page_config(
    page_title="Garmin Performance Dashboard",
    page_icon="🏃",
    layout="wide"
)

# ============================================
# ============================================
# LOAD DATA
# ============================================

data = collect_all_data()
metrics = extract_metrics(data)

# Salva métricas obtidas
save_metrics(metrics)

history = data.get("history", [])
history_df = pd.DataFrame(history)

if not history_df.empty and "date" in history_df.columns:
    history_df["date"] = pd.to_datetime(history_df["date"])
    history_df = history_df.sort_values("date").reset_index(drop=True)

# ------------------------------------------------------------------
# TRATAMENTO DE CORREÇÃO PARA O SONO (GARMIN API FALLBACK)
# ------------------------------------------------------------------
# Se metrics['sleep_hours'] vier zerado/inválido (devido ao dia em aberto na Garmin),
# pegamos o último valor de sono válido registrado no histórico recente (> 0).
current_sleep = metrics.get("sleep_hours")
if not current_sleep or float(current_sleep) == 0:
    if not history_df.empty and "sleep_hours" in history_df.columns:
        valid_sleep_series = history_df[history_df["sleep_hours"] > 0]["sleep_hours"]
        if not valid_sleep_series.empty:
            latest_sleep = valid_sleep_series.iloc[-1]
            metrics["sleep_hours"] = float(latest_sleep)
# ============================================
# PERFORMANCE METRICS
# ============================================

acwr = calculate_acwr(history)
recovery_score = calculate_recovery_score(metrics)
recovery = recovery_status(recovery_score)
recommendation = daily_recommendation(recovery_score, acwr)

fitness = calculate_fitness(history_df)
fatigue = calculate_fatigue(history_df)
form = calculate_form(fitness, fatigue)

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

# Tratamento para exibição visual do sono
sleep_val = metrics.get("sleep_hours")
sleep_display = f"{sleep_val} h" if sleep_val is not None else "Sincronizando..."

with col1:
    st.metric("😴 Sono", sleep_display)
    st.metric("👣 Passos", metrics.get("steps", 0))

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
# FITNESS / FATIGUE / FORM
# ============================================

st.divider()
st.header("🏋️ Fitness / Fatigue / Form")

col13, col14, col15 = st.columns(3)

with col13:
    st.metric("Fitness", round(fitness, 1))

with col14:
    st.metric("Fatigue", round(fatigue, 1))

with col15:
    if form >= 10:
        status = "🟢 Recuperado"
    elif form >= -10:
        status = "🟡 Normal"
    elif form >= -25:
        status = "🟠 Fadiga moderada"
    else:
        status = "🔴 Recuperação necessária"
    st.metric("Form", f"{round(form, 1)} ({status})")

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
# HISTORY & CHARTS
# ============================================

st.divider()
st.header("📉 Tendência semanal Garmin")

available_metrics = [
    "steps",
    "sleep_hours",
    "stress_avg",
    "resting_hr",
    "vo2max",
    "training_effect",
    "training_load"
]

selected_metric = st.selectbox("Escolha uma métrica", available_metrics)

if not history_df.empty and selected_metric in history_df.columns:
    fig = px.line(
        history_df,
        x="date",
        y=selected_metric,
        markers=True,
        title=f"{selected_metric} - histórico recente"
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
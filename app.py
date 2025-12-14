import streamlit as st
import pandas as pd
import joblib
import requests
import holidays
from datetime import datetime
import pytz # Para la zona horaria

# =========================
# 0. CONFIGURACIÓN
# =========================
API_KEY = "4975b6041755c654669c68ea111eed60"
CIUDAD = "Lima,PE"

# Valores MODALES O TÍPICOS para variables que el usuario ya no ingresa
# Estos deben ser valores comunes que el modelo RF aprendió a manejar.
MODAL_DEFAULTS = {
    "n_carriles": 3,
    "tipo_via": "Avenida",
    "tipo_evento": "Ninguno"
}

# Cargar modelo y columnas
try:
    modelo = joblib.load("modelo_trafico.pkl")
    columnas = joblib.load("columnas.pkl")
except FileNotFoundError:
    st.error("Error: No se encuentran los archivos .pkl. Ejecuta primero 'trafico1.py'.")
    st.stop()


# =========================
# 1. OBTENER DATOS Y TIEMPO REAL
# =========================

# --- A) Manejo de Tiempo y Feriados (Lima) ---
zona_lima = pytz.timezone('America/Lima')
hoy = datetime.now(zona_lima)
hora_actual = hoy.hour
dia_semana_actual = hoy.strftime('%A') # Obtiene el nombre del día

pe_holidays = holidays.PE()
es_feriado_hoy = 1 if hoy.date() in pe_holidays else 0
etiqueta_feriado = "SI" if es_feriado_hoy == 1 else "NO"

# Clasificar turno (misma lógica que en el entrenamiento)
def clasificar_turno(h):
    if 6 <= h < 12: return 'Mañana'
    elif 12 <= h < 18: return 'Tarde'
    elif 18 <= h < 22: return 'Noche'
    else: return 'Madrugada'

turno_actual = clasificar_turno(hora_actual)

# --- B) Obtener Clima desde API ---
def obtener_clima():
    url = f"http://api.openweathermap.org/data/2.5/weather?q={CIUDAD}&appid={API_KEY}&lang=es"
    try:
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            desc = data['weather'][0]['description']
            if "nub" in desc or "cubierto" in desc: return "Cielo cubierto"
            elif "lluvia" in desc: return "Lluvia ligera"
            elif "tormenta" in desc: return "Tormenta"
            elif "claro" in desc or "sol" in desc: return "Despejado"
            else: return "Desconocido"
        return "Desconocido"
    except Exception as e:
        return "Desconocido"

clima_actual = obtener_clima()


# =========================
# 2. INTERFAZ (REDSEÑADA)
# =========================
st.title("🚨 Monitor de Congestión en Tiempo Real")
st.markdown("---")

col_hora, col_dia = st.columns(2)

with col_hora:
    st.header(f"{hora_actual}:00 hrs")
    st.subheader(turno_actual)
with col_dia:
    st.markdown(f"**Día de la Semana:** {dia_semana_actual}")
    st.markdown(f"**Vía Típica (Modo):** {MODAL_DEFAULTS['tipo_via']} ({MODAL_DEFAULTS['n_carriles']} Carriles)")


st.sidebar.header("Estado Actual (Lima)")
st.sidebar.info(f"📅 ¿Es Feriado?: **{etiqueta_feriado}**")
st.sidebar.info(f"☁️ Clima: **{clima_actual}**")


# =========================
# 3. PROCESAMIENTO DE DATOS (CON VALORES FIJOS)
# =========================

# Las horas pico se basan en la lógica de turnos (6-10am y 5-8pm)
es_hora_pico_actual = 1 if (6 <= hora_actual <= 10) or (17 <= hora_actual <= 20) else 0

# Crear DataFrame con TODAS las columnas (usando datos reales + modales)
entrada = pd.DataFrame([{
    "hora": hora_actual,
    "es_hora_pico": es_hora_pico_actual,
    "n_carriles": MODAL_DEFAULTS["n_carriles"],
    "condicion_clima": clima_actual,
    "tipo_evento": MODAL_DEFAULTS["tipo_evento"],
    "dia_semana": dia_semana_actual,
    "tipo_via": MODAL_DEFAULTS["tipo_via"],
    "turno": turno_actual,
    "es_feriado": es_feriado_hoy
}])

# One-hot encoding y alineación con columnas de entrenamiento
entrada_dummies = pd.get_dummies(entrada)
entrada_dummies = entrada_dummies.reindex(columns=columnas, fill_value=0)


# =========================
# 4. PREDICCIÓN AUTOMÁTICA
# =========================

# Se predice automáticamente al cargar la página, sin botón
pred = modelo.predict(entrada_dummies)[0]
prob = modelo.predict_proba(entrada_dummies).max() * 100

# Colores y mensajes
color = "🔴" if pred == "ALTO" else "🟠" if pred == "MODERADO" else "🟢"

st.markdown("---")

# Muestra el resultado principal
st.subheader(f"Resultado de Congestión: {color} {pred}")
st.write(f"Probabilidad de acierto: **{prob:.2f}%**")

# Gráfico de probabilidades para transparencia
st.markdown("##### 📈 Distribución de Probabilidades:")
probs_all = modelo.predict_proba(entrada_dummies)[0]
df_probs = pd.DataFrame({
    "Nivel": modelo.classes_,
    "Probabilidad": probs_all * 100
})
st.bar_chart(df_probs.set_index("Nivel"))

# Recomendación final
st.markdown("##### Recomendación de Viaje:")
if pred == "ALTO":
    st.error("⚠️ ALERTA CRÍTICA: Tráfico denso. Evita esta vía o reprograma tu viaje.")
elif pred == "MODERADO":
    st.warning("⚠️ PRECAUCIÓN: Tráfico regular, espera demoras.")
else:
    st.success("✅ VÍA DESPEJADA: Tránsito fluido. ¡Buen viaje!")

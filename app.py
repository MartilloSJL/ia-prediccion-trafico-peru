import streamlit as st
import pandas as pd
import joblib
import requests
import holidays
from datetime import datetime

# =========================
# CONFIGURACIÓN
# =========================
API_KEY = "4975b6041755c654669c68ea111eed60"
CIUDAD = "Lima,PE"

try:
    modelo = joblib.load("modelo_trafico.pkl")
    columnas = joblib.load("columnas.pkl")
except FileNotFoundError:
    st.error("Error: No se encuentran los archivos .pkl. Ejecuta primero 'trafico1.py'.")
    st.stop()

st.title("🚦 Predicción de Tráfico Inteligente")
st.write("Sistema con IA y datos en tiempo real (Clima + Feriados Perú)")

# =========================
# 1 OBTENER DATOS REALES
# =========================
st.sidebar.header("Estado Actual (Lima)")

#Detectar si hoy es feriado
hoy = datetime.now()
pe_holidays = holidays.PE()


es_feriado_hoy = 1 if hoy in pe_holidays else 0
etiqueta_feriado = "SI" if es_feriado_hoy == 1 else "NO"

st.sidebar.info(f"📅 ¿Es Feriado?: **{etiqueta_feriado}**")

# B) Obtener Clima
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
    except:
        return "Desconocido"

clima_actual = obtener_clima()
st.sidebar.info(f"☁️ Clima: **{clima_actual}**")

# =========================
# 2 ENTRADA DEL USUARIO
# =========================
st.subheader("Configuración del Viaje")

hora_actual = hoy.hour
hora = st.slider("Hora del día", 0, 23, hora_actual)

usar_datos_reales = st.checkbox("Usar clima y fecha automáticos", value=True)

if usar_datos_reales:
    condicion_clima = clima_actual
    es_feriado_input = es_feriado_hoy
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_semana = dias[hoy.weekday()]
    st.caption(f"🔒 Datos fijos: {dia_semana}, {condicion_clima}, Feriado: {es_feriado_input}")
else:
    condicion_clima = st.selectbox("Condición del clima", ["Despejado", "Cielo cubierto", "Lluvia ligera", "Tormenta", "Desconocido"])
    dia_semana = st.selectbox("Día de la semana", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
    es_feriado_input = st.selectbox("¿Es Feriado?", [0, 1])

col1, col2 = st.columns(2)
with col1:
    es_hora_pico = st.selectbox("¿Es hora pico?", [0, 1])
    n_carriles = st.number_input("N° Carriles", 1, 10, 3)
with col2:
    tipo_evento = st.selectbox("Evento", ["Ninguno", "Accidente", "Obras", "Manifestación"])
    tipo_via = st.selectbox("Tipo de vía", ["Avenida", "Calle", "Jirón", "Autopista"])

# =========================
# 3. PROCESAMIENTO DE DATOS
# =========================
def clasificar_turno(h):
    if 6 <= h < 12: return 'Mañana'
    elif 12 <= h < 18: return 'Tarde'
    elif 18 <= h < 22: return 'Noche'
    else: return 'Madrugada'

turno = clasificar_turno(hora)


entrada = pd.DataFrame([{
    "hora": hora,
    "es_hora_pico": es_hora_pico,
    "n_carriles": n_carriles,
    "condicion_clima": condicion_clima,
    "tipo_evento": tipo_evento,
    "dia_semana": dia_semana,
    "tipo_via": tipo_via,
    "turno": turno,
    "es_feriado": es_feriado_input
}])


entrada_dummies = pd.get_dummies(entrada)
entrada_dummies = entrada_dummies.reindex(columns=columnas, fill_value=0)

# =========================
# 4. PREDICCIÓN
# =========================
st.markdown("---")
if st.button("🔮 Predecir Congestión") or usar_datos_reales:
    
    # predicción
    pred = modelo.predict(entrada_dummies)[0]
    prob = modelo.predict_proba(entrada_dummies).max() * 100
    
    # colores y mensajes
    color = "🔴" if pred == "ALTO" else "🟠" if pred == "MODERADO" else "🟢"
    
    st.subheader(f"Resultado: {color} {pred}")
    st.write(f"Probabilidad de acierto: **{prob:.2f}%**")

    # gráfico 
    probs_all = modelo.predict_proba(entrada_dummies)[0]
    df_probs = pd.DataFrame({
        "Nivel": modelo.classes_,
        "Probabilidad": probs_all * 100
    })
    st.bar_chart(df_probs.set_index("Nivel"))

    # final
    if pred == "ALTO":
        st.error("⚠️ Recomendación: Evita esta ruta o sal con mucha anticipación.")
    elif pred == "MODERADO":
        st.warning("⚠️ Recomendación: Tráfico regular, toma precauciones.")
    else:
        st.success("✅ Recomendación: Ruta despejada.")
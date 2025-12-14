import streamlit as st
import pandas as pd
import joblib
import requests
import holidays
from datetime import datetime
import pytz

# =========================
# 0. CONFIGURACIÓN Y DATOS
# =========================
API_KEY = "4975b6041755c654669c68ea111eed60"

# Estructura de Distritos de Lima
DISTRITOS_LIMA = {
    "Lima Centro": [
        "Cercado de Lima", "Breña", "La Victoria", "Rímac", "San Luis"
    ],
    "Lima Moderna": [
        "Jesús María", "Lince", "Magdalena del Mar", "Miraflores", 
        "Pueblo Libre", "San Borja", "San Isidro", "San Miguel", 
        "Santiago de Surco", "Surquillo"
    ],
    "Lima Norte": [
        "Ancón", "Carabayllo", "Comas", "Independencia", "Los Olivos", 
        "Puente Piedra", "San Martín de Porres", "Santa Rosa"
    ],
    "Lima Este": [
        "Ate", "Chaclacayo", "Cieneguilla", "El Agustino", "La Molina", 
        "Lurigancho-Chosica", "San Juan de Lurigancho", "Santa Anita"
    ],
    "Lima Sur": [
        "Barranco", "Chorrillos", "Lurín", "Pachacámac", "Pucusana", 
        "Punta Hermosa", "Punta Negra", "San Bartolo", "San Juan de Miraflores", 
        "Santa María del Mar", "Villa El Salvador", "Villa María del Triunfo"
    ]
}

# Valores por defecto para el modelo (necesarios para la predicción)
MODAL_DEFAULTS = {
    "n_carriles": 3,
    "tipo_via": "Avenida",
    "tipo_evento": "Ninguno"
}

# Cargar modelo
try:
    modelo = joblib.load("modelo_trafico.pkl")
    columnas = joblib.load("columnas.pkl")
except FileNotFoundError:
    st.error("Error: Archivos .pkl no encontrados.")
    st.stop()

# =========================
# 1. INTERFAZ: SELECCIÓN DE UBICACIÓN
# =========================
st.title("🚨 Monitor de Congestión - Lima Metropolitana")
st.markdown("Selecciona una zona y distrito para analizar el tráfico en tiempo real.")

st.sidebar.header("📍 Ubicación")

# Selectores anidados
zona_seleccionada = st.sidebar.selectbox("Zona de Lima", list(DISTRITOS_LIMA.keys()))
distrito_seleccionado = st.sidebar.selectbox("Distrito", DISTRITOS_LIMA[zona_seleccionada])

# Construimos la query para la API del clima
# Nota: Algunos distritos necesitan "Lima" para que la API los ubique bien en Perú
ciudad_query = f"{distrito_seleccionado},PE"

# =========================
# 2. OBTENER DATOS TIEMPO REAL
# =========================

# --- A) Tiempo y Feriados ---
zona_lima = pytz.timezone('America/Lima')
hoy = datetime.now(zona_lima)
hora_actual = hoy.hour
dia_semana_actual = hoy.strftime('%A')

pe_holidays = holidays.PE()
es_feriado_hoy = 1 if hoy.date() in pe_holidays else 0
etiqueta_feriado = "SI" if es_feriado_hoy == 1 else "NO"

def clasificar_turno(h):
    if 6 <= h < 12: return 'Mañana'
    elif 12 <= h < 18: return 'Tarde'
    elif 18 <= h < 22: return 'Noche'
    else: return 'Madrugada'

turno_actual = clasificar_turno(hora_actual)

# --- B) Clima Localizado (Por Distrito) ---
def obtener_clima(query):
    # URL dinámica basada en el distrito seleccionado
    url = f"http://api.openweathermap.org/data/2.5/weather?q={query}&appid={API_KEY}&lang=es"
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
        return "Desconocido" # Si la API no encuentra el distrito, devuelve neutro
    except:
        return "Desconocido"

clima_actual = obtener_clima(ciudad_query)

# =========================
# 3. INTERFAZ PRINCIPAL
# =========================
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown(f"### 🏙️ {distrito_seleccionado}")
    st.caption(f"Zona: {zona_seleccionada}")
    
with col2:
    st.metric(label="Hora Actual", value=f"{hora_actual}:00 hrs")
    st.caption(f"📅 {dia_semana_actual} | Feriado: {etiqueta_feriado}")

# Info del clima en sidebar para no saturar
st.sidebar.markdown("---")
st.sidebar.info(f"☁️ Clima en {distrito_seleccionado}: **{clima_actual}**")

# =========================
# 4. PREDICCIÓN
# =========================

es_hora_pico_actual = 1 if (6 <= hora_actual <= 10) or (17 <= hora_actual <= 20) else 0

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

entrada_dummies = pd.get_dummies(entrada)
entrada_dummies = entrada_dummies.reindex(columns=columnas, fill_value=0)

pred = modelo.predict(entrada_dummies)[0]
prob = modelo.predict_proba(entrada_dummies).max() * 100

color = "🔴" if pred == "ALTO" else "🟠" if pred == "MODERADO" else "🟢"

st.markdown("### Estado del Tráfico")
st.subheader(f"{color} {pred}")
st.write(f"Confianza de la IA: **{prob:.2f}%**")

# Gráfico simple
st.markdown("---")
probs_all = modelo.predict_proba(entrada_dummies)[0]
df_probs = pd.DataFrame({"Nivel": modelo.classes_, "Probabilidad": probs_all * 100})
st.bar_chart(df_probs.set_index("Nivel"))

if pred == "ALTO":
    st.error(f"⚠️ Alta congestión en {distrito_seleccionado}. Tomar precauciones.")
elif pred == "MODERADO":
    st.warning("🚗 Tráfico fluido pero con carga vehicular.")
else:
    st.success("✅ Vías libres en el distrito.")

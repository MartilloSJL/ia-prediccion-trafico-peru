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

# Lista de Distritos por Zonas
DISTRITOS_LIMA = {
    "Lima Centro": ["Cercado de Lima", "Breña", "La Victoria", "Rímac", "San Luis"],
    "Lima Moderna": ["Jesús María", "Lince", "Magdalena del Mar", "Miraflores", "Pueblo Libre", "San Borja", "San Isidro", "San Miguel", "Santiago de Surco", "Surquillo"],
    "Lima Norte": ["Ancón", "Carabayllo", "Comas", "Independencia", "Los Olivos", "Puente Piedra", "San Martín de Porres", "Santa Rosa"],
    "Lima Este": ["Ate", "Chaclacayo", "Cieneguilla", "El Agustino", "La Molina", "Lurigancho-Chosica", "San Juan de Lurigancho", "Santa Anita"],
    "Lima Sur": ["Barranco", "Chorrillos", "Lurín", "Pachacámac", "Pucusana", "Punta Hermosa", "Punta Negra", "San Bartolo", "San Juan de Miraflores", "Santa María del Mar", "Villa El Salvador", "Villa María del Triunfo"]
}

# Coordenadas aproximadas (Latitud, Longitud) para el mapa
COORDENADAS = {
    "Cercado de Lima": [-12.0464, -77.0428], "Breña": [-12.0569, -77.0536], "La Victoria": [-12.0642, -77.0144],
    "Rímac": [-12.0303, -77.0296], "San Luis": [-12.0769, -76.9928], "Jesús María": [-12.0772, -77.0494],
    "Lince": [-12.0867, -77.0347], "Magdalena del Mar": [-12.0911, -77.0658], "Miraflores": [-12.1111, -77.0316],
    "Pueblo Libre": [-12.0766, -77.0647], "San Borja": [-12.1077, -76.9994], "San Isidro": [-12.0963, -77.0352],
    "San Miguel": [-12.0838, -77.0931], "Santiago de Surco": [-12.1436, -76.9942], "Surquillo": [-12.1121, -77.0125],
    "Ancón": [-11.7736, -77.1761], "Carabayllo": [-11.8906, -77.0275], "Comas": [-11.9286, -77.0533],
    "Independencia": [-11.9906, -77.0553], "Los Olivos": [-11.9675, -77.0722], "Puente Piedra": [-11.8672, -77.0761],
    "San Martín de Porres": [-12.0003, -77.0614], "Santa Rosa": [-11.8058, -77.1717], "Ate": [-12.0255, -76.9205],
    "Chaclacayo": [-11.9839, -76.7686], "Cieneguilla": [-12.1075, -76.7644], "El Agustino": [-12.0428, -76.9858],
    "La Molina": [-12.0800, -76.9400], "Lurigancho-Chosica": [-11.9367, -76.6931], "San Juan de Lurigancho": [-11.9763, -77.0050],
    "Santa Anita": [-12.0433, -76.9669], "Barranco": [-12.1494, -77.0208], "Chorrillos": [-12.1769, -77.0153],
    "Lurín": [-12.2744, -76.8686], "Pachacámac": [-12.2319, -76.8589], "Pucusana": [-12.4831, -76.7972],
    "Punta Hermosa": [-12.3361, -76.8250], "Punta Negra": [-12.3653, -76.7950], "San Bartolo": [-12.3897, -76.7797],
    "San Juan de Miraflores": [-12.1625, -76.9667], "Santa María del Mar": [-12.4042, -76.7733],
    "Villa El Salvador": [-12.2153, -76.9381], "Villa María del Triunfo": [-12.1583, -76.9419]
}

MODAL_DEFAULTS = { "n_carriles": 3, "tipo_via": "Avenida", "tipo_evento": "Ninguno" }

# Cargar modelo
try:
    modelo = joblib.load("modelo_trafico.pkl")
    columnas = joblib.load("columnas.pkl")
except FileNotFoundError:
    st.error("Error: Archivos .pkl no encontrados.")
    st.stop()

# =========================
# 1. INTERFAZ LATERAL
# =========================
st.sidebar.header("📍 Ubicación")
zona_seleccionada = st.sidebar.selectbox("Zona de Lima", list(DISTRITOS_LIMA.keys()))
distrito_seleccionado = st.sidebar.selectbox("Distrito", DISTRITOS_LIMA[zona_seleccionada])
ciudad_query = f"{distrito_seleccionado},Lima,PE" # Mejorado para precisión en API

# =========================
# 2. LOGICA DE DATOS
# =========================
zona_lima = pytz.timezone('America/Lima')
hoy = datetime.now(zona_lima)
hora_actual = hoy.hour
hora_minutos = hoy.strftime("%H:%M") # Formato HH:MM
dia_semana_actual = hoy.strftime('%A')

pe_holidays = holidays.PE()
es_feriado_hoy = 1 if hoy.date() in pe_holidays else 0
etiqueta_feriado = "SI" if es_feriado_hoy == 1 else "NO"

# Clima
def obtener_clima(query):
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
            return "Desconocido"
        return "Desconocido"
    except:
        return "Desconocido"

clima_actual = obtener_clima(ciudad_query)

# =========================
# 3. PANTALLA PRINCIPAL
# =========================
st.title("🚨 Monitor de Congestión Vehicular")
st.markdown(f"### 🏙️ {distrito_seleccionado}")

# Columnas: Mapa y Datos
col_mapa, col_datos = st.columns([2, 1]) # El mapa ocupa más espacio

with col_datos:
    st.metric(label="Hora Actual", value=f"{hora_minutos} hrs")
    st.markdown(f"**Fecha:** {dia_semana_actual}")
    st.markdown(f"**Feriado:** {etiqueta_feriado}")
    st.info(f"☁️ Clima: **{clima_actual}**")

with col_mapa:
    # Obtener lat/lon del diccionario, si no existe usa Lima centro por defecto
    lat_lon = COORDENADAS.get(distrito_seleccionado, [-12.0464, -77.0428])
    df_mapa = pd.DataFrame({'lat': [lat_lon[0]], 'lon': [lat_lon[1]]})
    st.map(df_mapa, zoom=13)

# =========================
# 4. PREDICCIÓN
# =========================
def clasificar_turno(h):
    if 6 <= h < 12: return 'Mañana'
    elif 12 <= h < 18: return 'Tarde'
    elif 18 <= h < 22: return 'Noche'
    else: return 'Madrugada'

turno_actual = clasificar_turno(hora_actual)
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

st.markdown("---")
st.subheader("Estado del Tráfico en Tiempo Real")

col_res, col_graf = st.columns(2)

with col_res:
    color = "🔴" if pred == "ALTO" else "🟠" if pred == "MODERADO" else "🟢"
    st.markdown(f"# {color} {pred}")
    st.write(f"Probabilidad: **{prob:.1f}%**")
    
    if pred == "ALTO":
        st.error(f"⚠️ Evite circular por {distrito_seleccionado}.")
    elif pred == "MODERADO":
        st.warning("🚗 Tráfico regular.")
    else:
        st.success("✅ Tránsito fluido.")

with col_graf:
    st.caption("Distribución de Probabilidades:")
    probs_all = modelo.predict_proba(entrada_dummies)[0]
    df_probs = pd.DataFrame({"Nivel": modelo.classes_, "Probabilidad": probs_all * 100})
    st.bar_chart(df_probs.set_index("Nivel"))

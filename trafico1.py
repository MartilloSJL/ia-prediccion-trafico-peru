import holidays
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

from sklearn.model_selection import train_test_split, GridSearchCV 
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC 
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from sklearn.tree import plot_tree

# =============
# 1. CARGA DE DATOS
# ====
file_name = 'datos.xlsx' 
try:
    df = pd.read_excel(file_name)
    print(f"-> Archivo '{file_name}' cargado. Registros totales: {len(df)}")
except FileNotFoundError:
    print(f"ERROR: No se encuentra '{file_name}'.")
    exit()

# =======
# 2. LIMPIEZA Y PREPROCESAMIENTO
# ====
print("\n-> Procesando variables y limpiando nulos...")
df = df.dropna(subset=['nivel_congestion'])

columnas_categoricas = ['condicion_clima', 'tipo_evento', 'dia_semana', 'tipo_via']
columnas_numericas = ['hora', 'es_hora_pico', 'n_carriles']

# --- FACTOR PERÚ: DETECCIÓN DE FERIADOS ---
print("-> Generando variable 'es_feriado' (Factor Perú)...")
pe_holidays = holidays.PE()

# Verificamos si existe fecha para calcular feriados
if 'fecha_hora' in df.columns:
    df['fecha_obj'] = pd.to_datetime(df['fecha_hora'])
    # Creamos la columna: 1 si es feriado, 0 si no
    df['es_feriado'] = df['fecha_obj'].apply(lambda x: 1 if x in pe_holidays else 0)
else:
    print("⚠️ ADVERTENCIA: No se encontró columna 'fecha_hora'. Se asume es_feriado=0")
    df['es_feriado'] = 0

columnas_numericas.append('es_feriado') 


df[columnas_categoricas] = df[columnas_categoricas].fillna('Desconocido')
df['n_carriles'] = df['n_carriles'].fillna(df['n_carriles'].mode()[0]).astype(int)
df['es_hora_pico'] = df['es_hora_pico'].fillna(0).astype(int)
df['hora'] = pd.to_numeric(df['hora'], errors='coerce').fillna(0).astype(int)


def clasificar_turno(h):
    if 6 <= h < 12: return 'Mañana'
    elif 12 <= h < 18: return 'Tarde'
    elif 18 <= h < 22: return 'Noche'
    else: return 'Madrugada'

df['turno'] = df['hora'].apply(clasificar_turno)
columnas_categoricas.append('turno') 


df['nivel_congestion'] = df['nivel_congestion'].astype(str).str.upper().str.strip()
clases_validas = ['ALTO', 'BAJO', 'MODERADO']
df = df[df['nivel_congestion'].isin(clases_validas)]

print(f"-> Dataset filtrado para entrenamiento: {df.shape[0]} filas.")

# ========================
# 3. TRANSFORMACIÓN Y SPLIT
# =========
y = df['nivel_congestion']
X_dummies = pd.get_dummies(df[columnas_categoricas], drop_first=True)
X = pd.concat([df[columnas_numericas], X_dummies], axis=1)

# Split Estratificado
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# ==================
# 5. ENTRENAMIENTO
# ====
print("\n-> Iniciando búsqueda de hiperparámetros (Grid Search)...")

param_grid_rf = {
    'n_estimators': [50, 100],
    'max_depth': [3, 5, 10], 
    'min_samples_leaf': [2, 4]
}

grid_rf = GridSearchCV(
    estimator=RandomForestClassifier(random_state=42, class_weight='balanced'),
    param_grid=param_grid_rf,
    cv=3, 
    scoring='accuracy',
    n_jobs=-1
)
grid_rf.fit(X_train, y_train)
modelo_rf = grid_rf.best_estimator_
print(f"   ✅ Mejor Random Forest: {grid_rf.best_params_}")

modelo = modelo_rf 

# ==========================================
# 6. EVALUACIÓN Y GRÁFICOS
# ==========================================
y_pred = modelo.predict(X_test)
acc = accuracy_score(y_test, y_pred)

print(f"\nRESULTADOS DEL MODELO SELECCIONADO:")
print(f"Precisión: {acc * 100:.2f}%")
print(classification_report(y_test, y_pred))

# Matriz de Confusión
labels = ['ALTO', 'BAJO', 'MODERADO']
cm = confusion_matrix(y_test, y_pred, labels=labels)

plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=labels, yticklabels=labels)
plt.title('Matriz de Confusión')
plt.tight_layout()
plt.savefig('matriz_confusion.png')

# Importancia de Variables
importancias = pd.Series(modelo.feature_importances_, index=X.columns).sort_values(ascending=False)
plt.figure(figsize=(10, 6))
sns.barplot(x=importancias.head(10).values, 
            y=importancias.head(10).index, 
            hue=importancias.head(10).index,
            legend=False,
            palette='viridis')
plt.title('Variables más influyentes')
plt.tight_layout()
plt.savefig('importancia_variables.png')
print("-> Gráficos guardados.")

# Guardar modelo y columnas
joblib.dump(modelo, "modelo_trafico.pkl")
joblib.dump(X.columns, "columnas.pkl")

print("\nModelo actualizado y guardado correctamente en 'modelo_trafico.pkl'.")
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de página
st.set_page_config(page_title="Finanzas Familiares", layout="wide")
st.title("💸 Tablero de Control Familiar")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Función para cargar datos (con caché para que sea rápido)
# TTL es el tiempo de vida de la memoria, aquí 5 segundos para ver cambios rápido
def cargar_datos():
    # Lee la primera hoja por defecto (worksheet=0) o pon el nombre de la pestaña principal
    df = conn.read(usecols=list(range(10)), ttl=5) 
    return df

# 4. Intentar cargar y mostrar
try:
    st.write("Conectando con la base de datos...")
    df = cargar_datos()
    
    st.success("¡Conexión Exitosa!")
    
    # Mostrar métricas simples si existen columnas numéricas
    st.subheader("Vista Previa de los Datos")
    st.dataframe(df)

except Exception as e:
    st.error(f"Hubo un error al conectar: {e}")
    st.info("Revisa que hayas compartido la hoja con el email del robot service account.")

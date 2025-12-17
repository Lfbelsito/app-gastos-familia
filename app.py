import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Finanzas Familiares", layout="wide")

# Título y Sidebar
st.title("💸 Tablero de Control Familiar")
st.sidebar.header("Configuración")

# 1. Selector de Pestaña (IMPORTANTE: Pon aquí los nombres EXACTOS de tus pestañas)
# Ejemplo: "Resumen", "Enero", "Febrero", etc.
hoja_seleccionada = st.sidebar.selectbox(
    "Selecciona el Mes/Pestaña:",
    ["Hoja 1", "Enero", "Febrero", "Marzo", "Abril", "Resumen"] # <--- CAMBIA ESTO POR TUS NOMBRES REALES
)

# 2. Conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Cargar datos de la pestaña elegida
try:
    st.write(f"Cargando datos de: **{hoja_seleccionada}**...")
    
    # TRUCO: 'skiprows=1' salta la primera fila si tienes títulos raros.
    # Si ves que sigue mal, prueba cambiar a 0, 2 o 3.
    df = conn.read(
        worksheet=hoja_seleccionada,
        skiprows=0,  # <--- JUEGA CON ESTE NUMERO SI LOS ENCABEZADOS SALEN MAL
        ttl=5
    )
    
    # Limpieza básica: Eliminar filas donde todo esté vacío
    df = df.dropna(how="all")
    
    st.success("¡Datos cargados!")
    
    # Mostramos los datos
    st.dataframe(df)

except Exception as e:
    st.warning(f"No se pudo leer la pestaña '{hoja_seleccionada}'.")
    st.error(f"Error técnico: {e}")
    st.info("💡 Pista: Verifica que el nombre en el selector coincida EXACTAMENTE con el de tu Google Sheet (mayúsculas, espacios, etc).")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Configuración de página
st.set_page_config(page_title="Finanzas Familiares", layout="wide")
st.title("💸 Tablero de Control Familiar")

st.sidebar.header("Navegación")

# 2. LISTA EXACTA DE PESTAÑAS
# Aquí ponemos los nombres tal cual están en tu Google Sheet
lista_pestanas = [
    "Resumen Anual",
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

hoja_seleccionada = st.sidebar.selectbox(
    "Selecciona qué quieres ver:",
    lista_pestanas
)

# 3. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 4. Cargar y mostrar datos
try:
    st.write(f"📂 Cargando datos de: **{hoja_seleccionada}**...")
    
    # Leemos la pestaña seleccionada
    # Si tus encabezados (Fecha, Monto, etc.) no están en la primera fila (fila 1),
    # cambia skiprows=0 por skiprows=1 o 2.
    df = conn.read(
        worksheet=hoja_seleccionada,
        skiprows=0, 
        ttl=5
    )
    
    # Limpieza: quitamos filas que estén totalmente vacías
    df = df.dropna(how="all")
    
    st.success(f"✅ Mostrando {len(df)} registros")
    
    # Mostramos la tabla interactiva
    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"⚠️ No se pudo encontrar la pestaña '{hoja_seleccionada}'.")
    st.info("Por favor verifica que el nombre en la lista del código sea idéntico al de tu Google Sheet (mayúsculas, acentos, espacios).")
    st.caption(f"Detalle del error: {e}")

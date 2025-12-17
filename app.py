import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Finanzas Familiares", layout="wide")
st.title("💸 Tablero de Control Familiar")

# --- BARRA LATERAL ---
st.sidebar.header("Navegación")
lista_pestanas = [
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Resumen Anual"
]
hoja_seleccionada = st.sidebar.selectbox("Selecciona el Mes:", lista_pestanas)

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    st.write(f"📂 Cargando mes de: **{hoja_seleccionada}**...")
    
    # 1. LEER TODO EN CRUDO (Raw)
    # Leemos todo como texto sin encabezados para que no se mezcle nada
    df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)
    
    # --- PROCESAMIENTO: SEPARAR LAS 3 TABLAS ---
    
    # === TABLA 1: GASTOS (Izquierda) ===
    # Columnas A a E (índices 0:5). Filas desde la 1 en adelante (la 0 es vacía o técnica)
    gastos_raw = df_raw.iloc[1:, 0:5].copy() 
    # Ponemos la primera fila como encabezado (Fecha Vencimiento, Categoría...)
    gastos_raw.columns = gastos_raw.iloc[0]
    gastos_raw = gastos_raw[1:] # Borramos la fila repetida del header
    gastos_raw = gastos_raw.dropna(how='all') # Borramos filas vacías
    # Limpieza extra: filtramos si la columna "Monto" no tiene datos
    gastos_raw = gastos_raw[gastos_raw["Monto"].notna()]

    # === TABLA 2: RESUMEN (Arriba Derecha) ===
    # Columnas I a K (índices 8:11). Filas 1 y 2 (según tu imagen)
    resumen_raw = df_raw.iloc[1:3, 8:11].copy()
    resumen_raw.columns = resumen_raw.iloc[0]
    resumen_raw = resumen_raw[1:]
    
    # === TABLA 3: INGRESOS (Abajo Derecha) ===
    # Columnas I a N (índices 8:14). Empieza aprox en la fila 5 (índice 5)
    # Buscamos dinámicamente dónde empieza la palabra "Fecha" en la columna I por si cambia de lugar
    start_row = 5 # Valor por defecto según tu imagen
    for idx, val in df_raw.iloc[:, 8].items():
        if str(val).strip() == "Fecha": # Buscamos el título de la tabla
            start_row = idx
            break
            
    ingresos_raw = df_raw.iloc[start_row:, 8:14].copy()
    ingresos_raw.columns = ingresos_raw.iloc[0]
    ingresos_raw = ingresos_raw[1:]
    ingresos_raw = ingresos_raw.dropna(how='all')
    ingresos_raw = ingresos_raw[ingresos_raw["Monto"].notna()]

    # --- VISUALIZACIÓN EN PANTALLA ---
    
    # 1. Mostrar el Balance arriba destacado
    st.markdown("### 💰 Balance del Mes")
    if not resumen_raw.empty:
        col1, col2, col3 = st.columns(3)
        # Intentamos limpiar los símbolos de moneda para mostrarlos bonitos
        gastos_fijos = resumen_raw.iloc[0].get("Gastos fijos", "0")
        ingresos_total = resumen_raw.iloc[0].get("Ingresos", "0")
        ahorro = resumen_raw.iloc[0].get("Ahorro Mensual", "0")
        
        col1.metric("Gastos Fijos", gastos_fijos)
        col2.metric("Ingresos Totales", ingresos_total)
        col3.metric("Ahorro Neto", ahorro)
    else:
        st.info("No se encontró información de resumen en las celdas I2:K3")

    st.divider() # Línea separadora

    # 2. Mostrar Tablas de Detalle lado a lado
    col_izq, col_der = st.columns([1, 1])
    
    with col_izq:
        st.subheader("📉 Lista de Gastos")
        st.dataframe(gastos_raw, use_container_width=True, hide_index=True)
        
    with col_der:
        st.subheader("📈 Ingresos Detallados")
        st.dataframe(ingresos_raw, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error al procesar la hoja: {e}")
    st.write("Detalles técnicos para depurar:")
    st.write(e)

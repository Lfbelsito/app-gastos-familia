import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide")
st.title("💸 Tablero de Control Familiar")

# --- FUNCION DE LIMPIEZA (LA SOLUCIÓN AL ERROR JSON) ---
def limpiar_df(df):
    # 1. Convierte todo a tipos compatibles (evita el error int64)
    # Convierte columnas numéricas a float (decimales estándar)
    for col in df.columns:
        # Intenta convertir a número, si falla lo deja como texto
        df[col] = pd.to_numeric(df[col], errors='ignore')
    
    # 2. Resetea el índice para que no cause conflictos
    df = df.reset_index(drop=True)
    return df

# --- NAVEGACIÓN ---
lista_pestanas = [
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Resumen Anual"
]
hoja_seleccionada = st.sidebar.selectbox("Selecciona el Mes:", lista_pestanas)

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # CASO 1: RESUMEN ANUAL (Simple)
    if hoja_seleccionada == "Resumen Anual":
        st.info("📊 Estás viendo el Resumen Anual.")
        df = conn.read(worksheet=hoja_seleccionada, ttl=5)
        # Limpiamos antes de mostrar
        df = limpiar_df(df)
        st.dataframe(df, use_container_width=True)
    
    # CASO 2: MESES (Lógica de 3 tablas)
    else:
        st.write(f"📂 Cargando mes de: **{hoja_seleccionada}**...")
        
        # Leemos "en crudo" sin encabezados
        df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)
        
        # === TABLA 1: GASTOS (Izquierda) ===
        gastos_raw = df_raw.iloc[1:, 0:5].copy()
        gastos_raw.columns = gastos_raw.iloc[0].astype(str).str.strip() # Títulos limpios
        gastos_raw = gastos_raw[1:] # Borramos la fila de títulos duplicada
        
        # Filtramos filas vacías basándonos en si tienen datos
        gastos_raw = gastos_raw.dropna(how='all') 
        
        # APLICAMOS LA CURA AL ERROR JSON AQUÍ
        gastos_raw = limpiar_df(gastos_raw)
        
        # === TABLA 2: RESUMEN (Arriba Derecha) ===
        resumen_raw = df_raw.iloc[1:3, 8:11].copy()
        resumen_raw.columns = resumen_raw.iloc[0].astype(str).str.strip()
        resumen_raw = resumen_raw[1:]
        resumen_raw = limpiar_df(resumen_raw)

        # === TABLA 3: INGRESOS (Abajo Derecha) ===
        # Buscamos dónde empieza "Fecha" dinámicamente
        start_row = 5
        # Convertimos la columna a string para buscar sin errores
        col_busqueda = df_raw.iloc[:, 8].astype(str)
        for idx, val in col_busqueda.items():
            if val.strip() == "Fecha":
                start_row = idx
                break
                
        ingresos_raw = df_raw.iloc[start_row:, 8:14].copy()
        ingresos_raw.columns = ingresos_raw.iloc[0].astype(str).str.strip()
        ingresos_raw = ingresos_raw[1:]
        ingresos_raw = ingresos_raw.dropna(how='all')
        ingresos_raw = limpiar_df(ingresos_raw)

        # --- VISUALIZACIÓN ---
        st.markdown("### 💰 Balance del Mes")
        if not resumen_raw.empty:
            col1, col2, col3 = st.columns(3)
            # Usamos .get() con valores por defecto seguros
            gf = resumen_raw.iloc[0].get("Gastos fijos", "0")
            ing = resumen_raw.iloc[0].get("Ingresos", "0")
            aho = resumen_raw.iloc[0].get("Ahorro Mensual", "0")
            
            col1.metric("Gastos Fijos", str(gf))
            col2.metric("Ingresos", str(ing))
            col3.metric("Ahorro", str(aho))
        
        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📉 Gastos")
            st.dataframe(gastos_raw, hide_index=True, use_container_width=True)
        with c2:
            st.subheader("📈 Ingresos")
            st.dataframe(ingresos_raw, hide_index=True, use_container_width=True)

except Exception as e:
    st.error("⚠️ Ocurrió un error al procesar los datos.")
    st.code(f"Detalle del error: {e}") # Mostramos el error en formato código
    st.info("Prueba recargando la página o seleccionando otro mes.")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide")
st.title("💸 Tablero de Control Familiar")

# --- FUNCION DE LIMPIEZA BLINDADA ---
def limpiar_df(df):
    # 1. Eliminamos filas que sean todo NaN (vacías)
    df = df.dropna(how='all')
    
    # 2. Iteramos por POSICIÓN (0, 1, 2...) en vez de por nombre
    # Esto evita el error si hay columnas con nombres repetidos
    for i in range(len(df.columns)):
        try:
            # Intentamos convertir la columna i a números
            df.iloc[:, i] = pd.to_numeric(df.iloc[:, i], errors='ignore')
        except:
            pass # Si falla, dejamos el dato como estaba
            
    # 3. Reseteamos el índice
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
    # CASO 1: RESUMEN ANUAL
    if hoja_seleccionada == "Resumen Anual":
        st.info("📊 Estás viendo el Resumen Anual.")
        df = conn.read(worksheet=hoja_seleccionada, ttl=5)
        df = limpiar_df(df)
        st.dataframe(df, use_container_width=True)
    
    # CASO 2: MESES DETALLADOS
    else:
        st.write(f"📂 Cargando mes de: **{hoja_seleccionada}**...")
        
        # Leemos todo "en crudo"
        df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)
        
        # === TABLA 1: GASTOS (Izquierda) ===
        # Cortamos columnas A a E (0 a 5)
        gastos_raw = df_raw.iloc[1:, 0:5].copy()
        
        # Asignamos nombres de columnas con cuidado
        cols_gastos = gastos_raw.iloc[0].astype(str).str.strip().tolist()
        # Truco: Si hay nombres repetidos o vacíos, Pandas los sufija automáticamente al asignar
        gastos_raw.columns = cols_gastos
        
        gastos_raw = gastos_raw[1:] # Quitamos fila de títulos
        gastos_raw = limpiar_df(gastos_raw) # Limpieza segura
        
        # === TABLA 2: RESUMEN (Arriba Derecha) ===
        resumen_raw = df_raw.iloc[1:3, 8:11].copy()
        cols_resumen = resumen_raw.iloc[0].astype(str).str.strip().tolist()
        resumen_raw.columns = cols_resumen
        resumen_raw = resumen_raw[1:]
        resumen_raw = limpiar_df(resumen_raw)

        # === TABLA 3: INGRESOS (Abajo Derecha) ===
        # Buscamos dónde empieza "Fecha"
        start_row = 5
        col_busqueda = df_raw.iloc[:, 8].astype(str) # Columna I
        for idx, val in col_busqueda.items():
            if val.strip() == "Fecha":
                start_row = idx
                break
                
        ingresos_raw = df_raw.iloc[start_row:, 8:14].copy()
        cols_ingresos = ingresos_raw.iloc[0].astype(str).str.strip().tolist()
        ingresos_raw.columns = cols_ingresos
        ingresos_raw = ingresos_raw[1:]
        ingresos_raw = limpiar_df(ingresos_raw)

        # --- VISUALIZACIÓN ---
        st.markdown("### 💰 Balance del Mes")
        if not resumen_raw.empty:
            col1, col2, col3 = st.columns(3)
            # Usamos iloc[0, 0] (fila 0, columna 0) en vez de nombres para ser mas robustos
            try:
                gf = resumen_raw.columns[0] + ": " + str(resumen_raw.iloc[0, 0])
                ing = resumen_raw.columns[1] + ": " + str(resumen_raw.iloc[0, 1])
                aho = resumen_raw.columns[2] + ": " + str(resumen_raw.iloc[0, 2])
                
                col1.metric("Gastos Fijos", str(resumen_raw.iloc[0, 0]))
                col2.metric("Ingresos", str(resumen_raw.iloc[0, 1]))
                col3.metric("Ahorro", str(resumen_raw.iloc[0, 2]))
            except:
                st.warning("No se pudo leer el resumen correctamente.")
        
        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📉 Gastos")
            st.dataframe(gastos_raw, hide_index=True, use_container_width=True)
        with c2:
            st.subheader("📈 Ingresos")
            st.dataframe(ingresos_raw, hide_index=True, use_container_width=True)

except Exception as e:
    st.error("⚠️ Ocurrió un error inesperado.")
    st.code(f"Error: {e}")

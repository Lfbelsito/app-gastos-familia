import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide")
st.title("💸 Tablero de Control Familiar")

# --- FUNCIÓN 1: CURAR DATOS (Evita el error JSON/Int64) ---
def limpiar_datos(df):
    """
    Convierte todos los datos numéricos extraños de Pandas/Excel
    a números o texto estándar que Streamlit pueda entender.
    """
    if df.empty:
        return df

    # 1. Convertir todo a objetos nativos de Python (rompe la conexión con int64)
    df = df.astype(object)
    
    # 2. Reemplazar valores vacíos o 'nan' por guiones o 0
    df = df.fillna("")
    
    # 3. Intentar convertir números formateados (ej: "1.000,00")
    for col in df.columns:
        try:
            # Si parece número, lo forzamos a float
            df[col] = pd.to_numeric(df[col], errors='ignore')
        except:
            pass
            
    return df

# --- FUNCIÓN 2: CORTAR EXCEL POR COORDENADAS ---
def cortar_excel(df_raw, fila_titulo, fila_datos_inicio, col_inicio, col_fin):
    try:
        # Cortamos el pedazo de hoja
        sub_df = df_raw.iloc[:, col_inicio:col_fin]
        
        # Obtenemos los títulos
        titulos = sub_df.iloc[fila_titulo].astype(str).str.strip()
        
        # PARCHE DE SEGURIDAD: Si hay títulos vacíos ('nan'), les ponemos nombre genérico
        # Esto evita el error "Duplicate column names"
        titulos = [f"Col_{i}" if t.lower() == 'nan' or t == '' else t for i, t in enumerate(titulos)]
        
        # Tomamos los datos
        datos = sub_df.iloc[fila_datos_inicio:].copy()
        datos.columns = titulos
        
        # Limpieza básica de filas vacías
        datos = datos.dropna(how='all')
        
        # Aplicamos la cura de tipos
        datos = limpiar_datos(datos)
        
        return datos
    except Exception as e:
        return pd.DataFrame()

# --- NAVEGACIÓN ---
lista_pestanas = [
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Resumen Anual"
]
hoja_seleccionada = st.sidebar.selectbox("Selecciona el Mes:", lista_pestanas)

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    if hoja_seleccionada == "Resumen Anual":
        st.info("📊 Estás viendo el Resumen Anual.")
        df = conn.read(worksheet=hoja_seleccionada, ttl=5)
        st.dataframe(limpiar_datos(df), use_container_width=True)

    else:
        st.write(f"📂 Cargando mes de: **{hoja_seleccionada}**...")
        
        # Leemos TODO sin encabezados
        df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)

        # -----------------------------------------------------------
        # COORDENADAS EXACTAS (CONFIRMADAS POR TI)
        # Excel Fila 1 = Python 0
        # Excel Fila 2 = Python 1
        # Excel Fila 6 = Python 5
        # -----------------------------------------------------------

        # === 1. GASTOS ===
        # Títulos: Fila 1 (idx 0). Datos: Desde Fila 2 (idx 1). Cols A-E (0-5)
        gastos = cortar_excel(df_raw, fila_titulo=0, fila_datos_inicio=1, col_inicio=0, col_fin=5)

        # === 2. BALANCE (RESUMEN) ===
        # Títulos: Fila 2 (idx 1). Datos: Fila 3 (idx 2). Cols I-K (8-11)
        # Leemos solo la fila de datos específica (2:3) para no agarrar basura
        balance_raw = df_raw.iloc[2:3, 8:11].copy()
        
        # Asignamos títulos manualmente desde la fila anterior
        titulos_bal = df_raw.iloc[1, 8:11].astype(str).str.strip().tolist()
        balance_raw.columns = titulos_bal
        
        # Limpiamos tipos
        balance = limpiar_datos(balance_raw)

        # === 3. INGRESOS ===
        # Títulos: Fila 6 (idx 5). Datos: Desde Fila 7 (idx 6). Cols I-N (8-14)
        ingresos = cortar_excel(df_raw, fila_titulo=5, fila_datos_inicio=6, col_inicio=8, col_fin=14)


        # --- VISUALIZACIÓN ---
        
        st.markdown("### 💰 Balance del Mes")
        
        if not balance.empty:
            c1, c2, c3 = st.columns(3)
            # Extraemos valores con seguridad usando .iloc[0,0]
            # Convertimos explícitamente a string para evitar error JSON
            try:
                v_fijos = str(balance.iloc[0, 0])
                v_ingresos = str(balance.iloc[0, 1])
                v_ahorro = str(balance.iloc[0, 2])
                
                # Nombres de columnas (si existen)
                l_fijos = balance.columns[0] if len(balance.columns) > 0 else "Gastos Fijos"
                l_ingresos = balance.columns[1] if len(balance.columns) > 1 else "Ingresos"
                l_ahorro = balance.columns[2] if len(balance.columns) > 2 else "Ahorro"

                c1.metric(l_fijos, v_fijos)
                c2.metric(l_ingresos, v_ingresos)
                c3.metric(l_ahorro, v_ahorro)
            except Exception as e:
                st.warning(f"Error visualizando métricas: {e}")
        else:
            st.info("No se encontraron datos de Balance en las celdas I3:K3")

        st.divider()

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📉 Gastos")
            if not gastos.empty:
                st.dataframe(gastos, hide_index=True, use_container_width=True)
            else:
                st.info("No hay gastos registrados.")

        with col2:
            st.subheader("📈 Ingresos")
            if not ingresos.empty:
                st.dataframe(ingresos, hide_index=True, use_container_width=True)
            else:
                st.info("No hay ingresos registrados.")

except Exception as e:
    st.error("⚠️ Ocurrió un error inesperado.")
    st.code(str(e))

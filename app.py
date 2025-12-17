import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Finanzas Familiares", layout="wide")
st.title("💸 Tablero de Control Familiar")

# --- NAVEGACIÓN ---
lista_pestanas = [
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Resumen Anual"
]
hoja_seleccionada = st.sidebar.selectbox("Selecciona el Mes:", lista_pestanas)

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # SI ES RESUMEN ANUAL, LO MOSTRAMOS SIMPLE (sin procesar columnas específicas)
    if hoja_seleccionada == "Resumen Anual":
        st.info("📊 Estás viendo el Resumen Anual.")
        df = conn.read(worksheet=hoja_seleccionada, ttl=5)
        st.dataframe(df)
    
    # SI ES UN MES, APLICAMOS LA LÓGICA DE LAS 3 TABLAS
    else:
        st.write(f"📂 Cargando mes de: **{hoja_seleccionada}**...")
        
        # Leemos todo sin encabezados
        df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)
        
        # === TABLA 1: GASTOS (Izquierda) ===
        # Ajustamos para buscar el encabezado correcto
        gastos_raw = df_raw.iloc[1:, 0:5].copy()
        gastos_raw.columns = gastos_raw.iloc[0] # Usamos la primera fila visible como titulos
        gastos_raw = gastos_raw[1:] # Borramos la fila repetida
        
        # LIMPIEZA DE NOMBRES DE COLUMNAS (Clave para arreglar tu error)
        # Esto convierte "Monto " en "Monto" y quita espacios raros
        gastos_raw.columns = gastos_raw.columns.astype(str).str.strip()
        
        # Filtro de seguridad: Solo filtramos si existe la columna Monto
        if "Monto" in gastos_raw.columns:
            gastos_raw = gastos_raw[gastos_raw["Monto"].notna()]
        
        # === TABLA 2: RESUMEN (Arriba Derecha) ===
        resumen_raw = df_raw.iloc[1:3, 8:11].copy()
        resumen_raw.columns = resumen_raw.iloc[0]
        resumen_raw = resumen_raw[1:]
        resumen_raw.columns = resumen_raw.columns.astype(str).str.strip()

        # === TABLA 3: INGRESOS (Abajo Derecha) ===
        # Buscamos dónde empieza la palabra "Fecha" en la columna I
        start_row = 5
        for idx, val in df_raw.iloc[:, 8].items():
            if str(val).strip() == "Fecha":
                start_row = idx
                break
                
        ingresos_raw = df_raw.iloc[start_row:, 8:14].copy()
        ingresos_raw.columns = ingresos_raw.iloc[0]
        ingresos_raw = ingresos_raw[1:]
        ingresos_raw.columns = ingresos_raw.columns.astype(str).str.strip() # Limpieza
        
        if "Monto" in ingresos_raw.columns:
            ingresos_raw = ingresos_raw[ingresos_raw["Monto"].notna()]

        # --- VISUALIZACIÓN ---
        st.markdown("### 💰 Balance del Mes")
        if not resumen_raw.empty:
            col1, col2, col3 = st.columns(3)
            # Usamos .get() para que no falle si el nombre cambia un poco
            gf = resumen_raw.iloc[0].get("Gastos fijos", "-")
            ing = resumen_raw.iloc[0].get("Ingresos", "-")
            aho = resumen_raw.iloc[0].get("Ahorro Mensual", "-")
            
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
    st.error(f"⚠️ Error: {e}")
    st.write("Si el error persiste, verifica que hayas seleccionado un mes que tenga datos cargados.")

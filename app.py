import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide")
st.title("💸 Tablero de Control Familiar")

# --- FUNCIÓN DE EXTRACCIÓN QUIRÚRGICA ---
def cortar_excel(df_raw, fila_titulo, fila_datos_inicio, col_inicio, col_fin):
    try:
        # 1. Seleccionamos el rectángulo de datos
        # slice(col_inicio, col_fin) selecciona las columnas verticalmente
        sub_df = df_raw.iloc[:, col_inicio:col_fin]
        
        # 2. Atrapamos los títulos (headers)
        titulos = sub_df.iloc[fila_titulo].astype(str).str.strip()
        
        # 3. Atrapamos los datos
        datos = sub_df.iloc[fila_datos_inicio:].copy()
        
        # 4. Asignamos los títulos a los datos
        datos.columns = titulos
        
        # 5. Limpieza final: borrar filas totalmente vacías
        datos = datos.dropna(how='all')
        
        # Filtro extra: Si la columna clave (la primera) está vacía, borramos la fila
        # Esto evita que lea filas infinitas hacia abajo vacías
        if not datos.empty:
            datos = datos[datos.iloc[:, 0].ne("nan") & datos.iloc[:, 0].notna()]

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
        st.dataframe(df, use_container_width=True)

    else:
        st.write(f"📂 Cargando mes de: **{hoja_seleccionada}**...")
        
        # LEEMOS TODO EL MAPA (Indices empiezan en 0)
        df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)

        # -----------------------------------------------------------
        # COORDENADAS EXACTAS (AJUSTADAS A TU CORRECCIÓN)
        # Excel Fila 1 = Python 0
        # Excel Fila 2 = Python 1
        # Excel Fila 6 = Python 5
        # Col A=0, E=5, I=8, K=11, N=14
        # -----------------------------------------------------------

        # === 1. GASTOS ===
        # Títulos en Fila 1 (idx 0), Datos desde Fila 2 (idx 1). Cols A-E (0-5)
        gastos = cortar_excel(df_raw, fila_titulo=0, fila_datos_inicio=1, col_inicio=0, col_fin=5)

        # === 2. RESUMEN (BALANCE) ===
        # Títulos en Fila 2 (idx 1), Datos en Fila 3 (idx 2). Cols I-K (8-11)
        # Aquí limitamos los datos solo a la fila 2 (row 3 excel) para que no lea basura de abajo
        balance = df_raw.iloc[2:3, 8:11].copy()
        balance.columns = df_raw.iloc[1, 8:11].astype(str).str.strip() # Títulos de row 2 excel

        # === 3. INGRESOS ===
        # Títulos en Fila 6 (idx 5), Datos desde Fila 7 (idx 6). Cols I-N (8-14)
        ingresos = cortar_excel(df_raw, fila_titulo=5, fila_datos_inicio=6, col_inicio=8, col_fin=14)


        # --- MOSTRAR EN PANTALLA ---
        
        st.markdown("### 💰 Balance del Mes")
        if not balance.empty:
            c1, c2, c3 = st.columns(3)
            try:
                # Usamos indices posicionales para asegurar lectura
                c1.metric(str(balance.columns[0]), str(balance.iloc[0, 0]))
                c2.metric(str(balance.columns[1]), str(balance.iloc[0, 1]))
                c3.metric(str(balance.columns[2]), str(balance.iloc[0, 2]))
            except:
                st.warning("Formato de balance no reconocido.")
        
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
    st.error("⚠️ Algo salió mal al leer el Excel.")
    st.code(str(e))

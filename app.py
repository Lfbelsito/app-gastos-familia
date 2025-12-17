import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px # Usaremos gráficos lindos

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide", page_icon="💰")

# --- LISTAS ---
# Solo los meses que tienen datos reales o estructura válida
MESES_ORDENADOS = [
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
# Si ya tenés datos de 2025 cargados, agregalos a esta lista:
# "Enero", "Febrero", etc.

COLUMNAS_DINERO = ["Monto", "Total", "Gastos", "Ingresos", "Ahorro", "Valor", "Pesos", "USD"]

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_valor(val):
    """Convierte $ 1.000,00 a numero float 1000.0"""
    try:
        val_str = str(val).strip().replace("$", "").replace("USD", "").replace("Ars", "").strip()
        val_str = val_str.replace(".", "").replace(",", ".")
        return float(val_str)
    except:
        return 0.0

def formato_visual(val):
    """Para mostrar en pantalla: $ 1.000"""
    return "$ {:,.0f}".format(val).replace(",", ".")

# --- FUNCIONES DE EXTRACCIÓN (Las que ya funcionan) ---
def encontrar_celda(df_raw, palabras_clave, min_col=0, min_row=0):
    try:
        zona = df_raw.iloc[min_row:, min_col:]
        for r_idx, row in zona.iterrows():
            for c_idx, val in enumerate(row):
                val_str = str(val).lower()
                for p in palabras_clave:
                    if p.lower() in val_str:
                        return r_idx, (c_idx + min_col)
        return None, None
    except: return None, None

def cortar_bloque(df_raw, fila, col, num_cols, filas_aprox=30):
    try:
        headers = df_raw.iloc[fila, col : col + num_cols].astype(str).str.strip().tolist()
        headers = [f"C{i}" if h in ["nan", ""] else h for i,h in enumerate(headers)]
        start = fila + 1
        df = df_raw.iloc[start : start + filas_aprox, col : col + num_cols].copy()
        # Filtro: Eliminar filas donde las primeras 2 columnas estén vacías
        df = df[~((df.iloc[:, 0].astype(str).isin(["nan", "", "None"])) & (df.iloc[:, 1].astype(str).isin(["nan", "", "None"])))]
        df.columns = headers
        return df
    except: return pd.DataFrame()

# --- MOTOR DE DATOS (EL CEREBRO NUEVO) ---
@st.cache_data(ttl=60) # Guarda en memoria 60 segs para no recargar lento
def cargar_todo_el_anio(conn):
    datos_anuales = []
    resumen_kpi = []

    # Barra de progreso porque leer muchas hojas tarda unos segundos
    barra = st.progress(0, text="Analizando tu año financiero...")
    
    for i, mes in enumerate(MESES_ORDENADOS):
        barra.progress((i + 1) / len(MESES_ORDENADOS), text=f"Leyendo {mes}...")
        try:
            df_raw = conn.read(worksheet=mes, header=None)
            
            # 1. Extraer KPI (Balance)
            r_bal, c_bal = encontrar_celda(df_raw, ["Gastos fijos"], min_col=5)
            if r_bal is not None:
                bal = cortar_bloque(df_raw, r_bal, c_bal, 3, filas_aprox=1)
                if not bal.empty:
                    # Limpiamos y guardamos los totales
                    gastos = limpiar_valor(bal.iloc[0, 0])
                    ingresos = limpiar_valor(bal.iloc[0, 1])
                    ahorro = limpiar_valor(bal.iloc[0, 2])
                    
                    resumen_kpi.append({
                        "Mes": mes,
                        "Gastos": gastos,
                        "Ingresos": ingresos,
                        "Ahorro": ahorro
                    })

            # 2. Extraer Detalle de Gastos (para análisis futuro por categoría)
            # (Aquí podrías agregar lógica para guardar todos los gastos juntos)
            
        except Exception as e:
            print(f"Error leyendo {mes}: {e}")
            
    barra.empty() # Borra la barra
    return pd.DataFrame(resumen_kpi)

# --- INTERFAZ PRINCIPAL ---

st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", ["📊 Dashboard General", "📅 Ver Mensual"])

conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# PANTALLA 1: DASHBOARD INTELIGENTE
# ==========================================
if opcion == "📊 Dashboard General":
    st.title("💸 Tablero de Control Familiar")
    st.markdown("### Panorama Anual (Generado Automáticamente)")
    
    # Cargar datos
    df_resumen = cargar_todo_el_anio(conn)
    
    if not df_resumen.empty:
        # 1. TARJETAS DE TOTALES
        total_ingresos = df_resumen["Ingresos"].sum()
        total_gastos = df_resumen["Gastos"].sum()
        total_ahorro = df_resumen["Ahorro"].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Ingresos Año", formato_visual(total_ingresos), border=True)
        c2.metric("Total Gastos Año", formato_visual(total_gastos), delta_color="inverse", border=True)
        c3.metric("Ahorro Neto Acumulado", formato_visual(total_ahorro), border=True)
        
        st.divider()
        
        # 2. GRÁFICOS
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.subheader("Evolución de Gastos vs Ingresos")
            # Reestructurar datos para el gráfico
            df_melted = df_resumen.melt(id_vars=["Mes"], value_vars=["Ingresos", "Gastos"], var_name="Tipo", value_name="Monto")
            st.bar_chart(df_melted, x="Mes", y="Monto", color="Tipo", stack=False)

        with col_graf2:
            st.subheader("Curva de Ahorro")
            st.line_chart(df_resumen, x="Mes", y="Ahorro")
            
        # 3. TABLA DE DATOS
        with st.expander("Ver tabla de datos consolidada"):
            # Formateamos para mostrar bonito
            df_show = df_resumen.copy()
            for col in ["Gastos", "Ingresos", "Ahorro"]:
                df_show[col] = df_show[col].apply(formato_visual)
            st.dataframe(df_show, use_container_width=True)
            
    else:
        st.warning("No se pudieron cargar datos de los meses. Revisa la conexión.")


# ==========================================
# PANTALLA 2: DETALLE MENSUAL (Lo clásico)
# ==========================================
elif opcion == "📅 Ver Mensual":
    mes_seleccionado = st.sidebar.selectbox("Selecciona Mes:", MESES_ORDENADOS)
    st.title(f"Detalle de {mes_seleccionado}")
    
    try:
        df_raw = conn.read(worksheet=mes_seleccionado, header=None)
        
        # --- Extracción (Mismo código que ya funciona) ---
        r_bal, c_bal = encontrar_celda(df_raw, ["Gastos fijos"], min_col=5)
        balance = cortar_bloque(df_raw, r_bal, c_bal, 3, 1) if r_bal is not None else pd.DataFrame()
        
        r_gas, c_gas = encontrar_celda(df_raw, ["Vencimiento", "Categoría"], min_col=0)
        gastos = cortar_bloque(df_raw, r_gas, c_gas, 5, 40) if r_gas is not None else pd.DataFrame()
        
        r_ing, c_ing = encontrar_celda(df_raw, ["Fecha", "Descripcion"], min_col=6, min_row=3)
        ingresos = cortar_bloque(df_raw, r_ing, c_ing, 6, 20) if r_ing is not None else pd.DataFrame()

        # --- Visualización Mensual ---
        if not balance.empty:
            c1, c2, c3 = st.columns(3)
            # Limpiamos y mostramos
            try:
                v1 = balance.iloc[0,0]; v2 = balance.iloc[0,1]; v3 = balance.iloc[0,2]
                c1.metric("Gastos Fijos", str(v1)); c2.metric("Ingresos", str(v2)); c3.metric("Ahorro", str(v3))
            except: pass
            
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Gastos")
            st.dataframe(gastos, hide_index=True)
        with col2:
            st.subheader("Ingresos")
            st.dataframe(ingresos, hide_index=True)
            
    except Exception as e:
        st.error(f"Error cargando el mes: {e}")

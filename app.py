import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide", page_icon="💰")
st.title("💸 Tablero de Control Familiar")

# --- 2. LISTAS ---
MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
COLUMNAS_DINERO = [
    "Monto", "Total", "Gastos", "Ingresos", "Ahorro", 
    "Cotizacion", "Saldo", "Valor", "Pesos", "USD", "Ars"
] + MESES

# --- 3. FUNCIONES DE LIMPIEZA ---
def formato_pesos(valor):
    try:
        val_str = str(valor).strip()
        if val_str in ["", "-", "nan", "None", "0", "0.0"]: return "-"
        val_str = val_str.replace("$", "").replace("USD", "").replace("Ars", "").strip()
        val_str = val_str.replace(".", "").replace(",", ".")
        val_float = float(val_str)
        return "$ " + "{:,.0f}".format(val_float).replace(",", ".")
    except:
        return valor

def limpiar_y_formatear(df):
    if df.empty: return df
    # Primero convertimos todo a string para evitar el error int64/JSON
    df = df.astype(str).replace(["nan", "None", "<NA>"], "")
    
    for col in df.columns:
        if any(k.lower() in col.lower() for k in COLUMNAS_DINERO):
            if "descrip" not in col.lower() and "moneda" not in col.lower() and "fuente" not in col.lower():
                df[col] = df[col].apply(formato_pesos)
    return df

# --- 4. MOTORES DE BÚSQUEDA Y CORTE (VERSIÓN CLÁSICA) ---

def encontrar_celda(df_raw, palabras_clave, min_col=0, min_row=0):
    """Busca coordenadas de una palabra clave"""
    try:
        zona = df_raw.iloc[min_row:, min_col:]
        for r_idx, row in zona.iterrows():
            for c_idx, val in enumerate(row):
                val_str = str(val).lower()
                for p in palabras_clave:
                    if p.lower() in val_str:
                        return r_idx, (c_idx + min_col)
        return None, None
    except:
        return None, None

def cortar_bloque_fijo(df_raw, fila, col, num_cols, filas_aprox=30):
    """
    Corta un bloque de tamaño fijo y elimina filas vacías.
    ESTA ES LA VERSIÓN QUE FUNCIONABA BIEN.
    No intenta adivinar dónde termina la tabla fila por fila.
    """
    try:
        # Headers
        headers = df_raw.iloc[fila, col : col + num_cols].astype(str).str.strip().tolist()
        headers = [f"C{i}" if h in ["nan", ""] else h for i,h in enumerate(headers)]
        
        start_row = fila + 1
        
        # Cortamos el bloque entero
        df = df_raw.iloc[start_row : start_row + filas_aprox, col : col + num_cols].copy()
        
        # Eliminamos filas que estén totalmente vacías (o casi vacías)
        # Filtramos si la columna 0 y la columna 1 están vacías a la vez
        df = df[~((df.iloc[:, 0].astype(str).isin(["nan", "", "None"])) & (df.iloc[:, 1].astype(str).isin(["nan", "", "None"])))]
        
        df.columns = headers
        return df
    except:
        return pd.DataFrame()

# --- 5. APP PRINCIPAL ---

lista_pestanas = ["Resumen Anual"] + MESES[6:] + MESES[:6]
hoja_seleccionada = st.sidebar.selectbox("📅 Selecciona Período:", lista_pestanas)

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)
except:
    st.error("Error conectando con Google Sheets.")
    st.stop()

# ==========================================
# RESUMEN ANUAL
# ==========================================
if hoja_seleccionada == "Resumen Anual":
    st.header("📊 Resumen Anual")

    # 1. GASTOS
    r, c = encontrar_celda(df_raw, ["Categoría", "Categoria"])
    if r is not None:
        st.subheader("📉 Evolución de Gastos")
        df = cortar_bloque_fijo(df_raw, r, c, 14, filas_aprox=25)
        st.dataframe(limpiar_y_formatear(df), hide_index=True)

    st.divider()

    # 2. SALDOS
    r, c = encontrar_celda(df_raw, ["Saldos Mensuales"])
    if r is not None:
        st.subheader("💰 Saldos Mensuales")
        # Solo 1 fila de datos
        df = cortar_bloque_fijo(df_raw, r + 1, c, 14, filas_aprox=1)
        st.dataframe(limpiar_y_formatear(df), hide_index=True)

    st.divider()

    c1, c2 = st.columns([1, 2])

    # 3. AHORROS (Búsqueda por ANCLA: 'Paypal')
    with c1:
        st.subheader("🏦 Mis Ahorros")
        r_dato, c_dato = encontrar_celda(df_raw, ["Paypal", "Eft. casa"])
        if r_dato is not None:
            # Header está 1 arriba
            df = cortar_bloque_fijo(df_raw, r_dato - 1, c_dato, 5, filas_aprox=6)
            st.dataframe(limpiar_y_formatear(df), hide_index=True)
        else:
            # Fallback
            r, c = encontrar_celda(df_raw, ["Fuente"])
            if r is not None:
                df = cortar_bloque_fijo(df_raw, r, c, 5, filas_aprox=6)
                st.dataframe(limpiar_y_formatear(df), hide_index=True)

    # 4. CAMBIO (Búsqueda por ANCLA: 'Cotizacion')
    with c2:
        st.subheader("🔄 Cambio de Dólares")
        r_dato, c_dato = encontrar_celda(df_raw, ["Cotizacion"]) 
        if r_dato is not None:
            # Header está 2 arriba (según tus tablas)
            df = cortar_bloque_fijo(df_raw, r_dato - 2, 0, 14, filas_aprox=6)
            st.dataframe(limpiar_y_formatear(df), hide_index=True)
        else:
            # Fallback
            r, c = encontrar_celda(df_raw, ["Dolares"])
            if r is not None:
                 df = cortar_bloque_fijo(df_raw, r - 1, 0, 14, filas_aprox=6)
                 st.dataframe(limpiar_y_formatear(df), hide_index=True)

# ==========================================
# MESES INDIVIDUALES (LÓGICA RESTAURADA)
# ==========================================
else:
    st.write(f"📂 Viendo mes de: **{hoja_seleccionada}**")

    # 1. BALANCE
    # Buscamos en la zona derecha (col 5+)
    r_bal, c_bal = encontrar_celda(df_raw, ["Gastos fijos"], min_col=5)
    balance = pd.DataFrame()
    if r_bal is not None:
        balance = cortar_bloque_fijo(df_raw, r_bal, c_bal, 3, filas_aprox=1)

    # 2. GASTOS
    # Buscamos en la zona izquierda (col 0)
    r_gastos, c_gastos = encontrar_celda(df_raw, ["Vencimiento", "Categoría"], min_col=0)
    gastos = pd.DataFrame()
    if r_gastos is not None:
        # Recuperamos las 40 filas por seguridad
        gastos = cortar_bloque_fijo(df_raw, r_gastos, c_gastos, 5, filas_aprox=40)

    # 3. INGRESOS
    # Buscamos "Fecha" OBLIGATORIAMENTE a la derecha (min_col=6) y abajo (min_row=3)
    r_ing, c_ing = encontrar_celda(df_raw, ["Fecha", "Descripcion"], min_col=6, min_row=3)
    ingresos = pd.DataFrame()
    if r_ing is not None:
        ingresos = cortar_bloque_fijo(df_raw, r_ing, c_ing, 6, filas_aprox=20)
    
    # VISUALIZACIÓN
    st.markdown("### 💰 Balance del Mes")
    if not balance.empty:
        c1, c2, c3 = st.columns(3)
        try:
            # Forzamos conversión a string de índices para evitar líos
            v1 = formato_pesos(balance.iloc[0, 0])
            v2 = formato_pesos(balance.iloc[0, 1])
            v3 = formato_pesos(balance.iloc[0, 2])
            c1.metric(balance.columns[0], v1)
            c2.metric(balance.columns[1], v2)
            c3.metric(balance.columns[2], v3)
        except: 
            st.warning("Error visualizando balance.")
    else: 
        st.warning("No se encontró tabla Balance.")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📉 Gastos")
        if not gastos.empty: 
            st.dataframe(limpiar_y_formatear(gastos), hide_index=True)
        else: 
            st.info("Sin gastos registrados.")
            
    with col2:
        st.subheader("📈 Ingresos")
        if not ingresos.empty: 
            st.dataframe(limpiar_y_formatear(ingresos), hide_index=True)
        else: 
            st.info("Sin ingresos registrados.")

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
    df = df.astype(str).replace(["nan", "None", "<NA>"], "-")
    for col in df.columns:
        if any(k.lower() in col.lower() for k in COLUMNAS_DINERO):
            if "descrip" not in col.lower() and "moneda" not in col.lower() and "fuente" not in col.lower():
                df[col] = df[col].apply(formato_pesos)
    return df

# --- 4. MOTORES DE BÚSQUEDA ---

def encontrar_celda(df_raw, palabras_clave, min_col=0, min_row=0):
    """Devuelve (fila, columna) de la primera celda que contenga la palabra."""
    try:
        zona = df_raw.iloc[min_row:, min_col:]
        for r_idx, row in zona.iterrows():
            for c_idx, val in enumerate(row):
                val_str = str(val).lower()
                for p in palabras_clave:
                    if p.lower() in val_str:
                        # Retornamos indices absolutos
                        return r_idx, (c_idx + min_col)
        return None, None
    except:
        return None, None

def cortar_tabla_inteligente(df_raw, fila, col, num_cols, filas_fijas=None):
    """
    Corta una tabla desde (fila, col).
    Si filas_fijas es None, corta hacia abajo hasta encontrar VACÍO.
    """
    try:
        # 1. Definir Headers
        headers = df_raw.iloc[fila, col : col + num_cols].astype(str).str.strip().tolist()
        headers = [f"C{i}" if h in ["nan", ""] else h for i,h in enumerate(headers)]
        
        start_row = fila + 1
        
        # 2. Definir Datos
        if filas_fijas:
            # Caso Saldo Mensual (solo 1 fila)
            df = df_raw.iloc[start_row : start_row + filas_fijas, col : col + num_cols].copy()
        else:
            # Caso Tablas Largas (Gastos, Ahorros, Ingresos)
            # Cortamos un pedazo grande y luego limpiamos
            df = df_raw.iloc[start_row:, col : col + num_cols].copy()
            
            # LÓGICA DE FRENO:
            # Si la Columna 0 (ej: Categoría o Fecha) está vacía, ahí termina la tabla.
            # Iteramos para encontrar el primer vacío y cortar ahí.
            ultimo_idx_valido = -1
            for i in range(len(df)):
                val_col0 = str(df.iloc[i, 0]).lower()
                # Si encontramos un vacio o un titulo de otra tabla, cortamos
                if val_col0 in ["nan", "none", "", "saldos mensuales", "cambio de dolares"]:
                    break
                ultimo_idx_valido = i
            
            # Recortamos hasta donde encontramos datos validos
            df = df.iloc[:ultimo_idx_valido+1]
            
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
# VISTA: RESUMEN ANUAL
# ==========================================
if hoja_seleccionada == "Resumen Anual":
    st.header("📊 Resumen Anual")

    # 1. EVOLUCIÓN GASTOS
    # Busca "Categoría" en col A.
    r, c = encontrar_celda(df_raw, ["Categoría", "Categoria"])
    if r is not None:
        st.subheader("📉 Evolución de Gastos")
        # Cortamos 14 columnas (Enero a Total)
        df = cortar_tabla_inteligente(df_raw, r, c, num_cols=14)
        st.dataframe(limpiar_y_formatear(df), hide_index=True)

    st.divider()

    # 2. SALDOS MENSUALES
    # Busca Titulo Verde "Saldos Mensuales". Header está +1 abajo.
    r, c = encontrar_celda(df_raw, ["Saldos Mensuales"])
    if r is not None:
        st.subheader("💰 Saldos Mensuales")
        df = cortar_tabla_inteligente(df_raw, r + 1, c, num_cols=14, filas_fijas=1)
        st.dataframe(limpiar_y_formatear(df), hide_index=True)

    st.divider()

    c1, c2 = st.columns([1, 2])

    # 3. MIS AHORROS
    with c1:
        st.subheader("🏦 Mis Ahorros")
        # Busca "Fuente" (Header) directamente.
        r, c = encontrar_celda(df_raw, ["Fuente"])
        if r is not None:
            df = cortar_tabla_inteligente(df_raw, r, c, num_cols=5)
            st.dataframe(limpiar_y_formatear(df), hide_index=True)
        else:
            st.info("No encontré tabla Ahorros (buscando 'Fuente').")

    # 4. CAMBIO DE DÓLARES
    with c2:
        st.subheader("🔄 Cambio de Dólares")
        # Busca "Dolares" (Etiqueta fila) y sube 1 para el Header (Meses)
        r_label, c_label = encontrar_celda(df_raw, ["Dolares"]) 
        if r_label is not None:
            # Header está 1 fila arriba
            df = cortar_tabla_inteligente(df_raw, r_label - 1, c_label, num_cols=14)
            st.dataframe(limpiar_y_formatear(df), hide_index=True)
        else:
            # Plan B: buscar titulo verde "Cambio de dolares" y bajar 1
            r_tit, c_tit = encontrar_celda(df_raw, ["Cambio de dolares"])
            if r_tit is not None:
                df = cortar_tabla_inteligente(df_raw, r_tit + 1, c_tit, num_cols=14)
                st.dataframe(limpiar_y_formatear(df), hide_index=True)
            else:
                st.info("No encontré tabla Cambio.")

# ==========================================
# VISTA: MESES INDIVIDUALES
# ==========================================
else:
    st.write(f"📂 Viendo mes de: **{hoja_seleccionada}**")

    # 1. BALANCE (KPIs)
    # Busca "Gastos fijos" en la zona de resumen (cols I en adelante)
    r_bal, c_bal = encontrar_celda(df_raw, ["Gastos fijos"], min_col=5)
    balance = pd.DataFrame()
    if r_bal is not None:
        balance = cortar_tabla_inteligente(df_raw, r_bal, c_bal, num_cols=3, filas_fijas=1)

    # 2. GASTOS (Izquierda)
    # Busca "Vencimiento" o "Categoría" en la zona izquierda (col 0)
    r_gastos, c_gastos = encontrar_celda(df_raw, ["Vencimiento", "Categoría"], min_col=0)
    gastos = pd.DataFrame()
    if r_gastos is not None:
        gastos = cortar_tabla_inteligente(df_raw, r_gastos, c_gastos, num_cols=5)

    # 3. INGRESOS (Derecha) - AQUÍ ESTABA EL ERROR DE LOS MESES
    # Busca "Fecha" o "Descripcion", PERO OBLIGATORIAMENTE a la derecha (min_col=6)
    # y bajando unas filas (min_row=4) para no confundirse con otros headers.
    r_ing, c_ing = encontrar_celda(df_raw, ["Fecha", "Descripcion"], min_col=6, min_row=4)
    
    ingresos = pd.DataFrame()
    if r_ing is not None:
        # Encontramos el header, cortamos hacia abajo
        ingresos = cortar_tabla_inteligente(df_raw, r_ing, c_ing, num_cols=6)
    
    # VISUALIZACIÓN
    st.markdown("### 💰 Balance del Mes")
    if not balance.empty:
        c1, c2, c3 = st.columns(3)
        try:
            v1 = formato_pesos(balance.iloc[0, 0])
            v2 = formato_pesos(balance.iloc[0, 1])
            v3 = formato_pesos(balance.iloc[0, 2])
            c1.metric(balance.columns[0], v1)
            c2.metric(balance.columns[1], v2)
            c3.metric(balance.columns[2], v3)
        except: st.warning("Formato balance inesperado")
    else: 
        st.warning("No se encontró tabla Balance.")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📉 Gastos")
        if not gastos.empty: st.dataframe(limpiar_y_formatear(gastos), hide_index=True)
        else: st.info("Sin gastos.")
    with col2:
        st.subheader("📈 Ingresos")
        if not ingresos.empty: st.dataframe(limpiar_y_formatear(ingresos), hide_index=True)
        else: st.info("Sin ingresos (buscando 'Fecha' en cols I-N).")

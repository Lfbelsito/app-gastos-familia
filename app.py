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
    # Limpieza general
    df = df.astype(str).replace(["nan", "None", "<NA>"], "")
    
    # Formato moneda
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
                        return r_idx, (c_idx + min_col)
        return None, None
    except:
        return None, None

def cortar_tabla_segura(df_raw, fila, col, num_cols, filas_aprox=20):
    """
    Corta un bloque fijo (ej: 20 filas) y luego elimina las vacías.
    Es más seguro que intentar adivinar dónde termina.
    """
    try:
        # Headers
        headers = df_raw.iloc[fila, col : col + num_cols].astype(str).str.strip().tolist()
        headers = [f"C{i}" if h in ["nan", ""] else h for i,h in enumerate(headers)]
        
        start_row = fila + 1
        
        # Cortamos un bloque generoso
        df = df_raw.iloc[start_row : start_row + filas_aprox, col : col + num_cols].copy()
        
        # ELIMINAR FILAS VACÍAS
        # Si la primera columna (ej: Categoría o Fecha) está vacía, borramos esa fila
        df = df[df.iloc[:, 0].astype(str).ne("nan") & df.iloc[:, 0].astype(str).ne("")]
        
        # FILTRO EXTRA: Si encontramos un título de otra tabla (ej: "Saldos"), cortamos ahí
        indices_a_borrar = []
        for idx, row in df.iterrows():
            val = str(row.iloc[0]).lower()
            if "saldos mensuales" in val or "cambio de dolares" in val or "ahorro" in val:
                # Marcamos de aquí en adelante para borrar
                indices_a_borrar.append(idx)
        
        if indices_a_borrar:
            # Cortamos hasta el primer intruso encontrado
            primer_intruso = indices_a_borrar[0]
            df = df.loc[:primer_intruso-1]

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
    st.error("Error conectando con Google Sheets. Espera unos segundos y recarga.")
    st.stop()

# ==========================================
# VISTA: RESUMEN ANUAL
# ==========================================
if hoja_seleccionada == "Resumen Anual":
    st.header("📊 Resumen Anual")

    # 1. EVOLUCIÓN GASTOS
    r, c = encontrar_celda(df_raw, ["Categoría", "Categoria"])
    if r is not None:
        st.subheader("📉 Evolución de Gastos")
        # Cortamos 20 filas aprox (suficiente para categorías)
        df = cortar_tabla_segura(df_raw, r, c, num_cols=14, filas_aprox=25)
        st.dataframe(limpiar_y_formatear(df), hide_index=True)

    st.divider()

    # 2. SALDOS MENSUALES
    # Busca Titulo Verde "Saldos Mensuales". Header está +1 abajo.
    r, c = encontrar_celda(df_raw, ["Saldos Mensuales"])
    if r is not None:
        st.subheader("💰 Saldos Mensuales")
        # Solo necesitamos 1 fila de datos
        df = cortar_tabla_segura(df_raw, r + 1, c, num_cols=14, filas_aprox=1)
        st.dataframe(limpiar_y_formatear(df), hide_index=True)

    st.divider()

    c1, c2 = st.columns([1, 2])

    # 3. MIS AHORROS
    with c1:
        st.subheader("🏦 Mis Ahorros")
        # ESTRATEGIA ANCLA: Buscar "Paypal" (Dato seguro)
        r_dato, c_dato = encontrar_celda(df_raw, ["Paypal", "Eft. casa"])
        if r_dato is not None:
            # Si encontré el dato, el header está 1 fila arriba
            df = cortar_tabla_segura(df_raw, r_dato - 1, c_dato, num_cols=5, filas_aprox=5)
            st.dataframe(limpiar_y_formatear(df), hide_index=True)
        else:
            # Plan B: buscar Header "Fuente"
            r, c = encontrar_celda(df_raw, ["Fuente"])
            if r is not None:
                df = cortar_tabla_segura(df_raw, r, c, num_cols=5, filas_aprox=5)
                st.dataframe(limpiar_y_formatear(df), hide_index=True)

    # 4. CAMBIO DE DÓLARES
    with c2:
        st.subheader("🔄 Cambio de Dólares")
        # ESTRATEGIA ANCLA: Buscar "Cotizacion" (Dato seguro)
        r_dato, c_dato = encontrar_celda(df_raw, ["Cotizacion"]) 
        if r_dato is not None:
            # En tu tabla: Header (Meses) -> Dolares -> Cotizacion
            # Así que el header está 2 filas arriba de "Cotizacion"
            df = cortar_tabla_segura(df_raw, r_dato - 2, 0, num_cols=14, filas_aprox=4)
            st.dataframe(limpiar_y_formatear(df), hide_index=True)
        else:
            # Plan B: Buscar "Dolares" (etiqueta) -> Header 1 arriba
            r_dol, c_dol = encontrar_celda(df_raw, ["Dolares"])
            if r_dol is not None:
                 df = cortar_tabla_segura(df_raw, r_dol - 1, 0, num_cols=14, filas_aprox=4)
                 st.dataframe(limpiar_y_formatear(df), hide_index=True)
            else:
                 st.info("No se encontró tabla Cambio.")

# ==========================================
# VISTA: MESES INDIVIDUALES
# ==========================================
else:
    st.write(f"📂 Viendo mes de: **{hoja_seleccionada}**")

    # 1. BALANCE (KPIs)
    r_bal, c_bal = encontrar_celda(df_raw, ["Gastos fijos"], min_col=5)
    balance = pd.DataFrame()
    if r_bal is not None:
        balance = cortar_tabla_segura(df_raw, r_bal, c_bal, num_cols=3, filas_aprox=1)

    # 2. GASTOS (Izquierda)
    # Busca "Vencimiento" o "Categoría" en la izquierda (min_col=0)
    r_gastos, c_gastos = encontrar_celda(df_raw, ["Vencimiento", "Categoría"], min_col=0)
    gastos = pd.DataFrame()
    if r_gastos is not None:
        # Leemos 30 filas y limpiamos vacíos. Esto recupera la funcionalidad que se perdió.
        gastos = cortar_tabla_segura(df_raw, r_gastos, c_gastos, num_cols=5, filas_aprox=30)

    # 3. INGRESOS (Derecha)
    # Busca "Fecha" o "Descripcion" a la derecha (min_col=6)
    r_ing, c_ing = encontrar_celda(df_raw, ["Fecha", "Descripcion"], min_col=6, min_row=3)
    ingresos = pd.DataFrame()
    if r_ing is not None:
        ingresos = cortar_tabla_segura(df_raw, r_ing, c_ing, num_cols=6, filas_aprox=20)
    
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
        else: st.info("Sin ingresos.")

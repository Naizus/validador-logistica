import streamlit as st
import pandas as pd
import os
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Validador CDMA", layout="wide", page_icon="🚚")

PATH_MAESTRO = "data/maestro.csv"

def obtener_letra(fecha):
    if pd.isna(fecha): return "?"
    # 0=L, 1=M, 2=X, 3=J, 4=V, 5=S, 6=D
    mapa = {0: 'L', 1: 'M', 2: 'X', 3: 'J', 4: 'V', 5: 'S', 6: 'D'}
    return mapa[fecha.weekday()]

# --- PANEL ADMIN PARA MODIFICAR MAESTRO ---
with st.sidebar.expander("🔐 Panel de Control Maestro"):
    clave = st.text_input("Ingrese Clave Admin", type="password")
    if clave == "CDMA26":
        st.success("Acceso Permitido")
        if os.path.exists(PATH_MAESTRO):
            df_m = pd.read_csv(PATH_MAESTRO, sep=';', encoding='latin-1')
            id_t = st.number_input("Buscar ID Tienda (Pto Op)", min_value=0, step=1)
            
            if id_t in df_m['Pto Op'].values:
                idx = df_m[df_m['Pto Op'] == id_t].index[0]
                st.info(f"Tienda: {df_m.at[idx, 'Tienda']}")
                
                nuevo_ent = st.text_input("Modificar DIA DE ENTREGA", value=str(df_m.at[idx, 'DIA DE ENTREGA']))
                
                if st.button("💾 Actualizar Maestro"):
                    df_m.at[idx, 'DIA DE ENTREGA'] = nuevo_ent
                    df_m.to_csv(PATH_MAESTRO, sep=';', index=False, encoding='latin-1')
                    st.toast("✅ Cambios guardados!")
    elif clave:
        st.error("Clave incorrecta")

# --- FLUJO PRINCIPAL ---
st.title("🚚 Validación de Entrega")

if not os.path.exists(PATH_MAESTRO):
    st.error("No se encontró 'data/maestro.csv'. Verifique la ruta.")
    st.stop()

archivo = st.file_uploader("Subir Planning (Excel o CSV)", type=['xlsx', 'csv'])

if archivo:
    try:
        # 1. Cargar datos
        df_maestro = pd.read_csv(PATH_MAESTRO, sep=';', encoding='latin-1')
        
        if archivo.name.endswith(('xlsx', 'xls')):
            df_plan = pd.read_excel(archivo)
        else:
            df_plan = pd.read_csv(archivo, sep=None, engine='python', encoding='latin-1')
        
        # 2. Obtener el día del planning (Letra)
        # Convertimos la columna FECHA a formato fecha
        df_plan['FECHA_DT'] = pd.to_datetime(df_plan['FECHA'], errors='coerce')
        # Tomamos la letra del primer registro del archivo
        letra_dia_archivo = obtener_letra(df_plan['FECHA_DT'].iloc[0])
        
        # 3. Cruzar con Maestro
        df_res = pd.merge(df_plan, df_maestro[['Pto Op', 'DIA DE ENTREGA']], 
                          left_on='TIENDA', right_on='Pto Op', how='left')

        # 4. Validar contra columna DIA DE ENTREGA
        def validar_entrega(row):
            if pd.isna(row['DIA DE ENTREGA']):
                return "No corresponde"
            
            # Limpiar el texto del maestro (quitar comas y espacios)
            maestro_ent = str(row['DIA DE ENTREGA']).upper().replace(" ", "").replace(",", "")
            
            if letra_dia_archivo in maestro_ent:
                return "Corresponde"
            else:
                return "No corresponde"

        df_res['RESULTADO'] = df_res.apply(validar_entrega, axis=1)

        # 5. Mostrar Tabla
        st.subheader(f"Día del Planning detectado: {letra_dia_archivo}")
        
        def resaltar_resultado(val):
            color = '#c6efce' if val == "Corresponde" else '#ffc7ce'
            texto = '#006100' if val == "Corresponde" else '#9c0006'
            return f'background-color: {color}; color: {texto}; font-weight: bold'

        columnas_finales = ['RESULTADO', 'TIENDA', 'NOMBRE_TIENDA', 'DIA DE ENTREGA']
        st.dataframe(df_res[columnas_finales].style.applymap(resaltar_resultado, subset=['RESULTADO']), use_container_width=True)

    except Exception as e:
        st.error(f"Error al procesar: {e}")
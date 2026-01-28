import streamlit as st
import pandas as pd
import os
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión CDMA", layout="wide")
PATH_MAESTRO = "data/maestro.csv"

def obtener_letra(fecha):
    if pd.isna(fecha): return "?"
    mapa = {0: 'L', 1: 'M', 2: 'X', 3: 'J', 4: 'V', 5: 'S', 6: 'D'}
    return mapa[fecha.weekday()]

# --- LÓGICA DE ADMIN (Clave: CDMA26) ---
if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False

with st.sidebar:
    st.title("⚙️ Administración")
    if not st.session_state.admin_auth:
        clave = st.text_input("Clave de Acceso", type="password")
        if clave == "CDMA26":
            st.session_state.admin_auth = True
            st.rerun()
    else:
        if st.button("🔓 Cerrar Sesión Admin"):
            st.session_state.admin_auth = False
            st.rerun()
        
        st.markdown("---")
        opcion_admin = st.radio("Acción:", ["Modificar Tienda", "Añadir Tienda Nueva"])
        
        if os.path.exists(PATH_MAESTRO):
            df_m = pd.read_csv(PATH_MAESTRO, sep=';', encoding='latin-1')
            
            if opcion_admin == "Modificar Tienda":
                id_t = st.number_input("ID Tienda (Pto Op)", min_value=0, step=1)
                if id_t in df_m['Pto Op'].values:
                    idx = df_m[df_m['Pto Op'] == id_t].index[0]
                    st.write(f"📍 **{df_m.at[idx, 'Tienda']}**")
                    nuevo_ent = st.text_input("Días de Entrega", value=str(df_m.at[idx, 'DIA DE ENTREGA']))
                    if st.button("Guardar Cambios"):
                        df_m.at[idx, 'DIA DE ENTREGA'] = nuevo_ent
                        df_m.to_csv(PATH_MAESTRO, sep=';', index=False, encoding='latin-1')
                        st.success("Actualizado")
                else:
                    st.warning("ID no encontrado")

            else: # Añadir Tienda Nueva
                new_id = st.number_input("Nuevo Pto Op", min_value=1)
                new_nom = st.text_input("Nombre Completo de Tienda")
                new_zona = st.text_input("Zona Geográfica")
                new_dias = st.text_input("Días de Entrega (Ej: LXV)")
                
                if st.button("Registrar Tienda"):
                    if new_id in df_m['Pto Op'].values:
                        st.error("El ID ya existe.")
                    else:
                        nueva_fila = pd.DataFrame([{'CD': 'Malvinas', 'Pto Op': new_id, 'Tienda': new_nom, 'Formato': 'Express', 'Zona Geografica': new_zona, 'DIA DE ENTREGA': new_dias}])
                        df_m = pd.concat([df_m, nueva_fila], ignore_index=True)
                        df_m.to_csv(PATH_MAESTRO, sep=';', index=False, encoding='latin-1')
                        st.success("Tienda Añadida")

# --- APP PRINCIPAL ---
st.title("🚚 Validador de Planning CDMA")

archivo = st.file_uploader("Subir Planning", type=['xlsx', 'csv'])

if archivo:
    try:
        df_maestro = pd.read_csv(PATH_MAESTRO, sep=';', encoding='latin-1')
        df_plan = pd.read_excel(archivo) if archivo.name.endswith('xlsx') else pd.read_csv(archivo, sep=None, engine='python', encoding='latin-1')
        
        df_plan['FECHA_DT'] = pd.to_datetime(df_plan['FECHA'], errors='coerce')
        fecha_ref = df_plan['FECHA_DT'].iloc[0]
        letra_dia = obtener_letra(fecha_ref)
        
        # 1. Procesar tiendas que ESTÁN en el planning
        df_res = pd.merge(df_plan, df_maestro[['Pto Op', 'Tienda', 'DIA DE ENTREGA', 'Zona Geografica']], 
                          left_on='TIENDA', right_on='Pto Op', how='left')

        def validar_detalle(row):
            if pd.isna(row['DIA DE ENTREGA']): return "No corresponde"
            m_ent = str(row['DIA DE ENTREGA']).upper()
            if letra_dia in ['V', 'S']:
                if letra_dia in m_ent and 'L' in m_ent: return f"Corresponde ({'Viernes' if letra_dia=='V' else 'Sábado'} y Lunes)"
                if letra_dia in m_ent: return f"Corresponde ({'Viernes' if letra_dia=='V' else 'Sábado'})"
                if 'L' in m_ent: return "Corresponde (Lunes)"
                if letra_dia == 'V' and 'S' in m_ent: return "Corresponde (Sábado)"
            else:
                if letra_dia in m_ent: return "Corresponde"
            return "No corresponde"

        df_res['RESULTADO'] = df_res.apply(validar_detalle, axis=1)

        # 2. Identificar tiendas del Maestro que DEBERÍAN estar pero NO fueron planificadas
        dias_busqueda = [letra_dia]
        if letra_dia == 'V': dias_busqueda.extend(['S', 'L'])
        if letra_dia == 'S': dias_busqueda.append('L')

        def aplica_dia(dias_maestro):
            return any(d in str(dias_maestro).upper() for d in dias_busqueda)

        tiendas_deberian = df_maestro[df_maestro['DIA DE ENTREGA'].apply(aplica_dia)]
        tiendas_no_planificadas = tiendas_deberian[~tiendas_deberian['Pto Op'].isin(df_plan['TIENDA'])]

        # Formatear para unir
        df_np = tiendas_no_planificadas[['Pto Op', 'Tienda', 'Zona Geografica', 'DIA DE ENTREGA']].copy()
        df_np = df_np.rename(columns={'Pto Op': 'TIENDA', 'Tienda': 'NOMBRE_TIENDA'})
        df_np['RESULTADO'] = "No Planificado"

        # Unir ambos universos
        cols_finales = ['RESULTADO', 'TIENDA', 'NOMBRE_TIENDA', 'Zona Geografica', 'DIA DE ENTREGA']
        df_final = pd.concat([df_res[cols_finales], df_np], ignore_index=True)

        # UI
        st.info(f"📅 **Día del Planning**: {letra_dia}")
        
        def color_val(val):
            if "Corresponde" in val: return 'background-color: #c6efce; color: #006100; font-weight: bold'
            if val == "No Planificado": return 'background-color: #ffe5b4; color: #cc7a00; font-weight: bold'
            return 'background-color: #ffc7ce; color: #9c0006'

        st.dataframe(df_final.style.applymap(color_val, subset=['RESULTADO']), use_container_width=True)

        # BOTÓN EXCEL
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='Validacion')
        st.download_button(label="📥 Exportar Reporte a Excel", data=output.getvalue(), file_name=f"Validacion_{letra_dia}.xlsx")

    except Exception as e:
        st.error(f"Error: {e}")
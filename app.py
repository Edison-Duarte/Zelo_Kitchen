import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Zelo Kitchen - Inspeção", page_icon="🍳", layout="wide")

fuso_br = pytz.timezone('America/Sao_Paulo')
def obter_agora_br():
    return datetime.now(fuso_br)

# --- CONEXÃO AUTOMÁTICA ---
# O Streamlit vai ler os Secrets [connections.gsheets] sozinho
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro na conexão: {e}")

def carregar_dados():
    try:
        # Ele lê a planilha configurada no campo 'spreadsheet' dos Secrets
        return conn.read(ttl=0)
    except Exception as e:
        st.error(f"Erro ao ler dados: {e}")
        return pd.DataFrame()

# --- INTERFACE ---
st.title("🍳 Sistema de Inspeção Zelo Kitchen")

tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico"])

with tab1:
    if 'ultima_inspecao' in st.session_state and st.session_state.ultima_inspecao:
        st.success("✅ Inspeção guardada!")
        if st.button("🔄 Nova Inspeção"):
            st.session_state.ultima_inspecao = None
            st.rerun()
    else:
        with st.expander("Identificação", expanded=True):
            nome = st.text_input("Nome do Inspetor:")
            setor = st.selectbox("Setor:", ["Selecione...", "Espaço Café", "Cozinha", "Mirante", "Refeitório"])

        if setor != "Selecione...":
            # Exemplo simplificado de itens (ajuste conforme sua lista)
            itens = ["Equipamento 1", "Equipamento 2"] 
            respostas = []
            for item in itens:
                st.write(f"**{item}**")
                respostas.append({"Equipamento": item, "Status": st.radio(f"Estado {item}", ["OK", "NÃO"], horizontal=True)})

            if st.button("🚀 SALVAR", type="primary"):
                with st.spinner("Salvando..."):
                    df_atual = carregar_dados()
                    novo_dado = pd.DataFrame([{"Data": obter_agora_br(), "Nome": nome, "Setor": setor}])
                    df_final = pd.concat([df_atual, novo_dado], ignore_index=True)
                    conn.update(data=df_final)
                    st.session_state.ultima_inspecao = True
                    st.rerun()

with tab2:
    st.dataframe(carregar_dados(), use_container_width=True)

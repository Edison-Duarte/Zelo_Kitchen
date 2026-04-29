import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import urllib.parse

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Zelo Kitchen - Inspeção", page_icon="🍳", layout="wide")

fuso_br = pytz.timezone('America/Sao_Paulo')
def obter_agora_br():
    return datetime.now(fuso_br)

# --- CONEXÃO ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro na conexão: {e}")

def carregar_dados():
    try:
        return conn.read(ttl=0)
    except Exception as e:
        # Se a planilha estiver vazia, retorna um DataFrame com as colunas certas
        return pd.DataFrame(columns=["Data/Hora", "Funcionário", "Setor", "Equipamento", "Status", "Falhas"])

# --- ESTRUTURA DO CHECKLIST ---
setores = ["Espaço Café", "Cozinha", "Mirante", "Refeitório"]
itens_setores = {
    "Espaço Café": ["Estufa quente", "Estufa fria", "Geladeiras balcão", "Frigobares", "Máquina de café expresso"],
    "Cozinha": ["Geladeiras Bacio di Latte", "Geladeiras Resfriados", "Câmaras Frias", "Freezers Horizontais", "Fornos", "Fogões", "Fritadeiras", "Chapas", "Geladeiras Balcões", "Coifas", "Pista Fria"],
    "Mirante": ["Freezer Sorvete Dona Mazza", "Adega Vinhos", "Geladeiras", "Geladeiras Balcões", "Lava Louças", "Coifas", "Pista Fria", "Elevador Monta Carga", "Freezer Horizontal", "Churrasqueira", "Forno a Lenha"],
    "Refeitório": ["Lava Louças", "Geladeira Resfriados", "Rechaud"]
}

st.title("🍳 Sistema de Inspeção Zelo Kitchen")

tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico"])

with tab1:
    if 'sucesso' in st.session_state and st.session_state.sucesso:
        st.success("✅ Inspeção salva com sucesso na planilha!")
        if st.button("Realizar Nova Inspeção"):
            st.session_state.sucesso = False
            st.rerun()
    else:
        with st.expander("📌 Identificação", expanded=True):
            col1, col2 = st.columns(2)
            nome_inspetor = col1.text_input("Seu Nome:")
            setor_selecionado = col2.selectbox("Setor a Inspecionar:", ["Selecione..."] + setores)

        if setor_selecionado != "Selecione...":
            st.info(f"📋 Itens do Setor: **{setor_selecionado}**")
            respostas = []
            
            # Monta o checklist visualmente
            for item in itens_setores[setor_selecionado]:
                with st.container(border=True):
                    st.write(f"**{item}**")
                    c1, c2, c3 = st.columns(3)
                    h = c1.radio(f"Higiene", ["OK", "NÃO"], key=f"h_{item}", horizontal=True)
                    f = c2.radio(f"Funcionamento", ["OK", "NÃO"], key=f"f_{item}", horizontal=True)
                    e = c3.radio(f"Estado Geral", ["OK", "NÃO"], key=f"e_{item}", horizontal=True)
                    respostas.append({"Equipamento": item, "H": h, "F": f, "E": e})

            if st.button("🚀 FINALIZAR E SALVAR", type="primary", use_container_width=True):
                if not nome_inspetor:
                    st.error("Por favor, digite seu nome antes de salvar.")
                else:
                    with st.spinner("Salvando na planilha..."):
                        agora = obter_agora_br().strftime("%d/%m/%Y %H:%M")
                        novas_entradas = []
                        
                        for r in respostas:
                            falhas = []
                            if r["H"] == "NÃO": falhas.append("Higiene")
                            if r["F"] == "NÃO": falhas.append("Funcionamento")
                            if r["E"] == "NÃO": falhas.append("Estado Geral")
                            
                            novas_entradas.append({
                                "Data/Hora": agora,
                                "Funcionário": nome_inspetor,
                                "Setor": setor_selecionado,
                                "Equipamento": r["Equipamento"],
                                "Status": "✅ OK" if not falhas else "❌ FALHA",
                                "Falhas": ", ".join(falhas) if falhas else "Nenhuma"
                            })
                        
                        try:
                            df_atual = carregar_dados()
                            df_novo = pd.DataFrame(novas_entradas)
                            df_final = pd.concat([df_atual, df_novo], ignore_index=True)
                            
                            conn.update(data=df_final)
                            st.session_state.sucesso = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")

with tab2:
    st.subheader("📜 Histórico de Registros")
    dados_hist = carregar_dados()
    if not dados_hist.empty:
        st.dataframe(dados_hist, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum registro encontrado.")

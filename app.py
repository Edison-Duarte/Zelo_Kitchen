import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Zelo Kitchen - Inspeção", page_icon="🍳", layout="wide")

# Fuso horário para garantir data/hora correta do Brasil
fuso_br = pytz.timezone('America/Sao_Paulo')
def obter_agora_br():
    return datetime.now(fuso_br)

# --- CONEXÃO COM GOOGLE SHEETS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro na conexão com o banco de dados: {e}")

def carregar_dados():
    try:
        df = conn.read(ttl=0)
        # Converte a coluna Data/Hora para datetime real para os filtros funcionarem
        if not df.empty and "Data/Hora" in df.columns:
            df["Data/Hora"] = pd.to_datetime(df["Data/Hora"], dayfirst=True)
        return df
    except Exception as e:
        # Retorna estrutura vazia caso a planilha não exista ou esteja inacessível
        return pd.DataFrame(columns=["Data/Hora", "Funcionário", "Setor", "Equipamento", "Status", "Falhas", "Descrição do Problema"])

# --- ESTRUTURA DO CHECKLIST ---
setores_lista = ["Espaço Café", "Cozinha", "Mirante", "Refeitório"]
itens_setores = {
    "Espaço Café": ["Estufa quente", "Estufa fria", "Geladeiras balcão", "Frigobares", "Máquina de café expresso"],
    "Cozinha": ["Geladeiras Bacio di Latte", "Geladeiras Resfriados", "Câmaras Frias", "Freezers Horizontais", "Fornos", "Fogões", "Fritadeiras", "Chapas", "Geladeiras Balcões", "Coifas", "Pista Fria"],
    "Mirante": ["Freezer Sorvete Dona Mazza", "Adega Vinhos", "Geladeiras", "Geladeiras Balcões", "Lava Louças", "Coifas", "Pista Fria", "Elevador Monta Carga", "Freezer Horizontal", "Churrasqueira", "Forno a Lenha"],
    "Refeitório": ["Lava Louças", "Geladeira Resfriados", "Rechaud"]
}

st.title("🍳 Sistema de Inspeção Zelo Kitchen")

tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico"])

# --- ABA 1: NOVA INSPEÇÃO ---
with tab1:
    if 'sucesso' in st.session_state and st.session_state.sucesso:
        st.success("✅ Inspeção salva com sucesso na nuvem!")
        if st.button("Realizar Nova Inspeção"):
            st.session_state.sucesso = False
            st.rerun()
    else:
        with st.expander("📌 Identificação do Inspetor", expanded=True):
            col1, col2 = st.columns(2)
            nome_inspetor = col1.text_input("Seu Nome:")
            setor_selecionado = col2.selectbox("Setor a Inspecionar:", ["Selecione..."] + setores_lista)

        if setor_selecionado != "Selecione...":
            st.info(f"📋 Verificando Itens: **{setor_selecionado}**")
            respostas = []
            
            for item in itens_setores[setor_selecionado]:
                with st.container(border=True):
                    st.write(f"**{item}**")
                    c1, c2, c3 = st.columns(3)
                    h = c1.radio(f"Higiene", ["OK", "NÃO"], key=f"h_{item}", horizontal=True)
                    f = c2.radio(f"Funcionamento", ["OK", "NÃO"], key=f"f_{item}", horizontal=True)
                    e = c3.radio(f"Estado Geral", ["OK", "NÃO"], key=f"e_{item}", horizontal=True)
                    
                    # Abre caixa de descrição se algum campo for "NÃO"
                    obs = ""
                    if h == "NÃO" or f == "NÃO" or e == "NÃO":
                        obs = st.text_area(f"Descreva o problema no(a) {item}:", key=f"obs_{item}", placeholder="Relate o defeito ou sujeira encontrada...")
                    
                    respostas.append({"Equipamento": item, "H": h, "F": f, "E": e, "Detalhes": obs})

            if st.button("🚀 FINALIZAR E SALVAR", type="primary", use_container_width=True):
                if not nome_inspetor:
                    st.error("Por favor, digite seu nome antes de salvar.")
                else:
                    with st.spinner("Enviando dados para o Google Sheets..."):
                        agora = obter_agora_br().strftime("%d/%m/%Y %H:%M")
                        novas_entradas = []
                        
                        for r in respostas:
                            falhas_detectadas = [n for n, v in zip(["Higiene", "Funcionamento", "Estado"], [r["H"], r["F"], r["E"]]) if v == "NÃO"]
                            
                            novas_entradas.append({
                                "Data/Hora": agora,
                                "Funcionário": nome_inspetor,
                                "Setor": setor_selecionado,
                                "Equipamento": r["Equipamento"],
                                "Status": "❌ FALHA" if falhas_detectadas else "✅ OK",
                                "Falhas": ", ".join(falhas_detectadas) if falhas_detectadas else "Nenhuma",
                                "Descrição do Problema": r["Detalhes"]
                            })
                        
                        try:
                            df_atual = carregar_dados()
                            df_novo = pd.DataFrame(novas_entradas)
                            df_final = pd.concat([df_atual, df_novo], ignore_index=True)
                            
                            conn.update(data=df_final)
                            st.session_state.sucesso = True
                            st.rerun()
                        except Exception as e:
                            # Tratamento para erro de resposta falso (Response 200)
                            if "200" in str(e):
                                st.session_state.sucesso = True
                                st.rerun()
                            else:
                                st.error(f"Erro ao salvar: {e}")

# --- ABA 2: HISTÓRICO COM FILTROS ---
with tab2:
    st.subheader("📜 Filtros e Registros")
    df_hist = carregar_dados()
    
    if not df_hist.empty:
        # Bloco de Filtros
        with st.expander("🔍 Opções de Filtro", expanded=True):
            col_d1, col_d2 = st.columns(2)
            data_min = df_hist["Data/Hora"].min().date()
            data_max = df_hist["Data/Hora"].max

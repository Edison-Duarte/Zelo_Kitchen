import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import urllib.parse

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Zelo Kitchen - Inspeção", page_icon="🍳", layout="wide")

# Fuso horário para o Brasil
fuso_br = pytz.timezone('America/Sao_Paulo')

def obter_agora_br():
    return datetime.now(fuso_br)

# --- LIGAÇÃO AO GOOGLE SHEETS COM LIMPEZA DE CHAVE ---
def conectar_planilha():
    try:
        # 1. Obter segredos como dicionário
        secrets_dict = st.secrets["connections"]["gsheets"].to_dict()
        
        # 2. Limpeza profunda da private_key para evitar erro de PEM
        if "private_key" in secrets_dict:
            key = secrets_dict["private_key"]
            # Remove aspas extras, espaços e trata quebras de linha
            key = key.strip().replace("\\n", "\n")
            if key.startswith('"') and key.endswith('"'):
                key = key[1:-1]
            secrets_dict["private_key"] = key
        
        # 3. Criar conexão usando os dados limpos
        conn = st.connection(
            "gsheets", 
            type=GSheetsConnection, 
            service_account_info=secrets_dict
        )
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        return conn, url
    except Exception as e:
        st.error(f"Erro na configuração de acesso: {e}")
        return None, None

conn, url_planilha = conectar_planilha()

def carregar_dados():
    if conn and url_planilha:
        try:
            return conn.read(spreadsheet=url_planilha, ttl=0)
        except Exception as e:
            st.error(f"Erro ao ler dados: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- ESTADO DA SESSÃO ---
if 'ultima_inspecao' not in st.session_state:
    st.session_state.ultima_inspecao = None

# --- ESTRUTURA DE DADOS ---
setores = ["Espaço Café", "Cozinha", "Mirante", "Refeitório"]
itens_setores = {
    "Espaço Café": ["Estufa quente", "Estufa fria", "Geladeiras balcão", "Frigobares", "Máquina de café expresso"],
    "Cozinha": ["Geladeiras Bacio di Latte", "Geladeiras Resfriados", "Câmaras Frias", "Freezers Horizontais", "Fornos", "Fogões", "Fritadeiras", "Chapas", "Geladeiras Balcões", "Coifas", "Pista Fria"],
    "Mirante": ["Freezer Sorvete Dona Mazza", "Adega Vinhos", "Geladeiras", "Geladeiras Balcões", "Lava Louças", "Coifas", "Pista Fria", "Elevador Monta Carga", "Freezer Horizontal", "Churrasqueira", "Forno a Lenha"],
    "Refeitório": ["Lava Louças", "Geladeira Resfriados", "Rechaud"]
}

# --- INTERFACE ---
st.title("🍳 Sistema de Inspeção Zelo Kitchen")

tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico"])

with tab1:
    if st.session_state.ultima_inspecao:
        dados = st.session_state.ultima_inspecao
        st.success(f"✅ Inspeção de {dados['funcionario']} guardada!")
        
        if dados["falhas"]:
            texto_falha = f"🚨 *FALHAS DETECTADAS - {dados['setor']}*\n\n"
            for f in dados["falhas"]:
                texto_falha += f"• {f['Equipamento']}: {f['Falha']}\n"
            
            st.warning("Falhas detetadas! Comunique via:")
            c1, c2 = st.columns(2)
            c1.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(texto_falha)}" target="_blank"><button style="width:100%; background-color:#25d366; color:white; border:none; padding:12px; border-radius:10px;">🟢 WhatsApp</button></a>', unsafe_allow_html=True)
            c2.markdown(f'<a href="mailto:?subject=Falha Kitchen&body={urllib.parse.quote(texto_falha)}"><button style="width:100%; height:44px; border-radius:10px;">📧 E-mail</button></a>', unsafe_allow_html=True)
        
        if st.button("🔄 Nova Inspeção"):
            st.session_state.ultima_inspecao = None
            st.rerun()
    else:
        with st.expander("Identificação", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome do Inspetor:")
            setor = col2.selectbox("Setor:", ["Selecione..."] + setores)

        if setor != "Selecione...":
            respostas = []
            for item in itens_setores[setor]:
                with st.container(border=True):
                    st.write(f"**{item}**")
                    c1, c2, c3 = st.columns(3)
                    h = c1.radio(f"Higiene", ["OK", "NÃO"], key=f"h_{item}", horizontal=True)
                    f = c2.radio(f"Funcionamento", ["OK", "NÃO"], key=f"f_{item}", horizontal=True)
                    e = c3.radio(f"Estado", ["OK", "NÃO"], key=f"e_{item}", horizontal=True)
                    respostas.append({"Equipamento": item, "H": h, "F": f, "E": e})

            if st.button("🚀 FINALIZAR E GUARDAR", type="primary", use_container_width=True):
                if not nome:
                    st.error("Por favor, digite seu nome.")
                else:
                    with st.spinner("A guardar..."):
                        agora = obter_agora_br()
                        novas_linhas = []
                        falhas_lista = []
                        for r in respostas:
                            probls = [n for n, v in zip(["Higiene", "Funcionamento", "Estado"], [r["H"], r["F"], r["E"]]) if v == "NÃO"]
                            status = "✅ OK" if not probls else "❌ Falha"
                            obs = ", ".join(probls) if probls else "Nenhuma"
                            novas_linhas.append({
                                "Data/Hora": agora.strftime("%d/%m/%Y %H:%M"),
                                "Funcionário": nome,
                                "Setor": setor,
                                "Equipamento": r["Equipamento"],
                                "Status": status,
                                "Falhas": obs
                            })
                            if probls: falhas_lista.append({"Equipamento": r["Equipamento"], "Falha": obs})
                        
                        try:
                            df_atual = carregar_dados()
                            df_novo = pd.DataFrame(novas_linhas)
                            df_final = pd.concat([df_atual, df_novo], ignore_index=True)
                            conn.update(spreadsheet=url_planilha, data=df_final)
                            st.session_state.ultima_inspecao = {"funcionario": nome, "setor": setor, "falhas": falhas_lista}
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")

with tab2:
    st.header("📜 Histórico")
    df = carregar_dados()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum dado encontrado.")

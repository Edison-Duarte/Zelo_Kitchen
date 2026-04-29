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

# --- CONEXÃO COM LIMPEZA AUTOMÁTICA ---
def conectar_seguro():
    try:
        # Puxa os dados brutos dos secrets
        s = st.secrets["connections"]["gsheets"]
        
        # LIMPEZA CRÍTICA: Remove espaços extras e garante que as quebras de linha sejam reais
        # O .replace("\\n", "\n") resolve o erro de PEM na maioria dos casos
        private_key = s["private_key"].replace("\\n", "\n").strip()
        
        # Reconstrói o dicionário de credenciais de forma limpa
        creds = {
            "type": s["type"],
            "project_id": s["project_id"],
            "private_key_id": s["private_key_id"],
            "private_key": private_key,
            "client_email": s["client_email"],
            "client_id": s["client_id"],
            "auth_uri": s["auth_uri"],
            "token_uri": s["token_uri"],
            "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
            "client_x509_cert_url": s["client_x509_cert_url"]
        }
        
        return st.connection("gsheets", type=GSheetsConnection, service_account_info=creds)
    except Exception as e:
        st.error(f"Erro na limpeza da chave: {e}")
        return None

conn = conectar_seguro()

def carregar_dados():
    if conn:
        try:
            return conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], ttl=0)
        except Exception as e:
            st.error(f"Erro ao ler: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# ... (restante do código das abas continua igual)
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
        st.success(f"✅ Inspeção guardada com sucesso!")
        
        if st.button("🔄 Realizar Nova Inspeção", use_container_width=True):
            st.session_state.ultima_inspecao = None
            st.rerun()
    else:
        with st.expander("Identificação do Inspetor", expanded=True):
            col1, col2 = st.columns(2)
            nome_func = col1.text_input("Seu Nome:")
            setor_sel = col2.selectbox("Setor a Inspecionar:", ["Selecione..."] + setores)

        if setor_sel != "Selecione...":
            respostas = []
            for item in itens_setores[setor_sel]:
                with st.container(border=True):
                    st.write(f"**{item}**")
                    c1, c2, c3 = st.columns(3)
                    h = c1.radio(f"Higiene", ["OK", "NÃO"], key=f"h_{item}", horizontal=True)
                    f = c2.radio(f"Funcionamento", ["OK", "NÃO"], key=f"f_{item}", horizontal=True)
                    e = c3.radio(f"Estado Geral", ["OK", "NÃO"], key=f"e_{item}", horizontal=True)
                    respostas.append({"Equipamento": item, "H": h, "F": f, "E": e})

            if st.button("🚀 GUARDAR INSPEÇÃO", type="primary", use_container_width=True):
                if not nome_func:
                    st.error("Por favor, introduza o seu nome.")
                else:
                    with st.spinner("A enviar dados..."):
                        agora = obter_agora_br()
                        novas_linhas = []
                        for r in respostas:
                            falhas = [n for n, v in zip(["Higiene", "Funcionamento", "Estado"], [r["H"], r["F"], r["E"]]) if v == "NÃO"]
                            novas_linhas.append({
                                "Data/Hora": agora.strftime("%d/%m/%Y %H:%M"),
                                "Funcionário": nome_func,
                                "Setor": setor_sel,
                                "Equipamento": r["Equipamento"],
                                "Status": "✅ OK" if not falhas else "❌ Falha",
                                "Observações": ", ".join(falhas) if falhas else "Nenhuma"
                            })
                        
                        try:
                            df_atual = carregar_dados()
                            df_novo = pd.DataFrame(novas_linhas)
                            df_final = pd.concat([df_atual, df_novo], ignore_index=True)
                            
                            # Atualiza a planilha (usa a URL definida nos Secrets automaticamente)
                            conn.update(data=df_final)
                            
                            st.session_state.ultima_inspecao = {"funcionario": nome_func}
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar na planilha: {e}")

with tab2:
    st.header("📜 Histórico de Registos")
    df_hist = carregar_dados()
    if not df_hist.empty:
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum dado encontrado.")

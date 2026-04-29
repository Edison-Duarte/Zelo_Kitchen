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

# --- LIGAÇÃO AO GOOGLE SHEETS ---
# O Streamlit lê automaticamente o bloco [connections.gsheets] do Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # Tenta ler a planilha usando a URL que está no Secrets
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        return conn.read(spreadsheet=url, ttl=0)
    except Exception as e:
        st.error(f"Erro ao aceder à planilha: {e}")
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

# --- INTERFACE DO UTILIZADOR ---
st.title("🍳 Sistema de Inspeção Zelo Kitchen")

tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico Permanente"])

with tab1:
    if st.session_state.ultima_inspecao:
        dados = st.session_state.ultima_inspecao
        st.success(f"✅ Inspeção de {dados['funcionario']} guardada com sucesso!")
        
        if dados["falhas"]:
            texto_falha = f"🚨 *FALHAS DETECTADAS - {dados['setor']}*\n\n"
            for f in dados["falhas"]:
                texto_falha += f"• {f['Equipamento']}: {f['Falha']}\n"
            
            st.warning("Foram detetadas falhas! Comunique os responsáveis:")
            c1, c2 = st.columns(2)
            c1.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(texto_falha)}" target="_blank"><button style="width:100%; background-color:#25d366; color:white; border:none; padding:12px; border-radius:10px; cursor:pointer;">🟢 Enviar WhatsApp</button></a>', unsafe_allow_html=True)
            c2.markdown(f'<a href="mailto:?subject=Relato de Falha Kitchen&body={urllib.parse.quote(texto_falha)}" target="_blank"><button style="width:100%; height:44px; border-radius:10px; cursor:pointer;">📧 Enviar E-mail</button></a>', unsafe_allow_html=True)
        
        if st.button("🔄 Realizar Nova Inspeção", use_container_width=True):
            st.session_state.ultima_inspecao = None
            st.rerun()
    else:
        with st.expander("Informações do Inspetor", expanded=True):
            col_nome, col_setor = st.columns(2)
            nome_func = col_nome.text_input("Seu Nome:")
            setor_sel = col_setor.selectbox("Setor a inspecionar:", ["Selecione..."] + setores)

        if setor_sel != "Selecione...":
            respostas = []
            st.info(f"Inspecionando: **{setor_sel}**")
            
            for item in itens_setores[setor_sel]:
                with st.container(border=True):
                    st.write(f"**{item}**")
                    c1, c2, c3 = st.columns(3)
                    h = c1.radio(f"Higiene", ["OK", "NÃO"], key=f"h_{item}", horizontal=True)
                    f = c2.radio(f"Funcionamento", ["OK", "NÃO"], key=f"f_{item}", horizontal=True)
                    e = c3.radio(f"Estado Geral", ["OK", "NÃO"], key=f"e_{item}", horizontal=True)
                    respostas.append({"Equipamento": item, "H": h, "F": f, "E": e})

            if st.button("🚀 FINALIZAR E GUARDAR", type="primary", use_container_width=True):
                if not nome_func:
                    st.error("Por favor, introduza o seu nome.")
                else:
                    with st.spinner("A enviar dados para a nuvem..."):
                        agora = obter_agora_br()
                        novas_linhas = []
                        falhas_lista = []
                        
                        for r in respostas:
                            problemas = []
                            if r["H"] == "NÃO": problemas.append("Higiene")
                            if r["F"] == "NÃO": problemas.append("Funcionamento")
                            if r["E"] == "NÃO": problemas.append("Estado Geral")
                            
                            status = "✅ Conforme" if not problemas else "❌ Não Conforme"
                            obs = ", ".join(problemas) if problemas else "Nenhuma"
                            
                            novas_linhas.append({
                                "Data/Hora": agora.strftime("%d/%m/%Y %H:%M"),
                                "Funcionário": nome_func,
                                "Setor": setor_sel,
                                "Equipamento": r["Equipamento"],
                                "Status": status,
                                "Falhas": obs
                            })
                            if problemas:
                                falhas_lista.append({"Equipamento": r["Equipamento"], "Falha": obs})
                        
                        try:
                            # Tenta ler e atualizar
                            url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                            df_atual = carregar_dados()
                            df_novo = pd.DataFrame(novas_linhas)
                            df_final = pd.concat([df_atual, df_novo], ignore_index=True)
                            
                            st.connection("gsheets", type=GSheetsConnection).update(spreadsheet=url, data=df_final)
                            
                            st.session_state.ultima_inspecao = {
                                "funcionario": nome_func,
                                "setor": setor_sel,
                                "falhas": falhas_lista
                            }
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao guardar na planilha: {e}")

with tab2:
    st.header("📜 Histórico de Inspeções")
    df_sheets = carregar_dados()
    
    if not df_sheets.empty:
        st.dataframe(df_sheets, use_container_width=True, hide_index=True)
        csv = df_sheets.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descarregar CSV", csv, "historico_zelo.csv", "text/csv")
    else:
        st.info("Nenhum dado encontrado ou planilha vazia.")

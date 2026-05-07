import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import urllib.parse
from fpdf import FPDF
import io

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Zelo Kitchen - Inspeção", page_icon="🍳", layout="wide")

# CSS para garantir quebras de linha e visual limpo
st.markdown("""
    <style>
        [data-testid="stDataFrame"] td {
            white-space: normal !important;
            word-wrap: break-word !important;
        }
        .main { background-color: #f9f9f9; }
        .stButton>button { border-radius: 5px; height: 3em; width: 100%; }
    </style>
""", unsafe_allow_html=True)

fuso_br = pytz.timezone('America/Sao_Paulo')
def obter_agora_br():
    return datetime.now(fuso_br)

# --- CONEXÃO COM GOOGLE SHEETS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro na conexão: {e}")

def carregar_dados():
    try:
        df = conn.read(ttl=0)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        if not df.empty and "Data/Hora" in df.columns:
            df["Data/Hora"] = pd.to_datetime(df["Data/Hora"], dayfirst=True)
        return df
    except Exception as e:
        return pd.DataFrame(columns=["Data/Hora", "Funcionário", "Setor", "Equipamento", "Status", "Falhas", "Descrição do Problema"])

# --- FUNÇÃO PARA GERAR PDF ---
def gerar_pdf(df_filtrado):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Relatorio de Nao Conformidades - Zelo Kitchen", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 10, f"Gerado em: {obter_agora_br().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)

    for i, row in df_filtrado.iterrows():
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(190, 8, f"Equipamento: {row['Equipamento']} ({row['Setor']})", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        desc = str(row['Descrição do Problema']).replace('\n', ' ') if row['Descrição do Problema'] else "Nenhuma"
        pdf.multi_cell(190, 7, f"Data: {row['Data/Hora'].strftime('%d/%m/%Y %H:%M')}\nInspetor: {row['Funcionário']}\nFalha: {row['Falhas']}\nDescricao: {desc}")
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

# --- ESTRUTURA ---
setores_lista = ["Espaço Café", "Cozinha", "Mirante", "Refeitório"]
itens_setores = {
    "Espaço Café": ["Estufa quente", "Estufa fria", "Geladeiras balcão", "Frigobares", "Máquina de café expresso"],
    "Cozinha": ["Geladeiras Bacio di Latte", "Geladeiras Resfriados", "Câmaras Frias", "Freezers Horizontais", "Fornos", "Fogões", "Fritadeiras", "Chapas", "Geladeiras Balcões", "Coifas", "Pista Fria"],
    "Mirante": ["Freezer Sorvete Dona Mazza", "Adega Vinhos", "Geladeiras", "Geladeiras Balcões", "Lava Louças", "Coifas", "Pista Fria", "Elevador Monta Carga", "Freezer Horizontal", "Churrasqueira", "Forno a Lenha"],
    "Refeitório": ["Lava Louças", "Geladeira Resfriados", "Rechaud"]
}

st.title("🍳 Sistema de Inspeção - Zelo Kitchen")
tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico"])

# --- ABA 1: NOVA INSPEÇÃO ---
with tab1:
    if 'sucesso' in st.session_state and st.session_state.sucesso:
        st.success("✅ Inspeção salva com sucesso!")
        if st.button("Realizar Nova Inspeção"):
            st.session_state.sucesso = False
            st.rerun()
    else:
        with st.expander("📌 Identificação", expanded=True):
            col1, col2 = st.columns(2)
            nome_inspetor = col1.text_input("Seu Nome:")
            setor_selecionado = col2.selectbox("Setor a Inspecionar:", ["Selecione..."] + setores_lista)

        if setor_selecionado != "Selecione...":
            respostas = []
            for item in itens_setores[setor_selecionado]:
                with st.container(border=True):
                    st.write(f"**{item}**")
                    c1, c2, c3 = st.columns(3)
                    h = c1.radio(f"Higiene", ["OK", "NÃO"], key=f"h_{item}", horizontal=True)
                    f = c2.radio(f"Funcionamento", ["OK", "NÃO"], key=f"f_{item}", horizontal=True)
                    e = c3.radio(f"Estado Geral", ["OK", "NÃO"], key=f"e_{item}", horizontal=True)
                    obs = ""
                    if any(x == "NÃO" for x in [h, f, e]):
                        obs = st.text_area(f"Detalhes do problema:", key=f"obs_{item}")
                    respostas.append({"Equipamento": item, "H": h, "F": f, "E": e, "Detalhes": obs})

            if st.button("🚀 FINALIZAR E SALVAR", type="primary"):
                if not nome_inspetor: st.error("Preencha seu nome.")
                else:
                    agora = obter_agora_br().strftime("%d/%m/%Y %H:%M")
                    novas = []
                    for r in respostas:
                        falhas = [n for n, v in zip(["Higiene", "Funcionamento", "Estado"], [r["H"], r["F"], r["E"]]) if v == "NÃO"]
                        novas.append({"Data/Hora": agora, "Funcionário": nome_inspetor, "Setor": setor_selecionado, "Equipamento": r["Equipamento"], "Status": "❌ FALHA" if falhas else "✅ OK", "Falhas": ", ".join(falhas) if falhas else "Nenhuma", "Descrição do Problema": r["Detalhes"]})
                    conn.update(data=pd.concat([carregar_dados(), pd.DataFrame(novas)], ignore_index=True))
                    st.session_state.sucesso = True
                    st.rerun()

# --- ABA 2: HISTÓRICO E RELATÓRIOS ---
with tab2:
    st.subheader("📜 Filtros e Histórico")
    df_hist = carregar_dados()
    if not df_hist.empty:
        with st.expander("🔍 Filtros de Busca", expanded=True):
            col_d1, col_d2 = st.columns(2)
            d_ini = col_d1.date_input("Início", value=df_hist["Data/Hora"].min().date())
            d_fim = col_d2.date_input("Fim", value=df_hist["Data/Hora"].max().date())
            col_f1, col_f2 = st.columns(2)
            f_set = col_f1.multiselect("Setores", options=setores_lista, default=setores_lista)
            f_sta = col_f2.multiselect("Status", options=["✅ OK", "❌ FALHA"], default=["❌ FALHA"])

        mask = (df_hist["Data/Hora"].dt.date >= d_ini) & (df_hist["Data/Hora"].dt.date <= d_fim) & (df_hist["Setor"].isin(f_set)) & (df_hist["Status"].isin(f_sta))
        df_filtrado = df_hist[mask].sort_values("Data/Hora", ascending=False)
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

        # --- SEÇÃO DE RELATÓRIO COM O AVISO MANUTIDO ---
        st.divider()
        st.subheader("📊 Enviar Relatório de Não Conformidades")
        st.info("💡 **Aviso:** O relatório enviado será baseado exclusivamente no conteúdo **filtrado** na tabela acima.")
        
        if not df_filtrado.empty:
            texto_rel = f"*RELATÓRIO ZELO KITCHEN - {obter_agora_br().strftime('%d/%m/%Y')}*\n\n"
            for _, row in df_filtrado.iterrows():
                texto_rel += f"⚠️ *{row['Equipamento']}* ({row['Setor']})\nFalha: {row['Falhas']}\nObs: {row['Descrição do Problema']}\n---\n"
            
            c_rel1, c_rel2, c_rel3 = st.columns(3)
            # Botões
            c_rel1.link_button("🟢 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(texto_rel)}", use_container_width=True)
            c_rel2.link_button("📧 E-mail", f"mailto:?subject=Relatorio de Nao Conformidades&body={urllib.parse.quote(texto_rel)}", use_container_width=True)
            c_rel3.download_button("📥 PDF", gerar_pdf(df_filtrado), f"Relatorio_{obter_agora_br().strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True)
        else:
            st.warning("Não há dados para gerar o relatório com os filtros atuais.")
    else:
        st.info("Nenhum registro encontrado.")

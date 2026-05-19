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

st.markdown("""
    <style>
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
    st.error(f"Erro na conexão com o banco de dados: {e}")

def carregar_dados():
    try:
        df = conn.read(ttl=0)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Cria a coluna de Resolução se não existir
        if "Resolução" not in df.columns:
            df["Resolução"] = ""
            
        # Guarda o índice real da planilha para podermos atualizar a linha exata depois
        df["original_index"] = df.index
            
        if not df.empty and "Data/Hora" in df.columns:
            # Conversão segura para formato de data do pandas
            df_dt = pd.to_datetime(df["Data/Hora"], dayfirst=True, errors='coerce')
            df["Data"] = df_dt.dt.strftime('%d/%m/%Y')
            df["Hora"] = df_dt.dt.strftime('%H:%M')
        else:
            df["Data"] = ""
            df["Hora"] = ""
        
        colunas_desejadas = ["Data", "Hora", "Funcionário", "Setor", "Equipamento", "Status", "Falhas", "Descrição do Problema", "Resolução", "original_index"]
        df_limpo = df[[c for c in colunas_desejadas if c in df.columns]]
        return df_limpo
    except Exception as e:
        return pd.DataFrame(columns=["Data", "Hora", "Funcionário", "Setor", "Equipamento", "Status", "Falhas", "Descrição do Problema", "Resolução", "original_index"])

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
        pdf.cell(190, 8, f"{row.get('Equipamento', 'N/A')} ({row.get('Setor', 'N/A')})", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        desc = str(row.get('Descrição do Problema', '')).replace('\n', ' ') if row.get('Descrição do Problema') else "Nenhuma"
        resolvido = f"\nSolucionado em: {row.get('Resolução')}" if pd.notna(row.get('Resolução')) and row.get('Resolução') != "" else "\nStatus: PENDENTE"
        pdf.multi_cell(190, 7, f"Identificado em: {row.get('Data', '')} {row.get('Hora', '')}\nInspetor: {row.get('Funcionário', '')}\nFalha: {row.get('Falhas', '')}\nDescricao: {desc}{resolvido}")
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

# --- ESTRUTURA DO CHECKLIST ---
setores_lista = ["Espaço Café", "Cozinha", "Mirante", "Refeitório"]
itens_setores = {
    "Espaço Café": ["Estufa quente", "Estufa fria", "Geladeiras balcão", "Frigobares", "Máquina de café expresso"],
    "Cozinha": ["Geladeiras Bacio di Latte", "Geladeiras Resfriados", "Câmaras Frias", "Freezers Horizontais", "Fornos", "Fogões", "Fritadeiras", "Chapas", "Geladeiras Balcões", "Coifas", "Pista Fria"],
    "Mirante": ["Freezer Sorvete Dona Mazza", "Adega Vinhos", "Geladeiras", "Geladeiras Balcões", "Lava Louças", "Coifas", "Pista Fria", "Elevador Monta Carga", "Freezer Horizontal", "Churrasqueira", "Forno a Lenha"],
    "Refeitório": ["Lava Louças", "Geladeira Resfriados", "Rechaud"]
}

st.title("🍳 Sistema de Inspeção Zelo Kitchen")
tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Painel de Pendências & Histórico"])

# --- ABA 1: NOVA INSPEÇÃO ---
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
            setor_selecionado = col2.selectbox("Setor a Inspecionar:", ["Selecione..."] + setores_lista)

        if setor_selecionado != "Selecione...":
            respostas = []
            for item in itens_setores[setor_selecionado]:
                with st.container(border=True):
                    st.write(f"**{item}**")
                    c1, c2, c3 = st.columns(3)
                    h = c1.radio(f"Higiene", ["OK", "NÃO"], key=f"h_{item}", horizontal=True)
                    f = c2.radio(f"Funcionamento", ["OK", "NÃO"], key=f"f_{item}", horizontal=True)
                    e = c3.radio(f

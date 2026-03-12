import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
from fpdf import FPDF

# Configuração da página
st.set_page_config(page_title="Zelo Kitchen - Inspeção", page_icon="🍳", layout="wide")

# --- INICIALIZAÇÃO DA SESSÃO ---
if 'historico' not in st.session_state:
    st.session_state.historico = pd.DataFrame(columns=[
        "Data", "Colaborador", "Setor", "Status", "Irregularidades", "Data_Obj"
    ])

# --- DADOS ---
setores = ["Espaço Café", "Cozinha", "Mirante", "Refeitório"]
itens_setores = {
    "Espaço Café": ["Estufa quente", "Estufa fria", "Geladeiras balcão", "Frigobares", "Máquina de café expresso"],
    "Cozinha": ["Geladeiras Bacio di Latte", "Geladeiras Resfriados", "Câmaras Frias", "Freezers Horizontais", "Fornos", "Fogões", "Fritadeiras", "Chapas", "Geladeiras Balcões", "Coifas", "Pista Fria"],
    "Mirante": ["Freezer Sorvete Dona Mazza", "Adega Vinhos", "Geladeiras", "Geladeiras Balcões", "Lava Louças", "Coifas", "Pista Fria", "Elevador Monta Carga", "Freezer Horizontal", "Churrasqueira", "Forno a Lenha"],
    "Refeitório": ["Lava Louças", "Geladeira Resfriados", "Rechaud"]
}

# --- FUNÇÃO GERAR PDF ---
def gerar_pdf(df):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Relatorio Detalhado de Inspecoes", ln=True, align='C')
    pdf.ln(10)
    
    for i, row in df.iterrows():
        colaborador = str(row['Colaborador']).encode('latin-1', 'replace').decode('latin-1')
        setor = str(row['Setor']).encode('latin-1', 'replace').decode('latin-1')
        status = str(row['Status']).replace("✅ ", "").replace("❌ ", "")
        # Detalhes das irregularidades
        irregularidades = str(row['Irregularidades']).encode('latin-1', 'replace').decode('latin-1')
        
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, f"Data: {row['Data']} | Setor: {setor}", ln=True, fill=True)
        
        pdf.set_font("Arial", "", 10)
        texto_corpo = (
            f"Inspetor: {colaborador}\n"
            f"Status: {status}\n"
            f"Detalhes das Falhas: {irregularidades}\n"
            + "-"*85
        )
        pdf.multi_cell(0, 5, texto_corpo)
        pdf.ln(2)
    return pdf.output()

# --- INTERFACE ---
st.title("🍳 Inspeção de Equipamentos - Zelo Kitchen")

tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico Detalhado"])

with tab1:
    with st.container(border=True):
        c1, c2 = st.columns(2)
        nome_input = c1.text_input("👤 Nome do Colaborador:")
        setor_sel = c2.selectbox("📍 Setor:", ["Selecione..."] + setores)

    if setor_sel != "Selecione...":
        with st.form("checklist_form"):
            respostas = {}
            for equip in itens_setores[setor_sel]:
                st.subheader(f"🔹 {equip}")
                cols = st.columns(3)
                respostas[f"{equip} (Higiene)"] = cols[0].radio("Higiene", ["OK", "NÃO"], key=f"{equip}h", horizontal=True)
                respostas[f"{equip} (Funcionamento)"] = cols[1].radio("Funcionamento", ["OK", "NÃO"], key=f"{equip}f", horizontal=True)
                respostas[f"{equip} (Estado Geral)"] = cols[2].radio("Estado Geral", ["OK", "NÃO"], key=f"{equip}e", horizontal=True)
                st.divider()
            
            if st.form_submit_button("🚀 Finalizar Inspeção"):
                if not nome_input:
                    st.error("Por favor, preencha o nome.")
                else:
                    # Coleta as falhas específicas: Equipamento + Qual critério falhou
                    falhas_detalhadas = [item for item, status in respostas.items() if status == "NÃO"]
                    
                    status = "❌ Irregular" if falhas_detalhadas else "✅ Conforme"
                    agora = datetime.now()
                    
                    # Salva no histórico com os detalhes
                    detalhes_str = ", ".join(falhas_detalhadas) if falhas_detalhadas else "Nenhuma"
                    
                    nova_entrada = pd.DataFrame([{
                        "Data": agora.strftime("%d/%m/%Y %H:%M"),
                        "Colaborador": nome_input,
                        "Setor": setor_sel,
                        "Status": status,
                        "Irregularidades": detalhes_str,
                        "Data_Obj": agora.date()
                    }])
                    
                    st.session_state.historico = pd.concat([st.session_state.historico, nova_entrada], ignore_index=True)
                    st.success("Inspeção registrada!")
                    
                    # WhatsApp
                    msg_zap = f"🚨 *RELATÓRIO DE FALHAS - {setor_sel}*\n*Status:* {status}\n*Responsável:* {nome_input}\n*Falhas:* {detalhes_str}"
                    st.markdown(f"""
                        <a href="https://wa.me/?text={urllib.parse.quote(msg_zap)}" target="_blank">
                            <button style="width:100%; background-color:#25d366; color:white; border:none; padding:12px; border-radius:10px; font-weight:bold; cursor:pointer;">
                                🟢 Enviar para WhatsApp
                            </button>
                        </a>
                    """, unsafe_allow_html=True)

with tab2:
    st.header("📜 Histórico de Inspeções")
    
    if not st.session_state.historico.empty:
        # Filtros
        with st.expander("🔍 Filtros Avançados", expanded=True):
            f1, f2, f3 = st.columns(3)
            sel_setor = f1.multiselect("Setor:", setores)
            sel_status = f2.multiselect("Status:", ["✅ Conforme", "❌ Irregular"])
            sel_data = f3.date_input("Período:", value=[])

        # Lógica de Filtro
        df_f = st.session_state.historico.copy()
        if sel_setor: df_f = df_f[df_f["Setor"].isin(sel_setor)]
        if sel_status: df_f = df_f[df_f["Status"].isin(sel_status)]
        if isinstance(sel_data, list) and len(sel_data) == 2:
            df_f = df_f[(df_f["Data_Obj"] >= sel_data[0]) & (df_f["Data_Obj"] <= sel_data[1])]

        # Exibição
        st.dataframe(df_f.drop(columns=["Data_Obj"]), use_container_width=True, hide_index=True)

        # Botões de Exportação
        st.divider()
        e1, e2 = st.columns(2)
        
        try:
            pdf_bytes = bytes(gerar_pdf(df_f))
            e1.download_button("📄 Baixar PDF Filtrado", pdf_bytes, "inspeção.pdf", "application/pdf", use_container_width=True)
        except Exception as e:
            e1.error(f"Erro PDF: {e}")

        # Link de E-mail
        resumo_corpo = f"Resumo de Inspeções Zelo Kitchen\n"
        for _, r in df_f.iterrows():
            resumo_corpo += f"\n- {r['Data']} | {r['Setor']} | {r['Irregularidades']}"
        
        mailto = f"mailto:?subject=Relatorio de Falhas&body={urllib.parse.quote(resumo_corpo)}"
        e2.markdown(f'<a href="{mailto}" target="_blank"><button style="width:100%; height:42px; border-radius:8px; cursor:pointer;">📧 Enviar por E-mail</button></a>', unsafe_allow_html=True)
        
        if st.button("🗑️ Resetar Histórico"):
            st.session_state.historico = pd.DataFrame(columns=["Data", "Colaborador", "Setor", "Status", "Irregularidades", "Data_Obj"])
            st.rerun()
    else:
        st.info("Nenhum registro encontrado.")

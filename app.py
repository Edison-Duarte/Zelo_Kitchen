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

# --- FUNÇÃO GERAR PDF (CORRIGIDA) ---
def gerar_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Relatorio de Inspecoes - Zelo Kitchen", ln=True, align='C')
    pdf.ln(10)
    
    for i, row in df.iterrows():
        # Limpeza para evitar erro de codificação Unicode (Latin-1)
        # Removemos emojis e garantimos que acentos funcionem via tratamento de string
        colaborador = str(row['Colaborador']).encode('latin-1', 'ignore').decode('latin-1')
        setor = str(row['Setor']).encode('latin-1', 'ignore').decode('latin-1')
        status = str(row['Status']).replace("✅ ", "").replace("❌ ", "")
        irregularidades = str(row['Irregularidades']).encode('latin-1', 'ignore').decode('latin-1')
        
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, f"Data: {row['Data']} | Setor: {setor}", ln=True)
        
        pdf.set_font("Arial", "", 10)
        texto_corpo = (
            f"Inspetor: {colaborador}\n"
            f"Status: {status}\n"
            f"Irregularidades: {irregularidades}\n"
            + "-"*70
        )
        pdf.multi_cell(0, 5, texto_corpo)
        pdf.ln(2)
    
    return pdf.output()

# --- INTERFACE ---
st.title("🍳 Sistema de Inspeção de Equipamentos")

tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico Temporário"])

with tab1:
    st.header("Realizar Checklist")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        nome_input = c1.text_input("👤 Nome do Colaborador:")
        setor_sel = c2.selectbox("📍 Selecione o Local:", ["Selecione..."] + setores)

    if setor_sel != "Selecione...":
        with st.form("checklist_form"):
            respostas = {}
            st.markdown(f"### Itens: {setor_sel}")
            for equip in itens_setores[setor_sel]:
                st.write(f"**{equip}**")
                cols = st.columns(3)
                respostas[f"{equip}_H"] = cols[0].radio("Higiene", ["OK", "NÃO"], key=f"{equip}h", horizontal=True)
                respostas[f"{equip}_F"] = cols[1].radio("Funcion.", ["OK", "NÃO"], key=f"{equip}f", horizontal=True)
                respostas[f"{equip}_E"] = cols[2].radio("Estado", ["OK", "NÃO"], key=f"{equip}e", horizontal=True)
                st.divider()
            
            if st.form_submit_button("🚀 Finalizar e Salvar"):
                if not nome_input:
                    st.error("Por favor, preencha seu nome!")
                else:
                    # Lógica de processamento
                    falhas = []
                    for k, v in respostas.items():
                        if v == "NÃO":
                            item = k.rsplit('_', 1)[0]
                            if item not in falhas: falhas.append(item)
                    
                    status = "❌ Irregular" if falhas else "✅ Conforme"
                    agora = datetime.now()
                    
                    nova_entrada = pd.DataFrame([{
                        "Data": agora.strftime("%d/%m/%Y %H:%M"),
                        "Colaborador": nome_input,
                        "Setor": setor_sel,
                        "Status": status,
                        "Irregularidades": ", ".join(falhas) if falhas else "Nenhuma",
                        "Data_Obj": agora.date()
                    }])
                    
                    st.session_state.historico = pd.concat([st.session_state.historico, nova_entrada], ignore_index=True)
                    st.success("Inspeção registrada com sucesso!")
                    
                    # Link WhatsApp
                    msg_zap = f"🚨 *INSPEÇÃO: {setor_sel}*\nStatus: {status}\nResponsável: {nome_input}"
                    if falhas: msg_zap += f"\nItens: {', '.join(falhas)}"
                    st.markdown(f"[🟢 Enviar Resumo via WhatsApp](https://wa.me/?text={urllib.parse.quote(msg_zap)})")

with tab2:
    st.header("Consulta e Filtros")
    
    if st.session_state.historico.empty:
        st.info("O histórico está vazio. Realize uma inspeção para visualizar os dados.")
    else:
        # --- FILTROS ---
        with st.expander("🔍 Filtrar Resultados", expanded=True):
            f_c1, f_c2, f_c3 = st.columns(3)
            f_setor = f_c1.multiselect("Setor:", setores)
            f_status = f_c2.multiselect("Status:", ["✅ Conforme", "❌ Irregular"])
            f_data = f_c3.date_input("Filtrar por data:", [])

        # Aplicação dos Filtros
        df_f = st.session_state.historico.copy()
        if f_setor:
            df_f = df_f[df_f["Setor"].isin(f_setor)]
        if f_status:
            df_f = df_f[df_f["Status"].isin(f_status)]
        if len(f_data) == 2:
            df_f = df_f[(df_f["Data_Obj"] >= f_data[0]) & (df_f["Data_Obj"] <= f_data[1])]

        st.dataframe(df_f.drop(columns=["Data_Obj"]), use_container_width=True, hide_index=True)

        # --- EXPORTAÇÃO ---
        st.divider()
        st.subheader("📤 Exportar Relatório")
        
        e_c1, e_c2 = st.columns(2)
        
        # Botão PDF
        try:
            pdf_bytes = gerar_pdf(df_f)
            e_c1.download_button(
                label="📄 Baixar PDF Filtrado",
                data=pdf_bytes,
                file_name=f"relatorio_zelo_{datetime.now().strftime('%d_%m')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            e_c1.error(f"Erro ao gerar PDF: {e}")

        # Botão E-mail
        resumo_email = "Relatorio de Inspecao\n" + "="*20 + "\n"
        for _, r in df_f.iterrows():
            resumo_email += f"{r['Data']} - {r['Setor']} - {r['Status']}\n"
        
        mailto = f"mailto:?subject=Relatorio Inspecao Zelo Kitchen&body={urllib.parse.quote(resumo_email)}"
        e_c2.markdown(f"""
            <a href="{mailto}" target="_blank">
                <button style="width:100%; height:40px; background-color:#f0f2f6; border:1px solid #dcdfe3; border-radius:8px; cursor:pointer;">
                    📧 Enviar por E-mail
                </button>
            </a>
        """, unsafe_allow_html=True)

        if st.button("🗑️ Limpar Todo o Histórico"):
            st.session_state.historico = pd.DataFrame(columns=["Data", "Colaborador", "Setor", "Status", "Irregularidades", "Data_Obj"])
            st.rerun()

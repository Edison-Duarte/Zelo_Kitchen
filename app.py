import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
from fpdf import FPDF
import base64

# Configuração da página
st.set_page_config(page_title="Checklist Pro", page_icon="🍳", layout="wide")

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

# --- FUNÇÕES DE EXPORTAÇÃO ---
def gerar_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Relatório de Inspeções Filtrado", ln=True, align='C')
    pdf.set_font("Arial", "", 10)
    pdf.ln(10)
    
    for i, row in df.iterrows():
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, f"Data: {row['Data']} - Setor: {row['Setor']}", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 5, f"Inspetor: {row['Colaborador']}\nStatus: {row['Status']}\nIrregularidades: {row['Irregularidades']}\n" + "-"*50)
        pdf.ln(2)
    
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACE ---
tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico Temporário"])

with tab1:
    st.header("Nova Inspeção")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("👤 Nome do Inspetor:")
        setor_sel = c2.selectbox("📍 Setor:", ["Selecione..."] + setores)

    if setor_sel != "Selecione...":
        with st.form("checklist_form"):
            respostas = {}
            for equip in itens_setores[setor_sel]:
                st.write(f"**{equip}**")
                cols = st.columns(3)
                respostas[f"{equip}_H"] = cols[0].radio("Higiene", ["OK", "NÃO"], key=f"{equip}h", horizontal=True)
                respostas[f"{equip}_F"] = cols[1].radio("Funcion.", ["OK", "NÃO"], key=f"{equip}f", horizontal=True)
                respostas[f"{equip}_E"] = cols[2].radio("Estado", ["OK", "NÃO"], key=f"{equip}e", horizontal=True)
            
            if st.form_submit_button("🚀 Finalizar"):
                falhas = [k.rsplit('_', 1)[0] for k, v in respostas.items() if v == "NÃO"]
                falhas_unicas = list(set(falhas))
                status = "❌ Irregular" if falhas_unicas else "✅ Conforme"
                
                agora = datetime.now()
                nova_entrada = pd.DataFrame([{
                    "Data": agora.strftime("%d/%m/%Y %H:%M"),
                    "Colaborador": nome,
                    "Setor": setor_sel,
                    "Status": status,
                    "Irregularidades": ", ".join(falhas_unicas) if falhas_unicas else "Nenhuma",
                    "Data_Obj": agora.date()
                }])
                st.session_state.historico = pd.concat([st.session_state.historico, nova_entrada], ignore_index=True)
                st.success("Inspeção Salva!")

with tab2:
    st.header("Filtros do Histórico")
    
    if not st.session_state.historico.empty:
        # --- LINHA DE FILTROS ---
        f_col1, f_col2, f_col3 = st.columns(3)
        
        filtro_setor = f_col1.multiselect("Setor:", setores)
        filtro_status = f_col2.multiselect("Status:", ["✅ Conforme", "❌ Irregular"])
        
        # Filtro de Período
        data_inicio = f_col3.date_input("Início:", datetime.now())
        data_fim = f_col3.date_input("Fim:", datetime.now())

        # Aplicação dos Filtros
        df_filtrado = st.session_state.historico.copy()
        
        if filtro_setor:
            df_filtrado = df_filtrado[df_filtrado["Setor"].isin(filtro_setor)]
        if filtro_status:
            df_filtrado = df_filtrado[df_filtrado["Status"].isin(filtro_status)]
        
        df_filtrado = df_filtrado[
            (df_filtrado["Data_Obj"] >= data_inicio) & 
            (df_filtrado["Data_Obj"] <= data_fim)
        ]

        st.dataframe(df_filtrado.drop(columns=["Data_Obj"]), use_container_width=True, hide_index=True)

        # --- BOTÕES DE EXPORTAÇÃO ---
        st.write("### Exportar Dados Filtrados")
        e_col1, e_col2 = st.columns(2)

        # Botão PDF
        pdf_data = gerar_pdf(df_filtrado)
        e_col1.download_button(
            label="📄 Gerar PDF (Filtrado)",
            data=pdf_data,
            file_name="relatorio_inspeccao.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        # Botão E-mail (Link mailto)
        # Nota: O mailto tem limite de caracteres, enviamos um resumo
        corpo_email = f"Relatório de Inspeção - {datetime.now().strftime('%d/%m/%Y')}\n\n"
        for _, r in df_filtrado.iterrows():
            corpo_email += f"- {r['Data']} | {r['Setor']} | {r['Status']}\n"
        
        mailto_link = f"mailto:?subject=Relatorio de Inspecao&body={urllib.parse.quote(corpo_email)}"
        e_col2.markdown(f"""
            <a href="{mailto_link}" target="_blank">
                <button style="width:100%; height:38px; background-color:#f0f2f6; border:1px solid #dcdfe3; border-radius:5px; cursor:pointer;">
                    📧 Enviar Resumo por E-mail
                </button>
            </a>
        """, unsafe_allow_html=True)

    else:
        st.info("Nenhum dado para filtrar ainda.")

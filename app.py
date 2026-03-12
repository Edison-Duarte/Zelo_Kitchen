import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
from fpdf import FPDF

# Configuração da página para melhor experiência mobile e desktop
st.set_page_config(page_title="Zelo Kitchen - Inspeção", page_icon="🍳", layout="wide")

# --- INICIALIZAÇÃO DA SESSÃO (HISTÓRICO TEMPORÁRIO) ---
if 'historico' not in st.session_state:
    st.session_state.historico = pd.DataFrame(columns=[
        "Data", "Colaborador", "Setor", "Status", "Irregularidades", "Data_Obj"
    ])

# --- BASE DE DADOS DE EQUIPAMENTOS ---
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
    pdf.cell(200, 10, "Relatorio de Inspecoes - Zelo Kitchen", ln=True, align='C')
    pdf.ln(10)
    
    for i, row in df.iterrows():
        # Tratamento de strings para evitar erro Unicode/Latin-1 no PDF
        colaborador = str(row['Colaborador']).encode('latin-1', 'replace').decode('latin-1')
        setor = str(row['Setor']).encode('latin-1', 'replace').decode('latin-1')
        status = str(row['Status']).replace("✅ ", "").replace("❌ ", "")
        irregularidades = str(row['Irregularidades']).encode('latin-1', 'replace').decode('latin-1')
        
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, f"Data: {row['Data']} | Setor: {setor}", ln=True, fill=True)
        
        pdf.set_font("Arial", "", 10)
        texto_corpo = (
            f"Inspetor: {colaborador}\n"
            f"Status: {status}\n"
            f"Irregularidades: {irregularidades}\n"
            + "-"*85
        )
        pdf.multi_cell(0, 5, texto_corpo)
        pdf.ln(2)
    
    # Retorna o buffer do PDF (fpdf2 retorna bytearray por padrão)
    return pdf.output()

# --- INTERFACE PRINCIPAL ---
st.title("🍳 Sistema de Inspeção de Equipamentos")

tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico Temporário"])

with tab1:
    st.header("Realizar Checklist")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        nome_input = c1.text_input("👤 Nome do Colaborador:", placeholder="Ex: João Silva")
        setor_sel = c2.selectbox("📍 Selecione o Local da Inspeção:", ["Selecione..."] + setores)

    if setor_sel != "Selecione...":
        with st.form("checklist_form"):
            respostas = {}
            st.markdown(f"### Equipamentos: {setor_sel}")
            
            for equip in itens_setores[setor_sel]:
                st.write(f"**{equip}**")
                cols = st.columns(3)
                # Chaves únicas para evitar conflitos no session_state
                respostas[f"{equip}_H"] = cols[0].radio("Higiene", ["OK", "NÃO"], key=f"{equip}h", horizontal=True)
                respostas[f"{equip}_F"] = cols[1].radio("Funcion.", ["OK", "NÃO"], key=f"{equip}f", horizontal=True)
                respostas[f"{equip}_E"] = cols[2].radio("Estado", ["OK", "NÃO"], key=f"{equip}e", horizontal=True)
                st.divider()
            
            submit_btn = st.form_submit_button("🚀 Finalizar e Salvar Inspeção")
            
            if submit_btn:
                if not nome_input:
                    st.error("⚠️ Por favor, preencha o nome do responsável antes de finalizar.")
                else:
                    # Filtra apenas os itens com "NÃO"
                    falhas = [k.rsplit('_', 1)[0] for k, v in respostas.items() if v == "NÃO"]
                    falhas_unicas = sorted(list(set(falhas)))
                    
                    status = "❌ Irregular" if falhas_unicas else "✅ Conforme"
                    agora = datetime.now()
                    
                    # Adiciona ao DataFrame global da sessão
                    nova_entrada = pd.DataFrame([{
                        "Data": agora.strftime("%d/%m/%Y %H:%M"),
                        "Colaborador": nome_input,
                        "Setor": setor_sel,
                        "Status": status,
                        "Irregularidades": ", ".join(falhas_unicas) if falhas_unicas else "Nenhuma",
                        "Data_Obj": agora.date()
                    }])
                    
                    st.session_state.historico = pd.concat([st.session_state.historico, nova_entrada], ignore_index=True)
                    st.success("✅ Inspeção salva no histórico temporário!")
                    
                    # Preparação para WhatsApp
                    resumo_zap = f"🚨 *INSPEÇÃO: {setor_sel}*\n*Status:* {status}\n*Responsável:* {nome_input}"
                    if falhas_unicas:
                        resumo_zap += f"\n*Falhas detectadas:* {', '.join(falhas_unicas)}"
                    
                    st.markdown(f"""
                        <a href="https://wa.me/?text={urllib.parse.quote(resumo_zap)}" target="_blank">
                            <button style="width:100%; background-color:#25d366; color:white; border:none; padding:12px; border-radius:10px; font-weight:bold; cursor:pointer; margin-top:10px;">
                                🟢 Enviar Alerta via WhatsApp
                            </button>
                        </a>
                    """, unsafe_allow_html=True)

with tab2:
    st.header("Histórico e Filtros Avançados")
    
    if st.session_state.historico.empty:
        st.info("O histórico está vazio. As inspeções realizadas aparecerão aqui até que o app seja reiniciado.")
    else:
        # --- SEÇÃO DE FILTROS ---
        with st.expander("🔍 Filtrar Resultados", expanded=True):
            f_c1, f_c2, f_c3 = st.columns(3)
            f_setor = f_c1.multiselect("Filtrar Setor:", setores)
            f_status = f_c2.multiselect("Filtrar Status:", ["✅ Conforme", "❌ Irregular"])
            # Filtro de data (seleção de intervalo)
            f_data = f_c3.date_input("Filtrar Período:", value=[])

        # Aplicação da lógica de filtragem no DataFrame
        df_filtrado = st.session_state.historico.copy()
        
        if f_setor:
            df_filtrado = df_filtrado[df_filtrado["Setor"].isin(f_setor)]
        if f_status:
            df_filtrado = df_filtrado[df_filtrado["Status"].isin(f_status)]
        if isinstance(f_data, list) and len(f_data) == 2:
            df_filtrado = df_filtrado[(df_filtrado["Data_Obj"] >= f_data[0]) & (df_filtrado["Data_Obj"] <= f_data[1])]
        elif isinstance(f_data, datetime): # Caso selecione apenas uma data
            df_filtrado = df_filtrado[df_filtrado["Data_Obj"] == f_data]

        # Exibição da Tabela (Ocultando a coluna técnica de data)
        st.dataframe(df_filtrado.drop(columns=["Data_Obj"]), use_container_width=True, hide_index=True)

        # --- SEÇÃO DE EXPORTAÇÃO ---
        st.divider()
        st.subheader("📤 Exportar Dados Filtrados")
        
        exp_c1, exp_c2 = st.columns(2)
        
        # Lógica de geração de PDF com conversão bytearray -> bytes
        try:
            pdf_raw = gerar_pdf(df_filtrado)
            pdf_final = bytes(pdf_raw) # CORREÇÃO DO ERRO DE FORMATO BINÁRIO
            
            exp_c1.download_button(
                label="📄 Baixar Relatório em PDF",
                data=pdf_final,
                file_name=f"inspeção_zelo_{datetime.now().strftime('%d_%m_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            exp_c1.error(f"Erro técnico ao gerar PDF: {e}")

        # Lógica de E-mail (via cliente local)
        corpo_email = "Resumo de Inspeções Zelo Kitchen\n" + "="*30 + "\n"
        for _, r in df_filtrado.iterrows():
            corpo_email += f"{r['Data']} | {r['Setor']} | {r['Status']}\n"
        
        mailto_url = f"mailto:?subject=Relatorio de Inspecao&body={urllib.parse.quote(corpo_email)}"
        exp_c2.markdown(f"""
            <a href="{mailto_url}" target="_blank">
                <button style="width:100%; height:40px; background-color:#f0f2f6; border:1px solid #dcdfe3; border-radius:8px; cursor:pointer;">
                    📧 Enviar Resumo por E-mail
                </button>
            </a>
        """, unsafe_allow_html=True)

        st.divider()
        if st.button("🗑️ Limpar Todo o Histórico (Sessão Atual)"):
            st.session_state.historico = pd.DataFrame(columns=["Data", "Colaborador", "Setor", "Status", "Irregularidades", "Data_Obj"])
            st.rerun()

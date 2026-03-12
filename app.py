import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
from fpdf import FPDF
import pytz

# --- CONFIGURAÇÃO DE FUSO HORÁRIO ---
fuso_br = pytz.timezone('America/Sao_Paulo')

def obter_agora_br():
    return datetime.now(fuso_br)

# Configuração da página
st.set_page_config(page_title="Zelo Kitchen - Gestão", page_icon="🍳", layout="wide")

# --- INICIALIZAÇÃO DA SESSÃO ---
if 'historico' not in st.session_state:
    st.session_state.historico = pd.DataFrame(columns=[
        "Data", "Funcionário", "Setor", "Equipamento", "Status", "Falha", "Data_Obj"
    ])

if 'ultima_inspecao' not in st.session_state:
    st.session_state.ultima_inspecao = None

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
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, "Relatorio de Inspecao de Equipamentos", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(200, 200, 200)
    col_widths = [28, 32, 28, 42, 30, 30]
    headers = ["Data", "Funcionario", "Setor", "Equipamento", "Status", "Falha"]
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, 1, 0, 'C', True)
    pdf.ln()
    
    pdf.set_font("Arial", "", 7)
    for _, row in df.iterrows():
        # Tratamento básico de caracteres para PDF
        data = str(row['Data'])
        func = str(row['Funcionário'])[:20].encode('latin-1', 'replace').decode('latin-1')
        setor = str(row['Setor']).encode('latin-1', 'replace').decode('latin-1')
        equip = str(row['Equipamento']).encode('latin-1', 'replace').decode('latin-1')
        status = str(row['Status']).replace("✅ ", "").replace("❌ ", "")
        falha = str(row['Falha']).encode('latin-1', 'replace').decode('latin-1')
        
        pdf.cell(col_widths[0], 8, data, 1)
        pdf.cell(col_widths[1], 8, func, 1)
        pdf.cell(col_widths[2], 8, setor, 1)
        pdf.cell(col_widths[3], 8, equip, 1)
        pdf.cell(col_widths[4], 8, status, 1)
        pdf.cell(col_widths[5], 8, falha, 1)
        pdf.ln()
    return pdf.output()

# --- INTERFACE ---
st.title("🍳 Sistema de Inspeção Zelo Kitchen")

tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico de Relatórios"])

with tab1:
    if st.session_state.ultima_inspecao:
        dados = st.session_state.ultima_inspecao
        st.success(f"✅ Inspeção de {dados['setor']} salva com sucesso!")
        
        if not dados["falhas"]:
            st.info("Nenhuma não conformidade detectada.")
        else:
            texto_base = f"🚨 *NÃO CONFORMIDADES - {dados['setor']}*\n👤 *Por:* {dados['funcionario']}\n\n"
            for item in dados["falhas"]:
                texto_base += f"• *{item['Equipamento']}*: {item['Falha']}\n"
            
            c_z1, c_z2 = st.columns(2)
            url_zap = f"https://wa.me/?text={urllib.parse.quote(texto_base)}"
            c_z1.markdown(f'<a href="{url_zap}" target="_blank"><button style="width:100%; background-color:#25d366; color:white; border:none; padding:12px; border-radius:10px; font-weight:bold; cursor:pointer;">🟢 Enviar WhatsApp</button></a>', unsafe_allow_html=True)
            
            url_mail = f"mailto:?subject=Falhas {dados['setor']}&body={urllib.parse.quote(texto_base)}"
            c_z2.markdown(f'<a href="{url_mail}" target="_blank"><button style="width:100%; height:44px; background-color:#f0f2f6; border:1px solid #dcdfe3; border-radius:10px; cursor:pointer; font-weight:bold;">📧 Enviar E-mail</button></a>', unsafe_allow_html=True)
        
        st.divider()
        if st.button("🔄 INICIAR NOVA INSPEÇÃO", use_container_width=True, type="primary"):
            st.session_state.ultima_inspecao = None
            st.rerun()

    else:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            nome_input = c1.text_input("👤 Nome do Funcionário:")
            setor_sel = c2.selectbox("📍 Setor:", ["Selecione..."] + setores)

        if setor_sel != "Selecione...":
            respostas = {}
            for equip in itens_setores[setor_sel]:
                st.subheader(f"🔹 {equip}")
                col_h, col_f, col_e = st.columns(3)
                respostas[f"{equip}_H"] = col_h.radio("Higiene", ["OK", "NÃO"], key=f"{equip}h", horizontal=True)
                respostas[f"{equip}_F"] = col_f.radio("Funcionamento", ["OK", "NÃO"], key=f"{equip}f", horizontal=True)
                respostas[f"{equip}_E"] = col_e.radio("Estado Geral", ["OK", "NÃO"], key=f"{equip}e", horizontal=True)
                st.divider()
            
            if st.button("🚀 FINALIZAR E SALVAR", use_container_width=True, type="primary"):
                if not nome_input:
                    st.error("Por favor, digite seu nome.")
                else:
                    agora_br = obter_agora_br()
                    novos_registros = []
                    for equip in itens_setores[setor_sel]:
                        h, f, e = respostas[f"{equip}_H"], respostas[f"{equip}_F"], respostas[f"{equip}_E"]
                        falhas = []
                        if h == "NÃO": falhas.append("Higiene")
                        if f == "NÃO": falhas.append("Funcionamento")
                        if e == "NÃO": falhas.append("Estado Geral")
                        status = "✅ Conforme" if not falhas else "❌ Não Conforme"
                        falha_txt = "Nenhuma" if not falhas else ", ".join(falhas)
                        novos_registros.append({
                            "Data": agora_br.strftime("%d/%m/%Y %H:%M"),
                            "Funcionário": nome_input, "Setor": setor_sel, "Equipamento": equip,
                            "Status": status, "Falha": falha_txt, "Data_Obj": agora_br.date()
                        })
                    df_novos = pd.DataFrame(novos_registros)
                    st.session_state.historico = pd.concat([df_novos, st.session_state.historico], ignore_index=True)
                    st.session_state.ultima_inspecao = {"setor": setor_sel, "funcionario": nome_input, "falhas": [r for r in novos_registros if r["Status"] == "❌ Não Conforme"]}
                    st.rerun()

with tab2:
    st.header("📜 Histórico de Inspeções")
    if st.session_state.historico.empty:
        st.info("Nenhum registro ainda.")
    else:
        # Filtros Avançados
        with st.expander("🔍 Filtros de Busca"):
            f1, f2, f3, f4 = st.columns(4)
            sel_setor = f1.multiselect("Setor:", setores)
            sel_status = f2.multiselect("Status:", ["✅ Conforme", "❌ Não Conforme"])
            sel_equip = f3.multiselect("Equipamento:", options=sorted(st.session_state.historico["Equipamento"].unique()))
            sel_data = f4.date_input("Período:", value=[])

        df_f = st.session_state.historico.copy()
        if sel_setor: df_f = df_f[df_f["Setor"].isin(sel_setor)]
        if sel_status: df_f = df_f[df_f["Status"].isin(sel_status)]
        if sel_equip: df_f = df_f[df_f["Equipamento"].isin(sel_equip)]
        if isinstance(sel_data, list) and len(sel_data) == 2:
            df_f = df_f[(df_f["Data_Obj"] >= sel_data[0]) & (df_f["Data_Obj"] <= sel_data[1])]

        st.dataframe(df_f.drop(columns=["Data_Obj"]), use_container_width=True, hide_index=True)

        # --- AÇÕES DO HISTÓRICO (RESTAURADAS) ---
        st.divider()
        st.subheader("📤 Exportar Relatório Filtrado")
        h_col1, h_col2 = st.columns(2)
        
        # Botão PDF
        try:
            pdf_bytes = bytes(gerar_pdf(df_f))
            h_col1.download_button("📄 Baixar PDF do Histórico", pdf_bytes, "historico_zelo.pdf", "application/pdf", use_container_width=True)
        except Exception as e: h_col1.error(f"Erro ao gerar PDF: {e}")

        # Botão E-mail Filtrado
        resumo_email = f"Relatorio Zelo Kitchen - Extraído em {obter_agora_br().strftime('%d/%m/%Y')}\n\n"
        for _, r in df_f.iterrows():
            resumo_email += f"{r['Data']} | {r['Equipamento']} ({r['Setor']}): {r['Status']} | Falha: {r['Falha']}\n"
        
        url_mail_hist = f"mailto:?subject=Relatorio de Auditoria Kitchen&body={urllib.parse.quote(resumo_email)}"
        h_col2.markdown(f'<a href="{url_mail_hist}" target="_blank"><button style="width:100%; height:44px; background-color:#e1e4e8; border:1px solid #bcbfc2; border-radius:10px; cursor:pointer; font-weight:bold;">📧 Enviar Histórico por E-mail</button></a>', unsafe_allow_html=True)

        if st.button("🗑️ Resetar Todo o Histórico", use_container_width=True):
            st.session_state.historico = pd.DataFrame(columns=["Data", "Funcionário", "Setor", "Equipamento", "Status", "Falha", "Data_Obj"])
            st.rerun()

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
        data = str(row['Data']).encode('latin-1', 'replace').decode('latin-1')
        func = str(row['Funcionário']).encode('latin-1', 'replace').decode('latin-1')
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
    with st.container(border=True):
        c1, c2 = st.columns(2)
        nome_input = c1.text_input("👤 Nome do Funcionário:")
        setor_sel = c2.selectbox("📍 Setor:", ["Selecione..."] + setores)

    if setor_sel != "Selecione...":
        with st.form("form_checklist"):
            respostas = {}
            lista_equip_atual = itens_setores[setor_sel]
            for equip in lista_equip_atual:
                st.subheader(f"🔹 {equip}")
                col_h, col_f, col_e = st.columns(3)
                respostas[f"{equip}_H"] = col_h.radio("Higiene", ["OK", "NÃO"], key=f"{equip}h", horizontal=True)
                respostas[f"{equip}_F"] = col_f.radio("Funcionamento", ["OK", "NÃO"], key=f"{equip}f", horizontal=True)
                respostas[f"{equip}_E"] = col_e.radio("Estado Geral", ["OK", "NÃO"], key=f"{equip}e", horizontal=True)
                st.divider()
            submit_btn = st.form_submit_button("🚀 Salvar Inspeção")

        if submit_btn:
            if not nome_input:
                st.error("Digite o nome do funcionário!")
            else:
                agora_br = obter_agora_br()
                data_str = agora_br.strftime("%d/%m/%Y %H:%M")
                novos_registros = []
                for equip in lista_equip_atual:
                    h, f, e = respostas.get(f"{equip}_H"), respostas.get(f"{equip}_F"), respostas.get(f"{equip}_E")
                    falhas_lista = []
                    if h == "NÃO": falhas_lista.append("Higiene")
                    if f == "NÃO": falhas_lista.append("Funcionamento")
                    if e == "NÃO": falhas_lista.append("Estado Geral")
                    status = "✅ Conforme" if not falhas_lista else "❌ Não Conforme"
                    falha_txt = "Nenhuma" if not falhas_lista else ", ".join(falhas_lista)
                    novos_registros.append({
                        "Data": data_str, "Funcionário": nome_input, "Setor": setor_sel,
                        "Equipamento": equip, "Status": status, "Falha": falha_txt, "Data_Obj": agora_br.date()
                    })
                df_novos = pd.DataFrame(novos_registros)
                st.session_state.historico = pd.concat([df_novos, st.session_state.historico], ignore_index=True)
                st.session_state.ultima_inspecao = {"setor": setor_sel, "funcionario": nome_input, "falhas": [r for r in novos_registros if r["Status"] == "❌ Não Conforme"]}
                st.success(f"✅ Inspeção salva às {agora_br.strftime('%H:%M')}!")

    if st.session_state.ultima_inspecao:
        st.divider()
        st.subheader("📲 Comunicar Não Conformidades")
        dados = st.session_state.ultima_inspecao
        
        if not dados["falhas"]:
            st.info("Tudo em conformidade nesta inspeção.")
        else:
            texto_zap = f"🚨 *NÃO CONFORMIDADES - {dados['setor']}*\n👤 *Por:* {dados['funcionario']}\n\n"
            for item in dados["falhas"]: texto_zap += f"• *{item['Equipamento']}*: {item['Falha']}\n"
            cz1, cz2 = st.columns(2)
            cz1.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(texto_zap)}" target="_blank"><button style="width:100%; background-color:#25d366; color:white; border:none; padding:12px; border-radius:10px; font-weight:bold; cursor:pointer;">🟢 Enviar por WhatsApp</button></a>', unsafe_allow_html=True)
            cz2.markdown(f'<a href="mailto:?subject=Falhas - {dados["setor"]}&body={urllib.parse.quote(texto_zap)}" target="_blank"><button style="width:100%; height:44px; background-color:#f0f2f6; border:1px solid #dcdfe3; border-radius:10px; cursor:pointer; font-weight:bold;">📧 Enviar por E-mail</button></a>', unsafe_allow_html=True)
        
        # O BOTÃO QUE VOCÊ PEDIU: AGORA ELE ATUALIZA A PÁGINA COMPLETAMENTE
        if st.button("🔄 Iniciar Nova Limpa", use_container_width=True):
            st.session_state.ultima_inspecao = None
            st.rerun()

with tab2:
    st.header("📜 Histórico de Inspeções")
    if st.session_state.historico.empty:
        st.info("Nenhum dado registrado.")
    else:
        with st.expander("🔍 Filtros de Consulta", expanded=True):
            f1, f2, f3, f4 = st.columns(4)
            sel_setor = f1.multiselect("Setor:", options=sorted(st.session_state.historico["Setor"].unique()))
            sel_status = f2.multiselect("Status:", options=sorted(st.session_state.historico["Status"].unique()))
            sel_equip = f3.multiselect("Equipamento:", options=sorted(st.session_state.historico["Equipamento"].unique()))
            sel_data = f4.date_input("Período:", value=[])

        df_f = st.session_state.historico.copy()
        if sel_setor: df_f = df_f[df_f["Setor"].isin(sel_setor)]
        if sel_status: df_f = df_f[df_f["Status"].isin(sel_status)]
        if sel_equip: df_f = df_f[df_f["Equipamento"].isin(sel_equip)]
        if isinstance(sel_data, list) and len(sel_data) == 2:
            df_f = df_f[(df_f["Data_Obj"] >= sel_data[0]) & (df_f["Data_Obj"] <= sel_data[1])]

        st.dataframe(df_f[["Data", "Funcionário", "Setor", "Equipamento", "Status", "Falha"]], use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("📤 Exportar Relatório Filtrado")
        e1, e2 = st.columns(2)
        
        try:
            pdf_b = bytes(gerar_pdf(df_f))
            e1.download_button("📄 Baixar PDF do Histórico", pdf_b, "historico.pdf", "application/pdf", use_container_width=True)
        except Exception as err: e1.error(f"Erro PDF: {err}")

        resumo_filtrado = f"Relatorio Filtrado Zelo Kitchen - {obter_agora_br().strftime('%d/%m/%Y')}\n\n"
        for _, r in df_f.iterrows():
            resumo_filtrado += f"{r['Data']} | {r['Equipamento']} ({r['Setor']}): {r['Status']} | Falha: {r['Falha']}\n"
        
        url_mail_filtrado = f"mailto:?subject=Relatorio Filtrado Kitchen&body={urllib.parse.quote(resumo_filtrado)}"
        e2.markdown(f'<a href="{url_mail_filtrado}" target="_blank"><button style="width:100%; height:44px; background-color:#e1e4e8; border:1px solid #bcbfc2; border-radius:10px; cursor:pointer; font-weight:bold;">📧 Enviar Histórico Filtrado por E-mail</button></a>', unsafe_allow_html=True)

        if st.button("🗑️ Resetar Tudo"):
            st.session_state.historico = pd.DataFrame(columns=["Data", "Funcionário", "Setor", "Equipamento", "Status", "Falha", "Data_Obj"])
            st.session_state.ultima_inspecao = None
            st.rerun()

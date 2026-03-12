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

# --- INICIALIZAÇÃO DA SESSÃO (Crucial para não perder dados) ---
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
        pdf.cell(col_widths[0], 8, str(row['Data']), 1)
        pdf.cell(col_widths[1], 8, str(row['Funcionário'])[:20], 1)
        pdf.cell(col_widths[2], 8, str(row['Setor']), 1)
        pdf.cell(col_widths[3], 8, str(row['Equipamento']), 1)
        pdf.cell(col_widths[4], 8, str(row['Status']), 1)
        pdf.cell(col_widths[5], 8, str(row['Falha']), 1)
        pdf.ln()
    return pdf.output()

# --- INTERFACE ---
st.title("🍳 Sistema de Inspeção Zelo Kitchen")

tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico de Relatórios"])

with tab1:
    # Se já houve uma inspeção, mostra o resumo e botões de envio
    if st.session_state.ultima_inspecao:
        dados = st.session_state.ultima_inspecao
        st.success(f"✅ Inspeção de {dados['setor']} salva com sucesso!")
        
        if not dados["falhas"]:
            st.info("Nenhuma não conformidade detectada.")
        else:
            st.warning(f"Foram encontradas {len(dados['falhas'])} falhas.")
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
        # Modo de Preenchimento
        with st.container(border=True):
            c1, c2 = st.columns(2)
            nome_input = c1.text_input("👤 Nome do Funcionário:", key="nome_func")
            setor_sel = c2.selectbox("📍 Setor:", ["Selecione..."] + setores, key="setor_ativo")

        if setor_sel != "Selecione...":
            respostas = {}
            for equip in itens_setores[setor_sel]:
                st.subheader(f"🔹 {equip}")
                col_h, col_f, col_e = st.columns(3)
                respostas[f"{equip}_H"] = col_h.radio("Higiene", ["OK", "NÃO"], key=f"{equip}h")
                respostas[f"{equip}_F"] = col_f.radio("Funcionamento", ["OK", "NÃO"], key=f"{equip}f")
                respostas[f"{equip}_E"] = col_e.radio("Estado Geral", ["OK", "NÃO"], key=f"{equip}e")
                st.divider()
            
            # BOTÃO DE SALVAR FORA DE UM st.form PARA EVITAR TRAVAMENTOS
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
                        
                        registro = {
                            "Data": agora_br.strftime("%d/%m/%Y %H:%M"),
                            "Funcionário": nome_input,
                            "Setor": setor_sel,
                            "Equipamento": equip,
                            "Status": status,
                            "Falha": falha_txt,
                            "Data_Obj": agora_br.date()
                        }
                        novos_registros.append(registro)
                    
                    # Salva no histórico
                    df_novos = pd.DataFrame(novos_registros)
                    st.session_state.historico = pd.concat([df_novos, st.session_state.historico], ignore_index=True)
                    
                    # Define a última inspeção e RECARREGA para mostrar os botões de envio
                    st.session_state.ultima_inspecao = {
                        "setor": setor_sel,
                        "funcionario": nome_input,
                        "falhas": [r for r in novos_registros if r["Status"] == "❌ Não Conforme"]
                    }
                    st.rerun()

with tab2:
    st.header("📜 Histórico")
    if st.session_state.historico.empty:
        st.info("Nenhum registro ainda.")
    else:
        # Filtros
        with st.expander("🔍 Filtros"):
            f1, f2 = st.columns(2)
            sel_setor = f1.multiselect("Setor:", setores)
            sel_status = f2.multiselect("Status:", ["✅ Conforme", "❌ Não Conforme"])
        
        df_f = st.session_state.historico.copy()
        if sel_setor: df_f = df_f[df_f["Setor"].isin(sel_setor)]
        if sel_status: df_f = df_f[df_f["Status"].isin(sel_status)]
        
        st.dataframe(df_f.drop(columns=["Data_Obj"]), use_container_width=True, hide_index=True)
        
        # Ações do Histórico
        c_e1, c_e2 = st.columns(2)
        try:
            pdf_data = bytes(gerar_pdf(df_f))
            c_e1.download_button("📄 Baixar PDF", pdf_data, "relatorio.pdf", "application/pdf", use_container_width=True)
        except: pass
        
        if c_e2.button("🗑️ Limpar Tudo", use_container_width=True):
            st.session_state.historico = pd.DataFrame(columns=["Data", "Funcionário", "Setor", "Equipamento", "Status", "Falha", "Data_Obj"])
            st.rerun()

import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
from fpdf import FPDF
import pytz
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO DE FUSO HORÁRIO ---
fuso_br = pytz.timezone('America/Sao_Paulo')

def obter_agora_br():
    return datetime.now(fuso_br)

# Configuração da página
st.set_page_config(page_title="Zelo Kitchen - Nuvem", page_icon="🍳", layout="wide")

# --- CONEXÃO GOOGLE SHEETS ---
# Configuração via Secrets (URL da planilha)
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    return conn.read(ttl="0") # ttl=0 força a leitura do dado mais recente

if 'ultima_inspecao' not in st.session_state:
    st.session_state.ultima_inspecao = None

# --- DADOS ESTÁTICOS ---
setores = ["Espaço Café", "Cozinha", "Mirante", "Refeitório"]
itens_setores = {
    "Espaço Café": ["Estufa quente", "Estufa fria", "Geladeiras balcão", "Frigobares", "Máquina de café expresso"],
    "Cozinha": ["Geladeiras Bacio di Latte", "Geladeiras Resfriados", "Câmaras Frias", "Freezers Horizontais", "Fornos", "Fogões", "Fritadeiras", "Chapas", "Geladeiras Balcões", "Coifas", "Pista Fria"],
    "Mirante": ["Freezer Sorvete Dona Mazza", "Adega Vinhos", "Geladeiras", "Geladeiras Balcões", "Lava Louças", "Coifas", "Pista Fria", "Elevador Monta Carga", "Freezer Horizontal", "Churrasqueira", "Forno a Lenha"],
    "Refeitório": ["Lava Louças", "Geladeira Resfriados", "Rechaud"]
}

# --- INTERFACE ---
st.title("🍳 Sistema de Inspeção Zelo Kitchen (Nuvem)")

tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico Permanente"])

with tab1:
    if st.session_state.ultima_inspecao:
        dados = st.session_state.ultima_inspecao
        st.success(f"✅ Inspeção salva no Google Sheets!")
        
        if dados["falhas"]:
            texto_base = f"🚨 *NÃO CONFORMIDADES - {dados['setor']}*\n👤 *Por:* {dados['funcionario']}\n\n"
            for item in dados["falhas"]:
                texto_base += f"• *{item['Equipamento']}*: {item['Falha']}\n"
            
            c_z1, c_z2 = st.columns(2)
            url_zap = f"https://wa.me/?text={urllib.parse.quote(texto_base)}"
            c_z1.markdown(f'<a href="{url_zap}" target="_blank"><button style="background-color:#25d366; color:white; width:100%; border:none; padding:12px; border-radius:10px; font-weight:bold; cursor:pointer;">🟢 Enviar WhatsApp</button></a>', unsafe_allow_html=True)
            
            url_mail = f"mailto:?subject=Falhas {dados['setor']}&body={urllib.parse.quote(texto_base)}"
            c_z2.markdown(f'<a href="{url_mail}" target="_blank"><button style="width:100%; height:44px; background-color:#f0f2f6; border:1px solid #dcdfe3; border-radius:10px; cursor:pointer; font-weight:bold;">📧 Enviar E-mail</button></a>', unsafe_allow_html=True)
        
        if st.button("🔄 INICIAR NOVA INSPEÇÃO", use_container_width=True):
            st.session_state.ultima_inspecao = None
            st.rerun()

    else:
        nome_input = st.text_input("👤 Nome do Funcionário:")
        setor_sel = st.selectbox("📍 Setor:", ["Selecione..."] + setores)

        if setor_sel != "Selecione...":
            respostas = {}
            for equip in itens_setores[setor_sel]:
                st.subheader(f"🔹 {equip}")
                ch, cf, ce = st.columns(3)
                respostas[f"{equip}_H"] = ch.radio("Higiene", ["OK", "NÃO"], key=f"{equip}h", horizontal=True)
                respostas[f"{equip}_F"] = cf.radio("Funcionamento", ["OK", "NÃO"], key=f"{equip}f", horizontal=True)
                respostas[f"{equip}_E"] = ce.radio("Estado Geral", ["OK", "NÃO"], key=f"{equip}e", horizontal=True)
            
            if st.button("🚀 SALVAR NA NUVEM", use_container_width=True, type="primary"):
                if not nome_input:
                    st.error("Digite seu nome!")
                else:
                    agora_br = obter_agora_br()
                    novos_dados = []
                    for equip in itens_setores[setor_sel]:
                        h, f, e = respostas[f"{equip}_H"], respostas[f"{equip}_F"], respostas[f"{equip}_E"]
                        falhas = [n for n, v in zip(["Higiene", "Funcionamento", "Estado Geral"], [h, f, e]) if v == "NÃO"]
                        
                        novos_dados.append({
                            "Data": agora_br.strftime("%d/%m/%Y %H:%M"),
                            "Funcionário": nome_input,
                            "Setor": setor_sel,
                            "Equipamento": equip,
                            "Status": "✅ Conforme" if not falhas else "❌ Não Conforme",
                            "Falha": "Nenhuma" if not falhas else ", ".join(falhas),
                            "Data_Obj": agora_br.strftime("%Y-%m-%d")
                        })
                    
                    # ENVIAR PARA O GOOGLE SHEETS
                    df_existente = carregar_dados()
                    df_final = pd.concat([pd.DataFrame(novos_dados), df_existente], ignore_index=True)
                    conn.update(data=df_final)
                    
                    st.session_state.ultima_inspecao = {
                        "setor": setor_sel, "funcionario": nome_input, 
                        "falhas": [r for r in novos_dados if r["Status"] == "❌ Não Conforme"]
                    }
                    st.rerun()

with tab2:
    st.header("📜 Histórico Permanente (Google Sheets)")
    df_sheets = carregar_dados()
    
    if df_sheets.empty:
        st.info("Planilha vazia.")
    else:
        # Filtros
        f1, f2 = st.columns(2)
        filt_setor = f1.multiselect("Filtrar Setor:", setores)
        filt_status = f2.multiselect("Filtrar Status:", ["✅ Conforme", "❌ Não Conforme"])
        
        df_view = df_sheets.copy()
        if filt_setor: df_view = df_view[df_view["Setor"].isin(filt_setor)]
        if filt_status: df_view = df_view[df_view["Status"].isin(filt_status)]
        
        st.dataframe(df_view, use_container_width=True, hide_index=True)
        
        # Botão E-mail Histórico
        resumo_h = f"Relatorio Auditoria - {obter_agora_br().strftime('%d/%m/%Y')}\n\n"
        for _, r in df_view.head(50).iterrows(): # Limite de 50 para o link não quebrar
            resumo_h += f"{r['Data']} | {r['Equipamento']}: {r['Status']}\n"
        
        url_mail_h = f"mailto:?subject=Historico Kitchen&body={urllib.parse.quote(resumo_h)}"
        st.markdown(f'<a href="{url_mail_h}" target="_blank"><button style="width:100%; height:40px; border-radius:10px; cursor:pointer;">📧 Enviar Histórico por E-mail</button></a>', unsafe_allow_html=True)

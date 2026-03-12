import streamlit as st
from datetime import datetime
import urllib.parse

# Configuração da página para Mobile-First
st.set_page_config(
    page_title="Checklist Inspeção", 
    page_icon="🍳",
    layout="centered"
)

# CSS para melhorar a visualização no celular
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.2rem; }
    .stRadio > div { flex-direction: row !important; gap: 10px; }
    .stRadio label { 
        background: #f0f2f6; 
        padding: 5px 15px; 
        border-radius: 5px; 
        border: 1px solid #ddd;
    }
    </style>
    """, unsafe_allow_html=True)

setores = {
    "Espaço Café": ["Estufa quente", "Estufa fria", "Geladeiras balcão", "Frigobares", "Máquina de café expresso"],
    "Cozinha": ["Geladeiras Bacio di Latte", "Geladeiras Resfriados", "Câmaras Frias", "Freezers Horizontais", "Fornos", "Fogões", "Fritadeiras", "Chapas", "Geladeiras Balcões", "Coifas", "Pista Fria"],
    "Mirante": ["Freezer Sorvete Dona Mazza", "Adega Vinhos", "Geladeiras", "Geladeiras Balcões", "Lava Louças", "Coifas", "Pista Fria", "Elevador Monta Carga", "Freezer Horizontal", "Churrasqueira", "Forno a Lenha"],
    "Refeitório": ["Lava Louças", "Geladeira Resfriados", "Rechaud"]
}

st.title("🍳 Inspeção de Equipamentos")

# Alerta de Irregularidade
st.warning("⚠️ QUALQUER IRREGULARIDADE GRAVE DEVE SER REPORTADA IMEDIATAMENTE!")

# Identificação
col1, col2 = st.columns(2)
with col1:
    nome = st.text_input("👤 Nome:")
with col2:
    setor_sel = st.selectbox("📍 Local:", ["Selecione..."] + list(setores.keys()))

if setor_sel != "Selecione...":
    respostas = {}
    
    with st.form("form_checklist"):
        for equip in setores[setor_sel]:
            st.markdown(f"#### {equip}")
            # Layout em colunas para os critérios
            c1, c2, c3 = st.columns(3)
            with c1:
                respostas[f"{equip}_Higiene"] = st.radio("Higiene", ["OK", "NÃO"], key=f"{equip}1", horizontal=True)
            with c2:
                respostas[f"{equip}_Func."] = st.radio("Funcionamento", ["OK", "NÃO"], key=f"{equip}2", horizontal=True)
            with c3:
                respostas[f"{equip}_Geral"] = st.radio("Estado Geral", ["OK", "NÃO"], key=f"{equip}3", horizontal=True)
            st.write("---")
            
        submit = st.form_submit_button("🚀 FINALIZAR E GERAR WHATSAPP")

    if submit:
        if not nome:
            st.error("Por favor, digite seu nome.")
        else:
            # Lógica do relatório
            relatorio = f"🚨 *IRREGULARIDADES - {setor_sel}*\n"
            relatorio += f"👤 *Por:* {nome}\n"
            relatorio += f"📅 *Data:* {datetime.now().strftime('%d/%m/%Y')}\n\n"
            
            tem_problema = False
            for chave, valor in respostas.items():
                if valor == "NÃO":
                    tem_problema = True
                    item, crit = chave.split("_")
                    relatorio += f"❌ *{item}*\n   👉 Falha em: {crit}\n"
            
            if not tem_problema:
                relatorio += "✅ Tudo em conformidade!"

            # Botão do WhatsApp
            texto_url = urllib.parse.quote(relatorio)
            st.success("Relatório gerado!")
            st.markdown(f"""
                <a href="https://wa.me/?text={texto_url}" target="_blank">
                    <button style="width:100%; background-color:#25d366; color:white; border:none; padding:15px; border-radius:10px; font-weight:bold; cursor:pointer;">
                        🟢 ENVIAR PARA WHATSAPP
                    </button>
                </a>
                """, unsafe_allow_html=True)
            
            st.info("Cópia do texto para revisão:")
            st.code(relatorio)

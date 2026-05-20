import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import urllib.parse
from fpdf import FPDF

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Zelo Kitchen - Inspeção", page_icon="🍳", layout="wide")

# CSS para interface geral e botões do Streamlit
st.markdown("""
    <style>
        .main { background-color: #f9f9f9; }
        .stButton>button { border-radius: 5px; height: 3em; width: 100%; }
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
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
        df["original_index"] = df.index
        
        if "Resolução" in df.columns:
            df["Resolução"] = df["Resolução"].fillna("").astype(str).str.strip()
        else:
            df["Resolução"] = ""
        
        if not df.empty and "Data/Hora" in df.columns:
            df_dt = pd.to_datetime(df["Data/Hora"], dayfirst=True, errors='coerce')
            df["Data_Exibicao"] = df_dt.dt.strftime('%d/%m/%Y')
            df["Hora_Exibicao"] = df_dt.dt.strftime('%H:%M')
        else:
            df["Data_Exibicao"] = ""
            df["Hora_Exibicao"] = ""
        
        colunas_desejadas = ["Data_Exibicao", "Hora_Exibicao", "Funcionário", "Setor", "Equipamento", "Status", "Falhas", "Descrição do Problema", "Resolução", "original_index"]
        return df[[c for c in colunas_desejadas if c in df.columns]]
    except Exception as e:
        return pd.DataFrame(columns=["Data_Exibicao", "Hora_Exibicao", "Funcionário", "Setor", "Equipamento", "Status", "Falhas", "Descrição do Problema", "Resolução", "original_index"])

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
        res_text = f"\nSolucao: {row.get('Resolução')}" if row.get('Resolução') else "\nStatus: PENDENTE"
        pdf.multi_cell(190, 7, f"Data: {row.get('Data_Exibicao', '')} {row.get('Hora_Exibicao', '')}\nInspetor: {row.get('Funcionário', '')}\nFalha: {row.get('Falhas', '')}\nDescricao: {desc}{res_text}")
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

# --- ESTRUTURA DO CHECKLIST ---
setores_lista = ["Espaço Café", "Cozinha", "Mirante", "Refeitório", "Bar Varanda Alta", "Lanchonete", "Sushi"]
itens_setores = {
    "Espaço Café": ["Máquina de Suco", "Estufa quente", "Estufa fria", "Geladeiras balcão", "Frigobares", "Máquina de café expresso"],
    "Cozinha": ["Geladeiras Bacio di Latte", "Geladeiras Resfriados", "Câmaras Frias", "Freezers Horizontais", "Fornos", "Fogões", "Fritadeiras", "Chapas", "Geladeiras Balcões", "Coifas", "Pista Fria", "Banho Maria", "Máquina de Suco"],
    "Mirante": ["Máquina de Suco", "Freezer Sorvete Dona Mazza", "Adega Vinhos", "Geladeiras", "Geladeiras Balcões", "Lava Louças", "Coifas", "Pista Fria", "Elevador Monta Carga", "Freezer Horizontal", "Churrasqueira", "Forno a Lenha"],
    "Refeitório": ["Lava Louças", "Geladeira Resfriados", "Rechaud"],
    "Bar Varanda Alta": ["Geladeira Bancada", "Freezer Bancada", "Máquina de Gelo"],
    "Lanchonete": ["Geladeira Bacio de Latte", "Geladeiras Cervejas", "Máquina de Café", "Choppeira", "Estufa Salgados"],
    "Sushi": ["Fogão", "Freezer Horizontal", "Geladeira Bancada", "Estufa Fria"]
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
                    e = c3.radio(f"Estado Geral", ["OK", "NÃO"], key=f"e_{item}", horizontal=True)
                    
                    detalhes_obs = ""
                    if any(x == "NÃO" for x in [h, f, e]):
                        detalhes_obs = st.text_area(f"Descreva o problema:", key=f"obs_{item}")
                    
                    respostas.append({"Equipamento": item, "H": h, "F": f, "E": e, "Detalhes": detalhes_obs})

            if st.button("🚀 FINALIZAR E SALVAR", type="primary"):
                if not nome_inspetor:
                    st.error("Por favor, preencha o nome do inspetor.")
                else:
                    with st.spinner("Salvando dados..."):
                        agora = obter_agora_br().strftime("%d/%m/%Y %H:%M")
                        novas_entradas = []
                        for r in respostas:
                            f_list = [n for n, v in zip(["Higiene", "Funcionamento", "Estado"], [r["H"], r["F"], r["E"]]) if v == "NÃO"]
                            novas_entradas.append({
                                "Data": "", "Funcionário": nome_inspetor, "Setor": setor_selecionado,
                                "Equipamentos": "", "Status": "❌ FALHA" if f_list else "✅ OK",
                                "Falha": "", "Data_Obj": "", "Data/Hora": agora, 
                                "Equipamento": r["Equipamento"], "Falhas": ", ".join(f_list) if f_list else "Nenhuma", 
                                "Descrição do Problema": r["Detalhes"], "Resolução": ""
                            })
                        
                        try:
                            df_atual = conn.read(ttl=0)
                            df_final = pd.concat([df_atual, pd.DataFrame(novas_entradas)], ignore_index=True)
                            conn.update(data=df_final)
                            st.session_state.sucesso = True
                            st.rerun()
                        except Exception as ex:
                            if "200" in str(ex): st.session_state.sucesso = True; st.rerun()
                            else: st.error(f"Erro ao salvar: {ex}")

# --- ABA 2: PAINEL DE PENDÊNCIAS E HISTÓRICO ---
with tab2:
    df_hist = carregar_dados()
    
    if not df_hist.empty:
        with st.expander("🔍 Filtros de Busca", expanded=True):
            col_v1, col_v2, col_v3 = st.columns(3)
            tipo_visao = col_v1.radio("Visualização:", ["🔴 Apenas Pendentes", "🟢 Apenas Solucionados", "📋 Todos os Registros"], horizontal=True)
            f_set = col_v2.multiselect("Setores", options=setores_lista, default=setores_lista)
            f_sta = col_v3.multiselect("Status", options=["✅ OK", "❌ FALHA"], default=["❌ FALHA"])

            col_d1, col_d2 = st.columns(2)
            df_hist["dt_temp"] = pd.to_datetime(df_hist["Data_Exibicao"], dayfirst=True, errors='coerce').dt.date
            data_min = df_hist["dt_temp"].dropna().min() if not df_hist["dt_temp"].dropna().empty else obter_agora_br().date()
            data_max = df_hist["dt_temp"].dropna().max() if not df_hist["dt_temp"].dropna().empty else obter_agora_br().date()
            d_ini = col_d1.date_input("Início", value=data_min)
            d_fim = col_d2.date_input("Fim", value=data_max)

        mask = (df_hist["dt_temp"] >= d_ini) & (df_hist["dt_temp"] <= d_fim) & \
               (df_hist["Setor"].isin(f_set)) & (df_hist["Status"].isin(f_sta))
        
        if tipo_visao == "🔴 Apenas Pendentes":
            mask = mask & (df_hist["Resolução"] == "")
        elif tipo_visao == "🟢 Apenas Solucionados":
            mask = mask & (df_hist["Resolução"] != "")
        
        df_filtrado = df_hist[mask].drop(columns=["dt_temp"]).sort_values(by=["Data_Exibicao", "Hora_Exibicao"], ascending=False)

        st.markdown("---")
        st.subheader(f"📋 {tipo_visao}")
        
        if not df_filtrado.empty:
            # TABELA HTML CUSTOMIZADA COM FORÇAMENTO DE QUEBRA DE LINHA DINÂMICA
            html_tabela = f"""
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
            <style>
                body {{ background-color: transparent !important; font-family: sans-serif; }}
                th {{ background-color: #2c3e50 !important; color: white !important; font-size: 14px; position: sticky; top: 0; padding: 12px 10px !important; text-align: left; }}
                td {{ font-size: 13px; vertical-align: middle; padding: 10px 8px !important; }}
                
                /* Força a quebra total automática do texto na célula da Descrição */
                .celula-descricao {{
                    white-space: normal !important;
                    word-wrap: break-word !important;
                    overflow-wrap: break-word !important;
                    min-width: 300px;
                }}
                
                .table-container {{ max-height: 480px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 4px; }}
                .badge-resolvido {{ background-color: #198754; color: white; padding: 6px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
            </style>
            <div class="table-container">
                <table class="table table-striped table-hover m-0">
                    <thead>
                        <tr>
                            <th>Data</th><th>Hora</th><th>Funcionário</th><th>Setor</th><th>Equipamento</th><th>Status</th><th>Falhas</th><th style="min-width: 300px;">Descrição do Problema</th><th>Histórico de Resolução</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for _, row in df_filtrado.iterrows():
                desc_p = str(row.get('Descrição do Problema', '')) if pd.notna(row.get('Descrição do Problema')) else ""
                resolucao_p = str(row.get('Resolução', '')) if pd.notna(row.get('Resolução')) else ""
                
                res_status_col = f"<span class='badge-resolvido'>{resolucao_p}</span>" if resolucao_p else "<span class='text-muted'>Pendente</span>"

                html_tabela += f"""
                        <tr>
                            <td style="white-space: nowrap !important;">{row.get('Data_Exibicao','')}</td>
                            <td>{row.get('Hora_Exibicao','')}</td>
                            <td>{row.get('Funcionário','')}</td>
                            <td>{row.get('Setor','')}</td>
                            <td>{row.get('Equipamento','')}</td>
                            <td>{row.get('Status','')}</td>
                            <td>{row.get('Falhas','')}</td>
                            <td class="celula-descricao">{desc_p}</td>
                            <td style="min-width: 160px;">{res_status_col}</td>
                        </tr>
                """
            html_tabela += "</tbody></table></div>"
            
            # Renderiza o visual clássico perfeitamente ajustado
            st.components.v1.html(html_tabela, height=500, scrolling=False)
            
            # QUADRADINHOS DE CHECKBOX DO STREAMLIT (SISTEMA DE BAIXAS LOGO ABAIXO DA TABELA)
            if tipo_visao == "🔴 Apenas Pendentes":
                st.markdown("### 📋 Seleção de Itens Concluídos")
                st.caption("Marque os itens resolvidos na lista abaixo e clique no botão para atualizar a planilha:")
                
                itens_selecionados = []
                for _, row in df_filtrado.iterrows():
                    label_item = f"🔧 {row['Data_Exibicao']} {row['Hora_Exibicao']} - {row['Equipamento']} ({row['Setor']})"
                    if st.checkbox(label_item, key=f"chk_pure_{row['original_index']}"):
                        itens_selecionados.append(int(row['original_index']))
                
                if st.button("💾 CONFIRMAR SOLUÇÃO DOS ITENS MARCADOS", type="primary"):
                    if itens_selecionados:
                        with st.spinner("Gravando alterações no Google Sheets..."):
                            data_solucao = obter_agora_br().strftime("%d/%m/%Y %H:%M")
                            
                            df_sheets = conn.read(ttl=0)
                            df_sheets = df_sheets.loc[:, ~df_sheets.columns.str.contains('^Unnamed')]
                            df_sheets["Resolução"] = df_sheets["Resolução"].fillna("").astype(str)
                            
                            for idx_alvo in itens_selecionados:
                                df_sheets.loc[idx_alvo, "Resolução"] = f"Solucionado em {data_solucao}"
                            
                            conn.update(data=df_sheets)
                            st.success("🎉 Itens atualizados com sucesso!")
                            st.rerun()
                    else:
                        st.warning("Nenhum item foi selecionado. Marque os quadradinhos acima primeiro.")
        else:
            st.info("Nenhum registro encontrado para os filtros selecionados.")

# --- SEÇÃO DE RELATÓRIO ---
        st.divider()
        st.subheader("📊 Enviar Relatório de Não Conformidades")
        st.info("💡 **Aviso:** O relatório enviado será baseado exclusivamente no conteúdo **filtrado** na tabela acima.")
        
        if not df_filtrado.empty:
            df_enviar = df_filtrado.copy()
            if "original_index" in df_enviar.columns:
                df_enviar = df_enviar.drop(columns=["original_index"])
                
            texto_rel = f"*RELATÓRIO ZELO KITCHEN - {obter_agora_br().strftime('%d/%m/%Y')}*\n"
            texto_rel += f"Filtro: {tipo_visao}\n\n"
            
            for _, row in df_enviar.iterrows():
                res_status = f"\n✅ {row['Resolução']}" if row['Resolução'] != "" else "\n🔴 Status: Pendente"
                texto_rel += f"⚠️ *{row['Equipamento']}* ({row['Setor']})\nFalha: {row['Falhas']}\nObs: {row['Descrição do Problema']}{res_status}\n---\n"
            
            col_rel1, col_rel2, col_rel3 = st.columns(3)
            col_rel1.link_button("🟢 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(texto_rel)}", use_container_width=True)
            col_rel2.link_button("📧 E-mail", f"mailto:?subject=Relatorio_Zelo_Kitchen&body={urllib.parse.quote(texto_rel)}", use_container_width=True)
            col_rel3.download_button("📥 PDF", gerar_pdf(df_enviar), f"Relatorio_{obter_agora_br().strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True)
        else:
            st.warning("Não há falhas para exibir com os filtros atuais.")
    else:
        st.info("Nenhum registro encontrado.")

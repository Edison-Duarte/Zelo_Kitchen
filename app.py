import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import urllib.parse
from fpdf import FPDF
import io

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Zelo Kitchen - Inspeção", page_icon="🍳", layout="wide")

# CSS para interface geral, botões e detecção/ajuste de visualização mobile
st.markdown("""
    <style>
        .main { background-color: #f9f9f9; }
        .stButton>button { border-radius: 5px; height: 3em; width: 100%; }
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        
        /* Estilização dos Cards Mobile de Pendências */
        .mobile-card {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-left: 5px solid #dc3545;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .mobile-card-title {
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 8px;
        }
        .mobile-card-meta {
            font-size: 12px;
            color: #6c757d;
            margin-bottom: 10px;
        }
        .mobile-card-desc {
            font-size: 14px;
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            border: 1px dashed #dee2e6;
            word-break: break-word;
            white-space: pre-wrap;
        }
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
        df_limpo = df[[c for c in colunas_desejadas if c in df.columns]]
        return df_limpo
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
                                "Data": "", 
                                "Funcionário": nome_inspetor, "Setor": setor_selecionado,
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

        # Aplicação dos filtros de dados
        mask = (df_hist["dt_temp"] >= d_ini) & (df_hist["dt_temp"] <= d_fim) & \
               (df_hist["Setor"].isin(f_set)) & (df_hist["Status"].isin(f_sta))
        
        if tipo_visao == "🔴 Apenas Pendentes":
            mask = mask & (df_hist["Resolução"] == "")
        elif tipo_visao == "🟢 Apenas Solucionados":
            mask = mask & (df_hist["Resolução"] != "")
        
        df_filtrado = df_hist[mask].drop(columns=["dt_temp"]).sort_values(by=["Data_Exibicao", "Hora_Exibicao"], ascending=False)

        st.markdown("---")
        
        # MODO INTERATIVO (Dar baixa nas Pendências)
        if tipo_visao == "🔴 Apenas Pendentes":
            st.subheader("🚨 Lista de Pendências em Aberto")
            
            if not df_filtrado.empty:
                # Seletor para alternar modo de exibição caso o usuário prefira forçar o modo tabela
                modo_exibicao = st.radio("Formato de exibição:", ["Layout Mobile (Cards)", "Tabela Completa (PC)"], horizontal=True, label_visibility="collapsed")
                
                if modo_exibicao == "Layout Mobile (Cards)":
                    st.caption("Selecione abaixo os equipamentos que deseja solucionar e confirme no botão vermelho:")
                    
                    # Cria opções amigáveis para o Mobile Select baseadas no índice original
                    opcoes_fáceis = {}
                    for _, r in df_filtrado.iterrows():
                        label_item = f"⚠️ {r['Equipamento']} ({r['Setor']}) - {r['Data_Exibicao']}"
                        opcoes_fáceis[label_item] = int(r["original_index"])
                    
                    itens_selecionados_mobile = st.multiselect("Toque para escolher um ou mais itens corrigidos:", options=list(opcoes_fáceis.keys()))
                    
                    # Renderiza os blocos visuais das pendências em HTML limpo (sem risco de cortes)
                    for _, r in df_filtrado.iterrows():
                        desc_limpa = r['Descrição do Problema'] if pd.notna(r['Descrição do Problema']) and r['Descrição do Problema'] != "" else "Sem descrição registrada."
                        card_html = f"""
                        <div class="mobile-card">
                            <div class="mobile-card-title">⚠️ {r['Equipamento']} ({r['Setor']})</div>
                            <div class="mobile-card-meta"><b>Inspetor:</b> {r['Funcionário']} | <b>Data:</b> {r['Data_Exibicao']} às {r['Hora_Exibicao']}<br><b>Falha:</b> {r['Falhas']}</div>
                            <div class="mobile-card-desc"><b>Problema:</b> {desc_limpa}</div>
                        </div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)
                        
                    # Botão de confirmação para o modo Mobile
                    if st.button("✓ CONFIRMAR SOLUÇÃO DOS ITENS SELECIONADOS", type="primary", key="btn_mob"):
                        if itens_selecionados_mobile:
                            with st.spinner("Atualizando registros no Google Sheets..."):
                                data_solucao = obter_agora_br().strftime("%d/%m/%Y %H:%M")
                                df_sheets = conn.read(ttl=0)
                                df_sheets = df_sheets.loc[:, ~df_sheets.columns.str.contains('^Unnamed')]
                                df_sheets["Resolução"] = df_sheets["Resolução"].fillna("").astype(str)
                                
                                for item_rotulo in itens_selecionados_mobile:
                                    idx_alvo = opcoes_fáceis[item_rotulo]
                                    df_sheets.loc[idx_alvo, "Resolução"] = f"Solucionado em {data_solucao}"
                                
                                conn.update(data=df_sheets)
                                st.success("🎉 Item(ns) solucionado(s) com sucesso!")
                                st.rerun()
                        else:
                            st.warning("Nenhum item selecionado no campo de escolha acima.")
                            
                else:
                    # Fallback para o modo tabela clássico (Caso queira usar no PC)
                    st.caption("Marque a caixinha na coluna **'Solucionar'** e clique no botão abaixo para dar baixa.")
                    df_filtrado.insert(0, "Solucionar", False)
                    df_editado = st.data_editor(
                        df_filtrado,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Solucionar": st.column_config.CheckboxColumn("Solucionar", default=False),
                            "Data_Exibicao": st.column_config.TextColumn("Data", width="small"),
                            "Hora_Exibicao": st.column_config.TextColumn("Hora", width="small"),
                            "Descrição do Problema": st.column_config.TextColumn("Descrição do Problema", width="large"),
                            "Resolução": None,
                            "original_index": None
                        },
                        disabled=["Data_Exibicao", "Hora_Exibicao", "Funcionário", "Setor", "Equipamento", "Status", "Falhas", "Descrição do Problema"]
                    )
                    
                    if st.button("✓ CONFIRMAR SOLUÇÃO DOS ITENS SELECIONADOS", type="primary", key="btn_pc"):
                        itens_marcados = df_editado[df_editado["Solucionar"] == True]
                        if not itens_marcados.empty:
                            with st.spinner("Atualizando registros no Google Sheets..."):
                                data_solucao = obter_agora_br().strftime("%d/%m/%Y %H:%M")
                                df_sheets = conn.read(ttl=0)
                                df_sheets = df_sheets.loc[:, ~df_sheets.columns.str.contains('^Unnamed')]
                                df_sheets["Resolução"] = df_sheets["Resolução"].fillna("").astype(str)
                                
                                for _, row in itens_marcados.iterrows():
                                    idx_alvo = int(row["original_index"])
                                    df_sheets.loc[idx_alvo, "Resolução"] = f"Solucionado em {data_solucao}"
                                
                                conn.update(data=df_sheets)
                                st.success("🎉 Item(ns) solucionado(s) com sucesso!")
                                st.rerun()
                        else:
                            st.warning("Nenhum item marcado na tabela.")
            else:
                st.info("Nenhuma pendência em aberto para os filtros selecionados.")
                
        # MODO HISTÓRICO ORIGINAL COM DESIGN RESPONSIVO (TABELA -> CARDS AUTOMÁTICO)
        else:
            st.subheader(f"📋 {tipo_visao}")
            
            if not df_filtrado.empty:
                html_tabela = """
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
                <style>
                    body { background-color: transparent !important; font-family: sans-serif; }
                    .table-container { max-height: 520px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 4px; }
                    th { background-color: #2c3e50 !important; color: white !important; font-size: 14px; position: sticky; top: 0; padding: 12px 10px !important; text-align: left; }
                    td { font-size: 13px; vertical-align: middle; word-break: break-word !important; white-space: normal !important; padding: 10px 8px !important; }
                    
                    @media (max-width: 768px) {
                        .table-container { max-height: none; overflow-y: visible; border: none; }
                        table, tragedies, thead, tbody, th, td, tr { display: block; width: 100%; }
                        thead { display: none; }
                        tr {
                            background: #ffffff !important;
                            border: 1px solid #e0e0e0;
                            border-radius: 8px;
                            margin-bottom: 15px;
                            padding: 12px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
                        }
                        td { text-align: left !important; padding: 6px 4px !important; border: none !important; font-size: 13px; display: flex; flex-wrap: wrap; }
                        td::before {
                            content: attr(data-label);
                            font-weight: bold;
                            color: #2c3e50;
                            width: 120px;
                            min-width: 120px;
                            display: inline-block;
                        }
                        td .cell-content { flex: 1; word-break: break-word; }
                    }
                </style>
                <div class="table-container">
                    <table class="table table-striped table-hover m-0">
                        <thead>
                            <tr>
                                <th>Data</th><th>Hora</th><th>Funcionário</th><th>Setor</th><th>Equipamento</th><th>Status</th><th>Falhas</th><th>Descrição do Problema</th><th>Histórico de Resolução</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for _, row in df_filtrado.iterrows():
                    desc_p = str(row.get('Descrição do Problema', '')) if pd.notna(row.get('Descrição do Problema')) else ""
                    resolucao_p = str(row.get('Resolução', '')) if pd.notna(row.get('Resolução')) else ""
                    
                    if resolucao_p:
                        resolucao_html = f"<span class='badge bg-success' style='font-size:11px; padding:6px;'>{resolucao_p}</span>"
                    else:
                        resolucao_html = "<span class='badge bg-secondary' style='font-size:11px; padding:6px;'>Pendente</span>"

                    html_tabela += f"""
                            <tr>
                                <td data-label="Data"><div class="cell-content" style="white-space: nowrap;">{row.get('Data_Exibicao','')}</div></td>
                                <td data-label="Hora"><div class="cell-content">{row.get('Hora_Exibicao','')}</div></td>
                                <td data-label="Inspetor"><div class="cell-content">{row.get('Funcionário','')}</div></td>
                                <td data-label="Setor"><div class="cell-content">{row.get('Setor','')}</div></td>
                                <td data-label="Equipamento"><div class="cell-content"><b>{row.get('Equipamento','')}</b></div></td>
                                <td data-label="Status"><div class="cell-content">{row.get('Status','')}</div></td>
                                <td data-label="Falhas"><div class="cell-content">{row.get('Falhas','')}</div></td>
                                <td data-label="Descrição" style="min-width: 250px; max-width: 450px;"><div class="cell-content">{desc_p}</div></td>
                                <td data-label="Resolução" style="min-width: 180px;"><div class="cell-content">{resolucao_html}</div></td>
                            </tr>
                    """
                html_tabela += "</tbody></table></div>"
                st.components.v1.html(html_tabela, height=540, scrolling=True)
            else:
                st.info("Nenhum registro encontrado para os filtros selecionados.")

        # --- SEÇÃO DE RELATÓRIO ---
        st.divider()
        st.subheader("📊 Enviar Relatório de Não Conformidades")
        st.info("💡 **Aviso:** O relatório enviado será baseado exclusivamente no conteúdo **filtrado** na tabela acima.")
        
        if not df_filtrado.empty:
            df_enviar = df_filtrado.drop(columns=["Solucionar"]) if "Solucionar" in df_filtrado.columns else df_filtrado
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

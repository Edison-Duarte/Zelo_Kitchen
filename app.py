from fpdf import FPDF # fpdf2 também usa este import, mas é mais poderosa

def gerar_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    
    # Usando fontes padrão que aceitam latin-1 (Acentuação comum)
    # Nota: Emojis como ✅ e ❌ geralmente não funcionam em PDFs simples sem fontes externas.
    # Vamos substituir por texto para evitar o erro de encode.
    
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Relatorio de Inspecoes", ln=True, align='C')
    pdf.ln(10)
    
    for i, row in df.iterrows():
        # Limpeza de caracteres que o PDF padrão não entende
        status_texto = row['Status'].replace("✅ ", "").replace("❌ ", "")
        irregularidades = row['Irregularidades'].encode('latin-1', 'ignore').decode('latin-1')
        
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, f"Data: {row['Data']} - Setor: {row['Setor']}", ln=True)
        
        pdf.set_font("Arial", "", 10)
        # Escrevendo os dados limpando emojis para evitar o UnicodeEncodeError
        texto_corpo = (
            f"Inspetor: {row['Colaborador']}\n"
            f"Status: {status_texto}\n"
            f"Irregularidades: {irregularidades}\n"
            + "-"*50
        )
        pdf.multi_cell(0, 5, texto_corpo)
        pdf.ln(2)
    
    # Na fpdf2, o output('S') já retorna bytes ou string dependendo da versão, 
    # mas a forma mais segura no Streamlit Cloud é:
    return pdf.output() 

# --- No botão de download, altere para: ---
# pdf_data = gerar_pdf(df_filtrado)
# st.download_button(
#     label="📄 Gerar PDF (Filtrado)",
#     data=bytes(pdf_data), # Garante que está em formato de bytes
#     file_name="relatorio_inspeccao.pdf",
#     mime="application/pdf"
# )

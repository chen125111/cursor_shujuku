import markdown_it
import os
import win32com.client as win32

def convert_md_to_docx():
    # 1. MD -> HTML
    md_path = os.path.abspath('docs/用户手册.md')
    html_path = os.path.abspath('docs/temp_manual.html')
    docx_path = os.path.abspath('docs/用户手册.docx')
    
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()
    
    # 启用表格支持
    md = markdown_it.MarkdownIt("commonmark").enable("table")
    html_content = md.render(md_text)
    
    full_html = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: "SimSun", serif; line-height: 1.5; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        img {{ max-width: 100%; display: block; margin: 20px auto; }}
        h1, h2, h3 {{ color: #2C3E50; }}
    </style>
    </head>
    <body>
    {html_content}
    </body>
    </html>
    """
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    # 2. HTML -> DOCX (via Word COM)
    word = None
    try:
        word = win32.Dispatch('Word.Application')
        word.Visible = False
        doc = word.Documents.Open(html_path)
        
        # 强制嵌入图片并保存
        doc.SaveAs(docx_path, FileFormat=16) # wdFormatXMLDocument
        doc.Close()
        print(f"Successfully updated: {docx_path}")
    except Exception as e:
        print(f"Conversion error: {e}")
    finally:
        if word:
            word.Quit()
        if os.path.exists(html_path):
            os.remove(html_path)

if __name__ == "__main__":
    convert_md_to_docx()

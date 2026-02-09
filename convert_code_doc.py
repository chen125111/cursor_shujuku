import os
import win32com.client as win32
import markdown_it

def convert_to_docx():
    current_dir = os.path.abspath(os.getcwd())
    md_path = os.path.join(current_dir, 'docs', '系统代码文档.md')
    html_path = os.path.join(current_dir, 'docs', 'temp_code_doc.html')
    docx_path = os.path.join(current_dir, 'docs', '系统代码文档.docx')

    if not os.path.exists(md_path):
        print(f"Error: {md_path} not found")
        return

    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

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
        pre {{ background: #f5f5f5; padding: 10px; overflow-x: auto; }}
        code {{ font-family: Consolas, "Courier New", monospace; }}
    </style>
    </head>
    <body>
    {html_content}
    </body>
    </html>
    """

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(full_html)

    word = None
    try:
        word = win32.Dispatch('Word.Application')
        word.Visible = False

        doc = word.Documents.Open(html_path)
        doc.SaveAs(docx_path, FileFormat=16)
        doc.Close()
        print(f"Successfully created: {docx_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if word:
            word.Quit()
        if os.path.exists(html_path):
            os.remove(html_path)

if __name__ == "__main__":
    convert_to_docx()

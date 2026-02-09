import win32com.client as win32
import os

def convert_to_docx():
    # 获取绝对路径
    current_dir = os.path.abspath(os.getcwd())
    html_path = os.path.join(current_dir, 'docs', 'temp_manual.html')
    docx_path = os.path.join(current_dir, 'docs', '用户手册.docx')
    
    if not os.path.exists(html_path):
        print(f"Error: {html_path} not found")
        return

    word = None
    try:
        # 启动 Word
        word = win32.gencache.EnsureDispatch('Word.Application')
        word.Visible = False
        
        # 打开 HTML
        doc = word.Documents.Open(html_path)
        
        # 另存为 docx (wdFormatXMLDocument = 16)
        doc.SaveAs(docx_path, FileFormat=16)
        doc.Close()
        print(f"Successfully created: {docx_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if word:
            word.Quit()

if __name__ == "__main__":
    convert_to_docx()

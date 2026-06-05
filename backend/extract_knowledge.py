import os
import sys
import pypdf

def extract_pdf_summaries(knowledge_dir, output_file):
    if not os.path.exists(knowledge_dir):
        print(f"Error: Knowledge directory '{knowledge_dir}' does not exist.")
        return

    pdf_files = [f for f in os.listdir(knowledge_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print("No PDF files found in the knowledge directory.")
        return

    print(f"Found {len(pdf_files)} PDF files to process.")
    
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("# ApexTrade AI Mentor Knowledge Base\n\n")
        out.write("This file contains extracted knowledge from the user-provided trading guides and PDFs.\n")
        out.write("Use this information to answer trading questions, explain strategies, and mentor users.\n\n")
        
        for pdf_name in pdf_files:
            pdf_path = os.path.join(knowledge_dir, pdf_name)
            print(f"Processing: {pdf_name}...")
            out.write(f"## SOURCE DOCUMENT: {pdf_name}\n\n")
            
            try:
                reader = pypdf.PdfReader(pdf_path)
                total_pages = len(reader.pages)
                out.write(f"Total Pages: {total_pages}\n\n")
                
                # We want to extract content. To prevent the file from becoming huge, we will extract key sections,
                # or read the first/last pages and sample sections, or read up to 15 pages per document, or extract summaries.
                # Let's extract up to 25 pages per PDF, skipping empty text.
                pages_to_read = min(30, total_pages)
                step = 1 if total_pages <= 30 else total_pages // 30
                
                pages_extracted = 0
                for i in range(0, total_pages, step):
                    if pages_extracted >= 30:
                        break
                    page = reader.pages[i]
                    text = page.extract_text()
                    if text and len(text.strip()) > 100:
                        out.write(f"### [Page {i+1} / {total_pages}]\n")
                        # Keep it clean
                        cleaned_text = "\n".join([line.strip() for line in text.split("\n") if line.strip()])
                        out.write(cleaned_text)
                        out.write("\n\n")
                        pages_extracted += 1
                        
                print(f"Successfully extracted {pages_extracted} pages from {pdf_name}")
            except Exception as e:
                print(f"Error reading {pdf_name}: {e}")
                out.write(f"Error reading document: {e}\n\n")
            
            out.write("---\n\n")

if __name__ == '__main__':
    knowledge_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'knowledge'))
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'trading_knowledge.txt'))
    extract_pdf_summaries(knowledge_path, output_path)

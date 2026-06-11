import os
import sys
import ast
import re
import pypdf


def parse_python_file(filepath):
    blueprint = []
    filename = os.path.basename(filepath)
    blueprint.append(f"### File: backend/{filename}\n")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        tree = ast.parse(content)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                docstring = ast.get_docstring(node)
                doc = (
                    f"     Docstring: {docstring.strip()}"
                    if docstring
                    else "     No docstring."
                )
                args = [arg.arg for arg in node.args.args]
                blueprint.append(f" - Function: def {node.name}({', '.join(args)})")
                blueprint.append(doc)
            elif isinstance(node, ast.ClassDef):
                blueprint.append(f" - Class: class {node.name}")
                docstring = ast.get_docstring(node)
                if docstring:
                    blueprint.append(f"     Class Docstring: {docstring.strip()}")
                for subnode in node.body:
                    if isinstance(subnode, ast.FunctionDef):
                        sub_docstring = ast.get_docstring(subnode)
                        sub_doc = (
                            f"         Docstring: {sub_docstring.strip()}"
                            if sub_docstring
                            else "         No docstring."
                        )
                        args = [arg.arg for arg in subnode.args.args]
                        blueprint.append(
                            f"     * Method: def {subnode.name}({', '.join(args)})"
                        )
                        blueprint.append(sub_doc)
    except Exception as e:
        blueprint.append(f" - AST Error parsing file: {e}")

    blueprint.append("\n" + "=" * 40 + "\n")
    return "\n".join(blueprint)


def parse_jsx_file(filepath):
    blueprint = []
    filename = os.path.basename(filepath)
    blueprint.append(f"### File: frontend/src/{filename}\n")

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        # Find React components, hooks, or core event/state helpers
        if (
            line.startswith("export default function")
            or line.startswith("function ")
            or (line.startswith("const ") and "=>" in line)
        ):
            if any(
                kw in line
                for kw in [
                    "Panel",
                    "Chart",
                    "Bar",
                    "Screen",
                    "App",
                    "use",
                    "handle",
                    "calc",
                ]
            ):
                # Clean up function/component name for clarity
                clean_line = line.split("{")[0].strip()
                blueprint.append(f" - Component/Function: {clean_line}")

    blueprint.append("\n" + "=" * 40 + "\n")
    return "\n".join(blueprint)


def compile_system_blueprint(project_dir):
    blueprint_content = []
    blueprint_content.append("## APEXTRADE TECHNICAL CODEBASE BLUEPRINT\n")
    blueprint_content.append(
        "This section documents the filenames, functions, signatures, classes, components, and docstrings of the application code.\n\n"
    )

    py_files = [
        "signals.py",
        "main.py",
        "upstox_feed.py",
        "backtest_engine.py",
        "capital_allocator.py",
        "db.py",
        "auth_helpers.py",
    ]

    jsx_files = [
        "App.jsx",
        "SignalsPanel.jsx",
        "PerformancePanel.jsx",
        "OrderBookPanel.jsx",
        "AccountPanel.jsx",
        "LoginScreen.jsx",
        "IntroSplash.jsx",
    ]

    # Process Backend Python Files
    for filename in py_files:
        path = os.path.join(project_dir, "backend", filename)
        if os.path.exists(path):
            print(f"Parsing codebase structures from: {filename}...")
            blueprint_content.append(parse_python_file(path))

    # Process Frontend JSX Files
    for filename in jsx_files:
        path = os.path.join(project_dir, "frontend", "src", filename)
        if os.path.exists(path):
            print(f"Parsing codebase structures from: {filename}...")
            blueprint_content.append(parse_jsx_file(path))

    return "\n".join(blueprint_content)


def extract_knowledge(project_dir, knowledge_dir, output_file):
    print("Initializing ApexTrade AI Knowledge Compiler...")

    with open(output_file, "w", encoding="utf-8") as out:
        out.write("# ApexTrade AI Mentor System & Trading Knowledge Base\n\n")
        out.write(
            "This file is a unified context document containing the complete platform codebase blueprint followed by extracted trading guides.\n\n"
        )

        # 1. Write Codebase Blueprint
        blueprint = compile_system_blueprint(project_dir)
        out.write(blueprint)
        out.write("\n\n" + "#" * 50 + "\n\n")

        # 2. Append PDF Extracts
        out.write("## APEXTRADE EDUCATION & STRATEGY MANUALS\n\n")
        if not os.path.exists(knowledge_dir):
            print(
                f"Warning: Knowledge directory '{knowledge_dir}' does not exist. Skipping PDFs."
            )
            return

        pdf_files = [f for f in os.listdir(knowledge_dir) if f.lower().endswith(".pdf")]
        if not pdf_files:
            print("No PDF manuals found to extract.")
            return

        print(f"Found {len(pdf_files)} PDF manual files to process.")
        for pdf_name in pdf_files:
            pdf_path = os.path.join(knowledge_dir, pdf_name)
            print(f"Extracting manual pages from: {pdf_name}...")
            out.write(f"### SOURCE MANUAL: {pdf_name}\n\n")

            try:
                reader = pypdf.PdfReader(pdf_path)
                total_pages = len(reader.pages)
                out.write(f"Total Pages: {total_pages}\n\n")

                # Extract up to 30 key pages to fit context constraints
                pages_to_read = min(30, total_pages)
                step = 1 if total_pages <= 30 else total_pages // 30

                pages_extracted = 0
                for i in range(0, total_pages, step):
                    if pages_extracted >= 30:
                        break
                    page = reader.pages[i]
                    text = page.extract_text()
                    if text and len(text.strip()) > 100:
                        out.write(
                            f"#### [Manual: {pdf_name} - Page {i + 1} / {total_pages}]\n"
                        )
                        cleaned_text = "\n".join(
                            [line.strip() for line in text.split("\n") if line.strip()]
                        )
                        out.write(cleaned_text)
                        out.write("\n\n")
                        pages_extracted += 1
                print(f"Successfully compiled {pages_extracted} pages from {pdf_name}")
            except Exception as e:
                print(f"Error reading {pdf_name}: {e}")
                out.write(f"Error reading document: {e}\n\n")

            out.write("---\n\n")


if __name__ == "__main__":
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.abspath(os.path.join(backend_dir, ".."))
    knowledge_dir = os.path.join(project_dir, "knowledge")
    output_file = os.path.join(backend_dir, "trading_knowledge.txt")

    extract_knowledge(project_dir, knowledge_dir, output_file)
    print("AI Knowledge Base successfully compiled!")

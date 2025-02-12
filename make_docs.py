"""This script contains a function to make the documentation for the package.

It converts the notebooks in the demo folder to markdown files.
It also creates an API reference based on the docstrings of pymetadataeditor/interface.py.
To use this script, run `python make_docs.py` in the terminal.
"""

import os
import subprocess

import nbformat
from bs4 import BeautifulSoup
from nbconvert import MarkdownExporter

# # Filter out cells with warnings
# for cell in notebook.cells:
#     if cell.cell_type == "code":
#         cell.outputs = [output for output in cell.get("outputs", []) if output.get("name") != "stderr"]
# filtered_cells = notebook.cells


def extract_first_elements(soup, num_elements):
    """Extracts the first `num_elements` elements from a BeautifulSoup object, with handling for tables and styles.

    Args:
        soup (BeautifulSoup or Tag or NavigableString): The BeautifulSoup object or tag to extract elements from.
        num_elements (int): The number of elements to extract.

    Returns:
        str: A string representation of the first `num_elements` elements,
             with tables truncated to 3 rows and styles excluded. If `soup`
             does not have contents, returns the string representation of `soup`.
    """
    elements = []
    count = 0
    if not hasattr(soup, "contents"):
        return str(soup)
    for element in soup.contents:
        if count >= num_elements:
            elements += "..."
            break
        if isinstance(element, str) and element.strip() == "":
            continue
        elif element.name == "style":
            continue
        elif element.name == "table":
            # truncate the table to 3 rows
            rows = element.find_all("tr")
            for row in rows[5:]:
                row.decompose()
        # if isinstance(element, str):
        #     continue
        # if hasattr(element, 'children'):
        #     s = ""
        #     for i, elem in enumerate(element.children):
        #         if i >= num_elements:
        #             s += "..."
        #             break

        #         s += extract_first_elements(elem, num_elements)
        #     elements.append(s)
        # else:
        elements.append(str(element))
        count += 1
    return "".join(elements)


# Filter out cells with warnings and truncate long outputs
def simplify_notebook_outputs(notebook):
    """Simplifies the outputs of code cells in a Jupyter notebook.

    This function processes each cell in the provided notebook and modifies the outputs of code cells by:
    - Removing the 'traceback' key from the output, keeping only the last entry if it exists.
    - Truncating the 'text/plain' data to a maximum of 300 characters, appending '...' if truncated.
    - Simplifying the 'text/html' data by extracting the first 100 elements.

    Args:
        notebook (nbformat.NotebookNode): The Jupyter notebook object to be simplified.

    Returns:
        nbformat.NotebookNode: The simplified Jupyter notebook object.
    """
    for cell in notebook.cells:
        if cell.cell_type == "code":
            new_outputs = []
            for output in cell.get("outputs", []):
                if output.get("name") != "stderr":
                    # remove the 'traceback' key from the output
                    if "traceback" in output:
                        output["traceback"] = [output["traceback"][-1]]
                    if (
                        "data" in output
                        and isinstance(output["data"], dict)
                        and "text/plain" in output["data"]
                        and len(output["data"]["text/plain"]) > 300
                    ):
                        output["data"]["text/plain"] = output["data"]["text/plain"][:300].strip() + "..."
                    if "data" in output and isinstance(output["data"], dict) and "text/html" in output["data"]:
                        soup = BeautifulSoup(output["data"]["text/html"], "html.parser")
                        output["data"]["text/html"] = extract_first_elements(next(soup.children), 100)
                    new_outputs.append(output)
            cell.outputs = new_outputs
    filtered_cells = notebook.cells

    notebook.cells = filtered_cells

    return notebook


if __name__ == "__main__":
    """Converts the notebooks in the demo folder to markdown files and creates an API reference."""
    # list every file in the demo folder ending in .ipynb, using os
    filenames = [f for f in os.listdir("demo") if f.endswith(".ipynb")]
    # exclude the file extension
    filenames = [f.split(".")[0] for f in filenames]
    for filename in filenames:
        # Load the notebook
        with open(f"demo/{filename}.ipynb") as f:
            notebook = nbformat.read(f, as_version=4)

        simplify_notebook_outputs(notebook)

        # Create a Markdown exporter
        markdown_exporter = MarkdownExporter()

        # Convert the notebook to Markdown
        (body, resources) = markdown_exporter.from_notebook_node(notebook)

        # Save the Markdown to a file
        with open(f"docs/{filename}.md", "w") as f:
            f.write(body)

    command = ["lazydocs", "pymetadataeditor.interface.MetadataEditor", "--no-watermark", "--output-path", "docs"]

    # Run the command
    subprocess.run(command, check=True)

    # rename the file docs/pymetadataeditor.interface.MetadataEditor.md to docs/API_Reference.md using os
    os.rename("docs/pymetadataeditor.interface.MetadataEditor.md", "docs/API_Reference.md")

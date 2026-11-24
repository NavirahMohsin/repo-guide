
import os
import json

from pathlib import Path
#pdf
from pypdf import PdfReader

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.code_parser import get_repository_files


def load_repository(repo_path):

    files = get_repository_files(repo_path)

    documents = []

    for file_path in files:

        extension = Path(file_path).suffix.lower()

        relative_path = os.path.relpath(
            file_path,
            repo_path
        )

        try:

            # --------------------------------
            # PDF DOCUMENTS
            # --------------------------------

            if extension == ".pdf":

                reader = PdfReader(file_path)

                for page_number, page in enumerate(
                    reader.pages,
                    start=1
                ):

                    content = page.extract_text() or ""

                    if content.strip():

                        documents.append(
                            Document(
                                page_content=content,
                                metadata={
                                    "source": relative_path,
                                    "file_type": "pdf",
                                    "page": page_number
                                }
                            )
                        )

            # --------------------------------
            # JUPYTER NOTEBOOKS
            # --------------------------------

            elif extension == ".ipynb":

                with open(
                    file_path,
                    "r",
                    encoding="utf-8"
                ) as file:

                    notebook = json.load(file)

                for index, cell in enumerate(
                    notebook.get("cells", [])
                ):

                    cell_type = cell.get("cell_type", "")

                    # Include both markdown and code cells
                    if cell_type not in ["code", "markdown"]:
                        continue

                    content = cell.get("source", "")

                    if isinstance(content, list):
                        content = "".join(content)

                    if content.strip():

                        documents.append(
                            Document(
                                page_content=content,
                                metadata={
                                    "source": relative_path,
                                    "file_type": "notebook",
                                    "cell": index,
                                    "cell_type": cell_type
                                }
                            )
                        )

            # --------------------------------
            # NORMAL TEXT / CODE FILES
            # --------------------------------

            else:

                with open(
                    file_path,
                    "r",
                    encoding="utf-8",
                    errors="replace"
                ) as file:

                    content = file.read()

                if content.strip():

                    documents.append(
                        Document(
                            page_content=content,
                            metadata={
                                "source": relative_path,
                                "file_type": extension
                            }
                        )
                    )

        except Exception as error:

            print(
                f"Skipping {relative_path}: {error}"
            )

    return documents


def split_documents(documents):
    # Chunk size optimized for semantic search
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )

    cleaned_documents = []
    #invalid utf-8 characters
    for document in documents:
        clean_content = (
            document.page_content
            .encode("utf-8", errors="replace")
            .decode("utf-8")
        )

        cleaned_documents.append(
            Document(
                page_content=clean_content,
                metadata=document.metadata
            )
        )

    return splitter.split_documents(cleaned_documents)

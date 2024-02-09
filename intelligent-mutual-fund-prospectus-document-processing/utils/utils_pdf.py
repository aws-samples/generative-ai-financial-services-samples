from PyPDF2 import PdfWriter, PdfReader


# Function to keep only the first page of a PDF file
def first_page(local_file):
    """Trim and keep first page only"""
    page0 = PdfReader(local_file, "rb").getPage(0)
    pdf_out = PdfWriter()
    pdf_out.add_page(page0)

    # Write the first page back to the same file, overwriting it
    with open(local_file, "wb") as f:
        pdf_out.write(f)


# Function to count the number of pages in a PDF file
def num_of_pages(local_file):
    return len(PdfReader(local_file, "rb").pages)


# Function to iterate over pages of a PDF file and create separate PDFs for each page
def iterate_pages(local_file, max_pages=100):
    """Iterate over pdf pages"""
    reader = PdfReader(local_file, "rb")

    # Loop through each page and create a separate PDF for it
    for i, page in enumerate(reader.pages, 1):
        if i < max_pages:
            writer = PdfWriter()
            writer.add_page(page)

            # Naming each page file based on the original file name and page number
            pdf_page_file = local_file.replace(".pdf", f"{i}.pdf")
            with open(pdf_page_file, "wb") as f:
                writer.write(f)
            yield pdf_page_file


# Function to extract text from the first page of a PDF file
def to_text(local_pdf):
    """Extract text from 1st page of pdf"""
    with open(local_pdf, "rb") as f:
        reader = PdfReader(f)
        page = reader.pages[0]
        text = page.extract_text()

        # Replace tab characters and newlines with space for cleaner text
        return text.replace(chr(9), " ").replace("\n", " ")

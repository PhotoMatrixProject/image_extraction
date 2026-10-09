import fitz
from PyPDF2 import PdfWriter, PdfReader
import os

def check_size(width:int, height:int):
    MAX_SIZE = 32767
    m = max(width, height)
    shrink_par = 0 #default, if it is 0 - original size is appropriate, no need to shrink
    while m > MAX_SIZE:
        shrink_par += 1
        m = int(m/2)
    return shrink_par

def cut_pdf(pdf, output_folder):
    try:
        inputpdf = PdfReader(open(pdf, "rb"))
        for i in range(len(inputpdf.pages)):
            output = PdfWriter()
            output.add_page(inputpdf.pages[i])
            with open(output_folder+"/%s.pdf" % i, "wb") as outputStream:
                output.write(outputStream)
        return output_folder, i
    except Exception:
        return "", -1

def convert_pdf_to_images(pdf, output_folder, output_pdf):
    pdf_folder, page_num = cut_pdf(pdf, output_pdf)
    if page_num == -1: return -1

    for i in range(page_num+1):
        doc = fitz.open(f'{pdf_folder}/{i}.pdf')
        zoom = 2
        mat = fitz.Matrix(zoom, zoom)
        pix = doc[0].get_pixmap(matrix = mat,dpi=900)
        shrink_par = check_size(pix.width, pix.height)
        if shrink_par != 0:
            pix.shrink(shrink_par)
        pix.save(f'{output_folder}/{i}.png')
    return i


def convert_pdf_to_images_debug(output_folder):
    pdf_folder = "/Users/dariakorop/Desktop/rocnik/tp_pdf/"
    j = 603
    entries = os.listdir(pdf_folder)
    for i, entry in enumerate(entries):
        file_name = f'{pdf_folder}{entry}'
        if file_name.endswith('.pdf'):
            j += 1
            doc = fitz.open(file_name)
            zoom = 2
            mat = fitz.Matrix(zoom, zoom)
            pix = doc[0].get_pixmap(matrix = mat,dpi=900)#900
            pix.shrink(2)
            pix.save(f'{output_folder}/{j}.png')
        # if i == : break
    return i



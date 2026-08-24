import os
import sys
import pdf2png
import im_cap
import img_bal as ib
import im_link_cz as ilcz
import im_link_fr as ilfr
import im_link_deu as ildeu
import im_bal_fr as ibfr
from unidecode import unidecode

def work_with_pdf(pdf_address, metadata, language, input_path, output_path, dump_pdf):
    page_count = pdf2png.convert_pdf_to_images(pdf_address, input_path, dump_pdf)
    if page_count == -1: return
    im_cap.util_without_pagenum(input_path, output_path, page_count, language, pdf_address, metadata)
    # clean_directory(input_path)
    clean_directory(dump_pdf)

def work_with_folder(names, metadata, language):
    dump_pdf = 'dump_pdf'#resource_path('dump_pdf/')#'./dump_pdf/'
    # dump_pdf = r"X:\Projekty\Matrix\dump_pdf"
    if not os.path.exists(dump_pdf):
        os.mkdir(dump_pdf)

    path, out_path, language = utility(language)
    for i in range(len(names)):
        temp_path = create_folder(names[i], path)
        work_with_pdf(names[i], metadata[i], language, temp_path, out_path, dump_pdf)
    remove_empty_directory(dump_pdf)
    # remove_empty_directory(path)
    return

def create_folder(pdf_name, location):#creates folder for the pngs converted from pdf
    journal_info = os.path.splitext(os.path.basename(pdf_name))[0]
    journal_info = unidecode(journal_info).replace(' ', '_')
    folder_name = os.path.join(location, journal_info)
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
        
    return folder_name

def clean_directory(dir_name):
    try:
        files = os.listdir(dir_name)
        for file in files:
            file_path = os.path.join(dir_name, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
    except FileNotFoundError:
        return

def remove_empty_directory(dir_name):
    if os.path.isdir(dir_name):
        os.rmdir(dir_name)

def work_with_batches(folder_with_batches):
    temp_path, res_path, language = utility("")
    batch_folders = os.listdir(folder_with_batches)
    for batch_folder in batch_folders:
        batch_path = os.path.join(folder_with_batches, batch_folder)
        if os.path.isdir(batch_path):
            temp_path_b = create_folder(batch_folder, temp_path)
            ib.util_with_batch(temp_path_b, res_path, batch_path, language)
    return

def work_with_link(link:str, lang, volume_start:int,volume_fin:int, month_start:int, month_fin:int, issue_start:int, issue_fin:int):
    french_link_label = "https://gallica.bnf.fr"
    german_link_label = "https://digi.ub.uni-heidelberg.de/diglit"
    if link.startswith(french_link_label): # french link
        ilfr.utility(link, volume_start, volume_fin, month_start, month_fin, issue_start, issue_fin)
    elif link.startswith(german_link_label):
        ildeu.utility(link, volume_start, volume_fin)
    else:
        ilcz.utility(link, volume_start, volume_fin, issue_start, issue_fin) # czech link
    return

def work_with_french_batches(dir_path:str):
    ibfr.util(dir_path)
    return

def utility(language):
    # path = os.path.join(os.path.dirname(sys.argv[0]), 'temp/')
    # out_path = os.path.join(os.path.dirname(sys.argv[0]), 'result/')

    path = r'X:\Projekty\Matrix\temp'
    out_path = r'X:\Projekty\Matrix\result'
    if not os.path.exists(r'X:\Projekty\Matrix'):
        path = 'temp'
        out_path = 'result'

    if not os.path.exists(path):
        os.mkdir(path)

    if not os.path.exists(out_path):
        os.mkdir(out_path)

    if language == "":
        language = 'ces'
    return (path, out_path, language)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
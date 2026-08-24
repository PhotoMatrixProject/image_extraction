import os
import requests
import time
import json
import unidecode
import csv
import cv2
# from selenium import webdriver

RESULT_PATH_ON_PC = r"X:\Projekty\Matrix\result"
RESULT_PATH_ON_PC_PREFIX = r"X:\Projekty\Matrix"
if not os.path.exists(RESULT_PATH_ON_PC_PREFIX):
    RESULT_PATH_ON_PC = r"result"

IMG_HEAD_CSV = ['journal_name', 'issue', 'volume', 'publication_date',
                'page_number', 'page_index', 'image_number', 
                'caption', 'area_in_percentage', 'x1', 'y1', 'x2', 'y2', 'image',
                'width_page', 'height_page', 'language', 
                'img_address', 'author', 'publisher', 'contributor']

PAGE_HEAD_CSV = ['journal_name', 'issue', 'volume', 'publication_date',
                'page_number', 'page_index',
                'page_width', 'page_height', 'language', 
                'img_address', 'author', 'publisher', 'contributor']

last_request_time = 0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept-Encoding": "*",
    "Connection": "keep-alive"
}

def check_time():
    time_constraint = 3
    current_time = time.time()
    if (current_time - last_request_time) < time_constraint:
        time.sleep(time_constraint - (current_time - last_request_time))

def create_dir(dir_name:str)->None:
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)
    return

def read_api_url_unsafe(api_url:str, file_name:str)->bool:
    check_time()
    time.sleep(1)
    response = requests.get(api_url, headers=HEADERS)
    global last_request_time 
    last_request_time = time.time()
    tries = 5
    while (not response.ok and tries > 0):
        check_time()
        time.sleep(1)
        response = requests.get(api_url, headers=HEADERS)
        last_request_time = time.time()
        tries -= 1

    r = response.content
    with open(file_name, mode = "wb") as binary_file:
        binary_file.write(r)
    
    return response.ok

def read_api_url(api_url:str, file_name:str)->bool:
    try:
        response_ok = read_api_url_unsafe(api_url, file_name)
        return response_ok
    except Exception as e:
        print("Error occurred. The error is ", e)
        print("Let me try again...")
        time.sleep(60)
        response_ok = read_api_url_unsafe(api_url, file_name)
        return response_ok

def clean_if_empty(res_dir, csv_files):

    if os.path.exists(res_dir):
        if not os.listdir(res_dir):
            os.removedirs(res_dir)
            for csv_f in csv_files:
                if os.path.exists(csv_f):
                    os.remove(csv_f)
    return

def delete_json_files(root_folder:str):
    files_to_delete = ["journal.json", "volume.json", "year.json", "issue.json", "journal.xml", "issue.xml", "pages.json", "page.json", "pre_issue.json", "volume.json", "ocr.json"]
    for file in files_to_delete:
        if os.path.exists(os.path.join(root_folder, file)):
            os.remove(os.path.join(root_folder, file))
    return

def load_json(name:str)->dict:
    file = open(name, 'r', encoding='UTF8')
    content = json.loads(file.read())
    return content

def download_alto_file_unsafe(url:str, file_name:str)->bool:
    check_time()
    time.sleep(1)
    print(url)
    response = requests.get(url, headers=HEADERS)
    global last_request_time
    last_request_time = time.time()
    tries = 5
    while (not response.ok and tries > 0):
        check_time()
        time.sleep(1)
        response = requests.get(url, headers=HEADERS)
        last_request_time = time.time()
        tries -= 1
    
    r = response.content
    with open(file_name, "wb") as binary_file:
        binary_file.write(r)
    return response.ok

def download_alto_file(url:str, file_name:str)->bool:
    try:
        response_ok = download_alto_file_unsafe(url, file_name)
        if not response_ok:
            time.sleep(60)
            response_ok = download_alto_file_unsafe(url, file_name)
        return response_ok
    except Exception as e:
        print("Error occurred. The error is ", e)
        print("Let me try again...")
        time.sleep(60)
        response_ok = download_alto_file_unsafe(url, file_name)
        return response_ok

def save_img_unsafe(url:str, img_name:str)->bool:
    check_time()
    time.sleep(1)
    response = requests.get(url, headers=HEADERS)
    global last_request_time
    last_request_time = time.time()
    if response.ok:
        with open(img_name, "wb") as f:
            f.write(response.content)
    return response.ok
    
def save_img(url:str, img_name:str)->bool:
    try:
        response_ok = save_img_unsafe(url, img_name)
        return response_ok
    except Exception as e:
        print("Error occurred. The error is ", e)
        print("Let me try again...")
        time.sleep(60)
        response_ok = save_img_unsafe(url, img_name)
        return response_ok

def is_img_request_ok(url:str)->bool:
    check_time()
    time.sleep(1)
    response = requests.get(url, headers=HEADERS)
    global last_request_time
    last_request_time = time.time()
    return response.ok

def delete_file(path:str):
    if os.path.exists(path):
        os.remove(path)
    return

def get_img_dims(img_path:str)->list[int]:
    '''Returns [width, height] of the image in the givem path.'''
    img = cv2.imread(img_path)
    h, w, _ = img.shape
    return [w, h]

def format_string(s:str):
    '''Gets rid of diacriticts and punctution.'''

    format_str = unidecode.unidecode(s)
    bad_chars = [' ', '.', ',', ';', '\'', '-', ':', '/', '"', '<', '>']
    for c in bad_chars:
        format_str = format_str.replace(c, '_')
    format_str.replace('(', '')
    format_str.replace(')', '')
    finish = 0
    for c in reversed(format_str):
        if c.isalpha() or c.isdigit():
            break
        else: finish += 1
    
    res_str = format_str[:-finish] if finish>0 else format_str
    return res_str

def shorten_name(name:str)->str:
    split_name = name.split(' ')
    if len(split_name) > 3:
        return ' '.join(split_name[:3])
    return name

def create_csv_writer(csvfile:str, head:list[str])->tuple:
    f = open(csvfile, 'w', encoding='UTF8', newline='')
    writer = csv.DictWriter(f, fieldnames=head, delimiter = ";")
    writer.writeheader()
    return writer, f


def create_result_dirs_and_files(issue_dir_name:str, result_root = 'result'): # dir where extracted reproduction will be
    # result_root = "result"
    # result_root = os.path.join(r"X:\Projekty\Matrix", result_root)
    result_dir = os.path.join(result_root, issue_dir_name)#extracted reproductions
    create_dir(result_dir)

    result_dir_big = os.path.join(result_dir, 'big_original')
    create_dir(result_dir_big)

    csvfile = issue_dir_name + '_data.csv'
    csvfile_path = os.path.join(result_root, csvfile)

    csvfile_pages = issue_dir_name + '_pages.csv'
    csvfile_pages_path = os.path.join(result_root, csvfile_pages)
    
    return result_dir, csvfile_path, csvfile_pages_path

def language_formatting(lang:str)->str:
    '''for the database'''
    if lang == "ces": return "cs"
    if lang == "fra": return "fr"
    if lang == "rus": return "ru"
    if lang == "deu": return "de"

def delete_diacritics(s:str)->str:
    return unidecode.unidecode(s)

def create_entity(page_index, page_number, number, caption, area_percentage, coords, metadata, im_prefix, p_w, p_h, lang,
                  img_addr, author, publisher, contributor):
    journal_name, publication_date, volume, issue_number = metadata
    caption = caption.replace(';', ' ')
    return {"journal_name": journal_name,
            "issue":issue_number,
            "volume":volume,
            "publication_date":publication_date,
            "page_number": page_number,
            "page_index": page_index,
            "image_number": number,
            "caption":caption,
            "area_in_percentage":area_percentage,
            "x1":coords[0],
            "y1":coords[1],
            "x2":coords[2],
            "y2":coords[3],
            "image": (f"{im_prefix}{page_index}_{number}.jpeg"),
            "width_page":p_w, 
            "height_page": p_h, 
            "language":lang,
            "img_address":img_addr,
            "author":author, 
            "publisher":publisher,
            "contributor":contributor}

def create_page_entity(page_index, page_number, metadata, p_w, p_h, lang,
                  img_addr, author, publisher, contributor):
    journal_name, publication_date, volume, issue_number = metadata
    return {"journal_name": journal_name,
            "issue":issue_number,
            "volume":volume,
            "publication_date":publication_date,
            "page_number": page_number,
            "page_index": page_index,
            "page_width":p_w, 
            "page_height": p_h, 
            "language":lang,
            "img_address":img_addr,
            "author":author, 
            "publisher":publisher,
            "contributor":contributor}



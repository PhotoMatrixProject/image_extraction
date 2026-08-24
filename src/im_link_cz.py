import requests
import json
import os
from unidecode import unidecode
import csv
import image_mining_big as getim
import new_caption as cap
import versions as vrs
import utility_funcs as ut
import cap_img_from_alto_cz as ci_alto


def find_lib(url:str)->str:
    divider = '/'
    url_dirs = url.split(divider)
    if len(url_dirs) < 5:
        return
    NDK = "ndk.cz"
    KRAMERIUS_NKP = "kramerius5.nkp.cz"
    NKP = "nkp"
    MZK = "mzk"
    MLP = "mlp"
    if url_dirs[2] == NDK:
        return NKP
    if url_dirs[2] == KRAMERIUS_NKP:
        return NKP
    if url_dirs[3] == MZK:
        return MZK
    if url_dirs[3] == MLP:
        return MLP
    return

def find_id(url:str)->str:
    divider = '/'
    domens = url.split(divider)
    id_flag = "uuid:"
    for i in range(len(domens)):
        if len(domens[i]) >= 5:
            if domens[i][:5] == id_flag:
                ids = domens[i].split('?')
                return ids[0]
    return

def convert_to_iiif(url:str)->str:
    lib_abbr = find_lib(url)
    if lib_abbr == None:
        return None
    uuid = find_id(url)
    if uuid == None:
        return None
    head = "https://iiif."
    library_domain = f"digitalniknihovna.cz/{lib_abbr}/"
    iiif_url = head+library_domain+uuid
    return iiif_url

def extract_metadata(metadata:dict)->dict:#find doc type and language
    md = {'lang':'ces'} #default
    lang_map = {"němčina":"deu", "francouzština":"fra", "ruština":"rus", "čeština":"ces"}
    for m in metadata:
        if m["label"]["cz"][0] == "Jazyk":
            md['lang'] = lang_map[m["value"]["none"][0]]
        if m["label"]["cz"][0] == "Typ dokumentu":
            md['doctype'] = m["value"]["cz"][0]
    return md

def extract_part_num(metadata:dict)->str:
    for m in metadata:
        if m["label"]["cz"][0] == "Číslo části":
            return m["value"]["none"][0]
    return None

def extract_monografy_name(metadata:dict)->str:
    for m in metadata:
        if m["label"]["cz"][0] == "Název":
            return m["value"]["none"][0]
    return None

def find_publication_date(metadata:dict)->str:
    for item in metadata:
        if item['label']['cz'][0] == "Vydáno":
            return item['value']['none'][0]
    return ""

def convert_month_to_number(month:str)->str:
    month = ut.delete_diacritics(month.lower())
    months = {'leden':'01', 'unor':'02', 'brezen':'03', 
              'duben':'04', 'kveten':'05', 'cerven':'06', 
              'cervenec':'07', 'srpen':'08', 'zari':'09', 
              'rijen':'10', 'listopad':'11', 'prosinec':'12'}

    return months[month]

def format_publication_date(date:str)->str:
    publication_date = ""
    if len(date) == 0: return publication_date
    time_span = date.split('-')
    if len(time_span) == 1: # single date, not a span
        single_date = time_span[0].split('.')
        if len(single_date) == 1: # a year or month year
            month_year = single_date[0].split(' ')
            if len(month_year) == 2: # month year, month a word not a number
                month = convert_month_to_number(month_year[0]) 
                year = month_year[1]
                publication_date = "%s-%s-%s-%s-%s-%s" % (year, month, "01", year, month, "31")
            elif len(month_year) == 1:
                year = month_year[0]
                publication_date = "%s-%s-%s-%s-%s-%s" % (year, "01", "01", year, "12", "31")
        elif len(single_date) == 2:
            month = single_date[0]
            if len(month) == 1: month = '0'+month
            year = single_date[1]
            publication_date = "%s-%s-%s-%s-%s-%s" % (year, month, "01", year, month, "31")
        elif len(single_date) == 3:
            day = single_date[0]
            if len(day) == 1: day = '0'+ day
            month = single_date[1]
            if len(month) == 1: month = '0'+month
            year = single_date[2]
            publication_date = "%s-%s-%s-%s-%s-%s" % (year, month, day, year, month, day)
    elif len(time_span) == 2: # it is a time span, at this point it can process only 08.-09.1904 and 1901-1902
        first_month = time_span[0]
        second_month_year = time_span[1]
        single_date1 = first_month.split('.')
        single_date2 = second_month_year.split('.')
        if len(single_date2) == 2 and len(single_date1) == 2:
           month1 = single_date1[0]
           if len(month1) == 1: month1 = '0'+month1
           month2 = single_date2[0]
           if len(month2) == 1: month2 = '0'+month2
           year = single_date2[1]
           publication_date = "%s-%s-%s-%s-%s-%s" % (year, month1, "01", year, month2, "31")
        elif len(single_date1) == 1 and len(single_date2) == 1: #single_date1 and single_date2 do not contain '.' meaning that it is likely year-year (1901-1902)
            publication_date = "%s-%s-%s-%s-%s-%s" % (single_date1[0], "01", "01", single_date2[0], "12", "31")
    publication_date = publication_date.replace(' ', '')
    return publication_date

def format_img_url_cutout(page_url:str, bbox:list[int], page_width:int, page_height:int)->str:
    x1, y1, x2, y2 = bbox
    w, h = x2-x1, y2-y1 

    width = int((x2-x1)*0.05)
    height = int((y2-y1)*0.05)

    split_url = page_url.split('/')
    split_url[-4] = "%d,%d,%d,%d" % (max(0, x1-width), max(0, y1-height), min(page_width, w+2*width), min(page_height, h+2*height))
    split_url[-3] = 'max'
    res_url = '/'.join(split_url)
    return res_url

def process_page_image(img_file:str, img_url:str, lang:str, writer:csv.DictWriter, infos:list, page_index:str, res_dir:str, page_writer:csv.DictWriter, volume_index:int):
    journal_name, publication_date, volume, issue_number = infos
    image_name_prefix = "%s_%s_%s_%s_" % (journal_name, publication_date, volume, issue_number)
    # print('processing image:', volume, issue_number, page_index)

    success, boxes, captions, degrees_to_rotate, p_w, p_h, ocr_img_url = ci_alto.utility(img_url, res_dir, img_file)
    if not success: return

    if p_w == 0 or p_h == 0:
        print('downloaded img but no alto, preprocessing it with CV alg')
        boxes, p_h, p_w = getim.util(img_file, lang)
        ocr_img_url = img_url
        if len(boxes) > 0:
            captions, degrees_to_rotate = cap.util(img_file, boxes, lang) 

    if len(boxes) > 0: #page contains images
        # if p_w == 0 or p_h == 0:
        #     captions, degrees_to_rotate = cap.util(img_file, boxes, lang) 
        percentages, _ = vrs.get_versions(page_index, image_name_prefix, img_file, boxes, res_dir, degrees_to_rotate)
        for j in range(len(boxes)):
            ocr_img_url_cut = format_img_url_cutout(ocr_img_url, boxes[j], p_w, p_h)
            entity = ut.create_entity(page_index, "", j+1, captions[j], percentages[j], boxes[j], infos, 
                                    image_name_prefix, p_w, p_h, ut.language_formatting(lang), 
                                    ocr_img_url_cut, "", "", "")
            # 3 last are 'author', 'publisher', 'contributor'
            writer.writerow(entity)
    print(f'{journal_name}, {publication_date}, {volume}, {issue_number}, {page_index}, volume_index: {volume_index+1}')
    page_entity = ut.create_page_entity(page_index, "", infos, p_w, p_h, ut.language_formatting(lang),
                                        ocr_img_url, "", "", "")
    page_writer.writerow(page_entity)
    return

def work_with_page(page_item:dict, out_dir:str, writer:csv.DictWriter, infos:list, res_dir:str, lang:str, page_writer:csv.DictWriter, volume_index:int):
    page_index = page_item["label"]["none"][0]
    img_url = page_item["items"][0]["items"][0]["body"]["id"]

    img_name = os.path.splitext(os.path.basename(out_dir))[0] +"_"+ ut.format_string(page_index)+".jpeg"
    img_path = os.path.join(out_dir, img_name)
    process_page_image(img_path, img_url, lang, writer, infos, page_index, res_dir, page_writer, volume_index)
    return

def work_with_issue(issue_item:dict, journal_name:str, year:str, volume:str, lang:str, out_dir:str, root_dir:str, volume_index:int):
    uuid = issue_item["id"]
    issue_json_name = os.path.join(root_dir, "issue.json")
    response_ok = ut.read_api_url(uuid, issue_json_name)
    print(f"Processing issue: {uuid}")
    print(f"API response status code: {response_ok}")
    if not response_ok: return False
    content = ut.load_json(issue_json_name)
    issue_number = extract_part_num(content["metadata"])
    publication_date = find_publication_date(content["metadata"])
    publication_date = format_publication_date(publication_date)
    
    issue_dir_name = "%s_%s_%s_%s" % (journal_name, year, volume, issue_number)#for the images
    issue_dir_name = ut.format_string(issue_dir_name)
    issue_res_dir = os.path.join(out_dir, issue_dir_name)
    ut.create_dir(issue_res_dir)
    
    items = content["items"]

    res_dir, csvfile_path, csvfile_pages_path = ut.create_result_dirs_and_files(issue_dir_name)
    writer, file = ut.create_csv_writer(csvfile_path, ut.IMG_HEAD_CSV)
    p_writer, p_file = ut.create_csv_writer(csvfile_pages_path, ut.PAGE_HEAD_CSV)
    infos = [journal_name, publication_date, volume, issue_number]

    for item in items:
        work_with_page(item, issue_res_dir, writer, infos, res_dir, lang, p_writer, volume_index)

    file.close()
    p_file.close()
    return

def work_with_year(year_item:dict, journal_name:str, lang:str, out_dir:str, root_dir:str, issue_start:int, issue_fin:int, volume_index:int):
    uuid = year_item["id"]
    year = year_item["label"]["none"][0]
    year_json_name = os.path.join(root_dir, "year.json")
    response_ok = ut.read_api_url(uuid, year_json_name)
    if not response_ok: return False
    content = ut.load_json(year_json_name)
    volume = extract_part_num(content["metadata"])
    out_dir = os.path.join(out_dir, year)
    out_dir = ut.format_string(out_dir)
    ut.create_dir(out_dir)
    items = content["items"]

    if issue_start > len(items): issue_start = 0 # if the start is greater than the number of items

    if issue_fin == 0: issue_fin = len(items)
    elif issue_fin >= len(items): issue_fin = len(items)
    else: issue_fin += 1
    
    for i in range(issue_start, issue_fin):
        success = work_with_issue(items[i], journal_name, year, volume, lang, out_dir, root_dir, volume_index)
    return

def work_with_periodical(content:dict, lang:str, out_dir:str, root_dir:str, volume_start:int, volume_fin:int, issue_start:int, issue_fin:int):
    journal_name = content["label"]["none"][0]
    out_dir = os.path.join(out_dir, journal_name)
    out_dir = ut.format_string(out_dir)
    ut.create_dir(out_dir)
    items = content["items"]
    
    if volume_start > len(items): volume_start = 0 #if the start is greater than the number of items
    if volume_fin == 0: volume_fin = len(items)
    elif volume_fin >= len(items): volume_fin = len(items)
    else: volume_fin += 1
    
    for i in range(volume_start, volume_fin):
        if i < volume_fin - 1: work_with_year(items[i], journal_name, lang, out_dir, root_dir, issue_start, 0, i)
        else: work_with_year(items[i], journal_name, lang, out_dir, root_dir, issue_start, issue_fin, i) # the last volume to process, must have the last issue given by user
        issue_start = 0
    return

def work_with_monografy(content:dict, lang:str, out_dir:str):
    monografy_name = extract_monografy_name(content["metadata"])

    monografy_out_dir = os.path.join(out_dir, monografy_name)
    monografy_out_dir = ut.format_string(monografy_out_dir)
    ut.create_dir(monografy_out_dir)

    items = content["items"]

    res_dir, csvfile_path, csvfile_pages_path = ut.create_result_dirs_and_files(ut.format_string(monografy_name))
    writer, file = ut.create_csv_writer(csvfile_path, ut.IMG_HEAD_CSV)
    p_writer, p_file = ut.create_csv_writer(csvfile_pages_path, ut.PAGE_HEAD_CSV)
    infos = [monografy_name, "", "", ""]
    for item in items:
        work_with_page(item, monografy_out_dir, writer, infos, res_dir, lang, p_writer, -2)

    file.close()
    p_file.close()
    return

def work_with_journal(url:str, out_dir:str, root_dir:str, volume_start:int, volume_fin:int, issue_start:int, issue_fin:int):
    journal_json_file = os.path.join(root_dir, 'journal.json')
    response_ok = ut.read_api_url(url, journal_json_file)
    if not response_ok: return

    content = ut.load_json(journal_json_file)
    metadata = extract_metadata(content["metadata"])
    if metadata["doctype"] == "Monografie":
        work_with_monografy(content, metadata["lang"], out_dir)
    if metadata["doctype"] == "Periodikum":
        work_with_periodical(content, metadata["lang"], out_dir, root_dir, volume_start, volume_fin, issue_start, issue_fin)
    return


def utility(url:str, volume_start:int, volume_fin:int, issue_start:int, issue_fin:int):
    api_url = convert_to_iiif(url)
    if api_url == None:
        print("invalid url:", url)
        return
    out_dir = 'temp'
    ut.create_dir(out_dir)
    result_out_dir = 'result'
    ut.create_dir(result_out_dir)

    work_with_journal(api_url, out_dir, out_dir, volume_start, volume_fin, issue_start, issue_fin)
    ut.delete_json_files(out_dir)
    return


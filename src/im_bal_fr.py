import xml.etree.ElementTree as ET
import os
import utility_funcs as ut
import cap_img_from_alto_fr as ci_alto
import image_mining_big as getim
import new_caption as getcap
import versions as vrs
import csv
import zipfile
import math
import cv2
import time

def get_issue_volume(manifest_path:str):
    issue, volume = '', ''
    tree = ET.parse(manifest_path)
    root = tree.getroot()
    for child in root:
        if child.tag.endswith('dmdSec'):
            mdwraps = (e for e in child.iter() if e.tag.endswith("mdWrap"))
            for md in mdwraps:
                xmldata = next((e for e in md if e.tag.endswith("xmlData")), None)
                if xmldata is None:
                    continue

                # Find a child whose attributes contain 'premis:representation'
                rep = next((e for e in xmldata.iter() if e.tag.endswith('spar_dc')), None)
                if rep is None:
                    continue

                for ch in rep:
                    if ch.tag.endswith('description'):
                        if 'spar_dc:sequentialDesignation1' in ch.attrib.values():
                            issue = ch.text
                        if 'spar_dc:sequentialDesignation2' in ch.attrib.values():
                            volume = ch.text

    return issue, volume


def extract_metadata(info:dict)->list[str]:
    '''
    Uses set of keys to extract important metadata.
    '''
    # no auter Contributeur
    meta_dict = {'Title':'', 'Author':'', 'Publisher':'', 'Date':'', 'Contributor':'', 'Language':''}
    info_list = info #info['contenu'][0]['contenu']
    for info in info_list:
        key = info['label']['en'][0]#ut.delete_diacritics(info['key']['contenu'])
        if key in meta_dict.keys():
            meta_dict[key] = info['value']['en'][0] if 'en' in info['value'].keys() else info['value']['fr'][0]#info['value']['contenu']
    meta = list(meta_dict.values())
    return meta

    # for key, value in info.items():
    #     info[key]


def convert_to_json(url:str)->str:
    # conversion_part = "/info.json"
    #  https://openapi.bnf.fr/iiif/presentation/v3/ark:/12148/bpt6k6120151n/manifest.json
    # 'https://gallica.bnf.fr/ark:/12148/bpt6k6120151n'
    url_id = url.split('/')[-1]
    json_url = f" https://openapi.bnf.fr/iiif/presentation/v3/ark:/12148/{url_id}/manifest.json"
    # conversion_part = "/manifest.json"
    # json_url = url + conversion_part
    return json_url

def find_identifier2(child: ET.Element) -> str:
    mdwraps = (e for e in child.iter() if e.tag.endswith("mdWrap"))
    for md in mdwraps:
        xmldata = next((e for e in md if e.tag.endswith("xmlData")), None)
        if xmldata is None:
            continue

        # Find a child whose attributes contain 'premis:representation'
        rep = next(
            (e for e in xmldata.iter()
             if 'premis:representation' in e.attrib.values()),
            None
        )
        if rep is None:
            continue

        obj_id = next(
            (e for e in rep.iter() if e.tag.endswith("objectIdentifier")),
            None
        )
        if obj_id is None:
            continue

        val = next(
            (e for e in obj_id if e.tag.endswith("objectIdentifierValue")),
            None
        )
        return val.text if val is not None else ""

    return ""

def get_jornal_url(file_name:str):
    prefix = 'https://gallica.bnf.fr/'

    tree = ET.parse(file_name)
    root = tree.getroot()

    for child in root:
        if child.tag.endswith('amdSec'):
            for ch2 in child:
                id = find_identifier2(ch2)
                if id: return prefix+id

    return ''

def convert_month_to_number(month:str)->str:
    if month.isnumeric(): return month
    month = ut.delete_diacritics(month.lower())
    months = {'janvier':'01', 'fevrier':'02', 'mars':'03', 
              'avril':'04', 'mai':'05', 'juin':'06', 
              'juillet':'07', 'aout':'08', 'septembre':'09', 
              'octobre':'10', 'novembre':'11', 'decembre':'12'}

    return months[month]

def format_publication_date(date:str)->str:
    '''Converts publication date 1 avril 1900 to database format 1900-04-01-1900-12-31,
        also converts publication date 1897-04-01 to 1897-04-01-1897-04-01'''
    
    split_date = []
    if '-' in date:
        split_date = date.split('-')
    elif ' ' in date:
        split_date = date.split(' ')
    else:
        split_date = [date]

    if len(split_date[0]) == 4: # first is a year
        split_date.reverse()
    
    pub_date = ""
    if len(split_date) == 3: #day, month, year
        day = split_date[0]
        month = convert_month_to_number(split_date[1])
        year = split_date[2]
        pub_date = "%s-%s-%s-%s-%s-%s" % (year, month, day, year, month, day)
    elif len(split_date) == 2:
        month = convert_month_to_number(split_date[0])
        year = split_date[1]
        pub_date = "%s-%s-%s-%s-%s-%s" % (year, month, "01", year, month, "31")
    elif len(split_date) == 1:
        year = split_date[0]
        pub_date = "%s-%s-%s-%s-%s-%s" % (year, "01", "01", year, "12", "31")
    return pub_date

def convert_to_img_url(issue_url:str, index:int):
    # img_url = f"{issue_url}/f{str(index)}.item.highres"
    # TODO: test new img url format
    # print("ISSUE URL", issue_url)
    issue_id = issue_url.split('/')[-1]
    # print('EXTRACTED ISSUE ID', issue_id)
    # img_url = f'https://gallica.bnf.fr/iiif/ark:/12148/{issue_id}/f{str(index)}/full/full/0/native.jpg'
    img_url = f"https://openapi.bnf.fr/iiif/image/v3/ark:/12148/{issue_id}/f{str(index)}/full/max/0/default.jpg"
    return img_url

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


def adjust_img_bbox(bbox:list[int], width_coeff:float, height_coeff:float)->list[int]:

    x = math.floor(bbox[0]*width_coeff)
    y = math.floor(bbox[1]*height_coeff) 
    w = math.ceil(bbox[2]*width_coeff)
    h = math.ceil(bbox[3]*height_coeff)

    return [x, y, w, h]


def adjust_bboxes(img_path, ocr_w, ocr_h, bboxes):
    h, w, _ = cv2.imread(img_path).shape

    width_coeff = w / ocr_w # ocr to phys
    height_coeff = h / ocr_h

    adjusted_bboxes = []
    for bbox in bboxes:
        new_bbox = adjust_img_bbox(bbox, width_coeff, height_coeff)
        adjusted_bboxes.append(new_bbox)

    return adjusted_bboxes

def shorten_journal_name(long_name:str)->str:
    split_name = long_name.split(' - ')
    if len(split_name) > 1: return split_name[0]
    split_name_gap = long_name.split(' ')
    short_name = ' '.join(split_name_gap[:5])
    return short_name

def process_page(ocr_file:str, index:int, issue_url:str, info:list[str], res_dir:str, writer:csv.DictWriter, p_writer:csv.DictWriter, img_path:str):
    # print('ocr file', ocr_file)
    boxes, captions, degrees_to_rotate, p_w, p_h = ci_alto.process_page_alto(ocr_file)
    img_url = convert_to_img_url(issue_url, index)
    page_index = index

    journal_name, author, publisher, publication_date, contributor, l, issue_number, year = info
    publication_date = format_publication_date(publication_date) # database format
    image_name_prefix = "%s_%s_%s_" % (ut.format_string(journal_name)[:10], ut.format_string(publication_date), ut.format_string(issue_number))
    lang = 'fra'
    infos = [journal_name, publication_date, year, issue_number]

    highres_img_url = img_url#img_url_to_open_format(highres_img_url)
    # print(highres_img_url)
    time.sleep(10)
    success = ut.save_img(highres_img_url, img_path)
    if success: # was able to download the page image
        if len(boxes) > 0: #page contains images
            boxes = adjust_bboxes(img_path, p_w, p_h, boxes)
            percentages, _ = vrs.get_versions(page_index, image_name_prefix, img_path, boxes, res_dir, degrees_to_rotate)
            for j in range(len(boxes)):
                highres_img_url_cut = format_img_url_cutout(highres_img_url, boxes[j], p_w, p_h)
                entity = ut.create_entity(page_index, "", j+1, captions[j], percentages[j], boxes[j], infos, 
                                        image_name_prefix, p_w, p_h, ut.language_formatting(lang), 
                                        highres_img_url_cut, author, publisher, contributor)
                # 3 last are 'author', 'publisher', 'contributor'
                writer.writerow(entity)
    print(f'{journal_name}, {publication_date}, {year}, {issue_number}, {page_index}')
    page_entity = ut.create_page_entity(page_index, "", infos, p_w, p_h, ut.language_formatting(lang),
                                        highres_img_url, author, publisher, contributor)
    p_writer.writerow(page_entity)
    return

def convert_url_to_img_url(url:str, root_dir:str)->str:
    '''
    This function downloads json file describing one page, 
    finds image link,
    coverts it to a link where the image is,
    returns it.
    '''
    page_json_url = convert_to_json(url)
    page_json_file = os.path.join(root_dir, 'page.json') 
    response_ok = ut.read_api_url(page_json_url, page_json_file)
    if not response_ok: return
    content = ut.load_json(page_json_file)

    img_url = content['fragment']['parameters']['externalPageArkUrl']

    img_label = '.highres'
    img_url = img_url+img_label
    return img_url

def process_page_image_no_ocr(img_path:str, img_url:str, writer:csv.DictWriter, info:list[str], page_index:str, res_dir:str, journal_n:str, p_writer:csv.DictWriter):
    journal_name, author, publisher, publication_date, contributor, l, issue_number, year = info
    publication_date = format_publication_date(publication_date) # database format
    image_name_prefix = "%s_%s_%s_" % (ut.format_string(journal_n), ut.format_string(publication_date), ut.format_string(issue_number))
    lang = 'fra'
    infos = [journal_name, publication_date, year, issue_number]

    highres_img_url = img_url#img_url_to_open_format(highres_img_url)
    # print(highres_img_url)
    time.sleep(3)
    success = ut.save_img(highres_img_url, img_path)
    boxes, p_h, p_w = getim.util(img_path, lang)
    captions, degrees_to_rotate = getcap.util(img_path, boxes, 'fra')
    if success: # was able to download the page image
        if len(boxes) > 0: #page contains images
            percentages, _ = vrs.get_versions(page_index, image_name_prefix, img_path, boxes, res_dir, degrees_to_rotate)
            for j in range(len(boxes)):
                highres_img_url_cut = format_img_url_cutout(highres_img_url, boxes[j], p_w, p_h)
                entity = ut.create_entity(page_index, "", j+1, captions[j], percentages[j], boxes[j], infos, 
                                        image_name_prefix, p_w, p_h, ut.language_formatting(lang), 
                                        highres_img_url_cut, author, publisher, contributor)
                # 3 last are 'author', 'publisher', 'contributor'
                writer.writerow(entity)
    print(f'{journal_name}, {publication_date}, {year}, {issue_number}, {page_index}')
    page_entity = ut.create_page_entity(page_index, "", infos, p_w, p_h, ut.language_formatting(lang),
                                        highres_img_url, author, publisher, contributor)
    p_writer.writerow(page_entity)
    return

def work_with_page_no_ocr(page_item:dict, issue_url:str, root_dir:str, writer:csv.DictWriter, info:list[str], journal_name:str, issue_temp_fol:str, res_dir:str, p_writer:csv.DictWriter):
    page_index = page_item['label']['fr'][0]#page_item['contenu']
    # https://openapi.bnf.fr/iiif/presentation/v3/ark:/12148/bpt6k6120151n/f1/canvas works foe this one
    page_num = page_item['id'].split('/')[-2][1:]
    # page_url = page_item['url']
    # img_url = convert_url_to_img_url(page_url, root_dir)
    img_url = convert_to_img_url(issue_url, page_num)
    if not img_url or len(img_url) == 0:
        print('bad img url', img_url)
        return

    page_index = page_index + '_' + page_num
    img_name =  ut.format_string(page_index)+".jpeg"
    img_path = os.path.join(issue_temp_fol, img_name)

    process_page_image_no_ocr(img_path, img_url, writer, info, page_index, res_dir, journal_name, p_writer)
    return

def process_pages(ocr_folder:str, issue_url:str, metadata:list[str], temp_folder:str, content:dict):
    root_dir = temp_folder
    batch_id = os.path.basename(os.path.dirname(ocr_folder))
    temp_folder = os.path.join(temp_folder, batch_id)
    ut.create_dir(temp_folder)

    res_dir, csvfile_path, csvfile_pages_path = ut.create_result_dirs_and_files(batch_id)
    writer, file = ut.create_csv_writer(csvfile_path, ut.IMG_HEAD_CSV)
    p_writer, p_file = ut.create_csv_writer(csvfile_pages_path, ut.PAGE_HEAD_CSV)

    if os.path.exists(ocr_folder):
        pages = os.listdir(ocr_folder)
        for i in range(len(pages)):
            page_path = os.path.join(ocr_folder, pages[i])
            index = i + 1
            img_path = os.path.join(temp_folder, str(index)+'.jpeg')
            process_page(page_path, index, issue_url, metadata, res_dir, writer, p_writer, img_path)
    else:
        pages_url = content['items']#content['PageAViewerFragment']['contenu']['PaginationViewerModel']['url']
        # pages_json_url = convert_to_json(pages_url)
        # pages_json_file = os.path.join(root_dir, 'pages.json') 
        # response_ok = ut.read_api_url(pages_json_url, pages_json_file)
        # if not response_ok: return
        # content = ut.load_json(pages_json_file)
        pages = pages_url#content['fragment']['contenu']
        journal_name = shorten_journal_name(metadata[0]) if len(metadata) else 'no_journal_name'
        for i in range(len(pages)):
            work_with_page_no_ocr(pages[i], issue_url, root_dir, writer, metadata, journal_name, temp_folder, res_dir, p_writer)
    file.close()
    p_file.close()
    return

# 'https://gallica.bnf.fr/ark:/12148/bpt6k6120151n'
def parse_issue(issue_url:str, ocr_folder:str, root_dir:str, issue:str, volume:str):
    if len(issue_url) > 0:
        issue_json_url = convert_to_json(issue_url)
        issue_json_file = os.path.join(root_dir, 'issue.json') 
        response_ok = ut.read_api_url(issue_json_url, issue_json_file)
        if not response_ok: return

        content = ut.load_json(issue_json_file)
        info = content['metadata']
        info = extract_metadata(info)
        info.append(issue)
        info.append(volume)

        print(info)
        process_pages(ocr_folder, issue_url, info, root_dir, content)
    return

def utility(folder_path:str):# one issue
    manifest_file_path = os.path.join(folder_path, 'manifest.xml')
    if not os.path.exists(manifest_file_path): return
    issue, volume = get_issue_volume(manifest_file_path)
    ocr_folder = os.path.join(folder_path, 'ocr')
    # if not os.path.exists(ocr_folder): return
    journal_url = get_jornal_url(manifest_file_path)
    out_dir = 'temp' #here will be json files
    ut.create_dir(out_dir)
    result_out_dir = 'result'
    ut.create_dir(result_out_dir)

    parse_issue(journal_url, ocr_folder, out_dir, issue, volume)
    return

def util(path_to_ocr):
    content = os.listdir(path_to_ocr)
    for item in content:
        item_path = os.path.join(path_to_ocr, item)
        if os.path.isdir(item_path) and 'manifest.xml' in os.listdir(item_path): # directly folder with manifest and ocr
            utility(item_path)
        elif os.path.isdir(item_path): # folder with folder with manifest and ocr (extracted manually)
            dirs = os.listdir(item_path)
            for d in dirs:
                d_path = os.path.join(item_path, d)
                utility(d_path)
        elif item.endswith('.zip'): # zip folder
            file_name = os.path.join(path_to_ocr, item) # get full path of files
            zip_ref = zipfile.ZipFile(file_name) # create zipfile object
            zip_ref.extractall(path_to_ocr) # extract file to dir
            zip_ref.close() # close file
            os.remove(file_name) # delete zipped file

            item_path = os.path.join(path_to_ocr, item)[:-4]
            if os.path.isdir(item_path):
                utility(item_path)
    ut.delete_json_files('temp')
    return

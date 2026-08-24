import os
import xml.etree.ElementTree as ET
import csv

import utility_funcs as ut
import cap_img_from_alto_deu as ci_alto
import versions as vrs
import image_mining_big as getim
import new_caption as cap

YEARS_SET_FOR_ISSUE_ONLY_JOURNALS = set()

STRUCT_MAP_TAG = "structMap"

def extract_journal_web_name(url:str)->str:
    '''
    Extracts web name of the journal assuming that given url
    is of the given format: https://digi.ub.uni-heidelberg.de/diglit/antiquitaeten_zeitung
    '''
    split_url = url.split('/')
    return split_url[-1]

def convert_to_xml(url:str)->str:
    # https://digi.ub.uni-heidelberg.de/diglitData/mets/antiquitaeten_zeitung.xml
    # https://digi.ub.uni-heidelberg.de/diglit/antiquitaeten_zeitung
    if url.endswith('/'): url = url[:-1]
    web_name = extract_journal_web_name(url)
    xml_url = "https://digi.ub.uni-heidelberg.de/diglitData/mets/%s.xml" % (web_name)

    return xml_url

def convert_mets_url_to_iiifv3(mets_url:str)->str:
    '''
    Converts mets url https://digi.ub.uni-heidelberg.de/diglit/antiquitaeten_zeitung1893/mets
    to iiif v.3 url https://digi.ub.uni-heidelberg.de/diglit/iiif3/antiquitaeten_zeitung1893/manifest
    '''

    split_mets_url = mets_url.split('/')
    journal_name_year = split_mets_url[-2]
    iiif_url = "https://digi.ub.uni-heidelberg.de/diglit/iiif3/%s/manifest" % (journal_name_year)
    return iiif_url

def find_href_in_attrib(el:ET.Element)->str:
    href_tag = 'href'
    keys = el.attrib.keys()
    for k in keys:
        if k.endswith(href_tag):
            return el.attrib[k]
    return ""

def parse_struct_map(struct_map:ET.Element)->list[str]:
    volume_mets_hrefs = []
    for el in struct_map:
        for el2 in el:
            for el3 in el2:
                href = find_href_in_attrib(el3)
                if len(href) > 0: volume_mets_hrefs.append(href)
    return volume_mets_hrefs

def find_volume_mets_urls(journal_xml:str)->list[str]:
    parser = ET.XMLParser(encoding="utf-8")
    tree = ET.parse(journal_xml, parser=parser)
    root = tree.getroot()
    volumes = []
    for el in root:
        if el.tag.endswith(STRUCT_MAP_TAG):
            volumes = parse_struct_map(el)
    return volumes

def find_journal_name(journal_xml:str)->str:
    dmdSec_tag = "dmdSec"
    title_tag = "title"
    # title_info_tag = "titleInfo"
    parser = ET.XMLParser(encoding="utf-8")
    tree = ET.parse(journal_xml, parser=parser)
    root = tree.getroot()

    for el in root:
        if el.tag.endswith(dmdSec_tag):
            for el2 in el:
                for el3 in el2:
                    for el4 in el3:
                        if el4.tag.endswith(title_tag):
                            return el4.text
    return ""

def add_zero_to_date(date:str)->str:
    if len(date) == 1: return "0%s" % (date)
    return date


def format_single_date(date:str)->str:
    '''Format a single date not a timespan.'''
    if len(date) == 0: return date
    pub_date = ""
    split_date = date.split('.')
    if len(split_date) == 3:
        day = add_zero_to_date(split_date[0])
        month = add_zero_to_date(split_date[1])
        year = split_date[2]
        pub_date = "%s-%s-%s-%s-%s-%s" % (year, month, day, year, month, day)
    elif len(split_date) == 2:
        month = add_zero_to_date(split_date[0])
        year = split_date[1]
        pub_date = "%s-%s-%s-%s-%s-%s" % (year, month, "01", year, month, "31")
    elif len(split_date) == 1:
        year = split_date[0]
        pub_date = "%s-%s-%s-%s-%s-%s" % (year, "01", "01", year, "12", "31")
    return pub_date

def format_half_date(date:str, month:str, day:str)->str:
    if len(date) == 0: return date
    pub_date = ""
    year = ""
    split_date = date.split('.')
    if len(split_date) == 3:
        day = add_zero_to_date(split_date[0])
        month = add_zero_to_date(split_date[1])
        year = split_date[2]
    elif len(split_date) == 2:
        month = add_zero_to_date(split_date[0])
        year = split_date[1]
    elif len(split_date) == 1:
        year = split_date[0]
    pub_date = "%s-%s-%s" % (year, month, day)
    return pub_date

def convert_deu_month_to_num(month:str)->str:
    deu_to_num = {
        'Januar':'01', 'Februar':'02', 'März':'03',
        'April':'04', 'Mai':'05', 'Juni':'06', 'Juli':'07',
        'August':'08', 'September':'09', 'Oktober':'10', 'November':'11', 'Dezember':'12'
    }
    return deu_to_num[month]

def format_date_with_slash(date:str)->str:
    split_year = date.split('.')
    year_slash = split_year[-1]
    year_split = year_slash.split('/')
    if len(year_split) == 2:
        year1 = year_split[0]
        year2 = year_split[1]
        if len(year1) == 4 and len(year2) == 2:
            pub_date = "%s-01-01-%s-12-31" % (year1, year1[0]+year1[1]+year2)
    return pub_date

def format_publication_date(date:str)->str:
    if len(date) == 0: return date
    # if date.count('/') == 2: # 3./4.1921/22
    #     split_dot = date.split('.')
    #     years = split_dot[-1]
    #     if '/' in years: return format_date_with_slash(years)
    if '/' in date: return format_date_with_slash(date)
    if '(' in date: date = date[:date.index('(')]
    if ',' in date: date = date[:date.index(',')]  # '1.1896, Band 1 (Nr. 1-26)'

    pub_date = ""
    split_date = date.split('-') #might be a span 1.1987-1988
    if len(split_date) == 1:
        split_date_gap = date.split(' ')
        if (len(split_date_gap) == 2 and split_date_gap[0].startswith('Nr.')):
            pub_date = format_single_date(split_date_gap[1])
        else:
            pub_date = format_single_date(date)
    elif len(split_date) == 2:
        first_date_split = split_date[0].strip().split(' ')
        second_date_split = split_date[1].strip().split(' ')
        if (len(first_date_split) == 2):
            if not first_date_split[0].isnumeric():
                first_date = format_half_date(first_date_split[1], month=convert_deu_month_to_num(first_date_split[0]), day="01")
            else:
                first_date = format_half_date(first_date_split[1], month=first_date_split[0], day="01")
        else:
            first_date = format_half_date(split_date[0], month="01", day="01")
        if (len(second_date_split) == 2):
            if not second_date_split[0].isnumeric():
                second_date = format_half_date(second_date_split[1], month=convert_deu_month_to_num(second_date_split[0]), day="01")
            else:
                second_date = format_half_date(second_date_split[1], month=second_date_split[0], day="01")
        else:
            if len(second_date_split[0]) == 2: split_date[1] = first_date[:2] + second_date_split[0]
            second_date = format_half_date(split_date[1], month="12", day="31")  
        pub_date = "%s-%s" % (first_date, second_date)
    # print(pub_date)
    pub_date = pub_date.replace(' ', '')
    return pub_date


def format_year(year:str)->str:
    year_split = year.split('/')
    if len(year_split) == 2:
        first_year = year_split[0]
        second_year = year_split[1]

        if len(second_year) != 4:
            second_year = first_year[:len(first_year)-len(second_year)] + second_year
        
        result_years = "%s-%s" % (first_year, second_year)
        return result_years
    else: return year


def find_publication_date_volume(meta:dict)->tuple:
    '''Returns year, volume, issue'''
    for m in meta:
        if m['label']['en'][0] == 'Date':
            date = m['value']['none'][0]
            date_split = date.split('.')
            if len(date_split) == 2:
                year = format_year(date_split[1])
                volume_or_issue = date_split[0]

                if volume_or_issue.startswith("Heft"):
                    global YEARS_SET_FOR_ISSUE_ONLY_JOURNALS
                    YEARS_SET_FOR_ISSUE_ONLY_JOURNALS.add(year)
                    issue_num = volume_or_issue
                    volume_num = len(YEARS_SET_FOR_ISSUE_ONLY_JOURNALS)
                    return year, volume_num, issue_num
                else:
                    return year, volume_or_issue, ""
            elif len(date_split) == 3: 
                if (date.count('/') == 2): # "3./4.1921/22"
                    span = f'{date_split[0]}-{date_split[1][1]}'
                    year = format_year(date_split[2])
                    return year, span, ""
                    
                else : # '1.1896, Band 1 (Nr. 1-26)'
                    year = format_year(date_split[1])
                    volume_or_issue = date_split[0]
                    return year, volume_or_issue, ""
            else:
                return date, date, "" # August 1914 - März 1916
    return "", "", ""

def get_alto_link(ocr_link:str, out_dir:str)->str:
    ocr_json_file = os.path.join(out_dir, 'ocr.json')
    response_ok = ut.read_api_url(ocr_link, ocr_json_file)
    if not response_ok: return
    content = ut.load_json(ocr_json_file)
    alto_link = content['items'][0]['body']['id']
    return alto_link

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

def work_with_page_image(img_path:str, page_image_url:str, writer:csv.DictWriter, metadata:list[str], page_index:str, res_dir:str, page_writer:csv.DictWriter, alto_link:str, volume_index:int):
    journal_name, publication_date, volume, issue = metadata
    image_name_prefix = "%s_%s_%s_%s_" % (ut.format_string(ut.shorten_name(journal_name)), ut.format_string(publication_date), volume, ut.format_string(ut.shorten_name(issue)))
    lang = "deu"
    infos = [journal_name, format_publication_date(publication_date), volume, issue]

    if (len(alto_link) == 0):
        success = ut.save_img(page_image_url, img_path)
        if success:
            boxes, p_h, p_w = getim.util(img_path, lang)
            highres_img_url = page_image_url
        else:
            boxes, captions, degrees_to_rotate, p_w, p_h, highres_img_url = [], [], [], -1, -1, page_image_url
    else:
        boxes, captions, degrees_to_rotate, p_w, p_h, highres_img_url = ci_alto.utility(page_image_url, res_dir, alto_link, img_path)
    if len(boxes) > 0:
        if (len(alto_link) == 0):
            captions, degrees_to_rotate = cap.util(img_path, boxes, lang)
        percentages, _ = vrs.get_versions(page_index, image_name_prefix, img_path, boxes, res_dir, degrees_to_rotate)
        for j in range(len(boxes)):
            highres_img_url_cut = format_img_url_cutout(highres_img_url, boxes[j], p_w, p_h)
            entity = ut.create_entity(page_index, "", j+1, captions[j], percentages[j], boxes[j], infos,
                                      image_name_prefix, p_w, p_h, ut.language_formatting(lang),
                                      highres_img_url_cut, "", "", "")
            print('URL', highres_img_url_cut)
            writer.writerow(entity)
    print(f'{journal_name}, {infos[1]}, {volume}, {issue}, {page_index}, volume_index: {volume_index+1}')
    page_entity = ut.create_page_entity(page_index, "", infos, p_w, p_h, ut.language_formatting(lang),
                                        highres_img_url, "", "", "")
    page_writer.writerow(page_entity)
    return 

def work_with_page(page:dict, metadata:list[str], out_dir:str, temp_folder:str, writer:csv.DictWriter, page_writer:csv.DictWriter, res_dir:str, volume_index:int):
    canvas_id = page['id']

    page_json_file = os.path.join(out_dir, 'page.json')
    response_ok = ut.read_api_url(canvas_id, page_json_file)
    if not response_ok: return

    content = ut.load_json(page_json_file)
    page_index = content['label']['none'][0]
    # print('page index:', page_index)
    page_image_url = content['items'][0]['items'][0]['body']['id']

    if len(content['annotations']) > 0:
        alto_link = get_alto_link(content['annotations'][0]['id'], out_dir)
    else:
        alto_link = ''

    img_name =  ut.format_string(page_index)+".jpeg"
    img_path = os.path.join(temp_folder, img_name)

    if os.path.exists(img_path):
        page_index += '_02'
        img_name =  ut.format_string(page_index)+".jpeg"
        img_path = os.path.join(temp_folder, img_name)

    work_with_page_image(img_path, page_image_url, writer, metadata, page_index, res_dir, page_writer, alto_link, volume_index)

    return


def work_with_pages(content:dict, out_dir:str, temp_folder:str, metadata:list[str], volume_index:int):
    label = content['label']['none'][0]
    label = ut.shorten_name(label)
    pages = content['items']

    issue_temp_fol = os.path.join(temp_folder, ut.format_string(label))
    ut.create_dir(issue_temp_fol)

    issue_dir_name = "%s_%s_%s_%s" % (ut.shorten_name(metadata[0]), metadata[2], ut.shorten_name(metadata[1]), label)#for the page images
    issue_dir_name = ut.format_string(issue_dir_name)

    res_dir, csvfile_path, csvfile_pages_path = ut.create_result_dirs_and_files(issue_dir_name)
    writer, file = ut.create_csv_writer(csvfile_path, ut.IMG_HEAD_CSV)
    p_writer, p_file = ut.create_csv_writer(csvfile_pages_path, ut.PAGE_HEAD_CSV)


    for i in range(len(pages)):
        work_with_page(pages[i], metadata, out_dir, issue_temp_fol, writer, p_writer, res_dir, volume_index)
    
    file.close()
    p_file.close()

    big_original_path = os.path.join(res_dir, "big_original")
    ut.clean_if_empty(big_original_path, [csvfile_path, csvfile_pages_path])
    return


def work_with_volume(iiif_url:str, out_dir:str, temp_folder:str, metadata:list[str], volume_index:int):
    # iiif_url = convert_mets_url_to_iiifv3(mets_url)

    volume_json_file = os.path.join(out_dir, 'volume.json')
    response_ok = ut.read_api_url(iiif_url, volume_json_file)
    if not response_ok: return
    content = ut.load_json(volume_json_file)
    publication_date, volume, issue_num = find_publication_date_volume(content['metadata'])
    metadata[1] = publication_date 
    metadata[2] = volume
    metadata[3] = issue_num

    year_temp_fol = os.path.join(temp_folder, ut.format_string(publication_date))
    ut.create_dir(year_temp_fol)

    work_with_pages(content, out_dir, year_temp_fol, metadata, volume_index)
    return



def work_with_journal(url:str, out_dir:str, volume_start:int, volume_fin:int):
    journal_json_file = os.path.join(out_dir, 'journal.xml')
    response_ok = ut.read_api_url(url, journal_json_file)
    if not response_ok: return

    journal_name = find_journal_name(journal_json_file)
    metadata = [journal_name, '', '', '']
    volume_urls = find_volume_mets_urls(journal_json_file)

    journal_folder_temp = os.path.join(out_dir, ut.format_string(ut.shorten_name(journal_name)))
    ut.create_dir(journal_folder_temp)

    if (len(volume_urls)):
        if volume_start > len(volume_urls): volume_start = 0

        if volume_fin == 0: volume_fin = len(volume_urls)
        elif volume_fin >= len(volume_urls): volume_fin = len(volume_urls)
        else: volume_fin += 1 # 3 to 3 (user version) turns into 3 to 4

        for i in range(volume_start, volume_fin):
            iiif_url = convert_mets_url_to_iiifv3(volume_urls[i])
            work_with_volume(iiif_url, out_dir, journal_folder_temp, metadata, i)
    else:
        split_url = url.split('/')
        name_xml_split = split_url[-1].split('.')[0] 
        iiif_url = "https://digi.ub.uni-heidelberg.de/diglit/iiif3/%s/manifest" % (name_xml_split)
        work_with_volume(iiif_url, out_dir, journal_folder_temp, metadata, 0)
    
    return


def utility(url:str, volume_start:int, volume_fin:int):
    api_url = convert_to_xml(url)
    if api_url == None:
        print("Invalid url: ", url)
        return
    out_dir = 'temp'
    ut.create_dir(out_dir)
    result_dir = 'result'
    ut.create_dir(result_dir)

    work_with_journal(api_url, out_dir, volume_start, volume_fin)
    global YEARS_SET_FOR_ISSUE_ONLY_JOURNALS
    YEARS_SET_FOR_ISSUE_ONLY_JOURNALS.clear()
    ut.delete_json_files(out_dir)
    return



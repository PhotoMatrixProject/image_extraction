import os
import utility_funcs as ut
import csv
import cap_img_from_alto_fr as ci_alto
import versions as vrs
import image_mining_big as getim
import new_caption as getcap

def convert_to_json(url:str)->str:
    conversion_part = "/info.json"
    json_url = url + conversion_part
    return json_url

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

def create_img_name(journal_name:str, volume:str, issue:str)->str:
    name = journal_name+"_"+volume+"_"+issue
    name = ut.format_string(name)
    return name

def language_formatting_for_text_detection(lang:str)->str: #TODO: find more languages in french
    lang = ut.delete_diacritics(lang)
    if lang == "français":return "fra"
    return "fra" # default, if it is not possible to recognize language in json file

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

def convert_month_to_issue_number(pub_date:str)->str:
    '''Extracts issue number as a month from 01 juillet 1909 ->  7'''
    split_date = pub_date.split(' ')
    issue = ""
    if len(split_date) == 3:
        issue = convert_month_to_number(split_date[1])
    elif len(split_date) == 2:
        issue = convert_month_to_number(split_date[0])
    return issue

def extract_metadata(info:dict)->list[str]:
    '''
    Uses set of keys to extract important metadata.
    '''

    meta_dict = {'Titre':'', 'Auteur':'', 'Editeur':'', 'Date d\'edition':'', 'Contributeur':'', 'Langue':''}
    info_list = info['contenu'][0]['contenu']
    for info in info_list:
        key = ut.delete_diacritics(info['key']['contenu'])
        if key in meta_dict.keys():
            meta_dict[key] = info['value']['contenu']
    meta = list(meta_dict.values())
    return meta


def get_identifier(page_url:str)->str:
    split_url = page_url.split('/')
    if len(split_url) > 2:
        return split_url[-2]
    return ""

def get_page_num(page_url:str)->str:
    split_url = page_url.split('/')
    if len(split_url) > 1:
        item = split_url[-1]
        f_num = item.split('.')[0]
        num = f_num[1:]
        return num
    return ""

def convert_page_url_to_alto_url(page_url:str)->str:
    '''
    Converts page url to the alto url of the page 
    (example of the expected url: 
    'https://gallica.bnf.fr/services/ajax/pagination/page/SINGLE/ark:/12148/bpt6k9740716w/f1.item')
    '''
    
    identifier = get_identifier(page_url)
    page_num = get_page_num(page_url)

    alto_url = "https://gallica.bnf.fr/RequestDigitalElement?O=%s&E=ALTO&Deb=%s" % (identifier, page_num)
    return alto_url


def get_active_volumes(grid:dict)->list: #TODO: TEST!!!
    active_items = []
    grid_rows = grid['contenu']['CalendarGrid']['contenu'] #list of rows
    for row in grid_rows:
        row_columns = row['contenu']
        
        for column in row_columns:
            if len(column['url'])>0:
                active_items.append(column)
    return active_items

def get_active_issues(grid:dict)->list:
    active_items = []
    grid_rows = grid['contenu'] #list of rows
    for row in grid_rows:
        row_columns = row['contenu']
        
        for column in row_columns:
            if column['active']:
                active_items.append(column)
    return active_items

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

def img_url_to_open_format(img_url:str)->str:
    '''
    'https://gallica.bnf.fr/iiif/ark:/12148/bd6t54135551/f1/full/4589,5296/0/native.jpg'

    '''

    img_url_split = img_url.split('/')
    id = img_url_split[-6]
    screenNumber = img_url_split[-5]
    size = img_url_split[-3]
    res_url = f'https://openapi.bnf.fr/iiif/image/v3/ark:/12148/{id}/{screenNumber}/full/{size}/0/default.jpg'

    return res_url

def process_page_image(img_path:str, img_url:str, writer:csv.DictWriter, info:list[str], page_index:str, res_dir:str, journal_n:str, p_writer:csv.DictWriter, volume_index:int):
    journal_name, author, publisher, publication_date, contributor, l, issue_number, year = info
    publication_date = format_publication_date(publication_date) # database format
    image_name_prefix = "%s_%s_%s_" % (ut.format_string(journal_n), ut.format_string(publication_date), ut.format_string(issue_number))
    lang = language_formatting_for_text_detection(l)
    infos = [journal_name, publication_date, year, issue_number]

    highres_img_url = img_url#img_url_to_open_format(highres_img_url)
    print(highres_img_url)
    success = ut.save_img(highres_img_url, img_path)
    boxes, p_h, p_w = getim.util(img_path, lang)
    # boxes, captions, degrees_to_rotate, p_w, p_h, highres_img_url = ci_alto.utility(img_url, res_dir)
    # highres_img_url = img_url#img_url_to_open_format(highres_img_url)
    # success = ut.save_img(highres_img_url, img_path)
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
    print(f'{journal_name}, {publication_date}, {year}, {issue_number}, {page_index}, volume_index: {volume_index+1}')
    page_entity = ut.create_page_entity(page_index, "", infos, p_w, p_h, ut.language_formatting(lang),
                                        highres_img_url, author, publisher, contributor)
    p_writer.writerow(page_entity)
    return

def work_with_page(page_item:dict, root_dir:str, writer:csv.DictWriter, info:list[str], journal_name:str, issue_temp_fol:str, res_dir:str, p_writer:csv.DictWriter, volume_index:int):
    page_index = page_item['contenu']
    page_url = page_item['url']
    img_url = convert_url_to_img_url(page_url, root_dir)
    if not img_url or len(img_url) == 0:
        print('bad img url', img_url)
        return

    page_index = page_index + '_' + ci_alto.get_page_num(img_url)
    img_name =  ut.format_string(page_index)+".jpeg"
    img_path = os.path.join(issue_temp_fol, img_name)

    process_page_image(img_path, img_url, writer, info, page_index, res_dir, journal_name, p_writer, volume_index)
    return

def work_with_pages(url:str, root_dir:str, info:list[str], journal_name:str, year:str, issue_month:str, issue_num:str, issue_temp_fol:str, volume_index:int):
    pages_json_url = convert_to_json(url)
    pages_json_file = os.path.join(root_dir, 'pages.json') 
    response_ok = ut.read_api_url(pages_json_url, pages_json_file)
    if not response_ok: return
    content = ut.load_json(pages_json_file)
    pages = content['fragment']['contenu']

    issue_month = issue_month + '_' + issue_num
    issue_dir_name = "%s_%s_%s" % (journal_name, year, issue_month)#for the page images
    issue_dir_name = ut.format_string(issue_dir_name)
    issue_temp_fol = os.path.join(issue_temp_fol, issue_dir_name)
    ut.create_dir(issue_temp_fol)

    res_dir, csvfile_path, csvfile_pages_path = ut.create_result_dirs_and_files(issue_dir_name)
    writer, file = ut.create_csv_writer(csvfile_path, ut.IMG_HEAD_CSV)
    p_writer, p_file = ut.create_csv_writer(csvfile_pages_path, ut.PAGE_HEAD_CSV)
    infos = info + [issue_month, year]
    for i in range(len(pages)):
        work_with_page(pages[i], root_dir, writer, infos, journal_name, issue_temp_fol, res_dir, p_writer, volume_index)

    file.close()
    p_file.close()
    return

def work_with_issue_xml(xml_url:str, root_dir:str)->str:
    '''Extracts an url, which contains issue data from xml file'''

    issue_xml_file = os.path.join(root_dir, 'issue.xml')
    response_ok = ut.read_api_url(xml_url, issue_xml_file)
    if not response_ok: return
    file = open(issue_xml_file,  encoding="utf8", mode='r')
    content = file.read()
    words = content.split(' ')
    content_label = "content=\""
    url_label = "https://"
    content_url = ""
    for word in words:
        if word.startswith(content_label+url_label):
            content_url = word
            break
    url = content_url.split("\"")[1] if len(content_url.split("\"")) > 2 else ""
    return url

def work_with_issue(issue:dict, root_dir:str, journal_name:str, year:str, issue_month:str, issue_num:str, issue_temp_fol:str, volume_index:int):
    issue_url = issue['url']
    issue_url = work_with_issue_xml(issue_url, root_dir)
    if len(issue_url) > 0:
        issue_json_url = convert_to_json(issue_url)
        issue_json_file = os.path.join(root_dir, 'issue.json') 
        response_ok = ut.read_api_url(issue_json_url, issue_json_file)
        if not response_ok: return

        content = ut.load_json(issue_json_file)
        info = content['InformationsModel']
        info = extract_metadata(info)
        pages_url = content['PageAViewerFragment']['contenu']['PaginationViewerModel']['url']

        work_with_pages(pages_url, root_dir, info, journal_name, year, issue_month, issue_num, issue_temp_fol, volume_index)
    else:
        pre_issue_url = issue['url']
        pre_issue_json_url = convert_to_json(pre_issue_url)
        pre_issue_json_file = os.path.join(root_dir, 'pre_issue.json') 
        response_ok = ut.read_api_url(pre_issue_json_url, pre_issue_json_file)
        if not response_ok: return
        content = ut.load_json(pre_issue_json_file)

        issue_parts = content['PeriodicalPageFragment']['contenu']['SearchResultsFragment']['contenu']['ResultsFragment']['contenu']

        for i in range(len(issue_parts)):
            if issue_parts[i]['active'] == True:
                issue_title = issue_parts[i]['title']
                issue_num_num = '_'+str(i)
                work_with_issue(issue_title, root_dir, journal_name, year, issue_month, issue_num+issue_num_num, issue_temp_fol, volume_index)
    return


def work_with_month(month:dict, root_dir:str, journal_name:str, year:str, temp_fol:str, issue_start:str, issue_fin:int, volume_index:int):
    issue_month = convert_month_to_number(month['parameters']['nom'])
    items = get_active_issues(month)
    
    if issue_start > len(items): issue_start = 0 # if the start is greater than the number of items

    if issue_fin == 0: issue_fin = len(items)
    elif issue_fin >= len(items): issue_fin = len(items)
    else: issue_fin += 1

    for i in range(issue_start, issue_fin):
        work_with_issue(items[i], root_dir, journal_name, year, issue_month, str(i), temp_fol, volume_index)
    return

def work_with_one_month_issue(issue:dict, root_dir:str, journal_name:str, year:str, year_temp_fol:str, volume_index:int):
    issue_month = issue['PageAViewerFragment']['contenu']['IssuePaginationFragment']['currentPage']['contenu']
    issue_month = convert_month_to_issue_number(issue_month)
    issue_num = "1"
    # issue_temp_fol = os.path.join(year_temp_fol, ut.format_string(issue_month))
    # ut.create_dir(issue_temp_fol)
    info = issue['InformationsModel']
    info = extract_metadata(info)
    pages_url = issue['PageAViewerFragment']['contenu']['PaginationViewerModel']['url']
    
    work_with_pages(pages_url, root_dir, info, journal_name, year, issue_month, issue_num, year_temp_fol, volume_index)
    return

def work_with_volume(volume:dict, root_dir:str, journal_name:str, temp_fol:str, month_start:int, month_fin:int, issue_start:int, issue_fin:int, volume_index:int):
    year = volume['description']

    year_temp_fol = os.path.join(temp_fol, ut.format_string(year))
    ut.create_dir(year_temp_fol)

    volume_url = volume['url']
    volume_json_url = convert_to_json(volume_url)
    volume_json_file = os.path.join(root_dir, 'volume.json') 
    response_ok = ut.read_api_url(volume_json_url, volume_json_file)
    if not response_ok: return

    content = ut.load_json(volume_json_file)
    if 'PeriodicalPageFragment' in content.keys():
        months = content['PeriodicalPageFragment']['contenu']['CalendarPeriodicalFragment']['contenu']['CalendarGrid']['contenu']

        if month_start > len(months): month_start = 0
        
        if month_fin == 0: month_fin = len(months)
        elif month_fin >= len(months): month_fin = len(months)
        else: month_fin += 1
        for i in range(month_start, month_fin):
            if i < month_fin-1:  work_with_month(months[i], root_dir, journal_name, year, year_temp_fol, issue_start, 0, volume_index)
            else: work_with_month(months[i], root_dir, journal_name, year, year_temp_fol, issue_start, issue_fin, volume_index)
            issue_start = 0
    elif 'PageAViewerFragment' in content.keys():
        work_with_one_month_issue(content, root_dir, journal_name, year, year_temp_fol, volume_index)

    return

def work_with_volumes(volumes:dict, root_dir:str,  journal_name:str, temp_fol:str, volume_start:int, volume_fin:int, month_start:int, month_fin:int, issue_start:int, issue_fin:int):
    items = get_active_volumes(volumes)

    if volume_start > len(items): volume_start = 0

    if volume_fin == 0: volume_fin = len(items)
    elif volume_fin >= len(items): volume_fin = len(items)
    else: volume_fin += 1

    for i in range(volume_start, volume_fin):
        if i < volume_fin-1: work_with_volume(items[i], root_dir, journal_name, temp_fol, month_start, 0, issue_start, 0, i)
        else: work_with_volume(items[i], root_dir, journal_name, temp_fol, month_start, month_fin, issue_start, issue_fin, i)
        month_start = 0 # next volume will be processed from the beginning (first month, first issue)
        issue_start = 0
    return
 
def shorten_journal_name(long_name:str)->str:
    split_name = long_name.split(' - ')
    if len(split_name) > 1: return split_name[0]
    split_name_gap = long_name.split(' ')
    short_name = ' '.join(split_name_gap[:5])
    return short_name

def work_with_journal(url:str, root_dir:str, volume_start:int, volume_fin:int, month_start:int, month_fin:int, issue_start:int, issue_fin:int):
    journal_json_file = os.path.join(root_dir, 'journal.json')
    response_ok = ut.read_api_url(url, journal_json_file)
    if not response_ok: return
    content = ut.load_json(journal_json_file)
    
    if 'PeriodicalPageFragment' in content.keys():
        journal_name = content['PeriodicalPageFragment']['contenu']['PageModel']['parameters']['title']
        journal_name = shorten_journal_name(journal_name)
        volumes = content['PeriodicalPageFragment']['contenu']['CalendarPeriodicalFragment']

        journal_folder_temp = os.path.join(root_dir, ut.format_string(journal_name))
        ut.create_dir(journal_folder_temp)
        work_with_volumes(volumes, root_dir, journal_name, journal_folder_temp, volume_start, volume_fin, month_start, month_fin, issue_start, issue_fin)
    elif 'PageAViewerFragment' in content.keys():
        info = content['InformationsModel']
        info = extract_metadata(info)

        journal_name = shorten_journal_name(info[0])
        journal_folder_temp = os.path.join(root_dir, ut.format_string(journal_name))
        ut.create_dir(journal_folder_temp)

        year = info[3]
        year_temp_fol = os.path.join(journal_folder_temp, ut.format_string(year))
        ut.create_dir(year_temp_fol)
        work_with_one_month_issue(content, root_dir, journal_name, year, year_temp_fol, -2)
    
    return

def strip_url_from_request(url:str)->str:
    split_url = url.split('?')
    return split_url[0]

def get_rid_of_bad_ending(url:str)->str:
    flag_to_delete = ".planchecontact"
    if url.endswith(flag_to_delete):
        return url[:len(url)-len(flag_to_delete)]
    return url


def utility(url:str, volume_start:int, volume_fin:int, month_start:int, month_fin:int, issue_start:str, issue_fin:int)->None:
    url = strip_url_from_request(url)
    url = get_rid_of_bad_ending(url)
    api_url = convert_to_json(url)
    if api_url == None:
        print("invalid url:", url)
        return
    out_dir = 'temp' #here will be json files
    ut.create_dir(out_dir)
    result_out_dir = 'result'
    ut.create_dir(result_out_dir)
    work_with_journal(api_url, out_dir, volume_start, volume_fin, month_start, month_fin, issue_start, issue_fin)
    ut.delete_json_files(out_dir)
    return


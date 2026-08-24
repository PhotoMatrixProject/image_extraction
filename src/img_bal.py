import cv2
import os
import xml.etree.ElementTree as ET
import image_mining_big as getim
import new_caption as cap
import versions as vrs
import utility_funcs as ut
import os
import csv

TITLE_CONST = 'title'
VOLUME_CONST = 'partNumber'
YEAR_CONST = "dateIssued"
ISSUE_CONST = "partNumber"
LANGUAGE_CONST = "language"

def convert_jp2_to_png(folder_in, folder_out):
    files = os.listdir(folder_in)
    number_of_imgs = 0
    for i, file in enumerate(files):
        file_path = os.path.join(folder_in, file)
        if os.path.isfile(file_path):
            number_of_imgs += 1
            image = cv2.imread(file_path)
            cv2.imwrite(folder_out+'\\'+str(number_of_imgs)+'.png', image)
            # cv2.imwrite(folder_out+'\\'+str(i)+'.png', image)
            # print(i)
    return number_of_imgs

def normilize_date(date : str):
    date_span = date.split('-')
    start = '-01-01-'
    end = '-12-31'
    result = ""
    if len(date_span) == 2:
        result = date_span[0] + start + date_span[1] + end
    elif len(date_span) == 1:
        result = date_span[0] + start + date_span[0] + end

    return result

def get_clean_tag(tag, length):    
    return tag[len(tag)-length:]

def xml_to_dict_recursive(root, attr_name):
    res = []
    for child in root:
        if not child:
            if (get_clean_tag(child.tag, len(attr_name)) == attr_name):
                res.append(child.text)
                return res
        else:
            res += xml_to_dict_recursive(child, attr_name)
    return res

def get_page_nums_inds(root):
    ORDER_KEY = "ORDER"
    ORDERLABEL_KEY = "ORDERLABEL"
    nums = []
    inds = []
    for c in root.iter():
        if (ORDER_KEY in c.attrib.keys() and ORDERLABEL_KEY in c.attrib.keys()):
            nums.append(c.attrib[ORDER_KEY])
            inds.append(c.attrib[ORDERLABEL_KEY])
    return nums, inds

def metadata_reader_monograph(file):
    volume = 'Monograph'
    parser = ET.XMLParser(encoding="utf-8")
    tree = ET.parse(file, parser=parser)
    root = tree.getroot()

    for child in root:
        if 'ID' in child.attrib.keys() and child.attrib['ID'] == 'MODSMD_VOLUME_0001':
            res = xml_to_dict_recursive(child, 'title')
        # elif 'ID' in child.attrib.keys() and child.attrib['ID'] == 'DCMD_VOLUME_0001':
        #     print(child)
    
    if len(res) > 0:
        journal_name = res[0]
    return journal_name, volume

def metadata_reader(file):
    parser = ET.XMLParser(encoding="utf-8")
    tree = ET.parse(file, parser=parser)
    root = tree.getroot()
    KEY = 'ID'
    KEY2 = "LABEL"
    LABEL = "Physical_Structure"
    TITLE_ID = 'MODSMD_TITLE_0001'
    TITLE2_ID = 'DCMD_TITLE_0001'
    VOLUME_ID = 'MODSMD_VOLUME_0001'
    ISSUE_ID = 'MODSMD_ISSUE_0001'
    res_title = ""
    res_lang = ""
    res_volume = ""
    res_issue = ""
    res_year = ""
    page_nums = []
    page_inds = []
    for child in root:
        if (KEY in child.attrib.keys() and child.attrib['ID'] == TITLE_ID):
            title = xml_to_dict_recursive(child, TITLE_CONST)#title
            if len(title) >= 4: res_title = title[3]
            elif len(title)>0: res_title = title[0]
        elif (KEY in child.attrib.keys() and child.attrib[KEY] == TITLE2_ID):#language
            lang = xml_to_dict_recursive(child, LANGUAGE_CONST)
            if len(lang)>0: res_lang = lang[0]
        elif (KEY in child.attrib.keys() and child.attrib[KEY] == VOLUME_ID):#volume
            volume = xml_to_dict_recursive(child, VOLUME_CONST)
            if len(volume)>0: res_volume = volume[0]
            year = xml_to_dict_recursive(child, YEAR_CONST)
            if len(year) > 0: res_year = normilize_date(year[0])
        elif (KEY in child.attrib.keys() and child.attrib[KEY] == ISSUE_ID):#issue
            issue = xml_to_dict_recursive(child, ISSUE_CONST)
            if (len(issue)>0): res_issue = issue[0]
        elif (KEY2 in child.attrib.keys() and child.attrib[KEY2] == LABEL):
            page_nums, page_inds = get_page_nums_inds(child)
        
    if len(res_title) == 0: res_title, res_volume = metadata_reader_monograph(file)
        
    return [res_title, res_lang, res_volume, res_year, res_issue, page_nums, page_inds]

def work_with_batch(img_f, batch_path):
    DATA_FILE_FLAG = "mets"
    metadata = []
    jp2_folder = batch_path+'\\'+'usercopy'
    page_count = 0
    if os.path.exists(jp2_folder):#if there is a folder with jp2s
        files = os.listdir(batch_path)
        for file in files:
            file_path = os.path.join(batch_path, file)
            if os.path.isfile(file_path) and file_path.endswith('.xml') and len(file)>3 and file[0:4].lower() == DATA_FILE_FLAG:
                metadata = metadata_reader(file_path)
        
        batch_name = os.path.splitext(os.path.basename(batch_path))[0]
        folder_name = img_f#+"\\"+batch_name
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)

        page_count = convert_jp2_to_png(jp2_folder, folder_name)
        
    return metadata, page_count

def image_name(metadata):
    parsed_meta = metadata
    if len(parsed_meta) < 4: return ""
    split_pn = metadata[0].split(' ')
    name = ""
    for i in range(len(split_pn)):
        name += split_pn[i][0]
    year = parsed_meta[1]
    volume = parsed_meta[2]
    issue = parsed_meta[3]
    res_name = name+"_%s_%s_%s_" % (year, volume, issue)
    return res_name

def process_data(bfolder:str, metadata:list, output_folder:str, lang_op:str, imgfolder:str, page_count:int):
    # parsed_meta = [ut.format_string(metadata[0]), ut.format_string(metadata[4]), ut.format_string(metadata[2]), ut.format_string(metadata[3])]
    parsed_meta = [ut.format_string(metadata[0]), metadata[3], ut.format_string(metadata[2]), ut.format_string(metadata[4])]

    if len(parsed_meta[0]) == 0: image_name_prefix = ""
    else: image_name_prefix = image_name(parsed_meta)

    journal_info = os.path.splitext(os.path.basename(bfolder))[0]#batch name

    res_dir, csvfile_path, csvfile_pages_path = ut.create_result_dirs_and_files(journal_info, result_root=ut.RESULT_PATH_ON_PC)
    writer, f = ut.create_csv_writer(csvfile_path, ut.IMG_HEAD_CSV)
    p_writer, p_file = ut.create_csv_writer(csvfile_pages_path, ut.PAGE_HEAD_CSV)

    for i in range(1, page_count+1):#page numbers start from 1
        file = imgfolder + "/%d.png" % i
        boxes, p_h, p_w = getim.util(file, lang_op)
        
        if (i >= len(metadata[5])): #assumption: page number always has page index
            pnum, pind = str(i+1), ""
        else:
            if (i >= len(metadata[6])): pind = ""
            else: pind =  metadata[6][i]
            pnum = metadata[5][i]
        
        if len(boxes) > 0: #page contains images
            captions, degrees_to_rotate = cap.util(file, boxes, lang_op)
            percentages, img_paths = vrs.get_versions(pnum, image_name_prefix, file, boxes, res_dir, degrees_to_rotate)
            for j in range(len(boxes)):
                entity = ut.create_entity(pind, pnum, j+1, captions[j], percentages[j], boxes[j], parsed_meta,
                                        image_name_prefix, p_w, p_h, ut.language_formatting(lang_op), 
                                        img_paths[j], "", "", "")
                # the last 4 'img address', 'author', 'publisher', 'contributor
                writer.writerow(entity)
        print(parsed_meta[0], parsed_meta[1], parsed_meta[2], parsed_meta[3], pind, pnum)
        page_entity = ut.create_page_entity(pind, pnum, parsed_meta, p_w, p_h, ut.language_formatting(lang_op),
                                            file, "", "", "")
        p_writer.writerow(page_entity)
    f.close()
    p_file.close()

    return

def util_with_batch(temp_path, res_path, batch_path, lang):
    metadata, page_count = work_with_batch(temp_path, batch_path)
    if len(metadata) == 0:
        return
    process_data(batch_path, metadata, res_path, lang, temp_path, page_count)


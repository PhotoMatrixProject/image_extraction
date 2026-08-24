import image_mining_big as getim
import new_caption as cap
import versions as vrs
import utility_funcs as ut
import os
import csv
from unidecode import unidecode


def format_data(data:str)->str:
    data_split = data.split('_')
    if len(data_split) == 6:
        y1, m1, d1, y2, m2, d2 = data_split
        if len(m1) == 1: m1 = '0' + m1
        if len(d1) == 1: d1 = '0' + d1
        if len(m2) == 1: m2 = '0' + m2
        if len(d2) == 1: d2 = '0' + d2
        return '-'.join([y1, m1, d1, y2, m2, d2])
    else:
        return '1999-12-31-1999-12-31'

def parse_metadata(metadata):
    parsed_metadata = ['', '', '', '']
    name_issue_year = metadata.split(', ')
    for i in range(len(name_issue_year)):
        parsed_metadata[i] = ut.format_string(name_issue_year[i])
        if i == 3:
            break
    # sorted_parsed_matadata = [parsed_metadata[0], parsed_metadata[3], parsed_metadata[2], parsed_metadata[1]]
    sorted_parsed_matadata = [parsed_metadata[0], format_data(parsed_metadata[1]), parsed_metadata[2], parsed_metadata[3]]
    return sorted_parsed_matadata

def image_name(metadata):
    parsed_meta = metadata
    split_pn = metadata[0].split(' ')
    name = ""
    for i in range(len(split_pn)):
        name += split_pn[i][0]
    year = parsed_meta[1]
    volume = parsed_meta[2]
    issue = parsed_meta[3]
    res_name = name+"_%s_%s_%s_" % (year, volume, issue)
    return res_name

def util_without_pagenum(input_folder, output_folder, page_count, lang_op, pdf_name, metadata):
    parsed_meta = parse_metadata(metadata)
    if len(parsed_meta[0]) == 0: image_name_prefix = ""
    else: image_name_prefix = image_name(parsed_meta)
    journal_info = os.path.splitext(os.path.basename(pdf_name))[0]
    journal_info = unidecode(journal_info).replace(' ', '_')

    # output_dir = create_folder(journal_info, output_folder)
    res_dir, csvfile_path, csvfile_pages_path = ut.create_result_dirs_and_files(journal_info, result_root=ut.RESULT_PATH_ON_PC)
    # res_dir = os.path.join(r"X:\Projekty\Matrix", res_dir)
    # csvfile_path = os.path.join(r"X:\Projekty\Matrix", csvfile_path)
    # csvfile_pages_path = os.path.join(r"X:\Projekty\Matrix", csvfile_pages_path)
    writer, f = ut.create_csv_writer(csvfile_path, ut.IMG_HEAD_CSV)
    p_writer, p_file = ut.create_csv_writer(csvfile_pages_path, ut.PAGE_HEAD_CSV)

    for i in range(page_count+1):
        file = input_folder + "/%d.png" % i
        boxes, p_h, p_w = getim.util(file, lang_op)
        page_num = i+1
        if len(boxes) > 0: #page contains images
            captions, degrees_to_rotate = cap.util(file, boxes, lang_op) 
            
            percentages, img_paths = vrs.get_versions(page_num, image_name_prefix, file, boxes, res_dir, degrees_to_rotate)
            for j in range(len(boxes)):
                entity = ut.create_entity("", page_num, j+1, captions[j], percentages[j], boxes[j], parsed_meta, 
                                        image_name_prefix, p_w, p_h, ut.language_formatting(lang_op),
                                        img_paths[j], "", "", "")
                # the last four 'img address', 'author', 'publisher', 'contributor'
                writer.writerow(entity)
        print(parsed_meta[0], parsed_meta[1], parsed_meta[2], parsed_meta[3], page_num)
        page_entity = ut.create_page_entity("", page_num, parsed_meta, p_w, p_h, ut.language_formatting(lang_op),
                                            file, "", "", "")
        p_writer.writerow(page_entity)
    f.close()
    p_file.close()




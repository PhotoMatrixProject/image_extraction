import os
import utility_funcs as ut
import alto_parser as ap
import numpy as np
import math
import image_mining_big as im 


def adjust_img_bbox(bbox:list[int], width_coeff:float, height_coeff:float)->list[int]:

    x = math.floor(bbox[0]*width_coeff)
    y = math.floor(bbox[1]*height_coeff) 
    w = math.ceil(bbox[2]*width_coeff)
    h = math.ceil(bbox[3]*height_coeff)

    return [x, y, w, h]

def adjust_bboxes(bboxes:list[list[int]], ocr_page_dims:list[int], phys_page_dims:list[int])->list[list[int]]:
    width_coeff = ocr_page_dims[0] / phys_page_dims[0] # phys to ocr
    height_coeff = ocr_page_dims[1] / phys_page_dims[1]

    # width_coeff = phys_page_dims[0] / ocr_page_dims[0] # ocr to phys
    # height_coeff = phys_page_dims[1] / ocr_page_dims[1]

    adjusted_bboxes = []
    for bbox in bboxes:
        new_bbox = adjust_img_bbox(bbox, width_coeff, height_coeff)
        adjusted_bboxes.append(new_bbox)

    return adjusted_bboxes

def change_format(bboxes:list[list[int]])->list[list[int]]:
    res_bboxes = []

    for bbox in bboxes:
        x1, y1, x2, y2 = bbox
        res_bboxes.append([x1, y1, x2-x1, y2-y1])
    return res_bboxes

def get_uuid(url:str)->str:
    '''Finds the first uuid in the given url'''
    split_page_url = url.split('/')
    uuid = [d for d in split_page_url if d.startswith('uuid:')]
    uuid_ = ""
    if len(uuid) != 0:
        uuid_ = uuid[0]
    return uuid_

def convert_img_url_to_best_img_url(url:str, dims:list[int])->str:
    uuid = get_uuid(url)
    ocr_img_url = "https://api.kramerius.mzk.cz/search/iiif/%s/full/%d,%d/0/default.jpg" % (uuid, dims[0], dims[1])

    if ut.is_img_request_ok(ocr_img_url):
        return ocr_img_url

    max_url = "https://api.kramerius.mzk.cz/search/iiif/%s/full/max/0/default.jpg" % (uuid)
    return max_url

def process_page_alto(alto_path:str, ocr_page_dims:list[int], phys_page_dims:list[int], img_path:str):
    # illustrations = ap.find_interesting_bboxes_in_alto(alto_path, ap.ILLUSTRATION_FLAG)

    width, height = ocr_page_dims
    phys_w, phys_h = phys_page_dims

    text_blocks = ap.find_interesting_bboxes_in_alto(alto_path, ap.TEXT_BLOCK_FLAG)

    img_boxes, _, _ = im.util(img_path, 'ces')
    img_boxes = change_format(img_boxes)
    adjusted_bboxes = adjust_bboxes(img_boxes, ocr_page_dims, phys_page_dims)

    imgs = []
    caps = []
    angles = []
    for i in range(len(adjusted_bboxes)):
        # ill = ap.get_element_coordinates(illustration)
        if ap.is_big_enough(adjusted_bboxes[i], width, height):
            text_blocks_dict = ap.match_bboxes_to_illustrations(adjusted_bboxes[i], text_blocks)
            caption, angle = ap.find_caption(adjusted_bboxes[i], text_blocks_dict, width, height)
            caps.append(caption)
            angles.append(angle)
            x, y, w, h = img_boxes[i]
            # ad_x, ad_y, ad_w, ad_h = adjust_img_bbox([x, y, w, h], ocr_page_dims, phys_page_dims)
            imgs.append([x, y, x+w, y+h])
    imgs, caps, angles = ap.delete_inscribed_bboxes(imgs, caps, angles)
    return imgs, caps, angles, phys_w, phys_h


def convert_page_url_to_alto_url(page_url:str)->str:
    split_page_url = page_url.split('/')
    uuid = [d for d in split_page_url if d.startswith('uuid:')]
    if len(uuid) != 1:
        return ""
    uuid_ = uuid[0]

    alto_url = "https://api.kramerius.mzk.cz/search/api/client/v7.0/items/%s/ocr/alto" % (uuid_)
    return alto_url

def utility(page_url:str, dir_for_alto:str, img_path:str)->tuple:
    alto_url = convert_page_url_to_alto_url(page_url)
    alto_path = os.path.join(dir_for_alto, "page_alto.xml")
    ut.download_alto_file(alto_url, alto_path)

    ocr_page_dims = ap.find_page_width_height(alto_path)
    ocr_img_url = convert_img_url_to_best_img_url(page_url, ocr_page_dims)

    success = ut.save_img(ocr_img_url, img_path)

    if not success: return success, [], [], [], 0, 0, '' # image cannot be saved, error
    phys_page_dims = ut.get_img_dims(img_path)

    if ocr_page_dims[0] == 0 or ocr_page_dims[1] == 0:
        return success, [], [], [], 0, 0, '' # page has no dimensions, process physical file
    
    imgs, caps, angles, w, h = process_page_alto(alto_path, ocr_page_dims, phys_page_dims, img_path)
    ut.delete_file(alto_path)
    return success, imgs, caps, angles, w, h, ocr_img_url


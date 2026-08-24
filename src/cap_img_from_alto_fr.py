import requests
import xml.etree.ElementTree as ET
import numpy as np
import utility_funcs as ut
import os
import alto_parser as ap



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

def get_second_identifier(page_url:str)->str:
    split_url = page_url.split('/')
    if len(split_url) > 3:
        return split_url[-3]
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


def get_highres_img_url(url:str, alto_path:str)->str:
    # "https://gallica.bnf.fr/services/ajax/pagination/page/SINGLE/ark:/12148/bpt6k9740716w/f17.item"
    # "https://gallica.bnf.fr/iiif/ark:/12148/bpt6k9740716w/f17/full/3956,5328/0/native.jpg"

    w, h = ap.find_page_width_height(alto_path)
    id1 = get_identifier(url)
    id2 = get_second_identifier(url)
    page_num = get_page_num(url)
    highres_url = "https://gallica.bnf.fr/iiif/ark:/%s/%s/f%s/full/%d,%d/0/native.jpg" % (id2, id1, page_num, w, h)
    return highres_url


def process_page_alto(alto_path:str)->tuple:
    # illustrations = ap.find_interesting_bboxes_in_alto(alto_path, ap.ILLUSTRATION_FLAG)
    illustrations = ap.find_illustrations(alto_path)
    text_blocks = ap.find_interesting_bboxes_in_alto(alto_path, ap.TEXT_BLOCK_FLAG)

    width, height = ap.find_page_width_height(alto_path)
    imgs = []
    caps = []
    angles = []
    for illustration in illustrations:
        ill = ap.get_element_coordinates(illustration)
        if ap.is_big_enough(ill, width, height):
            text_blocks_dict = ap.match_bboxes_to_illustrations(ill, text_blocks)
            caption, angle = ap.find_caption(ill, text_blocks_dict, width, height)
            caps.append(caption)
            angles.append(angle)
            x, y, w, h = ill
            imgs.append([x, y, x+w, y+h])
    imgs, caps, angles = ap.delete_inscribed_bboxes(imgs, caps, angles)
    return imgs, caps, angles, width, height

def get_low_quality_img_url(page_url:str)->str:
    id1 = get_identifier(page_url)
    id2 = get_second_identifier(page_url)
    page_num = get_page_num(page_url)

    img_url = "https://gallica.bnf.fr/ark:/%s/%s/f%s.highres" % (id2, id1, page_num)
    return img_url

def utility(page_url:str, dir_for_alto:str)->tuple:
    '''Receives page url, calls functions, which find img bboxes and captions.'''
    alto_url = convert_page_url_to_alto_url(page_url)
    alto_path = os.path.join(dir_for_alto, "page_alto.xml")

    response_ok = ut.download_alto_file(alto_url, alto_path)
    if not response_ok: 
        ut.delete_file(alto_path)
        return [], [], [], -1, -1, get_low_quality_img_url(page_url)
    highres_img_url = get_highres_img_url(page_url, alto_path)
    imgs, caps, angles, w, h = process_page_alto(alto_path)
    ut.delete_file(alto_path)
    return imgs, caps, angles, w, h, highres_img_url



import cv2
import pytesseract
from difflib import SequenceMatcher
import numpy as np

to_exclude = ["http://digi.ub.uni-heidelberg.de/diglit/cicerone",
              "Kunstbibliothek Staatliche Museen zu Berlin", 
              "http://digi.ub.uni-heidelberg.de/diglit/kfal922_1923/0051", 
              "UNIVERSITÄTS BIBLIOTHEK HEIDELBERG",
              "Universitätsbibliothek Heidelberg"]


def is_vertical(box):
    [x1, y1, x2, y2] = box
    if (x2-x1) < (y2-y1):
        if (x2-x1) > 0 and (y2-y1) / (x2-x1) > 1.5:
            return True
    return False

def rotate(im, degree):
    if degree == 90:
        return cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE)
    if degree == 270:
        return cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return im

def paint_images_white(page, boxes):
    for i in range(len(boxes)):
        cv2.rectangle(page, (max(0, boxes[i][0]), max(0, boxes[i][1])),
                    (min(page.shape[1], boxes[i][2]), min(page.shape[0], boxes[i][3])), (255, 255, 255), -1)
    return page

def preprocess_for_text_block_detection(page, im_boxes):
    # page = cv2.imread(file)
    gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
    threshold_rc,thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY| cv2.THRESH_OTSU)
    white_im = paint_images_white(thresh, im_boxes)
    return white_im

def read_text(box, im, lang_op, ker):
    dif = 20
    [x1, y1, x2, y2] = box
    text_area = im[max(0, y1-dif):min(y2+dif, im.shape[0]), max(0, x1-dif):min(x2+dif, im.shape[1])]
    text_area_preproc = preprocess_for_text_detection(text_area, ker)
    # cv2.imshow("text_area in read_text", text_area_preproc)
    # cv2.waitKey()
    # cv2.destroyAllWindows()
    data = pytesseract.image_to_data(text_area_preproc, config='--psm 11', lang=lang_op, output_type="dict")
    mean_conf = 0
    caption_word_count = 0
    data_text = data["text"]
    data_config = data["conf"]
    cap_text = ""
    for i in range(len(data_text)):
        if data_config[i] >= 0:
            cap_text = ' '.join([cap_text, data_text[i]])
            mean_conf += data_config[i]
            caption_word_count += 1

    if caption_word_count > 0 and mean_conf/caption_word_count <= 35:#25, 50
        return ""
    else:
        cap_text = cap_text.replace('\n', ' ')
        cap_text = cap_text.replace('- ', '')
        return cap_text

def morf(img):
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray,(9, 9),0)
        ret, thresh1 = cv2.threshold(blur, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY_INV) 
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (100, 100))#50#100
        dilation = cv2.dilate(thresh1, rect_kernel, iterations = 1) 
        contours, hierarchy = cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE) 
        text_blocks = []
        for cnt in contours: 
            x, y, w, h = cv2.boundingRect(cnt) 
            text_blocks.append([x, y, x+w, y+h])

        text_blocks = sorted(text_blocks, key = lambda block: (block[0], block[1]))
        return text_blocks
    except:
        return []

def read_caption_data(box, im, lang_op, degree, ker):
    cap_text = ""
    [x1, y1, x2, y2] = box
    dif = 30
    text_area = im[max(0, y1-dif):min(im.shape[0], y2+dif), 
                   max(0, x1-dif):min(im.shape[1], x2+dif)]
    # text_area = rotate(text_area, degree)
    # cv2.imshow("text_area", text_area)
    # cv2.waitKey()
    # cv2.destroyAllWindows()
    text_blocks = morf(text_area)

    for i in range(len(text_blocks)):
        block = read_text([text_blocks[i][0], text_blocks[i][1], text_blocks[i][2], text_blocks[i][3]], text_area, lang_op, ker)
        cap_text = ' '.join([cap_text, block])

    return cap_text.strip()

def cut_bottom_area(im, box):
    dif = 30
    x, y, w, h = max(0, box[0]-dif), max(0, box[1]-dif), min(im.shape[1], box[2]+dif), min(im.shape[0], box[3])
    if x == y == w == h == 0:
        return []
    bottom = im[h:im.shape[0], max(0, x):min(im.shape[1], w)]
    return bottom

def cut_top_area(im, box):
    dif = 30
    x, y, w, h = max(0, box[0]-dif), max(0, box[1]-dif), min(im.shape[1], box[2]+dif), min(im.shape[0], box[3]+dif)
    if x == y == w == h == 0:
        return []
    top = im[0:y, max(0, x):min(im.shape[1], w)]
    return top

def cut_right_area(im, box):
    dif = 30
    x, y, w, h = max(0, box[0]-dif), max(0, box[1]-dif), min(im.shape[1], box[2]+dif), min(im.shape[0], box[3]+dif)
    if x == y == w == h == 0:
        return []
    right  = im[max(0, y):h, w:im.shape[1]]
    return right

def cut_left_area(im, box):
    dif = 30
    x, y, w, h = max(0, box[0]-dif), max(0, box[1]-dif), min(im.shape[1], box[2]+dif), min(im.shape[0], box[3]+dif)
    if x == y == w == h == 0:
        return []
    left = im[max(0, y):h , 0:x]
    return left

def find_text_blocks(area, lang_op):
    data = pytesseract.image_to_data(area, output_type="dict", lang=lang_op, config='--psm 1')
    return (data["level"], data["left"], data["top"], data["width"], data["height"], data["conf"], data["text"])

def preprocess_for_text_detection(img, kernel_size = 9):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray,(kernel_size, kernel_size), 0)
    ret, thresh1 = cv2.threshold(blur, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY_INV) 
    thresh = cv2.bitwise_not(thresh1)
    return thresh

def is_text(img, box, lang_op, kernel_size):
    dif = 20
    x1, y1, x2, y2 = max(0, box[0]-dif), max(0, box[1]-dif), min(img.shape[1], box[2]+dif), min(img.shape[0], box[3]+dif)
    area = img[y1:y2, x1:x2]
    preproc = preprocess_for_text_detection(area, kernel_size)
    # cv2.imshow("check if is text preproc", preproc)
    # cv2.waitKey()
    # cv2.destroyAllWindows()
    data = pytesseract.image_to_data(preproc, config='--psm 11', lang=lang_op, output_type="dict")
    mean_conf = 0
    word_count = 0
    data_config = data["conf"]
    data_level = data['level']
    for i in range(len(data_config)):
        if data_level[i] == 5:
            # print(data["text"][i])
            mean_conf += data_config[i]
            word_count += 1

    mean_conf = mean_conf/word_count if word_count > 0 else 0
    # print(mean_conf)
    if mean_conf >= 50:#70, 67, 60, 55-works best
            return True
    return False

def is_text_util(img, box, lang_op):
    small_ker_flag = is_text(img, box, lang_op, 1)
    if small_ker_flag:
        return True, 1
    big_ker_flag = is_text(img, box, lang_op, 9)
    if big_ker_flag:
        return True, 9
    return False, 0

def get_caption_box(boxes):
    # cap_box =[boxes[0][0], boxes[0][1], boxes[0][2], boxes[0][3]]
    cap_box = boxes[0]
    if len(boxes) == 1: return cap_box
    cap_box[0] = min(box[0] for box in boxes)
    cap_box[1] = min(box[1] for box in boxes)
    cap_box[2] = max(box[2] for box in boxes)
    cap_box[3] = max(box[3] for box in boxes)
    return cap_box

def get_box_square(box):
    return (box[3]-box[1])*(box[2]-box[0])

def unite(boxes):
    for i in range(len(boxes)-1):
        if boxes[i+1][1] - boxes[i][3] > 30:#NOTE:change from 20
            return boxes
    return [get_caption_box(boxes)]

def delete_cap_box_from_boxes(res, boxes):
    res_boxes = [box for box in boxes if box not in res]
    return res_boxes

# def is_in_textcolumn(cap_box, sorted_boxes):
#     if len(sorted_boxes) <= 0:
#         return False
#     dif = 0
#     dif2 = 0
#     for i in range(len(sorted_boxes)):
#         dif += abs(sorted_boxes[i][2]-cap_box[2])
#         dif2 += abs(sorted_boxes[i][0]-cap_box[0]) 

#     dif /= len(sorted_boxes)
#     dif2 /= len(sorted_boxes)
#     if dif <= 10 and dif2 <= 10:
#         return True
#     return False

def is_in_textcolumn(cap_box, sorted_boxes):#TODO: determine how close vertically text blocks must be, to be in one column
    if len(sorted_boxes) <= 0:
        return False
    for i in range(len(sorted_boxes)):
        if (abs(sorted_boxes[i][2]-cap_box[2]) < 10 and abs(sorted_boxes[i][0]-cap_box[0]) < 10 
            and (abs(sorted_boxes[i][3]-cap_box[1]) < 30 or abs(sorted_boxes[i][1]-cap_box[3]) < 30)):
            return True
    return False

def is_too_high(max_height, box):
    if (max_height > 0 and (box[3]-box[1]) / max_height) > 0.5:
        return True
    return False

def is_too_wide(max_width, box):
    if (max_width > 0 and (box[2]-box[0]) / max_width) > 0.5:
        return True
    return False

def must_be_rotated(potential_cap_boxes):#TODO:change name
    vertical_boxes = [box for box in potential_cap_boxes if is_vertical(box)]
    if (len(vertical_boxes)/len(potential_cap_boxes)) > 0.5:
        return True
    return False

def filter_text_blocks(orig, x, y, w, h, level, lang_op):
    potential_cap_boxes = []
    ker_sum = 0
    ker = 1
    for i in range(len(x)):
        if (level[i] == 3 and 1_000 <= w[i]*h[i] and w[i] > 10 and h[i] > 10):
            text_flag, ker_size = is_text_util(orig, [x[i], y[i], x[i]+w[i], y[i]+h[i]], lang_op)
            ker_sum += ker_size
            if text_flag:
                potential_cap_boxes.append([x[i], y[i], x[i]+w[i], y[i]+h[i]])
                # cv2.rectangle(orig, (x[i], y[i]), (x[i]+w[i], y[i]+h[i]), (0, 0, 255), 10)
    ker = 9 if (len(potential_cap_boxes) > 0 and ker_sum/len(potential_cap_boxes) > 4.5) else 1
    return potential_cap_boxes, ker

def find_nearest_text_bottom(text_boxes, max_wid, max_hei):
    text_boxes = unite(text_boxes)
    sorted_boxes = sorted(text_boxes, key = lambda b: b[1])
    min_distance = 30
    res = [sorted_boxes[0]]
    for i in range(1, len(sorted_boxes)):
        if sorted_boxes[i][1] - sorted_boxes[0][3] <= min_distance:
            if (1_000 <= get_box_square(sorted_boxes[i]) <= max_wid*max_hei/5):
                res.append(sorted_boxes[i])

    if len(res) == 0:
        return res, -1
    else:
        sorted_boxes = delete_cap_box_from_boxes(res, sorted_boxes)
        cap_box = get_caption_box(res)
        close_text = sorted(sorted_boxes, key = lambda b: b[1])

        if get_box_square(cap_box) > max_wid*max_hei/4 and max_hei > 2_000:
            return [], -1
        elif len(sorted_boxes) > 0 and is_in_textcolumn(cap_box, sorted_boxes):
            return [], -1
        elif (cap_box[2]-cap_box[0])/(cap_box[3]-cap_box[1]) < 10 and get_box_square(cap_box) > max_wid*max_hei/5:#500_000
            return [], -1
        elif is_too_high(max_hei, cap_box) and max_hei > 2_000:#if small area, text can be big
            return [], -1
        elif len(close_text) > 0 and 3_000 < get_box_square(close_text[0])  and abs(close_text[0][1]-cap_box[3]) < min_distance*2/3:
            return [], -1
        elif cap_box[3]-cap_box[1] < 10:
            return [], -1
        else:
            '''
            if len(close_text) == 1 and (get_box_square(close_text[0])/get_box_square(cap_box)) < 1:
                if not ((get_box_square(cap_box) + get_box_square(close_text[0])) > max_wid*max_hei/4 and max_hei > 1_000):
                    sparse_cap_box = [cap_box, close_text[0]]
                    bigger_cap_box = get_caption_box(sparse_cap_box)
                    cap_box = bigger_cap_box
            return cap_box, cap_box[1]
            '''
            sparse_cap_boxes = []##test
            for cap_b in close_text:
                if (not ((get_box_square(cap_box) + get_box_square(cap_b)) > max_wid*max_hei/8 and max_hei > 1_000) and
                    (cap_b[2]-cap_b[0])/(cap_b[3]-cap_b[1]) > 5):#TODO:test const
                    sparse_cap_boxes.append(cap_b)
                else: 
                    sparse_cap_boxes = []#if there is a big block of text, then only cap_box
                    break
            sparse_cap_boxes.append(cap_box)
            bigger_cap_box = get_caption_box(sparse_cap_boxes)
            return bigger_cap_box, bigger_cap_box[1]


def work_with_bottom(origin, preproc, im_box, lang):
    b_origin = cut_bottom_area(origin, im_box)
    b_preproc = cut_bottom_area(preproc, im_box)
    if len(b_origin) == 0 or b_origin.shape[0]*b_origin.shape[1] == 0: return "", -1, 0
    level, x, y, width, height, conf, text = find_text_blocks(b_preproc, lang)
    potential_cap_boxes, ker = filter_text_blocks(b_origin, x, y, width, height, level, lang)
    # cv2.imshow("orig", b_origin)
    # cv2.waitKey()

    if len(potential_cap_boxes) > 0:
        cap_box, distance = find_nearest_text_bottom(potential_cap_boxes, b_origin.shape[1], b_origin.shape[0])
        if len(cap_box) > 0:
            caption = read_caption_data(cap_box, b_origin, lang, 0, ker)
            caption = " ".join(caption.strip().split())
            if (len(caption.split(' ')) > 30 or len(caption) == 0):
                return "", -1, 0
            return caption, distance, 0
        else: return "", -1, 0
    return "", -1, 0

def find_nearest_text_top(text_boxes, max_wid, max_hei):
    res = []
    sorted_boxes = sorted(text_boxes, key = lambda b: b[3], reverse=True)
    for i in range(0, len(sorted_boxes)):
        if sorted_boxes[0][1] - sorted_boxes[i][3] <= 30:
            if (1_000 <= get_box_square(sorted_boxes[i]) <= max_wid*max_hei/5):
                res.append(sorted_boxes[i])

    if len(res) == 0:
        return res, -1
    else:
        sorted_boxes = delete_cap_box_from_boxes(res, sorted_boxes)
        cap_box = get_caption_box(res)
        close_text = sorted(sorted_boxes, key = lambda b: b[3], reverse=True)

        if get_box_square(cap_box) > max_wid*max_hei/10:
            return [], -1
        elif len(sorted_boxes) > 0 and is_in_textcolumn(cap_box, sorted_boxes):
            return [], -1
        elif (cap_box[2]-cap_box[0])/(cap_box[3]-cap_box[1]) < 10 and (get_box_square(cap_box) > 500_000 and get_box_square(cap_box)/(max_hei*max_wid) > 0.1):
            return [], -1
        elif is_too_high(max_hei, cap_box) and max_hei > 2_000:
            return [], -1
        elif len(close_text) > 0 and cap_box[1] - close_text[0][3] < 30:
            return [], -1
        elif cap_box[3]-cap_box[1] < 10:
            return [], -1
        else:
            return cap_box, max_hei - cap_box[3]

def work_with_top(origin, preproc, im_box, lang):
    t_origin = cut_top_area(origin, im_box)
    t_preproc = cut_top_area(preproc, im_box)
    if len(t_origin) == 0 or t_origin.shape[0]*t_origin.shape[1] == 0: return "", -1, 0
    level, x, y, width, height, conf, text = find_text_blocks(t_preproc, lang)
    potential_cap_boxes, ker = filter_text_blocks(t_origin, x, y, width, height, level, lang)
    if len(potential_cap_boxes) > 0:
        cap_box, distance = find_nearest_text_top(potential_cap_boxes, t_origin.shape[1], t_origin.shape[0])
        if len(cap_box) > 0:
            caption = read_caption_data(cap_box, t_origin, lang, 0, ker)
            caption = " ".join(caption.strip().split())
            if (len(caption.split(' ')) > 30 or len(caption) == 0):
                return "", -1, 0
            return caption, distance, 0
        else: return "", -1, 0

    return "", -1, 0

def find_nearest_text_right(text_boxes, max_wid, max_hei):
    text_boxes = unite(text_boxes)
    sorted_boxes = sorted(text_boxes, key = lambda b: b[0])
    res = [sorted_boxes[0]]
    j = 0
    for i in range(1, len(sorted_boxes)):
        if max(sorted_boxes[j][1], sorted_boxes[i][1]) - min(sorted_boxes[j][3], sorted_boxes[i][3]) <= 30:
            if (1_000 <= get_box_square(sorted_boxes[i]) <= max_wid*max_hei/2):
                res.append(sorted_boxes[i])
                j = i

    if len(res) == 0:
        return res, -1
    else:
        min_distance = 30
        min_height = 15
        min_width = 15
        cap_box = get_caption_box(res)
        if get_box_square(cap_box) > max_wid*max_hei/2:
            return [], -1

        if is_too_high(max_hei, cap_box):
            return [], -1

        sorted_boxes = delete_cap_box_from_boxes(res, sorted_boxes)
        if len(sorted_boxes) > 0 and is_in_textcolumn(cap_box, sorted_boxes):
            return [], -1

        close_text_up = sorted([box for box in sorted_boxes if box[1] <= cap_box[1]], key = lambda b: b[3], reverse=True)
        close_text_down = sorted([box for box in sorted_boxes if box[3] >= cap_box[3]], key = lambda b: b[1])

        if len(close_text_up) > 0 and cap_box[1] - close_text_up[0][3] < min_distance:
            return [], -1
        elif len(close_text_down) > 0 and close_text_down[0][1] - cap_box[3] < min_distance:
            return [], -1
        elif cap_box[3]-cap_box[1] < min_height:
            return [], -1
        elif cap_box[2]-cap_box[0] < min_width:
            return [], -1
        else:
            return cap_box, cap_box[0]

def work_with_right(origin, preproc, im_box, lang):
    r_origin = cut_right_area(origin, im_box)
    r_preproc = cut_right_area(preproc, im_box)
    if len(r_origin) == 0 or r_origin.shape[0]*r_origin.shape[1] == 0: return "", -1, 0
    caption = ""
    distance = -1
    angle = 0
    level, x, y, width, height, conf, text = find_text_blocks(r_preproc, lang)
    potential_cap_boxes, ker = filter_text_blocks(r_origin, x, y, width, height, level, lang)
    if len(potential_cap_boxes) > 0:
        cap_box, distance = find_nearest_text_right(potential_cap_boxes, r_origin.shape[1], r_origin.shape[0])
        if len(cap_box) > 0:
            caption = read_caption_data(cap_box, r_origin, lang, 0, ker)
    # cv2.imshow("before rotating orig", r_origin )
    # cv2.waitKey()

    if len(caption) == 0 or must_be_rotated(potential_cap_boxes):
        rotated_r_origin = rotate(r_origin, 90)
        rotated_r_preproc = rotate(r_preproc, 90)
        level, x, y, width, height, conf, text = find_text_blocks(rotated_r_preproc, lang)
        potential_cap_boxes, ker = filter_text_blocks(rotated_r_origin, x, y, width, height, level, lang)
        if len(potential_cap_boxes) > 0:
            cap_box, distance = find_nearest_text_bottom(potential_cap_boxes, rotated_r_origin.shape[1], rotated_r_origin.shape[0])
            if len(cap_box) > 0:
                caption = read_caption_data(cap_box, rotated_r_origin, lang, 0, ker)
                angle = 90 if len(caption) > 0 else 0
        # cv2.imshow("after rotating orig", rotated_r_origin )
        # cv2.waitKey()
    caption = " ".join(caption.strip().split())
    if (len(caption.split(' ')) > 30 or len(caption) == 0):
        return "", -1, 0
    return caption, distance, angle

def find_nearest_text_left(text_boxes, max_wid, max_hei):
    sorted_boxes = sorted(text_boxes, key = lambda b: b[2], reverse=True)
    res = []
    for i in range(len(sorted_boxes)):
        if max(sorted_boxes[0][1], sorted_boxes[i][1]) - min(sorted_boxes[0][3], sorted_boxes[i][3]) <= 30:
            if (1_000 <= get_box_square(sorted_boxes[i]) <= max_wid*max_hei/2):
                res.append(sorted_boxes[i])

    if len(res) == 0:
        return res, -1
    else:
        min_distance = 30
        min_height = 15
        min_width = 15
        cap_box = get_caption_box(res)

        if get_box_square(cap_box) > (max_wid/2)*max_hei:
            return [], -1
        if is_too_high(max_hei, cap_box):#cap_box[2]-cap_box[0] > 150
            return [], -1
        sorted_boxes = delete_cap_box_from_boxes(res, sorted_boxes)
        if len(sorted_boxes) > 0 and is_in_textcolumn(cap_box, sorted_boxes):
            return [], -1

        close_text_up = sorted([box for box in sorted_boxes if box[1] <= cap_box[1]], key = lambda b: b[3], reverse=True)
        close_text_down = sorted([box for box in sorted_boxes if box[3] >= cap_box[3]], key = lambda b: b[1])

        if len(close_text_up) > 0 and cap_box[1] - close_text_up[0][3] < min_distance:
            return [], -1
        elif len(close_text_down) > 0 and close_text_down[0][1]- cap_box[3] < min_distance:
            return [], -1
        elif cap_box[3]-cap_box[1] < min_height:
            return [], -1
        elif cap_box[2]-cap_box[0] < min_width:
            return [], -1
        else:
            return cap_box, max_wid - cap_box[2]

def work_with_left(origin, preproc, im_box, lang):
    l_origin = cut_left_area(origin, im_box)
    l_preproc = cut_left_area(preproc, im_box)
    if len(l_origin) == 0 or l_origin.shape[0]*l_origin.shape[1] == 0: return "", -1, 0
    caption = ""
    distance = -1
    angle = 0
    level, x, y, width, height, conf, text = find_text_blocks(l_preproc, lang)
    potential_cap_boxes, ker = filter_text_blocks(l_origin, x, y, width, height, level, lang)
    if len(potential_cap_boxes) > 0:
        cap_box, distance = find_nearest_text_left(potential_cap_boxes, l_origin.shape[1], l_origin.shape[0])
        if len(cap_box) > 0:
            caption = read_caption_data(cap_box, l_origin, lang, 0, ker)

    if len(caption) == 0 or must_be_rotated(potential_cap_boxes):
        rotated_l_origin = rotate(l_origin, 270)
        rotated_l_preproc = rotate(l_preproc, 270)
        level, x, y, width, height, conf, text = find_text_blocks(rotated_l_preproc, lang)
        potential_cap_boxes, ker = filter_text_blocks(rotated_l_origin, x, y, width, height, level, lang)
        if len(potential_cap_boxes) > 0:
            cap_box, distance = find_nearest_text_bottom(potential_cap_boxes, rotated_l_origin.shape[1], rotated_l_origin.shape[0])
            if len(cap_box) > 0:
                caption = read_caption_data(cap_box, rotated_l_origin, lang, 0, ker)
                angle = 270 if len(caption) > 0 else 0
    caption = " ".join(caption.strip().split())
    if (len(caption.split(' ')) > 30 or len(caption) == 0):
        return "", -1, 0
    return caption, distance, angle

def fix_multiple_captions(cd:list[tuple])->str:
    not_empty_cap = [cap[0] for cap in cd if len(cap[0]) > 0]

    if (len(not_empty_cap) == 0): return ""
    if (len(not_empty_cap) == 1): return not_empty_cap[0]
    if (len(cd[2][0]) > 0 and len(cd[3][0]) > 0): #caption is on both sides left and right
        if (cd[2][1] > 0 and cd[3][1] > 0 and 
            max(cd[2][1], cd[3][1]) / min(cd[2][1], cd[3][1]) < 2):
            return f"{cd[2][0]} {cd[3][0]}"
    if (len(cd[0][0]) > 0 and len(cd[2][0]) > 0): #something was found on the rigth and below, the closest to the image will be returned
        if (cd[0][1] > 0 and cd[2][1] > 0) and max(cd[0][1], cd[2][1]) / min(cd[0][1], cd[2][1]) <= 2:
            return f"{cd[0][0]} {cd[2][0]}"
        return cd[0][0] if cd[0][1] < cd[2][1] else cd[2][0]
    if (len(cd[0][0]) > 0 and len(cd[3][0]) > 0):#something was found on the left and below, the closest to the image will be returned
        if (cd[0][1] > 0 and cd[3][1] > 0) and max(cd[0][1], cd[3][1]) / min(cd[0][1], cd[3][1]) <= 2:
            return f"{cd[0][0]} {cd[3][0]}"
        return cd[0][0] if cd[0][1] < cd[3][1] else cd[3][0]
    if (len(cd[0][0]) > 0 and len(cd[1][0]) > 0):#something was found below and under the image, below will be returned or both
        if (cd[0][1] > 0 and cd[1][1] > 0 and
            max(cd[0][1], cd[1][1]) / min(cd[0][1], cd[1][1]) < 3
            and len(cd[1][0]) < 50):
            return f"{cd[0][0]} {cd[1][0]}"
        else: return cd[0][0]

    cap = ""
    for i in range(len(not_empty_cap)):
        cap = ' '.join([cap, not_empty_cap[i]])
    return cap.strip()

def has_exclude_exps(caption):
    for i in range(len(to_exclude)):
        if SequenceMatcher(None, caption, to_exclude[i]).ratio() > 0.5:
            return True
    return False

def work_with_image(origin, preproc, im_box, lang):
    res_caption = ""
    angle_to_rotate = 0
    cap_dist_pair = []
    caption_b, distance_b, _ = work_with_bottom(origin, preproc, im_box, lang)
    if caption_b.isnumeric(): caption_b, distance_b = "", -1
    if has_exclude_exps(caption_b): caption_b, distance_b = "", -1
    cap_dist_pair.append((caption_b, distance_b))

    caption_t, distance_t, _ = work_with_top(origin, preproc, im_box, lang)
    if caption_t.isnumeric(): caption_t, distance_t = "", -1
    if has_exclude_exps(caption_t): caption_t, distance_t = "", -1
    cap_dist_pair.append((caption_t, distance_t))

    caption_r, distance_r, angle_to_rotate_r = work_with_right(origin, preproc, im_box, lang)
    if caption_r.isnumeric(): caption_r, distance_r = "", -1
    if has_exclude_exps(caption_r): caption_r, distance_r = "", -1
    cap_dist_pair.append((caption_r, distance_r))

    caption_l, distance_l, angle_to_rotate_l = work_with_left(origin, preproc, im_box, lang)
    if caption_l.isnumeric(): caption_l, distance_l = "", -1
    if has_exclude_exps(caption_l): caption_l, distance_l = "", -1
    cap_dist_pair.append((caption_l, distance_l))

    if len(caption_b) < 5 and len(caption_t) < 5:
        if angle_to_rotate_l > 0 and len(caption_l) > 0 and len(caption_r) == 0:
            return caption_l, angle_to_rotate_l
        if angle_to_rotate_r > 0 and len(caption_r) > 0 and len(caption_l) == 0:
            return caption_r, angle_to_rotate_r
    res_caption = fix_multiple_captions(cap_dist_pair)
    return res_caption, angle_to_rotate

def util(file, im_boxes, lang):
    res_caps = []
    res_angles = []
    for j in range(len(im_boxes)):
        res_caps.append("")
        res_angles.append(0)
    try:
        origin = cv2.imread(file)
        preproc = preprocess_for_text_block_detection(origin, im_boxes)

        for i in range(len(im_boxes)):
            cap, angle = work_with_image(origin, preproc, im_boxes[i], lang)
            res_caps[i] = cap if len(cap) <= 1000 else cap[:1000]
            res_angles[i] = angle
        return res_caps, res_angles
    except Exception:
        # print("Exception", file)
        return res_caps, res_angles
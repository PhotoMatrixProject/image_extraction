import os
import cv2
import numpy as np
import pytesseract


# MAX_SIZE = 32767

def preprocess_for_text(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) 
    blur = cv2.GaussianBlur(gray,(9, 9),0)
    ret, thresh1 = cv2.threshold(blur, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY_INV) 
    thresh = cv2.bitwise_not(thresh1)
    # cv2.imshow("preproc for text detection", thresh)
    # cv2.waitKey()
    return thresh

def is_text(img, box, lang_op):
    [x1, y1, x2, y2] = box
    area = img[y1:y2, x1:x2]
    preproc = preprocess_for_text(area)

    data = pytesseract.image_to_data(preproc, config='--psm 11', lang=lang_op, output_type="dict")
    mean_conf = 0
    word_count = 0
    data_text = data["text"]
    data_config = data["conf"]
    data_level = data['level']
    width = data['width']
    height = data['height']
    text_area = 0
    for i in range(len(data_text)):
        if data_level[i] == 5:
            text_area += (width[i]*height[i])
            mean_conf += data_config[i]
            word_count += 1
    #         cv2.rectangle(area, (data['left'][i], data['top'][i]), (data['left'][i]+data['width'][i], data['top'][i]+data['height'][i]), (0, 0, 255), 5)
    # cv2.imshow('text', area)
    # cv2.waitKey()

    mean_conf = mean_conf/word_count if word_count > 0 else 0
    # print(mean_conf)
    if mean_conf >= 60:#75, 80
        if 0.1 <= (text_area/((x2-x1)*(y2-y1))) <= 1: #if it is text, than it is never greater than 1
            return True
    return False

def filter_text(img, boxes, lang):
    images = []
    for i in range(len(boxes)):
        if is_text(img, boxes[i], lang):
            continue
        images.append(boxes[i])
    return images

def filter_size(imW, imH, boxes):
    images = []
    for i in range(len(boxes)):
        if (boxes[i][2]-boxes[i][0])*(boxes[i][3]-boxes[i][1]) <= (imW*0.075)*(imH*0.075):
            continue
        if (boxes[i][2]-boxes[i][0])*(boxes[i][3]-boxes[i][1]) >= (imW*0.97)*(imH*0.97):#(imW*0.95)*(imH*0.95)
            continue
        images.append(boxes[i])
    return images

def filter_borders(imW, imH, boxes):
    images = []
    for i in range(len(boxes)):
        if ((boxes[i][3]-boxes[i][1]) > 0 
            and (boxes[i][2]-boxes[i][0])/(boxes[i][3]-boxes[i][1]) > 8):#horizontal
            if (is_on_edge(imW, imH, boxes[i])):
                continue
            else:
                images.append(boxes[i])
                continue
        elif ((boxes[i][2]-boxes[i][0]) > 0
              and (boxes[i][3]-boxes[i][1])/(boxes[i][2]-boxes[i][0])) > 8:#vertical
            if (is_on_edge(imW, imH, boxes[i])):
                continue
            else:
                images.append(boxes[i])
                continue
        else:
            images.append(boxes[i])
    return images

def filter_stripes(boxes):
    images = []
    for i in range(len(boxes)):
        if ((boxes[i][3]-boxes[i][1]) > 0 
            and (boxes[i][2]-boxes[i][0])/(boxes[i][3]-boxes[i][1]) > 8):#horizontal
            continue

        elif ((boxes[i][2]-boxes[i][0]) > 0
              and (boxes[i][3]-boxes[i][1])/(boxes[i][2]-boxes[i][0])) > 8:#vertical
            continue
        else:
            images.append(boxes[i])
    return images

def is_on_edge(imW, imH, box):
    border = 0.1
    [x1, y1, x2, y2] = box
    b1 = border * imH
    b2 = border * imW
    b3 = (1-border) * imH
    b4 = (1-border) * imW

    if x2 <= b2: return True
    if x1 <= b2/2 and x2 <= 3*b2/2: return True
    if y1 >= b3: return True
    if y2 >= (imH+b3)/2 and y1 >= (3*b3-imH)/2: return True
    if x1 >= b4: return True
    if x2 >= (imW+b4)/2 and x1 >= (3*b4-imW)/2: return True
    if y2 <= b1: return True
    if y1 <= b1/2 and y2 <= 3*b1/2: return True
    return False

def filter_edges(imW, imH, boxes):
    images = []
    for i in range(len(boxes)):
        if is_on_edge(imW, imH, boxes[i]): continue
        else: images.append(boxes[i])
    return images

def get_image_std(page, box):
    [x1, y1, x2, y2] = box
    area = page[y1:y2, x1:x2]
    img_gray = cv2.cvtColor(area, cv2.COLOR_RGB2GRAY)
    contrast = img_gray.std()
    return contrast

def filter_monotone(img, boxes):
    images = []
    for b in boxes:
        if get_image_std(img, b) > 8:
            images.append(b)

    return images

def process_image(source, lang, img_ind, size=0.93):
    # window_name = os.path.splitext(os.path.basename(source))[0]
    # source = cv2.imread(filename)
    if source is None:
        return []
    # print("size", size)
    contrast_image = preprocess_image(source, img_ind)#change_contrast(source) #cv2.imread(filename)
    # cv2.imwrite("contrast"+img_ind+".png", contrast_image)
    source_gray = contrast_image
    # cv2.imshow("source_gray ", source_gray )
    # cv2.waitKey()
    threshold_rc, threshold_image = cv2.threshold(source_gray, 0, 255, cv2.THRESH_BINARY|cv2.THRESH_OTSU)
    # cv2.imwrite("threshold"+img_ind+".png", threshold_image)
    # threshold_rc, threshold_image = cv2.threshold(source_gray, 40, 255, cv2.THRESH_BINARY)
    # cv2.imshow("threshold_image", threshold_image)
    # cv2.waitKey()
    output_image = cv2.bitwise_not(threshold_image)
    # cv2.imwrite("bitwise_not"+img_ind+".png", output_image)
    # cv2.imshow("output_base_image", output_image)
    # cv2.waitKey()

    contours, hierarchy = cv2.findContours(output_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    min_area_pct = 0.000001#0.000001
    min_area = min_area_pct * source.size

    max_height = int(round(size * source.shape[0]))
    max_width = int(round(size * source.shape[1]))
    min_height = int(round(0.1 * source.shape[0]))
    min_width = int(round(0.1 * source.shape[1]))

    l = []
    src_for_cnts = source.copy()
    img = src_for_cnts
    for i, contour in enumerate(contours):
        length = cv2.arcLength(contours[i], False)
        area = cv2.contourArea(contours[i], False)

        if area < min_area:
            continue
        # canny_output = cv2.Canny(src_gray, threshold, threshold * 2)
        poly = cv2.approxPolyDP(contour, 0.01 * cv2.arcLength(contour, False), False)
        x, y, w, h = cv2.boundingRect(poly)
        bbox = ((x, y), (x + w, y + h))

        minimum_area = 1_000#1000
        if w >= max_width or h >= max_height or w*h < minimum_area:
            continue

        if w*h >= 2_000:#2100:
            img = cv2.drawContours(src_for_cnts, contour, -1, (100,200,0), 3)
            img = cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 255), 5)
        else:
            continue

        l.append([x, y, x + w, y + h])

    found_ims = []
    # cv2.imwrite("contours"+img_ind+".png", img)
    # cv2.imshow("contours", img)
    # cv2.waitKey()
    if len(l) != 0:
        b = detect_overlap(l, src_for_cnts, 90_000, img_ind)
        for i in range(len(b)):
            x, y, w, h = b[i][0], b[i][1], b[i][2]-b[i][0], b[i][3]-b[i][1]
            found_ims.append([x, y, w+x, h+y])

    found_ims = filter_borders(source.shape[1], source.shape[0], found_ims)
    found_ims = filter_size(source.shape[1], source.shape[0], found_ims)
    found_ims = filter_edges(source.shape[1], source.shape[0], found_ims)
    found_ims = filter_stripes(found_ims)
    found_ims = filter_text(source, found_ims, lang)
    found_ims = filter_monotone(source, found_ims)
    # output_dir = r".\app_EXIM"
    # for i in range(len(found_ims)):
    #     x, y, w, h = found_ims[i][0], found_ims[i][1], found_ims[i][2]-found_ims[i][0], found_ims[i][3]-found_ims[i][1]
    #     extracted = source[y:y + h, x:x + w]
    #     cv2.imwrite(os.path.join(output_dir, "%s_%d.jpeg" % (img_ind, i)), extracted)
        # cv2.imshow("res_fin", extracted)
        # cv2.waitKey()
    return found_ims

def preprocess_image(image, img_ind):
    preprocessed = equist_and_contrast(image, img_ind)#change_contrast(image)
    return preprocessed

def equist_and_contrast(image, img_ind):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # cv2.imwrite("grayscale"+img_ind+".png", gray)
    equ = cv2.equalizeHist(gray)
    alpha = compute_alpha_hist(image)
    beta = 10
    adjusted = cv2.convertScaleAbs(equ, alpha=alpha, beta=beta)
    return adjusted

def compute_alpha_hist(image):
    minimum, maximum, dif = detect_contrast_level(image)
    # print(minimum, dif)
    if minimum >= 230:
        if dif <= 15: return 2.5
        return 1
    if minimum >= 220:
        if dif < 5: return 2.#wasnt there, 1-2
        if dif <= 10: return 2.
        elif dif < 15: return 2.5
        elif dif < 20: return 3.5
        elif dif < 35: return 2.
        else: return 3.5
    if minimum >= 210:
        if dif <= 3: return 1.6#wasnt there
        elif dif < 5: return 1#1
        elif dif <= 7: return 1.6
        elif dif <= 10: return 1.4 + (minimum - 210)*0.1#3, 2.6, 4, 3, 1 is for 216 and 9
        elif dif <= 15: return 2.# 3.5, 2
        elif dif <= 20: return 2.5#2, 2.5
        elif dif <= 30: return 3
        else: return 1
    if minimum >= 200:
        if dif <= 10: return 1.9 + (minimum - 200)*.1#2, 1.5 for 209, for 201 and 8: - 2.1 - (minimum - 200)*.1
        elif dif < 15: return 3#2.5, 3
        elif dif < 20: return 3.2#2.5, 3.2, 2 - is for 19
        elif dif < 25: return 3.5 - (minimum-200)*0.15#3.5
        else: return 4.5
    if minimum >= 190:
        if dif <= 5: return 2.5
        if dif <= 7: return 1. + (minimum - 190)*.1#1.5
        if dif <= 8: return 1.8#1.5 can be removed, 2
        elif dif <= 10: return 1.8 + (minimum - 190)*.1#2
        elif dif <= 13: return 2.5#196, 2.5
        elif dif <= 17: return 1.9 #wasnt there
        elif dif < 20: return 1.4#1.5, 1.4
        elif dif < 25: return 2+(minimum - 190)*0.1#1.5, 2
        elif dif <= 27: return 3-(minimum-190)*0.1# 3
        elif dif < 30: return 1
        else: return 2.5
    if minimum >= 180:
        if dif <= 5: return 2 #wasnt there
        if dif <= 8: return 2.6 - (minimum-180)*0.1 # 1.5, 2.5
        if dif <= 10: return 4
        if dif <= 11: return 1.8#1.8
        elif dif < 15: return 2.1#2, 2.1
        elif dif < 25: return 2.#wasnt there
        elif dif < 30: return 2.3#3, 2.8
        else: return 3
    if minimum >= 170:
        if dif <= 7: return 1.5#1.5
        if dif < 10: return 1.
        if dif <= 12: return 3
        elif dif <= 16: return 1.7#2
        elif dif <= 17: return 1.5#for 176
        elif dif <= 18: return 3#wasnt there
        elif dif <= 21: return 1. + (minimum-170)*0.1#1.
        elif dif <= 25: return 2#1.5, 1.6, 2-3
        elif dif < 30: return 2.2#2
        elif dif < 35: return 2.5
        else: return 2.6 #3, 2.7 is for 170
    if minimum >= 160:
        if dif <= 8: return 2#wasnt there
        if dif <= 11: return 1.6#2, 1.6
        elif dif <= 12: return 4 #11, 4 for 12
        elif dif < 15: return 2.7#1.5, 1, 1.7, 3 is for 166 and 14, 2.5
        elif dif <= 20: return 2.5#2.5, 1., 2.5 is for 167
        elif dif <= 25: return 1.5 + (minimum - 160)*0.1#wasnt there, 1.5
        elif dif < 30: return 2.5
        elif dif <= 35: return 1.5
        elif dif < 45: return 2 #40
        elif dif < 65: return 2
        else: return 1
    if minimum >= 150:
        if dif <= 10: return 2
        elif 10 < dif <= 15: return 1.5#1.5
        elif 15 < dif < 20: return 2.5#1, 1.5, 3, 2.5
        elif 20 <= dif <= 25: return 2.#1, 5, 1.5
        elif 25 < dif < 30: return 1#1
        elif 30 <= dif < 35: return 2.5
        elif 35 <= dif < 40: return 1.9 + (minimum - 150)*0.1#2, 1.9, 2.5, 3.2 is for dif=39
        elif 40 <= dif < 45: return 1.7#1.5
        elif 45 <= dif < 50: return 2
        else: return 2.5
    if minimum >= 140:
        if dif <= 10: return 1.3 + (minimum - 140)*.1#1.5, 1.3
        if dif <= 12: return 1.1
        if dif < 15: return 1.5 + (minimum - 140)*0.1#2
        if dif < 20: return 2.#2.5
        elif dif <= 27: return 1.7#wasnt there
        elif dif <= 30: return 1. + (minimum-140)*0.1#1.2
        elif dif <= 35: return 1.5#wasnt there
        elif dif <= 40: return 1.#1.
        elif dif <= 45: return 2.2 - (minimum-140)*.1#1., 2, 1.9
        elif dif <= 50: return 1.6#wasnt there, 1.5
        else: return 2
    if minimum >= 130:
        if dif <= 10: return 1.5
        elif dif <= 15: return 2.5
        if dif <= 30: return 2#1.5, 1.4, 2 is for dif=29
        elif dif <= 45: return 1.35#wasnt there
        return 2
    if minimum >= 120:
        if dif <= 25: return 2
        elif 25 < dif <= 45: return 1.2 #1, 1.2 for 120 and 37
        else: return 1.8#1.5
    elif minimum >= 110:
        if dif < 20: return 1
        else: return 2.#2.5
    elif minimum >= 100:
        # if dif < 15: return 1.0
        return 1
    elif minimum >= 90:
        if dif < 30: return 1.
        return 2
    return 1

def change_contrast(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    output_base_image = cv2.bitwise_not(gray)
    alpha = compute_alpha(image)
    # print(alpha)
    beta = 10
    adjusted = cv2.convertScaleAbs(output_base_image, alpha=alpha, beta=beta)
    return adjusted

def delete_on_edges(boxes, h, w):
    res_boxes = []
    for b in boxes:
        if b[0] <= 5 and b[1] <= 5 and (b[2] < w/2 or b[3] < h/2): continue
        if b[2] >= (w-5) and b[3] >= (h-5) and (b[0] > w/2 or b[1] > h/2): continue
        if b[2] >= (w-5) and b[1] <= 5 and (b[0] > w/2 or b[3] < h/2): continue
        if b[0] <= 5 and b[3] >= (h-5) and (b[2] < w/2 or b[1] > h/2): continue
        res_boxes.append(b)
    return res_boxes

def detect_overlap(list_of_boxes, im, size, img_ind):
    h, w, _ = im.shape
    list_of_boxes = delete_on_edges(list_of_boxes, h, w)
    l0 = sorted(list_of_boxes, key = lambda b: (b[2]-b[0])*(b[3]-b[1]))
    res_boxes =[]

    if len(l0) > 0:
        biggest = (l0[len(l0)-1][2] - l0[len(l0)-1][0])*(l0[len(l0)-1][3] - l0[len(l0)-1][1])
        res = l0[len(l0)-1]
        while(biggest > size):
                l, res = find_overlap(l0, res)
                while len(l) != len(l0):
                    l0 = l
                    l, res = find_overlap(l0, res)
                    cv2.rectangle(im, (res[0], res[1]), (res[2], res[3]), (0, 0, 255), 10)
                    # cv2.imshow("res", im)
                    # cv2.waitKey()
                    # cv2.imwrite("res_contours"+img_ind+".png", im)
                res_boxes.append(res)

                if len(l0) > 0:
                     biggest = (l0[len(l0)-1][2] - l0[len(l0)-1][0])*(l0[len(l0)-1][3] - l0[len(l0)-1][1])
                     res = l0[len(l0)-1]
                else:
                    break
    return res_boxes

def find_overlap(l1, box):
    l2 = []
    for i in range(len(l1)):
        if isOverlap(box, l1[i]):
            box = [min(box[0], l1[i][0]),
                    min(box[1], l1[i][1]),
                    max(box[2], l1[i][2]),
                    max(box[3], l1[i][3])]
        else:
            l2.append(l1[i])
    return l2, box

def isOverlap(box1, box2):
    l1x = box1[0]
    l1y = box1[1]
    r1x = box1[2]
    r1y = box1[3] 
    l2x = box2[0]
    l2y = box2[1]
    r2x = box2[2]
    r2y = box2[3] 
    if l1x > r2x or l2x > r1x:
        return False
    if r1y < l2y or r2y < l1y:
        return False
    return True 

def detect_contrast_level(img):
    lab = cv2.cvtColor(img,cv2.COLOR_BGR2LAB)
    L,A,B=cv2.split(lab)

    kernel = np.ones((5,5),np.uint8)
    minimum = cv2.erode(L,kernel,iterations = 1)
    maximum = cv2.dilate(L,kernel,iterations = 1)

    minimum = minimum.astype(np.float64) 
    maximum = maximum.astype(np.float64) 

    return np.mean(minimum), np.mean(maximum), round(np.mean(maximum) - np.mean(minimum))

def compute_alpha(image):
    minimum, maximum, dif = detect_contrast_level(image)
    print(minimum, maximum, dif)
    if minimum < 140: return 1.5
    if maximum < 160: return 1.5
    if minimum < 170:
        if dif >= 40: return 2.4
        elif dif > 20: return 2 + (dif - 25)*0.1
        elif dif > 10: return 2.5
        else: return 1.5
    if minimum < 180:
        if dif > 40: return 3
        if dif >= 25: return 2 + 0.4 - (dif - 25)*0.1
        elif dif >= 20: return 2 + 0.5 - (dif-20)*0.1#2.5#2#3
        else: return 2.5
    if 180 < minimum < 190:
        if dif > 20: return 3
        elif dif < 10: return 3.5#+(10-dif)*0.5#3.5
        else: return 1.5+((dif/20)*1.1)#1.5, 2.5
    if 190 <= minimum <= 200:
        if dif > 20: return 2.5 + (maximum-200)/55
        elif dif < 10: return 3.5-(minimum-190)*0.1#3+(0.5 - dif/20)#3.5#+(0.5 - (dif/10)*0.5)#3.5+((dif/10)*0.5)
        else: return 3 + (((dif-10)/10)*0.5)#2.6+, 3+
    if 200 < minimum <= 210:
        if dif > 20: return 3.5
        if dif >= 10: return 3 #+ (dif - 10)*0.5 #3#3.5
        elif dif > 7: return 3.5#2.5 #+ (0.5 - (dif/10)*0.5)#3 + ((dif/10)*0.5)#
        else: return 3-(minimum-200)*0.1#3
    if minimum > 210:
        if dif < 5: return 3.4
        else: return 2.7#3
    return 1

def compute_alpha_not_used(image):
    minimum, maximum, dif = detect_contrast_level(image)
    print(minimum, maximum, dif)
    if minimum < 140: return 1.5
    if maximum < 155: return 1.5
    if minimum < 160: return 2
    if minimum < 170:
        if dif >= 40: return 2.4
        elif dif > 20: return 2 + (dif - 25)*0.1
        elif dif > 10: return 2.5
        else: return 2
    if minimum < 180:
        if dif > 40: return 3
        if dif >= 25: return 2 + 0.4 - (dif - 25)*0.1
        elif dif >= 20: return 2 + 0.5 - (dif-20)*0.1#2.5#2#3
        else: return 2.5
    if 180 < minimum < 190:
        if dif > 20: return 3
        elif dif < 10: return 3.5#+(10-dif)*0.5#3.5
        else: return 2.5+((dif/20)*1.1)#1.5
    if 190 <= minimum <= 200:
        if dif > 20: return 2.5 + (maximum-200)/55
        elif dif < 10: return 3+(0.5 - dif/20)#3.5#+(0.5 - (dif/10)*0.5)#3.5+((dif/10)*0.5)
        else: return 3 + (((dif-10)/10)*0.5)#2.6+, 3+
    if 200 < minimum <= 210:
        if dif > 20: return 3.5
        if dif >= 10: return 3 #+ (dif - 10)*0.5 #3#3.5
        elif dif > 7: return 3.5#2.5 #+ (0.5 - (dif/10)*0.5)#3 + ((dif/10)*0.5)#
        else: return 3
    if minimum > 210:
        if dif < 5: return 3.4
        else: return 3
    return 1

def fix_image_boxes(im_boxes, x1, y1):
    for box in im_boxes:
        box[0]+=x1
        box[1]+=y1
        box[2]+=x1
        box[3]+=y1
    return

def detect_border(source):
    contrast_image = change_contrast(source)
    source_gray = contrast_image
    threshold_rc, threshold_image = cv2.threshold(source_gray, 0, 255, cv2.THRESH_BINARY|cv2.THRESH_OTSU)
    output_image = cv2.bitwise_not(threshold_image)

    contours, hierarchy = cv2.findContours(output_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    max_height = int(round(1 * source.shape[0]))
    max_width = int(round(1 * source.shape[1]))
    min_height = int(round(0.85 * source.shape[0]))
    min_width = int(round(0.85 * source.shape[1]))

    l = []
    src_for_cnts = source.copy()
    img = src_for_cnts
    for i, contour in enumerate(contours):
        length = cv2.arcLength(contours[i], False)
        area = cv2.contourArea(contours[i], False)

        if area < min_width*min_height:
            continue

        poly = cv2.approxPolyDP(contour, 0.00000001 * cv2.arcLength(contour, False), False)
        x, y, w, h = cv2.boundingRect(poly)

        img = cv2.drawContours(src_for_cnts, contour, -1, (100,200,0), 20)
        img = cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 255), 20)

        l.append([x, y, x + w, y + h])
    minimum = -1
    maximum = -1
    sorted_l = sorted(l, key = lambda b: (b[2]-b[0])*(b[3]-b[1]), reverse=True)
    if len(sorted_l) > 0:
        maximum = sorted_l[0]
        minimum = sorted_l[len(sorted_l)-1]
    return minimum, maximum


# def resize_img(img_path:str):
#     img = cv2.imread(img_path)
#     w, h, _ = img.shape
#     res_img = img
#     max_s = max(w, h)
#     if max_s > MAX_SIZE:
#         delta = max_s/MAX_SIZE
#         new_w = int(w/delta)
#         new_h = int(h/delta)
#         res_img = cv2.resize(res_img, (new_h, new_w), interpolation=cv2.INTER_LANCZOS4)
#         cv2.imwrite(img_path, res_img)
#     return res_img

def util(file, lang):
    img_ind = os.path.splitext(os.path.basename(file))[0]
    img = cv2.imread(file)
    if img is None:
        return [], 0, 0
    height = img.shape[0]
    width = img.shape[1]
    image_boxes = process_image(img, lang, img_ind, 0.945)#0.93, 0.95, 0.94, 0.945
    return image_boxes, height, width
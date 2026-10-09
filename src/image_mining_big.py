import os
import cv2
import numpy as np
import pytesseract

# MAX_SIZE = 32767

## block to compute contrast level of the image and adjust it accordingly
def detect_contrast_level(img:np.ndarray)->tuple:
    """Calculate the mean local minimum, maximum, and contrast difference.

    Args:
        img: BGR image whose contrast level should be measured.

    Returns:
        A tuple containing the mean eroded intensity, mean dilated intensity,
        and rounded difference between those values.
    """
    lab = cv2.cvtColor(img,cv2.COLOR_BGR2LAB)
    L,A,B=cv2.split(lab)

    kernel = np.ones((5,5),np.uint8)
    minimum = cv2.erode(L,kernel,iterations = 1)
    maximum = cv2.dilate(L,kernel,iterations = 1)

    minimum = minimum.astype(np.float64) 
    maximum = maximum.astype(np.float64) 

    return np.mean(minimum), np.mean(maximum), round(np.mean(maximum) - np.mean(minimum))

def _alpha_220(difference:float)->float:
    """Select the alpha value for images with minimum intensity at least 220.

    Args:
        difference: Difference between the local maximum and minimum intensity.

    Returns:
        The contrast-adjustment alpha value.
    """
    if difference <= 10.0: return 2.0
    elif difference < 15.0: return 2.5
    elif difference < 20.0: return 3.5
    elif difference < 35.0: return 2.0
    else: return 3.5

def _alpha_210(difference:float, minimum:float)->float:
    """Select the alpha value for minimum intensity in the 210-219 range.

    Args:
        difference: Difference between the local maximum and minimum intensity.
        minimum: Mean local minimum intensity.

    Returns:
        The contrast-adjustment alpha value.
    """
    if difference <= 3.0: return 1.6
    elif difference < 5.0: return 1.0
    elif difference <= 7.0: return 1.6
    elif difference <= 10.0: return 1.4 + (minimum - 210.0) * 0.1
    elif difference <= 15.0: return 2.0
    elif difference <= 20.0: return 2.5
    elif difference <= 30.0: return 3.0
    else: return 1.0

def _alpha_200(difference:float, minimum:float)->float:
    """Select the alpha value for minimum intensity in the 200-209 range.

    Args:
        difference: Difference between the local maximum and minimum intensity.
        minimum: Mean local minimum intensity.

    Returns:
        The contrast-adjustment alpha value.
    """
    if difference <= 10.0: return 1.9 + (minimum - 200.0) * 0.1
    elif difference < 15.0: return 3.0
    elif difference < 20.0: return 3.2
    elif difference < 25.0: return 3.5 - (minimum-200.0) * 0.15
    else: return 4.5

def _alpha_190(difference:float, minimum:float)->float:
    """Select the alpha value for minimum intensity in the 190-199 range.

    Args:
        difference: Difference between the local maximum and minimum intensity.
        minimum: Mean local minimum intensity.

    Returns:
        The contrast-adjustment alpha value.
    """
    if difference <= 5.0: return 2.5
    if difference <= 7.0: return 1.0 + (minimum - 190.0)*0.1
    if difference <= 8.0: return 1.8
    elif difference <= 10.0: return 1.8 + (minimum - 190.0)*0.1
    elif difference <= 13.0: return 2.5
    elif difference <= 17.0: return 1.9
    elif difference < 20.0: return 1.4
    elif difference < 25.0: return 2.0 + (minimum - 190.0)*0.1
    elif difference <= 27.0: return 3.0 - (minimum - 190.0)*0.1
    elif difference < 30.0: return 1.0
    else: return 2.5

def _alpha_180(difference:float, minimum:float)->float:
    """Select the alpha value for minimum intensity in the 180-189 range.

    Args:
        difference: Difference between the local maximum and minimum intensity.
        minimum: Mean local minimum intensity.

    Returns:
        The contrast-adjustment alpha value.
    """
    if difference <= 5.0: return 2.0
    if difference <= 8.0: return 2.6 - (minimum - 180.0) * 0.1
    if difference <= 10.0: return 4.0
    if difference <= 11.0: return 1.8
    elif difference < 15.0: return 2.1
    elif difference < 25.0: return 2.0
    elif difference < 30.0: return 2.3
    else: return 3.0

def _alpha_170(difference:float, minimum:float)->float:
    """Select the alpha value for minimum intensity in the 170-179 range.

    Args:
        difference: Difference between the local maximum and minimum intensity.
        minimum: Mean local minimum intensity.

    Returns:
        The contrast-adjustment alpha value.
    """
    if difference <= 7.0: return 1.5
    if difference < 10.0: return 1.0
    if difference <= 12.0: return 3.0
    elif difference <= 16.0: return 1.7
    elif difference <= 17.0: return 1.5
    elif difference <= 18.0: return 3.0
    elif difference <= 21.0: return 1.0 + (minimum - 170.0) * 0.1
    elif difference <= 25.0: return 2.0
    elif difference < 30.0: return 2.2
    elif difference < 35.0: return 2.5
    else: return 2.6

def _alpha_160(difference:float, minimum:float)->float:
    """Select the alpha value for minimum intensity in the 160-169 range.

    Args:
        difference: Difference between the local maximum and minimum intensity.
        minimum: Mean local minimum intensity.

    Returns:
        The contrast-adjustment alpha value.
    """
    if difference <= 8.0: return 2.0
    elif difference <= 11.0: return 1.6
    elif difference <= 12.0: return 4.0
    elif difference < 15.0: return 2.7
    elif difference <= 20.0: return 2.5
    elif difference <= 25.0: return 1.5 + (minimum - 160.0) * 0.1
    elif difference < 30.0: return 2.5
    elif difference <= 35.0: return 1.5
    elif difference < 45.0: return 2.0
    elif difference < 65.0: return 2.0
    else: return 1.0

def _alpha_150(difference:float, minimum:float)->float:
    """Select the alpha value for minimum intensity in the 150-159 range.

    Args:
        difference: Difference between the local maximum and minimum intensity.
        minimum: Mean local minimum intensity.

    Returns:
        The contrast-adjustment alpha value.
    """
    if difference <= 10.0: return 2.0
    elif difference <= 15.0: return 1.5
    elif difference < 20.0: return 2.5
    elif difference <= 25.0: return 2.0
    elif difference < 30.0: return 1.0
    elif difference < 35.0: return 2.5
    elif difference < 40.0: return 1.9 + (minimum - 150.0) * 0.1
    elif difference < 45.0: return 1.7
    elif difference < 50.0: return 2.0
    else: return 2.5

def _alpha_140(difference:float, minimum:float)->float:
    """Select the alpha value for minimum intensity in the 140-149 range.

    Args:
        difference: Difference between the local maximum and minimum intensity.
        minimum: Mean local minimum intensity.

    Returns:
        The contrast-adjustment alpha value.
    """
    if difference <= 10.0: return 1.3 + (minimum - 140.0) * 0.1
    elif difference <= 12.0: return 1.1
    elif difference < 15.0: return 1.5 + (minimum - 140.0) * 0.1
    elif difference < 20.0: return 2.0
    elif difference <= 27.0: return 1.7
    elif difference <= 30.0: return 1.0 + (minimum - 140.0) * 0.1
    elif difference <= 35.0: return 1.5
    elif difference <= 40.0: return 1.0
    elif difference <= 45.0: return 2.2 - (minimum - 140.0) * 0.1
    elif difference <= 50.0: return 1.6
    else: return 2.0

def _alpha_130(difference:float, minimum:float)->float:
    """Select the alpha value for minimum intensity in the 130-139 range.

    Args:
        difference: Difference between the local maximum and minimum intensity.
        minimum: Mean local minimum intensity.

    Returns:
        The contrast-adjustment alpha value.
    """
    if difference <= 10.0: return 1.5
    elif difference <= 15.0: return 2.5
    elif difference <= 30.0: return 2.0
    elif difference <= 45.0: return 1.35
    else: return 2.0

def _alpha_120(difference:float)->float:
    """Select the alpha value for minimum intensity in the 120-129 range.

    Args:
        difference: Difference between the local maximum and minimum intensity.

    Returns:
        The contrast-adjustment alpha value.
    """
    if difference <= 25.0: return 2.0
    elif difference <= 45.0: return 1.2
    else: return 1.8

def compute_alpha_hist(image:np.ndarray)->float:
    """Choose a contrast-adjustment alpha value based on image statistics.

    Args:
        image: BGR image whose contrast should be enhanced.

    Returns:
        Alpha multiplier used by :func:`equist_and_contrast`.
    """
    minimum, _, difference = detect_contrast_level(image)
    if minimum >= 230:
        return 2.5 if difference <= 15 else 1.0
    if minimum >= 220:
        return _alpha_220(difference)
    if minimum >= 210:
        return _alpha_210(difference, minimum)
    if minimum >= 200:
        return _alpha_200(difference, minimum)
    if minimum >= 190:
        return _alpha_190(difference, minimum)
    if minimum >= 180:
        return _alpha_180(difference, minimum)  
    if minimum >= 170:
        return _alpha_170(difference, minimum)
    if minimum >= 160:
        return _alpha_160(difference, minimum)
    if minimum >= 150:
        return _alpha_150(difference, minimum)
    if minimum >= 140:
        return _alpha_140(difference, minimum)
    if minimum >= 130:
        return _alpha_130(difference, minimum)
    if minimum >= 120:
        return _alpha_120(difference)
    elif minimum >= 110:
        return 1.0 if difference < 20.0 else 2.0
    elif minimum >= 100:
        return 1.0
    elif minimum >= 90:
        return 1.0 if difference < 30.0 else 2.0
    return 1.0

def equist_and_contrast(image:np.ndarray)->np.ndarray:
    """Equalize and contrast-enhance a BGR image in grayscale.

    Args:
        image: BGR image to preprocess.

    Returns:
        Contrast-enhanced grayscale image.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    equ = cv2.equalizeHist(gray)
    alpha = compute_alpha_hist(image)
    beta = 10
    adjusted = cv2.convertScaleAbs(equ, alpha=alpha, beta=beta)
    return adjusted

def preprocess_image(image:np.ndarray)->np.ndarray:
    """Preprocess a page image for contour-based image detection.

    Args:
        image: BGR page image to preprocess.

    Returns:
        Preprocessed grayscale image.
    """
    preprocessed = equist_and_contrast(image)
    return preprocessed


## block to consolidate overlapping boxes
def delete_on_edges(boxes:list, h:int, w:int)->list:
    """Remove boxes that touch page corners but do not cover most of the page.

    Args:
        boxes: Bounding boxes in ``[x1, y1, x2, y2]`` format.
        h: Image height in pixels.
        w: Image width in pixels.

    Returns:
        Boxes that are retained for overlap consolidation.
    """
    res_boxes = []
    for b in boxes:
        if b[0] <= 5 and b[1] <= 5 and (b[2] < w/2 or b[3] < h/2): continue
        if b[2] >= (w-5) and b[3] >= (h-5) and (b[0] > w/2 or b[1] > h/2): continue
        if b[2] >= (w-5) and b[1] <= 5 and (b[0] > w/2 or b[3] < h/2): continue
        if b[0] <= 5 and b[3] >= (h-5) and (b[2] < w/2 or b[1] > h/2): continue
        res_boxes.append(b)
    return res_boxes

def is_overlap(box1:list, box2:list)->bool:
    """Check whether two axis-aligned bounding boxes intersect.

    Args:
        box1: First box in ``[x1, y1, x2, y2]`` format.
        box2: Second box in ``[x1, y1, x2, y2]`` format.

    Returns:
        ``True`` when the boxes overlap; otherwise ``False``.
    """
    l1x, l1y = box1[0], box1[1]
    r1x, r1y = box1[2], box1[3]
    l2x, l2y = box2[0], box2[1]
    r2x, r2y = box2[2], box2[3]
    if l1x > r2x or l2x > r1x:
        return False
    if r1y < l2y or r2y < l1y:
        return False
    return True 

def find_overlap(l1:list, box:list)->tuple:
    """Merge a box with every intersecting box in a list.

    Args:
        l1: Candidate boxes in ``[x1, y1, x2, y2]`` format.
        box: Box to expand using intersecting candidates.

    Returns:
        A tuple containing non-overlapping candidates and the merged box.
    """
    l2 = []
    for i in range(len(l1)):
        if is_overlap(box, l1[i]):
            box = [
                    min(box[0], l1[i][0]),
                    min(box[1], l1[i][1]),
                    max(box[2], l1[i][2]),
                    max(box[3], l1[i][3])
                ]
        else:
            l2.append(l1[i])
    return l2, box

def detect_overlap(list_of_boxes:list, im:np.ndarray, size:int)->list:
    """Consolidate overlapping boxes whose area exceeds a threshold.

    Args:
        list_of_boxes: Candidate boxes in ``[x1, y1, x2, y2]`` format.
        im: Source image used to determine image dimensions.
        size: Minimum area required for a consolidated box.

    Returns:
        Consolidated bounding boxes.
    """
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

            res_boxes.append(res)

            if len(l0) > 0:
                    biggest = (l0[len(l0)-1][2] - l0[len(l0)-1][0])*(l0[len(l0)-1][3] - l0[len(l0)-1][1])
                    res = l0[len(l0)-1]
            else:
                break
    return res_boxes


## block to filter out fase positives (text, borders, stripes, etc.)
def preprocess_for_text(img:np.ndarray)->np.ndarray:
    """Prepare an image crop for OCR-based text detection.

    Args:
        img: Image crop to preprocess.

    Returns:
        Thresholded grayscale image suitable for OCR.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) 
    blur = cv2.GaussianBlur(gray,(9, 9),0)
    ret, thresh1 = cv2.threshold(blur, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY_INV) 
    thresh = cv2.bitwise_not(thresh1)
    return thresh

def get_image_std(page:np.ndarray, box:list)->float:
    """Calculate the grayscale standard deviation inside a bounding box.

    Args:
        page: Source page image.
        box: Bounding box in ``[x1, y1, x2, y2]`` format.

    Returns:
        Standard deviation of pixel intensity within the crop.
    """
    x1, y1, x2, y2 = box
    area = page[y1:y2, x1:x2]
    img_gray = cv2.cvtColor(area, cv2.COLOR_RGB2GRAY)
    contrast = img_gray.std()
    return contrast

def is_text(img:np.ndarray, box:list, lang_op:str)->bool:
    """Determine whether an image crop contains sufficiently confident text.

    Args:
        img: Source page image.
        box: Bounding box in ``[x1, y1, x2, y2]`` format.
        lang_op: Tesseract language code used for OCR.

    Returns:
        ``True`` when OCR detects qualifying text; otherwise ``False``.
    """
    x1, y1, x2, y2 = box
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

    mean_conf = mean_conf/word_count if word_count > 0 else 0

    if mean_conf >= 60:
        if 0.1 <= (text_area/((x2-x1)*(y2-y1))) <= 1: #if it is text, than it is never greater than 1
            return True
    return False

def is_on_edge(imW:int, imH:int, box:list)->bool:
    """Check whether a box lies within the configured page-edge regions.

    Args:
        imW: Image width in pixels.
        imH: Image height in pixels.
        box: Bounding box in ``[x1, y1, x2, y2]`` format.

    Returns:
        ``True`` when the box is considered close to an edge; otherwise ``False``.
    """
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

def filter_text(img:np.ndarray, boxes:list, lang:str)->list:
    """Remove candidate boxes identified as text by OCR.

    Args:
        img: Source page image.
        boxes: Candidate boxes in ``[x1, y1, x2, y2]`` format.
        lang: Tesseract language code used for OCR.

    Returns:
        Candidate boxes that are not classified as text.
    """
    images = []
    for i in range(len(boxes)):
        if is_text(img, boxes[i], lang):
            continue
        images.append(boxes[i])
    return images

def filter_size(imW:int, imH:int, boxes:list)->list:
    """Remove candidate boxes that are too small or nearly page-sized.

    Args:
        imW: Image width in pixels.
        imH: Image height in pixels.
        boxes: Candidate boxes in ``[x1, y1, x2, y2]`` format.

    Returns:
        Candidate boxes within the accepted size range.
    """
    images = []
    for i in range(len(boxes)):
        if (boxes[i][2]-boxes[i][0])*(boxes[i][3]-boxes[i][1]) <= (imW*0.075)*(imH*0.075):
            continue
        if (boxes[i][2]-boxes[i][0])*(boxes[i][3]-boxes[i][1]) >= (imW*0.97)*(imH*0.97):
            continue
        images.append(boxes[i])
    return images

def filter_borders(imW:int, imH:int, boxes:list)->list:
    """Remove elongated candidate boxes located on page edges.

    Args:
        imW: Image width in pixels.
        imH: Image height in pixels.
        boxes: Candidate boxes in ``[x1, y1, x2, y2]`` format.

    Returns:
        Candidate boxes remaining after border filtering.
    """
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

def filter_stripes(boxes:list)->list:
    """Remove horizontally or vertically elongated candidate boxes.

    Args:
        boxes: Candidate boxes in ``[x1, y1, x2, y2]`` format.

    Returns:
        Candidate boxes that are not classified as stripes.
    """
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

def filter_edges(imW:int, imH:int, boxes:list)->list:
    """Remove all candidate boxes located near a page edge.

    Args:
        imW: Image width in pixels.
        imH: Image height in pixels.
        boxes: Candidate boxes in ``[x1, y1, x2, y2]`` format.

    Returns:
        Candidate boxes that are not near an edge.
    """
    images = []
    for i in range(len(boxes)):
        if is_on_edge(imW, imH, boxes[i]): continue
        else: images.append(boxes[i])
    return images

def filter_monotone(img:np.ndarray, boxes:list)->list:
    """Remove candidate boxes whose crops have very low contrast.

    Args:
        img: Source page image.
        boxes: Candidate boxes in ``[x1, y1, x2, y2]`` format.

    Returns:
        Candidate boxes with grayscale standard deviation above the threshold.
    """
    images = []
    for b in boxes:
        if get_image_std(img, b) > 8:
            images.append(b)

    return images


## main function to extract bboxes of images from the page
def extract_img_bboxes(source:np.ndarray, lang:str, size=0.945)->list:
    """Extract and filter image bounding boxes from a page image.

    Args:
        source: BGR page image to analyze.
        lang: Tesseract language code used to remove text regions.
        size: Maximum fraction of page width or height accepted for a box.

    Returns:
        Filtered bounding boxes in ``[x1, y1, x2, y2]`` format.
    """
    if source is None:
        return []
    contrast_image = preprocess_image(source)
    source_gray = contrast_image
    _, threshold_image = cv2.threshold(source_gray, 0, 255, cv2.THRESH_BINARY|cv2.THRESH_OTSU)
    output_image = cv2.bitwise_not(threshold_image)
    contours, _ = cv2.findContours(output_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    min_area_pct = 0.000001
    min_area = min_area_pct * source.size

    max_height = int(round(size * source.shape[0]))
    max_width = int(round(size * source.shape[1]))

    l = []
    src_for_cnts = source.copy()
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contours[i], False)

        if area < min_area:
            continue
        poly = cv2.approxPolyDP(contour, 0.01 * cv2.arcLength(contour, False), False)
        x, y, w, h = cv2.boundingRect(poly)
        if w >= max_width or h >= max_height or w*h < 1_000:
            continue

        l.append([x, y, x + w, y + h])

    found_ims = []
    if len(l) != 0:
        b = detect_overlap(l, src_for_cnts, 90_000)
        for i in range(len(b)):
            x, y, w, h = b[i][0], b[i][1], b[i][2]-b[i][0], b[i][3]-b[i][1]
            found_ims.append([x, y, w+x, h+y])

    found_ims = filter_borders(source.shape[1], source.shape[0], found_ims)
    found_ims = filter_size(source.shape[1], source.shape[0], found_ims)
    found_ims = filter_edges(source.shape[1], source.shape[0], found_ims)
    found_ims = filter_stripes(found_ims)
    found_ims = filter_text(source, found_ims, lang)
    found_ims = filter_monotone(source, found_ims)
    return found_ims

def util(file:str, lang:str)->tuple[list, int, int]:
    """Load an image file and extract its image bounding boxes.

    Args:
        file: Path to the page image.
        lang: Tesseract language code used to remove text regions.

    Returns:
        A tuple containing bounding boxes, image height, and image width.
        If the file cannot be read, returns ``([], 0, 0)``.
    """
    img = cv2.imread(file)
    if img is None:
        return [], 0, 0
    height = img.shape[0]
    width = img.shape[1]
    image_boxes = extract_img_bboxes(img, lang, 0.945)
    return image_boxes, height, width


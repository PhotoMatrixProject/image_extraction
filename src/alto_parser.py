import xml.etree.ElementTree as ET
import xml.etree
import new_caption as nc

ILLUSTRATION_FLAG = 'Illustration'
TEXT_BLOCK_FLAG = 'TextBlock'
STRING_FLAG = 'String'
WIDTH_FLAG = 'WIDTH'
HEIGHT_FLAG = 'HEIGHT'
HPOS_FLAG = 'HPOS'
VPOS_FLAG = 'VPOS'
CONTENT_ATTR_FLAG = "CONTENT"
TEXT_LINE_FLAG = 'TextLine'
COMPOSED_BLOCK_FLAG = 'ComposedBlock'
BOTTOM_MARGIN_FLAG = 'BottomMargin'
PRINT_SPACE_FLAG = 'PrintSpace'
PAGE_FLAG = 'Page'
LAYOUT_FLAG = "Layout"

RIGHT_FLAG = "right"
LEFT_FLAG = "left"
TOP_FLAG = "up"
BOTTOM_FLAG = "bottom"

def get_element_width_height(e:ET.Element)->list[int]:
    ''' Returns width and height of the element.'''
    attr = e.attrib
    if (WIDTH_FLAG in attr.keys()) and (HEIGHT_FLAG in attr.keys()):
        return [int(float(attr[WIDTH_FLAG])), int(float(attr[HEIGHT_FLAG]))]
    return [0, 0]

def get_element_coordinates(e:ET.Element)->list[int]:
    attrs = e.attrib
    if len(attrs) == 0:
        return [-1, -1, -1, -1]

    needed_attrs = [HPOS_FLAG, VPOS_FLAG, WIDTH_FLAG, HEIGHT_FLAG]
    res_attrs = []
    for at in needed_attrs:
        if at in attrs.keys():
            res_attrs.append(int(float(attrs[at])))
        else:
            return [-1, -1, -1, -1]

    return res_attrs

def get_element_content(e:ET.Element)->str:
    attrs = e.attrib
    if CONTENT_ATTR_FLAG in attrs.keys():
        res = attrs[CONTENT_ATTR_FLAG]
        return res
    return ""

def parse_string(string:ET.Element)->str:
    content = get_element_content(string)
    return content

def parse_text_line(text_line:ET.Element)->list[str]:
    text = []
    for child in text_line:
        if child.tag.endswith(STRING_FLAG):
            text.append(parse_string(child))
    return text

def parse_text_block(text_block:ET.Element)->list[str]:
    text = []
    for child in text_block:
        if child.tag.endswith(TEXT_LINE_FLAG):
            text += parse_text_line(child)
    return text

def parse_illustration(illustartion:ET.Element)->list[int]:
    '''Returns coordinates of an illustration in page.'''
    coords = get_element_coordinates(illustartion)
    return coords

def find_elements_in_composed_block(composed_block:ET.Element, bbox_flag:str)->list[ET.Element]:
    '''returns elements with given flag found in a composed block of the alto file.'''
    blocks = []
    for child in composed_block:
        if child.tag.endswith(bbox_flag):
            blocks.append(child)
        elif child.tag.endswith(COMPOSED_BLOCK_FLAG):
            blocks += find_elements_in_composed_block(child, bbox_flag)
    return blocks

def parse_print_space(print_space:ET.Element, bbox_flag:str)->list[ET.Element]:
    blocks = []
    for child in print_space:
        if child.tag.endswith(COMPOSED_BLOCK_FLAG):
            blocks += find_elements_in_composed_block(child, bbox_flag)
        if child.tag.endswith(bbox_flag):
            blocks.append(child)
    return blocks

def parse_page(page:ET.Element, bbox_flag:str)->list[ET.Element]:
    blocks = []
    for child in page:
        if child.tag.endswith(PRINT_SPACE_FLAG):
            blocks += parse_print_space(child, bbox_flag)

    return blocks

def parse_layout(layout:ET.Element, bbox_flag:str)->list[ET.Element]:
    blocks = []
    for child in layout:
        if child.tag.endswith(PAGE_FLAG):
            blocks += parse_page(child, bbox_flag)
    return blocks


def find_interesting_bboxes_in_alto(alto_file_path:str, bbox_flag:str)->list[ET.Element]:
    try:
        try:
            parser = ET.XMLParser(encoding="latin-1")#encoding="utf-8"latin-1
            tree = ET.parse(alto_file_path, parser=parser)
        except:
            parser = ET.XMLParser(encoding="utf-8")#encoding="utf-8"latin-1
            tree = ET.parse(alto_file_path, parser=parser)
        root = tree.getroot()
        blocks = []
        for child in root:
            if child.tag.endswith(LAYOUT_FLAG):
                blocks += parse_layout(child, bbox_flag)

        return blocks
    except:
        print('ERROR IN ALTO in interesting blocks')
        return []

def find_illustrations(alto_file_path:str)->list[ET.Element]:
    ills = find_interesting_bboxes_in_alto(alto_file_path, ILLUSTRATION_FLAG)
    ills_comment = find_ills_in_comment(alto_file_path)
    res_ills = []
    if len(ills_comment) == 0: return ills
    for ill in ills:
        # coords = get_element_coordinates(ill)
        # if coords in ills_comment:
        res_ills.append(ill)
    return res_ills

class CommentTreeBuilder(ET.TreeBuilder):
    def __init__(self):
        self.COMMENT_FLAG = '!comment'

    def comment(self, data):
        self.start(self.COMMENT_FLAG, {})
        self.data(data)
        self.end(self.COMMENT_FLAG)

def get_coords_of_ill_from_comment(line:str)->list[int]:
    coords = {HPOS_FLAG:0, VPOS_FLAG:0, WIDTH_FLAG:0, HEIGHT_FLAG:0}
    words = line.split(' ')
    for word in words:
        if word.startswith(HPOS_FLAG):
            coords[HPOS_FLAG] = int(float(word.split('=')[1].replace('"', '')))
        if word.startswith(VPOS_FLAG):
            coords[VPOS_FLAG] = int(float(word.split('=')[1].replace('"', '')))
        if word.startswith(WIDTH_FLAG):
            coords[WIDTH_FLAG] = int(float(word.split('=')[1].replace('"', '')))  
        if word.startswith(HEIGHT_FLAG):
            coords[HEIGHT_FLAG] = int(float(word.split('=')[1].replace('"', '')))
    return list(coords.values())

def parse_comment_text(text:str)->list[list[int]]:
    ill_bboxes = []
    lines = text.split('\n')
    for line in lines:
        if 'Type="Picture"' in line:
            ill_bboxes.append(get_coords_of_ill_from_comment(line))
    return ill_bboxes

def find_ills_in_comment(alto_file_path:str)->list[list[int]]:
    tb = CommentTreeBuilder()
    try:
        xp = ET.XMLParser(target=tb, encoding="latin-1")#encoding="utf-8"latin-1
        tree = ET.parse(alto_file_path, parser=xp)
    except:
        xp = ET.XMLParser(target=tb, encoding="utf-8")#encoding="utf-8"latin-1
        tree = ET.parse(alto_file_path, parser=xp)
    root = tree.getroot()
    ill_bbboxes = []
    for child in root:
        if child.tag.endswith(tb.COMMENT_FLAG):
            ill_bbboxes = parse_comment_text(child.text)
    return ill_bbboxes

def get_pos(ill_bbox:list[int], text_bbox:list[int])->str:
    '''Returns a position of the bbox in relation to the image if the bbox has a probability of containing caption.'''
    x1, y1, x2, y2 = ill_bbox[0], ill_bbox[1], ill_bbox[0]+ill_bbox[2], ill_bbox[1]+ill_bbox[3] # image in page
    x3, y3, x4, y4 = text_bbox[0], text_bbox[1], text_bbox[0]+text_bbox[2], text_bbox[1]+text_bbox[3] # text block
    if x2 < x3: 
        if is_possible_to_contain_caption_right_left(ill_bbox, text_bbox):
            return RIGHT_FLAG
    if x4 < x1:
        if is_possible_to_contain_caption_right_left(ill_bbox, text_bbox):
            return LEFT_FLAG
    if y1 > y4: 
        if is_possible_to_contain_caption_up_down(ill_bbox, text_bbox):
            return TOP_FLAG
    if y2 < y3:
        if is_possible_to_contain_caption_up_down(ill_bbox, text_bbox):
            return BOTTOM_FLAG
    return ''

def is_possible_to_contain_caption_right_left(ill_coords:list[int], bbox:list[int]):
    x1, y1, x2, y2 = ill_coords[0], ill_coords[1], ill_coords[0]+ill_coords[2], ill_coords[1]+ill_coords[3] # image in page
    x3, y3, x4, y4 = bbox[0], bbox[1], bbox[0]+bbox[2], bbox[1]+bbox[3] # text block

    if y1 < y4 and y2 > y3: return True
    return False

def is_possible_to_contain_caption_up_down(ill_coords:list[int], bbox:list[int]):
    x1, y1, x2, y2 = ill_coords[0], ill_coords[1], ill_coords[0]+ill_coords[2], ill_coords[1]+ill_coords[3] # image in page
    x3, y3, x4, y4 = bbox[0], bbox[1], bbox[0]+bbox[2], bbox[1]+bbox[3] # text block

    if x1 < x4 and x2 > x3: return True
    return False

def match_bboxes_to_illustrations(ill_coords:list[int], bboxes:list[ET.Element])->dict:
    '''Returns dictionary, which contains text blocks around the image which are the most probable to contain caption. '''
    # ill_coords = get_element_coordinates(illustration)
    bboxes_pos = {RIGHT_FLAG:[], LEFT_FLAG:[], TOP_FLAG:[], BOTTOM_FLAG:[]}
    for bbox in bboxes:
        if len(list(bbox)) > 0: # german jornals have empty TextBlock bounding illustrations, they do not contain text
            bb_coords = get_element_coordinates(bbox)
            pos = get_pos(ill_coords, bb_coords)
            if len(pos) > 0:
                bboxes_pos[pos].append(bbox)

    return bboxes_pos


def find_page_width_height(alto_path:str)->list[int]:
    try:
        try:
            parser = ET.XMLParser(encoding="latin-1")#utf-8 latin-1
            tree = ET.parse(alto_path, parser=parser)
        except:
            parser = ET.XMLParser(encoding="utf-8")#utf-8 latin-1
            tree = ET.parse(alto_path, parser=parser)
        root = tree.getroot()

        for child in root:
            if child.tag.endswith(LAYOUT_FLAG):
                for child2 in child:
                    if child2.tag.endswith(PAGE_FLAG):
                        page_dims = get_element_width_height(child2)
                        if page_dims != [0,0]:
                            return page_dims
                        for child3 in child2:
                            if child3.tag.endswith(PRINT_SPACE_FLAG):
                                return get_element_width_height(child3)
        return [0, 0]
    except:
        print('ERROR IN ALTO from WIDTH/HEIGHT')
        return [0, 0]


def get_small_blocks(blocks:list[ET.Element], limit:int, criterion_index:int)->list[ET.Element]:
    small_close_text_blocks = []
    for block in blocks: # get rid of close blocks which are two times higher than the closest block
        if get_element_coordinates(block)[criterion_index]/2 < limit:
            small_close_text_blocks.append(block)
        else:
            break
    return small_close_text_blocks

def analyze_read_cap_blocks(blocks:list[ET.Element])->list[str]:
    if len(blocks) == 0:
        return []
    else:
        text = read_caption(blocks)
        if len(text) > 30:
            closest_text = read_caption([blocks[0]])
            return closest_text
        else:
            return text


def get_element_bbox_square(e:ET.Element)->int:
    w, h = get_element_width_height(e)
    return w*h

def read_caption(text_blocks:list[ET.Element])->list[str]:
    '''Returns text, which is in the given list of elements.'''
    blocks = []
    for text_block in text_blocks:
        if text_block.tag.endswith(TEXT_LINE_FLAG):
            blocks += parse_text_line(text_block)
        elif text_block.tag.endswith(TEXT_BLOCK_FLAG):
            blocks += parse_text_block(text_block)
    return blocks

def find_nearest_text_bottom(ill_coords, text_blocks:list[ET.Element], width_orig:int, height_orig:int)->tuple:
    sorted_blocks = sorted(text_blocks, key = lambda b: get_element_coordinates(b)[1]) # 1. sort according to the distance from the image

    closest_text_block = sorted_blocks[0]
    x0, y0, w0, h0 = get_element_coordinates(closest_text_block)
    dist_between_img_and_text_block = y0 - (ill_coords[1]+ill_coords[3])
    res = [closest_text_block]
    for i in range(1, len(sorted_blocks)): # 2. discard too small, too big text blocks or far blocks
        x, y, w, h = get_element_coordinates(sorted_blocks[i])
        if (y - (y0+h0)) < height_orig/100:
            if (1_000 <= get_element_bbox_square(sorted_blocks[i]) <= ill_coords[2]*ill_coords[3]/2):
                res.append(sorted_blocks[i])

    if len(res) == 0: return [], -1
    elif len(res) == 1:
        if get_element_width_height(closest_text_block)[1] < ill_coords[3]/2: # already checked if the size is appropriate (2.), now need to make sure that it is nit too high
            # dist_between_img_and_text_block = y0 - (ill_coords[1]+ill_coords[3])
            res_words = analyze_read_cap_blocks(res)
            return res_words, dist_between_img_and_text_block
        return [], -1
    else: # 3. find text blocks that are close to the closest text block to the image
        small_close_text_blocks = get_small_blocks(res, h0, 3)
        result = analyze_read_cap_blocks(small_close_text_blocks)
        if (0 < len(result) <= 30):
            return result, dist_between_img_and_text_block
        else: return [], -1

def work_with_bottom(ill_coords:list[int], text_blocks:list[ET.Element], width:int, height:int)->tuple:
    if len(text_blocks) > 0:
        caption_words, distance = find_nearest_text_bottom(ill_coords, text_blocks, width, height)
        if len(caption_words) > 0:
            caption = " ".join(caption_words)
            if len(caption) != 0:
                return caption, distance, 0
    return "", -1, 0

def find_nearest_text_top(ill_coords, text_blocks:list[ET.Element], width_orig:int, height_orig:int)->tuple:
    sorted_blocks = sorted(text_blocks, key = lambda b: get_element_coordinates(b)[1]+get_element_coordinates(b)[3], reverse=True)

    closest_text_block = sorted_blocks[0]
    x0, y0, w0, h0 = get_element_coordinates(closest_text_block)
    dist_between_img_and_text_block = ill_coords[1] - (y0+h0)#(ill_coords[1]+ill_coords[3]) - (y0+h0) - why like that???
    res = [closest_text_block]
    for i in range(1, len(sorted_blocks)): # 2. discard too small, too big text blocks or far blocks
        x, y, w, h = get_element_coordinates(sorted_blocks[i])
        if (y0 - (y+h)) < height_orig/100:
            if (1_000 <= get_element_bbox_square(sorted_blocks[i]) <= ill_coords[2]*ill_coords[3]/2):
                res.append(sorted_blocks[i])

    if len(res) == 0: return [], -1
    elif len(res) == 1:
        if get_element_width_height(closest_text_block)[1] < ill_coords[3]/2: # already checked if the size is appropriate (2.), now need to make sure that it is nit too high
            res_words = analyze_read_cap_blocks(res)
            return res_words, dist_between_img_and_text_block
        return [], -1
    else:
        small_close_text_blocks = get_small_blocks(res, h0, 3)
        result = analyze_read_cap_blocks(small_close_text_blocks)
        if (0 < len(result) <= 30):
            return result, dist_between_img_and_text_block
        else: return [], -1

def work_with_top(ill_coords:list[int], text_blocks:list[ET.Element], width:int, height:int)->tuple:
    if len(text_blocks) > 0:
        caption_words, distance = find_nearest_text_top(ill_coords, text_blocks, width, height)
        if len(caption_words) > 0:
            caption = " ".join(caption_words)
            if len(caption) != 0:
                return caption, distance, 0
    return "", -1, 0

def find_nearest_text_right(ill_coords, text_blocks:list[ET.Element], width_orig:int, height_orig:int)->tuple:
    sorted_blocks = sorted(text_blocks, key = lambda b: get_element_coordinates(b)[0])

    closest_text_block = sorted_blocks[0]
    x0, y0, w0, h0 = get_element_coordinates(closest_text_block)
    dist_between_img_and_text_block = x0 - (ill_coords[0]+ill_coords[2])
    res = [closest_text_block]
    for i in range(1, len(sorted_blocks)): # 2. discard too small, too big text blocks or far blocks
        x, y, w, h = get_element_coordinates(sorted_blocks[i])
        if (x - (x0+w0)) < width_orig/100:
            if (1_000 <= get_element_bbox_square(sorted_blocks[i]) <= ill_coords[2]*ill_coords[3]/2):
                res.append(sorted_blocks[i])


    if len(res) == 0: return [], -1
    elif len(res) == 1:
        if (get_element_width_height(closest_text_block)[0] < ill_coords[2]/2 and 
            get_element_width_height(closest_text_block)[1] < ill_coords[3]/2): # already checked if the size is appropriate (2.), now need to make sure that it is not too wide or too high
            res_words = analyze_read_cap_blocks(res)
            return res_words, dist_between_img_and_text_block
        return [], -1
    else:
        small_close_text_blocks = get_small_blocks(res, w0, 2)
        result = analyze_read_cap_blocks(small_close_text_blocks)
        if (0 < len(result) <= 30):
            return result, dist_between_img_and_text_block
        else: return [], -1

def work_with_right(ill_coords:list[int], text_blocks:list[ET.Element], width:int, height:int)->tuple:
    if len(text_blocks) > 0:
        caption_words, distance = find_nearest_text_right(ill_coords, text_blocks, width, height)
        if len(caption_words) > 0:
            caption = " ".join(caption_words)
            if len(caption) != 0:
                return caption, distance, 0
    return "", -1, 0

def find_nearest_text_left(ill_coords, text_blocks:list[ET.Element], width_orig:int, height_orig:int)->tuple:
    sorted_blocks = sorted(text_blocks, key = lambda b: get_element_coordinates(b)[0] + get_element_coordinates(b)[2], reverse=True)

    closest_text_block = sorted_blocks[0]
    x0, y0, w0, h0 = get_element_coordinates(closest_text_block)
    dist_between_img_and_text_block = ill_coords[0] - (x0+w0)
    res = [closest_text_block]
    for i in range(1, len(sorted_blocks)): # 2. discard too small, too big text blocks or far blocks
        x, y, w, h = get_element_coordinates(sorted_blocks[i])
        if ((x+w) - x0) < width_orig/100:
            if (1_000 <= get_element_bbox_square(sorted_blocks[i]) <= ill_coords[2]*ill_coords[3]/2):
                res.append(sorted_blocks[i])

    if len(res) == 0: return [], -1
    elif len(res) == 1:
        if (get_element_width_height(closest_text_block)[0] < ill_coords[2]/2 and
            get_element_width_height(closest_text_block)[1] < ill_coords[3]/2): # already checked if the size is appropriate (2.), now need to make sure that it is not too wide or too high
            res_words = analyze_read_cap_blocks(res)
            return res_words, dist_between_img_and_text_block
        return [], -1
    else:
        small_close_text_blocks = get_small_blocks(res, w0, 2)
        result = analyze_read_cap_blocks(small_close_text_blocks)
        if (0 < len(result) <= 30):
            return result, dist_between_img_and_text_block
        else: return [], -1

def work_with_left(ill_coords:list[int], text_blocks:list[ET.Element], width:int, height:int)->tuple:
    if len(text_blocks) > 0:
        caption_words, distance = find_nearest_text_left(ill_coords, text_blocks, width, height)
        if len(caption_words) > 0:
            caption = " ".join(caption_words)
            if len(caption) != 0:
                return caption, distance, 0
    return "", -1, 0

def get_textlines_from_textblock(text_block:ET.Element)->list[ET.Element]:
    text_lines = []
    for child in text_block:
        if child.tag.endswith(TEXT_LINE_FLAG):
            text_lines.append(child)
    return text_lines

def break_textblocks_into_textlines(text_blocks:list[ET.Element])->list[ET.Element]:
    text_lines = []
    for text_block in text_blocks:
        text_lines += get_textlines_from_textblock(text_block)
    return text_lines

def find_caption(ill_coords:list[int], text_blocks:dict, width:int, height:int)->tuple:
    caps_dists = []

    cap_b, distance_b, angle_b = work_with_bottom(ill_coords, text_blocks[BOTTOM_FLAG], width, height)
    if len(cap_b) == 0: cap_b, distance_b, angle_b = work_with_bottom(ill_coords, break_textblocks_into_textlines(text_blocks[BOTTOM_FLAG]), width, height)
    caps_dists.append((cap_b, distance_b))

    cap_t, distance_t, angle_t = work_with_top(ill_coords, text_blocks[TOP_FLAG], width, height)
    if len(cap_t) == 0: cap_t, distance_t, angle_t = work_with_top(ill_coords, break_textblocks_into_textlines(text_blocks[TOP_FLAG]), width, height)
    caps_dists.append((cap_t, distance_t))

    cap_r, distance_r, angle_r = work_with_right(ill_coords, text_blocks[RIGHT_FLAG], width, height)
    caps_dists.append((cap_r, distance_r))

    cap_l, distance_l, angle_l = work_with_left(ill_coords, text_blocks[LEFT_FLAG], width, height)
    caps_dists.append((cap_l, distance_l))

    caption = nc.fix_multiple_captions(caps_dists)
    return caption, 0


def is_big_enough(ill:list[int], width:int, height:int)->bool:
    '''If width or height of illustration is less than 5% of the page width or height respectively,
    then it is not an illustration. It is either a graphical element or an error.'''
    # _, _, w, h = get_element_coordinates(ill)
    _, _, w, h = ill
    if w < width*0.05 or h < height*0.05:
        return False
    return True

def is_inscribed(bbox1:list[int], bbox2:list[int])->bool:
    '''Returns True if bbox2 is inside bbox1, otherwise returns False.'''
    x1, y1, x2, y2 = bbox1
    x3, y3, x4, y4 = bbox2

    if x1 < x3 and y1 < y3 and x2 > x4 and y2 > y4:
        return True
    return False

def is_bbox_inscribed_in_bboxes(ill:list[int], ills:list[list[int]])->bool:
    for i in range(len(ills)):
        if is_inscribed(ills[i], ill):
            return True
    return False

def delete_inscribed_bboxes(ills:list[list[int]], caps:list[str], angles:list[int])->tuple:
    if len(ills) <= 1: return ills, caps, angles
    res_ills = []
    res_caps = []
    res_angles = []
    for i in range(len(ills)):
        if not is_bbox_inscribed_in_bboxes(ills[i], ills):
            res_ills.append(ills[i])
            res_caps.append(caps[i])
            res_angles.append(angles[i])
    return res_ills, res_caps, res_angles

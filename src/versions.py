import cv2 
import os
from unidecode import unidecode
# import math


def gray_version(coloured_ver):
    gray = cv2.cvtColor(coloured_ver, cv2.COLOR_BGR2GRAY)
    return gray

def rotate(im, degree):
    if degree == 0:
        return im
    if degree == 90:
        return cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE)
    if degree == 270:
        return cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)

def get_versions(page_num, name, file, images, output_dir, degrees_to_rotate):
    im = cv2.imread(file)
    area_percentages = []
    img_paths = []
    for i in range(len(images)):
        [x1, y1, x2, y2] = images[i]
        width = int((x2-x1)*0.05)
        height = int((y2-y1)*0.05)

        big_origin = rotate(im[max(0, y1-height):min(im.shape[0], y2+height),
                        max(0, x1-width):min(im.shape[1], x2+width)], degrees_to_rotate[i])
        res_image = fix_size(big_origin)
        # print(cv2.imwrite(os.path.join(output_dir+"/big_original/", name+"%d_%d.jpeg" % (page_num, i+1)), res_image))
        name = unidecode(name).replace(' ', '_')
        img_path = os.path.join(output_dir+"/big_original/", name+"%s_%d.jpeg" % (page_num, i+1))
        cv2.imwrite(img_path, res_image)
        img_paths.append(img_path)
        area_percentages.append(get_image_area_percentage((x2-x1), (y2-y1), im.shape[1], im.shape[0]))
    return area_percentages, img_paths

def get_image_area_percentage(im_w, im_h, page_w, page_h):
    return round((im_w*im_h)/(page_w*page_h), 2)

def fix_size(img):
    width = img.shape[1]
    height = img.shape[0]

    if max(width, height) < 3000:
        return img

    if width > height:
        new_width = 3000
        new_height = (height/width) * new_width
    else:
        new_height = 3000
        new_width = new_height/(height/width)

    dim = (int(new_width), int(new_height))
    resized_img = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
    return resized_img





import glob
from default_params import default_params
import skimage.io
import numpy as np
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
import os.path
import skimage.io
import time
import json
import multiprocessing

import skimage.io
from Panos.Pano_rectification import simon_rectification
from Panos.Pano_project import project_face, stitch_tiles, render_imgs
import matplotlib.pyplot as plt

from Panos.Pano_visualization import R_heading, draw_all_vp_and_hl_color, draw_all_vp_and_hl_bi, \
    draw_zenith_on_top_color, draw_zenith_on_top_bi, draw_sphere_zenith, R_roll, R_pitch
from Panos.Pano_zp_hvp import calculate_consensus_zp
from Panos.Pano_consensus_vis import draw_consensus_zp_hvps, draw_consensus_rectified_sphere, \
    draw_center_hvps_rectified_sphere, draw_center_hvps_on_panorams
import Pano_hvp
from Panos.Pano_histogram import calculate_histogram
from Panos.Pano_project import project_facade_for_refine
from argparse import ArgumentParser

import time

########## get param
parser = ArgumentParser()
parser.add_argument(
    '--imgs',
    default='Pano_new/New/images',
    help='image folder with .jpg image')
parser.add_argument(
    '--out',
    default='Pano_new/New/Rendering',
    help='image folder')
parser.add_argument(
    '--imgsmode',
    default='folder',
    help='--if imgs is a single image instead of a folder, enter "image"')
args = parser.parse_args()

########## add new random seed
#np.random.seed(1)

plot_redundant = False
save_directly = True

root = 'Pano_new'

Country_city = 'New'

tmp_count = 1 # pylsd.lsd(scale=tmp_count)

inter_Dir = os.path.join(root, 'Pano_hl_z_vp/')

if args.imgsmode=='image':
    print('single')
    imageList = [args.imgs]
else:
    Img_folder = args.imgs
    imageList = glob.glob(os.path.join(Img_folder ,'*.jpg'))
    imageList.sort()

rendering_output_folder = args.out
if not os.path.exists(rendering_output_folder):
    os.makedirs(rendering_output_folder)

# for im_path in ['/home/zhup/Desktop/GSV_Pano_val/Val/images/9wG3a9VOkwTSqnq6zsbdSQ.jpg']:
# for im_path in imageList[10*new_count:10*(new_count+1)]:
start_time = time.perf_counter()
temp_time = start_time 
img_sum = len(imageList)
img_num = 0
for im_path in imageList:
    img_num += 1
    print(f'===start processing: {img_num}/{img_sum} {im_path}')
    im = Image.open(im_path)
    # rendering_img_base = os.path.join(rendering_output_folder, os.path.splitext(os.path.basename(im_path))[0])
    rendering_img_base = os.path.join(rendering_output_folder, os.path.splitext(os.path.basename(im_path))[0])

    task = 'hahaha/'
    thread_num = 1
    thread = str(thread_num) + '/'
    tmp_folder = os.path.join(root, Country_city, 'tmp', task, thread)

    if not os.path.exists(tmp_folder):
        os.makedirs(tmp_folder)
    removelist = glob.glob(tmp_folder + '*.jpg')
    for i in removelist:
        os.remove(i)

    #render_num = 16
    render_num = 4
    start = int(-render_num / 2) + 1
    end = render_num + start
    degree = 360 / render_num
    panorama_img = skimage.io.imread(im_path)
    coordinates_list = []


    tilelist = render_imgs(panorama_img, tmp_folder, save_directly)
    if not save_directly:
        tilelist = glob.glob(tmp_folder + '*.jpg')
        tilelist.sort()

    hl = []
    hvps = []
    hvp_groups = []
    z = []
    z_group = []
    ls = []
    z_homo = []
    hvp_homo = []
    ls_homo = []

    for i in range(len(tilelist)):
        [tmp_hl, tmp_hvps, tmp_hvp_groups, tmp_z, tmp_z_group, tmp_ls, tmp_z_homo, tmp_hvp_homo, tmp_ls_homo, params] = simon_rectification(tilelist[i], i, inter_Dir, root, tmp_count)
        hl.append(tmp_hl)
        hvps.append(tmp_hvps)
        hvp_groups.append(tmp_hvp_groups)
        z.append(tmp_z)
        z_group.append(tmp_z_group)
        ls.append(tmp_ls)
        z_homo.append(tmp_z_homo)
        hvp_homo.append(tmp_hvp_homo)
        ls_homo.append(tmp_ls_homo)

    # print('get all the zenith points')


    removelist = glob.glob(tmp_folder + '*.jpg')
    for i in removelist:
        os.remove(i)

    ####################### Get all the zenith points from all the (8) viewpoints

    zenith_points = np.array([R_heading(np.pi / 2 * (i - 1)).dot(zenith) for i, zenith in enumerate(z_homo)])
    points2 = np.array([R_heading(np.pi / 2 * (i - 1)).dot(np.array([0., 0., 1.])) for i in range(len(z_homo))])
    hv_points = [(R_heading(np.pi / 2 * (i - 1)).dot(hv_p.T)).T for i, hv_p in enumerate(hvp_homo)]


    if plot_redundant:
        draw_all_vp_and_hl_color(zenith_points, hv_points, im.copy(), root)

        draw_all_vp_and_hl_bi(zenith_points, hv_points, im.copy(), root)
        #draw_zenith_on_top_color(zenith_points, root)
        #draw_zenith_on_top_bi(zenith_points, root)
        draw_sphere_zenith(zenith_points, hv_points, root)



    ####################### Calculate the consensus zenith point

    [zenith_consensus, best_zenith] = calculate_consensus_zp(zenith_points, method='svd')

    # Transform the zenith points back to original homogeneous coordinates
    # zenith_consensus_org = np.array(
    #     [R_heading(-np.pi / 6 * (i - 5)).dot(zenith) for i, zenith in enumerate(zenith_consensus)])
    zenith_consensus_org = np.array([R_heading(-np.pi / 2 * (i - 1)).dot(zenith) for i, zenith in enumerate(zenith_consensus)])



    result_list = []
    for i in range(len(zenith_consensus_org)):

        #result = Pano_hvp.hvp_from_zenith(ls_homo[i], zenith_consensus_org[i], params)

        result = Pano_hvp.get_all_hvps(ls_homo[i], zenith_consensus_org[i], params)
        result_list.append(result)

    hvps_consensus_org = []
    for i in range(len(result_list)):
        # hvps_consensus_org.append(result_list[i]['hvp_homo'])
        hvps_consensus_org.append(result_list[i])

    hvps_consensus_uni = [(R_heading(np.pi / 2 * (i - 1)).dot(hv_p.T)).T for i, hv_p in enumerate(hvps_consensus_org)]

    if plot_redundant:
        draw_consensus_zp_hvps(best_zenith, hvps_consensus_uni, im.copy(), root)


    ####################### Calculate pitch and roll
    pitch = np.arctan(best_zenith[2] / best_zenith[1])
    roll = - np.arctan(best_zenith[0] / np.sign(best_zenith[1]) * np.hypot(best_zenith[1], best_zenith[2]))


    hvps_consensus_rectified = [R_roll(-roll).dot(R_pitch(-pitch).dot(vp.T)).T for vp in hvps_consensus_uni]

    if plot_redundant:
        draw_consensus_rectified_sphere(hvps_consensus_rectified, root)



    ###################### Calculate horizontal VP histogram

    final_hvps_rectified = calculate_histogram(hvps_consensus_rectified, root, plot_redundant)

    # final_hvps_rectified = [np.array([1.,0.,0.]), np.array([0.,0.,1.])]
    # pitch = 0
    # roll = 0


    # rrd = np.random.rand() * np.pi
    # final_hvps_rectified = [np.array([np.sin(rrd), 0., np.cos(rrd)]), np.array([np.sin(np.pi/2 + rrd), 0., np.cos(np.pi/2 + rrd)])]
    # pitch = 0
    # roll = 0




    # Test whether the main vanishing point is near 90 degrees to the second vanishing point

    # if len(final_hvps_rectified) == 2:
    #     hvp1 = final_hvps_rectified[0]
    #     hvp2 = final_hvps_rectified[1]
    #     if np.abs(hvp1.dot(hvp2)) > np.sin(np.radians(5)):
    #         final_hvps_rectified = [final_hvps_rectified[0]]

    if plot_redundant:
        draw_center_hvps_rectified_sphere(np.array(final_hvps_rectified), root)
        draw_center_hvps_on_panorams(best_zenith, np.array(final_hvps_rectified), im.copy(), pitch, roll, root)



    # Draw rectified panorama

    # from Panos.Pano_new_pano import create_new_panorama, draw_new_panorama
    # if plot_redundant:
    #     new_pano_path = create_new_panorama(im_path, pitch, roll, root)
    #     draw_new_panorama(new_pano_path, np.array(final_hvps_rectified), root)



    ###################### Rendering images from panoramas

    project_facade_for_refine(np.array(final_hvps_rectified), im.copy(), pitch, roll, im_path, root, tmp_folder, rendering_img_base, tmp_count)
    now_time = time.perf_counter()
    cost = now_time - start_time 
    cost_h = int(cost // 3600)
    cost_m = int((cost - cost_h * 3600) // 60)
    cost_s = int(cost - cost_h * 3600 - cost_m * 60)
    predict = (img_sum - img_num) * ((now_time - start_time) / img_num)
    predict_h = int(predict // 3600)
    predict_m = int((predict - predict_h * 3600) // 60)
    predict_s = int(predict - predict_h * 3600 - predict_m * 60)
    print(f'=finish processing:{img_num}/{img_sum} {im_path}  \n'
            f'=total time cost：{cost_h}h{cost_m}m{cost_s}s  \n'
            f'=last image cost：{round(now_time - temp_time, 2)}s  \n'
            f'=average time per image：{round(cost / img_num, 2)}s \n'
            f'=still need：{predict_h}h{predict_m}m{predict_s}s')
    temp_time = now_time

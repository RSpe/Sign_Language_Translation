#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Aug 16 16:50:15 2020

@author: tim

tf hub test

# get started https://www.tensorflow.org/hub. MUST have tensorflow >= 2.2 for tf hub efficientnet model to work!
!pip install tensorflow_hub
!pip install tensorflow

Must run this file from the subdir ..../Sign_Language_Translation/models

"""

import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import matplotlib.pyplot as plt
import cv2
import sys

import cs760    #opencv based utils for vid / image manipulation


if sys.platform == 'win32':
    #sys.path.append('../tests')
    filedir = 'C:/Users/timha/OneDrive/Documents/uni/760 Data Mining and Machine Learning/GroupProj'
    outdir = 'C:/tmp'
else:
    #sys.path.append('/home/tim/OneDrive/gitrepos/tests')
    filedir = '/media/tim/dl3storage/Datasets/asllrp'    
    outdir = '/media/tim/dl3storage/tmp'

vid = 'Liz_10.mov'
bs = 40              #batch size


# quick tf test #######################################
a  = np.random.randn(100,200,40,3)

b = tf.constant(a, dtype=tf.float32)
b.device  #prints CPU but might be a bug and actually be on gpu?
#c = b.gpu()
#c.device
e = b*2
e.device # now should print a gpu device like '/job:localhost/replica:0/task:0/device:GPU:0'

del a
del b
del e  
# end tf test #########################################

# test vid ################################################

vid_np = cs760.get_vid_frames(vid, 
                  filedir, 
                  outdir,
                  writejpgs=False,
                  writenpy=False,
                  returnnp=True)

print(vid_np.shape, vid_np.dtype)
plt.imshow(vid_np[4])
print(vid_np[4, 75, 135])

batch = cs760.resize_batch(vid_np, width=600, height=600, pad_type='L',
                           inter=cv2.INTER_AREA, BGRtoRGB=False, 
                           simplenormalize=True,
                           imagenetmeansubtract=False)
print(batch.shape, batch.dtype)
plt.imshow(batch[4])
print(batch[4, 75, 135])


# tf hub test ########################
module_url = "https://tfhub.dev/tensorflow/efficientnet/b7/feature-vector/1"   #EfficientNet b7 model expects input 600x600

model = hub.KerasLayer(module_url)  # can be used like any other kera layer including in other layers...

batch_tf = tf.constant(batch[:bs], dtype=tf.float32)  # convert to tf (got OOM when tried to run all 128 frames through at once. 40 works ok)

# NOTE to train end-to-end I think setting model.trainable = True will work
features = model(batch_tf)   # Returns features with shape [batch_size, num_features].
print(features.shape)  #(batch_size, 2560)


# run a whole vid though model
fullfeatures_tf = tf.zeros((0, 2560), dtype=tf.float32)
for i in range(bs, batch.shape[0], bs):
    print(i-bs, i)
    batch_tf = tf.constant(batch[i-bs:i], dtype=tf.float32)  # convert to tf
    features = model(batch_tf)
    print(features[0], features[-1])
    fullfeatures_tf = tf.concat([fullfeatures_tf, features], axis=0)
if batch.shape[0] - i > 0:
    print(i, i + (batch.shape[0] - i))
    batch_tf = tf.constant(batch[i:i+(batch.shape[0]-i)], dtype=tf.float32)  # convert to tf
    features = model(batch_tf)
    fullfeatures_tf = tf.concat([fullfeatures_tf, features], axis=0)

print(fullfeatures_tf.shape)





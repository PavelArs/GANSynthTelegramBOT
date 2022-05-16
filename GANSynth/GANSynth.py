import sys
import os

sys.path.append('C:/Users/Pro10/Documents/GitHub/GANsynth-pytorch')
# sys.path.append('C:\\Users\\Pro10\\genaud')
# sys.path.append('C:\\FFmpeg\\bin')
import random
import soundfile as sf
from PIL import Image
from PGGAN import *
import torch
import torch.optim as optim
import torch.backends.cudnn as cudnn
import torchvision.utils as vutils
import librosa.display

import torch.utils.data as udata
import torchvision.datasets as vdatasets
import torchvision.transforms as transforms
from sklearn.model_selection import train_test_split
import h5py

import matplotlib.pyplot as plt
import spec_ops as spec_ops
import phase_operation as phase_op
import spectrograms_helper as spec_helper
from IPython.display import Audio
from normalizer import DataNormalizer

from tqdm import tqdm


g_net = Generator(256, 256, 2, is_tanh=True,channel_list=[256,256,256,256,256,128,64,32])
g_checkpoint = torch.load('C:\\Users\\Pro10\\Gnet_128x1024_step188.pth')

g_net.load_state_dict(g_checkpoint)
g_net.net_config = [6, 'stable', 1]
g_net.cuda()

def denormalize(spec, IF, s_a, s_b, p_a, p_b):
    spec = (spec -s_b) / s_a
    IF = (IF-p_b) / p_a
    return spec, IF

def polar2rect(mag, phase_angle): #
    """Convert polar-form complex number to its rectangular form."""
    #     mag = np.complex(mag)
    temp_mag = np.zeros(mag.shape,dtype=np.complex_)
    temp_phase = np.zeros(mag.shape,dtype=np.complex_)

    for i, time in enumerate(mag):
        for j, time_id in enumerate(time):
            ##print(mag[i,j])
            temp_mag[i,j] = np.complex(mag[i,j])
            ##print(temp_mag[i,j])

    for i, time in enumerate(phase_angle):
        for j, time_id in enumerate(time):
            temp_phase[i,j] = np.complex(np.cos(phase_angle[i,j]), np.sin(phase_angle[i,j]))
    #             print(temp_mag[i,j])

    #     phase = np.complex(np.cos(phase_angle), np.sin(phase_angle))

    return temp_mag * temp_phase

def mag_plus_phase(mag, IF):

    mag =  np.exp(mag) - 1.0e-6
    reconstruct_magnitude = np.abs(mag)

    # mag =  np.exp(mag) - 1e-6
    # reconstruct_magnitude = np.abs(mag)


    reconstruct_phase_angle = np.cumsum(IF * np.pi, axis=1)
    stft = polar2rect(reconstruct_magnitude, reconstruct_phase_angle)
    inverse = librosa.istft(stft, hop_length = 512, win_length=2048, window = 'hann')

    return inverse

def output_file(model,fake_seed, pitch):
    fake_pitch_label = torch.LongTensor(1, 1).random_() % 128
    pitch = [[pitch]]
    fake_pitch_label = torch.LongTensor(pitch)
    fake_one_hot_pitch_condition_vector = torch.zeros(1, 128).scatter_(1, fake_pitch_label, 1).unsqueeze(2).unsqueeze(3).cuda()
    fake_pitch_label = fake_pitch_label.cuda().squeeze()
    # generate random vector
#     fake_seed = torch.randn(1, 256, 1, 1).cuda()
    fake_seed_and_pitch_condition = torch.cat((fake_seed, fake_one_hot_pitch_condition_vector), dim=1)
    output = model(fake_seed_and_pitch_condition)
    output = output.squeeze()

    spec = output[0].data.cpu().numpy().T
    IF = output[1].data.cpu().numpy().T
    spec, IF = denormalize(spec, IF, s_a=0.060437, s_b=0.034964, p_a=0.0034997, p_b=-0.010897)
    back_mag, back_IF = spec_helper.melspecgrams_to_specgrams(spec, IF)
    back_mag = np.vstack((back_mag,back_mag[1023]))
    back_IF = np.vstack((back_IF,back_IF[1023]))
    audio = mag_plus_phase(back_mag,back_IF)
    return audio


def generate_aud(lowest_key_note=85, highest_key_note=110, BPM=60, composition_length=10, disc_rate=16000,
                 title='Default'):
    if (composition_length <= 0):
        print('Composition length should be positive')
        return
    if (lowest_key_note >= 127 or lowest_key_note <= 0):
        print('Lowest key note should be in range from 0 to 127')
        return
    if (highest_key_note >= 127 or highest_key_note <= 0):
        print('Highest key note should be in range from 0 to 127')
        return
    if (disc_rate <= 0):
        print('Discritization rate should be positive')
        return
    if (highest_key_note < lowest_key_note):
        highest_key_note, lowest_key_note = lowest_key_note, highest_key_note

    fake_seed = torch.randn(1, 256, 1, 1).cuda()

    list_audio = []

    complength = int(composition_length * disc_rate / 64000) * int(BPM / 15)

    for i in range(complength):
        seed = random.randint(lowest_key_note, highest_key_note)
        ad = output_file(g_net, fake_seed, pitch=seed)
        list_audio.append(ad[:int(960000 / BPM)])

    seed = random.randint(lowest_key_note, highest_key_note)
    remains = composition_length % (int(64000 / disc_rate))
    ad = output_file(g_net, fake_seed, pitch=seed)
    list_audio.append(ad[:int(remains * disc_rate)])

    list_audio = np.hstack(list_audio)
    sf.write(f'C:\\Users\\Pro10\\genaud\\{title}.wav', list_audio, disc_rate, format='WAV')
    print('Generated wav')
    aud = Audio(list_audio, rate=disc_rate)

    return aud
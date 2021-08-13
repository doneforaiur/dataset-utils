#!/usr/bin/env python

from __future__ import unicode_literals
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import youtube_dl
import ffmpeg  
from vosk import Model, KaldiRecognizer
import subprocess
from subprocess import Popen
import wave
import json
from rapidfuzz import fuzz
from rapidfuzz import process
import nltk
import argparse
import os
from os import path
import datetime
import multiprocessing


## dev imports
import sys


def sentence_crop(audio_data, sentences):
    if path.exists("./"+"Kurk_Mantolu_Madonna"+"_sentence") == False:
        os.mkdir("Kurk_Mantolu_Madonna"+"_sentence")

    toplam = 0
    alinan = 0
    commands = []
    for i in range(len(audio_data)):
        print(len(json.loads(audio_data[i])["text"]))
        if json.loads(audio_data[i])["text"] == "" or len(json.loads(audio_data[i])["text"])<15:
            continue
        print(json.loads(audio_data[i])["text"])
        extraction = process.extractOne(json.loads(audio_data[i])["text"], sentences,scorer=fuzz.token_sort_ratio)
        score=extraction[1]
        res=extraction[0]
        hold_num=sentences.index(res)
        print(extraction[1])
        print(res)
        print(score)
        if score > 60:
            print("girdi")
            res_split=res.split()
            last_word=res_split[-1]
            j_sentence_splitted=json.loads(audio_data[i])["text"].split()
            j_hold=json.loads(audio_data[i])["result"][:]
            print(json.loads(audio_data[i])["result"][0]['word'])
            j_first_word=""
            if len(res_split)>len(j_sentence_splitted):
                k=0
                word_score=0
                last_word=json.loads(audio_data[i])["text"].split()[-1]
                while(word_score<80):
                    print(len(json.loads(audio_data[i])["result"][:]),k)
                    if k>=(len(json.loads(audio_data[i])["result"][:])):
                        break
                    else:
                        first_word=process.extractOne(json.loads(audio_data[i])["result"][k]['word'],res_split,scorer=fuzz.token_sort_ratio)
                        k=k+1
                        word_score=first_word[1]
                j_first_word=first_word  #son ekleme
                first_word_ind=res_split.index(first_word[0])
                res=" ".join(res_split[first_word_ind:len(res_split)])  
            else:
                j_first_word=process.extractOne(res_split[0], j_sentence_splitted,scorer=fuzz.token_sort_ratio)
                first_word=process.extractOne(j_first_word[0],res_split,scorer=fuzz.token_sort_ratio)       
                first_word_ind=res_split.index(first_word[0])
                res=" ".join(res_split[first_word_ind:len(res_split)])             
            print(json.loads(audio_data[i])["text"])
            print(first_word)
            print(last_word)    

            ss_old=0
            end=0
            ss_old=0
            start=0
            start = json.loads(audio_data[i])["result"][0]["start"]
            end = json.loads(audio_data[i])["result"][-1]["end"]
            if j_first_word!="":
                for j in j_hold:
                    if j['word']==j_first_word[0]:
                        start=j["start"]
                        print("start için seçilen kelime",j['word'])
            for j in j_hold:
                ss=fuzz.token_sort_ratio(last_word,j['word'])
                print(ss,ss_old)
                if ss>ss_old:
                    end=j['end']
                    print(j['word'])
                    ss_old=ss


            alinan += 1
            with open('readme.txt','a') as f:
                f.write(str(alinan)+".wav" + str(score) + res)
                f.write("\n")
            f.close()
            commands.append(["ffmpeg", "-i" ,"{}".format(audio_path), "-ss", "{}".format(start), "-t" ,"{}".format(end-start) ,"./{}_sentence/{}-{}.wav".format("Kurk_Mantolu_Madonna","crop",alinan), "-hide_banner", "-y"])
            if len(commands) > 1:#multiprocessing.cpu_count()*1:
                procs = [Popen(i) for i in commands]
                for p in procs:
                    print("Started")
                    p.wait()
                commands = []

        toplam += 1
    procs = [Popen(i) for i in commands] 
    print("Toplam bulunan; ", alinan)
    print("Toplam cümle; ", toplam)

def epub2thtml(epub_path):
    book = epub.read_epub(epub_path)
    chapters = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            chapters.append(item.get_content())
    return chapters

def chap2text(chap):

    blacklist = ['[document]', 'noscript', 'header', 'html', 'meta', 'head','input', 'script']
    output = ''
    soup = BeautifulSoup(chap, 'html.parser')
    text = soup.find_all(text=True)
    for t in text:
        if t.parent.name not in blacklist:
            output += '{} '.format(t)
    return output

def thtml2ttext(thtml):
    Output = []
    for html in thtml:
        text =  chap2text(html)
        Output.append(text.replace("\n ", "").replace("\r", "").replace("\'", "'"))
    return Output

def epub2text(epub_path):
    chapters = epub2thtml(epub_path)
    ttext = thtml2ttext(chapters)
    return ttext


def audio2text(audio):
    model = Model("./model")
    wf = wave.open(audio)
    rec = KaldiRecognizer(model, 16000)
    rec.SetWords(True)
    frames = wf.getnframes()
    frame_size = 4000
    print(frames)
    results = []

    current_frame = 0
    while True:
        print(current_frame, "/", frames)
        current_frame += frame_size
        data = wf.readframes(frame_size)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            results.append(rec.Result())
        #else:
        #    rec.PartialResult()
    return results


#audio_input = ffmpeg.input("Kurk_Mantolu_Madonna" + ".wav")
#audio_cut = audio_input.audio.filter('atrim', duration=60*10)
#audio_output = ffmpeg.output(audio_cut, "Kurk_Mantolu_Madonna" + '_crop.wav', loglevel="quiet").overwrite_output()
#ffmpeg.run(audio_output)
#os.rename("Kurk_Mantolu_Madonna" + "_crop.wav", "Kurk_Mantolu_Madonna" + ".wav")

# downsample
#subprocess.check_call(args=["ffmpeg", "-i" ,"{}".format("Kurk_Mantolu_Madonna" + ".wav"), "-vn", "-ar", "16000", "-ac","1", "{}".format("Kurk_Mantolu_Madonna" + "_convert.wav"), "-hide_banner", "-y"])

#os.rename("Kurk_Mantolu_Madonna"+ "_convert.wav", "Kurk_Mantolu_Madonna" + ".wav")


audio_path = "Kurk_Mantolu_Madonna.wav"
epub_path = "Kurk_Mantolu_Madonna.epub"
audio_data = audio2text(audio_path)
text_data = epub2text(epub_path)



text = []
for data in text_data:
    text.extend(data)
text = "".join(text).replace("\n", "")
words = nltk.sent_tokenize("".join(text))    
#words=words[30:len(words)]
#print(words)
#print(audio_data)
text_mix_holder=[]
for i in range(0,len(words)-8):
    for j in range(0,8):
        text_mix_holder.append("".join(words[i:i+j]))
with open('words.txt','a') as f:
    for aa in text_mix_holder:
        f.write(aa)
        f.write("\n")
f.close()
with open('audio.txt','a') as f:
    for aa in audio_data:
        f.write(json.loads(aa)["text"])
        f.write("\n")
f.close()
sentence_crop(audio_data, text_mix_holder)

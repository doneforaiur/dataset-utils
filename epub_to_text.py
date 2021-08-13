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
from tqdm import tqdm

## dev imports
import sys


parser = argparse.ArgumentParser(description="Combine Audiobooks' and E-books' sentence for sentence. It is required to supply an EPUB version and a YouTube link to your AudioBook.")
parser.add_argument('-f', '--file_name', type=str, default='', help='Name of file. (If you have an EPUB file named "Little_Prince.epub" you should only supply the "Little_Prince" part as input.)')
parser.add_argument('-l', '--link', default="", help='Supply the AudioBook\'s link directly.')
parser.add_argument('-d', '--duration', type=int, default=0, help='Trim audio for testing. (in minutes)')
parser.add_argument('-v', '--verbose', default=False, help='If selected prints progress.')
parser.add_argument('-p', '--model_path', default="./model", help='Path to a custom VOSK model.')
parser.add_argument('-m', '--multiple_books_path',type=str, default='', help='The path to a TXT file containing EPUBs\' names and a YouTube links side by side.')


def download_wav(args):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'outtmpl': args.file_name + '.%(ext)s'
    }
    if path.exists(args.file_name + ".wav") == False:
        if args.link != "":
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([args.link])

        elif path.exists(args.file_name+".txt"): 
            file = open(args.file_name+".txt", "r")
            link = file.readline()
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([link])
            file.close()
        else:
            print("A .txt file containing link or --link argument weren\'t provided.")


    if args.duration != 0:
        print("Cropping audio to {} minutes.".format(args.duration))
        audio_input = ffmpeg.input(args.file_name + ".wav")
        audio_cut = audio_input.audio.filter('atrim', duration=60*args.duration)
        audio_output = ffmpeg.output(audio_cut, args.file_name + '_crop.wav', loglevel="quiet").overwrite_output()
        ffmpeg.run(audio_output)
        os.rename(args.file_name + "_crop.wav", args.file_name + ".wav")
    
    # downsample
    subprocess.check_call(args=["ffmpeg", "-i" ,"{}".format(args.file_name + ".wav"), "-vn", "-ar", "16000", "-ac","1", "{}".format(args.file_name + "_convert.wav"), "-hide_banner", "-y"])

    os.rename(args.file_name + "_convert.wav", args.file_name + ".wav")
    
    return args.file_name + ".wav"

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
    model = Model(args.model_path)
    wf = wave.open(audio)
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)
    frames = wf.getnframes()
    frame_size = wf.getframerate()
    results = []

    current_frame = 0
    for _ in tqdm(range(int(frames / 500))):
        data = wf.readframes(500)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            results.append(rec.Result())
    
    return results


## for future multiprocess pooling
def crop(file_name, start, duration, crop_type, index):
	process = Popen("ffmpeg", "-i" ,"{}".format(file_name), "-ss", "{}".format(start), "-t" ,"{}".format(duration) ,"./{}_{}/{}.wav".format(file_name,crop_type, index), "-hide_banner", "-y")
	return process.wait()


def sentence_crop(audio_data, sentences):
    if path.exists("./"+args.file_name+"_sentence") == False:
        os.mkdir(args.file_name+"_sentence")

    f = open(args.file_name+"_index.txt", "a")

    toplam = 0
    alinan = 0
    commands = []
    for i in tqdm(range(len(audio_data))):
        text = json.loads(audio_data[i])["text"]
        if text == "":
            continue
        ext1 = process.extractOne(text, sentences, scorer=fuzz.ratio)
        ext2 = process.extractOne(text, sentences, scorer=fuzz.token_set_ratio)
        if ext1 != None  and (ext1[0] == ext2[0]):
            
            start = json.loads(audio_data[i])["result"][0]["start"]
            end = json.loads(audio_data[i])["result"][-1]["end"]

            alinan += 1
            commands.append(["ffmpeg", "-i" ,"{}".format(audio_path), "-ss", "{}".format(start), "-t" ,"{}".format(end-start) ,"./{}_sentence/{}.wav".format(args.file_name,alinan), "-hide_banner", "-y", "-loglevel", "quiet"])
            f.write(str(alinan) +" "+ str(ext1[1]) +" " +ext1[0] +"\n")
            if len(commands) > multiprocessing.cpu_count()*2:
                procs = [Popen(i) for i in commands]
                for p in procs:
                    p.wait()
                commands = []
        toplam += 1

    procs = [Popen(i) for i in commands]
    print("Toplam bulunan; ", alinan)
    print("Toplam cümle; ", toplam)


def word_crop(audio_data, sentences):
    if path.exists("./"+args.file_name+"_word") == False:
        os.mkdir(args.file_name+"_word")
    
    toplam = 0
    for i in range(len(audio_data)):
        if json.loads(audio_data[i])["text"] == "":
            continue
        result = json.loads(audio_data[i])["result"]

        commands = []
        for word in result:
            start = word["start"]
            end   = word["end"]
            start = datetime.timedelta(seconds=start)
            end   = datetime.timedelta(seconds=end)
            duration = str(end-start)
            start = str(start)
            
            toplam += 1        
            commands.append(["ffmpeg", "-i" ,"{}".format(audio_path), "-ss", "{}".format(start), "-t" ,"{}".format(duration) ,"./{}_word/{}-{}.wav".format(args.file_name,word["word"], toplam), "-hide_banner", "-y"])
            if len(commands) > multiprocessing.cpu_count()*2:
                procs = [Popen(i) for i in commands]
                for p in procs:
                    p.wait()
                commands = []


if __name__ == "__main__":

    args = parser.parse_args()
    if args.multiple_books_path !=  '':
        books = []
        with open(args.multiple_book_path) as openfileobject:
            for line in openfileobject:
                books.append(line)
        info = []
        for book in books:
            info.append(book.split())

    elif args.file_name != '':
        with open(args.file_name+'.txt') as yt_link:
            link = yt_link.readline()
        info = [[args.file_name, link]]
    
    else:
        print("Supply multiple_book_path or file_name.")

    audio_path = download_wav(args)
    print("Downloaded and converted to .WAV")
    audio_data = audio2text(audio_path)
    print("Extracted speech data from .WAV")
    epub_path  = args.file_name + ".epub"
    text_data  = epub2text(epub_path)
    print("Converted .EPUB to text")

    # TODO: manual olarak seçme
    text = []
    text.extend(text_data[8])
    text.extend(text_data[9])
    text.extend(text_data[10])
    text.extend(text_data[5])

    text = "".join(text).replace("\n", "").replace("\t", "").replace("  ", " ")
    words = nltk.sent_tokenize("".join(text))
    print("Sentences count; " + str(len(words)))

    sentence_crop(audio_data, words)

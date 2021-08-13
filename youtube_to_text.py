#!/usr/bin/env python

from tqdm import tqdm
from vosk import Model, KaldiRecognizer
import youtube_dl
import wave
import os
import json
from subprocess import Popen
import multiprocessing
from readchar import readkey
from fileinput import FileInput
from zipfile import ZipFile


def download(index, link):
    ydl_opts = {'format': 'bestaudio/best', 
                'postprocessors':[{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '192'
                    }],
                'outtmpl':  index + '.%(ext)s',
                }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download(link)
    filepath =  index + ".wav"
    tempfile = "temp_"+index+".wav"
    Popen(["ffmpeg", "-i",filepath, "-ac", "1" ,"-ar" ,"16000", tempfile ,"-hide_banner" ,"-loglevel", "quiet" ,"-y"]).wait()
    os.rename(tempfile,filepath)
    return filepath




def stt(audio):
    model = Model("./model")
    wf = wave.open(audio)
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    results = []

    for _ in tqdm(range(int(wf.getnframes()/4000)), desc="VOSK"):
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        elif rec.AcceptWaveform(data):
            results.append(rec.Result())

    return results




def crop_sent(index,sentences, audio_path):
    commands = []
    f = open("index.txt", "a")
    for sentence in tqdm(sentences):
        sentence = json.loads(sentence)
        if sentence["text"] == "":
            continue

        start = sentence["result"][0]["start"]
        end   =sentence["result"][-1]["end"]

        commands.append(["ffmpeg", "-i" ,"{}".format(audio_path), "-ss", "{}".format(start), "-t" ,"{}".format(end-start) ,"data/{}.wav".format(index), "-hide_banner","-loglevel", "quiet","-nostdin", "-y"])
        f.write(str(index) +" "+ sentence["text"] + "\n")

        if len(commands) > multiprocessing.cpu_count()*2:
            procs = [Popen(i) for i in commands]
            for p in procs:
                p.wait()
            commands = []
        index += 1
    
    if len(commands) != 0:
        procs = [Popen(i) for i in commands]
        for p in procs:
            p.wait()

    os.remove(audio_path)
    return index



def check_sent(index, sentence):
    choice = ''
    #os.system("clear")
    print()
    print("   ", sentence.replace("\n", "").strip())
    print()
    print("     [A] Accept | [D] Delete | [E] Edit | [R] Replay | [K] Quit")

    p = Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "data/{}.wav".format(index)]) 

    while True:
        choice = readkey()
        if choice == "r":
            p.terminate()
            p = Popen(["ffplay", "-nodisp", "-autoexit","-loglevel", "quiet", "data/{}.wav".format(index)]) 
            continue
        elif choice == "a":
            p.terminate()
            os.replace("data/{}.wav".format(index), "accepted/{}.wav".format(index))
            return True
        elif choice == "d":
            p.terminate()
            os.remove("data/{}.wav".format(index))
            return False
        elif choice == "e":
            edit = input("New sentence for this sound: ")
            os.replace("data/{}.wav".format(index), "accepted/{}.wav".format(index))
            return edit
        elif choice == "k":
            p.terminate()
            return 
        else:
            print("Wrong key.")
            continue



def reindex():
    indexs = open("index.txt").readlines()
    reindex = open("new_index.txt", "a")
    new_idx = 0 
    files = os.listdir("accepted")
    for file in files:
        file_index = int(file.split(".")[0])
        os.rename("accepted/{}".format(file), "accepted/{}.wav".format(new_idx))
        text = indexs[file_index].split(" ",1)[1]
        reindex.write(str(new_idx) + " " +  text)
        new_idx += 1

    os.rename("new_index.txt", "index.txt")
   
def zipfiles():
    index = len(os.listdir("zips")) + 1
    with ZipFile("zips/{}.zip".format(index), "w") as zipObj:
        for file in os.listdir("accepted"):
            zipObj.write("accepted/"+file)

        zipObj.write("./accepted_index.txt")

    return
            

if __name__ == "__main__":
    links = open("links.txt")
    links = links.readlines()
    index = 0
    for index,link in enumerate(links):
        file = download(str(index), links)
        res = stt(file)
        print(len(res))
        index = crop_sent(index,res, file)
        
        index_file = open("index.txt", "r").readlines()
        print(len(index_file))
        accepted_index_file = open("accepted_index.txt", "w")
        for line in index_file:
            index = line.split(" ", 1)[0]
            line = line.split(" ", 1)[1]
            resp = check_sent(index, line)
            
            if resp == None:
                break
            if isinstance(resp, str):
                accepted_index_file.write(index + " " + resp+"\n")
            elif resp == True:
                accepted_index_file.write(index + " " + line)
            
    zipfiles() 


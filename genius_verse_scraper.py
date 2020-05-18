# -*- coding: utf-8 -*-
"""
Created on Fri May 15 02:35:39 2020

@author: andrewkn
"""
import requests
from bs4 import BeautifulSoup
import os
import re

base_url = 'https://genius.com/api/page_data/album?page_path=%2Falbums%2F'

#must follow convention from website url 
#i.e. 'https://genius.com/albums/Jay-park/Everything-you-wanted'
artist = 'Jay-park'
album_name = 'Everything-you-wanted'
num_songs = 19 #num of songs to scrape from tracklist

complete_url = base_url + artist + '%2F' + album_name

response = requests.get(complete_url)

json = response.json()

artist_dict = {}
info = []

#finds the verse identifier in the lyrics
def find_verse_id_start(lyrics, search_start, song_end):
    starters = ['[Verse', '(Verse']
        
    for i in range(len(starters)):
        index = lyrics.find(starters[i], search_start, song_end)
        if index != -1:
            return index
        
    return -1 #no more verses to find
   
#finds the verse identifier ending
def find_verse_id_end(lyrics, verse_start, song_end):
    endings = [']', ')']
    
    for i in range(len(endings)):
        index = lyrics.find(endings[i], verse_start + 1, song_end)
        if index != -1:
            return index
   
#finds the end of the verse in the lyrics     
def find_verse_end(lyrics, verse_index, song_end):
    verse_end = lyrics.find('[', verse_index + 1, song_end)
    
    if verse_end == -1:
        other_id= ['Hook', 'Chorus', 'Bridge', 'Verse']
        for i in range(len(other_id)):
            verse_end = lyrics.find(other_id[i], verse_index + 1, song_end)
            if verse_end != -1:
                return verse_end
    else:
        return verse_end        

#scrapes verses from the lyrics
def scrape_lyrics(url):
    page = requests.get(url)
    html = BeautifulSoup(page.text, 'html.parser')
    
    #gets the lyrics
    lyrics = html.find('div', class_ = 'lyrics').get_text()
    song_end = len(lyrics)

    #ignore appended english or romanization versions
    stop = ['English (Translated)', 'Romanization']
    stop_scrape = 0
    has_stop = False
    
    for i in range(len(stop)):
        if stop[i] in lyrics:
            stop_scrape = lyrics.find(stop[i], 0, song_end)
            
    verse_lyrics = []
    identifiers = []
    
    search_start = 0
    for verse in lyrics:
        
        verse_id_start = find_verse_id_start(lyrics, search_start, song_end)
        
        if verse_id_start != -1 and has_stop == False:
            verse_id_end = find_verse_id_end(lyrics, verse_id_start + 1, 
                                             song_end)
            identifier = lyrics[verse_id_start:verse_id_end + 1]
            verse_end = find_verse_end(lyrics, verse_id_end, song_end)
            search_start = verse_end 
            
            add_verse = True
            #only include verses from the artist 
            if len(identifier) > 10:
                joined = identifier.replace(' ', '').lower()
                artist_name = artist.replace('-', '').lower()
                if artist_name not in joined:
                    add_verse = False
                    
            if add_verse:
                if identifier not in identifiers:
                    identifiers.append(identifier)
                    verse = lyrics[verse_id_start:verse_end]
                    verse_lyrics.append(verse)
            
            if stop_scrape != 0:
                if search_start > stop_scrape:
                    has_stop = True
                    
    return verse_lyrics

#separates english, korean, and korean-english from verses
def separate_languages(lyrics):
    split_verse_lyrics = []
    
    for verse in lyrics:
        #remove verse identifiers
        verse = re.sub(r'[\(\[].*?[\)\]]', '', verse)
        
        #remove empty lines
        verse = os.linesep.join([s for s in verse.splitlines() if s]) 
        verse = verse.splitlines()
        
        eng = []
        kor = []
        konglish = [] #korean-english lyrics
        
        for line in verse:
            eng_words = []
            kor_words = []
        
            string_split = line.split()
            for elem in string_split: 
                eng_sep_char = []
                kor_sep_char = []
                
                #english
                if re.search('[A-Za-z]', elem) != None:
                    for char in elem:
                        if(ord(char) >= 44032 and ord(char) <= 55171):
                            kor_sep_char.append(char)
                        else:
                            eng_sep_char.append(char)

                    eng_word = ''.join(char for char in eng_sep_char)
                    kor_word = ''.join(char for char in kor_sep_char)
                    
                    eng_words.append(eng_word)
                    
                    #if korean characters trail english word
                    if(len(kor_word) != 0):
                        konglish.append(elem)

                #korean
                else:
                    kor_words.append(elem)
        
            #keep english word and korean word spacing
            eng_line = ' '.join(word for word in eng_words)
            kor_line = ' '.join(word for word in kor_words)
        
            eng.append(eng_line)
            kor.append(kor_line)
    
        #remove empty strings from both 
        eng = [a for a in eng if a]
        kor = [a for a in kor if a]
    
        split_verse_lyrics.append((eng, kor, konglish))
        
    return split_verse_lyrics
  
#for set number of songs in album      
for i in range(num_songs):
    
    base_json = json['response']['page_data']['album_appearances'][i]['song']
    excluded_terms = ['REMIX', 'Remix', 'remix', 'Cypher', 'cypher', '(Live)',
                      '(E)']
    title = base_json['title']
        
    ignore = False
    for i in range(len(excluded_terms)):
        contains_excluded = title.find(excluded_terms[i])
        if contains_excluded != -1:
            ignore = True
    
    if ignore == False:
        url = base_json['url']
        lyrics = scrape_lyrics(url)
        if len(lyrics) != 0:
            split_verse_lyrics = separate_languages(lyrics)

            info.append((title, split_verse_lyrics))

artist_dict[album_name] = info

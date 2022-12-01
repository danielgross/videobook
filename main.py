"""Load up book text, and generate a magic videobook, and serve it."""

import os
import re
from flask import Flask, render_template, request
import requests
import logging
from youtube_transcript_api import YouTubeTranscriptApi


APP = Flask(__name__)


# From https://stackoverflow.com/questions/4576077/how-can-i-split-a-text-into-sentences
alphabets = "([A-Za-z])"
prefixes = "(Mr|St|Mrs|Ms|Dr)[.]"
suffixes = "(Inc|Ltd|Jr|Sr|Co)"
starters = "(Mr|Mrs|Ms|Dr|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
websites = "[.](com|net|org|io|gov)"
digits = "([0-9])"
def split_into_sentences(text):
    text = " " + text + "  "
    text = text.replace("\n", " ")
    text = re.sub(prefixes, "\\1<prd>", text)
    text = re.sub(websites, "<prd>\\1", text)
    text = re.sub(digits + "[.]" + digits, "\\1<prd>\\2", text)
    if "..." in text:
        text = text.replace("...", "<prd><prd><prd>")
    if "Ph.D" in text:
        text = text.replace("Ph.D.", "Ph<prd>D<prd>")
    text = re.sub("\s" + alphabets + "[.] ", " \\1<prd> ", text)
    text = re.sub(acronyms+" "+starters, "\\1<stop> \\2", text)
    text = re.sub(alphabets + "[.]" + alphabets + "[.]" +
                  alphabets + "[.]", "\\1<prd>\\2<prd>\\3<prd>", text)
    text = re.sub(alphabets + "[.]" + alphabets +
                  "[.]", "\\1<prd>\\2<prd>", text)
    text = re.sub(" "+suffixes+"[.] "+starters, " \\1<stop> \\2", text)
    text = re.sub(" "+suffixes+"[.]", " \\1<prd>", text)
    text = re.sub(" " + alphabets + "[.]", " \\1<prd>", text)
    if "”" in text:
        text = text.replace(".”", "”.")
    if "\"" in text:
        text = text.replace(".\"", "\".")
    if "!" in text:
        text = text.replace("!\"", "\"!")
    if "?" in text:
        text = text.replace("?\"", "\"?")
    text = text.replace(".", ".<stop>")
    text = text.replace("?", "?<stop>")
    text = text.replace("!", "!<stop>")
    text = text.replace("<prd>", ".")
    sentences = text.split("<stop>")
    sentences = sentences[:-1]
    sentences = [s.strip() for s in sentences]
    return sentences


def get_book_sentences():
    """Get the book file, and tokenize it."""
    text = open('caesar-and-christ.txt', encoding = "utf-8").read()
    sentences = split_into_sentences(text)
    return sentences[5004:10000] # TODO: generalize this


@APP.route('/')
def index():
    """Serve the index page."""
    sentences = get_book_sentences()
    logging.info("Loaded sentences: %s", sentences)
    return render_template('index.html', sentences=sentences)


@APP.route('/image')
def image():
    """Serve the image page."""
    prompt = request.args.get('prompt')
    results = requests.get(
        'https://lexica.art/api/v1/search', params={'q': prompt})
    logging.info("Requesting image for prompt: %s", prompt)
    if results.status_code != 200:
        logging.info("Requested URL: %s", results.url)
        logging.info("Content: %s", results.content)
        results.raise_for_status()
    results = results.json()
    if results and results['images']:
        response = {
            'src': results['images'][0]['src'],
            'alt': results['images'][0]['prompt'],
        }
        return response
    return {}


_CACHED_TRANSCRIPTS = {}


@APP.route('/get_youtube_start_time')
def get_youtube_start_time():
    """Given a phrase and a YouTube video, find the start
    time of that phrase in the video by looking at the transcript from YouTube.
    """
    phrase = request.args.get('p')  # a string that's likely a sentence
    youtube_url = request.args.get('yt')
    video_id = youtube_url.split('v=')[1]
    if video_id not in _CACHED_TRANSCRIPTS:
        _CACHED_TRANSCRIPTS[video_id] = YouTubeTranscriptApi.get_transcript(
            video_id)
    transcript = _CACHED_TRANSCRIPTS[video_id]
    phrase = re.sub(r'[^\w\s]', '', phrase)
    phrase_words = ' '.join([x.strip() for x in phrase.split(
        ' ')[:3]]).lower()  # TODO: trigrams or somesuch
    print("Searching for: ", phrase_words)
    for sentence in transcript:
        if phrase_words in sentence['text']:
            print("Found %s in %s" % (phrase_words, sentence))
            return sentence
    return {}


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    APP.run(debug=True, port=5001)

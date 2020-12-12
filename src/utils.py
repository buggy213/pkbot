import html
import re
from itertools import groupby
from operator import itemgetter

import discord
import urllib

def inverse_dictionary_to_embed(title, dictionary, ctx):
    msg = discord.Embed(color=0xff0000, title=title, description=f'requested by {ctx.author.display_name}')
    for k, v in groupby(dictionary.items(), itemgetter(1)):
        msg.add_field(name=str(k), value=str(list(map(itemgetter(0), v))))
    return msg

def dictionary_to_embed(title, dictionary, ctx):
    msg = discord.Embed(color=0xff0000, title=title, description=f'requested by {ctx.author.display_name}')
    for k, v in dictionary.items():
        msg.add_field(name=str(k), value=str(v))
    return msg

def html_to_discord(html_text):
    markdown = html_text.replace('<u>', '__').replace('</u>', '__')
    markdown = markdown.replace('<em>', '*').replace('</em>', '*')
    markdown = markdown.replace('<b>', '**').replace('</b>', '**')
    markdown = markdown.replace('<strong>', '**').replace('</strong>', '**')
    markdown = html.unescape(markdown)
    return markdown

def code_block(string):
    return '```' + string + '```'

def hyperlink(text, url):
    return '[' + text + ']' + '(' + url + ')'

def get_wikipedia_search(answer):
    return f'https://en.wikipedia.org/w/index.php?search={urllib.parse.quote(answer)}'

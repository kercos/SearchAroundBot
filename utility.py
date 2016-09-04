# -*- coding: utf-8 -*-
import re
import logging
import textwrap

from datetime import datetime, timedelta

def representsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def representsFloat(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


re_digits = re.compile('^\d+$')

def hasOnlyDigits(s):
    return re_digits.match(s) != None

def fixWhiteSpaces(s):
    s = re.sub(r'\s+', ' ', s)
    s = s.replace("\xc2\xa0",' ')
    return s

def representsIntBetween(s, low, high):
    if not representsInt(s):
        return False
    sInt = int(s)
    if sInt>=low and sInt<=high:
        return True
    return False

def numberEnumeration(list):
    return [(str(x[0]), x[1]) for x in enumerate(list, 1)]

def letterEnumeration(list):
    return [(chr(x[0] + 65), x[1]) for x in enumerate(list, 0)]  #chd(65) = 'A'

def getIndexIfIntOrLetterInRange(input, max):
    if representsInt(input):
        result = int(input)
        if result in range(1, max + 1):
            return result
    if input in list(map(chr, range(65, 65 + max))):
        return ord(input) - 64  # ord('A') = 65
    return None

def makeArray2D(data_list, length=2):
    return [data_list[i:i+length] for i in range(0, len(data_list), length)]

def distributeElementMaxSize(seq, maxSize=5):
    lines = len(seq) / maxSize
    if len(seq) % maxSize > 0:
        lines += 1
    avg = len(seq) / float(lines)
    out = []
    last = 0.0
    while last < len(seq):
        out.append(seq[int(last):int(last + avg)])
        last += avg
    return out


def segmentArrayOnMaxChars(array, maxChar=20, ignoreString=None):
    #logging.debug('selected_tokens: ' + str(selected_tokens))
    result = []
    lineCharCount = 0
    currentLine = []
    for t in array:
        t_strip = t.replace(ignoreString, '') if ignoreString and ignoreString in t else t
        t_strip_size = len(t_strip.decode('utf-8'))
        newLineCharCount = lineCharCount + t_strip_size
        if not currentLine:
            currentLine.append(t)
            lineCharCount = newLineCharCount
        elif newLineCharCount > maxChar:
            #logging.debug('Line ' + str(len(result)+1) + " " + str(currentLine) + " tot char: " + str(lineCharCount))
            result.append(currentLine)
            currentLine = [t]
            lineCharCount = t_strip_size
        else:
            lineCharCount = newLineCharCount
            currentLine.append(t)
    if currentLine:
        #logging.debug('Line ' + str(len(result) + 1) + " " + str(currentLine) + " tot char: " + str(lineCharCount))
        result.append(currentLine)
    return result

reSplitSpace = re.compile("\s")

def splitTextOnSpaces(text):
    return reSplitSpace.split(text)

def escapeMarkdown(text):
    for char in '*_`[':
        text = text.replace(char, '\\'+char)
    return text

def containsMarkdown(text):
    for char in '*_`[':
        if char in text:
            return True
    return False

def now(addMinutes=0):
    return datetime.now() + timedelta(minutes=int(addMinutes))

def timeString(datetime=now(), ms=False):
    if ms:
        return datetime.strftime('%H:%M:%S.%f')[:-3]
    return datetime.strftime('%H:%M:%S')

def dateString(datetime=now()):
    return datetime.strftime('%d/%m/%y')

def unindent(s):
    return re.sub('[ ]+', ' ', textwrap.dedent(s))
#!/usr/bin/env python
#fileencoding: utf-8
#Author: Liu DongMiao <liudongmiao@gmail.com>
#Created  : Thu 17 Nov 2011 10:24:38 AM CST
#Modified : Thu 17 Nov 2011 11:44:17 AM CST

'''
get destiny from vip.astro.sina.com.cn and post to firebird 2000 bbs
'''

import re
import os
import sys
import time
import errno
import fcntl
import urllib2

# ASTRO = ('aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces')
ASTRO = ('sagittarius', 'capricorn', 'aquarius', 'pisces', 'aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio')
DATA = ('综合运势', '爱情运势', '工作状况', '理财投资', '健康指数', '商谈指数', '幸运颜色', '幸运数字', '速配星座')

def getdata(astro):
    date = time.localtime(time.time() + 86400)
    string = '%s%s%s' % (date.tm_year, date.tm_mon, date.tm_mday)
    url = 'http://vip.astro.sina.com.cn/astro/view/%s/day/%s' % (astro, string)
    content = ''
    try:
        data = urllib2.urlopen(url)
        content = data.read()
        data.close()
    except Exception, error:
        sys.stderr.write(repr(error))
    return content
    # i think i shoud sleep 1 second, otherwise, maybe blocked
    # time.sleep(1)

def parse(content):
    # <li class="datea">有效日期:2011-11-18</li>
    pattern = re.compile('<li class="datea">(.+?)</li>', re.S)
    result = re.findall(pattern, content)
    if not result:
        return False
    if len(result[0].split(':')) != 2:
        return False
    date = result[0].split(':')[1]

    pattern = re.compile('<span>(.+?)<em>(.+?)</em></span>', re.S)
    result = re.findall(pattern, content)
    if not result:
        return False
    title = '%s %s(%s)' % (date, result[0][0], result[0][1].replace(' ', '').replace('-', ' - '))

    context = ''
    for data in DATA:
        pattern = re.compile('<div class="tab"><h4>%s</h4><p>(.+?)</p>' % data, re.S)
        result = re.findall(pattern, content)
        if not result:
            return False
        if 'star.gif' in result[0]:
            context += '%s：%s\n' % (data, '★' * result[0].count('star.gif'))
        else:
            context += '%s: %s\n' % (data, result[0])

    pattern = re.compile('<div class="lotconts">(.+?)</div>', re.S)
    result = re.findall(pattern, content)
    if not result:
        return False
    context += '\n%s' % result[0].strip().replace('\r', '')
    return (title, context)

def getastros():
    astros = []
    for astro in ASTRO:
        content = getdata(astro)
        if not content:
            # try again ...
            sys.stderr.write('try again for %s...' % astro)
            time.sleep(1)
            content = getdata(astro)
            if not content:
                return False
        context = parse(content)
        if not context:
            return False
        astros.append(context)
    return astros

PATH = '/home/bbs/boards'
def _setheader(filename, owner, title):
    title = title.decode('utf8', 'ignore').encode('gbk')
    filename = filename[:78].ljust(78, '\0') + 'LL'
    owner = owner[:80].ljust(80, '\0')
    title = title[:80].ljust(80, '\0')
    return filename + owner + title + '\0' * 16

def _setcontent(board, title, content):
    data = ''
    data += '发信人: thom (爱美人，不爱星座) , 信区: %s\n' % board
    data += '标  题: %s\n' % title
    data += '发信站: 南开人社区 (%s)\n' % time.strftime('%a %b %d %H:%M:%S %Y')
    data += '\n%s\n' % content
    data += '--'
    data += '''
\x1b[1;36m  j&=  \x1b[m y+ y*    jv+   yy-v  \x1b[1;35m  v &  \x1b[m
\x1b[1;36m wE!"  \x1b[m j17$T   7MPC   NU$E- \x1b[1;35m  Ej&v-\x1b[m
\x1b[1;36m O*K^  \x1b[myHH:Ovm+ UMMk   BMNTO:\x1b[1;35m H1="7'\x1b[m
\x1b[1;36mjO&OH: \x1b[m"OH7"E"  U0H1   BB71` \x1b[1;35mjCf'U: \x1b[m
\x1b[1;36mvM1H1  \x1b[m jB-j1  wHhHh*-/$B)B- \x1b[1;35m  BkJUK\x1b[m
\x1b[1;36m^HI'OH \x1b[mj""^N1  "OHOK~  H$H"Da\x1b[1;35m jP'N ^\x1b[m
\x1b[1;36m "`  O|\x1b[m    "    jvHT   T ~ ""\x1b[1;35m    "  \x1b[m
'''
    # http://hiphotos.baidu.com/zhidao/pic/item/d11609248e3a5434d4074225.jpg
    data += '※ 来源:·南开人社区 all.inankai.net·[FROM: 210.51.191.217]'

    return data.decode('utf8', 'ignore').encode('gbk')

def write(name, data):
    pipe = os.open(name, os.O_WRONLY | os.O_CREAT, 0644)
    fcntl.lockf(pipe, fcntl.LOCK_EX)
    if hasattr(os, 'SEEK_END'):
        os.lseek(pipe, 0, os.SEEK_END)
    else:
        os.lseek(pipe, 0, 2)

    size = len(data)
    while True:
        ezis = os.write(pipe, data)
        size -= ezis
        if size <= 0:
            break
        data = data[ezis:]

    fcntl.lockf(pipe, fcntl.LOCK_UN)
    os.close(pipe)

def post(board, title, content):
    boardpath = os.path.join(PATH, board)
    if not os.path.isdir(boardpath):
        raise SystemError('Invalid Board %s' % board)

    _dirpath = os.path.join(boardpath, '.DIR')

    # makesure the filepath
    seconds = time.time()
    while True:
        filename = 'M.%d.A' % (seconds)
        filepath = os.path.join(boardpath, filename)
        try:
            os.stat(filepath)
        except os.error, error:
            if error.errno == errno.ENOENT:
                break
        seconds += 1

    header = _setheader(filename, 'thom', title)
    content = _setcontent(board, title, content)

    try:
        write(filepath, content)
        write(_dirpath, header)
    except Exception, error:
        raise SystemExit('%s' % repr(error))

    return True

def postastro():
    astros = getastros()
    if not astros:
        return False
    for astro in astros:
        sys.stdout.write('%s\n' % astro[0])
        post('Destiny', astro[0], astro[1])

if __name__ == '__main__':
    postastro()

# vim: set sta sw=4 et:

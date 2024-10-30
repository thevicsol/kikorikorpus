from flask import Flask, render_template, request, redirect, url_for
import re

from collections import Counter

app = Flask(__name__)  # инициализируем приложение

char_ids = {}  # словарь с айди персонажей
with open('static/data/char_ids.txt', encoding='UTF-8') as infile:
    for line in infile:  # проходимся по файлу построчно
        lines = line.strip().split('\t')
        char_ids[lines[0]] = lines[1]


text_ids = {}  # словарь с айди текстов
with open('static/data/text_ids.txt', encoding='UTF-8') as infile:
    for line in infile:  # проходимся по файлу построчно
        lines = line.strip().split('\t')
        text_ids[lines[0]] = lines[1]

# считываем список размеченных токенов

with open('static/data/corpus_tagged.txt', encoding='UTF-8') as infile:
    all_tagged_quotes = [threel.split('\n') for threel in infile.read().split('\n\n')]
    all_tagged_quotes = [[line[0].strip().split('\t'), line[1].strip().split('\t'), line[2].strip().split('\t')] for line in all_tagged_quotes]

# считываем список текстов

with open('static/data/corpus_clean.txt', encoding='UTF-8') as infile:
    dialogues = sum([threel.strip().split('\n') for threel in infile.read().split('\n\n')], [])


def search(query):
    if ' ' in query:  # если >1 токена, делим
        query = [elem.strip() for elem in query.split(' ')]
    else:  # иначе список с одним
        query = [query]
    while len(query) != 3:  # добиваем до 3 элементов если меньше 3 токенов
        query.append('')
    q_list = [[False, False, False], [False, False, False], [False, False, False]]  # парметры поиска
    for i in range(len(query)):
        if query[i]:
            if '+' in query[i]:  # если указана часть речи, отделяем ее
                plusplit = query[i].split('+')[1]
                if plusplit[-1] in spacypostags:
                    q_list[i] = [False, False, plusplit.pop()]
                    if len(plusplit) > 1:  # если есть + в регексе, склеиваем весь токен обратно
                        query[i] = '+'.join(plusplit)
                    else:
                        query[i] = plusplit[0]
            if query[i][-1] == '-':  # если указан запрет на пунктуацию, указываем это в параметрах
                query[i] = query[i][:-1]
                q_list[i] = q_list[i] + [False, True]
            if query[i][0] == '_' and query[i][-1] == '_':  # если регекс, указываем это параметром 4
                query[i] = query[i][1:-1]
                if len(q_list[i]) == 3:
                    q_list[i].append(True)
                else:
                    q_list[i][3] = True
            if query[i][0] == '"' and query[i][-1] == '"':
                q_list[i][1] = query[i][1:-1]  # если лемма, указываем как лемму
            else:
                if query[i] in spacypostags:  # если часть речи
                    q_list[i][2] = query[i]
                else:  # если словоформа
                    q_list[i][0] = query[i]
    if len(query) == 1:  # приводим к общему формату если меньше 3 токенов
        q_list = [[], q_list[0], []]
    elif len(query) == 2:
        q_list = [[]] + q_list[:2]
    results = all_tagged_quotes.copy()
    for elem in [1, 0, 2]:  # сначала смотрим серединный токен, потом крайние
        results = sort_out(q_list, elem, results)  # фильтруем вхождения оставляя подходящие
    return [[res[1][3], res] for res in results]  # список списков из номера текста и токенов


def sort_out(queryl, id, sample):
    if queryl[id]:
        if queryl[id][2]:  # меняем часть речи на ее айди
            queryl[id][2] = pos_ids_map[queryl[id][2]]
        for n in range(3):
            if queryl[id][n]:
                if len(queryl[id]) > 3:
                    if queryl[id][3]:  # если регекс, ищем как регекс
                        sample = [samp for samp in sample if re.fullmatch(queryl[id][n], samp[id][n])]
                    else:
                        sample = [samp for samp in sample if samp[id][n] == queryl[id][n]]
                else:
                    sample = [samp for samp in sample if samp[id][n] == queryl[id][n]]
        if len(queryl[id]) > 4:  # если ограничение на пунктуацию, учитываем
            if id != 0:
                sample = [samp for samp in sample if len(samp[id - 1]) == 5]
    return sample


def ngram_join(three):  # функция для склейки токена в 3грамму
    ngram = ''
    for m in range(3):
        if three[m][0] != 'None':
            ngram = ngram + three[m][0]
        if len(three[m]) == 6:
            if three[m][5] == '—':  # пробел перед тире
                ngram = ngram + ' '
            ngram = ngram + three[m][5]
        ngram = ngram + ' '
    while ' .' in ngram:  # убираем случайные пробелы где они не нужны
        ngram = ngram.replace(' .', '.')
    while ' !' in ngram:
        ngram = ngram.replace(' !', '!')
    while ' ?' in ngram:
        ngram = ngram.replace(' ?', '?')
    while ' …' in ngram:
        ngram = ngram.replace(' …', '…')
    return ngram.strip()



spacypostags = ["ADJ", "ADP", "ADV", "AUX", "CONJ", "CCONJ", "DET", "INTJ", "NOUN", "NUM", "PART", "PRON", "PROPN",
                "PUNCT", "SCONJ", "SYM", "VERB", "X", "GER", "PRTCP"]
pos_ids = {}
pos_ids_map = {}
for i in range(len(spacypostags)):  # словарь соответствий тегов чр и айди
    pos_ids[i] = spacypostags[i]
    pos_ids_map[spacypostags[i]] = str(i)


@app.route('/')
def main_page():
    return render_template('index.html')  # стартовая страница

@app.route('/search')
def search_page():
    return render_template('search.html')  # страница с поиском


@app.route('/search_results', methods=['get'])
def search_results():
    if not request.args:
        return redirect(url_for('search_page'))  # если пришли не с поиска, редиректируем
    word1 = request.args.get('word1')
    pos1 = request.args.get('pos1')
    lem1 = request.args.get('lem1')
    reg1 = request.args.get('reg1')
    pun1 = request.args.get('pun1')
    word2 = request.args.get('word2')
    pos2 = request.args.get('pos2')
    lem2 = request.args.get('lem2')
    reg2 = request.args.get('reg2')
    pun2 = request.args.get('pun2')
    word3 = request.args.get('word3')
    pos3 = request.args.get('pos3')
    lem3 = request.args.get('lem3')
    reg3 = request.args.get('reg3')
    pun3 = request.args.get('pun3')  # параметры слов
    if lem1 and word1:  # указываем в запросе что ищем лемму
        word1 = '"' + word1 + '"'
    if reg1 and word1:  # указываем что регекс
        word1 = '_' + word1 + '_'
    if not pun1 and word1:  # указываем что важна пунктуация
        word1 = word1 + '-'
    if pos1 != '':
        if word1:
            word1 = word1 + '+'  # указываем часть речи, ставим + если нужно
        word1 = word1 + pos1
    if lem2 and word2:
        word2 = '"' + word2 + '"'
    if reg2 and word2:
        word2 = '_' + word2 + '_'
    if not pun2 and word2:
        word2 = word2 + '-'
    if pos2 != '':
        if word2:
            word2 = word2 + '+'
        word2 = word2 + pos2
    if lem3 and word3:
        word3 = '"' + word3 + '"'
    if reg3 and word3:
        word3 = '_' + word3 + '_'
    if not pun3 and word3:
        word3 = word3 + '-'
    if pos3 != '':
        if word3:
            word3 = word3 + '+'
        word3 = word3 + pos3
    thequery = ' '.join([word1, word2, word3])  # склеиваем запрос
    thequery = thequery.strip()
    while '  ' in thequery:
        thequery = thequery.replace('  ', ' ')  # убираем пробелы если какие-то токены пропущены
    resids = search(thequery)
    results = []
    epnames = set()  # множество серий
    for resid in resids:
        thetext = []
        for i in range(1, len(dialogues)):  # ищем все фразы в тексте
            if dialogues[i] == resid[0] and not dialogues[i - 1].isnumeric():
                thetext.append([dialogues[i - 1], dialogues[i + 1]])
            if dialogues[i] == str(int(resid[0]) + 1):
                break
        thengram = ngram_join(resid[1])  # искомая нграмма
        textlines = []
        for textline in thetext:
            startid = 0
            endid = 1
            if thengram in textline[0]:
                startid = textline[0].index(thengram)  # позиция нграммы в тексте, чтобы выделить ее жирным
                endid = startid + len(thengram)
            textlines.append({'who': char_ids[textline[1]], 'text1': textline[0][:startid], 'ngram': textline[0][startid:endid], 'text2': textline[0][endid:]})
        epname = text_ids[resid[0]][:text_ids[resid[0]].index('_')]  # название серии
        epnames.add(epname)
        results.append({'name': epname, 'lines': textlines})  # название серии и список фраз диалога/монолога
    return render_template(
        'queryresults.html',
        querytext=thequery,
        results=results,
        epn=len(epnames),  # количество найденных серий
        gramn=len(resids)  # нграмм
    )


if __name__ == '__main__':  # запускаем программу
    app.run(debug=False)

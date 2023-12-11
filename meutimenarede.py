import requests
from bs4 import BeautifulSoup
import pprint
from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import re

uri = "mongodb+srv://devsakae:rodorigo@serverlessinstance0.bciy6lp.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri, server_api=ServerApi('1'))
try:
    client.criciuma.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
db = client.criciuma["jogos"]

def scrape_this(data):
  test = requests.get(data)
  # test.encoding = 'UTF-8'
  return BeautifulSoup(test.text, 'html.parser')

def get_players(data):
  temp = []
  for tr in data[1:]:
    tds = tr.find_all("td")
    temp.append({ "pos": tds[0].text, "num": tds[1].text, "nome": tds[2].text, "url": tds[2].find("a")["href"] })
  return temp

def get_cards(data):
  temp = []
  for tr in data:
    tds = tr.find_all("td")
    color = tds[1].find("span")["class"][0].replace("cartao", "")
    temp.append({ "nome": tds[3].text, "card": color, "url": tds[3].find("a")["href"] })
  return temp

def get_goals(data):
  temp = []
  for tr in data:
    tds = tr.find_all("td")
    minuto, tempo = tds[2].text.replace("'", "").replace("º", "").split("/")
    temp.append({ "autor": tds[1].text, "url": tds[1].find("a")["href"], "pos": tds[0].text, "minuto": int(minuto), "tempo": int(tempo) })
  return temp

def get_subs(data):
  temp = []
  for tr in data:
    tds = tr.find_all("td")
    vetor = re.search(r"(\w+)", tds[1].text)[0]
    minuto, tempo = re.search(r"(\d+\'\/\d+)", tds[1].text)[0].replace("'", "").split("/")
    temp.append({ "pos": tds[0].text, "numero": tds[2].text, "nome": tds[3].text, "vetor": vetor, "minuto": int(minuto), "tempo": int(tempo) })
  return temp

page = 1
while page < 5:
  soup = scrape_this(f'https://www.meutimenarede.com.br/partidas/adversarios/pagina:{page}')
  for item in soup.find("tbody").find_all("tr"):
    td = item.find_all("td")
    imagem = td[0].find("img").attrs["src"].replace("thumbs/2", "zoom")
    nome, uf, j, v, e, d = td[1].text, td[2].text, td[3].text, td[4].text, td[5].text, td[6].text
    moreInfo = scrape_this(item.get("data-link"))
    trJogo = moreInfo.find("table", { "id": "tabelaConfrontos" }).find("tbody").find_all("tr")
    jogos = []
    for tr in trJogo:
      if tr.has_attr("data-link"):
        details = scrape_this(tr.get("data-link"))
        homeScore, awayScore = details.find("h2", { "class": "tit" }).find_all("strong")
        matchInfo = details.find("div", { "class": "col colEsquerda" }).find_all("p")
        campeonato = matchInfo[0].find("a").text
        estadio = matchInfo[1].find("a").text
        roundanddata = re.search(r"(\d+/\d+/\d+)", matchInfo[0].text)[0]
        splittedata = roundanddata.split("/")
        data = f"{splittedata[0][-2:]}/{splittedata[1]}/{splittedata[2]}"
        if re.search(r"(Fase: \d+)", matchInfo[0].text):
          fase = int(re.search(r"(Fase: \d+)", matchInfo[0].text)[0].replace("Fase: ", ""))
          round = int(roundanddata.split("/")[0][:-2])
        if (re.search(r"(Público: \d+)", matchInfo[2].text)):
          publico = re.search(r"(Público: [0-9.,]+)", matchInfo[2].text)[0].replace("Público: ", "")
          renda = re.search(r"(Renda: [0-9.,]+)", matchInfo[2].text)[0].replace("Renda: ", "")
        
        ### HOME TEAM FUNCS
        home = details.find("div", { "class": "col colCentro" })
        homeTeam = home.find("h2").text
        thome_main, thome_subs, thome_goals, thome_cards = home.find_all("tbody")
        pbp_home = thome_main.find_all("tr")
        home_players = get_players(pbp_home[1:])
        home_treinador = pbp_home[0].find("a").text
        home_cards = get_cards(thome_cards.find_all("tr"))
        home_goals = get_goals(thome_goals.find_all("tr"))
        home_subs = get_subs(thome_subs.find_all("tr"))

        ### AWAY TEAM FUNCS
        away = details.find("div", { "class": "col colDireita" })
        awayTeam = away.find("h2").text
        taway_main, taway_subs, taway_goals, taway_cards = away.find_all("tbody")
        pbp_away = taway_main.find_all("tr")
        away_players = get_players(pbp_away[1:])
        away_treinador = pbp_away[0].find("a").text
        away_cards = get_cards(taway_cards.find_all("tr"))
        away_goals = get_goals(taway_goals.find_all("tr"))
        away_subs = get_subs(taway_subs.find_all("tr"))
        
        update = { "campeonato": campeonato, "fase": fase, "rodada": round, "publico": publico, "renda": renda, "homeTeam": homeTeam, "homeScore": int(homeScore.text), "awayTeam": awayTeam, "awayScore": int(awayScore.text), "date": data, "home_treinador": home_treinador, "home_escalacao": home_players, "home_cards": home_cards, "home_goals": home_goals, "home_subs": home_subs, "away_treinador": away_treinador, "away_players": away_players, "away_cards": away_cards, "away_goals": away_goals, "away_subs": away_subs }
        jogos.append(update)
        print(f">> {homeTeam} {homeScore.text} x {awayScore.text} {awayTeam} [{campeonato} - {data}]")
        # break # Quebra o loope aqui RETIRAR EM PRODUÇÃO
    print(f'[SALVANDO {nome}-{uf} NA DATABASE...]')
    # break # Quebra o loop aqui RETIRAR EM PRODUÇÃO
    pprint.pprint(db.insert_one({ "adversario": nome, "uf": uf, "logo": imagem, "resumo": { "j": j, "v": v, "e": e, "d": d }, "jogos": jogos }))
  print(f'Scrapped página {page} com sucesso, aguarde...')
  # break # Quebra o loop aqui RETIRAR EM PRODUÇÃO
  page += 1
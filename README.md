# exposure

## Lyhyt kuvaus

Exposure on sovellus, joka on tehty valokuvien jakamiseen. Monista muista
kuvasovelluksista poiketen, sovellukseen on tarkoitus sisällyttää lähinnä sellaisia
ominaisuuksia, jotka tukevat ammattimaisen tai vakavasti valokuvaukseen suhtautuvan
käyttäjän tarpeita. Erityisesti, pyrkimys on tarjota visuaalisesti minimalistinen
alusta erilaisten valokuvakokoelmien luomiseen.

## Sovelluksen toiminnot

* Käyttäjä pystyy luomaan tunnuksen ja kirjautumaan sisään sovellukseen.
* Käyttäjä pystyy lisäämään, muokkaamaan ja poistamaan omia kuviaan.
* Kuvaan on mahdollista liittää:
  - lyhyt kuvaus
  - tietoja kamerasta, objektiivista sekä näiden asetuksista
  - kommentteja
  - tagejä eli eräänlaisia kuvaan liitettäviä termejä, joiden avulla voi hakea
muita samankaltaisia kuvia
* Kayttäjä pystyy luomaan, muokkaamaan sekä poistamaan omia kuvia sitältäviä kokoelmia
* Kokoelmaan on mahdollista liittää:
  - kuvia
  - otsikko
  - kuvaus
  - mahdollisesti myös kuvien sekaan liitettäviä tekstiosuuksia (tämä vielä epävarma)
* Käyttäjä näkee omat kuvansa sekä kuvakokoelmansa
* Käyttäjä pystyy etsimään muiden käyttäjien kuvia tagien tai kuvausten perusteella
* Käyttäjä pystyy etsimään muiden käyttäjien kokoelmia otsikon tai kuvausten perusteella

Projektin edetessä, sovellukseen saatetaan lisätä myös muita ominaisuuksia.

## Sovelluksen asennus ja käynnistys

Sovellus vaatii Python 3:n sekä `sqlite3`-komentorivityökalun.

Luo virtuaaliympäristö ja ota se käyttöön:

```
$ python3 -m venv venv
$ source venv/bin/activate
```

Asenna `flask`-kirjasto:

```
$ pip install flask
```

Luo tietokanta ja sen taulut:

```
$ sqlite3 database.db < schema.sql
```

Käynnistä sovellus:

```
$ flask run
```

Sovellus on nyt käytettävissä osoitteessa http://127.0.0.1:5000.

## Testien suorittaminen

Testit käyttävät Pythonin omaa `unittest`-kirjastoa sekä Flaskin testiasiakasta, eivätkä ne
koske tiedostoon `database.db` (jokainen testi luo oman väliaikaisen tietokannan). Suorita testit
projektin juurikansiossa virtuaaliympäristön ollessa käytössä:

```
$ python3 -m unittest
```

Mikäli kansio `test_photos` löytyy, testit lähettävät sovellukseen myös sen sisältämän oikean kuvan.

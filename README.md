# exposure

[![CI](https://github.com/thiom/exposure/workflows/CI/badge.svg)](https://github.com/thiom/exposure/actions/workflows/ci.yaml)

## Lyhyt kuvaus

Exposure on sovellus, joka on tehty valokuvien jakamiseen. Monista muista
kuvasovelluksista poiketen, sovellukseen on tarkoitus sisällyttää lähinnä sellaisia
ominaisuuksia, jotka tukevat ammattimaisen tai vakavasti valokuvaukseen suhtautuvan
käyttäjän tarpeita. Erityisesti, pyrkimys on tarjota visuaalisesti minimalistinen
alusta erilaisten valokuvakokoelmien luomiseen.

## Arkkitehtuuri

Katso [arkkitehtuurikuvaus](docs/arkkitehtuurikuvaus/README.md).

## Sovelluksen toiminnot

* Käyttäjä pystyy luomaan tunnuksen ja kirjautumaan sisään sovellukseen.
* Käyttäjä pystyy lisäämään, muokkaamaan ja poistamaan omia kuviaan.
* Kuvaan on mahdollista liittää:
  - lyhyt kuvaus
  - tietoja kamerasta, objektiivista sekä näiden asetuksista
  - kommentteja
  - tägejä eli eräänlaisia kuvaan liitettäviä termejä, joiden avulla voi hakea
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

Sovellus vaatii Python 3.9:n tai uudemman sekä `sqlite3`-komentorivityökalun. Debianissa ja
Ubuntussa tarvitaan lisäksi paketti `python3-venv` (`sudo apt install python3-venv`).
Ohjeet on kirjoitettu macOS:lle ja Linuxille.

### Käynnistys yhdellä komennolla

```
$ ./run.sh
```

Skripti luo tarvittaessa virtuaaliympäristön (`venv`), asentaa Flaskin, luo tietokannan
`database.db` tiedostosta `schema.sql` ja käynnistää sovelluksen osoitteeseen
http://127.0.0.1:5001. Portin voi vaihtaa muuttujalla `PORT` (esim. `PORT=8000 ./run.sh`), ja
Flaskin valinnat välitetään eteenpäin (esim. `./run.sh --debug`).

### Käynnistys käsin

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
$ flask run --port 5001
```

Sovellus on nyt käytettävissä osoitteessa http://127.0.0.1:5001.

## Testien suorittaminen

### Kaikki testit yhdellä komennolla

```
$ ./test.sh
```

Skripti ajaa yksikkötestit, Robot Framework -testit ja pylintin ja asentaa tarvittavat työkalut
virtuaaliympäristöön. Sen voi ajaa myös osissa: `./test.sh unit`, `./test.sh robot` tai
`./test.sh lint`. Yhden testitiedoston voi ajaa antamalla sen nimen, esim.
`./test.sh tests.test_comments`. Jokainen osa asentaa vain omat työkalunsa.

| Osa | Vaatii |
| --- | --- |
| `unit` | Python 3.9 |
| `lint` | Python 3.10 |
| `robot` | Python 3.11 ja `curl` |

Robot-testit käynnistävät oman testipalvelimen porttiin 5002 (vaihdettavissa muuttujalla
`PORT`). Ensimmäisellä kerralla skripti lataa testiselaimen (Chromium). Linuxilla Chromium voi
tarvita järjestelmäkirjastoja, jotka asennetaan sudo-oikeuksin komennolla
`WITH_DEPS=1 ./test.sh robot`.

### Yksikkötestit käsin

Testit käyttävät Pythonin omaa `unittest`-kirjastoa sekä Flaskin testiasiakasta, eivätkä ne
koske tiedostoon `database.db` (jokainen testi luo oman väliaikaisen tietokannan). Suorita testit
projektin juurikansiossa virtuaaliympäristön ollessa käytössä:

```
$ python3 -m unittest
```

Mikäli kansio `test_photos` löytyy, testit lähettävät sovellukseen myös sen sisältämän oikean kuvan.

### Robot Framework -testit

Kansiossa `story_tests` on [Robot Framework](https://robotframework.org/) -testit, jotka
käyttävät sovellusta oikealla selaimella (Browser-kirjasto ja Chromium). Robot Framework on vain
testityökalu, eikä sovellus itse käytä sitä. Asenna testityökalut ja testiselain
virtuaaliympäristöön:

```
$ pip install robotframework robotframework-browser robotframework-browser-batteries
$ rfbrowser install chromium
```

Paketti `robotframework-browser-batteries` tuo mukanaan Browser-kirjaston tarvitseman
Node.js-ympäristön, joten Node.js:ää ei tarvitse asentaa erikseen.

Käynnistä testipalvelin yhdessä terminaalissa. Se käyttää omaa tietokantaansa
`robot_test.db` eikä koske tiedostoon `database.db`:

```
$ python3 story_tests/server.py
```

Aja testit toisessa terminaalissa:

```
$ robot --variable HEADLESS:true story_tests
```

Ilman muuttujaa `HEADLESS:true` selain avautuu näkyviin ja testit etenevät hitaasti, jolloin niitä
voi seurata. Tulokset tallentuvat tiedostoihin `report.html` ja `log.html`.

## Koodin laadun tarkistus

Koodin tyyli tarkistetaan [Pylint](https://pylint.readthedocs.io/)-työkalulla. Pylint on vain
kehitystyökalu, eikä sovellus itse käytä sitä. Asenna se virtuaaliympäristöön ja aja tarkistus
projektin juurikansiossa:

```
$ pip install pylint
$ pylint *.py tests story_tests
```

Asetukset ovat tiedostossa `.pylintrc`. Pylintin oletussäännöistä on poistettu käytöstä vain
tietoiset tyylivalinnat (esimerkiksi docstring-kommenttien puuttuminen), ja jokaiselle on
perustelu tiedostossa.

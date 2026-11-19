# Arkkitehtuurikuvaus

Tämä dokumentti kuvaa, miten sovellus toimii, miten se on toteutettu ja miksi.
Asennus- ja käynnistysohjeet ovat repositorion juuren `README.md`:ssä.

## 1. Yleiskuva

Exposure on Flask-sovellus valokuvien jakamiseen. Käyttäjä lisää kuviaan
(JPEG), liittää niihin kuvauksen, kamera- ja objektiivitiedot sekä tageja ja
kokoaa niistä kokoelmia. Kuvia ja kokoelmia voi selata ja hakea ilman
kirjautumista. Kirjautunut käyttäjä voi myös kommentoida kenen tahansa kuvia.

## 2. Tekniikka

| Osa | Valinta | Peruste |
| --- | --- | --- |
| Web-kehys | Flask 3 | Kurssin vaatimus |
| Tietokanta | SQLite (Pythonin `sqlite3`-moduuli) | Kurssin vaatimus, ei vaadi palvelinta |
| Tietokantakerros | SQL käsin, apufunktiot `db.py`:ssä | Kurssin vaatimus: ei ORM:ää, kuten kurssimateriaalissa |
| Riippuvuudet | Vain Flask (`pip install flask`) | Kurssin vaatimus: ei muita asennettavia Python-kirjastoja |
| Käyttöliittymä | HTML-sivut (Jinja), oma CSS | Kurssin vaatimus: ei JavaScriptiä eikä CSS-kirjastoja |
| Testit | `unittest` + Flaskin testiasiakas | Tulevat Pythonin ja Flaskin mukana, eivät vaadi lisäkirjastoja |
| Koodin tyyli | Pylint, asetukset `.pylintrc`:ssä | Kehitystyökalu, jota sovellus ei käytä ajon aikana (ks. luku 14) |
| CI | GitHub Actions | Testit ja pylint ajetaan jokaisella pushilla (ks. luku 14) |
| Salasanat | `werkzeug.security` (hajautus) | Tulee Flaskin mukana |
| Sumea tagihaku | `difflib.SequenceMatcher` | Pythonin standardikirjasto |

Koodin rakenne ja nimeäminen noudattavat kurssin esimerkkisovellusta
(huutokauppa): moduulit `db.py`, `users.py` jne., reitit `app.py`:ssä, funktiot
`require_login()` ja `check_csrf()` sekä virheet `abort(403)`/`abort(404)` ja
`flash()`-ilmoitukset.

## 3. Hakemistorakenne

```
app.py                  reitit, istunto, lomakkeiden käsittely, Jinja-suodattimet
config.py               istuntojen avain ja tietokantatiedoston polku
db.py                   tietokantayhteys: execute(), query(), last_insert_id()
users.py                käyttäjien luonti ja kirjautumisen tarkistus
photos.py               kuvat, kuvien tiedot (kamera ym.), kommentit, kuvahaku
tags.py                 tagien normalisointi, lisäys, poisto ja sumea haku
photo_collections.py    kokoelmat ja niiden kuvat, kokoelmahaku
schema.sql              tietokannan taulut ja indeksit
.pylintrc               pylintin asetukset
.github/workflows/ci.yaml  GitHub Actions: testit ja pylint
templates/              Jinja-sivupohjat (ks. luku 13)
static/main.css         kaikki tyylit
tests/                  unittest-testit (ks. luku 14)
run.sh                  käynnistys yhdellä komennolla (ei versionhallinnassa)
test.sh                 testien ajo yhdellä komennolla (ei versionhallinnassa)
database.db             kehitystietokanta (ei versionhallinnassa)
test_photos/            testikuvat käsin kokeilua varten (ei versionhallinnassa)
```

Kerrokset: `app.py` käsittelee HTTP:n, istunnon ja lomakkeet. Moduulit
`users.py`, `photos.py`, `tags.py` ja `photo_collections.py` sisältävät SQL:n ja
kutsuvat `db.py`:tä. Reiteissä ei ole SQL:ää. Validointi on enimmäkseen
reiteissä kuten esimerkkisovelluksessa. Kuvan tietojen jäsennys on kuitenkin
`photos.py`:ssä (`parse_details`) ja tagien `tags.py`:ssä (`normalize_title`,
`parse_titles`), koska niitä käytetään useammasta reitistä.

Kokoelmamoduulin nimi on `photo_collections.py` eikä `collections.py`, koska
projektin juuressa oleva `collections.py` peittäisi Pythonin
standardikirjaston `collections`-moduulin, ja silloin Flask lakkaisi toimimasta.

## 4. Asetukset

`config.py`:

| Muuttuja | Merkitys |
| --- | --- |
| `secret_key` | Flaskin istuntoevästeen allekirjoitusavain |
| `database` | SQLite-tiedoston polku, oletuksena `database.db` |

* Asetukset ovat Python-tiedostossa kuten kurssimateriaalissa, eivät
  ympäristömuuttujissa. Avain on siis versionhallinnassa. Kurssiprojektissa
  tämä on hyväksyttävää, mutta julkisessa käytössä avain pitäisi vaihtaa ja
  pitää salassa.
* `db.py` lukee polun `config.database` jokaisella yhteydellä. Testit vaihtavat
  sen väliaikaistiedostoon (ks. luku 14).
* `app.config["MAX_CONTENT_LENGTH"]` on 51 Mt: 50 Mt:n kuva ja 1 Mt lomakkeen
  muille kentille. Suurempi pyyntö hylätään jo ennen kuin sitä luetaan.
* `run.sh` luo tarvittaessa virtuaaliympäristön (`venv/`), asentaa Flaskin, luo
  `database.db`:n `schema.sql`:stä, jos tiedostoa ei ole, ja käynnistää
  komennon `flask run`. Lisäargumentit välitetään Flaskille (esim.
  `./run.sh --debug`).

## 5. Tietokanta

`schema.sql` (lyhennettynä):

```sql
CREATE TABLE users (id, username TEXT UNIQUE, password_hash TEXT);
CREATE TABLE photos (id, user_id REFERENCES users, image BLOB, description TEXT,
                     camera TEXT, lens TEXT, focal_length REAL, aperture REAL,
                     shutter_speed REAL, date_time_added TEXT);
CREATE TABLE tags (id, title TEXT UNIQUE);
CREATE TABLE photo_tags (id, photo_id REFERENCES photos, tag_id REFERENCES tags,
                         UNIQUE (photo_id, tag_id));
CREATE TABLE comments (id, photo_id REFERENCES photos, user_id REFERENCES users,
                       content TEXT, sent_at TEXT);
CREATE TABLE collections (id, user_id REFERENCES users, title TEXT,
                          description TEXT, date_time_added TEXT);
CREATE TABLE collection_photos (id, collection_id REFERENCES collections,
                                photo_id REFERENCES photos, position INTEGER,
                                UNIQUE (collection_id, photo_id));
```

Kaikkien taulujen `id` on `INTEGER PRIMARY KEY`.

* **Kuvat tallennetaan tietokantaan** `BLOB`-sarakkeeseen, kuten
  kurssimateriaalin kuvaesimerkissä. Erillistä tiedostohakemistoa ei
  tarvitse hallita, ja kuvan poisto poistaa myös tiedoston. Listauskyselyt
  hakevat vain `id`:n ja kuvauksen, ja itse kuva haetaan erikseen reitiltä
  `/image/<id>`, joten listaukset eivät lataa kuvadataa muistiin.
* **Tagit ovat oma tauluna** (`tags`), ja kuvat liitetään niihin
  liitostaululla `photo_tags`. `tags.title` on `UNIQUE`, joten samanniminen tagi
  on tietokannassa vain kerran, ja kaikki sitä käyttävät kuvat viittaavat
  samaan riviin.
* **Kokoelmat** liitetään kuviin liitostaululla `collection_photos`. Sarake
  `position` säilyttää kuvien järjestyksen. Sama kuva voi olla useassa
  kokoelmassa, mutta samassa kokoelmassa vain kerran.
* **Kuvan tiedot:** `camera` ja `lens` ovat tekstiä, polttoväli, aukko ja
  suljinaika lukuja (`REAL`). Tyhjä kenttä on `NULL`. Suljinaika tallennetaan
  nimittäjänä: `250` tarkoittaa 1/250 s ja `0.5` kahta sekuntia (ks. luku 8).
* **Ajat** tallennetaan SQLiten funktiolla `datetime('now')` tekstinä muodossa
  `YYYY-MM-DD HH:MM:SS` (UTC). Tämä muoto järjestyy oikein myös tekstinä.
* **Rajoitteet:** Pituudet, määrät ja pakollisuudet tarkistetaan
  sovelluksessa eikä `NOT NULL`- tai `CHECK`-rajoitteilla, kuten
  kurssimateriaalissa. Tietokanta takaa uniikkiuden (`UNIQUE`) ja viiteavaimet:
  `db.py` asettaa jokaiselle yhteydelle `PRAGMA foreign_keys = ON`.
* **Poistot tehdään käsin** oikeassa järjestyksessä eikä `ON DELETE CASCADE`
  -määreillä. Kun kuva poistetaan, `photos.remove_photo()` poistaa ensin sen
  tagiliitokset, kommentit ja kokoelmaliitokset, sitten kuvan, ja lopuksi
  käyttämättömät tagit ja tyhjiksi jääneet kokoelmat (ks. luvut 9 ja 11).

Indeksit:

| Indeksi | Käyttö |
| --- | --- |
| `idx_user_photos` (`photos.user_id`) | my photos, kuvamäärän raja |
| `idx_photos_added` (`photos.date_time_added`) | latest-näkymä |
| `idx_tag_photos` (`photo_tags.tag_id`) | tagin kuvat |
| `idx_photo_comments` (`comments.photo_id`) | kuvan kommentit |
| `idx_collection_photos` (`collection_photos.collection_id`) | kokoelman kuvat ja kansikuva |
| `idx_photo_collections` (`collection_photos.photo_id`) | kuvan poisto |
| `idx_user_collections` (`collections.user_id`) | my collections, kokoelmamäärän raja |
| `idx_collections_added` (`collections.date_time_added`) | latest-kokoelmat |

**Migraatioita ei ole.** Tietokanta luodaan komennolla
`sqlite3 database.db < schema.sql`. Jos skeema muuttuu, vanha tietokanta on
joko luotava uudelleen (data häviää) tai päivitettävä käsin `ALTER TABLE`
-lauseilla. Esimerkiksi vaiheessa 3 lisättiin `collections.date_time_added` ja
kolme indeksiä. Testit eivät huomaa vanhaa tietokantaa, koska ne luovat aina
uuden tietokannan `schema.sql`:stä.

## 6. Reitit

Merkinnät: *login* = vaatii kirjautumisen (muuten 403), *CSRF* = lomakkeen
`csrf_token` tarkistetaan (muuten 403), *oma* = kohteen on oltava kirjautuneen
käyttäjän (muuten 403, olematon kohde 404).

| Reitti | Metodi | Vaatimukset | Toiminta |
| --- | --- | --- | --- |
| `/` | GET | – | Etusivu: hakukenttä keskellä |
| `/search?query=` | GET | – | Kuvahaku. Tyhjä haku ohjaa `/`:hen. Jos tuloksia ei ole, näytetään etusivu ilmoituksella `No photos found` |
| `/latest`, `/latest/<page>` | GET | – | Uusimmat kuvat, 20 sivulla |
| `/collections`, `/collections/<page>` | GET | – | Uusimmat kokoelmat, 20 sivulla. `?query=` hakee kokoelmia |
| `/photo/<id>` | GET | – | Yhden kuvan näkymä. `?back=` kertoo, mihin back-painike palaa |
| `/image/<id>` | GET | – | Kuvadata (`image/jpeg`) |
| `/tag/<id>` | GET | – | Kuvat, joissa on tagi |
| `/collection/<id>` | GET | – | Kokoelman katselu |
| `/my_photos` | GET | login | Omat kuvat |
| `/my_collections` | GET | login | Omat kokoelmat |
| `/new_photo` | GET | login | Kuvan lisäyslomake. Jos 500 kuvan raja on täynnä, ohjataan `/my_photos`:iin |
| `/create_photo` | POST | login, CSRF | Tallentaa kuvan ja ohjaa tagisivulle `/tags/<id>` |
| `/edit_photo/<id>` | GET | login, oma | Muokkausnäkymä |
| `/update_photo` | POST | login, CSRF, oma | Tallentaa kuvauksen ja tiedot |
| `/tags/<id>` | GET | login, oma | Kuvan tagit ja tagien sumea haku (`?query=`) |
| `/add_tag`, `/remove_tag` | POST | login, CSRF, oma | Lisää tai poistaa kuvan tagin |
| `/remove_photo/<id>` | GET / POST | login, oma (+ CSRF) | Vahvistussivu / poisto |
| `/create_comment` | POST | login, CSRF | Lisää kommentin kenen tahansa kuvaan |
| `/new_collection` | GET | login | Aloittaa uuden kokoelman luonnoksen ja ohjaa `/collection_draft`:iin |
| `/edit_collection/<id>` | GET | login, oma | Lataa kokoelman luonnokseksi ja ohjaa `/collection_draft`:iin |
| `/collection_draft` | GET | login | Kokoelman luonti- ja muokkauslomake |
| `/update_collection_draft` | POST | login, CSRF | Lisää, poistaa tai siirtää luonnoksen kuvan tai tallentaa kokoelman |
| `/remove_collection/<id>` | GET / POST | login, oma (+ CSRF) | Vahvistussivu / poisto |
| `/register` | GET | – | Rekisteröintilomake |
| `/create` | POST | – | Luo käyttäjän, kirjaa sisään ja ohjaa `/`:hen |
| `/login` | GET / POST | – | Kirjautumislomake / kirjautuminen |
| `/logout` | GET | – | Kirjaa ulos ja ohjaa `/`:hen |

Sivutetuilla reiteillä liian pieni sivunumero ohjaa sivulle 1 ja liian suuri
viimeiselle sivulle. Kokoelmahaun hakusana säilyy ohjauksessa.

Reitit noudattavat kurssimateriaalin mallia: lomake näytetään GET-reitillä
(`/new_photo`), ja se lähetetään omaan POST-reittiin (`/create_photo`), joka ohjaa
lopuksi toiselle sivulle. Selaimen päivitys ei siis lähetä lomaketta
uudelleen.

## 7. Käyttäjät ja istunto

* **Käyttäjätunnus:** 1–30 merkkiä, ei pelkkiä välilyöntejä. Tunnus on uniikki
  (`UNIQUE`, isot ja pienet kirjaimet erotellaan). Varattu tunnus antaa
  ilmoituksen `Username already in use, pick another one`.
* **Salasana:** 10–30 merkkiä, ja se annetaan kahdesti. Tietokantaan
  tallennetaan vain hajautus (`generate_password_hash`).
* Onnistunut rekisteröinti kirjaa käyttäjän suoraan sisään ja ohjaa etusivulle.
* Kirjautumisvirheen ilmoitus (`Wrong username or password`) on sama väärälle
  tunnukselle ja väärälle salasanalle, joten tunnusten olemassaoloa ei voi
  päätellä.
* **Istunto** on Flaskin allekirjoitettu eväste. Siinä ovat `user_id`,
  `username` ja `csrf_token` sekä tarvittaessa kokoelman luonnos
  `collection_draft` (ks. luku 11). Kirjautuminen ja uloskirjautuminen
  poistavat luonnoksen, jotta se ei siirry toiselle käyttäjälle samassa
  selaimessa.
* **Pääsynhallinta:** `require_login()` vastaa kirjautumattomalle 403, kuten
  esimerkkisovelluksessa. Kirjautumista vaativia sivuja ei näytetä
  kirjautumattomalle yläpalkissa. Omistajuus tarkistetaan funktioilla
  `get_own_photo()` ja `get_own_collection()`: olematon kohde antaa 404 ja toisen
  käyttäjän kohde 403.
* **CSRF:** kirjautuminen luo satunnaisen tunnisteen
  (`secrets.token_hex(16)`), joka on piilokenttänä kaikissa kirjautuneen
  käyttäjän POST-lomakkeissa. `check_csrf()` tarkistaa sen. Kirjautumis- ja
  rekisteröintilomakkeissa tunnistetta ei ole, koska istuntoa ei vielä ole.
* **Uloskirjautuminen** on tavallinen linkki (`GET /logout`), kuten
  esimerkkisovelluksessa.

## 8. Kuvat

### Lisäys (`/new_photo` → `/create_photo`)

* Tiedoston on oltava `.jpg` tai `.jpeg` (pääte kirjainkoosta riippumatta) ja
  enintään 50 Mt, ja sen on alettava JPEG-tunnisteella `FF D8 FF`. Pelkkä pääte
  ei riitä, koska sen voi vaihtaa.
* Kuvaus on pakollinen, 1–200 merkkiä.
* Tagit annetaan valinnaisesti pilkuilla eroteltuina (enintään 20). Lisäyksen
  jälkeen avautuu tagisivu, jolla tageja voi hakea ja lisätä (ks. luku 9).
* Käyttäjällä voi olla enintään 500 kuvaa (`MAX_PHOTOS_PER_USER`).
* Virhetilanteessa palataan lomakkeeseen ilmoituksen kanssa. Selain ei voi
  täyttää tiedostokenttää uudelleen, joten kuva on valittava uudestaan.
  Epäkelpo kuvaus (tyhjä tai liian pitkä) antaa 403, koska lomakkeen
  `required`- ja `maxlength`-määreet estävät sen tavallisessa käytössä.

### Kuvan tiedot (`photos.parse_details`)

| Kenttä | Muoto | Näytetään |
| --- | --- | --- |
| camera | teksti, enintään 50 merkkiä | sellaisenaan |
| lens | teksti, enintään 50 merkkiä | sellaisenaan |
| focal length | luku 1.0–1000.0, enintään 1 desimaali | `50 mm` |
| aperture | luku 1.00–50.00, enintään 2 desimaalia | `f/2.8` |
| shutter speed | luku 0.01–5000.00, enintään 2 desimaalia | `1/250 s`, `2 s` |

* Kaikki kentät ovat valinnaisia. Tyhjä kenttä tallennetaan `NULL`-arvona, eikä
  sitä näytetä kuvan sivulla.
* Luvut tarkistetaan säännöllisellä lausekkeella `^[0-9]{1,4}(\.[0-9]{1,N})?$`
  ennen muunnosta. Näin `1e2`, `inf`, `nan`, negatiiviset luvut ja liian monet
  desimaalit hylätään, vaikka Pythonin `float()` hyväksyisi osan niistä.
  Desimaalipilkku hyväksytään pisteen lisäksi (`35,5`).
* Virheilmoitus nimeää kentän, esim. `Focal length must be a number between 1.0
  and 1000.0 with at most one decimal`.
* **Suljinaika** syötetään nimittäjänä, koska kamerat ilmoittavat lyhyet ajat
  muodossa 1/x: arvo `250` on 1/250 s. Arvot enintään 1 näytetään sekunteina
  (`0.5` → `2 s`). Suodatin `show_shutter_speed` muotoilee arvon, ja
  `show_number` poistaa turhat desimaalit (`50.0` → `50`).
* Tiedot näkyvät vain yhden kuvan näkymässä, eivät listauksissa.

### Yhden kuvan näkymä (`/photo/<id>`)

* Kuva on vasemmalla ja oikeassa palstassa kuvan yläreunasta alkaen `back`,
  kuvaus, tiedot, kuvaaja (`by`), lisäysaika ja tagit. Omistaja näkee lisäksi
  `edit`-painikkeen. Kommentit ovat kuvan alla (ks. luku 10).
* **Back-painike:** listausten kuvalinkit vievät mukanaan oman osoitteensa
  (`?back=/latest/2`), joten back palaa samalle sivulle ja samaan hakuun.
  `get_back_url()` hyväksyy vain sovelluksen sisäiset polut: osoitteen on
  alettava `/`-merkillä, se ei saa alkaa `//` eikä sisältää `\`-merkkiä. Muuten
  palataan etusivulle. Tämä estää käyttämästä parametria ohjaukseen
  ulkopuoliselle sivulle (open redirect).

### Muokkaus ja poisto

* Muokkausnäkymä on muuten sama kuin kuvan näkymä, mutta tietojen alla on
  lomake kuvaukselle ja tiedoille sekä painikkeet `edit tags` ja
  `delete photo`. Itse kuvatiedostoa ei voi vaihtaa.
* Poisto kysyy vahvistuksen omalla sivullaan. Jos kuva on jonkin kokoelman
  ainoa kuva, vahvistussivu luettelee kokoelmat, jotka poistuvat samalla.

## 9. Tagit (`tags.py`)

* **Normalisointi:** tagi muutetaan pieniksi kirjaimiksi, ja peräkkäiset
  välilyönnit yhdistetään. Sallittuja ovat kirjaimet (myös ääkköset), numerot,
  välilyönti ja yhdysmerkki, enintään 20 merkkiä. Näin `Lake`, `lake` ja
  ` LAKE ` ovat sama tagi.
* **Sama nimi, sama tagi:** `add_tag()` lisää tagin lauseella
  `INSERT OR IGNORE`, hakee sen `id`:n nimellä ja liittää sen kuvaan. Olemassa
  olevaa tagia ei siis luoda uudelleen.
* **Poisto:** kun tagi poistetaan kuvasta tai kuva poistetaan,
  `remove_unused_tags()` poistaa tagit, joita mikään kuva ei enää käytä.
* **Kaksivaiheinen lisäys:** lisäyslomakkeessa tagit kirjoitetaan
  pilkuilla eroteltuina, minkä jälkeen avautuu tagisivu `/tags/<id>`. Siellä
  hakukenttä (GET) näyttää olemassa olevia tageja painikkeina, ja
  painike `+ create #tagi` luo uuden. Ilman JavaScriptiä ehdotuksia ei voi
  näyttää kirjoittamisen aikana, joten haku tehdään lomakkeen lähetyksellä.
* **Sumea haku** (`find_tags`): jokaiselle tagille lasketaan samankaltaisuus.
  Alusta täsmäävä tagi saa arvon 1.0 ja tagi, jonka sisällä haku esiintyy,
  arvon 0.9. Muut tagit saavat `difflib.SequenceMatcher`in suhdeluvun (0–1), joka
  sietää kirjoitusvirheitä (`lnadscape` löytää tagin `landscape`). Arvoltaan
  vähintään 0.6 olevat tagit näytetään parhaasta alkaen, enintään 10.
  Vertailu tehdään Pythonissa kaikille tageille. Tagien määrä on pieni, ja
  SQLitessä ei ole valmista sumeaa hakua.
* Tagit ovat aina linkkejä sivulle `/tag/<id>`, jolla näkyvät kaikki tagin
  kuvat uusin ensin.

## 10. Kommentit

* Kirjautunut käyttäjä voi kommentoida omia ja muiden kuvia. Kirjautumaton
  näkee kommentit ja painikkeen `log in to comment`.
* Kommentti on 1–200 merkkiä (alun ja lopun välilyönnit poistetaan).
  Kuvassa voi olla enintään 100 kommenttia, minkä jälkeen lomake korvataan
  ilmoituksella.
* Kommentit näytetään kuvan alla lähetysjärjestyksessä kirjoittajan ja ajan
  kanssa. Rivinvaihdot säilyvät (`white-space: pre-line`), mutta HTML
  escapoidaan kuten kaikki käyttäjän syöte.
* Lähetyksen jälkeen palataan samaan näkymään kohtaan `#comments`: kuvan
  näkymässä `back`-osoite säilyy, ja muokkausnäkymästä lähetetty kommentti
  palaa muokkausnäkymään. Muokkausnäkymän osoite hyväksytään vain, jos se on
  täsmälleen saman kuvan `/edit_photo/<id>`.
* Kommentit poistetaan kuvan mukana.

## 11. Kokoelmat (`photo_collections.py`)

### Säännöt

* Otsikko 1–30 merkkiä (pakollinen), kuvaus enintään 200 merkkiä
  (valinnainen), 1–50 kuvaa. Käyttäjällä voi olla enintään 50 kokoelmaa.
* Kokoelmaan voi lisätä vain omia kuviaan. Tämä tarkistetaan kuvaa lisättäessä
  ja uudelleen tallennettaessa, koska kuva on voinut poistua sillä välin.
* Kansikuva on kokoelman ensimmäinen kuva (`position`-järjestyksessä). Se
  haetaan samassa kyselyssä alikyselynä (`cover_id`).

### Luonti ja muokkaus ilman JavaScriptiä

Ohjeen mukaan kuva siirtyy kokoelmaan `add`-painikkeella ja poistuu
listauksesta. Ilman JavaScriptiä jokainen painallus on lomakkeen lähetys, joten:

* **Koko sivu on yksi lomake** (`collection_form.html`). Kuvien
  lisäyspainikkeet (`<button name="add" value="<kuvan id>">`, plus-merkki) ja
  järjestyspainikkeet (`up`, `down`, `remove`) lähettävät myös otsikon ja
  kuvauksen, joten kirjoitettu teksti ei katoa. Lomakkeen ensimmäinen
  lähetyspainike on `create collection` / `save`, joten Enter tallentaa.
  Muissa painikkeissa on `formnovalidate`, joten kuvia voi lisätä ennen kuin
  pakollinen otsikko on täytetty.
* **Luonnos pidetään istunnossa** (`session["collection_draft"]`: kokoelman
  `id` tai `None`, otsikko, kuvaus ja kuvien `id`:t). Tietokantaan kirjoitetaan
  vasta tallennettaessa, joten sinne ei synny keskeneräisiä tai kuvattomia
  kokoelmia. Luonnos on pieni (enintään 50 numeroa ja kaksi lyhyttä tekstiä),
  joten se mahtuu evästeeseen.
* `/new_collection` ja `/edit_collection/<id>` aloittavat aina uuden luonnoksen.
  Keskeneräistä luonnosta ei jatketa vahingossa, ja `cancel` on pelkkä linkki
  takaisin (my collections tai kokoelman sivu).
* Lisäyksen, poiston ja siirron jälkeen ohjataan kohtaan `#selected`, jotta
  sivu ei hyppää alkuun.
* Muokkaus tallentaa otsikon ja kuvauksen ja kirjoittaa kokoelman kuvat
  uudelleen (`DELETE` + `INSERT` uusilla `position`-arvoilla).

### Poisto

* Kokoelman poisto kysyy vahvistuksen eikä poista kuvia.
* Jos kuvan poisto jättää kokoelman tyhjäksi,
  `remove_empty_collections()` poistaa kokoelman, koska kokoelmassa on oltava
  vähintään yksi kuva.

## 12. Selaus ja haku

* **Kuvahaku** (`/search`, `photos.find_photos`): `LIKE '%sana%'` kuvauksesta
  ja tagien nimistä, tulokset uusin ensin (`DISTINCT`, koska kuva voi osua
  usean tagin kautta). Hakutuloksia ei sivuteta. SQLiten `LIKE` ei erottele
  kirjainkokoa vain kirjaimissa a–z, joten esim. `Ä` ja `ä` ovat eri merkit.
  Lisäksi `%` ja `_` toimivat hakusanassa jokerimerkkeinä.
* **Kokoelmahaku** (`/collections?query=`): sama `LIKE`-haku otsikosta ja
  kuvauksesta. Tulokset sivutetaan, ja hakusana säilyy sivulinkeissä
  (`/collections/2?query=…`).
* **Latest:** sivun yläreunassa on valinta `photos    collections`, ja valitun
  alla on alaviiva. Molemmissa näkymissä on hakukenttä: photos-näkymän kenttä
  hakee kuvia (`/search`), collections-näkymän kenttä kokoelmia.
* **Sivutus** (`pagination.html`): `LIMIT`/`OFFSET`, 20 kohdetta sivulla
  (`PAGE_SIZE`), järjestys `date_time_added DESC, id DESC`. Toissijainen
  järjestys `id`:n mukaan pitää järjestyksen vakaana, kun kaksi kohdetta on
  lisätty samalla sekunnilla.

## 13. Käyttöliittymä

* **Yläpalkki** (`layout.html`, lohkot `nav_left` ja `nav_right`): vasemmalla
  `latest`, keskellä `exposure` (etusivulle) ja oikealla kirjautuneelle
  `my photos`, `my collections` ja `log out`, kirjautumattomalle `log in`.
  Kirjautumis- ja rekisteröintisivuilla on vain `exposure`.
* **Sivupohjat:** yhteiset osat ovat omia tiedostojaan, jotka liitetään
  `include`-lauseella: `photo_list.html` (kuvalista),
  `collection_list.html` (kokoelmaruudukko), `photo_info.html` (kuvan
  tiedot), `photo_details_form.html` (kameratietojen kentät), `comments.html`,
  `pagination.html`, `latest_tabs.html` sekä hakulomakkeet.
* **Kuvalistat:** kuvat ovat allekkain koko 60 rem:n palstan levyisinä.
  Yhden kuvan näkymässä kuva on leveämpi ja tiedot ovat sen oikealla puolella
  17 rem:n palstassa.
* **Kokoelmalistat:** kaksi saraketta, ja jos kokoelmia on vain yksi, se on
  keskellä. Kansikuvat rajataan suhteeseen 3:2 (`object-fit: cover`), jotta
  rivit ovat tasaisia. Kortissa on otsikko, kuvaus ja my collections
  -sivulla päiväys, latest-sivulla `by <username>`.
* **Plus-painikkeet:** my photos- ja my collections -sivujen lisäyspainike sekä
  kokoelmalomakkeen kuvan lisäyspainike ovat CSS:llä piirrettyjä ohuita
  plus-merkkejä (`::before`/`::after`). Sivujen plus on yläpalkin `latest`-linkin
  kohdalla ja ensimmäisen kuvan yläreunan tasalla. Sen koko on kolmasosa
  kokoelmakuvan korkeudesta, ja se lasketaan container query -yksiköillä
  (`cqw`). Lista kapenee tarvittaessa, jottei plus osu kuvien päälle.
* **Kokoelman sivu:** otsikko, kuvaus (enintään puoleen väliin kuvien
  leveydestä) ja omistajan `edit` ovat kuvien vasemman reunan tasalla, ja
  päiväys on viimeisen kuvan alla oikeassa reunassa.
* **Tyylit:** värit ja reunan väli (`--edge`) ovat CSS-muuttujia. Fonttina on
  Helvetica-tyyppinen järjestelmäfontti (`"Helvetica Neue", Helvetica, Arial`).
  Alle 700 px:n leveydellä palstat pinoutuvat allekkain ja reunan väli
  pienenee.
* Käyttäjän syöte escapoidaan kaikkialla (Jinjan oletus). Rivinvaihdot
  näytetään CSS:llä eikä `<br>`-tageilla.

## 14. Testaus

Testit ovat `unittest`-testejä, jotka käyttävät Flaskin testiasiakasta.
`./test.sh` ajaa kaikki testit ja sen jälkeen pylintin, ja se päättyy virheeseen, jos
jompikumpi epäonnistuu. `./test.sh lint` ajaa vain pylintin ja
`./test.sh tests.test_comments` vain yhden testitiedoston. Skripti asentaa
tarvittaessa Flaskin ja pylintin virtuaaliympäristöön.
Ilman skriptiä: `python3 -m unittest`.

| Tiedosto | Kattaa |
| --- | --- |
| `test_users.py` | Rekisteröinti ja sen virheet, kirjautuminen, uloskirjautuminen, yläpalkin linkit ja niiden järjestys |
| `test_photos.py` | Kuvan lisäys (pääte, koko, JPEG-tunniste, kuvaus, 500 kuvan raja, oikea testikuva), kuvadatan palautus, näyttö, muokkaus, poisto, omistajuus, CSRF, latest-sivutus, my photos ja sen plus-painike, back-painike ja sen osoitteen rajaus |
| `test_details.py` | Kameratietojen jäsennys ja rajat, virheilmoitukset, näyttömuotoilu (mm, f/, 1/x s), lisäys ja muokkaus, näkyvyys vain kuvan sivulla, kurssiohjeen testiarvot |
| `test_tags.py` | Normalisointi, pilkkulista, sama nimi = sama tagi, sumea haku, lisäys ja poisto, 20 tagin raja, käyttämättömien tagien poisto, tagisivu |
| `test_search.py` | Etusivun hakulomake, haku kuvauksesta ja tageista, usean tagin kautta osuva kuva näkyy kerran, haku ilman kirjautumista, tyhjä ja tulokseton haku, SQL-erikoismerkit hakusanassa |
| `test_comments.py` | Kommentointi omiin ja muiden kuviin, järjestys, pituus, 100 kommentin raja, kirjautumis- ja CSRF-vaatimus, escapointi, paluuosoitteet, poisto kuvan mukana |
| `test_collections.py` | Luonti, luonnos (lisäys, poisto, järjestys, tekstin säilyminen), validointi ja rajat, pääsynhallinta, muokkaus, poisto, tyhjäksi jäävän kokoelman poisto, katselu, my collections, latest-kokoelmat, sivutus ja haku |

* `tests/base.py`:n `BaseTestCase` luo jokaiselle testille väliaikaisen
  tietokannan `schema.sql`:stä ja vaihtaa `config.database`n osoittamaan
  siihen, joten testit eivät koske kehitystietokantaan. Apumetodeja ovat mm.
  `register`, `login`, `logout`, `csrf_token`, `post` (lisää CSRF-tunnisteen),
  `upload_photo`, `add_photo`, `query` ja `execute`.
* Testikuvana käytetään sataa tavua, jotka alkavat JPEG-tunnisteella, koska
  sovellus tarkistaa vain tunnisteen. `test_upload_real_test_photos` lähettää
  lisäksi kansion `test_photos/` oikean kuvan ja tarkistaa, että sama data
  palautuu. Kansio ei ole versionhallinnassa, joten testi ohitetaan, jos kuvaa
  ei ole.
* Ulkoasua (sijainnit, koot) ei testata automaattisesti. Testit tarkistavat
  vain, että oikeat luokat ja elementit ovat sivulla. Ulkoasu on tarkistettu
  käsin kuvakaappauksista.

### Pylint

`pylint *.py tests` tarkistaa koodin tyylin (`pip install pylint`). Pylint on
vain kehitystyökalu, joten sovelluksen ainoa ajonaikainen riippuvuus on
edelleen Flask. `.pylintrc` pitää oletussäännöt käytössä ja poistaa niistä
vain ne, jotka kurssin esimerkkisovelluksen pylint-raportissa todetaan
tietoisiksi tyylivalinnoiksi:

| Poistettu sääntö | Peruste |
| --- | --- |
| `missing-*-docstring` | Docstring-kommentteja ei käytetä |
| `no-else-return` | `else`-haara `return`in jälkeen näyttää molemmat vaihtoehdot selvemmin |
| `inconsistent-return-statements` | GET/POST-reitit palauttavat arvon kummassakin haarassa, eikä Flask päästä muita metodeja funktioon asti |
| `dangerous-default-value` | Oletusarvoa `params=[]` ei muuteta funktiossa |
| vakioiden nimeäminen (`const-naming-style=any`) | `config.py`:n asetukset ovat pienillä kirjaimilla (`config.secret_key`) |

Lisäksi reittien sallittua haarojen, `return`-lauseiden ja parametrien määrää
on nostettu hieman (15, 8 ja 6), koska lomakereitit tarkistavat useita kenttiä.
Rivin enimmäispituus on oletuksen mukainen 100 merkkiä. Koodi saa nykyisillä
asetuksilla arvosanan 10/10.

### GitHub Actions

`.github/workflows/ci.yaml` ajetaan jokaisella pushilla (kaikki haarat) ja
pull requestilla. Työ asentaa Python 3.12:n, Flaskin ja pylintin ja ajaa sitten
komennot `python -m unittest -v` ja `pylint *.py tests`. Jos testit
epäonnistuvat, pylintiä ei ajeta, ja ajo merkitään epäonnistuneeksi.

`test.sh` ei ole versionhallinnassa, joten työ ajaa komennot suoraan.
Kansio `test_photos/` ei myöskään ole versionhallinnassa, joten oikeaa kuvaa
käyttävä testi ohitetaan CI:ssä. Tietokanta luodaan testeissä aina
`schema.sql`:stä, eikä `database.db`:tä tarvita.

## 15. Päätökset

Keskeiset valinnat koottuna. Yksityiskohdat ovat viitatuissa luvuissa.

**Yleiset**

* Ei JavaScriptiä: kaikki vuorovaikutus on linkkejä ja lomakkeita (luvut 9 ja
  11).
* Kuvat tallennetaan tietokantaan `BLOB`-sarakkeeseen eikä tiedostoina (luku 5).
* Poistot tehdään sovelluksessa käsin eikä `ON DELETE CASCADE` -määreillä,
  jotta käyttämättömät tagit ja tyhjät kokoelmat siivotaan samalla (luku 5).
* Kirjautumattomalle käyttäjälle kirjautumista vaativa sivu antaa 403 kuten
  esimerkkisovelluksessa, ja tällaiset linkit piilotetaan yläpalkista (luku 7).

**Kuvat ja tiedot**

* Kuvan JPEG-tunniste tarkistetaan päätteen lisäksi (luku 8).
* Suljinaika syötetään ja tallennetaan nimittäjänä 1/x (luku 8).
* Kuvan tiedot näytetään vain yhden kuvan näkymässä (luku 8).

**Tagit ja kommentit**

* Tagit lisätään kahdessa vaiheessa: pilkkulista lisäyslomakkeessa ja sen
  jälkeen tagisivu, jolla on sumea haku (luku 9).
* Vain kirjautunut käyttäjä voi kommentoida (luku 10).

**Kokoelmat**

* Luonti ja muokkaus tehdään yhdellä lomakkeella, ja luonnos pidetään
  istunnossa, kunnes se tallennetaan (luku 11).
* Kuvien järjestystä voi muuttaa ↑/↓-painikkeilla (luku 11).
* Kokoelma, josta poistuu viimeinen kuva, poistetaan automaattisesti (luku 11).
* Kuvien väliin liitettäviä tekstiosuuksia ei ole toteutettu, koska ne ovat
  ohjeessa vielä epävarmoja. Sarake `position` tekee niiden lisäämisestä
  myöhemmin suoraviivaista.

**Ulkoasu**

* Fonttina on Helvetica-tyyppinen järjestelmäfontti (luku 13).
* Lisäyspainikkeet ovat plus-merkkejä, joiden koko määräytyy kuvien koosta
  (luku 13).

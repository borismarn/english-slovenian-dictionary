# Angleško-slovenski in slovensko-srbski slovar

Slovarja v formatih JSON in StarDict. Glavni datoteki sta `eng_slo.json` in
`slo_ser.json`; datoteke StarDict so njuna izvoza za bralnike in slovarske programe.

## Vsebina

| Datoteka ali mapa | Namen |
| --- | --- |
| `eng_slo.json` | Angleško-slovenska gesla in razlage |
| `slo_ser.json` | Slovensko-srbska gesla, vključno s pregibnimi oblikami |
| `slo_ser_sources.json` | Navedbe virov in metapodatki za dodane pregibne oblike |
| `stardict_eng_slo.*` | Angleško-slovenski izvoz: `.ifo`, `.idx`, `.dict` |
| `stardict_slo_ser.*` | Slovensko-srbski izvoz: `.ifo`, `.idx`, `.dict` |
| `tools/` | Eno skupno orodje za izvoz, preverjanje in statistiko |
| `tests/` | Preizkusi orodja |
| `review/` | Odprta gesla, izvirne vrednosti in evidence pregledov |
| `sources/` | Izvorni nabori, uporabljeni pri izdelavi |

Datoteke `.ifo`, `.idx` in `.dict` posameznega izvoza sodijo skupaj.

## Urejanje In Izvoz

Potrebujete Python 3.9 ali novejši. Dodatne knjižnice, računi in ključi API niso potrebni.

Prevode urejajte v glavnih datotekah JSON. Pri angleško-slovenskem slovarju
ločite prevod in razlago z `\n` v nizu JSON, na primer:

```json
{
  "abnegator": "odrekovalec, asket\nČlovek, ki se zavestno odpoveduje lastnim željam, udobju ali užitkom."
}
```

Izvoz obeh slovarjev:

```bash
python3 tools/stardict.py build
```

Izvoz samo angleško-slovenskega ali samo slovensko-srbskega slovarja:

```bash
python3 tools/stardict.py build --dictionary eng-slo
python3 tools/stardict.py build --dictionary slo-ser
```

Preverjanje vseh gesel, indeksov, besedil in metapodatkov izvoza ter statistika:

```bash
python3 tools/stardict.py verify
python3 tools/stardict.py stats
```

Orodje poišče podatke glede na svojo lokacijo, ne glede na trenutno mapo.
Glavnih datotek JSON ne spreminja. Pred zamenjavo izvoza preveri novo izdelane
datoteke; zavrne podvojene ključe, prazne prevode in neveljavne podatke.

Preizkusi:

```bash
python3 -B -m unittest discover -s tests
```

## Odprta Gesla

Preverjanje tehnične pravilnosti ne zagotavlja pravilnosti vseh prevodov.
Odprti angleško-slovenski vnosi so v `review/eng_slo_pending.json`.
Po prehodu 3. novembra 2026 je ostalo 255 nepotrjenih zapisov in 180 zapisov
`schemik…`, ki so po uporabnikovi odločitvi ohranjeni nespremenjeni.
Izvirne in popravljene vrednosti so shranjene v `review/`.

## Viri In Zgodovina

Izvorni nabori so navedeni v [sources/README.md](sources/README.md).
Za samodejno dodane pregibne oblike so navedbe Sloleks 3.1 in srLex 1.3 ter
njunih licenc ohranjene v `slo_ser_sources.json` in `review/inflections/`.
Te navedbe ne pomenijo ponovnega licenciranja vseh starejših prevodov.

Evidence o uvozih in viri objavljenih vnosov so opisani v
[review/README.md](review/README.md).

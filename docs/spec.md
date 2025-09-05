# TASAK: The Agent's Swiss Army Knife



## User Stories -- Personas
Personas: 

[[1]] Human-Power-User, 
[[2]] Agent AI z dostępem do command-line
[[3]] TASAK's technical product owner



## Product Vision
TASAK ma być "cmd"-line proxy do odpalania innych "pod - aplikacji"
aplikacje konfigurowane są dynamicznie / runtime, mimo, ze sam "tasak" powinien być kompilowalny
kongiguracja powinna być zawsze dwupoziomowa:

1) główna konfiguracja: <user-home-dir>/.tasak/tasak.yaml    (ważne: zachowujemy kompatybilność z windows/linux/mac)
2) "lokalna" konfiguracja oparta o aktualny katalog z którego tasak został odpalony
szukamy hierarchicznie:
    -> <curr_dir>tasak.yaml
    -> <curr_dir>/.tasak/tasak.yaml
    -> ../.tasak/tasak.yaml
    -> ../../.tasak/ ----> aż do roota

zasada łącznia:

a) najpierw wczytujemy zawsze <user-home-dir>/.tasak/tasak.yaml
b) potem skanujemy drzewo konfigów "lokalnych" 
c) "merdżujemy" je po kolei.

"merdżowanie" to:
- dodanie propertiesów które znaleźliśmy w nowym konfigu do aktualnego konfigu
- jeśli istniał: nadpisujemy, jesli nie istniał: dokładamy

kolejność merdżowania:
global -> local root -> local niższy -> local jeszcze niższy 

czyli: ten który jest najbliżej katalogu z którego uruchomiono -> jest "najświeższy"


struktura yamla:

----

apps_config:
    header: "this is header"
    enabled_apps:
        - app1
        - app2

app1: (...)

app2: (...)
 
app-n: 
    name: "<str>"
    type: "cmd"
    meta:
        command: "notepad.exe test.txt"

-----


Wymagania techniczne:
- kod python, pro jakość, setup pre-commit hookow z checkiem na nie przekraczanie 600 linii per plik
- DRY, logiczna struktura modułów / pod modułów
- TDD
- mało komentarzy (concise/avoid)
- wszystko po angielsku: kod, dokumentacja, komentarze, wiadomości

Typy appsów:
1) cmd - zwykły command line
2) mcp -> MCP serwer, musi być skonfigurowany w konfigu
3) api-client // Architektura gotowa, ale implementacja odroczona na "some-day"



## User stories
PRD-001: initial
Jako [[1]] lub [[3]] chcę na poziomie systemu wykonać komendę
pip install -e https://github.com/jacekjursza/TASAK    (lub coś podobnego)
LUB inny one-liner 

i od tego momentu mieć dostępną komendę, niezależnie od katalogu

okhan> tasak --help
-> Hello world!

AC:
- aplikacja zainstalowana i dostępna do odpalenia
- działa polecenie "tasak --help"
- lokalny katalog /home/okhan/code/tasak podpięty do repozytorium zdalnego https://github.com/jacekjursza/TASAK 
- wszystkie pliki wypchnięte na github z commitem "initial setup"



PRD-002:
Jako [[1]] chcę w swoim katalogu domowym móc stworzyć plik:

/home/okhan/.tasak/tasak.yaml

w którym będę mógł określić konfigurację aplikacji i będzie ona automatyznie wczytywana przez TASAK niezależnie od katalogu z którego została uruchomiona aplikacja

AC:
- /home/okhan/.tasak/tasak.yaml utworzony i zawiera jeden key: "header" oraz value: "tasak config test"
- uruchomienie "tasak" wyświetla wartość z configa z pola "header"


PRD-003:

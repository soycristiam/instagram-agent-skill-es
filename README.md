# Instagram con Claude, en español

Trece skills para que Claude te ayude a manejar una cuenta de Instagram:
escribir reels, captions, carruseles e historias, armar la semana, responder
comentarios y DMs, puntuar tu perfil y sacarle a un texto la cara de «esto lo
escribió una IA». Gratis, licencia MIT, sin registrarte, sin claves de API y
sin conectar tu cuenta.

Es la adaptación al español de
[**instagram-agent-skill**](https://github.com/Jakeschincariol/instagram-agent-skill),
creado por **Jake Schincariol** ([opusjake.ai](https://opusjake.ai)). La idea,
el método y casi todo el trabajo son de él. Esta versión hace que las skills te
respondan en español y que los puntuadores entiendan textos en español.

**Las skills escriben. Vos publicás.** Nada sale a Instagram sin que vos lo
copies y lo subas.

## Qué cambia en esta versión

- **Responden en español sin que lo pidas.** Cada skill tiene la instrucción
  de contestar en español, con voseo o tuteo según lo que pongas en tu
  `voice.md` (si no ponés nada, español neutro).
- **Se activan con frases en español**: «armame un reel», «puntuá mi perfil»,
  «qué publico esta semana», «escribime el caption», «humanizá esto». Las
  frases en inglés del original también siguen andando.
- **Los puntuadores entienden español.** En el original, un gancho en español
  sacaba puntaje bajo aunque fuera bueno, y el detector de «suena a IA» no
  reconocía ninguna muletilla en español. Ahora:
  - el puntaje de ganchos reconoce números escritos como se dicen («2.000
    dólares», «cinco horas»), saludos («hola gente»), preámbulos («hoy les
    quiero hablar de») y voseo;
  - el detector y el humanizador traen unas 280 palabras y frases de relleno
    típicas en español («en el mundo actual», «es fundamental», «llevar al
    siguiente nivel», «sin lugar a dudas»…) con su reemplazo simple;
  - el revisor de captions reconoce pedidos en español («Comentá GUÍA»,
    «escribime», «link en la bio», «guardá») y palabras clave con o sin tilde;
  - las 26 fórmulas de ganchos tienen un ejemplo en español.
- **Funciona bien en Windows.** Tildes y eñes salen bien en PowerShell y en
  Git Bash con `python` a secas, y los scripts leen archivos guardados como
  UTF-8, UTF-8 con BOM, UTF-16 (lo que escribe PowerShell con `>`) o ANSI.
- `templates/voice.md` está en español.

Lo que **no** cambia: las instrucciones internas de cada skill siguen en inglés,
como en el original, para que sea fácil seguir sus actualizaciones. Claude las
lee igual y te contesta en español. Los rótulos que imprimen los scripts
(`STRONG`, `WEAK`, `PASS`, `REVIEW`) también quedaron en inglés.

## Qué necesitás

- **Claude Code.** Es la versión de Claude que trabaja con archivos en tu
  computadora (terminal, app de escritorio o extensión de VS Code). No viene
  en el plan gratis de Claude: necesitás un plan pago (Pro o superior) o una
  cuenta de API.
- **Python 3**, para los seis scripts que puntúan y limpian textos. No hace
  falta instalar ninguna librería. En Mac y Linux suele venir instalado. En
  Windows bajalo de [python.org](https://www.python.org/downloads/) y, en el
  instalador, marcá «Add python.exe to PATH».
- **Git**, para descargar el repo. Si se lo pedís a Claude Code y no lo
  tenés, te lo va a avisar. En Windows se baja de
  [git-scm.com](https://git-scm.com/download/win).

Sin Claude Code también se puede usar a medias: pegá el contenido de un
`SKILL.md` al principio de un chat de Claude y funciona como un «modo». Perdés
los scripts, que son lo mejor de `/ig-reel` y `/ig-human`.

## Instalación

### La fácil: pedíselo a Claude Code

Abrí Claude Code y pegá esto:

```
https://github.com/soycristiam/instagram-agent-skill-es

Instalá esta skill y confirmá que /ig-reel funciona.
```

Claude va a descargar el repo y copiar las 13 carpetas `ig-*` a tu carpeta de
skills (`~/.claude/skills/`). Antes de cada comando te va a pedir permiso:
leelo y aceptá. Cuando termine, escribí `/ig` en Claude Code y tendrían que
aparecer las trece. Si no aparecen, cerrá Claude Code y volvé a abrirlo.

### A mano, en Windows (PowerShell)

```powershell
git clone https://github.com/soycristiam/instagram-agent-skill-es.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force instagram-agent-skill-es\skills\ig-* "$HOME\.claude\skills\"
Get-ChildItem "$HOME\.claude\skills" -Filter "ig-*"
```

El último comando tiene que listar 13 carpetas.

### A mano, en Mac o Linux

```bash
git clone https://github.com/soycristiam/instagram-agent-skill-es.git
mkdir -p ~/.claude/skills
cp -r instagram-agent-skill-es/skills/ig-* ~/.claude/skills/
ls ~/.claude/skills | grep '^ig-'
```

### Como plugin

Dentro de Claude Code:

```
/plugin marketplace add soycristiam/instagram-agent-skill-es
/plugin install instagram-agent-es@instagram-agent-skill-es
```

Instaladas como plugin, las skills llevan el nombre del plugin adelante (por
ejemplo `/instagram-agent-es:ig-reel`). Si ya tenés instalada la versión en
inglés, instalá solo una de las dos: comparten los nombres `ig-*`.

### Solo para un proyecto

Si preferís que las skills estén disponibles solo en una carpeta, copiá las
mismas carpetas a `.claude/skills/` dentro de esa carpeta en vez de a tu
carpeta personal.

## Las trece

| comando | qué hace |
| --- | --- |
| `/ig-reel` | De una idea a un reel: tres ganchos sobre [26 fórmulas](skills/ig-reel/hooks.json), puntuados, y después el guion, el texto en pantalla y una escaleta con tiempos. |
| `/ig-viral` | Busca qué está funcionando en tu nicho, lo ordena por cuánto superó cada reel al promedio de su propia cuenta, nombra la fórmula y arma un archivo de referencias. |
| `/ig-caption` | El caption, revisado. Te muestra los 125 caracteres que se ven en el feed antes del «más». |
| `/ig-carousel` | Carruseles: la portada que hace deslizar, el texto de cada placa y los archivos de 1080x1350. |
| `/ig-story` | La secuencia de historias del día, qué sticker usar en cada una y cómo llevar a la gente a los mensajes. |
| `/ig-profile` | Puntúa tu perfil sobre 100 con una [rúbrica de 12 partes](skills/ig-profile/rubric.json) y reescribe empezando por lo que más resta. |
| `/ig-plan` | La semana: qué publicar, en qué formato, cuándo y con qué 10 cuentas interactuar. |
| `/ig-human` | El humanizador: limpia relleno de IA, rayas largas y caracteres invisibles, y puntúa el resultado. |
| `/ig-comment` | Comentarios en posteos de otras cuentas que suenan a una persona, no a «🔥🔥🔥». |
| `/ig-reply` | Los comentarios de tus propios posteos: los ordena (palabra clave, posible cliente, pregunta, crítica, ruido) y responde en ese orden. |
| `/ig-dm` | La entrega de la palabra clave, el primer mensaje, la propuesta de colaboración y los dos seguimientos. Dos, no más. |
| `/ig-repurpose` | Un video, podcast o newsletter convertido en una semana de reels y carruseles que se entienden solos. |
| `/ig-audit` | Análisis de lo que ya publicaste: qué funcionó y qué dejar de hacer, mirando más allá de las vistas. |

## Primeros pasos

1. **Armá tu `voice.md`.** Es lo que hace que los textos suenen a vos y no a
   cualquiera. La forma rápida: pasale a Claude tres captions o guiones tuyos
   y pedile «armame mi voice.md con esto». La forma manual: copiá
   [`templates/voice.md`](templates/voice.md) a `~/.claude/instagram/voice.md`
   y completalo. Ahí también decís si hablás de vos o de tú.
2. **`/ig-profile`**: pegá tu bio y tus destacadas y arreglá primero el perfil.
   Si alguien llega desde un reel y el perfil no explica qué hacés, se va.
3. **`/ig-viral`**: mirá qué está funcionando en tu nicho antes de escribir.
4. **`/ig-plan`**: armá la semana con lo que encontraste.
5. **`/ig-reel`** y **`/ig-caption`** para cada pieza, y pasá todo por
   **`/ig-human`** antes de publicar.

Después de publicar unas semanas, **`/ig-audit`** con tus estadísticas te dice
qué repetir.

## Los scripts que corren en tu computadora

No necesitan internet ni librerías, y no suben nada a ningún lado. Claude los
corre solo cuando hace falta, pero también los podés usar vos. En Windows usá
`python`; en Mac o Linux, `python3`. Pasales el texto como archivo.

```bash
python ~/.claude/skills/ig-reel/hookscore.py ganchos.txt       # un gancho por línea
python ~/.claude/skills/ig-reel/beats.py guion.txt --target 30  # tiempos del guion
python ~/.claude/skills/ig-caption/caption.py caption.txt --keywords "instagram,claude"
python ~/.claude/skills/ig-human/humanize.py borrador.txt --report -o limpio.txt
python ~/.claude/skills/ig-human/detect.py borrador.txt limpio.txt   # antes y después
python ~/.claude/skills/ig-viral/swipe.py reels.tsv --out referencias.md
```

Así puntúa tres ganchos (salida real):

```
HOOK RANKING
==============================================================================
->  81.6 STRONG  Perdí un cliente de 2.000 dólares por responder un WhatsApp...
        weakest: ADDRESS (70)
    34.2 WEAK    Dejé de pasar horas pensando qué publicar
        weakest: SPECIFICITY (15)
     5.4 WEAK    Hola gente, hoy les quiero hablar de Instagram
        weakest: FRONTLOAD (0)
        dealbreaker: Video preamble. Delete it and open on the payoff.
        dealbreaker: Greeting. Nobody came to the feed to be greeted.
```

**Ojo con cómo leer estos puntajes.** Miden cosas concretas del texto: si
arranca con un saludo, si tiene un número, si dice algo en juego, si es corto.
Sirven para descartar ganchos flojos antes de grabar. **No predicen vistas.** El
autor original lo midió y lo dice claro en su README: el puntaje separa bien
los ganchos malos, pero entre dos ganchos decentes no sabe cuál va a andar
mejor. Eso lo deciden tu cara, tu edición, el audio y a quién se lo muestra
Instagram. Lo mismo para el detector de «suena a IA»: son chequeos locales, no
GPTZero ni ningún servicio externo, y nadie puede venderte en serio un texto
«indetectable».

La carpeta [`pruebas-es/`](pruebas-es) tiene textos de ejemplo para probar
cada script.

## La letra chica

- **Las skills no publican en Instagram.** Publicar, comentar, seguir o mandar
  DMs con herramientas automáticas va contra los
  [Términos de Uso de Instagram](https://help.instagram.com/581066165581870) y
  te pueden bloquear la cuenta. Por eso cada skill termina igual: un bloque
  listo para copiar, y lo publicás vos. Las respuestas automáticas a una
  palabra clave por DM sí existen, con las herramientas de Instagram o de
  partners aprobados; `/ig-dm` explica dónde está el límite.
- **Nunca le des tu contraseña de Instagram a Claude** ni a ninguna skill.
  Ninguna de estas la necesita.
- **`/ig-viral` lee, no scrapea.** Pocas cuentas, unos pocos reels cada una,
  a velocidad humana y con vos manejando tu propio navegador. Juntar datos de
  forma automática y masiva es lo que hace que restrinjan cuentas.
- **Nada se inventa.** Si un borrador necesita un número que no diste, vuelve
  con `{{tu número}}` marcado para que lo completes.
- **Los números de la plataforma cambian.** Si algo de acá contradice lo que
  Instagram hace hoy, tiene razón Instagram.
- **El léxico de relleno es para editar.** Está en
  [`skills/ig-human/slop.json`](skills/ig-human/slop.json). Si una palabra que
  usás de verdad cae en el filtro, borrala.

## Límites conocidos de la adaptación

- El humanizador reemplaza palabras por regex y no conoce el género ni la
  concordancia: a veces una frase queda rara («Usar un montón de posibilidades
  importa…»). Por eso reporta cada cambio. Leé el resultado antes de usarlo.
- «Escribí» es a la vez imperativo con voseo y pasado en primera persona; el
  puntuador lo toma como imperativo.
- Si le pasás texto por un pipe de Windows PowerShell 5.1 (`"texto" | python
  ...`), las tildes se pueden romper antes de llegar al script. Guardalo en un
  archivo y pasale el archivo.

## Archivos

```
skills/ig-*/SKILL.md               las 13 skills
skills/ig-reel/hooks.json          26 fórmulas de gancho, con ejemplo y regex en español
skills/ig-reel/hookscore.py        puntaje de ganchos (cinco chequeos)
skills/ig-reel/beats.py            guion a escaleta con tiempos
skills/ig-caption/caption.py       vista previa del feed y revisión del caption
skills/ig-human/slop.json          el léxico de relleno, en inglés y en español
skills/ig-human/humanize.py        la limpieza
skills/ig-human/detect.py          los cinco chequeos de «suena a IA»
skills/ig-viral/swipe.py           ranking por cuánto superó cada reel a su cuenta
skills/ig-profile/rubric.json      la rúbrica de 100 puntos del perfil
templates/voice.md                 tu perfil de voz. Empezá por acá.
pruebas-es/                        textos de ejemplo para probar los scripts
README.en.md                       el README original, en inglés
```

## Créditos y licencia

Original: [instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill)
de Jake Schincariol ([opusjake.ai](https://opusjake.ai)). Su repo hermano para
LinkedIn: [linkedin-agent-skill](https://github.com/Jakeschincariol/linkedin-agent-skill).

Adaptación al español: Cris Lemos.

Licencia MIT, la misma del original. Ver [`LICENSE`](LICENSE).

# steam-playtime

[English](README.md) · **Español**

Mira cómo evoluciona tu tiempo de juego en Steam, juego a juego. `steam-playtime` lee el registro de sesiones que el cliente de Steam ya guarda en tu ordenador y lo convierte en un informe HTML interactivo:

- **Horas por semana**, apiladas por juego
- **Horas acumuladas** de tus juegos más jugados
- **Detalle diario** del juego que elijas
- **Una tabla** con horas totales, número de sesiones, duración media y primera y última partida

El perfil de Steam solo muestra un total por juego. Esto muestra *cuándo* jugaste.

Todo se ejecuta en local. No se sube nada y no hace falta cuenta de Steam ni clave de API.

## Cómo usarlo

Necesitas el cliente de escritorio de Steam, con juegos lanzados desde él al menos una vez. Para ver los gráficos del informe hace falta conexión a internet; la tabla funciona sin conexión.

### Windows: solo el programa (sin instalar Python)

1. Entra en [**Releases**](https://github.com/SergaFTW/Playtime-Evolution-Chart-for-Steam/releases/latest) y descarga `SteamPlaytime.exe`.
2. Haz doble clic. Se abre una ventana con el progreso y el informe aparece en el navegador.
3. Vuelve a abrirlo cuando quieras un informe actualizado.

La primera vez Windows puede mostrar *«Windows protegió su PC»*, porque el programa no está firmado. Pulsa **Más información → Ejecutar de todas formas**.

El informe se guarda en `%LOCALAPPDATA%\steam-playtime\steam_playtime.html`, así que puedes abrirlo más tarde sin ejecutar el programa.

### Cualquier sistema, con Python

Si tienes Python 3.9 o superior ([python.org](https://www.python.org/downloads/)):

1. Descarga este repositorio: botón verde **Code** → **Download ZIP**, y descomprímelo.
2. Haz doble clic en `run.py`, o ejecuta `python run.py` en una terminal dentro de esa carpeta.

Para instalarlo como comando (`steam-playtime`), con todas las opciones de abajo:

```bash
pip install https://github.com/SergaFTW/Playtime-Evolution-Chart-for-Steam/archive/refs/heads/main.zip
```

```bash
steam-playtime
```

El comando guarda `steam_playtime.html` en la carpeta actual y lo abre en el navegador.

## Opciones

| Opción | Qué hace |
|---|---|
| `-o FICHERO`, `--output FICHERO` | Dónde guardar el informe (por defecto `steam_playtime.html`) |
| `--steam-dir CARPETA` | Carpeta de Steam, si no se encuentra sola (la que contiene `logs`) |
| `--lang {auto,en,es}` | Idioma del informe. `auto` usa el idioma del sistema |
| `--min-minutes N` | Ignora sesiones de menos de N minutos (por defecto 1) |
| `--exclude APPID` | Deja fuera una app. Repítelo para varias |
| `--include-all` | Incluye las apps que se excluyen por defecto (ver abajo) |
| `--history FICHERO` | Usa otro fichero de historial |
| `--no-history` | Usa solo lo que tienen ahora los logs de Steam |
| `--csv FICHERO`, `--json FICHERO` | Exporta también todas las sesiones |
| `--no-open` | No abre el navegador |

El AppID de un juego está en la URL de su página de la tienda: `store.steampowered.com/app/<AppID>/…`.

## Cómo funciona

Cada vez que Steam arranca un juego escribe una línea en `Steam/logs/gameprocess_log.txt`, y otra cuando el proceso termina:

```text
[2026-06-05 23:42:45] AppID 3224770 adding PID 10280 as a tracked process "...\Game.exe"
[2026-06-06 01:13:25] AppID 3224770 no longer tracking PID 10280, exit code 0
```

`steam-playtime` empareja esas líneas en sesiones:

- Si un juego tiene varios procesos a la vez (launcher y juego, por ejemplo), cuentan una sola vez.
- Una sesión sin línea de cierre, porque Steam se cerró o falló con el juego abierto, se descarta, ya que no se sabe cuánto duró.
- Los nombres salen de los ficheros `appmanifest_*.acf` de todas tus bibliotecas de Steam. Para juegos desinstalados se usa el nombre de su carpeta de instalación.
- **El AppID 480 («Spacewar»)** es una app de prueba pública que usan muchos juegos lanzados fuera de la tienda. Esas sesiones se nombran según la carpeta del ejecutable, cuando Steam la registró. El resto se agrupa como «Spacewar (AppID 480)».
- Excluidas por defecto: redistribuibles de Steamworks (228980), Wallpaper Engine (431960, está abierto todo el día) y el asistente de Steam de la app de EA (1182480, duplicaría las horas de los juegos de EA). Usa `--include-all` para incluirlas.

### Historial

Steam solo guarda el log actual y uno anterior rotado, así que suele cubrir unos pocos meses. Cada ejecución guarda todas las sesiones que encuentra en un fichero de historial, así que tus datos siguen creciendo aunque Steam borre los logs viejos. **Ejecútalo de vez en cuando** (una vez al mes basta) para no perder nada.

| Sistema | Fichero de historial |
|---|---|
| Windows | `%LOCALAPPDATA%\steam-playtime\history.json` |
| macOS | `~/Library/Application Support/steam-playtime/history.json` |
| Linux | `~/.local/share/steam-playtime/history.json` |

Borra ese fichero para empezar de cero.

## Dónde busca Steam

- **Windows**: la ruta de Steam en el registro y, si no, `Program Files (x86)\Steam`.
- **Linux**: `~/.steam/steam`, `~/.local/share/Steam` e instalaciones Flatpak y Snap.
- **macOS**: `~/Library/Application Support/Steam`.

Si lo tienes en otro sitio, usa `--steam-dir`.

## Limitaciones

- El historial empieza en la primera fecha de tu log de Steam. Steam no guarda un registro con fechas del tiempo jugado antes.
- Solo cuenta juegos lanzados desde Steam. Epic, GOG, Xbox y otros launchers no.
- Cuenta el tiempo que el proceso del juego está abierto, aunque esté minimizado o inactivo.
- Está probado en Windows. Linux y macOS usan el mismo formato de log, pero se han probado menos en uso real. Se agradecen los reportes.

## Desarrollo

```bash
python -m unittest -v
```

Los tests usan una carpeta de Steam falsa en `tests/fixtures`.

Para compilar el ejecutable tú mismo: `pip install pyinstaller` y luego `python build_exe.py` (sale en `dist/`). Al subir un tag como `v0.2.0`, GitHub compila el `.exe` de Windows y lo publica como Release automáticamente.

## Licencia

[MIT](LICENSE)

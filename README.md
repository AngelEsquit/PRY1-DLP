# PRY1-DLP

Generador de analizadores léxicos (YALex a lexer en Python), implementado sin librerías externas de expresiones regulares o autómatas.

## Resumen

El proyecto recibe una especificación YALex y permite:

- Parsear la especificación y sus regex.
- Construir AFN y AFD minimizado.
- Tokenizar entradas con estrategia maximal munch.
- Generar un lexer Python autónomo.

Incluye dos formas de uso:

- Modo CLI interactivo en terminal.
- App desktop estilo IDE con Tauri + React en la carpeta desktop-app.

## Estructura Principal

```text
src/
    main.py                  # Punto de entrada principal
    bridge_cli.py            # Bridge JSON para la app desktop
    yalex_parser/
        parser.py              # Parser de .yal
        regex_parser.py        # Parser de regex
        thompson.py            # Construcción AFN
        dfa.py                 # Construcción y minimización AFD
        simulator.py           # Tokenización con traza
        codegen.py             # Generación de lexer Python

desktop-app/
    src/                     # Frontend React + Monaco Editor
    src-tauri/               # Backend Tauri (comandos del sistema)

examples/
    simple.yal

tests/
    test_yalex_pipeline.py
    test_extreme_scenarios.py
```

## Requisitos

### Motor Python

- Python 3.10 o superior.

### App Desktop

- Node.js 18 o superior.
- Rust toolchain estable.
- Dependencias de compilación de Tauri para Windows (MSVC Build Tools).

## Pipeline

1. Parser YALex: extrae header, lets, rule y trailer.
2. Regex a AST: convierte regex de lets y rule en árboles.
3. Thompson: crea AFN por alternativa.
4. AFN combinado: unifica alternativas con prioridades.
5. Subset construction: convierte AFN a AFD.
6. Minimización: reduce AFD (Hopcroft).
7. Simulación: tokeniza texto y reporta errores léxicos.
8. Codegen: genera lexer Python autónomo.

## Ejecución

Desde la raíz del repositorio.

### Ver ayuda

```bash
python src/main.py --help
```

Comportamiento actual:

- Con --cli: menú interactivo en terminal.
- Sin argumentos: menú interactivo en terminal.

### Modo CLI (por defecto)

```bash
python src/main.py
```

Alias explícito:

```bash
python src/main.py --cli
```

### Ejecutar lexer generado

```bash
python output/lexer.py tests/input/medium.txt
```

Flujo típico del menú CLI:

1. Seleccionar archivo .yal.
2. Revisar spec, AST, AFN, AFN combinado o AFD.
3. Tokenizar entrada.
4. Generar lexer .py.

## App Desktop (Tauri + React)

La app en desktop-app ofrece una experiencia tipo VS Code, enfocada en flujo YALex:

- Explorer recursivo.
- Editor en pestañas con resaltado de sintaxis (Monaco Editor).
- Panel lateral de ejecución con una acción activa por vez (`spec`, `ast`, `nfa`, `combinedNfa`, `dfa`, `tokenize`, `generate`).
- Campos contextuales por acción (solo se muestran los necesarios).
- Panel de resultados JSON y panel de output para trazas y errores.
- Paneles redimensionables (Explorer, Pipeline, Resultado y Output) con persistencia de tamaños al reabrir.
- Acciones de uso diario: abrir carpeta, refrescar explorer, crear archivo/carpeta, guardar y ejecutar.

Flujo recomendado en la UI:

1. Abrir un `.yal` desde el explorer.
2. Elegir acción en el panel **Pipeline**.
3. Completar input/output solo si la acción lo requiere.
4. Ejecutar y revisar `Resultado JSON` + `Output`.

Comandos:

```bash
cd desktop-app
npm install
npm run tauri -- dev
```

Nota: también funciona `npm run tauri dev` en la mayoría de entornos.

Build de frontend:

```bash
cd desktop-app
npm run build
```

## Pruebas

Desde la raíz:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Script de apoyo (Linux/macOS con bash):

```bash
./run_tests.sh
./run_tests.sh 3
```

En Windows PowerShell, si python no está en PATH, usar py:

```bash
py -3 -m unittest discover -s tests -p "test_*.py" -v
```

## Solución de Problemas Rápida

- Error al correr npm run tauri dev desde la raíz: ejecutar dentro de desktop-app.
- Si falla el comando en tu shell, usar: `npm run tauri -- dev`.
- Error `Cannot read properties of undefined (reading 'invoke')`: la UI se abrió fuera de Tauri (por ejemplo con `npm run dev`). Iniciar con `npm run tauri -- dev` dentro de `desktop-app`.
- En Linux (Ubuntu), si aparece error de `gdk-3.0` / `pkg-config` / `webkit`: instalar dependencias nativas de Tauri:
    `sudo apt update && sudo apt install -y build-essential pkg-config libgtk-3-dev libwebkit2gtk-4.1-dev libayatana-appindicator3-dev librsvg2-dev patchelf libssl-dev`
- **Error de símbolo de glibc en Linux (con snaps instalados):** `symbol lookup error: libpthread.so.0: undefined symbol __libc_pthread_init`. Causa: snap proporciona una versión antigua 
de libc que entra en conflicto con las bibliotecas nativas. **Solución:**
    1. Verificar que existe script de lanzamiento limpie: `ls desktop-app/scripts/launch-clean.sh`
    2. Usar el launch script limpio en lugar de npm directo: `cd desktop-app && bash scripts/launch-clean.sh`
    3. (Alternativa manual) Ejecutar con `LD_PRELOAD=/lib/x86_64-linux-gnu/libc.so.6:/ lib/x86_64-linux-gnu/libpthread.so.0 npm run tauri -- dev`
- Error de cargo o rustc no encontrado: instalar Rust y reiniciar terminal.
- Error de linker en Windows: instalar MSVC Build Tools.
- Puerto ocupado de Vite: cerrar instancia anterior o reiniciar la app.

## Restricciones Cumplidas

- Sin librerías de regex/autómatas para el motor del lexer.
- Lexer generado autónomo.
- Interfaces CLI y desktop.
- Casos de prueba de baja, media y alta complejidad, además de escenarios extremos.


# PRY1-DLP

Generador de analizadores léxicos (YALex → analizador en Python),
implementado sin librerías de regexp/autómatas.

## Descripción

Este proyecto toma como entrada un archivo escrito en YALex y genera un analizador léxico
autónomo en Python capaz de reconocer los tokens especificados o reportar errores léxicos.

## Estructura del proyecto

```text
src/
    main.py                       # CLI principal
    yalex_parser/
        __init__.py
        models.py                 # Modelos del archivo YALex
        parser.py                 # Parser de archivos .yal
        regex_ast.py              # Nodos AST para expresiones regulares
        regex_parser.py           # Parser de regex YALex → AST
        thompson.py               # Construcción de Thompson (AFN)
        dfa.py                    # Subset construction + minimización (AFD)
        simulator.py              # Simulador AFD (maximal munch)
        codegen.py                # Generador de código (lexer autónomo)
    ui/
        __init__.py
        app.py                    # Interfaz gráfica (tkinter)
examples/
    simple.yal                    # Ejemplo básico
tests/
    yal/
        low.yal                   # Especificación baja complejidad
        medium.yal                # Especificación media complejidad
        high.yal                  # Especificación alta complejidad
    input/
        low.txt                   # Entrada baja complejidad
        medium.txt                # Entrada media complejidad
        high.txt                  # Entrada alta complejidad
```

## Pipeline

1. **Parser YALex** — Lee el archivo `.yal` y extrae header, lets, rule y trailer.
2. **Regex → AST** — Parsea cada expresión regular a un árbol de sintaxis abstracta.
3. **Thompson** — Construye un AFN por cada alternativa del rule, luego los combina.
4. **Subset Construction** — Convierte el AFN combinado en un AFD determinista.
5. **Minimización** — Reduce el AFD mediante el algoritmo de Hopcroft.
6. **Simulación** — Tokeniza texto de entrada con estrategia maximal munch + prioridad por orden.
7. **Generación de código** — Produce un archivo Python autónomo con el AFD serializado.

## Ejecución

Desde la raíz del proyecto:

### Parsear un archivo .yal (JSON)

```bash
python src/main.py examples/simple.yal
```

### Ver el AST de expresiones regulares

```bash
python src/main.py examples/simple.yal --ast
```

### Construir AFN por Thompson

```bash
python src/main.py examples/simple.yal --nfa
```

### Construir AFN combinado

```bash
python src/main.py examples/simple.yal --combined-nfa
```

### Construir y visualizar AFD

```bash
python src/main.py examples/simple.yal --dfa
```

### Tokenizar un archivo de texto

```bash
python src/main.py tests/yal/low.yal --tokenize tests/input/low.txt
python src/main.py tests/yal/medium.yal --tokenize tests/input/medium.txt
python src/main.py tests/yal/high.yal --tokenize tests/input/high.txt
```

### Generar analizador léxico autónomo

```bash
python src/main.py tests/yal/medium.yal --generate output/lexer.py
```

El archivo generado es independiente y se ejecuta así:

```bash
python output/lexer.py tests/input/medium.txt
```

### Interfaz gráfica

```bash
python src/main.py examples/simple.yal --gui
```

O directamente:

```bash
python src/ui/app.py
```

## Restricciones cumplidas

- **Sin librerías de regex**: toda la funcionalidad de expresiones regulares se implementa mediante autómatas finitos (Thompson + subset construction).
- **Lexer independiente**: el archivo generado no depende del generador.
- **Interfaz gráfica**: incluida con tkinter (carga `.yal`, diagrama AFD, análisis léxico).
- **3 pares de prueba**: baja, media y alta complejidad.


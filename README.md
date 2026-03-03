# PRY1-DLP

Generador de analizadores léxicos (YALex -> analizador en Python),
implementado sin librerías de regexp/autómatas.

## Estado actual

La estructura **va bien** para la fase actual del proyecto:

- `src/yalex_parser/models.py`: modelos del archivo YALex.
- `src/yalex_parser/parser.py`: parser del archivo `.yal` (header, let, rule, trailer).
- `src/yalex_parser/regex_ast.py`: nodos AST para expresiones regulares.
- `src/yalex_parser/regex_parser.py`: parser de regex YALex a AST.
- `src/main.py`: CLI para parsear y mostrar salida JSON.
- `examples/simple.yal`: caso de prueba base.

Esta base es correcta porque ya separa: (1) lectura de especificación YALex y (2) representación intermedia de regex.

## Estructura recomendada (siguiente fase)

Para continuar de forma ordenada, se sugiere agregar estos módulos:

```text
src/
	main.py
	yalex_parser/
	automata/
		nfa.py
		dfa.py
		thompson.py
		subset_construction.py
		simulator.py
	codegen/
		python_generator.py
	ui/
		app.py
tests/
	yal/
		low.yal
		medium.yal
		high.yal
	input/
		low.txt
		medium.txt
		high.txt
```

## Ejecución actual

Desde la raíz del proyecto:

```bash
python src/main.py examples/simple.yal
```

Para incluir AST de expresiones regulares:

```bash
python src/main.py examples/simple.yal --ast
```

Para construir e imprimir AFN por Thompson:

```bash
python src/main.py examples/simple.yal --nfa
```

Para construir el AFN combinado del `rule` (con prioridad por orden):

```bash
python src/main.py examples/simple.yal --combined-nfa
```

## Próximos hitos

1. Construcción de AFN (Thompson) desde AST.
2. Conversión AFN -> AFD (subconjuntos).
3. Simulación del AFD para tokenización (maximal munch + prioridad por orden).
4. Generación del analizador léxico en Python independiente del generador.
5. Interfaz gráfica para cargar `.yal`, visualizar autómata y ejecutar análisis léxico.


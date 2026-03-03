# PRY1-DLP

Parser básico de YALex en Python (fase inicial del proyecto).

## Estructura inicial

- `src/yalex_parser/models.py`: modelos de datos del archivo YALex.
- `src/yalex_parser/parser.py`: parser simplificado (asume entrada válida).
- `src/main.py`: CLI para parsear un archivo `.yal`.
- `examples/simple.yal`: ejemplo de entrada.

## Ejecución

Desde la raíz del proyecto:

```bash
python src/main.py examples/simple.yal
```

Salida esperada: JSON con `header`, `lets`, `rule` y `trailer`.


# Casos de uso del IDE YALex (3 escenarios)

Este documento describe **3 casos de uso completos** para el IDE y cómo ejecutarlos.
También incluye el propósito de cada botón para asegurar que toda acción tenga sentido funcional.

---

## 1) Propósito de botones del IDE

| Botón | Propósito | Validado en casos |
|---|---|---|
| `Nuevo .yal` | Crear una especificación nueva desde plantilla mínima | Caso 1 |
| `Abrir` | Cargar archivo existente (`.yal`, `.txt`, `.py`) al panel correcto | Caso 2 y 3 |
| `Guardar` | Persistir cambios del editor activo al disco | Caso 1 |
| `Compilar` | Parsear YALex + construir AFD + dibujar diagrama + regenerar código | Caso 1 y 2 |
| `Generar Lexer` | Exportar lexer autónomo `.py` | Caso 3 |
| `Analizar` | Ejecutar análisis léxico sobre el texto de entrada | Caso 2 |
| `Cargar archivo` (tab análisis) | Cargar archivo de texto de entrada en editor de input | Caso 2 |
| `Ejecutar análisis` (tab análisis) | Mismo motor que `Analizar`, muestra tokens/errores/traza | Caso 2 |
| `Agregar` (explorador) | Alias de abrir archivos al IDE | Caso 2 y 3 |
| `Nuevo` (explorador) | Alias de crear `.yal` nuevo | Caso 1 |

> Nota: algunos botones comparten callback por diseño (por ejemplo `Analizar` y `Ejecutar análisis`).

---

## 2) Caso de uso 1 — Crear, editar, compilar y guardar una especificación

### Objetivo
Comprobar flujo de autoría manual en el IDE (estilo VS simplificado): crear archivo, escribir reglas, guardar y compilar.

### Pasos manuales
1. Click en `Nuevo .yal`.
2. Guardar como `uc1_new_spec.yal`.
3. En el editor `.yal`, escribir reglas (por ejemplo `ws`, `'a'`, `'+'`).
4. Click en `Guardar`.
5. Click en `Compilar`.

### Resultado esperado
- El archivo queda guardado en disco.
- Se construye AFD sin error.
- Se actualiza estado con texto `Compilado...`.
- Se renderiza diagrama en la pestaña `Diagrama AFD`.
- Se actualiza código en `Código Generado`.

---

## 3) Caso de uso 2 — Abrir `.yal`, cargar entrada, analizar y revisar traza

### Objetivo
Comprobar ejecución funcional del analizador desde IDE, incluyendo tokens y pasos/transiciones.

### Pasos manuales
1. Click en `Abrir` y seleccionar `tests/yal/medium.yal`.
2. Click en `Compilar`.
3. En pestaña `Análisis Léxico`, click en `Cargar archivo` y seleccionar `tests/input/medium.txt`.
4. Click en `Analizar` (o `Ejecutar análisis`).

### Resultado esperado
- Se muestran tokens en `Resultado`.
- Si no hay errores, no aparece bloque de errores léxicos.
- En pestaña `Trazas/Pasos` aparece la secuencia de transiciones del AFD.

---

## 4) Caso de uso 3 — Generar lexer autónomo y ejecutarlo

### Objetivo
Comprobar que la salida del IDE produce un lexer independiente funcional.

### Pasos manuales
1. Click en `Abrir` y seleccionar `tests/yal/low.yal`.
2. Click en `Compilar`.
3. Click en `Generar Lexer` y guardar como `uc3_generated_lexer.py`.
4. En terminal, ejecutar:
   ```bash
   python3 manual_cases/output/uc3_generated_lexer.py tests/input/low.txt
   ```

### Resultado esperado
- Se crea el archivo `.py` del lexer.
- El lexer generado corre sin depender del IDE.
- Imprime tokens válidos (por ejemplo `Token('NUMBER', ...)`).

---

## 5) Evidencia de validación ejecutada

Se ejecutó la validación automática de estos 3 casos con simulación real de callbacks de botones:

```bash
xvfb-run -a python3 manual_cases/scripts/ide_use_cases_validation.py
```

Salida observada:

- `[OK] UC1 create/edit/compile/save`
- `[OK] UC2 open/analyze/trace`
- `[OK] UC3 generate/execute lexer`
- `[OK] 3/3 use cases validados`

Script usado:
- `manual_cases/scripts/ide_use_cases_validation.py`

---

## 6) Recomendación de uso diario

- Usar `python3 src/main.py` para entrar siempre al IDE.
- Usar `python3 src/main.py --cli` cuando quieras menú por terminal.

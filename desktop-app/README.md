# YALex Studio (Tauri + React)

Interfaz desktop reutilizable para proyectos de análisis léxico.

## Objetivo

Proveer una interfaz desktop clara y rápida de usar, con apariencia tipo editor profesional,
enfocada únicamente en el flujo principal del pipeline YALex.

## Arquitectura

- Frontend: React + TypeScript + Vite (`desktop-app/src`).
- Shell desktop: Tauri (`desktop-app/src-tauri`).
- Motor: Python existente (`src/yalex_parser`).
- Bridge: `src/bridge_cli.py` (stdin JSON -> stdout JSON).

## Comandos

```bash
npm install
npm run tauri -- dev
```

Alternativa compatible en muchos entornos:

```bash
npm run tauri dev
```

## Funcionalidad soportada

- Explorer recursivo con expand/collapse.
- Apertura y edición de archivos de texto en pestañas.
- Guardado manual del archivo activo.
- Ejecución del pipeline con una acción activa por vez: `spec`, `ast`, `nfa`, `combinedNfa`, `dfa`, `tokenize`, `generate`.
- Campos contextuales por acción (solo se muestran cuando aplican).
- Panel `Resultado JSON` para respuesta estructurada y panel `Output` para estado/errores.
- Paneles redimensionables (Explorer, Pipeline, Resultado y Output) con persistencia local de tamaños.

## Flujo de uso rápido

1. Abre un archivo `.yal` desde el explorer.
2. Selecciona la acción en el panel `Pipeline`.
3. Completa inputs solo si la acción lo requiere (`tokenize` o `generate`).
4. Presiona `Ejecutar acción` y revisa resultado + output.

## Notas

- En Windows, el backend intenta `python` y luego `py -3` como fallback.
- La ruta de workspace se detecta automáticamente asumiendo que la app vive en `desktop-app/`.

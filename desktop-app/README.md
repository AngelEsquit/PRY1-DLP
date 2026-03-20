# YALex Studio (Tauri + React)

Interfaz desktop reutilizable para proyectos de análisis léxico.

## Objetivo

Proveer un layout estilo IDE (explorer, pestañas, output) sobre el motor Python actual,
sin duplicar la lógica de parsing/autómatas.

## Arquitectura

- Frontend: React + TypeScript + Vite (`desktop-app/src`).
- Shell desktop: Tauri (`desktop-app/src-tauri`).
- Motor: Python existente (`src/yalex_parser`).
- Bridge: `src/bridge_cli.py` (stdin JSON -> stdout JSON).

## Comandos

```bash
npm install
npm run tauri dev
```

## Funcionalidad soportada

- Navegar archivos del workspace con explorer recursivo (expand/collapse).
- Abrir/editar/guardar archivos de texto.
- Ejecutar acciones YALex: `spec`, `ast`, `nfa`, `combinedNfa`, `dfa`, `tokenize`, `generate`.
- Tokenizar por archivo o por texto directo desde la interfaz.
- Vista dividida editor + resultados JSON de la última ejecución.
- Mostrar resultados en panel output en formato JSON legible.

## Notas

- En Windows, el backend intenta `python` y luego `py -3` como fallback.
- La ruta de workspace se detecta automáticamente asumiendo que la app vive en `desktop-app/`.

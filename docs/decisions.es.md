# Registro de decisiones

[English](decisions.md) · **Español**

> La versión de referencia es la inglesa. Si alguna vez no coinciden, manda la inglesa.

Una entrada por decisión: contexto, opciones consideradas, decisión y cómo sabremos si era un error. La más reciente primero.

---

## ADR-005 · Chunking por estructura del RITE

**Fecha:** 2026-11-13 · **Estado:** aceptada

**Contexto.** El chunk es la unidad que se convierte en vector, se recupera, lee el LLM y se cita. El RITE tiene 228 unidades con encabezado: mediana de 110 palabras, 32 por encima de unas 400 (más de lo que cabe en 512 tokens), 34 encabezados sin texto propio y varias unidades con tablas.

**Opciones.** Tamaño fijo con solapamiento; recursivo por separadores; *semantic chunking*; por estructura; jerárquico (*parent-child*).

**Decisión.** Chunking por estructura (`ingest/chunk.py`):
- Un chunk por artículo, disposición, sección IT con texto propio y definición del Apéndice 1; uno por apéndice para el resto.
- Los encabezados sin texto propio (Parte, Capítulo, IT padres) solo aportan su título a la ruta de sus hijos.
- Las unidades largas se parten por sus apartados numerados ("1.", "2.") y, si no basta, por párrafos, hasta un **límite provisional de 300 palabras**. Cada trozo lleva un id propio (`#1`, `#2`) y la ruta completa. Nunca se juntan unidades distintas.
- Las tablas van dentro de su sección (`has_table`).
- Cada chunk guarda `text` (el cuerpo, para el prompt) y `embed_text` (ruta de títulos + cuerpo, para el embedding).
- Ids deterministas y legibles: `RITE:art-2`, `RITE:IT-1.1.4.1.2`, `RITE:AP1:aire-de-expulsion`.

**Por qué.** Es la unidad que usa el propio reglamento y la que se cita: un chunk = una unidad de sentido = una cita. El prefijo de ruta da contexto a las 42 unidades muy cortas sin duplicar contenido, como haría un solapamiento. Los ids estables hacen posible el golden set de la Fase 2.

**Resultado.** 389 chunks (mediana de 99 palabras, máximo 300); 49 unidades partidas en trozos; 106 definiciones (más la introducción del apéndice); 25 chunks con tabla. Los 47 artículos y las 130 secciones IT hoja tienen su chunk. Se conserva todo el texto de cuerpo (49 780 palabras en las unidades = en los chunks), y dos ejecuciones producen el mismo fichero. Señales de maquetación usadas: un párrafo nuevo va sangrado (x0 ≈ 107,7) y una línea de continuación no (x0 ≈ 90,7), lo que además permite unir los títulos que ocupan dos líneas.

**Consecuencias y limitaciones conocidas.**
- El límite está en palabras; en la pieza 3 de la Fase 1 se medirá en tokens del modelo de embeddings real y se ajustará.
- El prefijo de ruta es largo en las IT profundas (unas 40 palabras): ocupa una parte apreciable de la ventana. Si perjudica, se dejan solo los últimos niveles.
- Las tablas son texto plano con una celda por línea: un LLM puede leerlas, pero una pregunta sobre un valor concreto puede no recuperarlas bien.
- Si un apartado numerado supera el límite, una lista ("a), b)…") puede quedar separada de su frase de introducción.
- Las referencias cruzadas (`refs`) se detectan con patrones aproximados, solo dentro del Reglamento. No se usan hasta la Fase 6.

**Cómo sabremos si era un error.** Si en la Fase 2 falla la recuperación en preguntas cuya respuesta necesita el contexto del padre o de secciones vecinas, se prueba el chunking jerárquico. Si fallan las preguntas sobre valores de tablas, se reconstruyen las tablas como filas de texto ("Verano: temperatura operativa 23…25 °C, humedad relativa 45…60 %").

---

## ADR-004 · Corpus e ingesta del PDF: RITE y extracción que conserva la estructura

**Fecha:** 2026-11-13 · **Estado:** aceptada

**Contexto.** La Fase 1 necesita una sola norma de acceso libre que el autor pueda juzgar, y una ingesta que conserve la estructura suficiente para citar el artículo exacto. Los candidatos eran el REBT, el reglamento de ICT y un Documento Básico del CTE.

**Opciones.**
- Formato de origen: el PDF consolidado del BOE, o el HTML/XML consolidado que también publica el BOE, con los artículos ya etiquetados.
- Extracción: texto plano por página (`page.get_text()`), o líneas de texto con sus señales de maquetación (negrita, tamaño de letra, posición).

**Decisión.** Corpus: el RITE (Real Decreto 1027/2007, `BOE-A-2007-15820`), texto consolidado del BOE, última modificación del 02/08/2022. Ingesta desde el **PDF** con PyMuPDF, en dos etapas: `ingest/extract.py` produce líneas limpias con sus señales de maquetación (`bold_ratio`, tamaño, posición, página impresa) y elimina la maquetación del BOE (portada, índice, cabecera, pie y aviso legal final); el chunker (siguiente paso) decide la estructura. El extractor se para con un error si no encuentra el inicio del cuerpo ("TEXTO CONSOLIDADO"), y guarda el identificador del documento, la versión del corpus y el SHA-256 del PDF.

**Por qué.** El PDF es el caso realista: las normas UNE, los manuales y la documentación de obra solo existen en PDF, sin alternativa estructurada. Conservar las señales de maquetación en lugar de aplanar a texto permite al chunker usarlas; al revisar los datos reales se vio que los encabezados de artículo llevan negrita parcial (número en negrita, título en cursiva) y los de las instrucciones técnicas (IT) no, así que los encabezados IT se detectan por regex a principio de línea. Fallar pronto evita indexar el índice sin darse cuenta: sus líneas, que son solo títulos, ganarían a los chunks reales en la búsqueda. La versión y el hash permiten saber si un cambio en los resultados de la evaluación viene del código o del corpus.

**Consecuencias y limitaciones conocidas.**
- Los Apéndices 4 y 5 (modelos de declaración responsable) son imágenes en el PDF: su texto no se extrae. Se acepta, porque son plantillas de formulario y no requisitos técnicos.
- El PDF consolidado no dice qué norma posterior modificó cada artículo. Las relaciones "modifica" del grafo (Fase 6) tendrán que salir del HTML del BOE o de su página de análisis.
- Las tablas (8 y 6,5 pt, unas 800 líneas) se conservan como texto plano en orden de lectura; su estructura no se reconstruye en la Fase 1.
- Las zonas de cabecera y pie y los patrones son propios de la maquetación del consolidado del BOE.
- Validación: 12 pruebas (`tests/test_extract.py`), 5 unitarias con datos fabricados y 7 sobre la salida real (artículos 1-47 sin huecos, cada sección IT con su padre, sin restos de maquetación del BOE, páginas 5-96). Comprueban la estructura, no que esté cada palabra del PDF.

**Cómo sabremos si era un error.** Si en la Fase 2 los errores de evaluación se deben a la extracción (texto perdido, tablas desordenadas), o si añadir un segundo documento del BOE obliga a reescribir los patrones, se cambia la fuente al XML consolidado del BOE para los documentos del BOE y se mantiene el PDF para los que solo existen en PDF.

---

## ADR-003 · Conda solo para el intérprete; pip + pyproject.toml para las dependencias

**Fecha:** 2026-11-11 · **Estado:** aceptada

**Contexto.** El proyecto necesita un entorno de Python aislado y reproducible. La máquina de desarrollo es Windows con Miniconda, y además tiene en el PATH un Python 3.13 del sistema que no tiene nada que ver con el proyecto. A partir de la Fase 3 la aplicación se ejecuta en contenedores Docker, así que lo que declare las dependencias en local debería funcionar sin cambios dentro de una imagen.

**Opciones.**
- Entorno conda completo descrito en `environment.yml`: gestiona binarios que no son Python (CUDA), pero las imágenes Docker rara vez usan conda, así que las dependencias acabarían declaradas dos veces.
- venv + pip con `pyproject.toml`: el estándar de Python y exactamente lo que usa un Dockerfile, pero antes hace falta un intérprete de la versión correcta.
- uv con `pyproject.toml` y un lockfile: rápido y reproducible de serie, pero es una herramienta más que aprender en este momento.

**Decisión.** Conda solo proporciona un intérprete de Python 3.12. Todas las dependencias se declaran en `pyproject.toml` y se instalan con pip; en este entorno nunca se instala nada con `conda install`. El código vive en un paquete con `src/` layout (`rag_normainst`) instalado en modo editable (`pip install -e .`). Python 3.12 y no la versión más reciente porque las librerías de IA (torch, sentence-transformers, chromadb) van por detrás de las versiones nuevas de Python.

**Por qué.** Entre el portátil y el contenedor solo cambia de dónde sale el intérprete (conda en local, la imagen `python:3.12-slim` en Docker); la declaración de dependencias y el comando de instalación son los mismos, así que no hay nada que traducir. El `src/` layout obliga a hacer una instalación real, de modo que los errores de empaquetado aparecen en local y no dentro del contenedor.

**Consecuencias.** `pyproject.toml` declara rangos de versiones, así que el entorno local y una imagen Docker construida más tarde pueden resolver versiones distintas; en la Fase 3 se añadirá un lockfile. Hay que activar el entorno antes de instalar nada: la primera instalación fue por error al Python 3.13 del sistema, se detectó con `sys.executable` y `pip show`, y se corrigió.

**Cómo sabremos si era un error.** Si el Dockerfile necesita un segundo fichero de dependencias, o si fijar versiones con pip se vuelve engorroso en la Fase 3, se cambia a uv, que lee el mismo `pyproject.toml`.

---

## ADR-002 · Tamaño del modelo limitado por una GPU de 4 GB

**Fecha:** 2026-11-11 · **Estado:** aceptada

**Contexto.** La máquina de desarrollo tiene una GPU NVIDIA con 4 GB de VRAM. Todo se ejecuta en local con Ollama.

**Opciones.**
- Modelo de 7B cuantizado a 4 bits: unos 4-5 GB, no cabe entero en la VRAM. Ollama descarga capas a la CPU y la generación se ralentiza de forma notable.
- Modelo de 3-4B cuantizado a 4 bits: unos 2-3 GB, cabe entero y deja algo de margen para la KV cache.

**Decisión.** Empezar con un modelo Qwen de 3-4B en Q4. Mantener el modelo de embeddings pequeño o mediano y permitir que se ejecute en CPU durante la ingesta.

**Consecuencias.** Caben menos fragmentos recuperados en el prompt, así que la calidad del troceado y (más adelante) el re-ranking importan más. Un modelo pequeño es un LLM-as-a-judge más débil, así que la evaluación automática debe calibrarse contra el juicio humano.

**Cómo sabremos si era un error.** Si la corrección de las respuestas en el golden set está limitada por el generador y no por la recuperación (se recupera el artículo correcto pero la respuesta es incorrecta), probar un modelo mayor o Azure OpenAI a través del mismo cliente compatible con OpenAI.

---

## ADR-001 · Primero Python llano, LangChain después

**Fecha:** 2026-11-11 · **Estado:** aceptada

**Contexto.** El proyecto es una pieza de portfolio para entrevistas de ingeniería de IA. La credibilidad viene de explicar el mecanismo, no de ensamblar componentes de un framework.

**Opciones.**
- Empezar con LangChain para tener rápido una línea base que funcione, y después reescribirla a mano.
- Construir el pipeline en Python llano primero, medirlo, y después portarlo a LangChain.

**Decisión.** Primero Python llano (Fase 1), evaluación (Fase 2) y después un port a LangChain (Fase 2B) detrás de la misma interfaz `answer(question) -> Answer` y con el mismo script de evaluación. El port a LangChain reutiliza el chunker escrito a mano.

**Por qué no LangChain primero.** Sus valores por defecto esconden justo las partes que hay que entender: cómo se trocean los documentos, qué prompt se envía realmente y cómo selecciona el retriever los fragmentos. Empezar con ellos supone el riesgo de copiar código de tutorial sin entenderlo.

**Cómo sabremos si era un error.** La Fase 2B produce una tabla comparativa (métricas, líneas de código, dependencias). Si la versión con framework es claramente mejor en el golden set sin pérdida de control, se deja constancia aquí.

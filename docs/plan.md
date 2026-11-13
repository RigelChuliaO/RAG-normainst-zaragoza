# Plan de trabajo: Asistente RAG sobre normativa técnica (Python puro → LangChain)

11 de noviembre de 2026 · Versión interactiva: [`docs/dashboard/index.html`](dashboard/index.html) (ábrelo en el navegador)

## Estado actual (actualizado el 13 de noviembre de 2026)

> Si retomas el proyecto en una conversación nueva, empieza por aquí.

**Fase actual:** **Fase 1**. Pieza 1 (extracción) cerrada en `c30e6b6`. Pieza 2 (chunking): `chunk.py` hecho, revisado y con 16 pruebas (ADR-005); falta el commit. Después, pieza 3 (embeddings).

**Siguiente tarea:** la primera casilla sin marcar de la Fase 1, en [Tareas por fase](#tareas-por-fase).

### Progreso

Leyenda: ✅ terminada · 🔄 en curso · ⬜ sin empezar. En las listas, `[x]` hecho y `[ ]` pendiente.

| Fase | Estado | Tareas hechas | Horas (estimadas) |
| --- | --- | --- | --- |
| F0 · Repositorio y esqueleto | ✅ | 9 / 9 | 2 / 2 h |
| F1 · RAG mínimo en Python puro | 🔄 | 18 / 31 | 8,35 / 14 h |
| F2 · Evaluación | ⬜ | 0 / 10 | 0 / 8 h |
| F2B · Port a LangChain | ⬜ | 0 / 6 | 0 / 6 h |
| F3 · Docker | ⬜ | 0 / 11 | 0 / 12 h |
| F4 · API e interfaz | ⬜ | 0 / 8 | 0 / 8 h |
| F5 · Búsqueda híbrida y re-ranking | ⬜ | 0 / 6 | 0 / 10 h |
| F6 · Grafo de conocimiento | ⬜ | 0 / 8 | 0 / 20 h |
| F7 · Function calling y agentes | ⬜ | 0 / 7 | 0 / 12 h |
| F8 · Airflow (opcional) | ⬜ | 0 / 6 | 0 / 20 h |
| **Total** | | **27 / 102** | **10,35 / 112 h** |

**Cómo se trabaja en local (para no repetir errores ya cometidos):**

- Editor: **VS Code**, con terminal **cmd** por defecto (`.vscode/settings.json`, fuera de git). El 13/11 se ejecutó `conda init cmd.exe powershell`: `conda activate rag_nomainst-zara` ya funciona en las terminales de VS Code.
- El prompt tiene que verse así: `(rag_nomainst-zara) F:\MI IA\RAG>`. Comprobar con `python -c "import sys; print(sys.executable)"`: si sale `Python313`, el entorno no está activo.
- Instalar siempre con `python -m pip ...`. Tras cambiar dependencias en `pyproject.toml`: `python -m pip install -e ".[dev]"`. Los cambios en el código no lo necesitan.
- Los scripts con argumentos se ejecutan desde la terminal con `python -m ...` o con **F5** (configuraciones de `.vscode/launch.json`). **El botón ▶ de arriba a la derecha los ejecuta sin argumentos y fallan.**
- Pruebas: `python -m pytest -v`.
- Antes de cada commit, revisar `git status` (con `-uall` para ver fichero por fichero).

**Decisiones pendientes:**

- [x] **Corpus inicial:** RITE (RD 1027/2007, `BOE-A-2007-15820`), texto consolidado del BOE en PDF, última modificación 02/08/2022.
- [ ] **Modelo exacto de la GPU:** la VRAM ya se sabe (4 GB, ADR-002); falta `nvidia-smi` con modelo, VRAM libre y versión de CUDA.
- [ ] **Modelo de embeddings:** 2-3 candidatos multilingües pequeños o medianos; se decide con la evaluación, no a ojo.
- [x] **Tablas en los chunks:** en la Fase 1, texto tal cual + título de la tabla; mejora medible después.
- [ ] **Relaciones "modifica" (Fase 6):** no están en el PDF consolidado; hay que sacarlas del HTML o del análisis del BOE.
- [ ] **Pendiente técnico de la Fase 3:** lockfile con versiones exactas (ver ADR-003).

## Enfoque: Python puro primero, LangChain después

El plan sigue el orden del briefing: el RAG se construye a mano, se mide, y después se reimplementa con LangChain para ver qué te estaba abstrayendo. El núcleo son 50 h (unas 7 semanas a 8-10 h/semana); las extensiones suman otras 62 h.

El motivo es el del briefing: en entrevista te van a pedir que expliques el mecanismo. Si empiezas con LangChain, el troceado, el prompt que se envía y lo que hace el retriever por defecto quedan escondidos justo cuando los estás aprendiendo.

LangChain entra dos veces:

1. **Fase 2B:** reimplementar el RAG con LangChain, detrás de la misma interfaz y con el mismo conjunto de evaluación. Así la comparación sale con números, no con opiniones.
2. **Fase 7:** LangGraph, después de haber hecho function calling a mano.

Para que la comparación sea posible, desde la Fase 1 todo pasa por una función `answer(question) -> Answer` (texto, citas, ids recuperados). El script de evaluación la llama sin saber qué hay detrás.

### Qué implica tu GPU de 4 GB

Cifras aproximadas, a confirmar en tu máquina:

- **LLM:** un modelo de 3-4B parámetros cuantizado a 4 bits ocupa unos 2-3 GB y cabe entero en la VRAM. Un 7B en Q4 ocupa unos 4-5 GB: no cabe, Ollama reparte capas con la CPU y va bastante más lento. El DeepSeek de 7B queda para pruebas puntuales.
- **Contexto:** la caché de atención (*KV cache*) también consume VRAM. Meter muchos trozos en el prompt penaliza, así que un buen troceado y, en la Fase 5, un re-ranker que permita pasar menos trozos importan todavía más.
- **Embeddings:** basta con un modelo multilingüe pequeño o mediano. Indexar unos miles de trozos va bien incluso en CPU. Evita tener cargados a la vez en GPU el LLM y un modelo de embeddings grande.
- **Docker:** usar la GPU desde un contenedor en Windows exige WSL2 y NVIDIA Container Toolkit. Propuesta: Ollama sigue en el host y los contenedores lo llaman por `host.docker.internal`. Se decide al llegar a la Fase 3.

## Reglas que no cambian

- **Credenciales:** `.env` en el `.gitignore` desde el primer commit. El repositorio será público.
- **Derechos de autor:** no se sube ningún PDF de normativa. Solo el código de ingesta y, como mucho, una muestra pequeña de texto del BOE. Las normas UNE no entran en el corpus.
- **Todo en local:** Ollama como LLM, sin enviar documentos fuera. El mismo cliente sirve contra Azure OpenAI cambiando la URL base.
- **Cada fase termina en algo que funciona,** con commit y README actualizado (en inglés).
- **Registro de decisiones** (`docs/decisions.md`) actualizado en cada fase con el porqué de cada elección.
- **Comentarios en español,** también los del código (comentarios, docstrings y mensajes). Los nombres de funciones y variables, en inglés.
- **Mensajes de commit en español** (desde la Fase 1; los de la Fase 0 quedaron en inglés).

**Cómo trabajaremos en cada pieza:**

1. Problema y opciones con sus compromisos, antes de tocar código.
2. Errores típicos avisados de antemano.
3. Tú escribes el código. Yo te doy la estructura (firmas, esqueleto) y reviso. Cuando me pides que lo escriba yo, lo hago, y después me lo explicas.
4. Al terminar, te pregunto cómo sabrías que funciona y cuándo NO usarías esa pieza.
5. Explicaciones en español, con los términos técnicos en inglés.

## Fases

Las fases 0 a 4 son el proyecto; de la 5 en adelante, extensiones. Respecto al briefing solo cambia una cosa: se añade la Fase 2B (port a LangChain) justo después de la evaluación.

### Fase 0 — Repositorio y esqueleto · 2 h

**✅ Terminada.** Repositorio en GitHub, entorno conda solo para el intérprete con dependencias en `pyproject.toml`, paquete instalable con src layout, `.gitignore` con `.env`, `.gitattributes`, licencia MIT, README inicial y registro de decisiones.

- **Cambio respecto al plan inicial:** no hay `requirements.txt`; las dependencias van en `pyproject.toml` (ADR-003). Fijar versiones exactas sigue siendo necesario, pero se hace con un lockfile en la Fase 3, cuando haya imagen Docker que reproducir.
- **Error típico (vivido):** instalar sin el entorno activado y acabar en otro Python.
- **Entregable:** commits sin secretos ni PDFs, subidos a `main`.

### Fase 1 — RAG mínimo en Python puro · 14 h

Extracción con PyMuPDF, troceado por artículo, embeddings con `sentence-transformers`, Chroma embebido (cliente `chromadb` directo), prompt montado por una función propia y llamada a Ollama con el cliente `openai` contra su endpoint `/v1`.

- **Conceptos:** qué es un embedding y cómo se elige el modelo; por qué similitud del coseno (una vez, como ejercicio, la búsqueda con NumPy a mano); relación entre la ventana del modelo de embeddings y el tamaño del trozo; por qué el troceado lo condiciona todo.
- **Errores típicos:** artículos largos que superan la ventana del modelo de embeddings y se truncan sin aviso; perder el número de artículo en los metadatos y no poder citar; modelos tipo E5 que exigen los prefijos `query:` y `passage:`; con 4 GB, pasar demasiados trozos al prompt.
- **Cómo sabrías que funciona:** 5 preguntas cuya respuesta conoces, revisando a mano qué trozos se recuperaron, no solo la respuesta.
- **Entregable:** script que responde citando el artículo, detrás de `answer(question) -> Answer`.

**Hallazgos de la pieza 1 (extracción), comprobados sobre el PDF real** (detalle y limitaciones en el ADR-004):

- 97 páginas; el cuerpo va de la página 5 a la 96. 5205 líneas tras quitar cabecera, pie, portada, índice y el aviso legal final.
- Artículos y disposiciones: número en negrita + título en cursiva. Encabezados IT **sin negrita** y con la sangría de un párrafo: se detectan por regex, no por formato. Errata en el propio PDF: "IT 1.2. 4.7".
- Las tablas van en letra de 8 y 6,5 pt (unas 800 líneas).
- Los formularios de los Apéndices 4 y 5 son **imágenes**: su texto no se extrae. Limitación aceptada (no son requisitos técnicos).
- El PDF consolidado **no** trae las notas de qué norma modificó cada artículo.

### Fase 2 — Evaluación · 8 h · no se salta

Conjunto de referencia (*golden set*) de 30-50 preguntas escritas por ti, cada una con su artículo o artículos correctos y la respuesta esperada. Se miden por separado recuperación y generación.

- **Vocabulario estándar de lo que ya haces:** *hit rate@k*, *recall@k* y *MRR* para la recuperación; *faithfulness* (¿la respuesta dice lo que dice el contexto?) y *answer correctness* para la generación; *LLM-as-a-judge* y su calibración contra tu juicio; *regression suite*.
- **Ir más allá:** preguntas sin respuesta en el corpus (¿el sistema dice "no consta"?) como equivalente de tu categoría "otros"; desglose de errores por tipo de pregunta. Ojo: con un modelo de 3-4B como juez, la calibración contra tu juicio es obligatoria.
- **Entregable:** script de evaluación y la **baseline v0 (Python puro)** en el README.

### Fase 2B — Port a LangChain · 6 h

La misma tubería con `Document`, `Embeddings`, `VectorStore`/`Retriever`, `PromptTemplate`, `ChatOllama` y una cadena LCEL. El troceado no se sustituye: LangChain importa tu función de chunking, para que la comparación mida el framework y no un troceado distinto.

- **Antes de escribir nada:** para cada abstracción, señala qué función tuya de la Fase 1 sustituye.
- **Error típico:** que el prompt por defecto o el `k` del retriever no coincidan con los tuyos y la diferencia de métricas sea un artefacto. Hay que imprimir el prompt real que envía LangChain.
- **Pregunta clave:** ¿qué te da el framework y qué te esconde? Cuándo SÍ lo usarías y cuándo NO.
- **Entregable:** tabla Python puro vs LangChain en el README (métricas, líneas de código, dependencias). La línea principal sigue siendo Python puro.

### Fase 3 — Docker · 12 h · la de mayor retorno

Imagen vs contenedor, Dockerfile, capas y caché, volúmenes, redes, docker compose. Postgres con pgvector en un segundo contenedor y migración del almacén.

- **Error típico:** imágenes de varios GB por `torch` con CUDA cuando no hace falta; copiar el código antes de instalar dependencias y romper la caché.
- **Entregable:** `docker compose up` levanta todo, y la evaluación da lo mismo que antes de migrar.

### Fase 4 — API e interfaz · 8 h

FastAPI con esquemas Pydantic (el `Answer` de la Fase 1 pasa a ser un modelo Pydantic), documentación automática, Streamlit encima, tercer servicio en el compose. Con esto el proyecto ya es enseñable.

### Fases 5 a 8 — Extensiones

Iguales que en el briefing, cada una medida contra la baseline:

- **Fase 5 · Búsqueda híbrida y re-ranking · 10 h.** BM25 o full-text de Postgres + vectorial, re-ranker, filtros por metadatos en SQL. Si no mejora, se dice.
- **Fase 6 · Grafo de conocimiento · 20 h.** Neo4j en contenedor, Cypher, relaciones "referencia" y "modifica". Ruta de GraphAcademy del briefing.
- **Fase 7 · Function calling y agentes · 12 h.** Function calling a mano y sus modos de fallo; luego LangGraph. Agente que decide entre normativa, grafo o respuesta directa.
- **Fase 8 · Airflow · 20 h · opcional.** DAG de ingesta idempotente, presentado como vocabulario estándar de tu proceso nocturno.

## Tareas por fase

Se marcan con `[x]` al terminarlas, y se actualiza la tabla de [Progreso](#progreso). El dashboard (`docs/dashboard/index.html`) muestra estas mismas tareas y el panel «Qué toca ahora»: **se actualizan los dos a la vez**. La siguiente tarea es siempre la primera casilla sin marcar de la fase en curso. Las tareas de las fases futuras son una primera propuesta: se afinarán al llegar a cada una. Las horas son **estimadas** (en cursiva tras cada tarea) y las de cada fase suman sus horas del calendario; no son tiempo medido.

### F0 · Repositorio y esqueleto ✅

- [x] Repositorio público en GitHub, commits con el email *noreply*. · *0,25 h*
- [x] Entorno conda solo para el intérprete (Python 3.12); dependencias en `pyproject.toml` con pip (ADR-003). · *0,5 h*
- [x] Paquete `src/rag_normainst/` (src layout) instalado en modo editable y comprobado. · *0,25 h*
- [x] `.gitignore` con `.env` y `data/raw/*` (excepción `!data/raw/.gitkeep`). · *0,25 h*
- [x] `.gitattributes` con finales de línea LF. · *0,1 h*
- [x] Licencia MIT. · *0,1 h*
- [x] README inicial con el problema y la sección *Development setup*. · *0,2 h*
- [x] Registro de decisiones en inglés y español (ADR-001 a ADR-003). · *0,25 h*
- [x] Commits subidos a `main` (`fb7c187`, `da61f7d`, `20eb566`). · *0,1 h*

### F1 · RAG mínimo en Python puro 🔄

**Pieza 1 — Extracción del PDF**

- [x] Elegir el corpus: RITE consolidado (`BOE-A-2007-15820`, versión 02/08/2022). · *0,25 h*
- [x] Analizar la anatomía del PDF: portada, índice, cabecera, pie, artículos, IT, tablas, apéndices. · *0,5 h*
- [x] `ingest/extract.py`: líneas limpias con su formato → `data/interim/*.lines.jsonl` + `.meta.json`. · *1 h*
- [x] Validar la extracción: invariantes (páginas, restos de maquetación) y dominio (artículos 1-47 sin huecos, IT con su padre). · *0,5 h*
- [x] `ingest/inspect_extraction.py`: inspector visual PDF frente a lo extraído. · *0,5 h*
- [x] Filtrar el aviso legal de la última página. · *0,25 h*
- [x] `tests/test_extract.py`: 5 pruebas unitarias + 7 sobre los datos reales (12 en verde). · *0,75 h*
- [x] Configurar VS Code: intérprete, terminal cmd con conda, `launch.json` con argumentos. · *0,25 h*
- [x] `pytest` como dependencia de desarrollo (`.[dev]`) en `pyproject.toml`. · *0,1 h*
- [x] Ejercicio de *mutation testing*: borrar "Artículo 23." del `.lines.jsonl` y ver fallar el test. · *0,25 h*
- [x] Explicar con tus palabras: `bold_ratio`, el error de `split_front_matter`, el `sha256` (reducido a los principios transferibles: la ingesta condiciona la calidad, la estructura tiene que llegar a los metadatos para citar, fail fast y versionado de datos). · *0,5 h*
- [x] Anotar en `decisions.md`: corpus y versión, apéndices como imagen, notas de modificación ausentes (ADR-004). · *0,25 h*
- [x] Commit de la pieza 1 (`ingest/`, `tests/`, `pyproject.toml`, `plan.md`): `c30e6b6`. · *0,25 h*

**Pieza 2 — Chunking por estructura**

- [x] Diseño: unidad de chunk (artículo, disposición, subsección IT más profunda), ruta de ancestros como prefijo, tablas pegadas a su sección. · *0,5 h*
- [x] `ingest/chunk.py` → `data/processed/chunks.jsonl` con `id`, `doc`, `path`, `title`, `page_start`, `text`. · *1,25 h*
- [x] Detectar referencias cruzadas ("artículo 18", "IT 1.2.4") y guardarlas en `refs`. · *0,5 h*
- [x] Tests del chunker (`tests/test_chunk.py`, 16 pruebas): ningún chunk sin cuerpo, todos los artículos e IT presentes, ninguno partido entre dos unidades. · *0,5 h*
- [x] Inspeccionar a mano una muestra de chunks (uno corto, uno largo, uno con tabla). · *0,25 h*

**Pieza 3 — Embeddings e índice**

- [ ] `nvidia-smi`: modelo de GPU, VRAM libre y versión de CUDA. · *0,1 h*
- [ ] Concepto: qué es un embedding, cómo se elige el modelo, prefijos `query:`/`passage:` de E5. · *0,5 h*
- [ ] Elegir 2-3 modelos candidatos (p. ej. multilingual-e5-small/base, bge-m3) con su ventana de tokens. · *0,4 h*
- [ ] Medir la longitud de los chunks en tokens del modelo; partir los que superen la ventana. · *0,5 h*
- [ ] Indexar en Chroma embebido (`chromadb`), con los metadatos para citar. · *1 h*

**Pieza 4 — Recuperación**

- [ ] Ejercicio: similitud del coseno a mano con NumPy y comparar con Chroma. · *0,5 h*
- [ ] Búsqueda top-k con Chroma. · *0,25 h*
- [ ] 5 preguntas cuya respuesta conoces, revisando qué chunks se recuperan. · *0,5 h*

**Pieza 5 — Generación y entregable**

- [ ] Prompt con los chunks etiquetados; la cita la construye el código desde los metadatos. · *0,5 h*
- [ ] Cliente `openai` contra Ollama `/v1` (Qwen 3-4B en Q4). · *0,25 h*
- [ ] `answer(question) -> Answer` (texto, citas, ids recuperados). · *0,5 h*
- [ ] Script de línea de comandos que responde citando el artículo. · *0,25 h*
- [ ] README (inglés) y `decisions.md` actualizados; commit de la Fase 1. · *0,4 h*

### F2 · Evaluación ⬜

- [ ] Golden set de 30-50 preguntas escritas por ti, con artículos correctos y respuesta esperada. · *2 h*
- [ ] Incluir preguntas sin respuesta en el corpus (¿dice "no consta"?). · *0,5 h*
- [ ] Métricas de recuperación: *hit rate@k*, *recall@k*, *MRR*. · *1 h*
- [ ] Métricas de generación: *faithfulness* y *answer correctness*. · *1 h*
- [ ] *LLM-as-a-judge* calibrado contra tu juicio en una muestra. · *1 h*
- [ ] Desglose de errores por tipo de pregunta. · *0,5 h*
- [ ] `eval/run_eval.py --pipeline pure`, con resultados fechados en `eval/results/`. · *1 h*
- [ ] *Regression suite*: correr la evaluación al cambiar el prompt o el chunking. · *0,5 h*
- [ ] Baseline v0 publicada en el README. · *0,25 h*
- [ ] Commit de la Fase 2. · *0,25 h*

### F2B · Port a LangChain ⬜

- [ ] Tabla: cada abstracción de LangChain frente a la función de la Fase 1 que sustituye. · *0,5 h*
- [ ] `langchain_port/pipeline.py` con la misma interfaz `answer()`, reutilizando el chunking propio. · *2,5 h*
- [ ] Imprimir el prompt real que envía LangChain y alinear `k` y prompt con los tuyos. · *0,75 h*
- [ ] `run_eval.py --pipeline langchain`. · *0,5 h*
- [ ] Tabla Python puro vs LangChain en el README (métricas, líneas de código, dependencias). · *1 h*
- [ ] Cuándo SÍ y cuándo NO usar el framework, por escrito en `decisions.md`. · *0,75 h*

### F3 · Docker ⬜

- [ ] Conceptos: imagen frente a contenedor, capas y caché, volúmenes, redes, puertos, variables de entorno. · *2 h*
- [ ] Lockfile con versiones exactas (ADR-003). · *0,5 h*
- [ ] `Dockerfile` de la aplicación (dependencias antes que código, sin CUDA si no hace falta). · *2 h*
- [ ] Contenedor de Postgres con pgvector. · *1 h*
- [ ] Migrar el almacén de Chroma a pgvector. · *2 h*
- [ ] Volumen para que el índice sobreviva a reinicios. · *0,5 h*
- [ ] Conexión con Ollama en el host (`host.docker.internal`). · *1 h*
- [ ] `docker-compose.yml` con los servicios. · *1,5 h*
- [ ] Comprobar que la evaluación da lo mismo que antes de migrar. · *0,75 h*
- [ ] README: `docker compose up` como única orden. · *0,5 h*
- [ ] Commit de la Fase 3. · *0,25 h*

### F4 · API e interfaz ⬜

- [ ] Concepto: por qué un esquema Pydantic y no un diccionario. · *0,75 h*
- [ ] `Answer` como modelo Pydantic. · *0,5 h*
- [ ] FastAPI: endpoints de pregunta y salud. · *2 h*
- [ ] Revisar la documentación automática (`/docs`). · *0,25 h*
- [ ] Interfaz Streamlit que llama a la API. · *2,5 h*
- [ ] Tercer servicio en el compose. · *1 h*
- [ ] Capturas y diagrama de arquitectura en el README. · *0,75 h*
- [ ] Commit de la Fase 4. · *0,25 h*

### F5 · Búsqueda híbrida y re-ranking ⬜

- [ ] Por qué la búsqueda semántica falla con códigos y números de artículo. · *0,5 h*
- [ ] Búsqueda léxica (full-text de Postgres o BM25). · *2,5 h*
- [ ] Combinar léxica y vectorial. · *2 h*
- [ ] Re-ranker y cuándo compensa su coste. · *2,5 h*
- [ ] Filtros por metadatos en SQL. · *1 h*
- [ ] Medición contra la baseline (si no mejora, se dice). · *1,5 h*

### F6 · Grafo de conocimiento ⬜

- [ ] Cursos de GraphAcademy (Fundamentals, Cypher, Data Modeling, GenAI, GraphRAG). · *7,5 h*
- [ ] Modelo: nodos (documento, sección, artículo, concepto…) y aristas (contiene, referencia, modifica, aplica a). · *2 h*
- [ ] Fuente de las relaciones "modifica" (HTML o análisis del BOE). · *1,5 h*
- [ ] Neo4j en un contenedor. · *1 h*
- [ ] Carga del grafo desde los chunks y sus `refs`. · *2,5 h*
- [ ] Recuperación híbrida: vectorial + vecinos en el grafo. · *3 h*
- [ ] Medición contra la baseline en preguntas que necesiten artículos relacionados. · *1,5 h*
- [ ] (Opcional) La misma ontología en OWL/RDF con SPARQL. · *1 h*

### F7 · Function calling y agentes ⬜

- [ ] Function calling a mano: definiciones de herramientas, petición estructurada, ejecución, respuesta. · *3 h*
- [ ] Modos de fallo: argumentos mal formados, herramientas inventadas, bucles que no convergen. · *1,5 h*
- [ ] Herramientas: consultar normativa, buscar en el grafo, responder directamente. · *2 h*
- [ ] Agente que decide entre ellas. · *2 h*
- [ ] Reimplementar con LangGraph y comparar. · *2 h*
- [ ] Cuándo una cadena determinista gana a un agente. · *0,5 h*
- [ ] Medición y commit. · *1 h*

### F8 · Airflow (opcional) ⬜

- [ ] Planteamiento: vocabulario estándar de tu proceso nocturno de 10 000 documentos. · *1 h*
- [ ] DAG de ingesta: extraer, trocear, embeddings, cargar. · *8 h*
- [ ] Reintentos y programación. · *3 h*
- [ ] Relanzado por fechas (*backfill*). · *3 h*
- [ ] Idempotencia: relanzar sin duplicar. · *3,5 h*
- [ ] Commit y README. · *1,5 h*

## Calendario orientativo

A unas 9 h por semana, el núcleo (F0-F4, 50 h) termina en la semana 7 y las extensiones (62 h) en la 17. El diagrama interactivo está en el dashboard.

| Fase | Horas | Semanas | Tipo |
| --- | --- | --- | --- |
| F0 · Repositorio | 2 | 1 | Núcleo |
| F1 · RAG en Python puro | 14 | 1-2 | Núcleo |
| **F2 · Evaluación** | 8 | 3 | Núcleo |
| F2B · Port a LangChain | 6 | 4 | Núcleo |
| F3 · Docker | 12 | 5-6 | Núcleo |
| F4 · API e interfaz | 8 | 7 | Núcleo |
| F5 · Búsqueda híbrida | 10 | 8-9 | Extensión |
| F6 · Grafo | 20 | 10-12 | Extensión |
| F7 · Agentes | 12 | 13-14 | Extensión |
| F8 · Airflow | 20 | 15-17 | Opcional |

La evaluación (F2) va en negrita porque es la bisagra: sin ella el port a LangChain de la F2B no se puede comparar con nada. Si una fase se alarga, se recorta de las extensiones, nunca de la F2.

## Estructura del repositorio

```
RAG/
├── README.md                # en inglés: problema, arquitectura, cómo ejecutar, resultados
├── LICENSE                  # MIT
├── pyproject.toml           # metadatos y dependencias del paquete (pytest en el grupo dev)
├── .env.example             # variables sin valores reales
├── .gitignore               # .env, data/raw/*, data/interim/, data/processed/, índices
├── .gitattributes           # finales de línea LF
├── docs/
│   ├── plan.md              # este plan
│   ├── decisions.md         # registro de decisiones (inglés, referencia)
│   ├── decisions.es.md      # registro de decisiones (español)
│   └── dashboard/index.html # plan interactivo
├── data/
│   ├── raw/                 # PDFs, fuera de git (solo .gitkeep)
│   ├── interim/             # salidas intermedias (líneas extraídas, inspector), fuera de git
│   ├── processed/           # chunks listos para indexar, fuera de git
│   └── sample/              # muestra pequeña de texto del BOE
├── src/rag_normainst/       # línea principal, Python puro (Fase 1)
│   ├── __init__.py          # vacío; sin imports pesados
│   ├── config.py
│   ├── ingest/
│   │   ├── extract.py             # ✅ PDF → líneas limpias con formato
│   │   ├── inspect_extraction.py  # ✅ inspector visual PDF frente a lo extraído
│   │   └── chunk.py               # ✅ troceado por estructura (lo reutiliza la 2B)
│   ├── embeddings.py
│   ├── store.py
│   ├── generate.py
│   └── pipeline.py          # answer(question) -> Answer
├── langchain_port/          # Fase 2B
│   └── pipeline.py          # misma interfaz answer()
├── eval/
│   ├── golden_set.jsonl     # tus preguntas de referencia
│   ├── run_eval.py          # --pipeline pure | langchain
│   └── results/             # una ejecución por fichero, con fecha
└── tests/
    ├── test_extract.py      # ✅ 12 pruebas del extractor
    └── test_chunk.py        # ✅ 16 pruebas del chunker
```

El port a LangChain importa el chunking de `src/rag_normainst/ingest/chunk.py` en vez de usar un splitter propio del framework. Así la comparación mide lo que cambia el framework, no un troceado distinto.

## Decisiones pendientes y siguiente paso

Ver **Estado actual**, al principio de este documento.

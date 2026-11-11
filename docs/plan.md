# Plan de trabajo: Asistente RAG sobre normativa técnica (Python puro → LangChain)

11 de noviembre de 2026 · Versión interactiva: [`docs/dashboard/index.html`](dashboard/index.html) (ábrelo en el navegador)

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

**Cómo trabajaremos en cada pieza:**

1. Problema y opciones con sus compromisos, antes de tocar código.
2. Errores típicos avisados de antemano.
3. Tú escribes el código. Yo te doy la estructura (firmas, esqueleto) y reviso. No te pego código terminado, tampoco el de LangChain.
4. Al terminar, te pregunto cómo sabrías que funciona y cuándo NO usarías esa pieza.
5. Explicaciones en español, con los términos técnicos en inglés.

## Fases

Las fases 0 a 4 son el proyecto; de la 5 en adelante, extensiones. Respecto al briefing solo cambia una cosa: se añade la Fase 2B (port a LangChain) justo después de la evaluación.

### Fase 0 — Repositorio y esqueleto · 2 h

Repositorio en GitHub, entorno conda con `requirements.txt` de versiones fijadas, `.gitignore` con `.env`, README inicial con el problema que resuelve y `docs/decisions.md`.

- **Error típico:** no fijar versiones en `requirements.txt`. Con torch y sentence-transformers, una actualización silenciosa rompe el entorno, y con LangChain pasará lo mismo en la Fase 2B.
- **Entregable:** primer commit, sin secretos ni PDFs.

### Fase 1 — RAG mínimo en Python puro · 14 h

Extracción con PyMuPDF, troceado por artículo, embeddings con `sentence-transformers`, Chroma embebido (cliente `chromadb` directo), prompt montado por una función propia y llamada a Ollama con el cliente `openai` contra su endpoint `/v1`.

- **Conceptos:** qué es un embedding y cómo se elige el modelo; por qué similitud del coseno (una vez, como ejercicio, la búsqueda con NumPy a mano); relación entre la ventana del modelo de embeddings y el tamaño del trozo; por qué el troceado lo condiciona todo.
- **Errores típicos:** artículos largos que superan la ventana del modelo de embeddings y se truncan sin aviso; perder el número de artículo en los metadatos y no poder citar; modelos tipo E5 que exigen los prefijos `query:` y `passage:`; con 4 GB, pasar demasiados trozos al prompt.
- **Cómo sabrías que funciona:** 5 preguntas cuya respuesta conoces, revisando a mano qué trozos se recuperaron, no solo la respuesta.
- **Entregable:** script que responde citando el artículo, detrás de `answer(question) -> Answer`.

### Fase 2 — Evaluación · 8 h · no se salta

Conjunto de referencia (*golden set*) de 30-50 preguntas escritas por ti, cada una con su artículo o artículos correctos y la respuesta esperada. Se miden por separado recuperación y generación.

- **Vocabulario estándar de lo que ya haces:** *hit rate@k*, *recall@k* y *MRR* para la recuperación; *faithfulness* (¿la respuesta dice lo que dice el contexto?) y *answer correctness* para la generación; *LLM-as-a-judge* y su calibración contra tu juicio; *regression suite*.
- **Ir más allá:** preguntas sin respuesta en el corpus (¿el sistema dice "no consta"?) como equivalente de tu categoría "otros"; desglose de errores por tipo de pregunta. Ojo: con un modelo de 3-4B como juez, la calibración contra tu juicio es obligatoria.
- **Entregable:** script de evaluación y la **baseline v0 (Python puro)** en el README.

### Fase 2B — Port a LangChain · 6 h

La misma tubería con `Document`, `Embeddings`, `VectorStore`/`Retriever`, `PromptTemplate`, `ChatOllama` y una cadena LCEL. El troceado no se sustituye: LangChain importa tu función de `chunking.py`, para que la comparación mida el framework y no un troceado distinto.

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
├── .env.example             # variables sin valores reales
├── .gitignore               # .env, data/raw/, índices
├── requirements.txt         # versiones fijadas (Fase 0)
├── docs/
│   ├── plan.md              # este plan
│   ├── decisions.md         # registro de decisiones
│   └── dashboard/index.html # plan interactivo
├── data/
│   ├── raw/                 # PDFs, fuera de git
│   └── sample/              # muestra pequeña de texto del BOE
├── src/rag/                 # línea principal, Python puro (Fase 1)
│   ├── config.py
│   ├── ingest.py            # extracción con PyMuPDF
│   ├── chunking.py          # troceado por artículo (lo reutiliza la 2B)
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
```

El port a LangChain importa `src/rag/chunking.py` en vez de usar un splitter propio del framework. Así la comparación mide lo que cambia el framework, no un troceado distinto.

## Decisiones pendientes y siguiente paso

Antes de empezar la Fase 1 hacen falta tres respuestas tuyas:

- [ ] **Modelo exacto de la GPU:** ejecuta `nvidia-smi` y apunta modelo, VRAM libre y versión de CUDA. Con 4 GB, el LLM de partida es un Qwen de 3-4B en Q4.
- [ ] **Corpus inicial:** un solo texto de acceso libre para empezar. Candidatos: el REBT y sus ITC-BT, o el reglamento de ICT. Ambos publicados en el BOE.
- [ ] **Modelo de embeddings:** 2-3 candidatos multilingües pequeños o medianos, y se decide con la evaluación, no a ojo.

**Siguiente paso inmediato:** la Fase 0 (2 h). Cuando tengas el repositorio creado, empezamos la Fase 1 con la parte conceptual: qué es un embedding y cómo trocear un artículo de un reglamento sin perder la cita.

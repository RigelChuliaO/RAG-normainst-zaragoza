# Registro de decisiones

[English](decisions.md) · **Español**

> La versión de referencia es la inglesa. Si alguna vez no coinciden, manda la inglesa.

Una entrada por decisión: contexto, opciones consideradas, decisión y cómo sabremos si era un error. La más reciente primero.

---

## ADR-008 · Evaluación: golden set por unidad, nota por código y juez LLM solo como alarma

**Fecha:** 2026-11-18 · **Estado:** aceptada

**Contexto.** La Fase 2 necesita números que sigan siendo comparables al cambiar el prompt, el chunking o el modelo. El generador y el único juez local son modelos de 4B.

**Opciones.**
- Corregir las respuestas solo con un juez LLM (lo habitual en los tutoriales).
- Corregir con comprobaciones deterministas en código (datos obligatorios, datos prohibidos, «No consta», citas) y usar un juez para la fidelidad, que el código no puede comprobar.
- Comparar la recuperación por id de chunk, o por unidad del reglamento (artículo, instrucción técnica, definición).

**Decisión.**
- Golden set de 42 preguntas (`eval/golden_set.jsonl`) con **unidades** esperadas, para que sobreviva a los cambios de chunking; 6 preguntas sin respuesta; 8 reservadas.
- Recuperación y generación se miden por separado. Cada fallo de generación se diagnostica como fallo de recuperación (los datos no llegaron al modelo) o fallo de generación.
- La nota oficial es la del código (`correct`, `complete`). El juez LLM (`judge.py`) se usa como alarma de respuestas infieles, no como nota.

**Por qué.** Al calibrar el juez (qwen3:4b-instruct) sobre sus 30 respuestas salieron 28/30 de acuerdo y kappa de Cohen 0,71, pero dejó pasar 2 de las 5 respuestas infieles, entre ellas q30 («Sí, puedes instalar una caldera de carbón en una casa nueva»), el tipo de error más peligroso. Detecta las afirmaciones fuera de tema y se le escapan las conclusiones sacadas de la ausencia de una norma y las generalizaciones. Además juzga las respuestas de su propio modelo. Salvedad: las etiquetas de referencia las puso Claude, no un experto, porque los veredictos del juez se vieron antes de etiquetar.

**Cómo sabremos si era un error.** Si un juez más fuerte o distinto (un modelo local mayor, o Azure OpenAI con el mismo cliente) llega a kappa ≥ 0,6 sin dejar pasar ninguna respuesta infiel en una muestra etiquetada por una persona, el juez podrá entrar en la nota.

---

## ADR-007 · Generador: qwen3:4b-instruct en Ollama, con un prompt que solo deja citar etiquetas

**Fecha:** 2026-11-16 · **Estado:** aceptada (a confirmar con la evaluación de la Fase 2)

**Contexto.** La ADR-002 eligió un Qwen de 3-4B en Q4. En Ollama, la etiqueta `qwen3:4b` es ahora la variante *Thinking-2507*: siempre razona antes de responder, emite un `</think>` suelto y `--think=false` no lo desactiva. Con unos 2 GB de VRAM libres, el modelo se carga repartido entre CPU y GPU, con una ventana de 4096 tokens.

**Opciones.** `qwen3:4b` (razonador), `qwen3:4b-instruct` (Instruct-2507, sin razonamiento), `qwen3:1.7b` (híbrido, razona por defecto).

**Decisión.** Usar **`qwen3:4b-instruct`** con temperatura 0, a través del endpoint compatible con OpenAI (`/v1`) y el cliente `openai`. El prompt numera los fragmentos `[1]…[k]`; el modelo solo escribe esas etiquetas y el código las convierte en citas a partir de los metadatos, así que no puede inventarse un número de artículo. Si los fragmentos no contienen la respuesta, debe contestar exactamente «No consta en el RITE.». Si la pregunta nombra una IT o un artículo, ese chunk se busca primero por id (arregla la q04 de la semilla). Si el prompt llena la ventana de 4096 tokens, el código para con un error en vez de dejar que Ollama recorte sin avisar.

**Evidencia** (4 preguntas a mano, con el modelo ya cargado).
| | qwen3:4b-instruct | qwen3:1.7b |
| --- | --- | --- |
| «¿Qué es el RITE?» | correcta, cita el art. 1 (sin RAG se inventó un decreto) | – |
| Temperatura operativa en invierno | correcta (21–23 °C, IT 1.1.4.1.2), pero omite la humedad y la IT 3.8 | mezcla la IT 3.8 con datos de diseño, **sin cita**, 571 tokens de salida |
| «¿Qué dice la IT 1.2.4.7.4?» | correcta, encontrada por id | – |
| Sección de cable (no está en el RITE) | «No consta» | «No consta» (332 tokens de razonamiento) |
| Tiempo de generación | 12–21 s (~110 tok/s leyendo el prompt, ~20 tok/s escribiendo) | 12–20 s |

El 1.7b no es más rápido en total, porque sus tokens de razonamiento anulan su velocidad, y además rompe la regla de citar. El 4b-instruct es fiel pero a veces incompleto; pedir respuestas «concisas pero completas» no lo ha arreglado.

**Cómo sabremos que era un error.** Si la Fase 2 muestra respuestas fieles que se dejan condiciones presentes en los fragmentos recuperados (completitud), probar ejemplos *few-shot* en el prompt, menos fragmentos y mejor ordenados (re-ranking, Fase 5) o un modelo mayor con el mismo cliente.

---

## ADR-006 · Modelo de embeddings: primero multilingual-e5-base, comparado con e5-small y bge-m3

**Fecha:** 2026-11-14 · **Estado:** aceptada (a confirmar con la evaluación de la Fase 2)

**Contexto.** El modelo de embeddings convierte cada chunk y cada pregunta en un vector. Tiene que manejar castellano, admitir los chunks en su ventana y funcionar en la CPU: la GPU es una GTX 1650 de 4 GB, de los que el escritorio de Windows ya ocupa unos 2, y el resto se reserva para el LLM (ADR-002).

**Opciones** (datos de las fichas de los modelos en Hugging Face).
- `intfloat/multilingual-e5-small`: 384 dimensiones, ventana de 512 tokens, exige los prefijos `query: ` / `passage: `. El más rápido.
- `intfloat/multilingual-e5-base`: 768 dimensiones, ventana de 512 tokens, los mismos prefijos.
- `BAAI/bge-m3`: 568 M de parámetros, 1024 dimensiones, ventana de 8192 tokens, sin prefijos; además produce vectores *sparse* (léxicos).
- Descartado: `paraphrase-multilingual-MiniLM-L12-v2`, muy habitual en tutoriales, porque su ventana de 128 tokens truncaría la mayoría de los chunks.

**Decisión.** Empezar con **multilingual-e5-base** en la CPU, mediante `sentence-transformers`. Mantener e5-small y bge-m3 como candidatos para comparar con el golden set de la Fase 2. Lo propio de cada modelo (nombre, prefijos, ventana) vive en un solo sitio, `embeddings.py`, así que cambiar de modelo es un argumento.

**Por qué.** Con 389 chunks, indexar en la CPU es un coste de minutos que se paga una vez; lo que se repite es convertir cada pregunta en vector, y un modelo de unos 278 M de parámetros lo hace en la CPU en una fracción de segundo. e5-base es mejor que e5-small sin el tamaño de bge-m3. Sus prefijos obligatorios son un fallo silencioso clásico que conviene tratar de forma explícita.

**Riesgo.** La ventana de 512 tokens: los chunks están limitados a 300 palabras más el prefijo de ruta (ADR-005), y el castellano gasta más tokens por palabra que el inglés. Se miden los chunks con el tokenizer del propio modelo antes de indexar; si muchos superan la ventana, se baja el límite de palabras o se pasa a bge-m3.

**Cómo sabremos si era un error.** Si la Fase 2 muestra que bge-m3 recupera claramente mejor en el golden set, o que e5-small es igual de bueno y más rápido, la tabla comparativa va al README y se actualiza esta decisión.

---

## ADR-005 · Chunking por estructura del RITE

**Fecha:** 2026-11-13 · **Estado:** aceptada

**Contexto.** El chunk es la unidad que se convierte en vector, se recupera, lee el LLM y se cita. El RITE tiene 228 unidades con encabezado: mediana de 110 palabras, 32 por encima de unas 400 (más de lo que cabe en 512 tokens), 34 encabezados sin texto propio y varias unidades con tablas.

**Opciones.** Tamaño fijo con solapamiento; recursivo por separadores; *semantic chunking*; por estructura; jerárquico (*parent-child*).

**Decisión.** Chunking por estructura (`ingest/chunk.py`):
- Un chunk por artículo, disposición, sección IT con texto propio y definición del Apéndice 1; uno por apéndice para el resto.
- Los encabezados sin texto propio (Parte, Capítulo, IT padres) solo aportan su título a la ruta de sus hijos.
- Las unidades largas se parten por sus apartados numerados ("1.", "2.") y, si no basta, por párrafos, hasta un límite de **250 palabras** (al principio 300; ver la medida más abajo). Cada trozo lleva un id propio (`#1`, `#2`) y la ruta completa. Nunca se juntan unidades distintas.
- Las tablas van dentro de su sección (`has_table`).
- Cada chunk guarda `text` (el cuerpo, para el prompt) y `embed_text` (ruta de títulos + cuerpo, para el embedding).
- Ids deterministas y legibles: `RITE:art-2`, `RITE:IT-1.1.4.1.2`, `RITE:AP1:aire-de-expulsion`.

**Por qué.** Es la unidad que usa el propio reglamento y la que se cita: un chunk = una unidad de sentido = una cita. El prefijo de ruta da contexto a las 42 unidades muy cortas sin duplicar contenido, como haría un solapamiento. Los ids estables hacen posible el golden set de la Fase 2.

**Resultado.** 417 chunks (mediana de 109 palabras, máximo 250); 58 unidades partidas en trozos; 106 definiciones (más la introducción del apéndice); 26 chunks con tabla. Los 47 artículos y las 130 secciones IT hoja tienen su chunk. Se conserva todo el texto de cuerpo (49 780 palabras en las unidades = en los chunks), y dos ejecuciones producen el mismo fichero. Señales de maquetación usadas: un párrafo nuevo va sangrado (x0 ≈ 107,7) y una línea de continuación no (x0 ≈ 90,7), lo que además permite unir los títulos que ocupan dos líneas.

**Consecuencias y limitaciones conocidas.**
- **Medido en tokens (14/11/2026).** Con 300 palabras, 7 de 389 chunks superaban la ventana de 512 tokens de multilingual-e5-base (hasta 564 tokens): la lista de normas UNE del Apéndice 2 (los códigos cuestan unos 1,9 tokens por palabra, frente a 1,41 de media) y secciones IT profundas cuya ruta de títulos ocupa hasta 96 tokens. Se bajó el límite a 250 palabras. El límite en palabras es solo una aproximación barata: la garantía es una comprobación al indexar con el tokenizer del propio modelo, que para con un error si algún chunk no cabe en lugar de truncarlo en silencio.
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

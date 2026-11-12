# Registro de decisiones

[English](decisions.md) · **Español**

> La versión de referencia es la inglesa. Si alguna vez no coinciden, manda la inglesa.

Una entrada por decisión: contexto, opciones consideradas, decisión y cómo sabremos si era un error. La más reciente primero.

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

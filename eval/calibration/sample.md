# Calibración del juez: fidelidad

Para cada respuesta decide: ¿TODAS sus afirmaciones están en los fragmentos?
- **si** (fiel): nada inventado, aunque esté incompleta.
- **no** (no fiel): al menos una afirmación no está en los fragmentos, los contradice o los aplica a otro caso.

Apunta tu veredicto en `labels.csv` (columna `fiel`: si / no) ANTES de mirar lo que dice el juez.
Abajo van completos los fragmentos que la respuesta cita; de los demás, solo el título.

---

## q01 · ¿Qué calidad de aire interior se exige en una oficina?

**Respuesta del modelo:**

> La calidad de aire interior que se exige en una oficina es IDA 2 (aire de buena calidad) [1].

**Fragmentos que recibió:**

**[1] IT 1.1.4.2.2. Categorías de calidad del aire interior en función del uso de los edificios (pág. 30)** — citado

```
En función del uso del edificio o local, la categoría de calidad del aire interior (IDA) que se deberá alcanzar será, como mínimo, la siguiente:
IDA 1 (aire de óptima calidad): hospitales, clínicas, laboratorios y guarderías.
IDA 2 (aire de buena calidad): oficinas, residencias (locales comunes de hoteles y similares, residencias de ancianos y de estudiantes), salas de lectura, museos, salas de tribunales, aulas de enseñanza y asimilables y piscinas.
IDA 3 (aire de calidad media): edificios comerciales, cines, teatros, salones de actos, habitaciones de hoteles y similares, restaurantes, cafeterías, bares, salas de fiestas, gimnasios, locales para el deporte (salvo piscinas) y salas de ordenadores.
IDA 4 (aire de calidad baja)
```

- [2] IT 1.1.4.2.1. Generalidades (pág. 30) — no citado

- [3] IT 1.1.4.2.5. Aire de extracción. (pág. 33) — no citado

- [4] Artículo 11. Bienestar e higiene. (pág. 10) — no citado

- [5] IT 1.1.4.2.5. Aire de extracción. (pág. 33) — no citado

---

## q02 · ¿Qué significa IDA 2?

**Respuesta del modelo:**

> IDA 2 significa aire de calidad media [1].

**Fragmentos que recibió:**

**[1] Apéndice 1, definición «IDA 2». IDA 2 (pág. 88)** — citado

```
IDA 2: aire de calidad media.
```

- [2] Apéndice 1, definición «IDA 1». IDA 1 (pág. 88) — no citado

- [3] IT 1.1.4.2.2. Categorías de calidad del aire interior en función del uso de los edificios (pág. 30) — no citado

- [4] Apéndice 1, definición «IDA 3». IDA 3 (pág. 88) — no citado

- [5] Apéndice 1, definición «IDA 4». IDA 4 (pág. 88) — no citado

---

## q06 · ¿Qué temperatura operativa se exige en invierno?

**Respuesta del modelo:**

> En invierno, la temperatura operativa se exige entre 21 °C y 23 °C [1].

**Fragmentos que recibió:**

**[1] IT 1.1.4.1.2. Temperatura operativa y humedad relativa (pág. 29)** — citado

```
1. Las condiciones interiores de diseño de la temperatura operativa y la humedad relativa se fijarán con base en la actividad metabólica de las personas, su grado de vestimenta y el porcentaje estimado de insatisfechos (PPD), según los siguientes casos:
a) Para personas con actividad metabólica sedentaria de 1,2 met, con grado de vestimenta de 0,5 clo en verano y 1 clo en invierno y un PPD (porcentaje de personas insatisfechas) menor al 10 %, los valores de la temperatura operativa y de la humedad relativa, asumiendo un nivel de velocidad de aire bajo (<0.1 m / s), estarán comprendidos entre los límites indicados en la tabla 1.4.1.1.
Tabla 1.4.1.1 Condiciones interiores de diseño
Estación Temperatura operativa ºC Humedad relativa %
Verano
23...25
45...60
Invierno
21...23
40...50
Para el dimensionamiento de los sistemas de calefacción, se empleará una temperatura de cálculo de las condiciones interiores de 21 ºC. Para los sistemas de refrigeración la temperatura de cálculo será de 25 ºC.
b) Para valores diferentes de la actividad metabólica, grado de vestimenta, velocidad del aire y PPD del apartado a) es válido el cálculo de la temperatura operativa y la humedad relativa realizado por el procedimiento indicado en la norma UNE-EN ISO 7730
En este caso los valores para el dimensionamiento de sistemas de refrigeración son los valores superiores del rango de bienestar considerado y para los sistemas de calefacción los valores más bajos del rango de bienestar considerado.
```

- [2] IT 1.1.4.1.2. Temperatura operativa y humedad relativa (pág. 29) — no citado

- [3] IT 1.2.4.1.1. Criterios generales. (pág. 37) — no citado

- [4] IT 3.8. Limitación de temperaturas (pág. 80) — no citado

- [5] IT 1.2.4.1.3.3. Maquinaria frigorífica enfriada por aire (pág. 40) — no citado

---

## q18 · ¿A qué presión se hace la prueba de resistencia mecánica de un circuito de calefacción?

**Respuesta del modelo:**

> La presión de la prueba de resistencia mecánica de un circuito de calefacción depende de la temperatura máxima de servicio del circuito:
> 
> - Para circuitos cerrados de agua refrigerada o de agua caliente hasta una temperatura máxima de servicio de 100 °C, la presión de prueba será equivalente a una vez y media la presión máxima efectiva de trabajo a la temperatura de servicio, con un mínimo de 6 bar. [1]
> 
> - Para circuitos de agua caliente sanitaria, la presión de prueba será equivalente a dos veces la presión máxima efectiva de trabajo a la temperatura de servicio, con un mínimo de 6 bar. [1]
> 
> No consta en el RITE.

**Fragmentos que recibió:**

**[1] IT 2.2.2.4. Prueba de resistencia mecánica (pág. 71)** — citado

```
1. Esta prueba se efectuará a continuación de la prueba preliminar: una vez llenada la red con el fluido de prueba, se someterá a las uniones a un esfuerzo por la aplicación de la presión de prueba. En el caso de circuitos cerrados de agua refrigerada o de agua caliente hasta una temperatura máxima de servicio de 100 °C, la presión de prueba será equivalente a una vez y media la presión máxima efectiva de trabajo a la temperatura de servicio, con un mínimo de 6 bar; para circuitos de agua caliente sanitaria, la presión de prueba será equivalente a dos veces la presión máxima efectiva de trabajo a la temperatura de servicio, con un mínimo de 6 bar.
2. Para los circuitos primarios de las instalaciones de energía solar, la presión de la prueba será de una vez y media la presión máxima de trabajo del circuito primario, con un mínimo de 3 bar, comprobándose el funcionamiento de las líneas de seguridad.
3. Los equipos, aparatos y accesorios que no soporten dichas presiones quedarán excluidos de la prueba.
4. La prueba hidráulica de resistencia mecánica tendrá la duración suficiente para verificar visualmente la resistencia estructural de los equipos y tuberías sometidos a la misma.
```

- [2] IT 2.2.3. Pruebas de estanquidad de los circuitos frigoríficos (pág. 72) — no citado

- [3] IT 2.2.2.3. Prueba preliminar de estanquidad (pág. 71) — no citado

- [4] IT 1.3.4.2.2. Alimentación. (pág. 65) — no citado

- [5] IT 4.2.1. Inspecciones de los sistemas de calefacción, ventilación y agua caliente sanitaria. (pág. 82) — no citado

---

## q19 · ¿Cada cuánto se inspecciona un sistema de aire acondicionado?

**Respuesta del modelo:**

> Cada 4 años se inspecciona un sistema de aire acondicionado [2].

**Fragmentos que recibió:**

- [1] IT 4.2.2. Inspección de los sistemas de las instalaciones de aire acondicionado y ventilación. (pág. 83) — no citado

**[2] IT 4.3.2. Periodicidad de las inspecciones de los sistemas de aire acondicionado y ventilación. (pág. 84)** — citado

```
La inspección de eficiencia energética que viene obligada por la IT 4.2.2 se realizará cada 4 años.
```

- [3] IT 4.2.4. Expertos independientes. (pág. 84) — no citado

- [4] IT 4.2.2. Inspección de los sistemas de las instalaciones de aire acondicionado y ventilación. (pág. 83) — no citado

- [5] IT 4.2.2. Inspección de los sistemas de las instalaciones de aire acondicionado y ventilación. (pág. 83) — no citado

---

## q23 · Para una instalación de 30 kW, ¿basta con una memoria técnica?

**Respuesta del modelo:**

> Sí, basta con una memoria técnica para una instalación de 30 kW. [3]

**Fragmentos que recibió:**

- [1] IT 1.2.3. Documentación justificativa. (pág. 35) — no citado

- [2] Artículo 17. Memoria técnica. (pág. 13) — no citado

**[3] Artículo 15. Documentación técnica de diseño y dimensionado de las instalaciones térmicas. (pág. 12)** — citado

```
1. Las instalaciones térmicas incluidas en el ámbito de aplicación del RITE deben ejecutarse sobre la base de una documentación técnica que, en función de su importancia, debe adoptar una de las siguientes modalidades:
a) cuando la potencia térmica nominal a instalar en generación de calor o frío sea mayor que 70 kW, se requerirá la realización de un proyecto;
b) cuando la potencia térmica nominal a instalar en generación de calor o frío sea mayor o igual que 5 kW y menor o igual que 70 kW, el proyecto podrá ser sustituido por una memoria técnica;
c) no es preceptiva la presentación de la documentación anterior para acreditar el cumplimiento reglamentario ante el órgano competente de la Comunidad Autónoma para las instalaciones de potencia térmica nominal instalada en generación de calor o frío menor que 5 kW, las instalaciones de producción de agua caliente sanitaria por medio de calentadores instantáneos, calentadores acumuladores, termos eléctricos cuando la potencia térmica nominal de cada uno de ellos por separado o su suma sea menor o igual que 70 kW y los sistemas solares consistentes en un único elemento prefabricado.
```

- [4] Artículo 15. Documentación técnica de diseño y dimensionado de las instalaciones térmicas. (pág. 12) — no citado

- [5] Artículo 15. Documentación técnica de diseño y dimensionado de las instalaciones térmicas. (pág. 12) — no citado

---

## q25 · ¿Cuándo es obligatorio firmar un contrato de mantenimiento?

**Respuesta del modelo:**

> Es obligatorio firmar un contrato de mantenimiento en los siguientes casos:
> 
> - Cuando la potencia térmica nominal total instalada en generación de calor o frío sea mayor que 70 kW [4].  
> - Cuando la potencia térmica nominal total instalada sea mayor que 5.000 kW en calor y/o 1.000 kW en frío, así como en instalaciones de calefacción o refrigeración solar cuya potencia térmica sea mayor que 400 kW [4].  
> 
> Además, en todos estos casos, el mantenimiento debe realizarse bajo la dirección de un técnico titulado competente con funciones de director de mantenimiento [4].  
> 
> No consta en el RITE.

**Fragmentos que recibió:**

- [1] Artículo 27. Registro de las operaciones de mantenimiento. (pág. 19) — no citado

- [2] Artículo 28. Certificado de mantenimiento. (pág. 19) — no citado

- [3] Disposición adicional segunda. Obligaciones de información. (pág. 28) — no citado

**[4] Artículo 26. Mantenimiento de las instalaciones. (pág. 18)** — citado

```
6. El mantenimiento de las instalaciones sujetas a este RITE será realizado de acuerdo con lo establecido en la IT 3, atendiendo a los siguientes casos:
a) Instalaciones térmicas con potencia térmica nominal total instalada en generación de calor o frío igual o superior a 5 kW e inferior o igual a 70 kW.
Estas instalaciones se mantendrán por una empresa mantenedora, que debe realizar su mantenimiento de acuerdo con las instrucciones contenidas en el «Manual de Uso y Mantenimiento».
b) Instalaciones térmicas con potencia térmica nominal total instalada en generación de calor o frío mayor que 70 kW.
Estas instalaciones se mantendrán por una empresa mantenedora con la que el titular de la instalación térmica debe suscribir un contrato de mantenimiento, realizando su mantenimiento de acuerdo con las instrucciones contenidas en el «Manual de Uso y Mantenimiento».
c) Instalaciones térmicas cuya potencia térmica nominal total instalada sea mayor que 5.000 kW en calor y/o 1.000 kW en frío, así como las instalaciones de calefacción o refrigeración solar cuya potencia térmica sea mayor que 400 kW.
Estas instalaciones se mantendrán por una empresa mantenedora con la que el titular debe suscribir un contrato de mantenimiento. El mantenimiento debe realizarse bajo la dirección de un técnico titulado competente con funciones de director de mantenimiento, ya pertenezca a la propiedad del edificio o a la plantilla de la empresa mantenedora.
```

- [5] Artículo 25. Titulares y usuarios. (pág. 18) — no citado

---

## q27 · En un edificio con ACS centralizada, ¿cada vecino debe tener su propio contador?

**Respuesta del modelo:**

> Sí, en un edificio con agua caliente sanitaria (ACS) centralizada, cada vecino debe tener su propio contador individual para el consumo de agua caliente sanitaria [1].

**Fragmentos que recibió:**

**[1] IT 1.2.4.4. Contabilización de consumos. (pág. 50)** — citado

```
1. Toda instalación térmica que dé servicio a más de un usuario dispondrá de algún sistema que permita el reparto de los gastos correspondientes a cada servicio (calor, frío y agua caliente sanitaria) entre los diferentes usuarios, en el caso del agua caliente sanitaria deberá ser un contador individual. El sistema previsto, instalado en el tramo de acometida a cada unidad de consumo, permitirá regular y medir los consumos, así como interrumpir los servicios desde el exterior de los locales.
Las instalaciones térmicas que suministren calefacción o refrigeración a un edificio a partir de una instalación centralizada que abastezca a varios consumidores y a los titulares que reciben dicho suministro desde una red de calefacción o refrigeración urbana, definidas en el apéndice 1 de este Reglamento, cuando dichas instalaciones térmicas no dispongan de un sistema que permita el reparto de los gastos correspondientes a cada servicio (calor y frío) entre los diferentes consumidores, deberán cumplir con las obligaciones establecidas en la normativa que regule la contabilización de consumos individuales en instalaciones de edificios.
Los clientes finales de los edificios abastecidos a partir de una red urbana de calefacción, refrigeración o agua caliente sanitaria, recibirán, por parte del titular de la red, contadores individuales, de precio razonable y asequible de acuerdo con los estándares del mercado, que reflejen con precisión su consumo real de energía.
```

- [2] IT 1.2.4.4. Contabilización de consumos. (pág. 50) — no citado

- [3] IT 1.3.4.1.2.2. Características comunes de los locales destinados a sala de máquinas (pág. 57) — no citado

- [4] Artículo 28. Certificado de mantenimiento. (pág. 19) — no citado

- [5] IT 1.3.4.4.3. Accesibilidad. (pág. 69) — no citado

---

## q28 · ¿Puedo poner estufas de gas en la terraza de un bar?

**Respuesta del modelo:**

> Sí, puede colocarse una estufa de gas en la terraza de un bar, siempre que se cumplan las condiciones de evacuación de los productos de la combustión establecidas en el RITE, específicamente en el apartado IT 1.3.4.1.3.3 [1][3].
> 
> Para ello:
> 
> - Si el eje del tubo de salida de los productos de la combustión se encuentra a una distancia **igual o inferior a 30 cm** respecto del techo de la terraza, debe prolongarse hacia el límite del techo de la terraza, balcón o galería, manteniendo una distancia máxima de **10 cm** entre el extremo del tubo y el techo, prevaleciendo las indicaciones del fabricante [1]b1).
> 
> - Si el eje del tubo se encuentra a una distancia **superior a 30 cm**, el extremo del tubo no debe sobresalir de la pared que atraviesa más de **10 cm**, prevaleciendo las indicaciones del fabricante [1]b2).
> 
> - Si la salida se realiza a través de una cornisa o balcón en cota superior a la de salida de los productos de la combustión, se debe seguir el mismo criterio que en el caso b), considerando el límite de la cornisa o balcón [1]c).
> 
> - En el caso de una terraza, balcón o galería **cerrada con sistema permanente**, posterior a la instalación del aparato, los tubos deben prolongarse para atravesar el cerramiento, siguiendo los mismos criterios que a través de muro o celosía [1]c).
> 
> - Además, cuando la salida de los productos de la combustión se realice directamente al exterior a través de una pared, el eje del conducto debe situarse, como mínimo, a **2,20 m** del nivel del suelo más próximo con tránsito o permanencia de personas, medido en sentido vertical [3].
> 
> - Se exceptúan de este requisito las salidas de productos de la combustión de **radiadores murales de tipo ventosa de potencia inferior a 4,2 kW**, siempre que estén protegidas adecuadamente [3].
> 
> Además, se debe garantizar que el sistema de detección y corte de fugas de gas esté instalado, especialmente en salas de máquinas con calderas a gas, en caso de no lograrse la superficie no resistente al exterior o a patio de ventilación [2]3.
> 
> Por último, en edificios existentes, se permite una ventilación forzada y un sistema de detección y corte de fugas de gas si no se logra la superficie no resistente al exterior [2]3.
> 
> Por tanto, la instalación de estufas de gas en la terraza de un bar es posible siempre que se cumplan estas condiciones técnicas y se respeten las distancias mínimas y las exigencias de evacuación de productos de la combustión establecidas en el RITE [1][3][2]. 
> 
> No consta en el RITE.

**Fragmentos que recibió:**

**[1] IT 1.3.4.1.3.3. Evacuación por conducto con salida directa al exterior o a patio de ventilación (pág. 63)** — citado

```
b1) El eje del tubo de salida de los productos de la combustión se encuentra a una distancia igual o inferior a 30 cm respecto del techo de la terraza, balcón o galería, medidos perpendicularmente.
En esta situación, dicho tubo se debe prolongar hacia el límite del techo de la terraza, balcón o galería de forma que entre el mismo y el extremo del tubo se guarde una distancia máxima de 10 cm, prevaleciendo las indicaciones que el fabricante facilite al respecto.
b2) El eje del tubo de salida de los productos de la combustión se encuentra a una distancia superior a 30 cm respecto del techo de la terraza, balcón o galería, medidos perpendicularmente. En esta situación, el extremo de dicho tubo no debe sobresalir de la pared que atraviesa más de 10 cm, prevaleciendo las indicaciones que el fabricante facilite al respecto.
c) A través de fachada, celosía o similar, existiendo una cornisa o balcón en cota superior a la de salida de los productos de la combustión. Se debe seguir el mismo criterio que en el caso b), siendo el límite a considerar el de la cornisa o balcón.
```

**[2] IT 1.3.4.1.2.8. Medidas especificas para edificación existente (pág. 61)** — citado

```
Para las salas de máquinas en edificios existentes se consideran válidos los mismos criterios detallados en los apartados anteriores, si bien cuando ello no sea posible se admiten las siguientes excepciones:
1. Dimensiones
Las dimensiones indicadas en la IT 1.3.4.1.2.2 y en la IT 1.3.4.1.2.3, podrán modificarse de manera justificada, siempre que se garantice el mantenimiento de los equipos instalados; en el caso concreto de las calderas se deberá incluir la documentación aportada por el fabricante de las mismas, en la cual se detalle el mencionado aspecto.
2. Patio de ventilación
En edificios ya construidos, dicho patio podrá tener una superficie mínima en planta de 3 m2 y la dimensión del lado menor será como mínimo de 1 m.
3. Salas de máquinas con calderas a gas en las que no se logre la superficie no resistente
En las reformas de las salas de máquinas en edificios existentes con calderas de gas, en las que no sea posible lograr la superficie no resistente al exterior, o a patio de ventilación, se realizará una ventilación forzada y se instalará un sistema de detección y corte de fugas de gas.
4. Emplazamiento
No está permitida la ubicación de salas máquinas con calderas a gas en niveles inferiores a semisótano o primer sótano; en las reformas de salas por debajo de ese nivel se deberá habilitar un nuevo local para las calderas.
```

**[3] IT 1.3.4.1.3.3. Evacuación por conducto con salida directa al exterior o a patio de ventilación (pág. 63)** — citado

```
d) Aparato situado en el exterior, en una terraza, balcón o galería abiertos y techados. De forma general se debe seguir el mismo criterio que en los casos b) y c), con la salvedad de que cuando el eje del tubo de salida de los productos de la combustión se encuentre a una distancia superior a 30 cm respecto del techo de la terraza, balcón o galería, la longitud del tubo de salida de los productos de la combustión debe ser la mínima indicada por el fabricante.
Si en los casos b) o d) la terraza, balcón o galería fuese cerrada con sistema permanente, con posterioridad a la instalación del aparato, los tubos de salida de los productos de la combustión se deben prolongar para atravesar el cerramiento siguiendo los mismos criterios que a través de muro o celosía indicados en el caso a).
En cualquiera de los casos anteriores, y de forma general, cuando la salida de los productos de la combustión se realice directamente al exterior a través de una pared, el eje del conducto de evacuación de los productos de la combustión se debe situar, como mínimo, a 2,20 m del nivel del suelo más próximo con tránsito o permanencia de personas, medidos en sentido vertical. Se exceptúan de este requisito, las salidas de productos de la combustión de los radiadores murales de tipo ventosa de potencia inferior a 4,2 kW, siempre y cuando estén protegidas adecuadamente para evitar el contacto directo.
```

- [4] IT 1.3.4.1.2.2. Características comunes de los locales destinados a sala de máquinas (pág. 57) — no citado

- [5] IT 1.3.4.1.3.3. Evacuación por conducto con salida directa al exterior o a patio de ventilación (pág. 63) — no citado

---

## q29 · ¿Se puede climatizar un trastero o un garaje?

**Respuesta del modelo:**

> Sí, se puede climatizar un trastero o un garaje, siempre que se cumplan las condiciones establecidas en el RITE.  
> 
> Según el fragmento [2], la climatización de espacios abiertos solo podrá realizarse mediante la utilización de energías renovables o residuales. No podrá utilizarse energía convencional para la generación de calor y frío destinado a la climatización de estos espacios.  
> 
> Además, según el fragmento [7], en espacios destinados a almacenes, talleres, naves industriales u otros recintos especiales, podrán ser utilizados equipos de generación de calor de hogar abierto, o que viertan los productos de la combustión al local a calentar, siempre que se justifique que la calidad del aire del recinto no se vea afectada negativamente, indicándose las medidas de seguridad adoptadas para tal fin.  
> 
> Por tanto, aunque el trastero o garaje no sea un espacio habitable, puede ser climatizado si se utilizan energías renovables o residuales, y si se justifica que la calidad del aire no se vea afectada, con medidas de seguridad adecuadas.  
> 
> [2][7]

**Fragmentos que recibió:**

- [1] IT 1.3.4.1.1. Condiciones Generales (pág. 55) — no citado

**[2] IT 1.2.4.6.3. Climatización de espacios abiertos. (pág. 53)** — citado

```
La climatización de espacios abiertos sólo podrá realizarse mediante la utilización de energías renovables o residuales. No podrá utilizarse energía convencional para la generación de calor y frío destinado a la climatización de estos espacios.
```

- [3] IT 1.2.4.5.1. Enfriamiento gratuito por aire exterior. (pág. 51) — no citado

- [4] IT 3.8. Limitación de temperaturas (pág. 80) — no citado

- [5] Artículo 2. Ámbito de aplicación. (pág. 8) — no citado

---

## q30 · ¿Puedo instalar una caldera de carbón en una casa nueva?

**Respuesta del modelo:**

> Sí, puedes instalar una caldera de carbón en una casa nueva, siempre que se cumplan los requisitos de accesibilidad y espacio libre establecidos para las salas de máquinas.
> 
> Según [3], para calderas de combustibles sólidos, la distancia entre ellas y la chimenea será al menos igual al tamaño de la caldera, y si es necesaria la accesibilidad al hogar para carga o reparto del combustible, el espacio frontal será al menos una vez y media la profundidad de la caldera. Además, en el caso de calderas de biocombustibles sólidos con retirada manual de cenizas, el espacio frontal será al menos una vez y media la profundidad de la caldera.
> 
> No hay en los fragmentos una prohibición específica para calderas de carbón en edificios de nueva construcción, por lo que, si se cumplen las condiciones de espacio y accesibilidad para las salas de máquinas, como se especifican en [1][3], la instalación es permitida.
> 
> No consta en el RITE.

**Fragmentos que recibió:**

**[1] IT 1.3.4.1.2.2. Características comunes de los locales destinados a sala de máquinas (pág. 57)** — citado

```
1. Las instalaciones térmicas deberán ser perfectamente accesibles en todas sus partes de forma que puedan realizarse adecuadamente y sin peligro todas las operaciones de mantenimiento, vigilancia y conducción.
2. La altura mínima de la sala será de 2,50 m; respetándose una altura libre de tuberías y obstáculos sobre la caldera de 0,5 m.
3. Los espacios mínimos libres que deben dejarse alrededor de los generadores de calor, según el tipo de caldera, serán los que se señalan a continuación, o los que indique el fabricante, cuando sus exigencias superen las mínimas anteriores:
a) Calderas con quemador de combustión forzada.
Para estas calderas el espacio mínimo será de 0,5 m entre uno de los laterales de la caldera y la pared permitiendo la apertura total de la puerta sin necesidad de desmontar el quemador, y de 0,7 m entre el fondo de la caja de humos y la pared de la sala.
Cuando existan varias calderas, la distancia mínima entre ellas será de 0,5 m, siempre permitiendo la apertura de las puertas de las calderas sin necesidad de desmontar los quemadores.
El espacio libre en la parte frontal será igual a la profundidad de la caldera, con un mínimo de un metro; en esta zona se respetará una altura mínima libre de obstáculos de 2 m.
b) Calderas de cámara de combustión abierta y tiro natural.
```

- [2] IT 1.3.4.1.2.8. Medidas especificas para edificación existente (pág. 61) — no citado

**[3] IT 1.3.4.1.2.2. Características comunes de los locales destinados a sala de máquinas (pág. 57)** — citado

```
El espacio libre en el frente de la caldera será como mínimo de 1 m, con una altura mínima de 2 m libre de obstáculos.
Entre calderas, así como las calderas extremas y los muros laterales y de fondo, debe existir un espacio libre de al menos 0,5 m que podrá disminuirse en los modelos en que el mantenimiento de las calderas y su aislamiento térmico lo permita. Deben tenerse en cuenta las recomendaciones del fabricante.
En el caso de que las calderas a instalar sean del tipo mural y/o modular formando una batería de calderas o cuando las paredes laterales de las calderas a instalar no precisen acceso, puede reducirse la distancia entre ellas, teniendo en cuenta el espacio preciso para poder efectuar las operaciones de desmontaje de la envolvente y del mantenimiento de las mismas.
Con calderas de combustibles sólidos, la distancia entre éstas y la chimenea será igual, al menos, al tamaño de la caldera.
Las calderas de combustibles sólidos en las que sea necesaria la accesibilidad al hogar, para carga o reparto del combustible, tendrán un espacio libre frontal igual, por lo menos, a una vez y media la profundidad de la caldera.
Las calderas de biocombustibles sólidos en las que la retirada de cenizas sea manual, tendrán un espacio libre frontal igual, por lo menos, a vez y media la profundidad de la caldera.
```

- [4] IT 1.3.4.1.3.1. Evacuación de los productos de la combustión (pág. 62) — no citado

- [5] IT 1.2.4.1.2.1. Requisitos mínimos de rendimientos energéticos de los generadores de calor. (pág. 38) — no citado

---

## q31 · ¿Se puede usar calefacción eléctrica con resistencias en una instalación centralizada?

**Respuesta del modelo:**

> Sí, se puede usar calefacción eléctrica con resistencias en una instalación centralizada, pero solo bajo las siguientes condiciones [1]:
> 
> a) En instalaciones con bomba de calor, cuando la relación entre la potencia eléctrica en resistencias de apoyo y la potencia eléctrica en bornes del motor del compresor sea igual o inferior a 1,2.  
> 
> b) En locales servidos por instalaciones que usen fuentes de energía renovable o energía residual, y que empleen la energía eléctrica como fuente auxiliar de apoyo, siempre que el grado de cobertura de las necesidades energéticas anuales por parte de la fuente de energía renovable o energía residual sea mayor que dos tercios.  
> 
> c) En locales servidos con instalaciones de generación de calor mediante sistemas de acumulación térmica, siempre que la capacidad de acumulación sea suficiente para captar y retener durante las horas de suministro eléctrico tipo «valle», definidas para la tarifa eléctrica regulada, la demanda térmica total diaria prevista en proyecto, y se justifique en la memoria el número de horas al día de cobertura de dicha demanda por el sistema de acumulación sin necesidad de acoplar su generador de calor a la red de suministro eléctrico.  
> 
> No consta en el RITE.

**Fragmentos que recibió:**

**[1] IT 1.2.4.7.1. Limitación de la utilización de energía convencional para la producción de calefacción centralizada. (pág. 53)** — citado

```
La utilización de energía eléctrica directa por «efecto Joule» para la producción de calefacción, en instalaciones centralizadas solo estará permitida en:
a) Las instalaciones con bomba de calor, cuando la relación entre la potencia eléctrica en resistencias de apoyo y la potencia eléctrica en bornes del motor del compresor, sea igual o inferior a 1,2.
b) Los locales servidos por instalaciones que, usando fuentes de energía renovable o energía residual, empleen la energía eléctrica como fuente auxiliar de apoyo, siempre que el grado de cobertura de las necesidades energéticas anuales por parte de la fuente de energía renovable o energía residual sea mayor que dos tercios.
c) Los locales servidos con instalaciones de generación de calor mediante sistemas de acumulación térmica, siempre que la capacidad de acumulación sea suficiente para captar y retener durante las horas de suministro eléctrico tipo «valle», definidas para la tarifa eléctrica regulada, la demanda térmica total diaria prevista en proyecto, debiéndose justificar en su memoria el número de horas al día de cobertura de dicha demanda por el sistema de acumulación sin necesidad de acoplar su generador de calor a la red de suministro eléctrico.
```

- [2] IT 1.2.4.1.3.2. Escalonamiento de potencia en centrales de generación de frío. (pág. 40) — no citado

- [3] IT 1.2.4.3.1. Control de las instalaciones de climatización (pág. 47) — no citado

- [4] Artículo 12. Eficiencia energética, energías renovables y energías residuales. (pág. 11) — no citado

- [5] Artículo 23. Certificado de la instalación. (pág. 16) — no citado

---

## q32 · ¿Qué dice el artículo 33?

**Respuesta del modelo:**

> El artículo 33 establece la clasificación de defectos en las instalaciones térmicas, que se divide en tres categorías: muy graves, graves y leves.  
> 
> 1. Defecto muy grave: es aquel que suponga un peligro inmediato para la seguridad de las personas, los bienes o el medio ambiente [1].  
> 2. Defecto grave: es el que no supone un pelig Đo inmediato para la seguridad de las personas o de los bienes o del medio ambiente, pero el defecto puede reducir de modo sustancial la capacidad de utilización de la instalación térmica, su eficiencia energética, el grado de utilización de energías renovables o el aprovechamiento de energías residuales, así como la sucesiva reiteración o acumulación de defectos leves [1].  
> 3. Defecto leve: es aquel que no perturba el funcionamiento de la instalación y por el que la desviación respecto de lo reglamentado no tiene valor significativo para el uso efectivo o el funcionamiento de la instalación [1].

**Fragmentos que recibió:**

**[1] Artículo 33. Clasificación de defectos en las instalaciones. (pág. 22)** — citado

```
Los defectos en las instalaciones térmicas se clasificarán en: muy graves, graves o leves.
1. Defecto muy grave: es aquel que suponga un peligro inmediato para la seguridad de las personas, los bienes o el medio ambiente.
2. Defecto grave: es el que no supone un peligro inmediato para la seguridad de las personas o de los bienes o del medio ambiente, pero el defecto puede reducir de modo sustancial la capacidad de utilización de la instalación térmica, su eficiencia energética, el grado de utilización de energías renovables o el aprovechamiento de energías residuales, así como la sucesiva reiteración o acumulación de defectos leves.
3. Defecto leve: es aquel que no perturba el funcionamiento de la instalación y por el que la desviación respecto de lo reglamentado no tiene valor significativo para el uso efectivo o el funcionamiento de la instalación.
```

- [2] Artículo 39. Registro. (pág. 24) — no citado

- [3] Artículo 38. Libre prestación. (pág. 23) — no citado

- [4] Artículo 32. Calificación de las instalaciones. (pág. 21) — no citado

- [5] Artículo 36. Habilitación de empresas instaladoras y empresas mantenedoras. (pág. 22) — no citado

---

## q33 · Si cambio mi caldera por otra de distinta potencia, ¿eso cuenta como reforma?

**Respuesta del modelo:**

> Sí, cambiar la caldera por otra de distinta potencia cuenta como reforma, según lo establecido en el artículo 2.3.b) del RITE [1], ya que se trata de una modificación del proyecto o memoria técnica con el que fue ejecutada y registrada, y específicamente se incluye en el caso de "la sustitución de un generador de calor o frío por otro de diferentes características" [1]. 
> 
> Además, según el artículo 24.11 [4], en el caso de sustitución de equipos de generación de calor o frío, se requiere cumplir con ciertas condiciones, como que la variación de potencia útil nominal no supere el 25 por ciento respecto a la potencia útil nominal del generador sustituido, y que la potencia útil nominal del generador instalado no supere los 70 kW. 
> 
> Por tanto, si la potencia útil nominal de la nueva caldera es distinta y se supera el 25 % de la anterior, o si supera los 70 kW, se considerará una reforma que debe cumplir con los requisitos del RITE, incluyendo la documentación técnica correspondiente [1][4]. 
> 
> No obstante, si el cambio de potencia no supone modificación del proyecto técnico y se trata de un cambio de características similares, podría no considerarse reforma según el apartado 4 del artículo 2 [1], aunque en este caso se especifica que se trata de una caldera de distinta potencia, por lo que no se aplica esa excepción. 
> 
> En conclusión, el cambio de caldera por otra de distinta potencia sí cuenta como reforma [1].

**Fragmentos que recibió:**

**[1] Artículo 2. Ámbito de aplicación. (pág. 8)** — citado

```
3. Se entenderá por reforma de una instalación térmica todo cambio que se efectúe en ella y que suponga una modificación del proyecto o memoria técnica con el que fue ejecutada y registrada. En tal sentido, se consideran reformas las que estén comprendidas en alguno de los siguientes casos:
a) La incorporación de nuevos subsistemas de climatización o de producción de agua caliente sanitaria o la modificación de los existentes.
b) La sustitución de un generador de calor o frío por otro de diferentes características o la interconexión con una red urbana de calefacción o refrigeración.
c) La ampliación del número de equipos generadores de calor o frío.
d) El cambio del tipo de energía utilizada o la incorporación de energías renovables.
e) El cambio de uso previsto del edificio.
4. También se considerará reforma de una instalación térmica, a efectos de aplicación del RITE, la sustitución o reposición de un generador de calor o frío por otro de similares características, aunque ello no suponga una modificación del proyecto o memoria técnica.
5. Con independencia de que un cambio efectuado en una instalación térmica sea considerado o no reforma de acuerdo con lo dispuesto en el apartado anterior, todos los productos que se incorporen a la misma deberán cumplir los requisitos relativos a las condiciones de los equipos y materiales en el artículo 18 de este reglamento.
```

- [2] IT 1.2.4.1.2.2. Fraccionamiento de potencia. (pág. 39) — no citado

- [3] Artículo 15. Documentación técnica de diseño y dimensionado de las instalaciones térmicas. (pág. 12) — no citado

**[4] Artículo 24. Puesta en servicio de la instalación. (pág. 16)** — citado

```
9. Antes de solicitar el suministro de energía, el titular de la instalación debe hacer entrega a la empresa distribuidora y, en su defecto, a la empresa comercializadora, de una copia del certificado de la instalación, registrado en el órgano competente de la comunidad autónoma.
10. Queda prohibido el suministro de energía a aquellas instalaciones sujetas a este reglamento cuyo titular no hubiera facilitado a la empresa distribuidora y, en su defecto, a la empresa comercializadora, copia del certificado de la instalación registrado en el órgano competente de la comunidad autónoma correspondiente.
11. No será necesario el registro previsto en el apartado 1 de este artículo en caso de sustitución o reposición de equipos de generación de calor o frío cuando se trate de generadores de potencia útil nominal menor o igual que 70 kW, siempre que la variación de la potencia útil nominal del generador no supere el 25 por ciento respecto de la potencia útil nominal del generador sustituido ni la potencia útil nominal del generador instalado supere los 70 kW.
El titular o usuario de la instalación deberá conservar la documentación de la reforma de acuerdo con lo establecido en el artículo 25.5.c). Dicha documentación comprenderá como mínimo la factura de adquisición del generador y de su instalación, salvo que concurran otros reglamentos de seguridad industrial que requieran certificación de la actuación, en cuyo caso bastará la certificación exigida por tales reglamentos.
```

- [5] IT 1.3.4.1.2.8. Medidas especificas para edificación existente (pág. 61) — no citado

---

## q34 · ¿Se aplica el RITE a la calefacción de un proceso industrial?

**Respuesta del modelo:**

> No, el RITE no se aplica a las instalaciones térmicas de procesos industriales [2].

**Fragmentos que recibió:**

- [1] Artículo 2. Ámbito de aplicación. (pág. 8) — no citado

**[2] Artículo 2. Ámbito de aplicación. (pág. 8)** — citado

```
6. No será de aplicación el RITE a las instalaciones térmicas de procesos industriales, agrícolas o de otro tipo, en la parte que no esté destinada a atender la demanda de bienestar térmico e higiene de las personas.
```

- [3] Artículo 1. Objeto. (pág. 8) — no citado

- [4] Artículo único. Aprobación del Reglamento de instalaciones térmicas en los edificios (RITE). (pág. 6) — no citado

- [5] Artículo 20. Recepción en obra de equipos y materiales. (pág. 15) — no citado

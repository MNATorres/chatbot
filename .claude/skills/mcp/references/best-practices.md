# Mejores prácticas para clientes/hosts MCP (referencia)

Resumen fiel de https://modelcontextprotocol.io/docs/develop/clients/client-best-practices
más las buenas prácticas del tutorial de cliente. Con notas de aplicación a este repo.

## El problema que resuelven

Cuando un host se conecta a muchos servers y acumula cientos/miles de tools, el
enfoque naíf (cargar TODAS las definiciones de tools al inicio de cada
conversación) rompe: gasta tokens, sube latencia y degrada al modelo. Pasar
resultados intermedios grandes por el modelo entre llamadas encadenadas lo empeora.

Dos patrones lo abordan: **progressive discovery** (controla *cuándo* entran las
definiciones al contexto) y **programmatic tool calling** (controla *cómo* se
invocan las tools).

> En este repo hay **3 tools** y un solo server: el enfoque naíf (cargar todas)
> es perfectamente válido HOY. Estos patrones importan si el proyecto crece a
> muchos servers/tools. Documentados aquí para cuando llegue ese momento.

## 1. Progressive Tool Discovery

En vez de inyectar todas las definiciones al modelo:
- El host hace `tools/list` normal pero **difiere** inyectarlas al contexto.
- Ofrece una meta-tool ligera `search_tools`.
- Carga la definición completa **solo cuando hace falta**.

**Cuándo activarlo**: cuando las definiciones ocupan una parte significativa de
la ventana de contexto. Regla práctica: umbral como % del contexto (ej. 1–5%);
al superarlo, cambiar a progressive discovery. Con pocas tools, cargar todo está bien.

**Estrategias de búsqueda** (capa "catálogo"):
- **Keyword** (BM25, regex): simple y efectivo con nombres/descripciones claros.
- **Embeddings**: similitud vectorial; maneja sinónimos y semántica.
- **Subagente**: un modelo pequeño y rápido (ej. Haiku) selecciona las tools.
  Suele funcionar muy bien pero es más caro.
- **Híbrido**: combinar. Algunos proveedores ya ofrecen tool-search nativo
  (Anthropic, OpenAI); si existe, considéralo antes de implementar el tuyo.

**Patrón de 3 capas**: (1) *Catalog* `search_tools({query})` → nombres +
descripción corta; (2) *Inspect* `get_tool_details({name})` → schema completo de
esa tool; (3) *Execute* llamada con conocimiento pleno de la interfaz.

**Gestión dinámica de servers**: conectar un server solo cuando el modelo lo
necesita y desconectarlo al terminar (libera contexto). Encaja muy bien con
agentes de propósito general y con *agent skills* que declaran qué servers
necesitan.

**Guías de implementación**:
- Ofrecer varios niveles de detalle (solo nombre / nombre+desc / schema completo).
- **Cachear** definiciones de tools del lado del host (memoizar) para no repetir
  `tools/list`.
- Re-indexar el catálogo al recibir `notifications/tools/list_changed`.
- Agrupar tools por server para que el modelo razone sobre capacidades relacionadas.

**Interacción con prompt caching** (¡clave para coste!): la mayoría de proveedores
cachean el prefijo del prompt, incluido el array `tools`. Añadir/quitar tools a
mitad de conversación **invalida** la caché y el miss puede costar más que lo que
ahorraste. Para preservarla:
- Añadir definiciones nuevas **después** del breakpoint de caché, o enrutar todo
  por una meta-tool estable `call_tool({name, args})` para que el array no cambie.
- Tratar la desconexión de un server como operación de "frontera de conversación",
  no por turno.

## 2. Programmatic Tool Calling ("code mode")

Con tool calling directo, cada invocación es un round trip y **todo** resultado
intermedio pasa por el contexto del modelo. Encadenar varias tools (leer →
transformar → escribir) infla tokens y latencia.

En code mode el modelo **escribe código** que llama a las tools; el código corre
en un **sandbox** y solo el resultado final vuelve al modelo.

Cómo funciona:
1. El host convierte los schemas MCP en una **API tipada** dentro del sandbox
   (usa `outputSchema` de la tool si existe; si no, tipo genérico o extracción
   con un modelo rápido).
2. El modelo escribe un script contra esa API (filtra/deduplica/itera dentro del
   sandbox, no en el contexto).
3. El sandbox ejecuta; las llamadas se **interceptan** y se enrutan al server vía
   el host (broker). Solo vuelve al modelo lo que el script imprime/retorna.

Requiere implementar un sandbox (Deno/`isolated-vm` para JS, Wasm, etc.).

**Seguridad de code mode**:
- **Autorización por llamada**: aprobar el script NO aprueba cada tool call; el
  broker evalúa cada llamada. Aplica la misma política human-in-the-loop.
- **Flujo entre servers**: el resultado de un server es entrada **no confiable**
  para otro; truncar el output no evita exfiltración.
- **Aislamiento de red**: el sandbox sin acceso a red; todo pasa por el broker.
- **Sin credenciales en el sandbox**: las API keys las tiene el host.
- **Límites de recursos**: timeouts y memoria para scripts descontrolados.
- **Filtrar output**: validar y truncar la salida antes de devolverla al modelo.

Ambos patrones se combinan: discovery para elegir las tools + code mode para
ejecutarlas en un solo pase → minimiza tokens de definiciones **y** de resultados.

## 3. Buenas prácticas base (del tutorial de cliente)

- **Manejo de errores**: envolver las llamadas a tools en try/except; mensajes
  claros; manejar caídas de conexión con elegancia. En MCP, error de tool =
  respuesta con `isError: true` (conviértelo en excepción/aviso al modelo).
- **Gestión de recursos**: `AsyncExitStack` / `async with`; cerrar conexiones;
  manejar desconexiones del server.
- **Seguridad**: API keys en `.env` (fuera de git); **validar** las respuestas
  del server; cautela con los permisos de las tools (son superficie de ataque).
- **Nombres de tools**: seguir el formato válido de la spec; si cumple, no debería
  fallar la validación del client.

## Aplicación concreta a ESTE repo

Prioridad razonable si se quiere endurecer/escalar:
1. **Ahora** (barato y de alto valor): manejar `isError` de las tools y
   concatenar todos los bloques `text` del resultado; buscar el primer bloque
   `text` en la respuesta final; poner timeouts en `call_tool`. (Ver
   `cliente-y-host.md`.)
2. **Mantener** la validación de solo-lectura de `query_production_db` (lista
   blanca + negra). Tratar el output de las tools como no confiable.
3. **Más adelante** (solo si crece a muchos servers/tools): progressive discovery
   y, si hay necesidad real de encadenar muchas tools, evaluar code mode con
   sandbox. Cuidar el prompt caching al modificar el array de tools.

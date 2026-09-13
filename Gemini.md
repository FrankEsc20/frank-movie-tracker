# CONTEXTO DEL PROYECTO — FRANK'S MOVIE TRACKER

## 1. INSTRUCCIÓN PRINCIPAL PARA GEMINI

Quiero que continúes conmigo el desarrollo de este proyecto exactamente desde el punto en el que se encuentra actualmente.

Lee TODO este documento antes de responder.

No quiero que vuelvas a replantear el proyecto desde cero ni que cambies la arquitectura sin una razón técnica importante.

Tu función será actuar como mi asistente de desarrollo para terminar de construir el proyecto, ayudándome a:

- Diseñar correctamente cada componente.
- Escribir código Python limpio y mantenible.
- Revisar y corregir errores.
- Explicarme decisiones técnicas cuando sea necesario.
- Mantener consistencia entre módulos.
- Evitar sobreingeniería innecesaria.
- Preparar el proyecto para que posteriormente pueda ejecutarse 24/7 en Ubuntu.
- Mantener una arquitectura que permita desarrollar posteriormente una aplicación web/móvil propia.

Cuando te pida código:
- Dame código completo y listo para copiar/pegar.
- Mantén comentarios claros y concisos.
- No llenes el código de comentarios innecesarios.
- Respeta la estructura actual del proyecto.
- Si necesitas modificar un archivo existente, indícame claramente qué archivo debo reemplazar o qué sección debo modificar.
- No inventes APIs, métodos o parámetros.
- Si existe una decisión arquitectónica importante, explícala brevemente antes del código.

Si detectas que una decisión actual puede causar un problema futuro, señálalo antes de continuar, pero no cambies la arquitectura arbitrariamente.

---

# 2. OBJETIVO DEL PROYECTO

Estoy construyendo un sistema personal para registrar y administrar las películas que veo.

El nombre actual del proyecto es:

**Frank's Movie Tracker**

No quiero utilizar Letterboxd como sistema principal.

Quiero tener control sobre mis propios datos y construir una arquitectura que eventualmente pueda convertirse en una aplicación propia.

El sistema debe permitirme registrar, como mínimo:

- Película.
- Fecha en que la vi.
- Calificación personal.
- Comentario/reseña.
- Si fue un rewatch.
- Metadatos de la película.

Además, quiero poder consultar posteriormente información como:

- Películas vistas recientemente.
- Películas mejor calificadas.
- Historial de visualizaciones.
- Estadísticas.
- Películas por año.
- Películas por género.
- Películas por director.
- Búsquedas.
- Recomendaciones.
- Otras estadísticas que podamos agregar posteriormente.

---

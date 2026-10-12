<h1 align="center">todo · Getting Things Done, sin app</h1>

<p align="center">
  <b>Dile a tu agente de IA lo que tienes que hacer. Captura, aclara, te recuerda y te ayuda a elegir, siguiendo
  Getting Things Done y las reglas que le enseñas.</b>
</p>

<p align="center">
  <a href="https://github.com/howware/todo/actions/workflows/ci.yml"><img src="https://github.com/howware/todo/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/versión-0.1.1-blue" alt="Versión 0.1.1">
  <a href="https://howware.org/es/"><img src="https://img.shields.io/badge/howware-0.2-5a45d6" alt="howware 0.2"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/licencia-Apache%202.0-green" alt="Apache 2.0">
</p>

<p align="center"><a href="README.md">English</a> · <a href="docs/building.md">Cómo se construyó</a></p>

> **Un [howware](https://howware.org/es/):** tu saber hacer, puesto a trabajar con IA. Aquí el saber hacer es
> [Getting Things Done](https://gettingthingsdone.com) más **tus propias reglas**: qué es urgente, qué áreas tiene
> tu vida, cuándo revisas. No hay app: tú hablas, el agente sigue el protocolo, una herramienta pequeña mantiene
> exactas las fechas y una memoria que es tuya lo guarda todo.

```text
› Anota: llamar a la contadora, pagar la luz y comprar el regalo de mamá.
✓ Anotado (3). Bandeja: 3.

› Vamos a aclarar.
  Pagar la luz → siguiente acción «Pagar en la app del banco» · Casa · computadora · 10 min ·
                 vence sáb 10 de oct, dura · se repite cada mes el día 10
  Llamar a la contadora → ¿en espera? o siguiente acción «Llamar para pedir la declaración» · Trabajo · teléfono
  Regalo de mamá → proyecto «Cumpleaños de mamá» · primer paso «Preguntarle a mi hermana qué le gustaría»
  ¿Lo aplico?

› ¿Qué hago ahora? Tengo 20 minutos, estoy en la computadora, con poca energía.
  1. Pagar la luz: vencida hace 2 días, fecha límite dura, 10 min.
  2. …
```

## Qué hace

| Dices | Hace |
|---|---|
| «Anota…» | **Captura** en la bandeja, sin preguntas |
| «Vamos a aclarar» | **Triage** al estilo GTD: siguiente acción (un verbo), proyecto, en espera de quién, algún día, área, contexto, estimación, energía, fecha límite dura o blanda, recurrencia. Lo propone en un solo mensaje y lo aplica cuando apruebas |
| «¿Qué hago ahora?» | Pregunta tu **tiempo, lugar y energía**, aplica tus reglas y sugiere **tres opciones con su razón** |
| «Mis pendientes del trabajo» | **Lista** por área, contexto, proyecto o vencimiento |
| «Listo» · «Pásalo al viernes» · «Olvídalo» | Completa (las recurrentes programan la siguiente), pospone (contando cuántas veces) o descarta |
| (cada sesión) | **Te recuerda** lo vencido hasta que se resuelva; después de 3 postergaciones pregunta si lo achicamos, lo delegamos o lo soltamos |
| (tu día de revisión) | Te lleva por la **revisión semanal de GTD**: bandeja en cero, vencidos, proyectos sin siguiente acción, en espera, estancados, algún día |
| «Lo del banco siempre es urgente» | Guarda una **regla** con tus palabras y la aplica; además propone reglas nuevas a partir de tu historia, que tú apruebas |

**Las áreas son tuyas.** Empieza sin ninguna: cuando algo necesita un área, el agente la propone y tú la apruebas.
Los contextos empiezan como computadora, teléfono, calle y casa; puedes agregar más.

## Cómo funciona

| Parte | Aquí |
|---|---|
| Protocolo | [`skill/todo/SKILL.md`](skill/todo/SKILL.md): GTD y las reglas para el agente, en palabras claras |
| Herramienta | [`todo.py`](skill/todo/scripts/todo.py): solo lo que debe ser exacto: la fecha y el día de hoy, vencimientos, recurrencias (el día 10, el último viernes, cada martes…), días de vencido, estados e historia |
| Memoria | El adaptador [Long-Term Memory for AI](https://github.com/howware/long-term-memory-for-AI): tus tareas y tus reglas, en un archivo local, con historia |

El agente nunca adivina fechas: «mañana a las 10» se convierte en fecha con el `now` de la herramienta y se
confirma («martes 13 de octubre a las 10:00»).

## Instalación

```bash
git clone https://github.com/howware/long-term-memory-for-AI
python long-term-memory-for-AI/tools/install_skill.py --target ~/.claude/skills/project-memory
git clone https://github.com/howware/todo
python todo/tools/install_skill.py
```

Crea una carpeta para tus pendientes, abre ahí Claude Code (agrega a su `CLAUDE.md` la instrucción de memoria
persistente de [Long-Term Memory for AI](https://github.com/howware/long-term-memory-for-AI/blob/main/README.es.md#configurar-un-proyecto))
y di *«Quiero llevar mis pendientes aquí.»*

## Privacidad y límites

| Diseñado para quedarse en tu computadora | Lo que ve el agente de IA |
|---|---|
| El archivo de la memoria con tus tareas, historia y reglas | Títulos, siguientes acciones, áreas, vencimientos e historia cuando los consulta; tus reglas; lo que escribes |

**Lo que no puede hacer ni garantizar:**
- **No hay notificaciones.** Los recordatorios aparecen cuando abres una conversación. (Está planeado exportar las
  fechas límite duras a tu calendario).
- Lo que ve el agente sale de tu computadora hacia tu proveedor de IA, bajo sus términos. No pongas contraseñas ni
  secretos en una tarea.
- El archivo de la memoria no está cifrado.
- **Todavía no se ha probado en una conversación real** en ningún anfitrión; `howware.json` solo lista los
  anfitriones cuando ya se probaron.

## Licencia

[Apache 2.0](LICENSE). Sin afiliación con David Allen ni David Allen Company; Getting Things Done® es su marca.

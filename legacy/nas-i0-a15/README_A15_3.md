# A15.3 JANUS SHRINE SEMANTIC CORE

Полный запуск Shrine layer для I0 / A14.x корпуса.

Это не просто graph importer. Это слой:

```text
glyph / proof / log / old HRain HTML
  -> concept atoms
  -> essence families
  -> route semantic pressure
  -> temple_route_bias.json output-only
```

## Установка

Распакуй **папкой** внутрь `I0`:

```text
I0/
  janus_io_o1_runs/
  A15_3_JANUS_SHRINE_SEMANTIC_CORE_PACK/
    Yaksa_A15_3_JANUS_SHRINE_FULL_START.bat
```

Не раскидывай файлы россыпью в корень I0.

## Старые Shrine/HRain наработки

Если есть архив `iNaiRH.rar`, распакуй его рядом:

```text
I0/
  iNaiRH/
  A15_3_JANUS_SHRINE_SEMANTIC_CORE_PACK/
```

A15.3 сам просканирует `.html` из `iNaiRH`, `iNaiHR`, `HRain`, `_old_shrine`.

## Запуск

Основной запуск:

```text
Yaksa_A15_3_JANUS_SHRINE_FULL_START.bat
```

Откроется:

```text
http://127.0.0.1:8793/index.html
```

Если порт занят, будет выбран следующий и напечатан в терминале.

## Файлы результата

```text
janus_shrine_graph.json
temple_route_bias.json
shrine_status.json
```

`temple_route_bias.json` пока только output-only. A14.2 его не читает. Для реального управления нужен следующий miner слой: A14.3 Temple-Aware PureRoute.

## Безопасность

```text
observer_only = true
WIRE/HASH/SUBMIT frozen
mirror untouched
miner not modified
bias file output only
```

Граф/смысловая карта — память и контекст, не proof сам по себе.

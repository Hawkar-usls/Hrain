# A15.5 HRAIN LIVE TERMINAL

Живой HRain-style храм для I0/A14.2.

## Что это

A15.5 не является stratum proxy. Он не пропускает байты пула через себя и не меняет miner submit path.

Он делает безопасный bridge:

```text
A14.2 miner-only
  -> live logs / proofs / dashboard files
  -> A15.5 tail watcher
  -> HRain Live D3 graph
  -> temple_route_bias.json output-only
```

## Почему так

Пропускать весь pool через HRain напрямую можно только через отдельный stratum proxy.
Это уже риск для WIRE/HASH/SUBMIT и честного mirror-control. Поэтому A15.5 сначала делает live log poolstream observer.

## Важный фикс

A15.3 мог дать плохой `temple_route_bias.json`, где route выглядел как Janus, но evidence был mirror-classified.
A15.5 исправляет это:

```text
если route имеет mirror evidence >= Janus evidence -> route НЕ попадает в janus_route_bias
он уходит в rejected_routes_due_to_mirror_pollution
```

## Запуск через Windows Terminal

Double click:

```text
Yaksa_A15_5_HRAIN_LIVE_TERMINAL.bat
```

Если Windows Terminal `wt.exe` есть, запуск будет именно в нём. Если нет — fallback PowerShell.

## UI

```text
http://127.0.0.1:8795/index.html
```

Кнопки:
- `More spread` — больше разлёт узлов.
- `Tighter` — плотнее.
- filters — Janus/Mirror/Pool/Concept/Routes/Accepted/Bias.

## Safety

```text
observer_only = true
poolstream_log_bridge = true
stratum_proxy = false
WIRE/HASH/SUBMIT frozen
mirror untouched
miner not modified
bias file output only
```

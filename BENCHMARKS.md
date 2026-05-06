# ARC-AudioBench Benchmarks

## Signal benchmarks

| Signal | Purpose |
|---|---|
| `sine_100hz.wav` | low-frequency EQ and bass path sanity |
| `sine_1000hz.wav` | midrange unity/reference test |
| `sine_10000hz.wav` | high-frequency response sanity |
| `silence.wav` | noise/denormal/DC stability |
| `impulse.wav` | impulse response / latency / ringing observation |
| `log_sweep_20_20000hz.wav` | broad frequency response observation |

## Plugin benchmarks

- pluginval strictness 10 result
- DAW load/scan report
- preset recall report
- automation write/read report
- sample-rate transition report
- buffer-size transition report
- rendered WAV analysis before/after processing

## Evidence outputs

- analysis JSON
- comparison JSON
- HTML report
- Markdown summary
- release manifest
- source inventory

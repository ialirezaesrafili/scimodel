# Example datasets

Every file is redistributable. Ground truth below is asserted by
`tests/scientific/`. Synthetic files are regenerated deterministically with
`python examples/generate_examples.py` (seed 20261019).

| File | Kind | Rows | Response ← predictors | Ground truth / reference |
|---|---|---:|---|---|
| `kepler_planets.csv` | real (public astronomical constants) | 8 | orbital period [yr] ← semi-major axis [AU], mass | T = a^1.5; mass is a distractor |
| `enzyme_kinetics_puromycin.csv` | real (Treloar 1974; Bates & Watts 1988; R `datasets::Puromycin`) | 12 | velocity ← substrate | Vmax = 212.684 ± 6.947, Km = 0.06412 ± 0.00828, RSS = 1195.45 |
| `catalysis_arrhenius.csv` | synthetic lab export | 64 | rate [mmol/(g·h)] ← temperature [K], catalyst loading [mol%] | rate = 2.4·10⁷·exp(−58 000/(R·T))·C^0.8, 4% log-normal noise, 2 replicates, one missing value, one ×1.6 transcription outlier, operator column |
| `bacterial_growth_od600.csv` | synthetic plate reader | 99 | OD600 ← time [h] | Gompertz y₀ = 0.05, A = 1.32, k = 0.42 h⁻¹, t_mid = 9.5 h; three wells; noise SD 0.006 + 2.5% of signal; constant incubator column |
| `damped_oscillator.csv` | synthetic sensor | 160 | displacement [mm] ← time [s] | x = 0.3 + 12·e^(−0.18 t)·cos(2.6 t + 0.4), noise SD 0.25 |
| `enzyme_kinetics_synthetic.csv` | synthetic | 14 | velocity ← substrate | Vmax = 200, Km = 0.05 |
| `enzyme_kinetics_advanced.csv` | synthetic | 20 | velocity ← substrate (+ replicate) | saturating kinetics with replicates and nonuniform spacing |
| `non_kinetics_exponential_decay.csv` | synthetic negative control | 10 | concentration ← time | C = 100·e^(−0.3 t); Michaelis–Menten must be rejected |

Try one:

```bash
scimodel discover examples/catalysis_arrhenius.csv --level novice
```

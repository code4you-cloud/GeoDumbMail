# v1.1.0 - 2026-04-03 (o data odierna)

### Changed
- Riscritta la logica di riconoscimento user ID tra Facebook e Google: ora si basa sulla **lunghezza del codice** (es. ID Facebook di lunghezza X, ID Google di lunghezza Y).
- Migliorata la robustezza del parsing in caso di ID inattesi.

### Warning / Known Issues
- **Potenziale fragilità futura**: la distinzione basata sulla lunghezza degli ID dipende dalle attuali policy di Facebook e Google. Se in futuro queste aziende modificheranno il formato o la lunghezza dei propri identificatori, il riconoscimento potrebbe fallire. Monitorare eventuali annunci di breaking change.

### Notes
- Testato con i pattern correnti (es. ID Facebook numerici lunghi ~15-16 cifre? ID Google di solito più lunghi? Aggiungi i dettagli che hai osservato).
- Nessuna modifica al database richiesta.

# v1.0.0 - 2026-02-20

### Added
- Internal user_id mapping between Django and FastAPI
- Facebook ID resolution endpoint
- Stable email parsing pipeline

### Fixed
- Integer overflow bug
- RecyclerView empty issue

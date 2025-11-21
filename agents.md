## Standards and Coding Practices

- Keep the repo layout clear: docs (`README.md`, `psudeocode.md`, `agents.md`) and config (`pyproject.toml`) stay at the root, business logic lives under `src/subject_recommender`, tests under `tests/`, and generated artifacts under `output/`.

- Treat `config.py` as the canonical source for adjustable weights, “secret” parameters, and session defaults. Other modules should read configuration through helper functions so tests can override values.

- Keep I/O concerns in `io.py`. Modules under `preprocessing` and `sessions` should only deal with in-memory data structures passed to them.

- Follow the preprocessing pipeline boundaries: `preprocessing.weighting` handles history iteration and weight application, `preprocessing.aggregation` computes averages/flooring, and `preprocessing.normalisation` normalizes scores and selects the next subject. Re-export the orchestration helper via `preprocessing.__init__`.

- Limit session logic to `sessions.generator`. External code should call the function exposed in `sessions.__init__` instead of importing submodules directly.

- Use `utils.py` only for helpers that genuinely span multiple modules; avoid circular dependencies by keeping utilities stateless and pure when possible.

- Mirror the package structure in `tests/` (`test_preprocessing.py`, `test_sessions.py`, etc.) so every public function has unit coverage. Keep exploratory scripts confined to `tests/AlgoTesting.py`.

- Keep exploratory scripts guarded with `if __name__ == "__main__":` and direct any generated artefacts to `output/`, creating the directory if needed so pytest collection stays read-only.

- At the start of each file and function there should be a docstring detailing function/file purpose, inputs & input types and outputs & output types

## Extra Notes

- All spellings should be in british english

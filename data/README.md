# Scene Data

| File | Tracked in Git? | Size | Description |
|---|---|---|---|
| `test.jsonl` | Yes | ~32 MB | 1,000 evaluation households |
| `logicworld/test.jsonl` | Yes | ~2 MB | Paper evaluation task split |
| `train.jsonl` | **No** (local only) | ~331 MB | 10,000 training households |

`train.jsonl` exceeds GitHub’s 100 MB file-size limit, so it is listed in `.gitignore`.

Place `train.jsonl` under this directory if you already have it locally:

```text
data/train.jsonl
```

Or point the package to another folder:

```bash
export LOGICWORLD_DATA_DIR=/path/to/your/data
```

The interactive CLI and smoke tests only need `test.jsonl`, which is included in the repository.

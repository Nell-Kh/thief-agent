# `config-najamjad/` — the same peer, one term changed

A per-opponent identity for the series against **najamjad**, passed with
`--config-dir config-najamjad`. It is a copy of `config/` with exactly one
difference:

    game.json:  "map_area": "Haifa"  ->  "New York"

`setting` is one of the fourteen signed terms, and `validate_terms` compares
the whole object byte-for-byte, so a single differing label refuses the
handshake at kickoff with both teams waiting. najamjad sign `"New York"`; we
verified that adopting it reproduces their published contract hash exactly:

    a284082dfb1572236f1b614d29295a99625539c7d33a096f7f8921bafbc3d08d

The shipped `config/` stays on `"Haifa"` — sharNamr play on that term, and the
committed artifacts, README and vectors are all written against it. A per-
opponent directory is how a signed term gets negotiated without the repository
having to pick a favourite.

Nothing else differs. Report mode is `draft` here exactly as it is there; a
counted run arms it deliberately, in both role files, and disarms afterwards.

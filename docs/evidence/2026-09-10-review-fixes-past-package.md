# 34 of 38 packaged pull requests merged past what PACKAGE pushed

`docs/BACKLOG.md` item 97. Measured 2026-09-10, on the host, against
`~/.saffron/ledger.db` and GitHub, by
`docs/evidence/scripts/review_fixes_past_package.py` — read-only, no spend.

**Question.** How often does a spec pull request's head, at merge, differ from
the commit PACKAGE pushed and recorded as `tasks.pushed_sha`? Every commit in
that gap was made after the cell and reached no gate, critic or ledger row.

**Answer.** 34 of 38. Four merged exactly as packaged: `SA-0013`, `SA-0023`,
`SA-0052`, `SA-0063`.

- **24** have the packaged commit in their history, with 1–5 commits on top.
- **10** (`?` below) do not have it in their history at all: the branch was
  rewritten after PACKAGE, so the packaged commit cannot even be walked back
  to from the merged head. Why each was rewritten is not recorded here.

What this does not say: whether any of those commits was *wrong*. Most were the
review round's fixes, and the 2026-09-07 plan's table records that each round
found something real. The measurement is that none of it was judged by the
machinery that judged the cell's work.

## Output

```
SA-0013 #51 MERGED pushed=31fc392b6 head=31fc392b6 same commits_after_package=0
SA-0014 #56 MERGED pushed=305ce100d head=30bd85c55 MOVED commits_after_package=3
SA-0015 #59 MERGED pushed=7db07f2bd head=d1da315bb MOVED commits_after_package=3
SA-0016 #60 MERGED pushed=71764ef73 head=497b221a5 MOVED commits_after_package=2
SA-0017 #64 MERGED pushed=896511a1a head=eb715ccaa MOVED commits_after_package=1
SA-0018 #65 MERGED pushed=88d9fdffc head=d0e553d74 MOVED commits_after_package=2
SA-0019 #70 MERGED pushed=cfb778799 head=474c4ee05 MOVED commits_after_package=1
SA-0023 #75 MERGED pushed=4f9ed5d63 head=4f9ed5d63 same commits_after_package=0
SA-0024 #78 MERGED pushed=43fbe1b78 head=d787c876c MOVED commits_after_package=2
SA-0022 #81 MERGED pushed=fed3a7e47 head=c6fb22b2a MOVED commits_after_package=2
SA-0025 #82 MERGED pushed=8d26bc939 head=0301518af MOVED commits_after_package=3
SA-0026 #84 MERGED pushed=ab235236c head=d0867883e MOVED commits_after_package=4
SA-0028 #87 MERGED pushed=65acf72e5 head=f7f41cedc MOVED commits_after_package=3
SA-0027 #88 MERGED pushed=e93282449 head=b72f8d89c MOVED commits_after_package=?
SA-0029 #91 MERGED pushed=ad92654aa head=a90f04c72 MOVED commits_after_package=3
SA-0040 #93 MERGED pushed=5e3fdf3e2 head=71f4b2b4c MOVED commits_after_package=2
SA-0030 #98 MERGED pushed=4bd4eae8b head=5b1d52d40 MOVED commits_after_package=2
SA-0041 #101 MERGED pushed=3ed8da6c5 head=857d89c6b MOVED commits_after_package=5
SA-0042 #103 MERGED pushed=97a293efe head=47e96e34a MOVED commits_after_package=3
SA-0043 #105 MERGED pushed=80a7a3e3b head=fc027f3ee MOVED commits_after_package=1
SA-0045 #115 MERGED pushed=f9f007c4b head=fb73c4e69 MOVED commits_after_package=?
SA-0046 #116 MERGED pushed=c71eeca9c head=81539b604 MOVED commits_after_package=?
SA-0048 #117 MERGED pushed=64c716142 head=05e625d8c MOVED commits_after_package=?
SA-0052 #118 MERGED pushed=a4a03cf73 head=a4a03cf73 same commits_after_package=0
SA-0049 #120 MERGED pushed=5c103860d head=0949239b5 MOVED commits_after_package=?
SA-0050 #121 MERGED pushed=91f56c695 head=54394dd1f MOVED commits_after_package=?
SA-0051 #122 MERGED pushed=fe39b41a6 head=d7d745a1e MOVED commits_after_package=?
SA-0054 #123 MERGED pushed=70091cd84 head=7ae5c9db5 MOVED commits_after_package=?
SA-0055 #131 MERGED pushed=e5a7cbe93 head=9836f7726 MOVED commits_after_package=1
SA-0056 #135 MERGED pushed=7ed9f1f0a head=a1f8757c5 MOVED commits_after_package=1
SA-0057 #136 MERGED pushed=d71b7d4d7 head=020351009 MOVED commits_after_package=2
SA-0058 #139 MERGED pushed=86fa8080d head=1d16db563 MOVED commits_after_package=1
SA-0060 #148 MERGED pushed=d600e7856 head=eec8868c6 MOVED commits_after_package=?
SA-0061 #150 MERGED pushed=7f296090e head=8f7226e8c MOVED commits_after_package=1
SA-0062 #154 MERGED pushed=78a25a237 head=290f070f2 MOVED commits_after_package=2
SA-0063 #158 MERGED pushed=f76931df2 head=f76931df2 same commits_after_package=0
SA-0064 #160 MERGED pushed=2544fc055 head=5b7aae967 MOVED commits_after_package=?
SA-0065 #185 MERGED pushed=259f6f984 head=f0beaa158 MOVED commits_after_package=1

34/38 pull requests moved past what PACKAGE pushed
```

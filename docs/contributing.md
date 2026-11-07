# Contributing

How to get a change in, whether you write code or not. The full team rules are in [`CLAUDE.md`](../CLAUDE.md).

## The rules in short

- **Every change is a small pull request (PR).** Never commit straight to `main`.
- **CI must pass:** tests and the osv-scanner security check run on every PR.
- **The Engineering Lead reviews; Tran approves the merge.** Don't click Merge on a PR, including your own, until Tran has said yes.
- **Nothing public, deployed, or sent outside the team without Tran's explicit yes.**
- **No secrets in the repo.** Keys go in `.env`, which git ignores. Document new settings in `.env.example`.
- **Open data only**, licence recorded in `docs/sources.md`. **No personal data.**
- **Every answer shown to a user says where the data came from and how fresh it is.**
- **Accessibility:** WCAG 2.2 AA minimum.

## Editing a doc in the browser (no coding needed)

1. Open the file on GitHub and click the **pencil icon**.
2. Make your change.
3. Click **Commit changes…**
4. **Choose "Create a new branch for this commit and start a pull request".** (The default, "Commit directly to the main branch", breaks the team rule.)
5. Name the branch, e.g. `docs/pitch-update`, then **Propose changes → Create pull request**.
6. Tell the team in chat so it gets reviewed.

To add new files: on the repo page, **Add file → Upload files**, then choose the new-branch option in step 4.

## Making a change from the terminal

```bash
git checkout main && git pull
git checkout -b feat/short-description
# make changes
make test
git add <files>
git commit -m "feat: short description"
git push -u origin feat/short-description
```

Open the link git prints to create the PR. **Check the PR's base branch is `main`**: GitHub sometimes defaults to another branch, and PRs merged into feature branches don't reach `main`.

## On Windows (PowerShell)

PowerShell has no `make` and doesn't accept `&&`. Use these instead:

| Instead of | Run |
|---|---|
| `make test` | `$env:PYTHONPATH = "src"` then `python -m unittest discover -s tests -t . -v` |
| `make snapshot` | `$env:PYTHONPATH = "src"` then `python -m corkathon.snapshot` |
| Run the app | `$env:PYTHONPATH = "src"` then `python -m corkathon.server`, and open http://localhost:8000 |
| `git checkout main && git pull` | `git checkout main; git pull` |

If `python` isn't recognised, use `py`. `$env:PYTHONPATH` lasts only for that terminal window.

## Branch and commit names

| Prefix | For |
|---|---|
| `feat/` | New feature or data source |
| `fix/` | Bug fix |
| `docs/` | Documentation only |
| `chore/` | Setup, CI, tidying |

## Adding a package

Stdlib only for now. If you need a package, it must have: an exact pinned version, a committed lockfile, a clean osv-scanner result, a review of any install scripts, and SWE sign-off.

## Before you open a PR

- [ ] `make test` passes
- [ ] No `.env`, keys or personal data in the diff
- [ ] New data source? Licence in `docs/sources.md`, notes in `docs/data-sources-guide.md`
- [ ] Design changed? `docs/architecture.md` updated
- [ ] PR base branch is `main`

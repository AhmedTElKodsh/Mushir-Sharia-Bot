# Client Pages

Two client-facing pages, kept in the repository so they are versioned with the project.

| Page | Open from the repo | Shared link |
| --- | --- | --- |
| Mushir Client Guide | [client-guide.html](client-guide.html) | https://claude.ai/artifact/N5sTGi4S15Kj3A1KdADGtP |
| Mushir Scholar Review Pack | [scholar-review-pack.html](scholar-review-pack.html) | https://claude.ai/artifact/4CE8SuwyTbb4vCQK56asMQ |

The `.html` files here are standalone: download one (or the folder) and open it in a browser. The two pages link to each other. GitHub shows `.html` files as source text, so open them locally or use the shared links.

The Markdown version of the guide is [client-guide.md](../client-guide.md).

## Editing

Edit only the sources in `src/`:

- `client-pages.css`: shared styles for both pages;
- `client-guide.body.html`, `scholar-review-pack.body.html`: page content. Links between the pages use the `{{GUIDE_URL}}` and `{{PACK_URL}}` placeholders.

Then rebuild:

```bash
python scripts/build_client_pages.py
```

This rewrites the standalone pages here and the publish-ready copies in `outputs/client-pages/` (git-ignored), which are what the shared links show. Republish those to the same links after a change.

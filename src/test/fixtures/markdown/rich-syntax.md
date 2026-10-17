# Feature Checklist

A dense sample of Markdown *syntax* that translators must **preserve**:
links, images, tables, quotes, task lists, and more.

## Status

- [x] Parser handles nested `inline code`
- [ ] Renderer keeps ~~strikethrough~~ text readable
- [x] Tables survive round-trips

## Release matrix

| Feature  | Status       | Notes                 |
|:---------|-------------:|:---------------------:|
| Headings | stable       | anchors are rewritten |
| Tables   | stable       | cells translate alone |
| Math     | pass-through | `$E = mc^2$` stays raw |

> Blockquotes keep their markers.
> > Nested quotes nest too.

Footnote-style references like [^1] remain plain text.

---

Images and autolinks: ![logo](https://example.com/logo.png) and
https://example.com/open-source — plus an emoji 🎉 for good measure.

[^1]: This footnote body is never parsed as a real footnote.

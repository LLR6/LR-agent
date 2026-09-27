# ChronoForge demo workspace

This deliberately tiny project has one current configuration contract:

- input key: `api_url`
- optional key: `timeout_s`
- output key: `base_url`

The current tests pass.

The point of the demo is **not** that the implementation is intentionally “bad.” The point is to give ChronoForge a small repository whose behavior is easy to inspect while future-maintenance scenarios evolve configuration, API and adjacent-feature requirements.

## Run current tests

```bash
pytest
```

## Use it as LR-Agent workspace

From the LR-Agent repository root, set:

```env
LR_AGENT_WORKSPACE=./examples/chronoforge-demo
```

Then:

```bash
lr-agent chrono "Keep client configuration behavior stable while allowing future configuration evolution" --generations 3 --trajectories 3
```

Outcomes depend on the configured model. Inspect the resulting Patch Life Report and the shadow workspaces under `data/chronoforge/`.

See [the guided demo](../../docs/DEMO_CHRONOFORGE.md) for the full walkthrough.

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.33.3](https://github.com/philipreese/the-record/compare/v0.33.2...v0.33.3) (2026-06-30)


### Bug Fixes

* **migrations:** optimize 014 data migration to use bulk update ([9efa499](https://github.com/philipreese/the-record/commit/9efa499cca3a75ee93a8651ea281653b091fec66)), closes [#221](https://github.com/philipreese/the-record/issues/221)

## [0.33.2](https://github.com/philipreese/the-record/compare/v0.33.1...v0.33.2) (2026-06-29)


### Code Refactoring

* **all:** SQL consistency, sync modularization, chart extraction, test teardown ([e2a3c1e](https://github.com/philipreese/the-record/commit/e2a3c1eece87b7a9fedd6def2157af5d1a710016))

## [0.33.1](https://github.com/philipreese/the-record/compare/v0.33.0...v0.33.1) (2026-06-29)


### Code Refactoring

* **all:** Modularize backend and split large frontend components ([6cf3f23](https://github.com/philipreese/the-record/commit/6cf3f235c49e67fd7088e942870971279a392aee))

## [0.33.0](https://github.com/philipreese/the-record/compare/v0.32.0...v0.33.0) (2026-06-29)


### Features

* **data:** Corrected listens view with per-listen and per-track correction system ([df1ed1e](https://github.com/philipreese/the-record/commit/df1ed1ee0f927de154c990a70f8a0d707cafc52b))
* **data:** Per-listen metadata correction with LB write-back ([c19a860](https://github.com/philipreese/the-record/commit/c19a8602ecc1c20fcd5eeb688152a646c1282461))
* **ui:** Album in listen row details, collapsible album tracks on artist page, mobile edit affordance ([968437f](https://github.com/philipreese/the-record/commit/968437f446733cd6c9f795d764f1c897c75491b5))
* **ui:** Metadata correction drawer redesign with cover art search and delete ([a4afe0e](https://github.com/philipreese/the-record/commit/a4afe0e5b662ca50dbd24d43c90e0f0fbfe0fffb))
* **ui:** Track listens modal, bulk delete, track count, and original cover art ([f2315ec](https://github.com/philipreese/the-record/commit/f2315ec71d5e18179656a46817e7e14d22aaffae))


### Tests

* **all:** Comprehensive test coverage and spec documentation for all features ([1683af1](https://github.com/philipreese/the-record/commit/1683af1ecea72a0a162927af5bb788358ec2954e))

## [0.32.0](https://github.com/philipreese/the-record/compare/v0.31.0...v0.32.0) (2026-06-28)


### Features

* **scripts:** Add normalize_album_art.py MusicBrainz/CAA art normalization ([1ea08b4](https://github.com/philipreese/the-record/commit/1ea08b4fb7209218a3088b2b0baa5a0a82d255bc))
* **scripts:** Add seed_cover_art.py and extend mirror_to_prod to cover cover_art_cache ([e5bef2f](https://github.com/philipreese/the-record/commit/e5bef2f6bfa4d06d5788557e17456a8bde8fa5b5))


### Bug Fixes

* **art:** Serve cover art from DB on cold start; fix instrumental tier preference ([be25574](https://github.com/philipreese/the-record/commit/be255741aa0ecd3ed91d986702fa26c0ebd82eee))
* **ui:** Restore cover art placeholder and fix journal date-anchor persistence ([fbb58cf](https://github.com/philipreese/the-record/commit/fbb58cfb8f856222c203e7a4724f20f80f5ec5d0))

## [0.31.0](https://github.com/philipreese/the-record/compare/v0.30.0...v0.31.0) (2026-06-27)


### Features

* **frontend:** Album art thumbnails on listen rows ([0018dc9](https://github.com/philipreese/the-record/commit/0018dc9864b62936ef9dd6c636d7c9d2608b3fd9))


### Bug Fixes

* **art:** Persist cover art to DB and rate-limit iTunes resolution ([e336913](https://github.com/philipreese/the-record/commit/e33691311bde5a53c1d76176755e96c883285f92))


### Miscellaneous

* **frontend:** Fix prettier formatting on art-related components ([6cac479](https://github.com/philipreese/the-record/commit/6cac4790e1752f16291468316dac794228174e98))

## [0.30.0](https://github.com/philipreese/the-record/compare/v0.29.1...v0.30.0) (2026-06-26)


### Features

* **frontend:** Add MetaChip pill component and apply to list rows ([b79fb58](https://github.com/philipreese/the-record/commit/b79fb586dae2a8368c28a4b2addcc7f5b2bc55e0))


### Bug Fixes

* **frontend:** Prevent chip row stacking on mobile in ArtistView ([18b9363](https://github.com/philipreese/the-record/commit/18b93630e5c227fb2492e6d94278cff93b937155))
* **frontend:** Redesign ArtistView track row secondary info ([c38d9da](https://github.com/philipreese/the-record/commit/c38d9dae31f109352bf2584f9d3c22f0e66b654b))


### Code Refactoring

* **frontend:** Revert chip usage on Charts and ListenRow collapsed state ([8f0a998](https://github.com/philipreese/the-record/commit/8f0a998d4179db3ebf3891bb75c3cd60dec8a199))

## [0.29.1](https://github.com/philipreese/the-record/compare/v0.29.0...v0.29.1) (2026-06-26)


### Bug Fixes

* **net:** Revert cover art client transport to OS default ([596946e](https://github.com/philipreese/the-record/commit/596946e9914cf4d65c50f483b26eb56e9bfeab74))
* **net:** Revert cover art client transport to OS default ([de04066](https://github.com/philipreese/the-record/commit/de040666184bd85137884c7e3b4a9e8e563cf3bf))


### Code Refactoring

* **net:** Scope IPv4 preference to httpx transports ([49dc254](https://github.com/philipreese/the-record/commit/49dc254aa1d527f486671979a396a068940a30b1))


### Documentation

* **spec:** Document lb_client, protocol rationale, and production deployment ([d7e7901](https://github.com/philipreese/the-record/commit/d7e790172769044ca709cb934385e2d704da5b98))

## [0.29.0](https://github.com/philipreese/the-record/compare/v0.28.0...v0.29.0) (2026-06-25)


### Features

* **graphql:** GraphQL endpoint for Artist Explorer data ([ae96f03](https://github.com/philipreese/the-record/commit/ae96f03bcfe8cb9685cff77660f47daae80fbc3e))


### Code Refactoring

* **graphql:** Use Strawberry Pydantic integration for leaf types ([8e2f079](https://github.com/philipreese/the-record/commit/8e2f07945d18779cda205329fe4a7bf6e28f613d))

## [0.28.0](https://github.com/philipreese/the-record/compare/v0.27.0...v0.28.0) (2026-06-25)


### Features

* **sse:** SSE endpoint for playing-now push ([b651e46](https://github.com/philipreese/the-record/commit/b651e46123e44189dfb1a8d78f6a68f551941c2b))

## [0.27.0](https://github.com/philipreese/the-record/compare/v0.26.1...v0.27.0) (2026-06-25)


### Features

* **sync:** WebSocket endpoint for real-time sync events ([bd0f0d7](https://github.com/philipreese/the-record/commit/bd0f0d7e4d7225c13cce86cfc73e573c6a702c52))


### Bug Fixes

* **sync:** Connect WebSocket before triggering startup sync, proxy WS in Vite ([6c9a2f8](https://github.com/philipreese/the-record/commit/6c9a2f8d94996c381bec86087ff857c83aed8944))


### Tests

* **ws:** add WebSocket endpoint and ConnectionManager tests ([00204f8](https://github.com/philipreese/the-record/commit/00204f871a1ece63262eef02ce193a551aaedb9e))

## [0.26.1](https://github.com/philipreese/the-record/compare/v0.26.0...v0.26.1) (2026-06-25)


### Bug Fixes

* **lint:** Prettier formatting in WrappedView year options ([bf55b00](https://github.com/philipreese/the-record/commit/bf55b0076adaf3b6dabd93cdc2ccda9b3a27bad8))


### Miscellaneous

* **frontend:** Derive Wrapped year range from first_year stat ([60da2a9](https://github.com/philipreese/the-record/commit/60da2a987a625add59f9cebc02098dcab82505a1))

## [0.26.0](https://github.com/philipreese/the-record/compare/v0.25.5...v0.26.0) (2026-06-25)


### Features

* **data:** Add artist_corrections table to normalize scrobbler metadata ([d8ec0ad](https://github.com/philipreese/the-record/commit/d8ec0ada036e30709ac7d7b9abc23df30420e5c4))


### Code Refactoring

* **data:** Manage artist corrections via code dict, not migrations ([d9b0daf](https://github.com/philipreese/the-record/commit/d9b0dafd08a09b4d37125779bd14b02ada263a5b))


### Documentation

* **spec:** Document artist_corrections table and data quality workflow ([4d7ae62](https://github.com/philipreese/the-record/commit/4d7ae6295676e5a86fda0c7a184f10e60240d30e))

## [0.25.5](https://github.com/philipreese/the-record/compare/v0.25.4...v0.25.5) (2026-06-25)


### Code Refactoring

* **api:** Return schema instances from repo layer and annotate route handlers ([dc2de22](https://github.com/philipreese/the-record/commit/dc2de2298a48b107b77b56f45d92fb9bbaa38d85))


### Documentation

* **spec:** Document typed repo return convention and updated layer map ([3f5b8e3](https://github.com/philipreese/the-record/commit/3f5b8e34b4a2d82615e74e265f661f75e6c991ea))

## [0.25.4](https://github.com/philipreese/the-record/compare/v0.25.3...v0.25.4) (2026-06-24)


### Miscellaneous

* **backend:** Remove get_db_connection and migrate tests to engine.connect() ([62a227e](https://github.com/philipreese/the-record/commit/62a227e144df62ef00df8d62002303112b735b4a))

## [0.25.3](https://github.com/philipreese/the-record/compare/v0.25.2...v0.25.3) (2026-06-24)


### Tests

* **sync:** Cover LB retry/backoff and 429 handling with respx mocks ([7db8826](https://github.com/philipreese/the-record/commit/7db8826d945e8e83325a8662b90d866d4b72d3b4))


### Miscellaneous

* **deps:** Regenerate pixi.lock after adding respx ([2d17d2e](https://github.com/philipreese/the-record/commit/2d17d2e40b49f60bf317da65f8ad2d61d5a9e12f))

## [0.25.2](https://github.com/philipreese/the-record/compare/v0.25.1...v0.25.2) (2026-06-24)


### Bug Fixes

* **backend:** Harden sync-token compare, bound art cache, cap batch endpoint ([2a07e7c](https://github.com/philipreese/the-record/commit/2a07e7c460149f1598335ffc992877d60ef80b94))

## [0.25.1](https://github.com/philipreese/the-record/compare/v0.25.0...v0.25.1) (2026-06-24)


### Documentation

* **spec:** Scrub spec for end-of-Phase-3 accuracy ([b24c940](https://github.com/philipreese/the-record/commit/b24c940167fcf10636db4fdc05b7f0b3ba11231a))

## [0.25.0](https://github.com/philipreese/the-record/compare/v0.24.0...v0.25.0) (2026-06-24)


### Features

* **artist:** Full track list with sort controls and log-scale chart ([b738a64](https://github.com/philipreese/the-record/commit/b738a64134a25758bd955d72b8479cc621cfb7ba))
* **artist:** Paginated track list with album, duration, and full timestamps ([c95e9dd](https://github.com/philipreese/the-record/commit/c95e9dd1d31e7e9bc06533011dedc8fa2ad4d7a8))
* **discovery:** Discovery timeline and artist anniversaries ([ad77154](https://github.com/philipreese/the-record/commit/ad77154504a2c9b216a6acf4726367d408ab3577))


### Bug Fixes

* **artist:** Show dates in track secondary line only for relevant sort modes ([75ea98c](https://github.com/philipreese/the-record/commit/75ea98c5721d9b0fd4100e0e5279b4e5f9ace193))
* **lint:** LF line endings on ArtistView for CI prettier check ([d4cbd04](https://github.com/philipreese/the-record/commit/d4cbd048acafa9946150299fa6051b7e4ec42949))
* **lint:** Remove orphaned svelte-ignore comment in OnThisDaySection ([6ffb9c1](https://github.com/philipreese/the-record/commit/6ffb9c1b7f33c4906a6a386977a92e07c644cfe7))

## [0.24.0](https://github.com/philipreese/the-record/compare/v0.23.0...v0.24.0) (2026-06-23)


### Features

* **artist:** Add hover labels to listening history chart; style tweaks ([aa39803](https://github.com/philipreese/the-record/commit/aa39803b6ee6884ffff16ac2f203db8759ff95cd))
* **artist:** Artist detail view with per-artist stats ([49515a3](https://github.com/philipreese/the-record/commit/49515a3d6b78343d305ccb4172862b5d0b7118c2))

## [0.23.0](https://github.com/philipreese/the-record/compare/v0.22.2...v0.23.0) (2026-06-23)


### Features

* **sync:** Report modified count alongside added and deleted ([267d38b](https://github.com/philipreese/the-record/commit/267d38b9eab3e8706fceb30ab11f5c97b070bc8a))

## [0.22.2](https://github.com/philipreese/the-record/compare/v0.22.1...v0.22.2) (2026-06-23)


### Performance Improvements

* **sync:** Bulk-update mirror backfill instead of per-row ([f55d02a](https://github.com/philipreese/the-record/commit/f55d02a61130a821b41b19a97432121268b593f7))

## [0.22.1](https://github.com/philipreese/the-record/compare/v0.22.0...v0.22.1) (2026-06-23)


### Bug Fixes

* **sync:** Read recording_mbid from LB mbid_mapping ([6a61ac9](https://github.com/philipreese/the-record/commit/6a61ac920d3e0eff19432470697198b536389a3b))

## [0.22.0](https://github.com/philipreese/the-record/compare/v0.21.4...v0.22.0) (2026-06-23)


### Features

* **db:** Store recording_mbid for canonical track identity ([86a676f](https://github.com/philipreese/the-record/commit/86a676f4b77b66361945051f17016a4ceefa7c91))


### Documentation

* **blog:** Expand Takeout steps and refine data-cleaning notes ([d5b2889](https://github.com/philipreese/the-record/commit/d5b2889e3beb176375c7874b44fbf76cc049d5da))

## [0.21.4](https://github.com/philipreese/the-record/compare/v0.21.3...v0.21.4) (2026-06-22)


### Documentation

* **blog:** Add origin story about the missing YouTube Music API ([cf54b25](https://github.com/philipreese/the-record/commit/cf54b250223053e121dae72c631c32b3598e1b8c))
* **blog:** Move and tighten the API origin section ([662cc2f](https://github.com/philipreese/the-record/commit/662cc2f4be260b1c6b4088525356db423b4eec3a))


### Miscellaneous

* **backend:** Add production DB mirror script ([a5c39d1](https://github.com/philipreese/the-record/commit/a5c39d1c3b99fbc9bcb166e89b4c89c724378fa0))

## [0.21.3](https://github.com/philipreese/the-record/compare/v0.21.2...v0.21.3) (2026-06-22)


### Documentation

* **blog:** Make migration stats block format consistent ([3e36044](https://github.com/philipreese/the-record/commit/3e3604460f3bc1327af098d5158908b3e14eee45))

## [0.21.2](https://github.com/philipreese/the-record/compare/v0.21.1...v0.21.2) (2026-06-22)


### Bug Fixes

* **frontend:** Show 'writing' in navbar breadcrumb on blog pages ([b9e1c62](https://github.com/philipreese/the-record/commit/b9e1c625ede7056aaf9fc61f50376a3105679b66))

## [0.21.1](https://github.com/philipreese/the-record/compare/v0.21.0...v0.21.1) (2026-06-22)


### Bug Fixes

* **frontend:** Use shared PageHeader on blog pages ([8a9d220](https://github.com/philipreese/the-record/commit/8a9d2201f7988ebd4e4436804f91761e79eb774b))


### Tests

* **backend:** Anchor on-repeat peak test to local midday to fix midnight flake ([31cf2a8](https://github.com/philipreese/the-record/commit/31cf2a8152484acc123390bfde456d08196df3d1))

## [0.21.0](https://github.com/philipreese/the-record/compare/v0.20.2...v0.21.0) (2026-06-21)


### Features

* **frontend:** Add blog section with rendered markdown posts ([c8ee99c](https://github.com/philipreese/the-record/commit/c8ee99c765fd6fce0bfbdebf60f4196411eaacce))


### Documentation

* **spec:** Document Writing section and missing Phase 2 features ([af47c67](https://github.com/philipreese/the-record/commit/af47c67634c35d6967f189c6fbae567172994597))

## [0.20.2](https://github.com/philipreese/the-record/compare/v0.20.1...v0.20.2) (2026-06-21)


### Miscellaneous

* **ci:** Exclude backend/scripts from pyrefly type-checking ([84eab1a](https://github.com/philipreese/the-record/commit/84eab1ae03af2a2d876fe4817b22504a2a36f039))
* **scripts:** Add LB reconciliation tooling and sync standalone entry point ([6bd926a](https://github.com/philipreese/the-record/commit/6bd926a7619f87963f9a6a3c1e863abfd1ff93c9))
* **scripts:** MusicBrainz backfill workflow and ListenBrainz sync tooling ([cfa80ec](https://github.com/philipreese/the-record/commit/cfa80ec2abcc5df00465c9c14f05320e4fbfdfa8))

## [0.20.1](https://github.com/philipreese/the-record/compare/v0.20.0...v0.20.1) (2026-06-19)


### Bug Fixes

* **docker:** Copy backend/data into container image ([6aa7515](https://github.com/philipreese/the-record/commit/6aa75152714b0180bf33c414c08b402f43d5b90f))

## [0.20.0](https://github.com/philipreese/the-record/compare/v0.19.0...v0.20.0) (2026-06-19)


### Features

* **frontend:** Add 404 not-found view with narrative text ([d1d7d94](https://github.com/philipreese/the-record/commit/d1d7d94e12a0c4a4f5d4fd49c4ccca5dab93510a))
* **frontend:** Add hash-based router module ([5ecf162](https://github.com/philipreese/the-record/commit/5ecf162294c5ba10c3d5702644e6e4534cbd01ec))
* **frontend:** Sync overlay and view params to URL ([2b2d8ae](https://github.com/philipreese/the-record/commit/2b2d8ae5fbcd17a6be6f7ab75e3e8d100db7eab0))
* **frontend:** Wire primary view navigation to router ([bf7d48e](https://github.com/philipreese/the-record/commit/bf7d48e4c688e5ad67bc752c813fa17a7fe0c633))


### Documentation

* **spec:** Update narrative, roadmap, and architecture for routing PR ([e38f30d](https://github.com/philipreese/the-record/commit/e38f30de4bf34622d6c965e9e120061460a9e036))


### Miscellaneous

* **lint:** Add endOfLine lf to prettier config; fix line wrapping ([554ca65](https://github.com/philipreese/the-record/commit/554ca65568d356619d50b2327e74b4ee7322b3f5))

## [0.19.0](https://github.com/philipreese/the-record/compare/v0.18.0...v0.19.0) (2026-06-19)


### Features

* **frontend:** Replace streamgraph year dropdown with arrow selector; fix backdrop a11y ([f15f6d1](https://github.com/philipreese/the-record/commit/f15f6d16e4e607b6d602ab8c63f61e91f64d04c0))


### Bug Fixes

* **backend:** DNS cache TTL/IPv4 filter and anchor_date warning log ([68ee46c](https://github.com/philipreese/the-record/commit/68ee46c35607b003ae461b635b36e85c952c8793))


### Documentation

* **spec:** Phase 2 close-out — roadmap scrub and issue links ([353dbd2](https://github.com/philipreese/the-record/commit/353dbd2ce547552e1531028805939c9015a816d3))

## [0.18.0](https://github.com/philipreese/the-record/compare/v0.17.0...v0.18.0) (2026-06-19)


### Features

* **narrative:** Expand narrative engine to power all dynamic UI copy ([403d98e](https://github.com/philipreese/the-record/commit/403d98eecd596727c39c5285c9e18599f97ce8e5))
* **narrative:** Split into plain/rich, replace * delimiter with [[...]] ([2aef101](https://github.com/philipreese/the-record/commit/2aef101ec048df0f9e70cef681898d0207f2dc7d))


### Bug Fixes

* **narrative:** replace {[@html](https://github.com/html)} with NarrativeText for XSS safety ([d0d578a](https://github.com/philipreese/the-record/commit/d0d578a255b457b9709e08c2e5c5caae737dd7ac))
* **narrative:** Replace HTML entities with Unicode characters in templates ([b80897d](https://github.com/philipreese/the-record/commit/b80897d75d31ef9642458ff1eb92aab244742940))
* **playing-now:** Background cover art resolution, wire NarrativeResponse, eager narrative load ([ec0e12c](https://github.com/philipreese/the-record/commit/ec0e12cb8bba04ca45a09f84fc66614ebd209e92))


### Documentation

* **spec:** Document narrative engine — product, architecture, roadmap, data-models ([22b3784](https://github.com/philipreese/the-record/commit/22b37846f17de404a51995f1d0e55cbf456df115))


### Miscellaneous

* **lint:** Fix code style issues ([3388c3b](https://github.com/philipreese/the-record/commit/3388c3bb8f1bb205108ee20fda5a403f0005a2c8))

## [0.17.0](https://github.com/philipreese/the-record/compare/v0.16.0...v0.17.0) (2026-06-18)


### Features

* **charts:** Add temporal streamgraph showing top artist trends ([9c63a8b](https://github.com/philipreese/the-record/commit/9c63a8b672cd037eb8ce91efa50b1b1f9ec0d68e))
* **charts:** Fix mobile streamgraph zoom and make filters sticky ([e26a0a9](https://github.com/philipreese/the-record/commit/e26a0a920f62bd31a655314e3e6b5b862f66d238))
* **charts:** Relocate top lists range filters below streamgraph ([f7e5f55](https://github.com/philipreese/the-record/commit/f7e5f5541081de7f7f8c5f3104709e6cded17adc))
* **charts:** Style year selector dropdown using SelectDropdown ([9d89f17](https://github.com/philipreese/the-record/commit/9d89f177b79d2f6f55c8507ef7451a108d81ee2e))


### Bug Fixes

* **charts:** Restrict streamgraph double-tap zoom gesture to mobile viewports ([689aaeb](https://github.com/philipreese/the-record/commit/689aaeb133303495b5a194ce894cbd046d526693))


### Documentation

* **spec:** Document temporal streamgraph feature and new API routes ([7e8d066](https://github.com/philipreese/the-record/commit/7e8d066591e09bae3fee8a8621001175d1c00cc7))

## [0.16.0](https://github.com/philipreese/the-record/compare/v0.15.2...v0.16.0) (2026-06-18)


### Features

* **backend:** Add /api/day/{date} and /api/trends/monthly/{year}/{month}/weekly endpoints ([197c3aa](https://github.com/philipreese/the-record/commit/197c3aa46888464b166e0b577c07c8feda81e2b0))
* **frontend:** Add drill-down overlays for heatmap cells and monthly bars ([2589ea5](https://github.com/philipreese/the-record/commit/2589ea514274d602e460034c6c60ed7fd6ea1ebe))
* **frontend:** Interactive legend tooltips, dynamic heatmap weights, overlay polish ([b79abd6](https://github.com/philipreese/the-record/commit/b79abd647807e92b1ded0637b1da92b9e1c6aed2))
* **frontend:** Regenerate OpenAPI types and add fetchDayListens/fetchWeeklyBreakdown ([f554cfa](https://github.com/philipreese/the-record/commit/f554cfa709418fa4755dce4d014c0664799a27c6))


### Bug Fixes

* **frontend:** Portal overlays to body to escape .memory-surface stacking context ([6bf2dd0](https://github.com/philipreese/the-record/commit/6bf2dd07417e9552d43262d6afefbe6ecce9b280))

## [0.15.2](https://github.com/philipreese/the-record/compare/v0.15.1...v0.15.2) (2026-06-18)


### Miscellaneous

* **frontend:** Add keyboard accessibility to SVG chart interactive elements ([fc4adbe](https://github.com/philipreese/the-record/commit/fc4adbe140c03ac5fa3eeec24d35171fe7221ad3))

## [0.15.1](https://github.com/philipreese/the-record/compare/v0.15.0...v0.15.1) (2026-06-18)


### Bug Fixes

* **backend:** Fix Lucene quote escaping and conditional UPDATE in backfill script ([e4e150d](https://github.com/philipreese/the-record/commit/e4e150da5dea3e15fc25b0caa8d0c600e5972c3b))
* **frontend:** Fix api.test.ts for openapi-fetch Request-based fetch signature ([df32b7d](https://github.com/philipreese/the-record/commit/df32b7de34439a74f96ebbc8e756bd117216e31a))
* **frontend:** Trigger a soft background sync automatically on page load ([f124a7b](https://github.com/philipreese/the-record/commit/f124a7be91acd0cf5351cf480f13e60464abf53c))
* **routes:** Verify track metadata match before enriching last-played MBIDs ([cc4294a](https://github.com/philipreese/the-record/commit/cc4294a1252a53c79533dd4ac02a0ebfd27c23a9))


### Documentation

* **spec:** Update architecture.md for openapi-fetch and auto-sync on page load ([1868325](https://github.com/philipreese/the-record/commit/186832533849b29f552741dabe643d5c8e1ab44d))


### Miscellaneous

* **backend:** Add backfill_metadata.py script to fetch and populate durations and albums from MusicBrainz ([ba49282](https://github.com/philipreese/the-record/commit/ba49282d7be695c8927eb664d2e0784894d4a091))
* **frontend:** Replace apiFetch wrappers with openapi-fetch for end-to-end type safety ([35d29ff](https://github.com/philipreese/the-record/commit/35d29ff3a8ec25038b638664f41dd3f9e883fbc7))

## [0.15.0](https://github.com/philipreese/the-record/compare/v0.14.0...v0.15.0) (2026-06-18)


### Features

* **journal:** Batch track-stats endpoint for inline play counts on journal rows ([b2f15af](https://github.com/philipreese/the-record/commit/b2f15aff797c05a0181ef23b91680b97f5a73072))
* **journal:** Improve row wrapping, style play counts, and extend batch stats to overview ([0efd541](https://github.com/philipreese/the-record/commit/0efd5419f05483384efef70838769c4887e01ead))


### Bug Fixes

* **backend:** Add Cache-Control middleware to prevent browser caching of API endpoints ([19b70ca](https://github.com/philipreese/the-record/commit/19b70ca6d19403612fbbb9b81ea64480cedee899))
* **backend:** Cache DNS socket address lookups to bypass IPv6 DNS timeouts ([83124e1](https://github.com/philipreese/the-record/commit/83124e18a1a8a2d5b4dfec86b175b6f4cad14766))
* **sync:** Cache cover art lookup failures immediately to prevent repeated 2s delays ([0a23873](https://github.com/philipreese/the-record/commit/0a23873cfed1f766e48e397ebb65bf4ef278d800))
* **sync:** Optimize playing-now timeouts and add polling in-flight guard ([d5d7946](https://github.com/philipreese/the-record/commit/d5d794695b8618176d346be1d1792cea3f6a4110))
* **sync:** Skip ListenBrainz listens lookup when last played cover art is cached ([1ed0d3b](https://github.com/philipreese/the-record/commit/1ed0d3bbc601ac6451275357af887375143a3571))


### Code Refactoring

* **frontend:** Consolidate batch track stats caching and fetching into shared appCache ([69e7a32](https://github.com/philipreese/the-record/commit/69e7a32153806324b89ca444950bef42316c1f8c))


### Documentation

* **spec:** Document TrackBatchRequestItem and TrackBatchResponseItem schemas ([3ec582b](https://github.com/philipreese/the-record/commit/3ec582bc1f2f69761db40d41a7cdceded5fa3aab))

## [0.14.0](https://github.com/philipreese/the-record/compare/v0.13.0...v0.14.0) (2026-06-17)


### Features

* **journal:** Date jump control to seek to a point in listening history ([1b1327e](https://github.com/philipreese/the-record/commit/1b1327e8caee27ca8dd2b1a517e1868af712986f))

## [0.13.0](https://github.com/philipreese/the-record/compare/v0.12.0...v0.13.0) (2026-06-17)


### Features

* **charts:** Implement search, count-based pagination, and absolute rankings ([19b2837](https://github.com/philipreese/the-record/commit/19b2837a52b2a1e0026ded9cfebb3c3faa7808d8))

## [0.12.0](https://github.com/philipreese/the-record/compare/v0.11.1...v0.12.0) (2026-06-17)


### Features

* **sync:** Add reconcile mode to diff and remove deleted ListenBrainz plays ([b7a7484](https://github.com/philipreese/the-record/commit/b7a74849bf7f7f2d33f2433c98cff25b87c5622a))
* **sync:** Implement mirror mode with full parity and performance fixes ([48f4bee](https://github.com/philipreese/the-record/commit/48f4bee3ec30f43c0e0489036c6dab7bf85136ba))


### Code Refactoring

* **sync:** Replace full+reconcile modes with unified mirror mode ([9935b6e](https://github.com/philipreese/the-record/commit/9935b6e498fd12c5df1090c8d983b733b562fd6f))


### Documentation

* **spec:** Update sync dedup and mirror mode notes for [#33](https://github.com/philipreese/the-record/issues/33) ([87f55b9](https://github.com/philipreese/the-record/commit/87f55b9ee5853ea14ebf4853703e00ec3129cc2b))


### Miscellaneous

* **lint:** Fixed front-end linting ([61118a2](https://github.com/philipreese/the-record/commit/61118a2cc2c0d6d72f3a76d0f227aea7b06bcb78))

## [0.11.1](https://github.com/philipreese/the-record/compare/v0.11.0...v0.11.1) (2026-06-17)


### Bug Fixes

* **tests:** Add None guards on fetchone() calls to satisfy pyrefly ([2c8dc84](https://github.com/philipreese/the-record/commit/2c8dc84b909cba8cfadbe5a8cb865ddbddca4f5b))


### Documentation

* **spec:** Update dedup notes to reflect case-insensitive SQL fix from [#105](https://github.com/philipreese/the-record/issues/105) ([6c985a2](https://github.com/philipreese/the-record/commit/6c985a2ff26d33b560aa21a5c4332a540aaa7e64))


### Miscellaneous

* **db:** Normalize artist/title casing across historical import data ([c913ba2](https://github.com/philipreese/the-record/commit/c913ba2ac14366064f7e91c8ee05e6400d470fe5))

## [0.11.0](https://github.com/philipreese/the-record/compare/v0.10.0...v0.11.0) (2026-06-17)


### Features

* **wrapped:** Add On-Repeat Peak slide — max same-track plays in a day ([14eb757](https://github.com/philipreese/the-record/commit/14eb7572e0b49b519baaa32443383380a4a0c391))


### Bug Fixes

* **wrapped:** Case-insensitive GROUP BY for on-repeat peak ([60330b1](https://github.com/philipreese/the-record/commit/60330b1215ee0b6f5b6d115434bc2a359ecc18ee))


### Documentation

* **spec:** Mark export and on-repeat badges as shipped in Phase 2 ([e84dcc7](https://github.com/philipreese/the-record/commit/e84dcc77bcbcfd01a0df2792e214944b2fea6544))

## [0.10.0](https://github.com/philipreese/the-record/compare/v0.9.0...v0.10.0) (2026-06-17)


### Features

* **settings:** Add CSV/JSON export endpoint and download UI ([b3fab50](https://github.com/philipreese/the-record/commit/b3fab50adbef5730da69d72ba39f5aa8f003d649))

## [0.9.0](https://github.com/philipreese/the-record/compare/v0.8.1...v0.9.0) (2026-06-17)


### Features

* **backfill:** Add endpoint to backfill duration_secs and album for historical listens ([c4ad22e](https://github.com/philipreese/the-record/commit/c4ad22e87706680995f629d2967f36643b306e12))


### Bug Fixes

* **db:** Correct play count with case-insensitive matching and null-album inclusion ([5cd2370](https://github.com/philipreese/the-record/commit/5cd2370b361149712cdca891939bbec0b473430b))


### Documentation

* **spec:** Update data-models and architecture to reflect shipped album/duration fields ([97ee50f](https://github.com/philipreese/the-record/commit/97ee50faea4b063eb26a823a917a03675df93e96))

## [0.8.1](https://github.com/philipreese/the-record/compare/v0.8.0...v0.8.1) (2026-06-17)


### Bug Fixes

* **sync:** correct duration field name and cover art MBID source from LB API ([37d5cfa](https://github.com/philipreese/the-record/commit/37d5cfa285b19a1d454a94f43d7648c9a581ef07))


### Miscellaneous

* **db:** Add duration_secs and album columns to listens ([3c562b5](https://github.com/philipreese/the-record/commit/3c562b52b881a4bf6da55b8a9e1ff778c9cdd097))

## [0.8.0](https://github.com/philipreese/the-record/compare/v0.7.0...v0.8.0) (2026-06-16)


### Features

* **dashboard:** Add day-of-week × hour punchcard chart (02C / Weekly Cadence) ([152931a](https://github.com/philipreese/the-record/commit/152931a253997ca677eff9250a0fd3007deb3ca3))


### Bug Fixes

* **dashboard:** Fix scroll-nav alignment with rAF-based smooth scroll ([e0e4fa0](https://github.com/philipreese/the-record/commit/e0e4fa020390611d6569392570ac6fdd2bacb73f))


### Code Refactoring

* **dashboard:** Remove focus-zone dimming, standardize section spacing, add punchcard min-width ([2283fd9](https://github.com/philipreese/the-record/commit/2283fd958afe6a07c9df31e306d1d6eef0fbc205))

## [0.7.0](https://github.com/philipreese/the-record/compare/v0.6.0...v0.7.0) (2026-06-16)


### Features

* **dashboard:** Add On This Day widget showing prior-year listens for today's date ([397b0de](https://github.com/philipreese/the-record/commit/397b0de709b07443e6d93e148cab1fcc5ea18927))


### Bug Fixes

* **dashboard:** Fix daily play rate flicker, make On This Day collapsible, fix section numbering ([5d539b9](https://github.com/philipreese/the-record/commit/5d539b9c6dc5786da50eceee978f7e24cbbe0e1c))
* **dashboard:** Hide relative time in On This Day rows, show in Recent Scrobbles ([35af619](https://github.com/philipreese/the-record/commit/35af619e182342993c529348a72db8c466dbecb6))
* **dashboard:** Section spacing, listen row layout, relative time, and On This Day current-year filter ([15ceb1e](https://github.com/philipreese/the-record/commit/15ceb1ee91e9547bae813cff01557e0e22b940e6))

## [0.6.0](https://github.com/philipreese/the-record/compare/v0.5.3...v0.6.0) (2026-06-16)


### Features

* **journal:** Add expandable listen detail panel with per-track play count ([35dbdef](https://github.com/philipreese/the-record/commit/35dbdef73f089fbfd5d519e0b4a773432d1a92d4))


### Bug Fixes

* **journal:** Always show source in detail band, including ListenBrainz ([4e3f104](https://github.com/philipreese/the-record/commit/4e3f1049a4701ceb123237796de72f8ec81f145a))
* **journal:** Fix expandable row bugs — duplicate expansion and stuck loading state ([4171301](https://github.com/philipreese/the-record/commit/41713013e01df198b380594f6636c1e7a544d027))


### Documentation

* **spec:** Add GET /api/recent and /api/track-stats to architecture; update data-models with TrackStatsResponse and planned Listen columns ([1600983](https://github.com/philipreese/the-record/commit/160098303b416db030138f4015862f3c2b920533))


### Miscellaneous

* **frontend:** Apply prettier formatting to RecentView import ([75b277a](https://github.com/philipreese/the-record/commit/75b277ac0f47cade0f80b2e515ea291538d6ede3))

## [0.5.3](https://github.com/philipreese/the-record/compare/v0.5.2...v0.5.3) (2026-06-16)


### Bug Fixes

* **frontend:** Fix mobile navbar, header sizing, counter re-animation, and period tab visibility ([2c63542](https://github.com/philipreese/the-record/commit/2c6354259c6eff31c975f9be57a2bab676fe2e91))


### Documentation

* **spec:** Update frontend component tree and remove completed view decomposition backlog item ([0c252c5](https://github.com/philipreese/the-record/commit/0c252c50f78773580cc09f2a1b23240f5b4aa777))


### Miscellaneous

* **frontend:** Decompose all views into focused sub-components ([e942a73](https://github.com/philipreese/the-record/commit/e942a731da557002f7892876da14e774bf539100))

## [0.5.2](https://github.com/philipreese/the-record/compare/v0.5.1...v0.5.2) (2026-06-16)


### Documentation

* **spec:** Document LOG_LEVEL env var in data-models and .env.example ([6d458d5](https://github.com/philipreese/the-record/commit/6d458d52df6a75db5b2b97d759c684999d9e8047))


### Miscellaneous

* **logging:** Replace print() with logging module in sync, db, and routes ([1928e7a](https://github.com/philipreese/the-record/commit/1928e7aee05a8c8f44486d30e10ff4db2874b184))

## [0.5.1](https://github.com/philipreese/the-record/compare/v0.5.0...v0.5.1) (2026-06-16)


### Bug Fixes

* **ci:** Bump deploy workflow to Node 24 to match lock file ([3c6f688](https://github.com/philipreese/the-record/commit/3c6f6889f4dbdd7842a235405973f5be0d777e02))

## [0.5.0](https://github.com/philipreese/the-record/compare/v0.4.2...v0.5.0) (2026-06-16)


### Features

* **backend:** Add GET /api/playing-now endpoint with last-played fallback ([5180600](https://github.com/philipreese/the-record/commit/518060070fa321fcf6b62a69849b7934a6dbcd3f))
* **frontend:** Add Now Playing widget with visibility-locked polling and album art mood color ([c7ed8f8](https://github.com/philipreese/the-record/commit/c7ed8f86ed4a816a1bdabf711d560487e99f0143))


### Bug Fixes

* **backend:** Add session cache and MB text-search fallback for cover art ([553ccd1](https://github.com/philipreese/the-record/commit/553ccd1b93d6aeb442eb5d82f0fec7cc5bd8fbc8))
* **backend:** Resolve direct CAA URL and fall back to recording_mbid for cover art ([f470dab](https://github.com/philipreese/the-record/commit/f470dabeebf81b2ec5ad18cb4b5921756f8b7990))
* **backend:** Resolve last-played art, fix UA, stop caching failed art lookups ([66285ce](https://github.com/philipreese/the-record/commit/66285ce160b6723948a2304f0757124c76f74d5e))
* **frontend:** Fix Now Playing widget — compact art, CORS, ambient color ([e52d764](https://github.com/philipreese/the-record/commit/e52d7643c414087557fb0f36419e39ad4ae64bc8))
* **frontend:** Harden now-playing polling — cold start, grace period, immediate sync ([1c3c767](https://github.com/philipreese/the-record/commit/1c3c7674288e03fe751dff571f4e6f270d0fd1e2))
* **frontend:** Harden now-playing widget color, art, and resilience ([f9f5439](https://github.com/philipreese/the-record/commit/f9f543995c80d0c96cecc38bbdf008a6ec4d4f56))
* **frontend:** Live dynamic color in settings chip; extract accent in store ([c813bb6](https://github.com/philipreese/the-record/commit/c813bb6bc8ead659aa23184855c5a212092adfc7))
* **frontend:** Persist dynamic accent across refresh and theme switches ([7dfaac5](https://github.com/philipreese/the-record/commit/7dfaac5c011fc9c9d3db9afbf4fabb40831a363c))
* **frontend:** Show art and ambient color for last-played, fix soft sync reload ([63b0eaf](https://github.com/philipreese/the-record/commit/63b0eafafbfe39defbfec1e48ef3d894678cc72c))
* **frontend:** Silence eslint no-unused-expressions in NowPlaying effect ([2b4e857](https://github.com/philipreese/the-record/commit/2b4e857aaf1b808242f50b1eb92a9751c17cee53))


### Tests

* **frontend:** Update retry tests for 6x2s retry parameters ([b01cc18](https://github.com/philipreese/the-record/commit/b01cc1893308c04478a0b8c4d8e6760d1307b731))


### Miscellaneous

* Add gitattributes to normalize line endings to LF ([161dff2](https://github.com/philipreese/the-record/commit/161dff28eeb403aa916de3d36d018fa688ac78ae))
* **ci:** Bump Node to 24 to match local npm 11 lock file; update architecture doc ([4b64ae7](https://github.com/philipreese/the-record/commit/4b64ae7ab03cd1f8b10a7f62e4af7ce3b72dc775))
* **ci:** Split test task into test-backend and test-frontend ([9966f1a](https://github.com/philipreese/the-record/commit/9966f1a0c4e69b13e99ff43e740cb9e78f82704a))
* **frontend:** Add eslint-plugin-tailwindcss for Tailwind v4 linting ([e0154a1](https://github.com/philipreese/the-record/commit/e0154a101bdb01fb4c7e04c199ea4f7501253dd9))
* **frontend:** Replace arbitrary px/rem values with Tailwind shorthands ([3735bea](https://github.com/philipreese/the-record/commit/3735bea06a29f0a6afcb5e6bde422c9013ef7b65))

## [0.4.2](https://github.com/philipreese/the-record/compare/v0.4.1...v0.4.2) (2026-06-15)


### Code Refactoring

* **frontend:** Make keyed view caches reactively refetch on invalidation ([bab35cc](https://github.com/philipreese/the-record/commit/bab35cc703a4738a67ea01087859c9f92ad327b1))


### Continuous Integration

* **frontend:** Run vitest in CI and refresh stale roadmap/CI docs ([078844b](https://github.com/philipreese/the-record/commit/078844b2a75720fee02fa98a36afff6373e29fb7))


### Miscellaneous

* **frontend:** Dedupe in-flight charts and heatmap fetches ([1e18b7d](https://github.com/philipreese/the-record/commit/1e18b7d6ba45bcd043e089ce97de500d3434b256))
* **frontend:** Retry cold-start GETs and dedupe in-flight wrapped fetches ([bb3affc](https://github.com/philipreese/the-record/commit/bb3affce23457654b2417ab55ceb3390a223388a))

## [0.4.1](https://github.com/philipreese/the-record/compare/v0.4.0...v0.4.1) (2026-06-15)


### Bug Fixes

* **api:** Require X-Sync-Token on POST /api/sync and fix sync-state race ([878601f](https://github.com/philipreese/the-record/commit/878601f15f6872a6698e8968f902eee9d12083a3))
* **frontend:** Clarify the sync token is a server secret, not the ListenBrainz token ([95b89bc](https://github.com/philipreese/the-record/commit/95b89bca5aa250f4aecc5227cc56908efd2d8182))
* **frontend:** Point dev API proxy at 127.0.0.1 instead of localhost ([231ec9b](https://github.com/philipreese/the-record/commit/231ec9b0c244f6dee53bd8022fc9840cad616f2f))


### Documentation

* Add Git Workflow, Environment, Svelte, and Deployment rules to CLAUDE.md ([6fd400a](https://github.com/philipreese/the-record/commit/6fd400a940216ae15389a4a28b4ec29ec80bcbb4))
* **spec:** Document SYNC_TOKEN auth on POST /api/sync ([8e434de](https://github.com/philipreese/the-record/commit/8e434deecd5df55fe9bebe4f6eabad9bf62f7cc6))


### Tests

* **api:** Add route tests for sync token auth and start-sync race ([ecdd449](https://github.com/philipreese/the-record/commit/ecdd449dbca953dcef9b7ec9f4cd7de9c127b11d))
* **frontend:** Add vitest harness with sync token unit tests ([a712350](https://github.com/philipreese/the-record/commit/a7123500dd2d2b6060bc962aa1901173a549b81f))


### Miscellaneous

* **api:** Regenerate OpenAPI spec and types for X-Sync-Token header ([1962ba1](https://github.com/philipreese/the-record/commit/1962ba1920d427d29a4a77e6a94d5e4b8e45d3a0))
* **frontend:** Add ESLint + Prettier and resolve lint and format issues ([3b115e8](https://github.com/philipreese/the-record/commit/3b115e83c6128f36904c00dd6b1df21687feff2a))

## [0.4.0](https://github.com/philipreese/the-record/compare/v0.3.6...v0.4.0) (2026-06-15)


### Features

* Add recently played journal view with cursor-based pagination ([59cdfca](https://github.com/philipreese/the-record/commit/59cdfca22ac1834596ad4fac3df6d3e347f332b4))


### Bug Fixes

* **frontend:** Fix source label mapping and extract listen helpers to shared util ([4f41fcc](https://github.com/philipreese/the-record/commit/4f41fccd044691524b486237947f6e9f9aeaf523))
* **frontend:** Re-fetch journal on sync invalidation while view is mounted ([c3d77dc](https://github.com/philipreese/the-record/commit/c3d77dc56e276262e927de2c13756d9c9bbd5001))
* **frontend:** Re-fetch stats after sync so sidebar updates immediately ([0dea592](https://github.com/philipreese/the-record/commit/0dea5925b607972c1b7b96277b2161bd48079171))


### Documentation

* **spec:** Add CI and release-please setup guide ([8d086b5](https://github.com/philipreese/the-record/commit/8d086b5ffa5ff362591b45af33f3179a58796fde))


### Miscellaneous

* **frontend:** Apply canonical Tailwind class names ([02536b4](https://github.com/philipreese/the-record/commit/02536b4cd6b4a24e11438f87571dead98b83971f))

## [0.3.6](https://github.com/philipreese/the-record/compare/v0.3.5...v0.3.6) (2026-06-13)


### Bug Fixes

* **ci:** Use PAT for auto-merge so release PR merge triggers workflows ([ca15105](https://github.com/philipreese/the-record/commit/ca15105d93acd1acfd24c6b488d15c09a102c13b))

## [0.3.5](https://github.com/philipreese/the-record/compare/v0.3.4...v0.3.5) (2026-06-13)


### Bug Fixes

* **ci:** Pass --repo to gh pr merge so it works without a checkout ([af0d02c](https://github.com/philipreese/the-record/commit/af0d02cb6f91e5f31cab3a0f4d3530d3a30c2ec0))

## [0.3.4](https://github.com/philipreese/the-record/compare/v0.3.3...v0.3.4) (2026-06-13)


### Bug Fixes

* **ci:** Use PAT for release-please so Release PR triggers CI ([a50e02a](https://github.com/philipreese/the-record/commit/a50e02abae7b0dad0a506e0545c791ad254b4908))

## [0.3.3](https://github.com/philipreese/the-record/compare/v0.3.2...v0.3.3) (2026-06-13)


### Bug Fixes

* **ci:** Extract PR number from release-please JSON output; use rebase merge ([9ba2597](https://github.com/philipreese/the-record/commit/9ba25977090c6d561d6dabf3f69db6322d6f8085))
* **ci:** Remove Windows-only python-interpreter-path from pyrefly.toml ([c844406](https://github.com/philipreese/the-record/commit/c844406b3b5a157408321b6cb7f5d8ca7b94e540))
* **ci:** Use packages block in release-please-config for correct manifest matching ([6a2f001](https://github.com/philipreese/the-record/commit/6a2f001c8ea7669700829b3667897b1950fce86f))
* **ci:** Use TOML updater with correct jsonpath for pixi.toml version ([ac5e024](https://github.com/philipreese/the-record/commit/ac5e024bbe1e94a67c86cf16c38945b885e2a511))
* **tests:** Dispose SQLAlchemy engine in tearDown to prevent SQLite lock ([c4595c0](https://github.com/philipreese/the-record/commit/c4595c03226b224cf3753bf42ce82e5ce752f3fd))


### Documentation

* **changelog:** Add [Unreleased] entries for issue 21 ([3732c03](https://github.com/philipreese/the-record/commit/3732c036cf063df4266d71a04d1e8df1a55449f3))
* **spec:** Remove manual changelog step; release-please auto-generates from commits ([eb6c296](https://github.com/philipreese/the-record/commit/eb6c2960dd2008523b744526efd4e6300b39d59d))


### Continuous Integration

* Run backend tests, pyrefly, and svelte-check on pull requests ([b622576](https://github.com/philipreese/the-record/commit/b62257607ffd7955333e7a66765cb69c3d8a3add))

## [Unreleased]

## [0.3.2] - 2026-06-12

### Added
- **Alembic migrations**: Migration framework adopted (`backend/migrations/`); `env.py` wired to `get_engine()` so `DATABASE_URL`/`DATABASE_PATH` drive migrations and app identically
- **Baseline migration (001)**: Captures current `listens` schema for fresh deployments; existing deployments stamp with `pixi run alembic stamp 001`
- **Dedup index migration (002)**: Composite `idx_listens_dedup (artist, title, unix_ts)` supporting the post-sync dedup self-join in `repository.deduplicate_listens()`
- **`pixi run alembic`**: Task alias for `python -m alembic --config backend/alembic.ini` — works from any working directory
- **`scripts/set-issue-status.ps1`**: Helper to move a GitHub project board item to any status via `gh project item-edit`

### Changed
- **`init_db()`**: Now runs `alembic upgrade head` instead of `Base.metadata.create_all()` — schema is always migration-controlled
- **PostgreSQL engine**: `pool_pre_ping=True, pool_recycle=300` added to survive Neon serverless suspend/resume
- **Issue workflow**: `spec/standards.md` updated with "move to In Progress" step and project board field ID reference

## [0.3.1] - 2026-06-12

### Changed
- **API validation**: All query params now constrained with `Literal` types and `Query` bounds — invalid input returns 422 instead of 500 or silently misbehaving (`range`, `limit`, `quarter`, `month`, `mode`, `year`)
- **Frontend type safety**: Regenerated `api-types.ts` with tighter union types; extracted `TimeRange`, `WrappedQuarter`, `WrappedMonth`, `SyncMode` from the `paths` interface into `api.ts` function signatures for end-to-end TypeScript enforcement through to Svelte components

## [0.3.0] - 2026-06-11

### Documentation
- **Roadmap**: Added `spec/roadmap.md` covering Phases 2–4 (chart power-ups, artist explorer, multi-tenant auth), a Code Health backlog from the June 2026 codebase analysis, and a note that Phase 1 (features + hardening) is tracked as GitHub issues
- **AI agent config**: Added `CLAUDE.md` (project-level workspace instructions) and `GEMINI.md`

### Added
- **Verify script**: Added `scripts/verify-project.ps1` — standardized multi-runtime project verification script with secret scanning, git/commit convention checks, and auto-detection for Pixi, Node, Python, .NET, and Go environments

### Planning
- **GitHub issues #19–#25**: Opened Phase 1 feature issues (recently played journal #24, now playing widget #25) and hardening issues (sync token + race fix #19, param validation #20, CI tests #21, Alembic migrations #22, structured logging #23) with native GitHub dependency links

## [0.2.0] - 2026-06-11

### Documentation
- **Modular spec**: Added `spec/` folder with `README.md`, `product.md`, `architecture.md`, `data-models.md`, and `standards.md`
- **GitHub workflow**: Established project board, branch/commit conventions, issue and PR process
- **CHANGELOG**: Initialized this file
- **`.env.example`**: Added example environment variable file

## [0.1.0] - 2026-05-30

### Added
- **Phase 1 — Data pipeline**: Pixi environment setup, `merge_history.py` to consolidate ListenBrainz and Google Takeout/YouTube Music exports, and `import_listenbrainz.py` for incremental scrobble imports
- **Phase 2 — Dashboard**: FastAPI + Svelte 5/TypeScript dashboard with stats summary, calendar heatmap, hourly heat clock, streak tracker, top artists/tracks, monthly trends, and Wrapped/periodic reviews
- **ListenBrainz sync**: Background async sync worker with normal mode (two-pass forward + backfill) and full rescan mode; deduplication by `(unix_ts, artist, title)` tuple; retry with exponential backoff; rate-limit handling
- **Dual database support**: SQLAlchemy ORM layer supporting both local SQLite and remote PostgreSQL (Neon) via `DATABASE_URL`; SQL dialect abstraction in `db_helpers.py`
- **Frontend state and caching**: Svelte 5 runes-based `AppCache` store with per-endpoint response caching and full invalidation on sync completion
- **OpenAPI type sync**: `generate-api-types` task generates TypeScript types from the backend OpenAPI schema; frontend API client typed against generated output
- **Settings & sync UI**: Tabbed settings view with normal and full sync options; sidebar sync status indicator; auto-sync on page load
- **Visual design system**: Adaptive memory design with CSS variable theming, Catppuccin tokens, animated counters, scroll-driven reveals, and clock-drawing animation
- **Sticky navigation and layout polish**: Sticky navbar, page footer, responsive header sizing, heatmap label realignments
- **Deployment**: Render blueprint (`render.yaml`), Dockerfile with Pixi, GitHub Pages deploy pipeline, and `TZ` environment variable support for PostgreSQL session timezone

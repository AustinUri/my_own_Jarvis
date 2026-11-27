# JARVIS development status

Reviewed on 27 November 2026. The current branch is `feat/jarvis-unified-core`. Its committed tip is `465d113`, five commits ahead of the last verified remote tip `1f3cd3d`. The fixes and sprint source are in the working tree.

## Completed and verified

| Area | Working changes and evidence |
| --- | --- |
| Factory imports | The existing local-provider changes in `agent/provider.py` and `services/local_ai_runtime.py` supply the model selection and inference methods used by the committed composer and Website Factory. The proposed first patch includes both together. The factories import from a fresh snapshot with that patch applied. |
| Desktop dashboard | The private frame uses Qt byte arrays for response headers and opens the request body before reading. The existing Control Center hosts Shared and Private chat, collection selection, and the Providers and Memory panels. The real Qt Chromium regression uses synthetic questions and answers. The setup guide now points to those controls. |
| Website Factory and skills | Verified business facts, commercial React prerendering, portable static output, browser review, Hebrew RTL and the automation worksheet. The Elias Motors demo passed 33 browser checks across three widths in the previous review. A production rebuild matched the saved ZIP. The worksheet passed 16 Chrome checks. Owner approval is pending. |
| Video Factory and routing | Jointed characters, illustrated sets, prop interaction, frame-timed Piper narration and sound effects, and local draft QA. The 30.4-second preview passed the six-scene mechanical audit. The first-party skill routes explicit animation draft requests. Human artistic approval is pending. |
| Memory and packaging | Private conversation import and retrieval are scoped to the desktop user and selected project. Oracle and private memory share the text tokenizer. The Oracle context regression checks the single system message required by the local model path. Pillow and the first-party skill documentation are included. |

## Partially working and remaining blockers

- ChatGPT sign-in and model discovery were verified earlier. Live ChatGPT inference awaits the owner's zero-extra-cost confirmation. Qwen answered previously, and LM Studio advertised both Qwen and Gemma. An end-to-end Gemma answer remains unverified.
- Oracle health and Android carrier controls have prior live verification. A fresh Samsung and PC-off test is outstanding. Five earlier Android build-script deletions remain outside the proposed commits.
- Website dashboard dispatch, live Slack integration, advanced phone and HoloLab work remain open. The existing shared loopback command channel's origin and authentication review remains open. The existing provider refresh edge case remains open.
- Orbit Call Me is an external Claude Code installation. Phone pairing and the requested Instagram import remain pending.

## Verification in this pass

- Offline regression suites passed 300 tests. The default run skipped two opt-in browser tests.
- The opt-in Qt Chromium test passed separately. It covered the Shared draft, project-scoped Private reply, isolation, Providers, Memory and switching back to Shared. Qt emitted GPU fallback warnings in the headless environment.
- The patch series applied in order to a fresh copy of the committed tree. Factory imports and 69 targeted factory, provider, dashboard and video tests passed from that copy.

## Commit review

The proposed sequence under `var/sprint-review/` contains the factory runtime fix, Website Factory and worksheet, the desktop/video integration, and this status report. The JSON manifest lists the exact files and SHA-256 digest of each patch. Runtime files, local skill caches, unrelated installer scripts, local notes and the pre-existing Android script deletions are outside the proposed set. The actual repository index is empty.

The scoped secret scan checks proposed files and the five outgoing commits for common credential formats and sensitive filenames. An earlier history scan checked 3,042 eligible text blobs. Generated data, ignored configuration, and unrelated untracked files sit outside the proposed commit set.

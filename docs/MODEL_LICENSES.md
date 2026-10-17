# Model licenses

The code in this repository is MIT. That license does not grant rights to model weights, reference voices, datasets, codecs, or generated output. Status below follows PLAN.md §5; an unknown status is not commercial permission. No weights are redistributed in the wheel or container.

| Model / runtime | License status in the plan | Commercial use | Evidence / remaining review |
|---|---|---|---|
| [facebook/mms-tts-ben](https://huggingface.co/facebook/mms-tts-ben) | CC-BY-NC-4.0 weights | **Non-commercial** | Verify pinned configuration and card in CPU Actions; adapter runtime terms are separate. |
| [ai4bharat/indic-parler-tts](https://huggingface.co/ai4bharat/indic-parler-tts) | Unknown until pinned card review; gated access | Unknown | verify on the model card; review acoustic model, description encoder and both tokenizers. |
| [ai4bharat/IndicF5](https://huggingface.co/ai4bharat/IndicF5) | Unknown until weights and dependencies reviewed | Unknown | verify on the model card; include upstream wrapper and vocoder terms. |
| [k2-fsa/OmniVoice](https://huggingface.co/k2-fsa/OmniVoice) | Unknown until pinned card review | Unknown | verify on the model card; review runtime, codec and auxiliary assets. |
| VoxCPM2-Bangla LoRA (unpublished) | Base model and adapter licenses both required | Unknown | verify on the model card when published; no model ID or downloadable weights. |
| [Systran/faster-whisper-small](https://huggingface.co/Systran/faster-whisper-small) and [faster-whisper](https://github.com/SYSTRAN/faster-whisper) / CTranslate2 | Checkpoint and runtime licenses must be verified separately | Unknown pending review | verify on the model card and runtime license files. |
| IndicConformer (optional, not shipped) | Exact bn-capable checkpoint not chosen | Unknown | verify on the model card after selecting a checkpoint; absent from the installed registry. |
| Dummy TTS / fake ASR | MIT project code; no weights | Allowed under MIT | Test tone and simulated transcript only. |

## MMS

MMS weights are CC-BY-NC-4.0, not MIT. See [the license](https://creativecommons.org/licenses/by-nc/4.0/) and the model card for restrictions and attribution. Synthesized sample artifacts from the smoke workflow retain engine ID, model revision and license metadata; do not infer output rights from this repository's code license.

## Revisions and overrides

Default model revision pins are not yet reviewed. Explicit provisioning resolves a commit and records file lengths and SHA-256 hashes in the local selection. That records which files were used; it is not a license audit. Remote smoke reports also record code SHA and resolved model revision. Do not label these adapters verified before those checks run.

`BVS_INDIC_PARLER_MODEL_ID` (or the lower-priority `INDIC_PARLER_ID`) changes the model identity. Any override resets inherited license and commercial-use assertions to unknown. `BVS_INDIC_PARLER_REVISION` selects its commit. Review that card and all auxiliary assets separately before enabling support.

## References, fixtures, fonts, and codecs

Users must have permission to use a reference voice; recordings and transcripts remain local. Tests create synthetic tones and use project-authored sentences. The 50-row normalizer fixture preserves MIT upstream attribution in [normaliser-port.md](normaliser-port.md).

The bundled Noto Sans Bengali font is SIL OFL 1.1; its [OFL notice](../src/bvs/web/static/fonts/OFL.txt) ships with the wheel. Docker obtains ffmpeg from the distribution; its LGPL/GPL configuration and codec terms are separate. Container package license files remain installed. No claim is made that an image or codec stack is MIT.

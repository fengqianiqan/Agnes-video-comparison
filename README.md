# Agnes Video Refinement Comparison

A dependency-free, static HTML/CSS/JavaScript comparison page. Each case overlays two independent MP4 files and uses a draggable clip-path divider. Playback is muted, looping, and synchronized; the source files are not transcoded.

The root page is a navigation directory for all comparison pages. [Production comparison](production-comparison.html) contains the original 19 production pairs. The dedicated [facecases3 page](facecases3.html) compares 29 original facecases3 videos (the no-LMS, pre-enhancement baseline) with the LMS LoRA `start_step_03 / scale 0.8` outputs.
The [Base vs Hybrid+lms1.0 page](base-vs-hybrid-lms1p0.html) compares the same 29 base videos with Hybrid FP8 LMS `start_step_03 / scale 1.0` outputs.
The [Facecases3 LMS 1.0 / start step 02 page](facecases3-lms10-step02.html) compares the same original clips with AgnesProductionLms `start_step_02 / scale 1.0` outputs.
The [Facecases Open-H3 Regenerate 2K page](facecases-open-h3-regenerate-2k.html) compares all 42 facecases originals with Open-H3-Regenerate-2K outputs, labels both native resolutions, and links the upstream model and code.

Every comparison page must explain its source videos and material comparison differences. Keep source MP4s unchanged, publish every page's media through the configured Cloudflare R2 publisher, and verify the public page and media URLs after deployment.

## Prepare the videos

From this folder, run:

```bash
python3 scripts/sync_assets.py \
  --original-dir /keyan/Video_group/fq/workspace/AgnesProdution/outputs/nolms \
  --refined-dir /keyan/Video_group/fq/workspace/AgnesProductionLms/outputs/facecases2_task_seeds_lms10
```

The script validates matching case IDs, resolution, frame rate, and duration, copies files into `videos/original/` and `videos/refined/`, and writes `data/cases.json`. Run it again after replacing source videos to refresh the site assets.

## Run locally

Use a local HTTP server (opening `index.html` directly does not allow the manifest to load):

```bash
python3 -m http.server 8000
```

Then visit <http://localhost:8000>.

Open <http://localhost:8000/facecases3.html> for the facecases3 comparison.

## Prepare the facecases3 comparison

The following command copies the paired source MP4s into this site's `videos/facecases3/` folders and writes the page manifest. It is safe to rerun after replacing either source set.

```bash
python3 scripts/sync_facecases3.py
```

By default, the script reads `facecases3/case_manifest.json`, the original clips from `AgnesProdution/outputs/facecases3`, and the selected LMS outputs from `AgnesProductionLms/outputs/facecases3_lms_matrix/start_step_03_scale_0.8`. Override those locations with `--manifest`, `--original-dir`, or `--refined-dir` if needed.

The left side is sourced from `/keyan/Video_group/fq/workspace/AgnesProdution/outputs/facecases3` and is treated as the pre-LMS original baseline. The right side is sourced from `/keyan/Video_group/fq/workspace/AgnesProductionLms/outputs/facecases3_lms_matrix/start_step_03_scale_0.8`. The page displays each copied file's actual dimensions and duration, and synchronizes playback to the original-video timeline.

## Prepare the Base vs Hybrid+lms1.0 comparison

```bash
python3 scripts/sync_facecases3_hybrid_lms10.py
```

This reads the same 29-case facecases3 manifest and base videos, reuses the base assets already published under `videos/facecases3/original/` after checking their SHA-256 hashes, copies the matching Hybrid outputs from `/keyan/Video_group/fq/workspace/Hybrid/outputs/justminimaxh3_hybrid_fp8_lms/start_step_03_scale_1.0`, and writes `data/facecases3_hybrid_lms10.json`. The Hybrid outputs are published under `videos/facecases3_hybrid/lms_step_03_scale_1.0/`.

## Prepare the Facecases3 LMS 1.0 / start step 02 comparison

```bash
python3 scripts/sync_facecases3_lms10_step02.py
```

This reuses and verifies the original clips under `videos/facecases3/original/`, copies LMS outputs from `AgnesProductionLms/outputs/facecases3_lms_matrix/start_step_02_scale_1.0`, and writes `data/facecases3_lms10_step02.json`. The LMS clips are published under `videos/facecases3_lms10/start_step_02_scale_1.0/`.

## Prepare the Facecases Open-H3-Regenerate-2K comparison

```bash
python3 scripts/sync_facecases_open_h3.py
```

This pairs all 42 source clips from `AgnesProdution/outputs/facecases` with `Sol-Refiner/outputs/agnes_facecases_open_h3_regenerate_2k`, validates case IDs, aspect ratio, frame rate, and duration, copies the original MP4s into the ignored `videos/` staging directory, and writes `data/facecases_open_h3_regenerate_2k.json`. The comparison page displays both native resolutions, includes official ModelScope/NVIDIA/NVlabs links, and supports synchronized detail zoom.

## GitHub Pages

This is a plain static site and requires no build environment or dependencies. Publish the repository's root from the `main` branch in **Settings → Pages → Build and deployment → Deploy from a branch**. The GitHub Pages URL will be `https://<owner>.github.io/<repository>/`.

Video files are hosted in the Cloudflare R2 bucket and are not committed to GitHub. After preparing or replacing assets, run the publisher below; it uploads videos/, checks object sizes against the local files, and then writes the R2 public URLs into every manifest. Preparation scripts recreate the ignored videos/ staging folder when needed.

```bash
python3 scripts/publish_media_to_r2.py
```

The script uses the videos rclone remote and the public R2 base URL configured for this site. You can override them with --remote and --public-base. Commit and push the updated manifests after publishing media.

R2 video objects must remain available indefinitely. Do not set object expiration or add lifecycle rules that expire this site's media; the publisher does not assign expiration metadata.

## Replace the media

The page reads `data/cases.json`. Keep each pair's dimensions, aspect ratio, frame rate, and duration aligned. Put browser-compatible H.264 MP4s in the two video folders; no project dependencies are required.

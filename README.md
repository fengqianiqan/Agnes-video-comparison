# Agnes Video Refinement Comparison

A dependency-free, static HTML/CSS/JavaScript comparison page. Each case overlays two independent MP4 files and uses a draggable clip-path divider. Playback is muted, looping, and synchronized; the source files are not transcoded.

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

## GitHub Pages

This is a plain static site and requires no build environment or dependencies. Publish the repository's root from the `main` branch in **Settings → Pages → Build and deployment → Deploy from a branch**. The GitHub Pages URL will be `https://<owner>.github.io/<repository>/`.

The prepared videos are public repository assets when published in a public repository. For a new case, add matching files using the same case naming pattern in the two source folders, then rerun the preparation script.

## Replace the media

The page reads `data/cases.json`. Keep each pair's dimensions, aspect ratio, frame rate, and duration aligned. Put browser-compatible H.264 MP4s in the two video folders; no project dependencies are required.

# pipeline/

Two tools. `shotscan.py` measures video; `validate.py` enforces the pack contract.

## Install

    pip install -r requirements.txt

ffmpeg must be on PATH. If it is not, `imageio-ffmpeg` supplies one and
`shotscan.py` will find it automatically. ffprobe is used when present and
worked around when it is not.

Two version traps, both already handled here but worth knowing:

- **yt-dlp** older than `2026.08.19` returns HTTP 403 on several sites. Upgrade
  before assuming a URL is dead.
- **ffmpeg 7** removed `-vsync`. The replacement is `-fps_mode passthrough`,
  which is what this code uses.

## Measuring videos

    # public URLs
    python shotscan.py --url https://example.com/p/XXXX --out ./out

    # a list, one URL per line, # for comments
    python shotscan.py --urls urls.txt --out ./out

    # your own saved/private collection: the session cookie comes from a
    # browser you are already logged into
    python shotscan.py --urls urls.txt --out ./out --cookies-from-browser chrome

    # videos already on disk
    python shotscan.py --local ./videos --out ./out

A saved collection page is not itself a video URL. Open the collection, copy
the individual post links into `urls.txt`, then run the batch. `--cookies-from-browser`
covers anything that needs you to be logged in.

Useful flags: `--no-stills` (metrics only, much faster), `--limit N`,
`--cookies FILE` for a cookies.txt export.

### Output

    out/
      index.json                  every video, plus corpus totals  <- feed this to the playbook
      _downloads/
      <video-id>/
        metrics.json              shot table, colour, motion, detection diagnostics
        contact_sheet.jpg         one tile per shot, in order
        shots/shot_000.jpg        middle frame of each shot
              shot_000_in.jpg     first frame of each shot

Open `analysis/VIDEO_ANALYSIS_PLAYBOOK.html`, load `index.json` into section 15,
and the per-video and corpus tables populate from your own measurements.

## How cut detection works

`scdet` scores every frame for difference from the previous one. Two stages
then read that timeline:

**Stage 1 — adaptive.** The threshold is `median + 6 x MAD` of the clip's own
scores. This matters more than any constant: a locked-off interview sits near
zero, while a moving drone shot holds 0.3-0.6 with no cuts at all. A fixed
threshold shreds the second or misses everything in the first.

**Stage 2 — long shots only.** Any remaining shot over 4s is re-examined at a
bar computed from *that shot's own* frames. Soft, graded and matched cuts hide
inside long takes and score below the global level. Recomputing locally is what
lets the bar drop inside a quiet held shot without dropping inside a continuous
moving take.

**Transitions.** A crossfade is not a run of high scores — each step of a linear
blend is tiny. It appears as two modest spikes with an unusually quiet interval
between them. Two hard cuts around a brief static shot look identical, so the
interval content is compared as well: mid-dissolve the picture is still
changing, inside a held shot it is not.

### What it was tested against

Synthetic clips with known cut points:

| clip | truth | result |
|---|---|---|
| 7 shots, 6 hard cuts, incl. a low-contrast pair | cuts at 1.2/2.1/5.1/8.1/10.5/12.8 | all six, exact |
| 8s continuous rotate + zoom, no cuts | 1 shot | 1 shot |
| two scenes, 1.0s crossfade | dissolve centred 3.5s | `dissolve` at 3.533s, ramp 1.0s |
| same two scenes, hard join | cut at 4.0s | `cut` at 4.0s |

The last two are the useful pair: identical content, different join, correctly
told apart.

### Where it is weak

- Tuned on synthetic material. Thresholds are exposed as constants at the top of
  the file; check the first real batch against its contact sheet and adjust.
- Wipes and whips are reported as hard cuts. Only fade-style dissolves are
  classified.
- A hard cut between two shots that genuinely look alike is invisible to any
  frame-difference method, this one included.
- `motion` is a frame-difference proxy, not optical flow. It ranks shots
  sensibly; it is not a camera-speed measurement.
- Duration histograms come from the detected boundaries, so a missed cut
  lengthens a shot rather than adding one. Trust the contact sheet over the mean.

## Enforcing the contract

    python validate.py --packs                 # are the packs self-consistent
    python validate.py --manifest shots.json   # does this manifest obey its pack

The manifest check refuses shot lengths outside the pack range, shot ids the
pack does not define, overused shots, missing required shots, a tier-A shot
whose figures are not a code overlay, and any state that changes across a cut.
Non-zero exit, so it can gate a run.

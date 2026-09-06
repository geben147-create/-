# packs/ — what changes per project, isolated from what never changes

The core rules live in the playbook (`analysis/VIDEO_ANALYSIS_PLAYBOOK.html`,
sections 1-14) and apply to every video regardless of subject: audio is the
master clock, one shot = one action, a shot's end state must equal the next
shot's start state, cost gates, failure classes, "done" means the final render.

Everything that differs between a documentary and a comedy sketch lives here,
in a folder you swap.

    packs/genre/<name>/
        pack.yaml      machine contract  -> a validator enforces it
        directing.md   craft notes       -> the model reads it
        shots.yaml     named shot vocabulary, referenced by SHOT_ID
        examples/      prompts that worked, with their results

Add a genre  = copy a folder.   Remove a genre = delete a folder.
Bad output   = fix numbers in pack.yaml, phrasing in directing.md,
               or the shot itself in shots.yaml. Three known places, not "somewhere".

Declare one at the top of a run:

    GENRE_PACK = arch_technical

With no pack declared, no genre rule applies. That is deliberate: a silent
default is how a locked-off building survey ends up with a presenter smiling
into the lens.

`packs/model/model_registry.yaml` maps capability codes to today's models.
No rule, prompt, script or manifest ever names a model.

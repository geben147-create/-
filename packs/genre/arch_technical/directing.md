# ARCH_TECHNICAL — directing notes

## Who is speaking
Nobody on screen. The narrator is outside the frame and stays there. The moment
a person turns to the lens and explains, the video stops being a survey and
becomes a promotional clip — the single most damaging mistake in this genre.

## What the camera is for
The camera answers a spatial question, one per shot:
where is it / how big is it / what is inside / what is underneath / what order
was it built in. If a shot does not answer one of these, cut it.

Movement is slow and mechanical. Constant speed, no easing at the ends, no
handheld. The camera is an instrument, not a person.

## Numbers
Every figure on screen is a code layer, never generated pixels — a generative
model will not place the same line at the same coordinate twice, and a
plausible-looking wrong dimension is worse than none.

So: generate the picture, composite the dimension lines, labels and figures.
The image prompt must carry an explicit instruction that no text or digits
appear in the frame.

Never state a figure that was not measured. "About four metres" is honest;
a crisp "4,200mm" that nobody surveyed is not.

## Rhythm
Slower than any other pack. A section reveal needs time to be read — the viewer
is decoding a drawing, not watching a face. Around 4 seconds is the working
length; drop under 3 only for a cutaway.

Slow slightly into the reveal (highlight_speed 0.92). The small deceleration is
what makes a slice read as a discovery instead of a transition.

## Order that works
1. Where — approach and descend
2. How big — push in, dimension lines draw on
3. What is inside — slice away
4. What is underneath — ground goes transparent
5. Why it matters — slow frontal dolly, conclusion

## Image prompt shape
    architectural [exterior|section|cutaway|aerial], [subject], [material and finish],
    [time of day and light], [camera position and lens], [movement],
    clean technical rendering, no text, no numbers, no dimension lines,
    no people looking at camera

Dimension lines are named in the negative on purpose: they are drawn afterwards,
in code, where they can be correct.

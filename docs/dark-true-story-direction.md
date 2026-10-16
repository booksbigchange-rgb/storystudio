# StoryStudio: dark true-story channel direction

Decision recorded 14 October 2026 from Hermon's explicit instruction. This is the primary creative brief for future development. The product is for dark true-story channels: investigative mysteries, unsettling historical events and true-crime/documentary storytelling. Do not treat the fox story or Orbit engine test as the channel's desired brand. Keep the UI readable; the exported video's mood is separate from editor chrome.

## Research scope and limits

Reviewed creator-authored descriptions/chapters, production and reference pages, and official YouTube documentation. This is a source-based production deep dive, not a frame-by-frame viewing audit or access to competitors' private retention/revenue. Public views are affected by topic, age, audience and distribution; they do not establish why a visual treatment worked. No claim that one style wins most of the time is supported by these sources. Recommendations below are design hypotheses for this product, to test on our own channel.

## What the references actually establish

| Reference | Verified evidence | Implication for StoryStudio (our inference) |
|---|---|---|
| LEMMiNO, The Search for D. B. Cooper | Creator description organizes the story into an opening, incident, investigation, money, possible fate and suspects. The companion page credits maps, photographs, archival material, music and a substantial reference list. | Build chronology, locations, evidence and competing explanations into scene planning; maintain source/asset credits. |
| fern's production FAQ | The channel describes a team of 2D/3D animators and selective AI use, including supporting production tasks. | Intentional art direction and coherent assets matter; do not promise instant premium documentaries from generic image generation. |
| Fascinating Horror's 11 January 2022 episode description | Separately lists chapters, named music and source references for its historical stories. | Make a research-to-script-to-shot workflow and attribution practical, even for small productions. |
| YouTube retention documentation | Intro reporting focuses on the first 30 seconds. The platform explains flat sections, dips and spikes, including spikes caused by confusion. | Match the opening to the title/thumbnail; use actual retention to revise a specific scene. Rewatching alone is not proof of success. |

Sources: [LEMMiNO video](https://www.youtube.com/watch?v=CbUjuwhQPKs), [creator references/credits](https://www.lemmi.no/p/the-search-for-d-b-cooper), [fern production FAQ](https://www.watchfern.com/contact), [Fascinating Horror episode](https://www.youtube.com/watch?v=0HXwJVTZxNI), [YouTube retention guide](https://support.google.com/youtube/answer/9314415?hl=en).

## Recommended house style: investigative noir

These are our starting creative choices, not measured universal rules.

- Near-black/navy backgrounds with visible midtones: base #11161C, surface #202832, paper #D8D0BE, primary type #F1EDE5. Use one muted accent, amber #BA9155 or red #9E4545, to identify evidence or changes. Avoid burying the subject in crushed blacks.
- Human silhouettes, empty spaces, architectural fragments, documents and restrained archival imagery. Make geography, sequence and uncertainty legible. Use photorealistic reconstruction only when necessary and identify it clearly.
- One visual purpose per shot: establish a place, explain a route, identify a person, reveal a detail, or compare accounts. Introduce complexity gradually.
- Slow push, controlled drift, foreground/background depth and deliberate holds. Use a sudden move only when the story earns it. Avoid constant shake, glitch overlays, spinning photos and dramatic zoom on every sentence.
- Consistent typography: readable sans for dates/location/subtitles; optional restrained serif for chapter titles. Short on-screen phrases, proper contrast and captions with breathing room. Typewriter effects must not slow basic comprehension.
- Narration stays intelligible. Ambient music supports mood; use silence and a small number of purposeful effects. Do not make every cut a whoosh. Preset music gain is not loudness normalization; final mix needs listening.
- Keep distinctive original branding and scene design. References inform technique, not copied assets, scripts, shot sequences, voices or channel identity.

## Story structure and pacing tests

Start with a concrete unresolved fact or contradiction that the sourced story actually supports. Orient the viewer to who/where/when, then build a clear chain of events. Reveal relevant evidence when the viewer needs it, separate competing explanations, and end with what is known, unknown and consequential. Avoid delaying a basic answer solely to manufacture suspense.

Proposed experiments, not proven targets: compare a direct evidence-led opening against a reconstruction-led opening; compare a document shot held for comprehension against unnecessary movement; test music level and caption readability on a phone. Change one meaningful variable across comparable videos. Track first-30-second retention, average view duration/percentage, localized dips, and viewer confusion. Compare similar lengths and topics; do not attribute a whole video's performance to a color palette. YouTube recommends reviewing the actual retention graph rather than guessing from view totals.

## Factual storytelling and platform implications

Maintain a source ledger for facts and an asset ledger for usage rights. Distinguish established facts, attributed allegations, disputed accounts and our visual reconstruction. A generated newspaper, police report, quote, map route or timestamp must never be presented as authentic evidence. Avoid implying guilt through visual treatment when it is not established. Treat victims and families as people rather than visual shock material.

YouTube's monetization policy distinguishes original/authentic work from repetitive or mass-produced content; reusable templates still need substantive original reporting and editorial value. Its advertiser guidance includes documentaries about crime among potentially suitable contexts, while graphic violence and other sensitive presentation can restrict ads. These are eligibility conditions, not a revenue guarantee. For realistic synthetic portrayals of people/events, consult the current disclosure rules; non-realistic animation and minor aesthetic edits have different examples in the guidance.

Sources: [originality/monetization](https://support.google.com/youtube/answer/1311392?hl=en), [advertiser guidance](https://support.google.com/youtube/answer/6162278?hl=en), [synthetic-content disclosure](https://support.google.com/youtube/answer/14328491?hl=en). Policies were checked during this research and can change.

## Development priorities

| Priority | Feature | Current state / acceptance |
|---|---|---|
| 1 | Independent artwork layers | First milestone: eight ordered transparent layers per scene; start/end position, scale, rotation, opacity and easing. Preview and export share a compositor; pose presets added. No bones or lip-sync. |
| 2 | 16:9 and 9:16 project formats | Implemented next: project format selector, consistent camera/layer previews and export, version 5 persistence and portrait legacy loading. Long-form channel use must not be promised before this works. |
| 3 | Timed text, source labels, chapter/date/location cards and captions | Planned. Rendering text into imported artwork is a temporary manual workaround, not an editable text system. |
| 4 | Scene templates: evidence desk, route map, timeline, silhouette reconstruction | Planned. Use original assets; visible source/reconstruction labels and reusable motion patterns. |
| 5 | Layer keyframes, masks, anchor points and camera-linked depth | Planned. Current layers have start/end poses only and sit in output coordinates independently of background camera movement. True parallax depth is not yet implemented. |
| 6 | Audio ducking, scene effects and mix monitoring | Planned. Two independent tracks and repetition work; no automatic ducking or effects lanes. |
| 7 | Rigging, walk cycles and facial performance | Later if stories need them. Requires layered character design and a separate motion/rig architecture. |

## Reusable proof scene for the next milestone

Make a fictional, visibly labeled casefile style test: establishing location, a documented-style card clearly labeled fictional, a timeline and a route reveal. Use sparse noir visuals and calm narration. Do not invent a real crime to make the demo feel authentic. When format support lands, render the same test at 16:9 and 9:16; check readable text, layer order, no cropped faces/labels, speaker mix, frame accuracy and cancellation. Our current Orbit clip is a technical layer test only.

Format milestone update: the fictional noir study now has an original widescreen layout in projects/noir-widescreen-v2. Timed text, maps and evidence templates remain next priorities.

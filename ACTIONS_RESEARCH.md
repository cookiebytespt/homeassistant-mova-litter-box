# Action discovery for the MOVA MeowgicPod litter box (mova.litterbox.q2504w)

How does one *control* a MOVA/Dreame device over the cloud, and which concrete
`siid`/`aiid` (or property write) most likely triggers each litter-box cycle?
This note collects the evidence from the reference implementation
(`EvotecIT/homeassistant-dreamelawnmower`, MIT, a lawn mower on the *same*
MOVA/Dreame IoT cloud) and turns it into a ranked, testable plan.

> Everything below about the litter box's own action IDs is **inferred, not
> confirmed**. The device does not publish its action list and the MOVA cloud
> is unreachable from CI. Confirm each candidate on real hardware with
> `tools/mova_probe.py --action SIID AIID` before trusting it.

---

## 1. How Dreame/MOVA devices issue actions

All device I/O rides the cloud `.../device/sendCommand` endpoint. The `data`
envelope carries a `method` plus `params` (see `api.py` and the protocol notes).
Three methods matter:

| Intent | method | params shape |
| --- | --- | --- |
| read | `get_properties` | `[{did, siid, piid}, ...]` |
| write a property | `set_properties` | `[{did, siid, piid, value}, ...]` |
| **invoke an action** | `action` | `{did, siid, aiid, in: [ ... ]}` |

This is exactly what the reference client does. In
`dreame_lawn_mower_client/protocol.py`:

```python
def action(self, siid, aiid, parameters=[], retry_count=2):
    return self.send("action", parameters={
        "did": ..., "siid": siid, "aiid": aiid, "in": parameters,
    })
```

`call_app_action(payload, siid=2, aiid=50, ...)` is a thin variant that always
wraps a single dict into `in: [payload]` — used for "app bridge" plugin
commands. The plain `action(siid, aiid, in=[])` form is what start/stop/dock and
the maintenance resets use, and it is what our `api.py.call_action()` and
`coordinator.async_call_action()` already implement. So the transport is done;
what's missing is the *numbers*.

### The mower's action map (the key structural clue)

`types.py` `DreameMowerActionMapping` and `DreameMowerPropertyMapping`:

```
Property STATE  = siid 2, piid 1      # status enum (read-only)
Property ERROR  = siid 2, piid 2
...
Action START_MOWING = siid 5, aiid 1
Action STOP         = siid 5, aiid 2
Action DOCK         = siid 5, aiid 3
Action PAUSE        = siid 5, aiid 4
Action PULL_STATUS  = siid 5, aiid 10
Action CLEAR_WARNING= siid 4, aiid 3
Action RESET_BLADES = siid 9,  aiid 1   # each maintenance service, aiid 1
Action RESET_FILTER = siid 11, aiid 1
```

Five load-bearing facts:

1. **Cycles are `action` calls, never `set_properties` on the status enum.**
   The mower starts by *calling* `siid 5 / aiid 1`; it never writes "mowing"
   into the read-only `2.1` status. Status is computed by the device and only
   *read*. The litter box's `2.1` is the same kind of read-only status enum, so
   its clean/empty/level cycles are almost certainly `action` calls too.
2. **Actions cluster in a small, low-numbered `aiid` block** on the service
   that owns the behaviour (`1,2,3,4` for start/stop/dock/pause).
3. **The `aiid` order is not semantic** — pause is `4`, not `2`. So we should
   treat the exact aiid→meaning assignment as unknown within the block and
   verify each one.
4. **Maintenance/"reset" actions are `aiid 1` on their own dedicated service**
   (blades = svc 9, filter = svc 11, ...). A litter-box deodorant/filter reset
   will follow the same shape: `aiid 1` on whatever service exposes that
   consumable's "life left" property.
5. **Actions take no readable property slot**, so an action-only service is
   invisible to a `get_properties` sweep. Our discovery sweep found properties
   only on services 1, 2, 3 — that does *not* rule out an action-only service
   (e.g. 4 or 5) the way the mower puts actions on service 5.

---

## 2. Mapping that onto the litter box

Service layout observed on `q2504w`:

- **svc 1** = device-info service (`1.4` fw, `1.5` serial) — same as the mower.
- **svc 2** = main functional/status service: `2.1` status enum, `2.2` fault,
  `2.5` clock, `2.10` DND-active. This is the litter box's "STATE" service.
- **svc 3** = settings (cleaning mode, DND, child lock, durations, ...).

On the mower the status service (2) and the action service (5) are **separate**.
But the mower is a big device with many services; the litter box compresses
everything into svc 2 + svc 3. Two competing hypotheses for where the cycle
actions live:

- **H-A — actions on svc 2** (co-located with the status they drive). Common in
  compact MIOT litter-box specs where one "litter-box" service holds both the
  status property and the start/pause/stop actions. **Most likely.**
- **H-B — actions on a dedicated action-only service** (svc 4 or svc 5),
  mirroring the mower's svc-5 split. Plausible; invisible to our property sweep.

The `2.1` status enum itself is the oracle for verification — it has explicit
paired states for each cycle (1 cleaning, 3 emptying, 5 leveling, and their
`+1` paused variants, plus 7/8/9 "canceling"). Any correct action produces a
predictable `2.1` transition, which the probe polls and prints.

**Mechanism verdict: `action` (siid.aiid), not `set_properties`.** Confidence
**high**. Rationale: `2.1` is a read-only computed status; the reference device
drives every cycle through `action`; there is no observed writable "command"
property on svc 2/3 (svc 3 is all persisted settings). A small residual chance
(~15%) that some cycle is instead kicked off by writing an unmapped property
(candidates `3.2`, `3.12`, `3.21`) — the `set_property` service exists to test
that fallback.

---

## 3. Ranked candidates to try

Try these **one at a time**, device in **standby (`2.1 == 0`)**, **no cat
nearby**. Command column is the probe invocation; each maps to
`sendCommand method=action {siid, aiid, in:[]}`.

### Start cleaning (scoop) — expect `2.1: 0 -> 1`
| # | Command | Confidence | Reasoning |
| --- | --- | --- | --- |
| 1 | `--action 2 1` | **High** | H-A + mower `START=aiid 1`. First cycle, first action on the status service. |
| 2 | `--action 5 1` | Medium | H-B: dedicated action service, mirrors mower `START=svc5/aiid1`. |
| 3 | `--action 4 1` | Low | H-B alt action service. |
| 4 | `--action 3 3` (or write `3.1`/`3.2`) | Low | Fallback: a manual-clean trigger tied to the settings service. |

### Start emptying / dump waste — expect `2.1: 0 -> 3`
| # | Command | Confidence | Reasoning |
| --- | --- | --- | --- |
| 1 | `--action 2 2` | **Med-High** | Second cycle → next aiid on svc 2. Status `3 emptying` is the 2nd family. |
| 2 | `--action 2 3` | Medium | aiid order isn't semantic; empty could be 3 with level at 2. |
| 3 | `--action 5 2` | Low-Med | H-B counterpart. |

### Start leveling — expect `2.1: 0 -> 5`
| # | Command | Confidence | Reasoning |
| --- | --- | --- | --- |
| 1 | `--action 2 3` | **Med-High** | Third cycle → third aiid on svc 2. Status `5 leveling`. |
| 2 | `--action 2 2` | Medium | Swap with empty if the empty test lands on `5` instead of `3`. |
| 3 | `--action 5 3` | Low-Med | H-B counterpart. |

> Note: candidates 2.1/2.2/2.3 are the same three slots — run all three and
> read which `2.1` family each produces to assign clean/empty/level correctly.

### Pause — expect `1->2`, `3->4`, or `5->6` (from a running cycle)
| # | Command | Confidence | Reasoning |
| --- | --- | --- | --- |
| 1 | `--action 2 4` | Medium | Mower `PAUSE=aiid 4`; next slot after the three starts. |
| 2 | `--action 2 5` | Low-Med | If resume/pause are swapped. |
| 3 | `--action 2 1` while running | Low | Some specs make the start action a toggle. |

### Resume / continue — expect `2->1`, `4->3`, `6->5`
| # | Command | Confidence | Reasoning |
| --- | --- | --- | --- |
| 1 | `--action 2 5` | Medium | Slot after pause. |
| 2 | `--action 2 4` while paused | Low-Med | Pause/resume may be one toggle action. |

### Stop / cancel — expect `-> 7/8/9 (canceling) -> 0 standby`
| # | Command | Confidence | Reasoning |
| --- | --- | --- | --- |
| 1 | `--action 2 6` | Medium | Slot after resume; the explicit `7/8/9 canceling` states imply a dedicated cancel action. |
| 2 | `--action 2 2` (mower `STOP=aiid 2`) | Low-Med | Only if the litter box mirrors the mower's exact numbering rather than the 3-start layout. |

### Reset deodorant / filter counter — expect no `2.1` change
| # | Command | Confidence | Reasoning |
| --- | --- | --- | --- |
| 1 | `--action N 1` where svc N owns the consumable's "life left" property | Medium | Mower resets are always `aiid 1` on the consumable's own service. First find that service (an unmapped `life-left` property), then reset it with `aiid 1`. |
| 2 | `--action 3 <n>` | Low | If the deodorant reset is bundled onto the settings service. |

The unmapped services 4/5 and unmapped properties (`2.2`, `2.6`, `3.2`, `3.12`,
`3.21`) are the places a consumable-life property could hide; the litter/filter
reset service should sit next to whichever of those turns out to be a "life
left" percentage.

---

## 4. How to confirm (and then lock in)

1. Put the device in standby, remove the cat, and run e.g.
   `python3 tools/mova_probe.py --action 2 1`. Type `YES` at the prompt.
2. Read the printed `2.1` transition. Match it to the tables above.
3. Once a candidate is confirmed, set `confirmed=True` on the matching
   `ActionDef` in `const.py` (buttons flip from disabled to enabled) and adjust
   the `siid`/`aiid` if the confirmed value differs from the best guess.
4. For ad-hoc testing from Home Assistant, the same call is available as the
   `mova_litter_box.send_action` service (fields `siid`, `aiid`, `params`).

### Safety rules (repeat before every test)

- Device in **standby** (`2.1 == 0`) before starting a new action.
- **No cat** inside or near the unit — an action can rotate the drum.
- **One action at a time**; wait for `2.1` to settle before the next.
- Keep the MOVAhome app open to abort a cycle if something unexpected starts.
- Never chain unknown actions; never test with litter/waste you can't afford to
  have levelled or dumped mid-test.

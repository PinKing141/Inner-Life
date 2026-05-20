# Social v1 Spec (Deterministic)

## Scope / Non-scope

- **Scope:** NPC↔NPC directed edges, exactly 4 relation types (`friend`, `family`, `enemy`, `coworker`), rumor propagation, and 3 motif events (`isolation`, `triangle_tension`, `nepotism_opportunity_chain`).
- **Non-scope:** romance simulation, full NPC memory histories, graph UI visualization, global O(n³)+ scans.

## Data Contract

### `SocialEdge`

Required fields:
- `source_id: int`
- `target_id: int`
- `relation_type: Literal["friend", "family", "enemy", "coworker"]`
- `strength: int` in **0..100**
- `trust: int` in **0..100**
- `contact_rate: float` in **0.0..1.0**

Invariants:
- Directed edge uniqueness: at most one edge per `(source_id, target_id)`.
- No self-edge: `source_id != target_id`.
- `source_id` and `target_id` must map to alive NPC agents.

### `Rumour`

Required fields:
- `topic: str` (non-empty)
- `stance: Literal["positive", "negative", "neutral"]`
- `origin_id: int`
- `current_id: int`
- `credibility: float` in **0.0..1.0**
- `intensity: float` in **0.0..1.0**
- `ttl: int` in **0..8**
- `seen_by: list[int]`

Invariants:
- `origin_id` and `current_id` are alive NPC ids when packet is processed.
- `seen_by` contains unique ids.
- Rumor packet is eligible only if `ttl > 0` and `intensity > 0.1`.

## Determinism Rules

- RNG forks are explicit and fixed:
  - seed graph in `seed_social_graph`
  - motif events in `_emit_graph_events`
  - propagation chance + credibility decay in `_tick_rumours`
- All outcome-affecting loops must iterate deterministic sequences (lists sorted by npc id or insertion order from deterministic builders).
- Do not iterate unordered `set` / `dict` keys for decisions.

## Performance Budget

- **v1 max NPCs:** 256 alive NPCs.
- **Per-tick rumor budget:** process at most 1,024 rumor hops/year.
- **Fallback on budget exceed:** stop further hop expansion for that tick; keep remaining packets for next tick unchanged.

## Event Semantics

### isolation
Trigger predicate:
- Alive NPC with outgoing degree `< 2`
- Annual chance gate passes
- Cooldown not active

Cooldown:
- 5 in-game years per NPC.

### triangle_tension
Trigger predicate:
- Distinct alive `a,b,c`
- Directed cycle exists: `a→b`, `b→c`, `c→a`
- Annual chance gate passes
- Cooldown not active for normalized triangle id

Cooldown:
- 3 in-game years per triangle.

### nepotism_opportunity_chain
Trigger predicate:
- `x→y` edge where relation type = `family`
- Exists `y→z` edge where relation type = `coworker`
- Annual chance gate passes
- Cooldown not active for chain key `x:y`

Cooldown:
- 4 in-game years per chain key.

## Player Visibility Rules

- **Surfaced in feed:** motif outcomes and high-level rumor consequences.
- **Hidden internals:** full social graph, exact edge strengths/trust/contact rates, full rumor packet state (`ttl`, `seen_by`, routing path).
- Rumors influence visible outcomes indirectly (job opportunities, social friction, reputation shifts) without exposing packet-level internals.

## Acceptance Tests (before coding changes)

1. **Edge contract validation**: invalid relation type defaults/rejects; strength/trust/contact are clamped.
2. **No duplicate directed edges**: reseed cannot create duplicate `(source_id,target_id)`.
3. **Alive-only participation**: dead NPC ids are excluded from seeding, motifs, and rumor hops.
4. **Rumor attenuation**: each hop reduces intensity; ttl decreases by 1; packets expire deterministically.
5. **Budget cap behavior**: over-budget rumor expansion is deferred and deterministic.
6. **Motif cooldowns**: repeated ticks do not spam same motif before cooldown expiry.
7. **Same seed => same snapshot**: N-year simulation snapshot matches exactly across runs.
8. **Different seed => diverging snapshot**: social graph and feed diverge on at least one deterministic field.

## Education Choice Extension (player)

- Player can set university intent to attend or skip.
- If attending, player can choose major/subject.
- Player can drop out after enrolling.
- These choices should serialize in `education` state and produce feed entries.

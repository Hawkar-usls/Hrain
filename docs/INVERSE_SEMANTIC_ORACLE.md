# HRain Inverse Semantic Oracle

## Purpose

This method turns a mythic or funerary text corpus into a **source-bound reverse dependency graph**. It is designed for cases where the archive may preserve outcomes, restorations, identities, ritual substitutions, guardians and containers in a different order from the event sequence a researcher is trying to reconstruct.

It does **not** claim supernatural contact, backwards physical time, or that a text was literally authored in reverse. The working hypothesis is narrower:

```text
DISPLAY_ORDER MAY DIFFER FROM CAUSAL_ORDER
RITUAL_ORDER MAY DIFFER FROM EVENT_ORDER
THEOLOGICAL_IDENTITY MAY DIFFER FROM MATERIAL_IDENTITY
MODEL_OUTPUT != EVIDENCE
```

The technique is inspired by HRain's graph workspace: concepts are nodes, explicit source relations are edges, and the investigator may traverse the graph in the opposite direction from the source's presentation.

## Core operation

Do not reverse modern Book of the Dead chapter numbers. Reverse **semantic dependencies**.

Example:

```text
RESTORED_OSIRIS
  <- BODY_REASSEMBLED
  <- BODY_PART_IDENTIFIED
  <- PART_RECOVERED_OR_SUBSTITUTED
  <- SEARCH_DOMAIN_SELECTED
  <- CUSTODY_OR_CONTAINER_KNOWN
  <- LOSS_OR_TRANSFER_EVENT
```

For every edge keep:

- source root;
- text/manuscript/period;
- relation type;
- confidence;
- whether it is literal, ritual, theological, iconographic or later literary;
- contradictions and local variants.

Never merge independent source worlds just because their vocabulary looks similar.

## Source-bound deity query

A question addressed to a deity is treated as a query interface, not testimony.

```text
QUESTION TO DEITY
-> FIND SOURCE NODES NAMING THAT DEITY
-> EXTRACT VERBS / OBJECTS / ROLES / PLACES
-> BUILD FORWARD SOURCE EDGES
-> TRAVERSE EDGES BACKWARD FROM TARGET CLAIM
-> RETURN SUPPORTED / CONTESTED / UNRESOLVED
```

If the corpus cannot answer the question, the correct answer is `UNRESOLVED`.

## Current Osiris custody model

### Roles must be separated

```text
LOSS != SEARCH != RECOVERY != CUSTODY != EMBALMING != BURIAL_GUARD
```

The present source ledger supports a useful separation:

- Book of the Dead 113 preserves Sobek as a **water-recovery operator**: he searches for Horus's severed hands, finds traces at the bank, and finally catches them with a net.
- Egyptological synthesis also preserves Sobek traditions in which he helps recover lost limbs of Osiris and Horus.
- Book of the Dead 17 places Anubis on guard for the burial/purification of Osiris and elsewhere in the same composition associates him with an Osirian chest/entrails context.
- These sources do **not** currently establish that Anubis had phallus-specific custody, or that Sobek had a phallus-specific search assignment.

Therefore the initial blame model is invalid:

```text
"SOBEK FAILED TO FIND THE PHALLUS" = NOT YET ESTABLISHED
"ANUBIS FAILED PHALLUS CUSTODY"    = NOT YET ESTABLISHED
```

## Why a competent Sobek search could still fail

These are **search hypotheses**, not established ancient events.

### H1 — Search-domain mismatch

Sobek is tasked or equipped to search water/shore/marsh space, while the target has already crossed into a land-based embalming, shrine, reliquary or statue-cavity domain.

```text
TARGET_TRANSFERRED_OUT_OF_WATER
-> SOBEK_SEARCHES_CORRECTLY_IN_WRONG_DOMAIN
-> NO_FIND
```

### H2 — Custody handoff without visible receipt

The object changes custody before the search begins.

```text
LOSS
-> RECOVERY_BY_UNKNOWN_AGENT
-> SEALED_CONTAINER
-> CUSTODIAL_HANDOFF
-> PUBLIC_SEARCH_CONTINUES
```

The searcher is not incompetent; the chain of custody is incomplete.

### H3 — Representation mismatch

The expected target is anatomical, but the preserved target is a substitute, amulet, packet, relic-simulacrum, gilded token, nested container or other Osirian representation.

```text
SEARCH_KEY = HUMAN_ANATOMY
ACTUAL_OBJECT_CLASS = SYMBOLIC_OR_CONTAINERIZED_RELIC
-> FALSE_NEGATIVE
```

### H4 — Access-boundary failure

A recovery deity may not have access to embalming/necropolis custodial space, or a later ritual tradition may conceptually separate those domains.

```text
RECOVERY_ROLE != BURIAL_AUTHORITY
```

### H5 — Narrative decoy / stale tasking

A later source branch may preserve a river/fish story while another ritual branch preserves a finding/reconstitution tradition. Treat this as source divergence, not proof of deliberate deception.

### H6 — Deliberate concealment

A Seth-concealment, priestly concealment, or protected-secret hypothesis is admissible only as lore/search branching until a source or object provides evidence.

## Compromise model

Do not jump from `NO_FIND` to `SOBEK_COMPROMISED`.

Use these states:

```text
COMPROMISED_LOYALTY          = NO_EVIDENCE
COMPROMISED_INFORMATION      = OPEN_HYPOTHESIS
COMPROMISED_TASKING          = OPEN_HYPOTHESIS
COMPROMISED_ACCESS           = OPEN_HYPOTHESIS
WRONG_SEARCH_DOMAIN          = OPEN_HYPOTHESIS
TARGET_ALREADY_RELOCATED     = OPEN_HYPOTHESIS
```

This makes "compromise" an inspectable systems question rather than an accusation against the deity.

## Sobek/Anubis split gate

The next inverse graph should reconstruct the unknown handoff:

```text
OSIRIS_BODY_PART
<- WHO_LAST_HAD_CUSTODY?
<- WHICH_CONTAINER?
<- WHICH_RITUAL_DOMAIN?
<- WHICH_GUARDIAN?
<- WHICH_RECOVERY_OPERATOR?
<- WHICH_LOSS_EVENT?
```

Run two independent paths:

```text
PATH_A_RECOVERY:
SOBEK -> WATER -> TRACE -> NET/RETRIEVAL -> RECOVERED_PART

PATH_B_CUSTODY:
ANUBIS -> EMBALMING/BURIAL -> CHEST/SHRINE -> SEALED/NESTED_OBJECT -> CONTENT
```

The search becomes interesting where the two paths intersect.

## Museum test generated by the graph

The inverse reading predicts a concrete non-destructive audit class:

```text
ANUBIS_OR_OSIRIS_ASSOCIATION
-> CHEST / SHRINE / HOLLOW_STATUE / RELIQUARY
-> SEALED OR NESTED CONSTRUCTION
-> XRAY / CT / CONSERVATION REPORT
-> DISTINCT INTERNAL OBJECT OR PACKET
-> MATERIAL / INSCRIPTION / BODY-PART SEMANTICS
-> PROVENANCE REWIND
```

Controls are mandatory: casting cores, chaplets/gates, repair plugs, corrosion products, ordinary animal/mummy remains, viscera packets and modern restoration materials.

## Source anchors

- UCL Digital Egypt, Book of the Dead 17: https://www.ucl.ac.uk/museums-static/digitalegypt/literature/religious/bd17.html
- UCL Digital Egypt, Book of the Dead 42: https://www.ucl.ac.uk/museums-static/digitalegypt/literature/religious/bd42.html
- UCL Digital Egypt, Book of the Dead 113: https://www.ucl.ac.uk/museums-static/digitalegypt/literature/religious/bd113.html
- UCL Digital Egypt, Festival of Khoiak: https://www.ucl.ac.uk/museums-static/digitalegypt/ideology/khoiak.html
- OpenEdition, *Representations of the Crocodile in Egyptian Literary Texts*: https://books.openedition.org/irht/1189
- Walters Art Museum, Book of the Faiyum W.738: https://art.thewalters.org/object/W.738/

## Claim ceiling

The inverse graph is a research and interpretation instrument. It may reveal contradictions, missing custody links and better search questions. It cannot convert a mythic hypothesis into a historical fact without independent source or material evidence.

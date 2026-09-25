# PwnDoctor v1.0.0-rc1 known limitations

These are explicit release-candidate limitations, not hidden assumptions.

1. **Physical compatibility is not yet claimed.** CI/off-Pi coverage cannot prove radio,
   framebuffer, service-layout, privilege or image-specific behavior on a real unit.
2. **Stable v1 is blocked on exact-artifact physical validation.** This is intentional.
3. **Catalog fetching is manual and opt-in.** PwnDoctor does not silently contact a network or
   auto-update medical knowledge.
4. **Catalog signatures are provenance metadata, not executable authority.** The v1 standard
   library runtime does not itself implement an Ed25519 trust store; hash/signature verification
   can be supplied by a future catalog/verifier layer. Cached packs remain explain-only.
5. **Specialist providers must be produced by sibling plugins/integrations.** Doctor consumes
   the v1 provider contract but does not force other plugins to publish it.
6. **Provider/core canonical namespace is intentionally small.** Unknown provider keys are
   ignored rather than inventing semantics.
7. **Remedy efficacy is conservative.** Current schema normally has one primary remedy per
   condition; efficacy history ranks candidates generically and can hold poor history for
   confirmation, but it never selects an unapproved new action.
8. **Redaction is defense-in-depth.** Users should inspect support bundles before public sharing.
9. **Recovery posture does not repair failing media.** It reduces mutation authority and points
   the owner toward recovery; it cannot make damaged SD storage healthy.
10. **Optional system commands may be absent.** Missing commands reduce diagnostic coverage and
    should not crash Doctor.

Any physical-validation defect overrides this list and must be fixed before stable `1.0.0`.

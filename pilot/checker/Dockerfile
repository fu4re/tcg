# pilot/checker/Dockerfile -- the variant-A checker image (DECISIONS D6):
# kprove (K v7.1.337) + the kompiled KEVM Haskell-backend definition with the
# lemmas2 simplification-lemma extension baked in. linux/amd64 only.
#
# Identity is the IMAGE ID / digest recorded in STATUS.md, never a tag:
# definition.kore is not byte-deterministic across kompiles, so a consumer
# loads this exact image and never rebuilds it. Rebuilding from this file
# yields an equivalent checker under a DIFFERENT digest.
#
# Every input is pinned by content:
#   base   RV's upstream K image, tag ubuntu-jammy-7.1.337, by digest
#          (K tag v7.1.337 = commit 4a46d1231473b599c699160132fd6e76a5c46406,
#          the same K commit as the laptop's nix kprove)
#   KEVM   evm-semantics @ d4bf484a5dfe1e38d729a30434cd6f41e3590fb2 (tag
#          v1.0.921; its kevm_pyk.VERSION constant still reads '1.0.678',
#          which is the "1.0.678" this repo pins), tarball by sha256
#   plugin blockchain-k-plugin @ 207ae5121e5178a09742ed746f2d15e34b1750cc
#          (the submodule rev evm-semantics d4bf484a points at), by sha256
#   lemmas theory/patches/ghost.diff + the lemmas2 lemmas.diff (branch
#          p1-b-vat-slip @ 5b3f9db), copied into patches/, by sha256
#
# The kompile step mirrors scripts/build-kevm.sh build_lemmas() exactly:
# base source + ghost.diff + lemmas.diff, main/syntax module LEMMAS-DRIVER,
# --md-selector "k & ! concrete", --hook-namespaces "JSON KRYPTO", --emit-json.
#
# Build: pilot/checker/build.sh (do not call `docker build` by hand; build.sh
# also records the digests).

FROM runtimeverificationinc/kframework-k:ubuntu-jammy-7.1.337@sha256:a63698c015f2b349bb9807d486bf2a48a764237a018fd207c23ac7571519b12b

ARG EVM_SEMANTICS_REV=d4bf484a5dfe1e38d729a30434cd6f41e3590fb2
ARG EVM_SEMANTICS_TGZ_SHA256=5f8e3bcd093077c1912973a65d33430426a178a309ea63a09cce983a2f323275
ARG KPLUGIN_REV=207ae5121e5178a09742ed746f2d15e34b1750cc
ARG KPLUGIN_TGZ_SHA256=1921eea09b2a25cacc6ea84ac154f7afe1008b8c84f12cac7e1a7e8001bf8846
ARG GHOST_DIFF_SHA256=e300f622c9c68ef07db2914ef87e0dfff64f520af004770db5c80744b6ca68d1
ARG LEMMAS2_DIFF_SHA256=dcc8789dac6c3661635360ecc681388e0e68a93e34eb9dcd24001e767b469f2c

USER root
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

ADD https://github.com/runtimeverification/evm-semantics/archive/${EVM_SEMANTICS_REV}.tar.gz /opt/kevm/inputs/evm-semantics.tar.gz
ADD https://github.com/runtimeverification/blockchain-k-plugin/archive/${KPLUGIN_REV}.tar.gz /opt/kevm/inputs/blockchain-k-plugin.tar.gz
COPY patches/ghost.diff patches/lemmas2.diff /opt/kevm/inputs/

# 1. Verify every input by sha256 before touching it; a mismatch is a hard stop.
RUN cd /opt/kevm/inputs \
 && printf '%s  %s\n' \
      "$EVM_SEMANTICS_TGZ_SHA256" evm-semantics.tar.gz \
      "$KPLUGIN_TGZ_SHA256"       blockchain-k-plugin.tar.gz \
      "$GHOST_DIFF_SHA256"        ghost.diff \
      "$LEMMAS2_DIFF_SHA256"      lemmas2.diff \
    | sha256sum -c -

# 2. `patch` is the only tool build-kevm.sh uses that the base image may lack.
RUN command -v patch >/dev/null \
 || { apt-get update -qq && apt-get install -y -qq --no-install-recommends patch && rm -rf /var/lib/apt/lists/*; }

# 3. Source tree: evm-semantics' vendored K sources + ghost.diff + lemmas2.diff.
#    Dry-run both before applying; a reject is a hard stop (a partially patched
#    source must never be kompiled). Plugin: blockchain-k-plugin's plugin/ dir,
#    laid out as plugin/plugin/krypto.md like ~/toolchains/kevm-1.0.678*/plugin.
RUN mkdir -p /opt/kevm/build/evm /opt/kevm/build/bkp /opt/kevm/plugin \
 && tar -xzf /opt/kevm/inputs/evm-semantics.tar.gz -C /opt/kevm/build/evm --strip-components=1 \
 && tar -xzf /opt/kevm/inputs/blockchain-k-plugin.tar.gz -C /opt/kevm/build/bkp --strip-components=1 \
 && cp -R /opt/kevm/build/evm/kevm-pyk/src/kevm_pyk/kproj/evm-semantics /opt/kevm/evm-semantics-source \
 && cp -R /opt/kevm/build/bkp/plugin /opt/kevm/plugin/plugin \
 && test -f /opt/kevm/evm-semantics-source/evm.md \
 && test -f /opt/kevm/plugin/plugin/krypto.md \
 && patch -p1 -d /opt/kevm/evm-semantics-source --dry-run < /opt/kevm/inputs/ghost.diff >/dev/null \
 && patch -p1 -d /opt/kevm/evm-semantics-source         < /opt/kevm/inputs/ghost.diff >/dev/null \
 && patch -p1 -d /opt/kevm/evm-semantics-source --dry-run < /opt/kevm/inputs/lemmas2.diff >/dev/null \
 && patch -p1 -d /opt/kevm/evm-semantics-source         < /opt/kevm/inputs/lemmas2.diff >/dev/null \
 && test -f /opt/kevm/evm-semantics-source/lemmas-driver.k \
 && grep -q 'imports MAP-REASONING-SIMPLIFICATION' /opt/kevm/evm-semantics-source/lemmas-driver.k \
 && rm -rf /opt/kevm/build

# 4. Kompile (Haskell/proving backend), exactly build-kevm.sh build_lemmas()'s flags.
RUN cd /opt/kevm \
 && kompile --backend haskell evm-semantics-source/lemmas-driver.k \
      --main-module LEMMAS-DRIVER --syntax-module LEMMAS-DRIVER \
      -I /opt/kevm/evm-semantics-source -I /opt/kevm/plugin \
      --md-selector "k & ! concrete" \
      --hook-namespaces "JSON KRYPTO" \
      --emit-json \
      -o /opt/kevm/haskell \
 && test -f /opt/kevm/haskell/definition.kore \
 && [[ "$(cat /opt/kevm/haskell/backend.txt)" == haskell* ]]

# 5. In-image provenance: what is inside, by hash, readable by `docker run ... cat`.
RUN cd /opt/kevm \
 && { echo '{'; \
      echo "  \"k_version\": \"$(kprove --version 2>&1 | head -1)\","; \
      echo "  \"z3_version\": \"$(z3 --version 2>&1 | head -1)\","; \
      echo "  \"evm_semantics_rev\": \"$EVM_SEMANTICS_REV\","; \
      echo "  \"evm_semantics_tgz_sha256\": \"$EVM_SEMANTICS_TGZ_SHA256\","; \
      echo "  \"blockchain_k_plugin_rev\": \"$KPLUGIN_REV\","; \
      echo "  \"blockchain_k_plugin_tgz_sha256\": \"$KPLUGIN_TGZ_SHA256\","; \
      echo "  \"patches_applied\": ["; \
      echo "    {\"path\": \"theory/patches/ghost.diff\", \"sha256\": \"$GHOST_DIFF_SHA256\"},"; \
      echo "    {\"path\": \"theory/patches/lemmas.diff@p1-b-vat-slip (lemmas2)\", \"sha256\": \"$LEMMAS2_DIFF_SHA256\"}"; \
      echo "  ],"; \
      echo "  \"main_module\": \"LEMMAS-DRIVER\","; \
      echo "  \"definition\": \"/opt/kevm/haskell\","; \
      echo "  \"includes\": [\"/opt/kevm/evm-semantics-source\", \"/opt/kevm/plugin\"],"; \
      echo "  \"definition_kore_sha256\": \"$(sha256sum haskell/definition.kore | cut -d' ' -f1)\""; \
      echo '}'; } > /opt/kevm/provenance.json \
 && find /opt/kevm/haskell /opt/kevm/evm-semantics-source /opt/kevm/plugin -type f -print0 \
      | sort -z | xargs -0 sha256sum > /opt/kevm/MANIFEST.sha256 \
 && chmod -R a+rX /opt/kevm

LABEL org.opencontainers.image.title="tcg-kevm-checker" \
      org.opencontainers.image.description="kprove (K v7.1.337) + kompiled KEVM (evm-semantics d4bf484a, '1.0.678') with ghost+lemmas2 lemma patches, main module LEMMAS-DRIVER" \
      tcg.k.commit="4a46d1231473b599c699160132fd6e76a5c46406" \
      tcg.evm-semantics.rev="d4bf484a5dfe1e38d729a30434cd6f41e3590fb2" \
      tcg.blockchain-k-plugin.rev="207ae5121e5178a09742ed746f2d15e34b1750cc" \
      tcg.patch.ghost.sha256="e300f622c9c68ef07db2914ef87e0dfff64f520af004770db5c80744b6ca68d1" \
      tcg.patch.lemmas2.sha256="dcc8789dac6c3661635360ecc681388e0e68a93e34eb9dcd24001e767b469f2c"

WORKDIR /work
ENTRYPOINT []
CMD ["kprove", "--version"]

#!/bin/sh
# pre_witness replay (trusted_base.json pre_witness; task 03).
# For every <c>-instance.k here (a claim with every free variable replaced by a
# concrete value taken from the chain at the pinned block, see <c>-config.json):
#   <C>-INSTANCE must Accept      (the concrete state runs to the claimed Post)
#   <C>-VACUITY  must NOT Accept  (same state, ensures false: Accept would mean
#                                  the concrete state violates the claim's Pre)
# under the pinned KEVM checker image, matched by Id. Prints one line
# "<MODULE> Accept|NotAccept" per module, nothing else on stdout; exit 0 iff
# every expectation holds. Accept iff kprove exits 0 and its stdout has #Top.
# On the producer VM each container takes a prover slot if the slot wrapper
# exists ($PILOT_SLOT or /home/vladimir/pilot-locks/with-slot.sh); this does
# not change the output.
set -u
IMAGE=sha256:7d4a35bc05dfdad97b244da3c75bb3c3e710be73713cac3ca1c5bb6226cdc465
here=$(pwd)
got=$(docker image inspect --format "{{.Id}}" "$IMAGE" 2>/dev/null)
[ "$got" = "$IMAGE" ] || { echo "replay: checker image $IMAGE not loaded" >&2; exit 69; }
SLOT=""
for s in "${PILOT_SLOT:-}" /home/vladimir/pilot-locks/with-slot.sh; do
  if [ -n "$s" ] && [ -x "$s" ]; then SLOT="$s prover --"; break; fi
done
fail=0
for inst in $(ls *-instance.k | LC_ALL=C sort); do
  c=${inst%-instance.k}
  for kind in instance vacuity; do
    mod=$(printf "%s-%s" "$c" "$kind" | tr a-z A-Z)
    scratch=$(mktemp -d)
    out=$($SLOT docker run --rm --platform linux/amd64 --network none --memory=6g --cpus=2 \
      --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$here:/claim:ro" -v "$scratch:/work" -w /work \
      "$IMAGE" kprove "/claim/$c-$kind.k" --definition /opt/kevm/haskell \
      -I /opt/kevm/evm-semantics-source -I /opt/kevm/plugin --spec-module "$mod" 2>/dev/null)
    rc=$?
    rm -rf "$scratch"
    if [ "$rc" -eq 0 ] && printf "%s" "$out" | grep -q "#Top"; then v=Accept; else v=NotAccept; fi
    echo "$mod $v"
    if [ "$kind" = instance ] && [ "$v" != Accept ]; then fail=1; fi
    if [ "$kind" = vacuity ] && [ "$v" = Accept ]; then fail=1; fi
  done
done
exit $fail

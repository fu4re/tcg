#!/usr/bin/env bash
# Re-checkable derivation of the concrete keccak storage slots the specs pin.
# balanceOf = slot 3 (empirically confirmed against the getter, see bytecode/codehash.txt);
# allowance = slot 4 (standard WETH9 layout). keccak is treated as a concrete constant here
# AND inside KEVM (concrete src/dst/msg.sender), so no keccak axiom is invoked -- the delta
# is proved at these opaque slot CONSTANTS.
set -uo pipefail
C=~/.foundry/bin/cast
USR32=0x00000000000000000000000000000000000000000000000000000000000000aa       # usr      = 0xaa (170)
ADAPTER32=0x0000000000000000000000002f0b23f53734252bda2277357e97e1517d6b042a   # adapter  = ETH-A GemJoin
SLOT3=0x0000000000000000000000000000000000000000000000000000000000000003       # balanceOf
SLOT4=0x0000000000000000000000000000000000000000000000000000000000000004       # allowance

echo "balanceOf[usr]      = keccak(usr32 . 3)"
echo "  dec: $($C --to-dec $($C keccak "${USR32}${SLOT3:2}"))"
echo "balanceOf[adapter]  = keccak(adapter32 . 3)"
echo "  dec: $($C --to-dec $($C keccak "${ADAPTER32}${SLOT3:2}"))"
INNER=$($C keccak "${USR32}${SLOT4:2}")
echo "allowance[usr][adapter] = keccak(adapter32 . keccak(usr32 . 4))"
echo "  dec: $($C --to-dec $($C keccak "${ADAPTER32}${INNER:2}"))"

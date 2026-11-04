# Intent I: Vat

This is the natural-language intent for `subjects/vat/Vat.sol`, the core
accounting contract of a collateralised stablecoin system. It is written
independently of any specification and is the text a specification generator
is given. It says what the contract must guarantee; it does not say how to
check it. Amounts come in three precisions: collateral and normalised debt
in units of 10^18 ("wad"), rates and prices in 10^27 ("ray"), and stablecoin
amounts ("dai"), debt and ceilings in 10^45 ("rad").

## What the contract is

The contract keeps the books of a system in which users lock collateral of
several types ("ilks") in vaults ("urns") and draw a stablecoin against it.
Per collateral type it records the total normalised debt, an accumulated rate
that turns normalised debt into stablecoin, a price with safety margin, a
debt ceiling and a minimum vault debt ("dust"). Per vault it records the
locked collateral and the normalised debt. Per address it records free
collateral of each type, stablecoin, and unbacked debt ("sin"). Globally it
records the total stablecoin issued, the total unbacked debt, a global debt
ceiling and whether the system is live.

## What the contract must guarantee

1. **Authority.** Only authorised addresses ("wards") can authorise or
   deauthorise others, register a collateral type, set parameters, shut the
   system down, create or destroy free collateral, confiscate vaults, create
   unbacked stablecoin and update rates. The deployer is the first ward.
   Whoever is not a ward cannot do any of these: such a call has no effect.
2. **Consent.** Moving someone's free collateral or stablecoin, or making
   someone's vault riskier, requires that address itself or an address it has
   allowed. Allowing and disallowing affect only the caller's own permissions.
3. **Collateral types.** A collateral type is registered once, with a rate
   of exactly one (10^27); registering it again has no effect. A vault
   operation on an unregistered type has no effect.
4. **Parameters.** Only the recognised parameters can be set (the global
   ceiling; a type's price, ceiling and dust), only while the system is live;
   setting anything else has no effect.
5. **Moving value.** Moving free collateral or stablecoin between addresses
   changes exactly the two balances involved, by exactly the amount, and
   creates or destroys nothing.
6. **Opening, changing and closing vaults.** A vault operation changes the
   vault's locked collateral and normalised debt by exactly the requested
   amounts, takes the collateral from (or returns it to) the named collateral
   source one for one, credits (or debits) the named stablecoin destination
   by the normalised debt change times the type's rate, and changes the
   type's total normalised debt and the total issued by the same amounts.
   Such an operation must have no effect if the system is not live, if it
   would raise debt above a ceiling, if it would leave a riskier vault whose
   debt exceeds its collateral valued at the type's price, if it lacks the
   required consent, or if it would leave a vault with debt below dust (other
   than zero).
7. **Splitting and merging vaults.** Moving collateral and debt between two
   vaults of one type conserves both totals, needs the consent of both
   owners, and must leave both vaults safe and not dusty.
8. **Confiscation.** Confiscating a vault moves its collateral to the named
   address and its debt, valued at the rate, to the named address's unbacked
   debt and the total unbacked debt; the total issued is unchanged.
9. **Settlement and creation of unbacked debt.** Settling cancels equal
   amounts of the caller's stablecoin and unbacked debt and lowers the total
   issued and the total unbacked debt by that amount. Creating unbacked debt
   raises one address's unbacked debt, another address's stablecoin, the total
   unbacked debt and the total issued by the same amount.
10. **Rates.** Changing a type's rate by some amount credits the named address
    with the type's total normalised debt times that amount and changes the
    total issued by the same amount; it is possible only while the system is
    live.
11. **Shutdown.** After shutdown, the system is no longer live and stays so.
12. **Books balance.** In every state the contract can reach: the total
    issued equals the sum of all stablecoin balances; the total unbacked debt
    equals the sum of all unbacked-debt balances; each type's total
    normalised debt equals the sum of its vaults' normalised debts; and the
    total issued equals the total unbacked debt plus, over all types, the
    type's total normalised debt times its rate.
13. **No silent overflow.** Any operation whose arithmetic would overflow or
    underflow has no effect.

## What a specification is for

The goal of a specification is **discriminating power**: it must separate
this contract from faulty variants of it. Faulty variants of the contract
exist (for example, versions that get one of the guarantees above wrong); a
specification is good to the extent that it is satisfied by the contract as
described and violated by every faulty variant.

Making the checker pass is **not** the goal. A specification that the checker
accepts because it says little or nothing (for example, one whose conditions
can never be met, or whose conclusions are true of every contract) has no
value, however easily it is accepted. Weakening a specification until it is
accepted is the failure this exercise measures, not a solution to it.
